"""Safety checks for the local-song transfer tool."""
import importlib.util
import sqlite3
from pathlib import Path

import pytest


def load_migrator():
    path = Path(__file__).resolve().parents[2] / "tools" / "migrate_music_data.py"
    spec = importlib.util.spec_from_file_location("migrate_music_data", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_data_migration_dry_run_and_idempotent_copy(tmp_path):
    module = load_migrator()
    sr = tmp_path / "source"
    dr = tmp_path / "destination"
    key = "full_song/0123456789abcdef0123456789abcdef/a.wav"
    path = sr / key
    path.parent.mkdir(parents=True)
    path.write_bytes(b"test-WAV-payload")
    db = sr / "metadata" / "files.sqlite3"
    db.parent.mkdir(parents=True)
    with sqlite3.connect(db) as conn:
        conn.execute(module.SCHEMAS["generated_files"])
        conn.execute("""INSERT INTO generated_files
            (id,category,name,storage_key,size,mime,created_at,license_status)
            VALUES (?,?,?,?,?,?,?,?)""",
            ("0123456789abcdef0123456789abcdef", "full_song", "a.wav", key,
             len(path.read_bytes()), "audio/wav", "2026-01-01", "not_licensed"))
    dest_db = dr / "metadata" / "files.sqlite3"
    options = (sr, dr, db, dest_db, sr / "full_song_projects", dr / "full_song_projects")
    dry = module.migrate(*options)
    assert dry["songs"] == 1 and dry["executed"] is False
    assert not dr.exists()
    copied = module.migrate(*options, execute=True)
    assert copied["songs"] == 1
    assert (dr / key).read_bytes() == path.read_bytes()
    module.migrate(*options, execute=True)
    with sqlite3.connect(dest_db) as conn:
        assert conn.execute("SELECT count(*) FROM generated_files").fetchone()[0] == 1
    (dr / key).write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="conflicts"):
        module.migrate(*options, execute=True)


def test_migration_does_not_escape_root(tmp_path):
    module = load_migrator()
    with pytest.raises(ValueError, match="Unsafe"):
        module.valid_path(tmp_path, "../outside")
