import sqlite3
from dataclasses import dataclass

from rules import Rule, RelationType


@dataclass
class TagAction:
    rule_label: str
    src_type: str
    src_name: str
    dst_type: str
    dst_name: str
    key: str
    value: str
    status: str  # "inserted" | "skipped" | "conflict"


def propagate(conn: sqlite3.Connection, rules: list[Rule]) -> list[TagAction]:
    actions: list[TagAction] = []

    for rule in rules:
        if rule.relation.type == RelationType.ONE_TO_MANY:
            pairs = _find_one_to_many(conn, rule)
        else:
            pairs = _find_many_to_many(conn, rule)

        for (value, dst_id, dst_type, src_name, dst_name) in pairs:
            status = _upsert_tag(conn, dst_id, dst_type, rule.tag, value, rule.label)
            actions.append(TagAction(
                rule_label=rule.label,
                src_type=rule.source_entity,
                src_name=src_name,
                dst_type=dst_type,
                dst_name=dst_name,
                key=rule.tag,
                value=value,
                status=status,
            ))

    conn.commit()
    return actions


def _find_one_to_many(conn: sqlite3.Connection, rule: Rule) -> list[tuple]:
    return conn.execute(f"""
        SELECT src_tag.value, dst.id, dst.type, src.name, dst.name
        FROM entities src
        JOIN entity_tags src_tag ON src_tag.entity_id = src.id AND src_tag.key = :tag
        JOIN entities dst        ON dst.id = src.{rule.relation.field} AND dst.type = :destination_entity
        WHERE src.type = :source_entity
    """, {
        "tag": rule.tag,
        "source_entity": rule.source_entity,
        "destination_entity": rule.destination_entity,
    }).fetchall()


def _find_many_to_many(conn: sqlite3.Connection, rule: Rule) -> list[tuple]:
    return conn.execute("""
        SELECT src_tag.value, dst.id, dst.type, src.name, dst.name
        FROM entities src
        JOIN entity_tags src_tag   ON src_tag.entity_id = src.id AND src_tag.key = :tag
        JOIN entity_connections ec ON ec.source_id = src.id
        JOIN entities dst          ON dst.id = ec.destination_id AND dst.type = :destination_entity
        WHERE src.type = :source_entity
    """, {
        "tag": rule.tag,
        "source_entity": rule.source_entity,
        "destination_entity": rule.destination_entity,
    }).fetchall()


def _upsert_tag(
    conn: sqlite3.Connection,
    dst_id: int,
    dst_type: str,
    key: str,
    value: str,
    rule_label: str,
) -> str:
    row = conn.execute(
        "SELECT value FROM entity_tags WHERE entity_id = ? AND key = ?",
        (dst_id, key),
    ).fetchone()

    if row is None:
        conn.execute(
            "INSERT INTO entity_tags (entity_id, entity_type, key, value) VALUES (?, ?, ?, ?)",
            (dst_id, dst_type, key, value),
        )
        return "inserted"
    elif row[0] != value:
        conn.execute(
            """INSERT OR IGNORE INTO tag_conflicts
               (entity_id, key, existing_value, attempted_value, rule)
               VALUES (?, ?, ?, ?, ?)""",
            (dst_id, key, row[0], value, rule_label),
        )
        return "conflict"
    else:
        return "skipped"
