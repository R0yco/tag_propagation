import sqlite3
from dataclasses import dataclass
from enum import StrEnum

from rules import Rule, RelationType


class TagStatus(StrEnum):
    INSERTED = "inserted"
    SKIPPED = "skipped"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class TagAction:
    rule_label: str
    src_type: str
    src_name: str
    dst_type: str
    dst_name: str
    key: str
    value: str
    status: TagStatus


def propagate(conn: sqlite3.Connection, rules: list[Rule]) -> list[TagAction]:
    actions: list[TagAction] = []

    for rule in rules:
        if rule.relation.type == RelationType.ONE_TO_MANY:
            matches = _find_one_to_many(conn, rule)
        else:
            matches = _find_many_to_many(conn, rule)

        for value, dst_id, dst_type, src_name, dst_name in matches:
            status = _upsert_tag(conn, dst_id, dst_type, rule.tag, value, rule.label)
            actions.append(
                TagAction(
                    rule_label=rule.label,
                    src_type=rule.source_entity,
                    src_name=src_name,
                    dst_type=dst_type,
                    dst_name=dst_name,
                    key=rule.tag,
                    value=value,
                    status=status,
                )
            )

    conn.commit()
    return actions


def _find_one_to_many(
    conn: sqlite3.Connection, rule: Rule
) -> list[tuple[str, int, str, str, str]]:
    return conn.execute(
        f"""
        SELECT src_tag.value, dst.id, dst.type, src.name, dst.name
        FROM entities src
        JOIN entity_tags src_tag ON src_tag.entity_id = src.id AND src_tag.key = :tag
        JOIN entities dst        ON dst.id = src.{rule.relation.field} AND dst.type = :destination_entity
        WHERE src.type = :source_entity
    """,
        {
            "tag": rule.tag,
            "source_entity": rule.source_entity,
            "destination_entity": rule.destination_entity,
        },
    ).fetchall()


def _find_many_to_many(
    conn: sqlite3.Connection, rule: Rule
) -> list[tuple[str, int, str, str, str]]:
    return conn.execute(
        """
        SELECT src_tag.value, dst.id, dst.type, src.name, dst.name
        FROM entities src
        JOIN entity_tags src_tag   ON src_tag.entity_id = src.id AND src_tag.key = :tag
        JOIN entity_connections ec ON ec.source_id = src.id
        JOIN entities dst          ON dst.id = ec.destination_id AND dst.type = :destination_entity
        WHERE src.type = :source_entity
    """,
        {
            "tag": rule.tag,
            "source_entity": rule.source_entity,
            "destination_entity": rule.destination_entity,
        },
    ).fetchall()


def _upsert_tag(
    conn: sqlite3.Connection,
    dst_id: int,
    dst_type: str,
    key: str,
    value: str,
    rule_label: str,
) -> TagStatus:
    existing = conn.execute(
        "SELECT value FROM entity_tags WHERE entity_id = :entity_id AND key = :key",
        {"entity_id": dst_id, "key": key},
    ).fetchone()

    if existing is None:
        conn.execute(
            """INSERT INTO entity_tags (entity_id, entity_type, key, value)
               VALUES (:entity_id, :entity_type, :key, :value)""",
            {"entity_id": dst_id, "entity_type": dst_type, "key": key, "value": value},
        )
        return TagStatus.INSERTED
    elif existing[0] != value:
        conn.execute(
            """INSERT OR IGNORE INTO tag_conflicts
               (entity_id, key, existing_value, attempted_value, rule)
               VALUES (:entity_id, :key, :existing_value, :attempted_value, :rule)""",
            {
                "entity_id": dst_id,
                "key": key,
                "existing_value": existing[0],
                "attempted_value": value,
                "rule": rule_label,
            },
        )
        return TagStatus.CONFLICT
    else:
        return TagStatus.SKIPPED
