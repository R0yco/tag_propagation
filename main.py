"""Tag propagation system.

Usage:
    uv run main.py -f rules.json -d database.sqlite
    uv run main.py -f rules.json -d database.sqlite --init   # create and seed on first run
"""

import argparse
import sys
from pathlib import Path

from tabulate import tabulate

from db import bootstrap_database, open_database
from propagate import TagAction, TagStatus, propagate
from rules import load_rules


def _print_results(actions: list[TagAction]) -> None:
    rows = [
        (
            a.status,
            f"{a.src_type}: {a.src_name}",
            f"{a.key}={a.value}",
            f"{a.dst_type}: {a.dst_name}",
        )
        for a in actions
    ]
    print(
        tabulate(
            rows,
            headers=("Status", "Source", "Tag", "Destination"),
            tablefmt="rounded_outline",
        )
    )

    print()
    inserted = sum(1 for a in actions if a.status == TagStatus.INSERTED)
    skipped = sum(1 for a in actions if a.status == TagStatus.SKIPPED)
    conflicts = sum(1 for a in actions if a.status == TagStatus.CONFLICT)
    print(f"{inserted} propagated · {skipped} skipped · {conflicts} conflicts")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply tag propagation rules to a SQLite database."
    )
    parser.add_argument(
        "-f", "--rules", required=True, type=Path, help="Path to rules JSON file."
    )
    parser.add_argument(
        "-d",
        "--database",
        required=True,
        type=Path,
        help="Path to SQLite database file.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show per-tag propagation output."
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Create and seed the database if it does not exist.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.database.exists():
        if not args.init:
            sys.exit(f"Database not found: {args.database} (use --init to create it)")
        bootstrap_database(args.database)
        print(f"Initialized database: {args.database}")

    try:
        rules = load_rules(args.rules)
    except ValueError as e:
        sys.exit(f"Rules error: {e}")

    conn = open_database(args.database)
    try:
        actions = propagate(conn, rules)
    finally:
        conn.close()

    if args.verbose:
        _print_results(actions)
    else:
        inserted = sum(1 for a in actions if a.status == TagStatus.INSERTED)
        skipped = sum(1 for a in actions if a.status == TagStatus.SKIPPED)
        conflicts = sum(1 for a in actions if a.status == TagStatus.CONFLICT)
        print(f"{inserted} propagated · {skipped} skipped · {conflicts} conflicts")

    return 0


if __name__ == "__main__":
    sys.exit(main())
