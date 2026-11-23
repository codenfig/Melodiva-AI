#!/usr/bin/env python3
"""Safely COPY MixMaster generated-song data to Melodiva. Source is never modified.

Local-file backends only. Run against consistent DB/file snapshots after backups.
Default is a read-only dry-run. Use --execute to write the destination.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from urllib.parse import quote

SONG_CATEGORIES = ("full_song", "text_to_song")
SCHEMAS = {
    "generated_files": """CREATE TABLE IF NOT EXISTS generated_files (
        id TEXT PRIMARY KEY, category TEXT NOT NULL, name TEXT NOT NULL,
        storage_key TEXT NOT NULL, size INTEGER NOT NULL, mime TEXT NOT NULL,
        created_at TEXT NOT NULL, song_title TEXT, artwork_svg TEXT,
        license_status TEXT NOT NULL DEFAULT 'not_licensed')""",
    "commercial_license_requests": """CREATE TABLE IF NOT EXISTS commercial_license_requests (
        id TEXT PRIMARY KEY, file_id TEXT NOT NULL, contact_email TEXT NOT NULL,
        status TEXT NOT NULL, created_at TEXT NOT NULL)""",
    "commercial_license_orders": """CREATE TABLE IF NOT EXISTS commercial_license_orders (
        id TEXT PRIMARY KEY, file_id TEXT NOT NULL, request_id TEXT NOT NULL,
        stripe_session TEXT UNIQUE, stripe_payment_intent TEXT,
        amount INTEGER NOT NULL, currency TEXT NOT NULL,
        status TEXT NOT NULL, created_at TEXT NOT NULL, paid_at TEXT,
        license_id TEXT UNIQUE, issued_at TEXT)""",
    "stripe_processed_events": """CREATE TABLE IF NOT EXISTS stripe_processed_events (
        id TEXT PRIMARY KEY, processed_at TEXT NOT NULL)""",
}
DEFAULTS = {
    "generated_files": {"song_title": None, "artwork_svg": None, "license_status": "not_licensed"},
}


def connect_source(path):
    if not path.is_file():
        raise FileNotFoundError("Source SQLite metadata DB was not found: " + str(path))
    uri = "file:" + quote(str(path.resolve()), safe="/") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def has_table(conn, name):
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


def table_rows(conn, table, where="", params=()):
    if not has_table(conn, table):
        return []
    return [dict(row) for row in conn.execute("SELECT * FROM " + table + (" WHERE " + where if where else ""), params)]


def valid_path(root, key):
    root = root.resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Unsafe song storage key")
    return path


def digest(path):
    h = sha256()
    with path.open("rb") as inp:
        for chunk in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_verified(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if digest(source) != digest(target):
            raise ValueError("Destination file differs from source: " + str(target))
        return
    handle, tmp = tempfile.mkstemp(dir=str(target.parent), prefix=".melodiva-migration-")
    try:
        with os.fdopen(handle, "wb") as out, source.open("rb") as inp:
            shutil.copyfileobj(inp, out, 1024 * 1024)
        if digest(source) != digest(Path(tmp)):
            raise ValueError("Copied file checksum mismatch")
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def upsert_rows(conn, table, rows):
    if not rows:
        return
    columns = [r[1] for r in conn.execute("PRAGMA table_info(" + table + ")")]
    for row in rows:
        known = {key: row.get(key, DEFAULTS.get(table, {}).get(key))
                 for key in columns if key in row or key in DEFAULTS.get(table, {})}
        existing = conn.execute("SELECT * FROM " + table + " WHERE id=?", (row["id"],)).fetchone()
        if existing is not None:
            for key, val in known.items():
                if existing[key] != val:
                    raise ValueError("Conflicting destination record in " + table + ": " + str(row["id"]))
            continue
        keys = list(known)
        sql = "INSERT INTO " + table + " (" + ",".join(keys) + ") VALUES (" + ",".join("?" for _ in keys) + ")"
        conn.execute(sql, [known[k] for k in keys])


def migrate(source_root, dest_root, source_db, dest_db,
            source_projects, dest_projects, execute=False):
    src = connect_source(source_db)
    try:
        if not has_table(src, "generated_files"):
            raise ValueError("Source generated_files table was not found")
        songs = table_rows(src, "generated_files", "category IN (?, ?)", SONG_CATEGORIES)
        ids = {r["id"] for r in songs}
        requests = [r for r in table_rows(src, "commercial_license_requests") if r["file_id"] in ids]
        request_ids = {r["id"] for r in requests}
        orders = [r for r in table_rows(src, "commercial_license_orders")
                  if r["file_id"] in ids and r["request_id"] in request_ids]
        # The event ledger contains only commercial-license webhook IDs. Copy all
        # to avoid reprocessing already-consumed Stripe events after cutover.
        events = table_rows(src, "stripe_processed_events") if orders else []

        file_pairs = []
        for row in songs:
            source = valid_path(source_root, row["storage_key"])
            destination = valid_path(dest_root, row["storage_key"])
            if not source.is_file():
                raise FileNotFoundError("Source audio object missing: " + str(source))
            if source.stat().st_size != row["size"]:
                raise ValueError("Audio size does not match source metadata: " + str(source))
            if destination.exists() and digest(source) != digest(destination):
                raise ValueError("Destination audio conflicts with source: " + str(destination))
            file_pairs.append((source, destination))
        projects = []
        if source_projects.is_dir():
            for source in sorted(source_projects.glob("*.json")):
                destination = valid_path(dest_projects, source.name)
                if destination.exists() and digest(source) != digest(destination):
                    raise ValueError("Destination project draft conflicts with source")
                projects.append((source, destination))

        summary = {"songs": len(songs), "license_requests": len(requests),
                   "license_orders": len(orders), "processed_stripe_events": len(events),
                   "project_drafts": len(projects), "executed": execute}
        if not execute:
            return summary
        if source_root.resolve() == dest_root.resolve() or source_db.resolve() == dest_db.resolve():
            raise ValueError("Source and destination storage must be different")
        for source, destination in file_pairs + projects:
            copy_verified(source, destination)

        dest_db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(dest_db) as dst:
            dst.row_factory = sqlite3.Row
            for stmt in SCHEMAS.values():
                dst.execute(stmt)
            for table, cols in DEFAULTS.items():
                present = {r[1] for r in dst.execute("PRAGMA table_info(" + table + ")")}
                for column in cols:
                    if column not in present:
                        definition = "TEXT NOT NULL DEFAULT 'not_licensed'" if column == "license_status" else "TEXT"
                        dst.execute("ALTER TABLE " + table + " ADD COLUMN " + column + " " + definition)
            upsert_rows(dst, "generated_files", songs)
            upsert_rows(dst, "commercial_license_requests", requests)
            upsert_rows(dst, "commercial_license_orders", orders)
            upsert_rows(dst, "stripe_processed_events", events)
        # Post-copy verification includes stored file SHA-256, preserved IDs and metadata.
        with sqlite3.connect(dest_db) as dst:
            dst.row_factory = sqlite3.Row
            for row in songs:
                copied = dst.execute("SELECT * FROM generated_files WHERE id=?", (row["id"],)).fetchone()
                if not copied or any(copied[key] != value for key, value in row.items()):
                    raise ValueError("Destination metadata verification failed")
            for source, target in file_pairs + projects:
                if digest(source) != digest(target):
                    raise ValueError("Post-copy checksum mismatch")
        return summary
    finally:
        src.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--dest-root", type=Path, required=True)
    parser.add_argument("--source-db", type=Path)
    parser.add_argument("--dest-db", type=Path)
    parser.add_argument("--source-projects", type=Path)
    parser.add_argument("--dest-projects", type=Path)
    parser.add_argument("--execute", action="store_true", help="Copy files and metadata; default is read-only")
    args = parser.parse_args()
    srcroot, dstroot = args.source_root.expanduser(), args.dest_root.expanduser()
    srcdb = (args.source_db or (srcroot / "metadata" / "files.sqlite3")).expanduser()
    dstdb = (args.dest_db or (dstroot / "metadata" / "files.sqlite3")).expanduser()
    srcproj = (args.source_projects or (srcroot / "full_song_projects")).expanduser()
    dstproj = (args.dest_projects or (dstroot / "full_song_projects")).expanduser()
    result = migrate(srcroot, dstroot, srcdb, dstdb, srcproj, dstproj, execute=args.execute)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
