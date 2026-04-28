# Miggo Tag Propagation

CLI that propagates tags across an entity graph in SQLite according to rules in JSON.

Each rule names a `tag`, a source entity type, a destination entity type, and a relation (`one-to-many` via a column on the source, or `many-to-many` via the `entity_connections` table). For every source entity that has the tag, the script copies the tag to all matching destinations.

## Usage

```sh
uv run src/main.py -f rules.json -d database.sqlite --init        # first run (bootstraps the DB)
uv run src/main.py -f rules.json -d database.sqlite               # subsequent runs
uv run src/main.py -f rules.json -d database.sqlite --verbose     # show the propagation as a table
uv run pytest                                                 # run the test suite
```

The database is read and written in place. Re-running is safe — nothing duplicates. Mismatches between an existing tag and an inferred one are recorded in `tag_conflicts` rather than overwritten.

## Files

| File | Purpose |
|---|---|
| `rules.json` | Example rules from the brief |
| `src/schema.sql` | DDL + seed data |
| `src/db.py` | `bootstrap_database`, `open_database` |
| `src/rules.py` | Pydantic `Rule`/`Relation` models, `load_rules` |
| `src/propagate.py` | Propagation engine, `TagAction`, `TagStatus` |
| `src/main.py` | CLI |
| `tests/conftest.py` | Shared `db_path` pytest fixture |
| `tests/test_propagate.py` | Test suite (see below) |

## design choices
### Idempotency

- `entity_tags` PK on `(entity_id, key)` — duplicate rows impossible.
- `_upsert_tag` reads the existing value before writing, so it can return `SKIPPED` or `CONFLICT` instead of the PK silently squashing the insert.
- `tag_conflicts` UNIQUE + `INSERT OR IGNORE` — the conflict log is a set, not a list.

### Pydantic for rule parsing

`rules.json` is validated by Pydantic — types, required fields, and an allowlist for `field` so it's safe to interpolate into SQL. Internal types (`TagAction`, `TagStatus`) skip Pydantic; they're not parsed from input.

### on not using an ORM for SQL
I chose using sqlite library directly because of the small scope, instead of opting for an ORM like sqlalchemy or prisma. I judged that the scope here is too small to demand it, and the result came out pretty clean with raw sql.

## Tests

Run with `uv run pytest`. Five tests:

- **test_produces_expected_tags** — runs the brief's test scenario and checks the resulting tags match.
- **test_is_idempotent** — runs propagation twice, asserts the second run changes nothing.
- **test_records_conflict** — pre-plants a different value on a destination, asserts the conflict is logged and the existing value is preserved.
- **test_skip_does_not_create_conflict** — pre-plants the same value on a destination, asserts nothing is logged.
- **test_multiple_sources_different_values_records_conflict** — two sources try to set different values on the same destination; asserts one wins and the other is logged as a conflict.

## Not implemented

- **Transitive propagation.** Each rule traverses one edge. If a propagated tag should keep flowing further along the graph, the engine would need a separate iteration mechanism — not added because the brief's scenario stops at one hop.
- **Bulk SQL upsert.** Each destination is checked and written individually. For large graphs this would be slower than a single set-based statement per rule, at the cost of losing the per-action status used by the verbose output.
- **Logging beyond stdout.** A real service would emit structured logs; for a CLI, `print` is fine.

