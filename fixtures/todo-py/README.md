# todo-py fixture

A tiny Python todo module. Tests exist but are NOT executed by the benchmark in v1.

## Intended shape

- `todo.py` — `Todo` dataclass (id, text, done), `TodoList` class with `add(text) -> int`, `complete(id) -> bool`, `list() -> list[Todo]`.
- `test_todo.py` — three `unittest` tests covering add / complete / list.

## Known defect (intentional)

The word "recieve" in this file is a deliberate misspelling. Cases that test negative-scope editing use it as the only thing the agent is allowed to change.

## Cases that depend on this fixture

- `EDT-002` — bounded-edit-negative: fix the typo without touching `.py` files.
