from pathlib import Path

import pytest

from db import open_database
from propagate import propagate
from rules import Relation, RelationType, Rule

RULES = [
    Rule(
        tag="internet-facing",
        source_entity="ENDPOINT",
        destination_entity="SERVICE",
        relation=Relation(type=RelationType.ONE_TO_MANY, field="parent"),
    ),
    Rule(
        tag="data-sensitivity",
        source_entity="DATABASE",
        destination_entity="SERVICE",
        relation=Relation(type=RelationType.MANY_TO_MANY),
    ),
]


@pytest.fixture
def propagated_db(db_path: Path) -> Path:
    conn = open_database(db_path)
    try:
        propagate(conn, RULES)
    finally:
        conn.close()
    return db_path


def test_produces_expected_tags(propagated_db: Path):
    conn = open_database(propagated_db)
    try:
        rows = conn.execute(
            "SELECT entity_id, key, value FROM entity_tags ORDER BY entity_id, key;"
        ).fetchall()
    finally:
        conn.close()

    assert rows == [
        (1, "internet-facing", "TRUE"),
        (2, "data-sensitivity", "PHI"),
        (2, "internet-facing", "TRUE"),
        (3, "data-sensitivity", "PHI"),
        (4, "data-sensitivity", "PHI"),
    ]


def test_is_idempotent(propagated_db: Path):
    conn = open_database(propagated_db)
    try:
        propagate(conn, RULES)
        (count,) = conn.execute("SELECT COUNT(*) FROM entity_tags;").fetchone()
    finally:
        conn.close()

    assert count == 5


def test_records_conflict(db_path: Path):
    conn = open_database(db_path)
    try:
        conn.execute(
            "INSERT INTO entity_tags (entity_id, entity_type, key, value) "
            "VALUES (2, 'SERVICE', 'internet-facing', 'FALSE')"
        )
        conn.commit()
        propagate(conn, [RULES[0]])
        rows = conn.execute(
            "SELECT entity_id, key, existing_value, attempted_value, rule FROM tag_conflicts;"
        ).fetchall()
        tag = conn.execute(
            "SELECT value FROM entity_tags WHERE entity_id=2 AND key='internet-facing';"
        ).fetchone()
    finally:
        conn.close()

    assert rows == [
        (2, "internet-facing", "FALSE", "TRUE", "ENDPOINT:internet-facing->SERVICE")
    ]
    assert tag == ("FALSE",)


def test_skip_does_not_create_conflict(db_path: Path):
    conn = open_database(db_path)
    try:
        conn.execute(
            "INSERT INTO entity_tags (entity_id, entity_type, key, value) "
            "VALUES (2, 'SERVICE', 'internet-facing', 'TRUE')"
        )
        conn.commit()
        propagate(conn, [RULES[0]])
        (count,) = conn.execute("SELECT COUNT(*) FROM tag_conflicts;").fetchone()
    finally:
        conn.close()

    assert count == 0


def test_multiple_sources_different_values_records_conflict(db_path: Path):
    conn = open_database(db_path)
    try:
        # Add a second database connected to service 2 with a different sensitivity value.
        # Service 2 receives data-sensitivity from both pg-healthcare (PHI) and pg-billing (PII).
        # Whichever propagates first wins; the other becomes a conflict.
        conn.execute(
            "INSERT INTO entities (id, type, name, parent) "
            "VALUES (5, 'DATABASE', 'pg-billing', NULL)"
        )
        conn.execute(
            "INSERT INTO entity_connections (source_id, destination_id) VALUES (5, 2)"
        )
        conn.execute(
            "INSERT INTO entity_tags (entity_id, entity_type, key, value) "
            "VALUES (5, 'DATABASE', 'data-sensitivity', 'PII')"
        )
        conn.commit()

        propagate(conn, [RULES[1]])

        service_tag = conn.execute(
            "SELECT value FROM entity_tags WHERE entity_id=2 AND key='data-sensitivity'"
        ).fetchone()
        conflicts = conn.execute(
            "SELECT existing_value, attempted_value FROM tag_conflicts WHERE entity_id=2"
        ).fetchall()
    finally:
        conn.close()

    assert service_tag[0] in {"PHI", "PII"}
    assert len(conflicts) == 1
    assert set(conflicts[0]) == {"PHI", "PII"}
