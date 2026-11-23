"""Optional PostgreSQL metadata connection compatible with existing storage queries."""
import os
import re
from contextlib import contextmanager

SCHEMA = (
"""CREATE TABLE IF NOT EXISTS generated_files (
id TEXT PRIMARY KEY, category TEXT NOT NULL, name TEXT NOT NULL,
storage_key TEXT NOT NULL, size BIGINT NOT NULL, mime TEXT NOT NULL,
created_at TEXT NOT NULL, song_title TEXT, artwork_svg TEXT,
license_status TEXT NOT NULL DEFAULT 'not_licensed')""",
"""CREATE TABLE IF NOT EXISTS commercial_license_requests (
id TEXT PRIMARY KEY, file_id TEXT NOT NULL, contact_email TEXT NOT NULL,
status TEXT NOT NULL, created_at TEXT NOT NULL)""",
"""CREATE TABLE IF NOT EXISTS commercial_license_orders (
id TEXT PRIMARY KEY, file_id TEXT NOT NULL, request_id TEXT NOT NULL,
stripe_session TEXT UNIQUE, stripe_payment_intent TEXT,
amount BIGINT NOT NULL, currency TEXT NOT NULL,
status TEXT NOT NULL, created_at TEXT NOT NULL, paid_at TEXT,
license_id TEXT UNIQUE, issued_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS stripe_processed_events (
id TEXT PRIMARY KEY, processed_at TEXT NOT NULL)""",
)

class PGConnection:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=None):
        # SQL text is exclusively from trusted application constants.
        if isinstance(params, dict):
            sql = re.sub(r":([a-zA-Z_][a-zA-Z_0-9]*)", r"%(\1)s", sql)
        else:
            sql = sql.replace("?", "%s")
        return self.conn.execute(sql, params if params is not None else ())

    def __enter__(self):
        self.conn.__enter__()
        return self

    def __exit__(self, *args):
        return self.conn.__exit__(*args)

    def close(self):
        self.conn.close()

def connect():
    import psycopg
    from psycopg.rows import dict_row
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required when STORAGE_METADATA_BACKEND=postgres")
    conn = psycopg.connect(url, row_factory=dict_row)
    try:
        for statement in SCHEMA:
            conn.execute(statement)
        conn.commit()
        return PGConnection(conn)
    except Exception:
        conn.close()
        raise
