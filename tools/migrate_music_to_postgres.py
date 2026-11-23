#!/usr/bin/env python3
"""Copy MixMaster generated songs and licensing metadata to Melodiva PostgreSQL.

Dry-run by default. Source SQLite and files are never changed.
Set DATABASE_URL in the environment; do not put passwords in command history.
"""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from metadata_postgres import SCHEMA
from migrate_music_data import (
    SONG_CATEGORIES, connect_source, table_rows, has_table,
    valid_path, digest, copy_verified,
)

TABLES = ("generated_files", "commercial_license_requests",
          "commercial_license_orders", "stripe_processed_events")

def migrate(src_root, dst_root, src_db, execute=False):
    import psycopg
    from psycopg.rows import dict_row

    if src_root.resolve() == dst_root.resolve():
        raise ValueError("Source and destination storage roots must differ")
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("Set DATABASE_URL for the destination PostgreSQL database")
    with connect_source(src_db) as source:
        if not has_table(source, "generated_files"):
            raise ValueError("Source generated_files table not found")
        songs = table_rows(source, "generated_files", "category IN (?, ?)", SONG_CATEGORIES)
        ids = {row["id"] for row in songs}
        requests = [r for r in table_rows(source, "commercial_license_requests") if r["file_id"] in ids]
        request_ids = {r["id"] for r in requests}
        orders = [r for r in table_rows(source, "commercial_license_orders")
                  if r["file_id"] in ids and r["request_id"] in request_ids]
        events = table_rows(source, "stripe_processed_events") if orders else []
        data = dict(zip(TABLES, (songs, requests, orders, events)))
        files = []
        for row in songs:
            src = valid_path(src_root, row["storage_key"])
            dst = valid_path(dst_root, row["storage_key"])
            if not src.is_file() or src.stat().st_size != row["size"]:
                raise ValueError("Missing or incorrect source audio: " + str(src))
            if dst.exists() and digest(src) != digest(dst):
                raise ValueError("Conflicting destination audio: " + str(dst))
            files.append((src, dst))
        summary = {"songs": len(songs), "license_requests": len(requests),
                   "license_orders": len(orders), "processed_stripe_events": len(events),
                   "executed": execute}
        # Validate destination credentials, table layout and ID conflicts before copying.
        with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn:
            if execute:
                for statement in SCHEMA:
                    conn.execute(statement)
            for table, rows in data.items():
                if not rows:
                    continue
                if not execute:
                    exists = conn.execute(
                        "SELECT to_regclass(%s) AS table_name", ("public." + table,)
                    ).fetchone()["table_name"]
                    if not exists:
                        continue
                for row in rows:
                    existing = conn.execute(
                        "SELECT * FROM " + table + " WHERE id=%s", (row["id"],)
                    ).fetchone()
                    if existing and any(existing.get(k) != v for k, v in row.items()):
                        raise ValueError("Conflicting PostgreSQL record: " + table + "/" + row["id"])
            if not execute:
                return summary
            for src, dst in files:
                copy_verified(src, dst)
            for table, rows in data.items():
                for row in rows:
                    columns = list(row)
                    names = ",".join(columns)
                    placeholders = ",".join(["%s"] * len(columns))
                    conn.execute(
                        "INSERT INTO " + table + " (" + names + ") VALUES (" + placeholders +
                        ") ON CONFLICT (id) DO NOTHING", tuple(row[k] for k in columns))
            # Transaction commits on successful context exit.
        with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn:
            for table, rows in data.items():
                for row in rows:
                    actual = conn.execute("SELECT * FROM " + table + " WHERE id=%s",
                                          (row["id"],)).fetchone()
                    if not actual or any(actual.get(k) != v for k, v in row.items()):
                        raise ValueError("Post-import metadata verification failed: " + table)
        for src, dst in files:
            if digest(src) != digest(dst):
                raise ValueError("Post-import audio checksum mismatch: " + str(dst))
        return summary

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--dest-root", type=Path, required=True)
    parser.add_argument("--source-db", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    source = args.source_root.expanduser()
    dest = args.dest_root.expanduser()
    source_db = (args.source_db or source / "metadata/files.sqlite3").expanduser()
    print(json.dumps(migrate(source, dest, source_db, args.execute), indent=2))

if __name__ == "__main__":
    main()
