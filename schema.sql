PRAGMA foreign_keys = ON;

CREATE TABLE entities (
    id     INTEGER PRIMARY KEY,
    type   TEXT    NOT NULL,
    name   TEXT    NOT NULL,
    parent INTEGER REFERENCES entities(id)
);

CREATE TABLE entity_connections (
    source_id      INTEGER NOT NULL REFERENCES entities(id),
    destination_id INTEGER NOT NULL REFERENCES entities(id),
    PRIMARY KEY (source_id, destination_id)
);

CREATE TABLE entity_tags (
    entity_id   INTEGER NOT NULL REFERENCES entities(id),
    entity_type TEXT    NOT NULL,
    key         TEXT    NOT NULL,
    value       TEXT    NOT NULL,
    PRIMARY KEY (entity_id, key)
);

CREATE TABLE tag_conflicts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id       INTEGER NOT NULL REFERENCES entities(id),
    key             TEXT    NOT NULL,
    existing_value  TEXT    NOT NULL,
    attempted_value TEXT    NOT NULL,
    rule            TEXT    NOT NULL,
    UNIQUE (entity_id, key, existing_value, attempted_value, rule)
);

INSERT INTO entities (id, type, name, parent) VALUES
    (2, 'SERVICE',  'user-management',       NULL),
    (3, 'DATABASE', 'pg-healthcare',         NULL),
    (1, 'ENDPOINT', '/api/v2/users/:id',     2),
    (4, 'SERVICE',  'documentation-website', 2);

INSERT INTO entity_connections (source_id, destination_id) VALUES
    (3, 2),
    (3, 4);

INSERT INTO entity_tags (entity_id, entity_type, key, value) VALUES
    (1, 'ENDPOINT', 'internet-facing',  'TRUE'),
    (3, 'DATABASE', 'data-sensitivity', 'PHI');
