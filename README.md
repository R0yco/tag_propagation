# Miggo Tag Propagation

Rule-driven propagation of security/context tags across an entity graph stored in SQLite.

## Run

```sh
uv run main.py -f rules.json -d database.sqlite --init        # first run
uv run main.py -f rules.json -d database.sqlite               # subsequent
uv run main.py -f rules.json -d database.sqlite --verbose     # show table
uv run pytest                                                 # tests
```

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

## Design choices

| Decision | Rejected | Why |
|---|---|---|
| One-hop propagation per rule | Recursive/transitive | Brief's scenario is one-hop; YAGNI |
| Raw `sqlite3` with `:name` params | SQLAlchemy | 3 queries, 4 tables — ORM is overkill |
| Pydantic for `Rule`, dataclass for `TagAction` | Pydantic everywhere | Pydantic at trust boundaries (JSON), not for internal objects |
| `field` whitelist (`{"parent"}`) before SQL interpolation | F-string the value | Column names can't be parameterized; whitelist makes interpolation safe |
| `--init` flag | Silent bootstrap on missing DB | Implicit creation hides bugs (wrong path, deleted file) |
| `tag_conflicts` UNIQUE on full tuple + `INSERT OR IGNORE` | Plain table | Re-runs don't duplicate conflict rows |
| `StrEnum` for `TagStatus` | Magic strings or plain `Enum` | Namespace safety + transparent string behavior |
| `tabulate` for verbose output | Manual width-aligned printing | Library output is cleaner; manual alignment is bug-prone |
| `Status` column with words | `[+]/[~]/[!]` markers | Self-documenting; no legend needed |
| 4 tests, one per requirement | Coverage chasing | Pydantic, schema PKs, SQLite mechanics aren't our code |

## Idempotency

Three layers:

1. `entity_tags` PK on `(entity_id, key)` — schema enforces no duplicates.
2. `_upsert_tag` checks before inserting: same value → skip, different → conflict.
3. `tag_conflicts` UNIQUE + `INSERT OR IGNORE` — conflict rows don't duplicate either.

## Not implemented

- **Transitive propagation.** A tag walking multiple hops (A → B → C) would need a recursive CTE within a rule, or a fixed-point loop across rules. The brief doesn't ask for it.
- **Multiple `field` values.** Only `parent` is whitelisted. Adding a column means adding it to `VALID_ENTITY_FIELDS`.
- **Logging beyond stdout.** A real service would emit structured logs; for a CLI, `print` is fine.
