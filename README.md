# Miggo Tag Propagation

CLI that propagates tags across an entity graph in SQLite according to rules in JSON.

Each rule names a `tag`, a source entity type, a destination entity type, and a relation (`one-to-many` via a column on the source, or `many-to-many` via the `entity_connections` table). For every source entity that has the tag, the script copies the tag to all matching destinations.

## Usage

```sh
uv run main.py -f rules.json -d database.sqlite --init        # first run (bootstraps the DB)
uv run main.py -f rules.json -d database.sqlite               # subsequent runs
uv run main.py -f rules.json -d database.sqlite --verbose     # show the propagation as a table
uv run pytest                                                 # run the test suite
```

The database is read and written in place. Re-running is safe — nothing duplicates. Mismatches between an existing tag and an inferred one are recorded in `tag_conflicts` rather than overwritten.

## Files

| File | Purpose |
|---|---|
| `schema.sql` | DDL + seed data |
| `rules.json` | Example rules from the brief |
| `db.py` | `bootstrap_database`, `open_database` |
| `rules.py` | Pydantic `Rule`/`Relation` models, `load_rules` |
| `propagate.py` | Propagation engine, `TagAction`, `TagStatus` |
| `main.py` | CLI |
| `conftest.py` | Shared `db_path` pytest fixture |
| `test_propagate.py` | One test per behavior in the brief |

## Not implemented

- **Transitive propagation.** A tag walking multiple hops (A → B → C) would need a recursive CTE within a rule, or a fixed-point loop across rules. The brief doesn't ask for it.
- **Bulk SQL upsert.** Each rule fires `1 + 2N` queries (one find, then probe + write per destination). For thousands of entities a set-based `INSERT … ON CONFLICT` per rule would be faster, at the cost of harder per-action status reconstruction.
- **Logging beyond stdout.** A real service would emit structured logs; for a CLI, `print` is fine.
