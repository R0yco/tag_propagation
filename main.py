# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Tag propagation system.

Usage:
    uv run main.py -f rules.json -d database.sqlite

The database is treated as an input — it must exist before running. To create
a fresh seeded database for testing, see test_main.py.
"""

import argparse
import sys
from pathlib import Path

from db import open_database
from propagate import propagate
from rules import load_rules


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply tag propagation rules to a SQLite database.")
    parser.add_argument("-f", "--rules", required=True, type=Path, help="Path to rules JSON file.")
    parser.add_argument("-d", "--database", required=True, type=Path, help="Path to SQLite database file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.database.exists():
        sys.exit(f"Database not found: {args.database}")

    try:
        rules = load_rules(args.rules)
    except ValueError as e:
        sys.exit(f"Rules error: {e}")

    conn = open_database(args.database)
    try:
        propagate(conn, rules)
    finally:
        conn.close()

    print(f"Applied {len(rules)} rule(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
