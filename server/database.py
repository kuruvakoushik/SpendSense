"""SQLite connection helpers with foreign-key enforcement."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import current_app, g

from server.config import resolve_database_path


def get_db_path() -> Path:
    return resolve_database_path(current_app.config["DATABASE_PATH"])


def connect(database_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(
        str(database_path),
        detect_types=sqlite3.PARSE_DECLTYPES,
        timeout=10,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(get_db_path())
    return g.db


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(database_path: str | Path | None = None) -> None:
    """Create tables from schema.sql if they do not already exist."""
    path = Path(database_path) if database_path else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    schema_file = Path(__file__).resolve().parent / "schema.sql"
    schema = schema_file.read_text(encoding="utf-8")
    conn = connect(path)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()
