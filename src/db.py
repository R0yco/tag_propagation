import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def bootstrap_database(db_path: Path) -> None:
    """Create db_path and seed it by executing schema.sql. Used by tests."""
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"schema.sql not found at {SCHEMA_PATH}")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text())


def open_database(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
