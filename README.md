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
| `tests/test_propagate.py` | One test per behavior in the brief |

## design choices
### Idempotency

`entity_tags` is keyed on `(entity_id, key)`. Duplicate tag rows can't exist.

`_upsert_tag` SELECTs the existing value before writing, returning `SKIPPED` when it matches and `CONFLICT` when it doesn't. Without the read, a second insert with a different value would be silently squashed by the PK, and we'd never know to log it as a conflict.

`tag_conflicts` is keyed on the full `(entity_id, key, existing_value, attempted_value, rule)` tuple with `INSERT OR IGNORE`. The conflict log doesn't grow when the same conflict is detected twice.

### on not using an ORM for SQL
I chose using sqlite library directly because of the small scope, instead of opting for an ORM like sqlalchemy or prisma. I judged that the scope here is too small to demand it, and the result came out pretty clean with raw sql.

## Not implemented

- **Transitive propagation.** Each rule traverses one edge. If a propagated tag should keep flowing further along the graph, the engine would need a separate iteration mechanism — not added because the brief's scenario stops at one hop.
- **Bulk SQL upsert.** Each destination is checked and written individually. For large graphs this would be slower than a single set-based statement per rule, at the cost of losing the per-action status used by the verbose output.
- **Logging beyond stdout.** A real service would emit structured logs; for a CLI, `print` is fine.

