# playground-agent-benchmark v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the validator-first v1 slice of `playground-agent-benchmark`: 4 cases, 2 fixtures, 5 validators, 3 CLI scripts (plus 1 stub), and the shared utility package they need — all Python 3 stdlib, no harness.

**Architecture:** Three Python packages divide responsibility cleanly. `validators/` holds one-file-per-check modules, each exposing `validate(case, workdir) -> dict`. `bench/` houses shared helpers used by ≥2 callers: case loading + schema check, allowed-path matching, baseline capture + diff, run-dir/manifest/result I/O. `scripts/` holds thin `argparse`-driven CLI entry points (`new_run`, `validate`, `summarize`, stub `compare`) that orchestrate the loop: **scaffold run → operator fills `workdir/` manually → validate → summarize**. No script invokes an agent.

`bench/` is a concrete shared package, not a speculative `core/`/`lib/` — it exists only because specific helpers (`paths.matches`, `baseline.walk`, case loader, run-dir layout) are reused by two scripts plus the `allowed_paths_check` validator. Every function in `bench/` has at least two real callers at merge time.

**Tech Stack:** Python 3.10+, stdlib only (`json`, `argparse`, `pathlib`, `hashlib`, `fnmatch`, `shutil`, `datetime`, `difflib`, `platform`, `unittest`). No third-party dependencies.

**Run/result design (2026-04-21 revision):** Every run captures enough metadata to support later cross-model comparison — `agent.{frontend, model, provider, local_vs_cloud, runtime_base_url, notes}`, auto-collected `environment.{host, os, python, arch}` and best-effort `hardware.{cpu_cores, memory_gb, gpu}`, and per-case artifact references (`case_snapshot`, `workdir`, `changes_json`, `changes_diff`, `transcript`). `validate.py` writes `changes.json` (machine-readable diff summary) and `changes.diff` (unified diff vs fixture source) next to `result.json` so retrospective analysis works from the run directory alone. See spec §9 for the authoritative shape.

**Spec reference:** `docs/plans/v1-design.md`. The load-bearing sections are §4 (case format), §7 (validators), §8 (`allowed_paths_check`), §9 (run/result format), §10 (script surface).

**Branch:** `feat/v1-benchmark-core`.

**Test strategy:** `unittest` from stdlib. Each module under `bench/` and `validators/` gets a sibling `tests/test_<module>.py`. Scripts are tested by invoking them as subprocesses (`python3 -m scripts.new_run …`) against temp directories. Run the full suite with `python3 -m unittest discover -s tests -v`.

**Repo state at plan start:** bootstrap. Only `README.md`, `AGENTS.md`, `CLAUDE.md`, `.gitignore`, `docs/plans/v1-design.md`, and `.gitkeep`-ed empty `artifacts/`, `reports/`, `runs/`.

---

### Task 1: Bootstrap scaffold, branch, and package layout

**Files:**
- Create: `bench/__init__.py`
- Create: `validators/__init__.py`
- Create: `tests/__init__.py`
- Create: `cases/smoke/.gitkeep`
- Create: `cases/structured/.gitkeep`
- Create: `cases/bounded-edit/.gitkeep`
- Create: `fixtures/.gitkeep`
- Create: `schemas/.gitkeep`
- Create: `scripts/__init__.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create and switch to the feature branch**

```bash
git checkout -b feat/v1-benchmark-core
```

- [ ] **Step 2: Create empty package directories with `__init__.py`**

Create each of these as an empty file:
- `bench/__init__.py`
- `validators/__init__.py`
- `tests/__init__.py`
- `scripts/__init__.py`

And empty `.gitkeep` in each of: `cases/smoke/`, `cases/structured/`, `cases/bounded-edit/`, `fixtures/`, `schemas/`.

- [ ] **Step 3: Extend `.gitignore` for test artifacts**

Append to `.gitignore`:

```
# Unit-test scratch
/tmp_test_*/
.coverage
```

- [ ] **Step 4: Verify the test harness discovers zero tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: "Ran 0 tests in 0.000s". Exit code is 5 on Python ≥ 3.12 ("NO TESTS RAN") and 0 on older Pythons; either is acceptable for this sanity check. From Task 2 onward, tests exist and exit code is 0 on success.

- [ ] **Step 5: Commit**

```bash
git add bench/ validators/ tests/ scripts/ cases/ fixtures/ schemas/ .gitignore
git commit -m "chore: scaffold package layout for v1 benchmark core"
```

---

### Task 2: JSON schemas for case, manifest, and result

**Files:**
- Create: `schemas/case.schema.json`
- Create: `schemas/run-manifest.schema.json`
- Create: `schemas/case-result.schema.json`
- Test: `tests/test_schemas.py`

Schemas are hand-rolled JSON documents. They are not consumed via a third-party validator; `bench.loader` will validate against them in Task 3.

- [ ] **Step 1: Write a failing test that each schema file is valid JSON and has required top-level keys**

Create `tests/test_schemas.py`:

```python
import json
import unittest
from pathlib import Path

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"

class TestSchemas(unittest.TestCase):
    def test_case_schema_loads(self):
        data = json.loads((SCHEMAS_DIR / "case.schema.json").read_text())
        self.assertEqual(data["$id"], "case.schema.json")
        self.assertEqual(data["schema_version"], 1)
        self.assertIn("id", data["required"])
        self.assertIn("validator", data["required"])

    def test_manifest_schema_loads(self):
        data = json.loads((SCHEMAS_DIR / "run-manifest.schema.json").read_text())
        self.assertEqual(data["$id"], "run-manifest.schema.json")
        self.assertIn("run_id", data["required"])

    def test_result_schema_loads(self):
        data = json.loads((SCHEMAS_DIR / "case-result.schema.json").read_text())
        self.assertEqual(data["$id"], "case-result.schema.json")
        self.assertIn("case_id", data["required"])
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `python3 -m unittest tests.test_schemas -v`
Expected: FAIL — FileNotFoundError for each schema.

- [ ] **Step 3: Create `schemas/case.schema.json`**

```json
{
  "$id": "case.schema.json",
  "schema_version": 1,
  "type": "object",
  "required": [
    "schema_version", "id", "title", "category", "difficulty",
    "mode", "tags", "fixture", "allowed_paths", "prompt",
    "expected_output", "validator"
  ],
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "id": { "type": "string", "pattern": "^[A-Z]+-\\d{3}$" },
    "title": { "type": "string" },
    "category": { "type": "string" },
    "difficulty": { "type": "string", "enum": ["trivial", "easy", "medium"] },
    "mode": { "type": "string", "enum": ["read-only", "plan-only", "write"] },
    "tags": { "type": "array", "items": { "type": "string" } },
    "fixture": { "type": ["string", "null"] },
    "allow_deletions": { "type": "boolean" },
    "allowed_paths": { "type": "array", "items": { "type": "string" } },
    "prompt": { "type": "string" },
    "expected_output": {
      "type": "object",
      "required": ["kind"],
      "properties": {
        "kind": { "type": "string", "enum": ["file", "stdout", "json", "none"] },
        "path": { "type": "string" }
      }
    },
    "validator": {
      "type": "object",
      "required": ["type", "args"],
      "properties": {
        "type": { "type": "string" },
        "args": { "type": "object" }
      }
    }
  }
}
```

- [ ] **Step 4: Create `schemas/run-manifest.schema.json`**

```json
{
  "$id": "run-manifest.schema.json",
  "schema_version": 1,
  "type": "object",
  "required": [
    "schema_version", "run_id", "timestamp", "started_at", "finished_at",
    "label", "agent", "suite", "cases",
    "environment", "hardware", "counts", "notes"
  ],
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "run_id":      { "type": "string" },
    "timestamp":   { "type": ["string", "null"] },
    "started_at":  { "type": ["string", "null"] },
    "finished_at": { "type": ["string", "null"] },
    "label":       { "type": "string" },
    "suite":       { "type": ["string", "null"] },
    "cases":       { "type": "array", "items": { "type": "string" } },
    "agent": {
      "type": "object",
      "required": ["frontend", "model", "provider", "local_vs_cloud", "runtime_base_url", "notes"],
      "properties": {
        "frontend":         { "type": "string" },
        "model":            { "type": "string" },
        "provider":         { "type": "string" },
        "local_vs_cloud":   { "type": "string", "enum": ["local", "cloud", "unknown"] },
        "runtime_base_url": { "type": ["string", "null"] },
        "notes":            { "type": "string" }
      }
    },
    "environment": {
      "type": "object",
      "required": ["host", "os", "python", "arch"],
      "properties": {
        "host":   { "type": "string" },
        "os":     { "type": "string" },
        "python": { "type": "string" },
        "arch":   { "type": "string" }
      }
    },
    "hardware": {
      "type": "object",
      "required": ["cpu_cores", "memory_gb", "gpu"],
      "properties": {
        "cpu_cores": { "type": ["integer", "null"] },
        "memory_gb": { "type": ["number",  "null"] },
        "gpu":       { "type": ["string",  "null"] }
      }
    },
    "counts": {
      "type": "object",
      "required": ["total", "passed", "failed", "error"],
      "properties": {
        "total":  { "type": "integer" },
        "passed": { "type": "integer" },
        "failed": { "type": "integer" },
        "error":  { "type": "integer" }
      }
    },
    "notes": { "type": "string" }
  }
}
```

- [ ] **Step 5: Create `schemas/case-result.schema.json`**

```json
{
  "$id": "case-result.schema.json",
  "schema_version": 1,
  "type": "object",
  "required": [
    "schema_version", "case_id", "status", "validators",
    "allowed_paths_check", "duration_ms", "latency_ms",
    "artifacts", "notes"
  ],
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "case_id": { "type": "string" },
    "status": { "type": "string", "enum": ["pass", "fail", "error", "skipped"] },
    "validators": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "ok"],
        "properties": {
          "type":     { "type": "string" },
          "ok":       { "type": "boolean" },
          "detail":   { "type": "string" },
          "observed": {},
          "expected": {}
        }
      }
    },
    "allowed_paths_check": {
      "type": "object",
      "required": ["ok", "violations", "counts"],
      "properties": {
        "ok":         { "type": "boolean" },
        "violations": { "type": "array" },
        "counts":     { "type": "object" }
      }
    },
    "duration_ms": { "type": "integer" },
    "latency_ms":  { "type": ["integer", "null"] },
    "artifacts": {
      "type": "object",
      "required": ["case_snapshot", "workdir", "changes_json", "changes_diff", "transcript"],
      "properties": {
        "case_snapshot": { "type": "string" },
        "workdir":       { "type": "string" },
        "changes_json":  { "type": "string" },
        "changes_diff":  { "type": "string" },
        "transcript":    { "type": "string" }
      }
    },
    "notes": { "type": "string" }
  }
}
```

- [ ] **Step 6: Run the test and confirm it passes**

Run: `python3 -m unittest tests.test_schemas -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add schemas/ tests/test_schemas.py
git commit -m "feat: add case, run-manifest, and case-result JSON schemas"
```

---

### Task 3: Case loader with stdlib schema validation

**Files:**
- Create: `bench/loader.py`
- Test: `tests/test_loader.py`

`bench/loader.py` exposes:
- `load_case(path: Path) -> dict` — reads JSON, validates against `schemas/case.schema.json`, raises `CaseLoadError` on any problem.
- `validate_against_schema(instance, schema) -> list[str]` — returns list of human-readable error messages (empty list = valid). Supports: `type` (single or list), `required`, `enum`, `const`, `pattern` (regex), object `properties`, array `items`.
- Module-level constant `SCHEMA_PATH = Path(...) / "schemas" / "case.schema.json"`.

Only the schema subset used by the v1 schemas is supported — do not implement the full JSON-Schema spec.

- [ ] **Step 1: Write failing tests**

Create `tests/test_loader.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from bench import loader


VALID_CASE = {
    "schema_version": 1,
    "id": "TST-001",
    "title": "Test",
    "category": "exact-output",
    "difficulty": "trivial",
    "mode": "write",
    "tags": ["smoke"],
    "fixture": None,
    "allowed_paths": ["out/x.txt"],
    "prompt": "do thing",
    "expected_output": {"kind": "file", "path": "out/x.txt"},
    "validator": {"type": "exact_text", "args": {"path": "out/x.txt", "expect": "X"}}
}


class TestValidateAgainstSchema(unittest.TestCase):
    def test_accepts_valid_case(self):
        schema = json.loads(loader.SCHEMA_PATH.read_text())
        errors = loader.validate_against_schema(VALID_CASE, schema)
        self.assertEqual(errors, [])

    def test_rejects_missing_required_field(self):
        bad = {k: v for k, v in VALID_CASE.items() if k != "id"}
        schema = json.loads(loader.SCHEMA_PATH.read_text())
        errors = loader.validate_against_schema(bad, schema)
        self.assertTrue(any("id" in e for e in errors), errors)

    def test_rejects_wrong_enum(self):
        bad = dict(VALID_CASE, mode="write-all")
        schema = json.loads(loader.SCHEMA_PATH.read_text())
        errors = loader.validate_against_schema(bad, schema)
        self.assertTrue(any("mode" in e for e in errors), errors)

    def test_rejects_bad_id_pattern(self):
        bad = dict(VALID_CASE, id="not-matching")
        schema = json.loads(loader.SCHEMA_PATH.read_text())
        errors = loader.validate_against_schema(bad, schema)
        self.assertTrue(any("id" in e for e in errors), errors)


class TestLoadCase(unittest.TestCase):
    def test_loads_valid_case_from_disk(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "c.json"
            p.write_text(json.dumps(VALID_CASE))
            case = loader.load_case(p)
            self.assertEqual(case["id"], "TST-001")

    def test_raises_on_malformed_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "c.json"
            p.write_text("not json")
            with self.assertRaises(loader.CaseLoadError):
                loader.load_case(p)

    def test_raises_on_schema_violation(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "c.json"
            p.write_text(json.dumps({"id": "X"}))
            with self.assertRaises(loader.CaseLoadError):
                loader.load_case(p)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest tests.test_loader -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bench.loader'`.

- [ ] **Step 3: Implement `bench/loader.py`**

```python
"""Case loading + stdlib-only schema validation.

Only the JSON-Schema subset used by our v1 schemas is supported:
type (single or list), required, enum, const, pattern, object properties,
array items. No $ref, no oneOf/anyOf, no format, no dependencies.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "case.schema.json"


class CaseLoadError(Exception):
    pass


_JSON_TYPE_TO_PY = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _type_matches(value: Any, type_decl: Any) -> bool:
    types = [type_decl] if isinstance(type_decl, str) else list(type_decl)
    for t in types:
        py = _JSON_TYPE_TO_PY[t]
        if t == "integer" and isinstance(value, bool):
            continue  # bool is subclass of int in Python; reject for integer
        if isinstance(value, py):
            return True
    return False


def validate_against_schema(instance: Any, schema: dict, path: str = "$") -> list[str]:
    errors: list[str] = []

    if "type" in schema and not _type_matches(instance, schema["type"]):
        errors.append(f"{path}: type mismatch; want {schema['type']}, got {type(instance).__name__}")
        return errors  # further checks are meaningless

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: const mismatch; want {schema['const']!r}, got {instance!r}")

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: not in enum {schema['enum']}; got {instance!r}")

    if "pattern" in schema and isinstance(instance, str):
        if not re.search(schema["pattern"], instance):
            errors.append(f"{path}: does not match pattern {schema['pattern']!r}; got {instance!r}")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required field '{key}'")
        for key, sub in schema.get("properties", {}).items():
            if key in instance:
                errors.extend(validate_against_schema(instance[key], sub, f"{path}.{key}"))

    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errors.extend(validate_against_schema(item, schema["items"], f"{path}[{i}]"))

    return errors


def load_case(path: Path) -> dict:
    try:
        raw = path.read_text()
    except OSError as e:
        raise CaseLoadError(f"cannot read case {path}: {e}") from e
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise CaseLoadError(f"invalid JSON in {path}: {e}") from e
    schema = json.loads(SCHEMA_PATH.read_text())
    errors = validate_against_schema(data, schema)
    if errors:
        raise CaseLoadError(f"case {path} fails schema:\n  " + "\n  ".join(errors))
    return data
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_loader -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add bench/loader.py tests/test_loader.py
git commit -m "feat(bench): add case loader with stdlib schema validation"
```

---

### Task 4: Fixture `routes-php`

**Files:**
- Create: `fixtures/routes-php/README.md`
- Create: `fixtures/routes-php/routes/web.php`
- Create: `fixtures/routes-php/app/Http/Controllers/UserController.php`
- Create: `fixtures/routes-php/app/Http/Controllers/ProductController.php`

No PHP runtime required. These files exist to be read/edited as text.

- [ ] **Step 1: Create `fixtures/routes-php/README.md`**

```markdown
# routes-php fixture

A Laravel-style routes-only fixture. Never executed; read/edited as text.

## Intended shape

- `routes/web.php` — six routes using `Route::get/post/put/delete`, each pointing at a controller method.
- `app/Http/Controllers/UserController.php` — stub with method signatures only.
- `app/Http/Controllers/ProductController.php` — stub with method signatures only.

## Cases that depend on this fixture

- `RO-001` — read-only: list every route as JSON.

Any change to the number, method, path, or handler of any route is benchmark drift and requires bumping `schema_version` on dependent cases.
```

- [ ] **Step 2: Create `fixtures/routes-php/routes/web.php`**

```php
<?php

use App\Http\Controllers\UserController;
use App\Http\Controllers\ProductController;
use Illuminate\Support\Facades\Route;

Route::get('/users', [UserController::class, 'index']);
Route::get('/users/{id}', [UserController::class, 'show']);
Route::post('/users', [UserController::class, 'store']);
Route::put('/users/{id}', [UserController::class, 'update']);
Route::delete('/users/{id}', [UserController::class, 'destroy']);
Route::get('/products', [ProductController::class, 'index']);
```

- [ ] **Step 3: Create `fixtures/routes-php/app/Http/Controllers/UserController.php`**

```php
<?php

namespace App\Http\Controllers;

class UserController extends Controller
{
    public function index() {}
    public function show($id) {}
    public function store() {}
    public function update($id) {}
    public function destroy($id) {}
}
```

- [ ] **Step 4: Create `fixtures/routes-php/app/Http/Controllers/ProductController.php`**

```php
<?php

namespace App\Http\Controllers;

class ProductController extends Controller
{
    public function index() {}
}
```

- [ ] **Step 5: Verify file layout**

Run: `python3 -c "from pathlib import Path; [print(p) for p in sorted(Path('fixtures/routes-php').rglob('*')) if p.is_file()]"`
Expected: four files listed — README.md, routes/web.php, and two controllers.

- [ ] **Step 6: Commit**

```bash
git add fixtures/routes-php/
git commit -m "feat(fixtures): add routes-php fixture (6 routes, 2 stub controllers)"
```

---

### Task 5: Fixture `todo-py`

**Files:**
- Create: `fixtures/todo-py/README.md` (with deliberate typo)
- Create: `fixtures/todo-py/todo.py`
- Create: `fixtures/todo-py/test_todo.py`

- [ ] **Step 1: Create `fixtures/todo-py/README.md`**

Contains a deliberate typo — `recieve` instead of `receive` — that EDT-002 targets.

```markdown
# todo-py fixture

A tiny Python todo module. Tests exist but are NOT executed by the benchmark in v1.

## Intended shape

- `todo.py` — `Todo` dataclass (id, text, done), `TodoList` class with `add(text) -> int`, `complete(id) -> bool`, `list() -> list[Todo]`.
- `test_todo.py` — three `unittest` tests covering add / complete / list.

## Known defect (intentional)

The word "recieve" in this file is a deliberate misspelling. Cases that test negative-scope editing use it as the only thing the agent is allowed to change.

## Cases that depend on this fixture

- `EDT-002` — bounded-edit-negative: fix the typo without touching `.py` files.
```

- [ ] **Step 2: Create `fixtures/todo-py/todo.py`**

```python
from dataclasses import dataclass


@dataclass
class Todo:
    id: int
    text: str
    done: bool = False


class TodoList:
    def __init__(self) -> None:
        self._items: list[Todo] = []
        self._next_id = 1

    def add(self, text: str) -> int:
        todo = Todo(id=self._next_id, text=text)
        self._items.append(todo)
        self._next_id += 1
        return todo.id

    def complete(self, todo_id: int) -> bool:
        for t in self._items:
            if t.id == todo_id:
                t.done = True
                return True
        return False

    def list(self) -> list[Todo]:
        return list(self._items)
```

- [ ] **Step 3: Create `fixtures/todo-py/test_todo.py`**

```python
import unittest

from todo import TodoList


class TestTodoList(unittest.TestCase):
    def test_add_assigns_incrementing_ids(self):
        tl = TodoList()
        self.assertEqual(tl.add("a"), 1)
        self.assertEqual(tl.add("b"), 2)

    def test_complete_marks_done(self):
        tl = TodoList()
        i = tl.add("x")
        self.assertTrue(tl.complete(i))
        self.assertTrue(tl.list()[0].done)

    def test_complete_missing_returns_false(self):
        tl = TodoList()
        self.assertFalse(tl.complete(99))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Verify fixture readme contains the typo marker**

Run: `python3 -c "from pathlib import Path; assert 'recieve' in Path('fixtures/todo-py/README.md').read_text(); print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add fixtures/todo-py/
git commit -m "feat(fixtures): add todo-py fixture (Todo dataclass + TodoList)"
```

---

### Task 6: Four v1 case JSON files

**Files:**
- Create: `cases/smoke/SMK-001.json`
- Create: `cases/structured/STR-001.json`
- Create: `cases/structured/RO-001.json`
- Create: `cases/bounded-edit/EDT-002.json`
- Test: `tests/test_cases.py`

- [ ] **Step 1: Write failing test that all four cases load cleanly**

Create `tests/test_cases.py`:

```python
import unittest
from pathlib import Path

from bench import loader

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"
EXPECTED_IDS = {"SMK-001", "STR-001", "RO-001", "EDT-002"}


class TestCaseFiles(unittest.TestCase):
    def setUp(self):
        self.files = sorted(CASES_DIR.rglob("*.json"))

    def test_four_cases_on_disk(self):
        self.assertEqual(len(self.files), 4, [p.name for p in self.files])

    def test_all_cases_load_against_schema(self):
        ids = set()
        for f in self.files:
            case = loader.load_case(f)
            ids.add(case["id"])
        self.assertEqual(ids, EXPECTED_IDS)

    def test_smk_001_shape(self):
        case = loader.load_case(CASES_DIR / "smoke" / "SMK-001.json")
        self.assertEqual(case["mode"], "write")
        self.assertEqual(case["validator"]["type"], "exact_text")
        self.assertEqual(case["allowed_paths"], ["out/banner.txt"])

    def test_str_001_shape(self):
        case = loader.load_case(CASES_DIR / "structured" / "STR-001.json")
        self.assertEqual(case["validator"]["type"], "keys_present")
        self.assertIn("smoke", case["tags"])
        self.assertIn("structured-output", case["tags"])

    def test_ro_001_shape(self):
        case = loader.load_case(CASES_DIR / "structured" / "RO-001.json")
        self.assertEqual(case["mode"], "read-only")
        self.assertEqual(case["fixture"], "routes-php")

    def test_edt_002_shape(self):
        case = loader.load_case(CASES_DIR / "bounded-edit" / "EDT-002.json")
        self.assertEqual(case["fixture"], "todo-py")
        self.assertIn("todo-py/README.md", case["allowed_paths"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest tests.test_cases -v`
Expected: FAIL — zero or fewer than 4 case files found.

- [ ] **Step 3: Create `cases/smoke/SMK-001.json`**

```json
{
  "schema_version": 1,
  "id": "SMK-001",
  "title": "Echo exact banner",
  "category": "exact-output",
  "difficulty": "trivial",
  "mode": "write",
  "tags": ["smoke", "no-fixture"],
  "fixture": null,
  "allowed_paths": ["out/banner.txt"],
  "prompt": "Write the following exact text to out/banner.txt, with no leading or trailing whitespace and no trailing newline:\n\nHELLO-BENCHMARK-V1",
  "expected_output": { "kind": "file", "path": "out/banner.txt" },
  "validator": {
    "type": "exact_text",
    "args": {
      "path": "out/banner.txt",
      "expect": "HELLO-BENCHMARK-V1",
      "trailing_newline": false
    }
  }
}
```

- [ ] **Step 4: Create `cases/structured/STR-001.json`**

The validator here is the `keys_present` variant — it is responsible for invoking the JSON-parse check itself (Task 11 implements that). Earlier design referred to chaining `json_file` + `keys_present`; in v1 we single-validator every case and let `keys_present` accept a `path` arg that points at a JSON file.

```json
{
  "schema_version": 1,
  "id": "STR-001",
  "title": "Write project summary JSON",
  "category": "structured-json",
  "difficulty": "easy",
  "mode": "write",
  "tags": ["smoke", "structured-output", "no-fixture"],
  "fixture": null,
  "allowed_paths": ["out/summary.json"],
  "prompt": "Write a valid JSON file to out/summary.json with exactly these three keys: name (string), version (string matching semver like \"1.2.3\"), tags (array of exactly 3 lowercase strings matching ^[a-z][a-z0-9-]*$). Do not add any other keys.",
  "expected_output": { "kind": "file", "path": "out/summary.json" },
  "validator": {
    "type": "keys_present",
    "args": {
      "path": "out/summary.json",
      "required": ["name", "version", "tags"],
      "constraints": {
        "name":    { "type": "string" },
        "version": { "type": "string", "regex": "^\\d+\\.\\d+\\.\\d+$" },
        "tags":    { "type": "array",  "len": 3, "items_regex": "^[a-z][a-z0-9-]*$" }
      }
    }
  }
}
```

- [ ] **Step 5: Create `cases/structured/RO-001.json`**

```json
{
  "schema_version": 1,
  "id": "RO-001",
  "title": "List routes as JSON",
  "category": "read-only-understanding",
  "difficulty": "easy",
  "mode": "read-only",
  "tags": ["structured-output", "read-only"],
  "fixture": "routes-php",
  "allowed_paths": ["out/routes.json"],
  "prompt": "Read routes-php/routes/web.php. Write a JSON array to out/routes.json where each element is an object with keys method (uppercase HTTP verb), path (string starting with /), handler (string like \"UserController@index\"). Include every Route declared in the file. Do not modify any fixture file.",
  "expected_output": { "kind": "file", "path": "out/routes.json" },
  "validator": {
    "type": "keys_present",
    "args": {
      "path": "out/routes.json",
      "top_type": "array",
      "min_len": 6,
      "each_item": {
        "required": ["method", "path", "handler"],
        "constraints": {
          "method":  { "type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"] },
          "path":    { "type": "string", "regex": "^/" },
          "handler": { "type": "string", "regex": "^[A-Z][A-Za-z]*@[a-z][A-Za-z]*$" }
        }
      }
    }
  }
}
```

- [ ] **Step 6: Create `cases/bounded-edit/EDT-002.json`**

```json
{
  "schema_version": 1,
  "id": "EDT-002",
  "title": "Fix README typo without touching code",
  "category": "bounded-edit-negative",
  "difficulty": "easy",
  "mode": "write",
  "tags": ["bounded-edit", "scope"],
  "fixture": "todo-py",
  "allowed_paths": ["todo-py/README.md"],
  "prompt": "In todo-py/README.md there is a misspelled word \"recieve\". Fix it to \"receive\". Do not modify any other file. In particular, do not edit any .py file.",
  "expected_output": { "kind": "file", "path": "todo-py/README.md" },
  "validator": {
    "type": "file_exists",
    "args": {
      "path": "todo-py/README.md",
      "exists": true,
      "not_contains": "recieve",
      "contains": "receive"
    }
  }
}
```

- [ ] **Step 7: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_cases -v`
Expected: PASS (6 tests).

- [ ] **Step 8: Commit**

```bash
git add cases/ tests/test_cases.py
git commit -m "feat(cases): add SMK-001, STR-001, RO-001, EDT-002 for v1 suites"
```

---

### Task 7: Allowed-path matcher (`bench/paths.py`)

**Files:**
- Create: `bench/paths.py`
- Test: `tests/test_paths.py`

Implements spec §4 + §8.3 matching rules. Exact-path, directory-prefix (`/` suffix), and single-segment `fnmatch` globs. No recursive `**`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_paths.py`:

```python
import unittest

from bench.paths import matches, any_match


class TestMatches(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(matches("out/banner.txt", "out/banner.txt"))
        self.assertFalse(matches("out/banner2.txt", "out/banner.txt"))

    def test_directory_prefix_self(self):
        self.assertTrue(matches("out", "out/"))
        self.assertTrue(matches("out/banner.txt", "out/"))
        self.assertTrue(matches("out/nested/deep.txt", "out/"))

    def test_directory_prefix_non_match(self):
        self.assertFalse(matches("output.txt", "out/"))
        self.assertFalse(matches("other/banner.txt", "out/"))

    def test_single_segment_glob(self):
        self.assertTrue(matches("out/x.json", "out/*.json"))
        self.assertFalse(matches("out/sub/x.json", "out/*.json"))  # * does not cross /
        self.assertFalse(matches("out/x.txt", "out/*.json"))

    def test_question_mark_glob(self):
        self.assertTrue(matches("out/a.txt", "out/?.txt"))
        self.assertFalse(matches("out/ab.txt", "out/?.txt"))

    def test_any_match_true_on_any(self):
        self.assertTrue(any_match("out/x.json", ["other/", "out/*.json"]))

    def test_any_match_false_on_none(self):
        self.assertFalse(any_match("out/x.json", ["other/", "out/*.txt"]))

    def test_any_match_empty_patterns(self):
        self.assertFalse(any_match("anything", []))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest tests.test_paths -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bench.paths'`.

- [ ] **Step 3: Implement `bench/paths.py`**

```python
"""Allowed-path matching per spec §4 and §8.3.

Entries are one of:
  * exact relative path       -> equal compare
  * path ending in '/'        -> self or any descendant
  * fnmatch glob (*, ?)       -> fnmatch.fnmatchcase within a single segment;
                                 wildcards do NOT cross '/' boundaries

Recursive ** globs are intentionally not supported in v1.
"""
from __future__ import annotations

import fnmatch


def _is_glob(pattern: str) -> bool:
    return any(ch in pattern for ch in "*?[")


def matches(candidate: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        stem = pattern[:-1]
        return candidate == stem or candidate.startswith(stem + "/")

    if not _is_glob(pattern):
        return candidate == pattern

    # Segment-aware glob: the candidate must have the same number of '/' segments
    # as the pattern, and each segment must fnmatch the corresponding one.
    pat_parts = pattern.split("/")
    cand_parts = candidate.split("/")
    if len(pat_parts) != len(cand_parts):
        return False
    return all(fnmatch.fnmatchcase(c, p) for c, p in zip(cand_parts, pat_parts))


def any_match(candidate: str, patterns: list[str]) -> bool:
    return any(matches(candidate, p) for p in patterns)
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_paths -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add bench/paths.py tests/test_paths.py
git commit -m "feat(bench): add segment-aware allowed-path matcher"
```

---

### Task 8: Baseline capture + diff (`bench/baseline.py`)

**Files:**
- Create: `bench/baseline.py`
- Test: `tests/test_baseline.py`

Exposes:
- `walk(workdir: Path) -> dict[str, dict]` — for each regular file under `workdir/` except `workdir/.bench/`, return `{"sha256": str, "size": int}` keyed by POSIX-style relative path.
- `capture(workdir: Path) -> dict` — writes `workdir/.bench/baseline.json` and returns the dict written.
- `diff(baseline: dict, current: dict) -> dict` — returns `{"created": [paths], "modified": [paths], "deleted": [paths], "unchanged": [paths], "unsupported": [paths]}`. `unsupported` is populated only if `walk` flagged a non-regular file (walk returns such entries with `sha256 = "__unsupported__"`).

- [ ] **Step 1: Write failing tests**

Create `tests/test_baseline.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from bench import baseline


class TestWalk(unittest.TestCase):
    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(baseline.walk(Path(td)), {})

    def test_skips_bench_sidecar(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / ".bench").mkdir()
            (p / ".bench" / "x.json").write_text("{}")
            (p / "a.txt").write_text("hi")
            result = baseline.walk(p)
            self.assertEqual(list(result.keys()), ["a.txt"])

    def test_walks_nested_files(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "sub").mkdir()
            (p / "sub" / "b.txt").write_text("b")
            (p / "a.txt").write_text("a")
            result = baseline.walk(p)
            self.assertEqual(set(result), {"a.txt", "sub/b.txt"})
            self.assertEqual(result["a.txt"]["size"], 1)
            self.assertEqual(len(result["a.txt"]["sha256"]), 64)


class TestCapture(unittest.TestCase):
    def test_writes_sidecar_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "a.txt").write_text("hello")
            result = baseline.capture(p)
            data = json.loads((p / ".bench" / "baseline.json").read_text())
            self.assertEqual(set(data["files"]), {"a.txt"})
            self.assertEqual(result, data)
            self.assertIn("captured_at", data)


class TestDiff(unittest.TestCase):
    def test_created_modified_deleted_unchanged(self):
        base = {"same.txt": {"sha256": "A"}, "change.txt": {"sha256": "B"}, "gone.txt": {"sha256": "C"}}
        cur  = {"same.txt": {"sha256": "A"}, "change.txt": {"sha256": "X"}, "new.txt": {"sha256": "Z"}}
        d = baseline.diff(base, cur)
        self.assertEqual(d["unchanged"], ["same.txt"])
        self.assertEqual(d["modified"], ["change.txt"])
        self.assertEqual(d["deleted"], ["gone.txt"])
        self.assertEqual(d["created"], ["new.txt"])
        self.assertEqual(d["unsupported"], [])

    def test_unsupported_flagged(self):
        base = {}
        cur  = {"weird.lnk": {"sha256": "__unsupported__"}}
        d = baseline.diff(base, cur)
        self.assertEqual(d["unsupported"], ["weird.lnk"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest tests.test_baseline -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `bench/baseline.py`**

```python
"""Baseline capture + diff per spec §8."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SIDECAR_DIRNAME = ".bench"
BASELINE_FILENAME = "baseline.json"
ALLOWED_PATHS_FILENAME = "allowed_paths.json"
_UNSUPPORTED_MARKER = "__unsupported__"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(workdir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in sorted(workdir.rglob("*")):
        rel_parts = p.relative_to(workdir).parts
        if rel_parts and rel_parts[0] == SIDECAR_DIRNAME:
            continue
        if p.is_dir():
            continue
        rel = "/".join(rel_parts)
        if p.is_symlink() or not p.is_file():
            out[rel] = {"sha256": _UNSUPPORTED_MARKER, "size": 0}
            continue
        out[rel] = {"sha256": _sha256(p), "size": p.stat().st_size}
    return out


def capture(workdir: Path) -> dict:
    files = walk(workdir)
    data = {
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "files": files,
    }
    sidecar = workdir / SIDECAR_DIRNAME
    sidecar.mkdir(parents=True, exist_ok=True)
    (sidecar / BASELINE_FILENAME).write_text(json.dumps(data, indent=2))
    return data


def diff(baseline: dict, current: dict) -> dict:
    b_files = baseline.get("files", baseline) if "files" in baseline else baseline
    all_paths = set(b_files) | set(current)
    created, modified, deleted, unchanged, unsupported = [], [], [], [], []
    for path in sorted(all_paths):
        b = b_files.get(path)
        c = current.get(path)
        if c and c.get("sha256") == _UNSUPPORTED_MARKER:
            unsupported.append(path)
            continue
        if b is None:
            created.append(path)
        elif c is None:
            deleted.append(path)
        elif b.get("sha256") == c.get("sha256"):
            unchanged.append(path)
        else:
            modified.append(path)
    return {
        "created": created,
        "modified": modified,
        "deleted": deleted,
        "unchanged": unchanged,
        "unsupported": unsupported,
    }
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_baseline -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add bench/baseline.py tests/test_baseline.py
git commit -m "feat(bench): add workdir baseline capture + diff"
```

---

### Task 9: Validator `exact_text`

**Files:**
- Create: `validators/exact_text.py`
- Test: `tests/test_exact_text.py`

Signature: `validate(case: dict, workdir: Path) -> dict` returning `{"type": "exact_text", "ok": bool, "detail": str, ...}`.

Args supported: `path` (required), `expect` (required), `trailing_newline` (default `true`), `strip` (default `false`).

- [ ] **Step 1: Write failing tests**

Create `tests/test_exact_text.py`:

```python
import tempfile
import unittest
from pathlib import Path

from validators import exact_text


def case(**args):
    return {"validator": {"type": "exact_text", "args": args}}


def write(td: Path, name: str, data: bytes) -> None:
    (td / name).write_bytes(data)


class TestExactText(unittest.TestCase):
    def test_exact_match_no_trailing_newline(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write(td, "o.txt", b"HELLO")
            r = exact_text.validate(case(path="o.txt", expect="HELLO", trailing_newline=False), td)
            self.assertTrue(r["ok"], r)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as td:
            r = exact_text.validate(case(path="o.txt", expect="HELLO"), Path(td))
            self.assertFalse(r["ok"])
            self.assertIn("missing", r["detail"])

    def test_rejects_trailing_newline_when_forbidden(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write(td, "o.txt", b"HELLO\n")
            r = exact_text.validate(case(path="o.txt", expect="HELLO", trailing_newline=False), td)
            self.assertFalse(r["ok"])

    def test_requires_trailing_newline_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write(td, "o.txt", b"HELLO")
            r = exact_text.validate(case(path="o.txt", expect="HELLO"), td)
            self.assertFalse(r["ok"])

    def test_content_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write(td, "o.txt", b"BYE")
            r = exact_text.validate(case(path="o.txt", expect="HELLO", trailing_newline=False), td)
            self.assertFalse(r["ok"])
            self.assertEqual(r["observed"], "BYE")
            self.assertEqual(r["expected"], "HELLO")

    def test_strip(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write(td, "o.txt", b"  HELLO  ")
            r = exact_text.validate(case(path="o.txt", expect="HELLO", trailing_newline=False, strip=True), td)
            self.assertTrue(r["ok"], r)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest tests.test_exact_text -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `validators/exact_text.py`**

```python
from __future__ import annotations

from pathlib import Path


def validate(case: dict, workdir: Path) -> dict:
    args = case["validator"]["args"]
    rel = args["path"]
    expect = args["expect"]
    trailing_nl = args.get("trailing_newline", True)
    strip = args.get("strip", False)

    p = workdir / rel
    if not p.exists():
        return {"type": "exact_text", "ok": False, "detail": f"missing file: {rel}"}

    data = p.read_bytes()
    if strip:
        data = data.strip()

    if trailing_nl:
        if not data.endswith(b"\n"):
            return {"type": "exact_text", "ok": False, "detail": "missing required trailing newline"}
        data = data[:-1]
    else:
        if data.endswith(b"\n"):
            return {"type": "exact_text", "ok": False, "detail": "unexpected trailing newline"}

    try:
        observed = data.decode("utf-8")
    except UnicodeDecodeError:
        return {"type": "exact_text", "ok": False, "detail": "file is not valid UTF-8"}

    if observed == expect:
        return {"type": "exact_text", "ok": True, "detail": "bytes match"}
    return {
        "type": "exact_text",
        "ok": False,
        "detail": "byte mismatch",
        "observed": observed,
        "expected": expect,
    }
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_exact_text -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add validators/exact_text.py tests/test_exact_text.py
git commit -m "feat(validators): add exact_text validator"
```

---

### Task 10: Validator `json_file`

**Files:**
- Create: `validators/json_file.py`
- Test: `tests/test_json_file.py`

Args: `path`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_json_file.py`:

```python
import tempfile
import unittest
from pathlib import Path

from validators import json_file


def case(**args):
    return {"validator": {"type": "json_file", "args": args}}


class TestJsonFile(unittest.TestCase):
    def test_valid_json_passes(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "o.json").write_text('{"a": 1}')
            r = json_file.validate(case(path="o.json"), Path(td))
            self.assertTrue(r["ok"])
            self.assertEqual(r["observed"], {"a": 1})

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as td:
            r = json_file.validate(case(path="o.json"), Path(td))
            self.assertFalse(r["ok"])
            self.assertIn("missing", r["detail"])

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "o.json").write_text("not json")
            r = json_file.validate(case(path="o.json"), Path(td))
            self.assertFalse(r["ok"])
            self.assertIn("JSON", r["detail"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest tests.test_json_file -v`
Expected: FAIL.

- [ ] **Step 3: Implement `validators/json_file.py`**

```python
from __future__ import annotations

import json
from pathlib import Path


def validate(case: dict, workdir: Path) -> dict:
    rel = case["validator"]["args"]["path"]
    p = workdir / rel
    if not p.exists():
        return {"type": "json_file", "ok": False, "detail": f"missing file: {rel}"}
    try:
        parsed = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        return {"type": "json_file", "ok": False, "detail": f"invalid JSON: {e}"}
    return {"type": "json_file", "ok": True, "detail": "parsed OK", "observed": parsed}
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_json_file -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add validators/json_file.py tests/test_json_file.py
git commit -m "feat(validators): add json_file validator"
```

---

### Task 11: Validator `keys_present`

**Files:**
- Create: `validators/keys_present.py`
- Test: `tests/test_keys_present.py`

Accepts args: `path` (required; JSON file to load), optional `top_type` (`object` default | `array`), `min_len` (for arrays), `required` (list of keys for object-shaped JSON), `constraints` (dict keyed by required key), `each_item` (dict applied to every array element, with its own `required`/`constraints`).

Per-key constraint fields supported: `type`, `regex`, `enum`, `len`, `items_regex`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_keys_present.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from validators import keys_present


def case(**args):
    return {"validator": {"type": "keys_present", "args": args}}


def write_json(td: Path, name: str, obj) -> None:
    (td / name).write_text(json.dumps(obj))


class TestKeysPresent(unittest.TestCase):
    def test_object_required_pass(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write_json(td, "o.json", {"name": "x", "version": "1.0.0", "tags": ["a", "b", "c"]})
            r = keys_present.validate(case(
                path="o.json",
                required=["name", "version", "tags"],
                constraints={
                    "name":    {"type": "string"},
                    "version": {"type": "string", "regex": r"^\d+\.\d+\.\d+$"},
                    "tags":    {"type": "array",  "len": 3, "items_regex": "^[a-z][a-z0-9-]*$"},
                },
            ), td)
            self.assertTrue(r["ok"], r)

    def test_missing_required_key(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write_json(td, "o.json", {"name": "x"})
            r = keys_present.validate(case(path="o.json", required=["name", "version"]), td)
            self.assertFalse(r["ok"])
            self.assertIn("version", r["detail"])

    def test_regex_fail(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write_json(td, "o.json", {"version": "not-semver"})
            r = keys_present.validate(case(
                path="o.json", required=["version"],
                constraints={"version": {"type": "string", "regex": r"^\d+\.\d+\.\d+$"}},
            ), td)
            self.assertFalse(r["ok"])

    def test_array_top_type_min_len(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write_json(td, "o.json", [
                {"method": "GET",  "path": "/a", "handler": "A@a"},
                {"method": "POST", "path": "/b", "handler": "B@b"},
            ])
            r = keys_present.validate(case(
                path="o.json",
                top_type="array",
                min_len=2,
                each_item={
                    "required": ["method", "path", "handler"],
                    "constraints": {
                        "method":  {"type": "string", "enum": ["GET", "POST"]},
                        "path":    {"type": "string", "regex": "^/"},
                        "handler": {"type": "string", "regex": "^[A-Z][A-Za-z]*@[a-z][A-Za-z]*$"},
                    },
                },
            ), td)
            self.assertTrue(r["ok"], r)

    def test_array_min_len_violation(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            write_json(td, "o.json", [])
            r = keys_present.validate(case(path="o.json", top_type="array", min_len=1), td)
            self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest tests.test_keys_present -v`
Expected: FAIL.

- [ ] **Step 3: Implement `validators/keys_present.py`**

```python
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_JSON_TYPES = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array":   list,
    "object":  dict,
    "null":    type(None),
}


def _type_ok(value: Any, type_name: str) -> bool:
    py = _JSON_TYPES[type_name]
    if type_name == "integer" and isinstance(value, bool):
        return False
    return isinstance(value, py)


def _check_constraints(value: Any, constraints: dict, label: str) -> list[str]:
    errs: list[str] = []
    if "type" in constraints and not _type_ok(value, constraints["type"]):
        errs.append(f"{label}: expected type {constraints['type']}, got {type(value).__name__}")
        return errs
    if "enum" in constraints and value not in constraints["enum"]:
        errs.append(f"{label}: value {value!r} not in enum {constraints['enum']}")
    if "regex" in constraints and isinstance(value, str):
        if not re.search(constraints["regex"], value):
            errs.append(f"{label}: {value!r} does not match /{constraints['regex']}/")
    if "len" in constraints:
        try:
            if len(value) != constraints["len"]:
                errs.append(f"{label}: length {len(value)} != required {constraints['len']}")
        except TypeError:
            errs.append(f"{label}: cannot take length of {type(value).__name__}")
    if "items_regex" in constraints and isinstance(value, list):
        rx = constraints["items_regex"]
        for i, item in enumerate(value):
            if not (isinstance(item, str) and re.search(rx, item)):
                errs.append(f"{label}[{i}]: {item!r} does not match /{rx}/")
    return errs


def _check_object(obj: dict, required: list[str], constraints: dict[str, dict]) -> list[str]:
    errs: list[str] = []
    for key in required:
        if key not in obj:
            errs.append(f"missing required key '{key}'")
    for key, rules in constraints.items():
        if key in obj:
            errs.extend(_check_constraints(obj[key], rules, key))
    return errs


def validate(case: dict, workdir: Path) -> dict:
    args = case["validator"]["args"]
    rel = args["path"]
    p = workdir / rel
    if not p.exists():
        return {"type": "keys_present", "ok": False, "detail": f"missing file: {rel}"}
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        return {"type": "keys_present", "ok": False, "detail": f"invalid JSON: {e}"}

    top_type = args.get("top_type", "object")
    if not _type_ok(data, top_type):
        return {"type": "keys_present", "ok": False,
                "detail": f"top-level type mismatch: want {top_type}, got {type(data).__name__}"}

    errors: list[str] = []

    if top_type == "object":
        errors.extend(_check_object(data, args.get("required", []), args.get("constraints", {})))

    if top_type == "array":
        if "min_len" in args and len(data) < args["min_len"]:
            errors.append(f"array length {len(data)} < min_len {args['min_len']}")
        item_rules = args.get("each_item")
        if item_rules:
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    errors.append(f"[{i}]: not an object")
                    continue
                sub_errs = _check_object(item, item_rules.get("required", []), item_rules.get("constraints", {}))
                errors.extend(f"[{i}].{e}" for e in sub_errs)

    if errors:
        return {"type": "keys_present", "ok": False, "detail": "; ".join(errors), "observed": data}
    return {"type": "keys_present", "ok": True, "detail": "all checks passed", "observed": data}
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_keys_present -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add validators/keys_present.py tests/test_keys_present.py
git commit -m "feat(validators): add keys_present validator with object/array modes"
```

---

### Task 12: Validator `file_exists`

**Files:**
- Create: `validators/file_exists.py`
- Test: `tests/test_file_exists.py`

Args: `path`, `exists: bool = true`, optional `contains: str`, optional `not_contains: str`. `contains`/`not_contains` require the file to exist.

- [ ] **Step 1: Write failing tests**

Create `tests/test_file_exists.py`:

```python
import tempfile
import unittest
from pathlib import Path

from validators import file_exists


def case(**args):
    return {"validator": {"type": "file_exists", "args": args}}


class TestFileExists(unittest.TestCase):
    def test_exists_true_passes(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.txt").write_text("hi")
            r = file_exists.validate(case(path="a.txt", exists=True), Path(td))
            self.assertTrue(r["ok"])

    def test_exists_true_fails_when_missing(self):
        with tempfile.TemporaryDirectory() as td:
            r = file_exists.validate(case(path="a.txt", exists=True), Path(td))
            self.assertFalse(r["ok"])

    def test_exists_false_passes_when_missing(self):
        with tempfile.TemporaryDirectory() as td:
            r = file_exists.validate(case(path="a.txt", exists=False), Path(td))
            self.assertTrue(r["ok"])

    def test_contains_passes(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.txt").write_text("please receive this")
            r = file_exists.validate(case(path="a.txt", exists=True, contains="receive"), Path(td))
            self.assertTrue(r["ok"])

    def test_not_contains_passes(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.txt").write_text("please receive this")
            r = file_exists.validate(case(path="a.txt", exists=True, not_contains="recieve"), Path(td))
            self.assertTrue(r["ok"])

    def test_contains_fails(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.txt").write_text("bye")
            r = file_exists.validate(case(path="a.txt", exists=True, contains="hello"), Path(td))
            self.assertFalse(r["ok"])

    def test_not_contains_fails(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.txt").write_text("please recieve this")
            r = file_exists.validate(case(path="a.txt", exists=True, not_contains="recieve"), Path(td))
            self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest tests.test_file_exists -v`
Expected: FAIL.

- [ ] **Step 3: Implement `validators/file_exists.py`**

```python
from __future__ import annotations

from pathlib import Path


def validate(case: dict, workdir: Path) -> dict:
    args = case["validator"]["args"]
    rel = args["path"]
    want_exists = args.get("exists", True)
    contains = args.get("contains")
    not_contains = args.get("not_contains")

    p = workdir / rel
    exists = p.exists()

    if exists != want_exists:
        return {
            "type": "file_exists",
            "ok": False,
            "detail": f"exists={exists}, required exists={want_exists} for {rel}",
        }

    if not exists:
        return {"type": "file_exists", "ok": True, "detail": f"{rel} absent as required"}

    if contains is None and not_contains is None:
        return {"type": "file_exists", "ok": True, "detail": f"{rel} present"}

    content = p.read_text()
    if contains is not None and contains not in content:
        return {"type": "file_exists", "ok": False,
                "detail": f"{rel} is missing required substring {contains!r}"}
    if not_contains is not None and not_contains in content:
        return {"type": "file_exists", "ok": False,
                "detail": f"{rel} still contains forbidden substring {not_contains!r}"}
    return {"type": "file_exists", "ok": True, "detail": f"{rel} present and content checks pass"}
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_file_exists -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add validators/file_exists.py tests/test_file_exists.py
git commit -m "feat(validators): add file_exists with contains/not_contains"
```

---

### Task 13: Validator `allowed_paths_check`

**Files:**
- Create: `validators/allowed_paths_check.py`
- Test: `tests/test_allowed_paths_check.py`

Reads `workdir/.bench/baseline.json` + `workdir/.bench/allowed_paths.json`. Walks current state. Uses `bench.baseline.diff` and `bench.paths.any_match`. Emits the result shape documented in spec §8.4.

- [ ] **Step 1: Write failing tests**

Create `tests/test_allowed_paths_check.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from bench import baseline
from validators import allowed_paths_check


def setup_workdir(files: dict[str, bytes], allowed: list[str]) -> Path:
    td = Path(tempfile.mkdtemp(prefix="tmp_test_apc_"))
    for rel, data in files.items():
        p = td / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    baseline.capture(td)
    (td / ".bench" / "allowed_paths.json").write_text(json.dumps(allowed))
    return td


class TestAllowedPathsCheck(unittest.TestCase):
    def test_no_changes_passes(self):
        td = setup_workdir({"fix/a.py": b"x"}, ["out/"])
        r = allowed_paths_check.validate({}, td)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["counts"]["unchanged"], 1)

    def test_allowed_create_passes(self):
        td = setup_workdir({"fix/a.py": b"x"}, ["out/", "out/banner.txt"])
        (td / "out").mkdir()
        (td / "out" / "banner.txt").write_text("HI")
        r = allowed_paths_check.validate({}, td)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["counts"]["created"], 1)

    def test_disallowed_create_violates(self):
        td = setup_workdir({"fix/a.py": b"x"}, ["out/banner.txt"])
        (td / "rogue.txt").write_text("nope")
        r = allowed_paths_check.validate({}, td)
        self.assertFalse(r["ok"])
        self.assertEqual([v["path"] for v in r["violations"]], ["rogue.txt"])
        self.assertEqual(r["violations"][0]["kind"], "created")

    def test_disallowed_modify_violates(self):
        td = setup_workdir({"fix/a.py": b"x"}, ["out/"])
        (td / "fix" / "a.py").write_text("CHANGED")
        r = allowed_paths_check.validate({}, td)
        self.assertFalse(r["ok"])
        kinds = {v["path"]: v["kind"] for v in r["violations"]}
        self.assertEqual(kinds["fix/a.py"], "modified")

    def test_delete_default_violates(self):
        td = setup_workdir({"fix/a.py": b"x"}, ["fix/a.py"])
        (td / "fix" / "a.py").unlink()
        r = allowed_paths_check.validate({}, td)
        self.assertFalse(r["ok"])
        self.assertEqual(r["violations"][0]["kind"], "deleted")

    def test_delete_with_allow_deletions(self):
        td = setup_workdir({"fix/a.py": b"x"}, ["fix/a.py"])
        (td / "fix" / "a.py").unlink()
        case = {"allow_deletions": True}
        r = allowed_paths_check.validate(case, td)
        self.assertTrue(r["ok"])

    def test_unsupported_flagged(self):
        td = setup_workdir({}, [])
        # Create a symlink pointing at non-existent target — still a non-regular file
        (td / "s").symlink_to("nowhere")
        r = allowed_paths_check.validate({}, td)
        self.assertFalse(r["ok"])
        kinds = {v["kind"] for v in r["violations"]}
        self.assertIn("unsupported", kinds)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest tests.test_allowed_paths_check -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `validators/allowed_paths_check.py`**

```python
from __future__ import annotations

import json
from pathlib import Path

from bench import baseline, paths


def validate(case: dict, workdir: Path) -> dict:
    sidecar = workdir / baseline.SIDECAR_DIRNAME
    try:
        baseline_data = json.loads((sidecar / baseline.BASELINE_FILENAME).read_text())
        allowed = json.loads((sidecar / baseline.ALLOWED_PATHS_FILENAME).read_text())
    except FileNotFoundError as e:
        return {
            "type": "allowed_paths_check",
            "ok": False,
            "detail": f"missing sidecar file: {e.filename}",
            "violations": [],
            "counts": {"created": 0, "modified": 0, "deleted": 0, "unchanged": 0},
        }

    current = baseline.walk(workdir)
    d = baseline.diff(baseline_data["files"], current)
    allow_deletions = bool(case.get("allow_deletions", False))

    violations: list[dict] = []

    for path in d["created"]:
        if not paths.any_match(path, allowed):
            violations.append({"path": path, "kind": "created"})
    for path in d["modified"]:
        if not paths.any_match(path, allowed):
            violations.append({"path": path, "kind": "modified"})
    for path in d["deleted"]:
        if not (allow_deletions and paths.any_match(path, allowed)):
            violations.append({"path": path, "kind": "deleted"})
    for path in d["unsupported"]:
        violations.append({"path": path, "kind": "unsupported"})

    return {
        "type": "allowed_paths_check",
        "ok": not violations,
        "detail": "no violations" if not violations else f"{len(violations)} violation(s)",
        "violations": violations,
        "counts": {
            "created":   len(d["created"]),
            "modified":  len(d["modified"]),
            "deleted":   len(d["deleted"]),
            "unchanged": len(d["unchanged"]),
        },
    }
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_allowed_paths_check -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add validators/allowed_paths_check.py tests/test_allowed_paths_check.py
git commit -m "feat(validators): add always-on allowed_paths_check"
```

---

### Task 14: Run-dir + manifest helpers (`bench/runs.py`)

**Files:**
- Create: `bench/runs.py`
- Test: `tests/test_runs.py`

Exposes:
- `new_run_id(label, now=None) -> str` — `YYYYMMDD-HHMMSS-<label>`.
- `new_run_dir(runs_root, label) -> Path` — creates and returns the run dir.
- `write_manifest(run_dir, manifest) -> None` / `read_manifest(run_dir) -> dict`.
- `write_result(case_dir, result) -> None` / `read_result(case_dir) -> dict`.
- `list_cases(cases_root) -> list[Path]` — all `*.json` cases.
- `filter_by_suite(cases: list[dict], suite: str | None, explicit_ids: list[str] | None) -> list[dict]` — suite match via `suite in case["tags"]`; `explicit_ids` overrides suite filtering.
- `collect_environment() -> dict` — host/os/python/arch from `platform.*`. Always returns every key (never missing).
- `collect_hardware(gpu: str | None = None) -> dict` — `cpu_cores` from `os.cpu_count()`; `memory_gb` parsed from `/proc/meminfo` on Linux (`null` elsewhere); `gpu` is the operator-supplied value (`null` if not given).
- `utc_now_iso() -> str` — helper for canonical ISO-8601 UTC timestamps used in manifests.

- [ ] **Step 1: Write failing tests**

Create `tests/test_runs.py`:

```python
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bench import runs


class TestRuns(unittest.TestCase):
    def test_new_run_id_shape(self):
        now = datetime(2026, 4, 21, 18, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(runs.new_run_id("local-llama", now=now), "20260421-180000-local-llama")

    def test_new_run_dir_created(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            d = runs.new_run_dir(root, "x")
            self.assertTrue(d.exists())
            self.assertTrue(d.name.endswith("-x"))

    def test_manifest_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            m = {"run_id": "r1", "label": "x"}
            runs.write_manifest(Path(td), m)
            self.assertEqual(runs.read_manifest(Path(td))["run_id"], "r1")

    def test_result_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            runs.write_result(Path(td), {"case_id": "C", "status": "pass"})
            self.assertEqual(runs.read_result(Path(td))["status"], "pass")

    def test_list_cases(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "a").mkdir()
            (td / "a" / "X.json").write_text("{}")
            (td / "b").mkdir()
            (td / "b" / "Y.json").write_text("{}")
            (td / "README.md").write_text("skip")
            found = sorted(p.name for p in runs.list_cases(td))
            self.assertEqual(found, ["X.json", "Y.json"])

    def test_filter_by_suite_tag(self):
        cases = [
            {"id": "A", "tags": ["smoke", "no-fixture"]},
            {"id": "B", "tags": ["bounded-edit"]},
            {"id": "C", "tags": ["smoke", "structured-output"]},
        ]
        ids = [c["id"] for c in runs.filter_by_suite(cases, suite="smoke", explicit_ids=None)]
        self.assertEqual(sorted(ids), ["A", "C"])

    def test_filter_explicit_ids_overrides(self):
        cases = [{"id": "A", "tags": ["smoke"]}, {"id": "B", "tags": ["bounded-edit"]}]
        ids = [c["id"] for c in runs.filter_by_suite(cases, suite="smoke", explicit_ids=["B"])]
        self.assertEqual(ids, ["B"])

    def test_collect_environment_shape(self):
        env = runs.collect_environment()
        for key in ("host", "os", "python", "arch"):
            self.assertIn(key, env)
            self.assertIsInstance(env[key], str)
            self.assertNotEqual(env[key], "")

    def test_collect_hardware_shape(self):
        hw = runs.collect_hardware()
        for key in ("cpu_cores", "memory_gb", "gpu"):
            self.assertIn(key, hw)
        self.assertTrue(hw["cpu_cores"] is None or isinstance(hw["cpu_cores"], int))
        self.assertTrue(hw["memory_gb"] is None or isinstance(hw["memory_gb"], (int, float)))
        self.assertTrue(hw["gpu"] is None or isinstance(hw["gpu"], str))

    def test_collect_hardware_gpu_override(self):
        hw = runs.collect_hardware(gpu="RTX 4090")
        self.assertEqual(hw["gpu"], "RTX 4090")

    def test_utc_now_iso_format(self):
        import re
        s = runs.utc_now_iso()
        self.assertRegex(s, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest tests.test_runs -v`
Expected: FAIL.

- [ ] **Step 3: Implement `bench/runs.py`**

```python
"""Run-dir layout, manifest and result I/O, case filtering, env/hardware collection."""
from __future__ import annotations

import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path


MANIFEST_NAME = "manifest.json"
RESULT_NAME = "result.json"
CASE_SNAPSHOT_NAME = "case.json"


def new_run_id(label: str, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{label}"


def new_run_dir(runs_root: Path, label: str, now: datetime | None = None) -> Path:
    rid = new_run_id(label, now=now)
    d = runs_root / rid
    (d / "cases").mkdir(parents=True, exist_ok=True)
    return d


def write_manifest(run_dir: Path, manifest: dict) -> None:
    (run_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2))


def read_manifest(run_dir: Path) -> dict:
    return json.loads((run_dir / MANIFEST_NAME).read_text())


def write_result(case_dir: Path, result: dict) -> None:
    (case_dir / RESULT_NAME).write_text(json.dumps(result, indent=2))


def read_result(case_dir: Path) -> dict:
    return json.loads((case_dir / RESULT_NAME).read_text())


def list_cases(cases_root: Path) -> list[Path]:
    return sorted(cases_root.rglob("*.json"))


def filter_by_suite(cases: list[dict], suite: str | None, explicit_ids: list[str] | None) -> list[dict]:
    if explicit_ids:
        wanted = set(explicit_ids)
        return [c for c in cases if c["id"] in wanted]
    if suite:
        return [c for c in cases if suite in c.get("tags", [])]
    return list(cases)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect_environment() -> dict:
    return {
        "host":   platform.node() or "unknown",
        "os":     platform.platform() or "unknown",
        "python": platform.python_version() or "unknown",
        "arch":   platform.machine() or "unknown",
    }


def _read_memory_gb() -> float | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    try:
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                return round(kb / 1024 / 1024, 1)
    except (OSError, ValueError, IndexError):
        return None
    return None


def collect_hardware(gpu: str | None = None) -> dict:
    return {
        "cpu_cores": os.cpu_count(),
        "memory_gb": _read_memory_gb(),
        "gpu":       gpu,
    }
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_runs -v`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git add bench/runs.py tests/test_runs.py
git commit -m "feat(bench): add run-dir, manifest, result, and case-filter helpers"
```

---

### Task 15: Script `new_run.py`

**Files:**
- Create: `scripts/new_run.py`
- Test: `tests/test_new_run_script.py`

Responsibilities (spec §8.1, §9.1, §10):

1. Parse required `--label`, plus optional `--suite`, `--cases id,id`, `--runs-dir`, `--cases-dir`, `--fixtures-dir`.
2. Parse optional agent-metadata flags: `--frontend`, `--model`, `--provider`, `--local-or-cloud` (choices: `local`, `cloud`, `unknown`; default `unknown`), `--runtime-base-url`, `--agent-notes`, `--notes`, `--gpu`.
3. Load all cases under `--cases-dir` (default `cases/`). Filter by suite/cases.
4. Create the run dir via `runs.new_run_dir`. Populate `manifest.json` with full v1 shape (spec §9.1): `timestamp` + `started_at` = `runs.utc_now_iso()`, `finished_at = null`, full `agent` / `environment` / `hardware` blocks, `counts` zeroed, `notes` from `--notes`.
5. For each selected case: create `cases/<id>/workdir/`; snapshot `case.json`; if `fixture` non-null, `shutil.copytree` the fixture into `workdir/<basename>/`; capture baseline; write `workdir/.bench/allowed_paths.json`.
6. Print the new run path to stdout (one line) on success.

- [ ] **Step 1: Write a failing end-to-end test**

Create `tests/test_new_run_script.py`:

```python
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run(*args, **kwargs) -> subprocess.CompletedProcess:
    env = kwargs.pop("env", None)
    return subprocess.run(
        [sys.executable, "-m", "scripts.new_run", *args],
        cwd=REPO, capture_output=True, text=True, env=env, **kwargs,
    )


class TestNewRun(unittest.TestCase):
    def test_creates_run_dir_for_smoke_suite(self):
        with tempfile.TemporaryDirectory() as td:
            r = run("--label", "unit", "--suite", "smoke", "--runs-dir", td)
            self.assertEqual(r.returncode, 0, r.stderr)
            run_dir = Path(td)
            children = list(run_dir.iterdir())
            self.assertEqual(len(children), 1)
            d = children[0]
            self.assertTrue(d.name.endswith("-unit"))
            self.assertTrue((d / "manifest.json").exists())

            manifest = json.loads((d / "manifest.json").read_text())
            self.assertEqual(manifest["label"], "unit")
            self.assertEqual(manifest["suite"], "smoke")
            self.assertEqual(sorted(manifest["cases"]), ["SMK-001", "STR-001"])

            for cid in manifest["cases"]:
                workdir = d / "cases" / cid / "workdir"
                self.assertTrue(workdir.exists(), cid)
                self.assertTrue((workdir / ".bench" / "baseline.json").exists())
                self.assertTrue((workdir / ".bench" / "allowed_paths.json").exists())
                self.assertTrue((d / "cases" / cid / "case.json").exists())

    def test_manifest_has_full_v1_shape(self):
        with tempfile.TemporaryDirectory() as td:
            r = run("--label", "u", "--cases", "SMK-001", "--runs-dir", td,
                    "--frontend", "claude-code",
                    "--model", "claude-opus-4-7",
                    "--provider", "anthropic",
                    "--local-or-cloud", "cloud",
                    "--runtime-base-url", "",
                    "--agent-notes", "test run",
                    "--notes", "first smoke",
                    "--gpu", "none")
            self.assertEqual(r.returncode, 0, r.stderr)
            m = json.loads((next(Path(td).iterdir()) / "manifest.json").read_text())

            # Top-level required fields present
            for key in ("schema_version", "run_id", "timestamp", "started_at", "finished_at",
                        "label", "suite", "cases", "agent", "environment", "hardware",
                        "counts", "notes"):
                self.assertIn(key, m, f"missing top-level field: {key}")

            # Timestamps populated at scaffold time
            self.assertIsNotNone(m["timestamp"])
            self.assertIsNotNone(m["started_at"])
            self.assertIsNone(m["finished_at"])
            self.assertEqual(m["timestamp"], m["started_at"])

            # Agent populated from CLI
            self.assertEqual(m["agent"]["frontend"], "claude-code")
            self.assertEqual(m["agent"]["model"], "claude-opus-4-7")
            self.assertEqual(m["agent"]["provider"], "anthropic")
            self.assertEqual(m["agent"]["local_vs_cloud"], "cloud")
            self.assertIsNone(m["agent"]["runtime_base_url"])   # empty string normalizes to null
            self.assertEqual(m["agent"]["notes"], "test run")

            # Environment auto-populated
            for key in ("host", "os", "python", "arch"):
                self.assertIn(key, m["environment"])
                self.assertIsInstance(m["environment"][key], str)

            # Hardware: cpu_cores always populated; gpu from CLI
            self.assertIsInstance(m["hardware"]["cpu_cores"], int)
            self.assertEqual(m["hardware"]["gpu"], "none")

            # Counts start at zero
            self.assertEqual(m["counts"], {"total": 1, "passed": 0, "failed": 0, "error": 0})
            self.assertEqual(m["notes"], "first smoke")

    def test_manifest_defaults_when_flags_omitted(self):
        with tempfile.TemporaryDirectory() as td:
            r = run("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            self.assertEqual(r.returncode, 0, r.stderr)
            m = json.loads((next(Path(td).iterdir()) / "manifest.json").read_text())
            self.assertEqual(m["agent"]["frontend"], "")
            self.assertEqual(m["agent"]["model"], "")
            self.assertEqual(m["agent"]["provider"], "")
            self.assertEqual(m["agent"]["local_vs_cloud"], "unknown")
            self.assertIsNone(m["agent"]["runtime_base_url"])
            self.assertEqual(m["agent"]["notes"], "")
            self.assertEqual(m["notes"], "")
            self.assertIsNone(m["hardware"]["gpu"])

    def test_fixture_gets_copied_for_ro_001(self):
        with tempfile.TemporaryDirectory() as td:
            r = run("--label", "x", "--cases", "RO-001", "--runs-dir", td)
            self.assertEqual(r.returncode, 0, r.stderr)
            d = next(Path(td).iterdir())
            workdir = d / "cases" / "RO-001" / "workdir"
            self.assertTrue((workdir / "routes-php" / "routes" / "web.php").exists())

    def test_no_fixture_case_has_empty_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            r = run("--label", "x", "--cases", "SMK-001", "--runs-dir", td)
            self.assertEqual(r.returncode, 0, r.stderr)
            d = next(Path(td).iterdir())
            baseline = json.loads((d / "cases" / "SMK-001" / "workdir" / ".bench" / "baseline.json").read_text())
            self.assertEqual(baseline["files"], {})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `python3 -m unittest tests.test_new_run_script -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `scripts/new_run.py`**

```python
"""Scaffold a new run directory for manual case execution."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from bench import baseline, loader, runs


REPO_ROOT = Path(__file__).resolve().parent.parent


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="new_run", description="Scaffold a run directory.")
    p.add_argument("--label", required=True)
    p.add_argument("--suite", default=None)
    p.add_argument("--cases", default=None, help="Comma-separated case IDs (overrides --suite).")
    p.add_argument("--runs-dir", default=str(REPO_ROOT / "runs"))
    p.add_argument("--cases-dir", default=str(REPO_ROOT / "cases"))
    p.add_argument("--fixtures-dir", default=str(REPO_ROOT / "fixtures"))

    # Agent metadata (all optional; defaults preserve key presence with empty/null values)
    p.add_argument("--frontend", default="", help="Agent tool name: claude-code, codex, cursor, aider, ollama-cli, ...")
    p.add_argument("--model", default="", help="Model identifier string.")
    p.add_argument("--provider", default="", help="Vendor/engine name: anthropic, openai, ollama, vllm, ...")
    p.add_argument("--local-or-cloud", default="unknown", choices=["local", "cloud", "unknown"])
    p.add_argument("--runtime-base-url", default="", help="Non-empty for local servers or custom proxies.")
    p.add_argument("--agent-notes", default="", help="Freeform note attached to the agent block.")

    # Run-level metadata
    p.add_argument("--notes", default="", help="Freeform run-level note.")
    p.add_argument("--gpu", default=None, help="GPU description; stored as null if omitted.")
    return p.parse_args()


def _load_all_cases(cases_dir: Path) -> list[dict]:
    out = []
    for path in runs.list_cases(cases_dir):
        out.append(loader.load_case(path))
    return out


def _scaffold_case(case: dict, case_dir: Path, fixtures_dir: Path) -> None:
    workdir = case_dir / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case.json").write_text(json.dumps(case, indent=2))

    fixture = case.get("fixture")
    if fixture:
        src = fixtures_dir / fixture
        dst = workdir / Path(fixture).name
        if not src.exists():
            raise SystemExit(f"fixture not found: {src}")
        shutil.copytree(src, dst)

    baseline.capture(workdir)
    (workdir / baseline.SIDECAR_DIRNAME / baseline.ALLOWED_PATHS_FILENAME).write_text(
        json.dumps(case.get("allowed_paths", []), indent=2)
    )


def _build_manifest(args: argparse.Namespace, run_dir: Path, case_ids: list[str]) -> dict:
    now_iso = runs.utc_now_iso()
    base_url = args.runtime_base_url.strip() or None
    return {
        "schema_version": 1,
        "run_id":      run_dir.name,
        "timestamp":   now_iso,
        "started_at":  now_iso,
        "finished_at": None,
        "label":       args.label,
        "suite":       args.suite,
        "cases":       case_ids,
        "agent": {
            "frontend":         args.frontend,
            "model":            args.model,
            "provider":         args.provider,
            "local_vs_cloud":   args.local_or_cloud,
            "runtime_base_url": base_url,
            "notes":            args.agent_notes,
        },
        "environment": runs.collect_environment(),
        "hardware":    runs.collect_hardware(gpu=args.gpu),
        "counts":      {"total": len(case_ids), "passed": 0, "failed": 0, "error": 0},
        "notes":       args.notes,
    }


def main() -> int:
    args = _parse_args()
    cases_dir = Path(args.cases_dir)
    fixtures_dir = Path(args.fixtures_dir)
    runs_dir = Path(args.runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)

    explicit = [c.strip() for c in args.cases.split(",")] if args.cases else None
    all_cases = _load_all_cases(cases_dir)
    selected = runs.filter_by_suite(all_cases, suite=args.suite, explicit_ids=explicit)
    if not selected:
        raise SystemExit("no cases matched the selection")

    now = datetime.now(timezone.utc)
    run_dir = runs.new_run_dir(runs_dir, args.label, now=now)
    case_ids = [c["id"] for c in selected]

    runs.write_manifest(run_dir, _build_manifest(args, run_dir, case_ids))

    for case in selected:
        case_dir = run_dir / "cases" / case["id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        _scaffold_case(case, case_dir, fixtures_dir)

    print(str(run_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `python3 -m unittest tests.test_new_run_script -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/new_run.py tests/test_new_run_script.py
git commit -m "feat(scripts): add new_run.py that scaffolds a run dir with baseline"
```

---

### Task 16: Script `validate.py`

**Files:**
- Create: `scripts/validate.py`
- Test: `tests/test_validate_script.py`

Responsibilities (spec §9 + §10):

1. Parse `--run <run_dir>`.
2. Read manifest.
3. For each case id: load `cases/<id>/case.json`; run the declared validator (via `REGISTRY[case["validator"]["type"]]`) and always-on `allowed_paths_check`; determine status.
4. For each case, write three artifacts next to `result.json`:
   - `changes.json` — machine-readable diff summary (spec §9.3).
   - `changes.diff` — unified-diff text vs fixture source (spec §9.4); empty file if no textual changes.
   - `result.json` — full per-case result per spec §9.2, including `artifacts` references, `duration_ms`, and `latency_ms: null`.
5. Update manifest: `counts`, and set `finished_at = runs.utc_now_iso()`.
6. Exit 0 iff every case `status == "pass"`; else exit 1.

Validator dispatch via a registry dict in `validators/__init__.py`.

- [ ] **Step 1: Update `validators/__init__.py` with a registry**

Replace the empty `validators/__init__.py` with:

```python
"""Validator registry: name -> module exposing validate(case, workdir)."""
from . import exact_text, json_file, keys_present, file_exists, allowed_paths_check

REGISTRY = {
    "exact_text": exact_text,
    "json_file": json_file,
    "keys_present": keys_present,
    "file_exists": file_exists,
}

ALWAYS_ON = allowed_paths_check  # runs for every case in addition to the declared validator
```

- [ ] **Step 2: Write a failing end-to-end test**

Create `tests/test_validate_script.py`:

```python
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run_new(*args) -> Path:
    r = subprocess.run(
        [sys.executable, "-m", "scripts.new_run", *args],
        cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    return Path(r.stdout.strip())


def run_validate(run_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "scripts.validate", "--run", str(run_dir)],
        cwd=REPO, capture_output=True, text=True,
    )


class TestValidateScript(unittest.TestCase):
    def test_pass_case_smk_001(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")

            r = run_validate(run_dir)
            self.assertEqual(r.returncode, 0, r.stderr)
            result = json.loads((run_dir / "cases" / "SMK-001" / "result.json").read_text())
            self.assertEqual(result["status"], "pass")
            self.assertTrue(result["allowed_paths_check"]["ok"])

    def test_fail_case_when_content_wrong(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"WRONG")

            r = run_validate(run_dir)
            self.assertEqual(r.returncode, 1)
            result = json.loads((run_dir / "cases" / "SMK-001" / "result.json").read_text())
            self.assertEqual(result["status"], "fail")

    def test_fail_on_scope_violation(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")
            (workdir / "rogue.txt").write_text("nope")

            r = run_validate(run_dir)
            self.assertEqual(r.returncode, 1)
            result = json.loads((run_dir / "cases" / "SMK-001" / "result.json").read_text())
            self.assertEqual(result["status"], "fail")
            self.assertFalse(result["allowed_paths_check"]["ok"])

    def test_manifest_counts_and_finished_at_updated(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")

            run_validate(run_dir)
            m = json.loads((run_dir / "manifest.json").read_text())
            self.assertEqual(m["counts"], {"total": 1, "passed": 1, "failed": 0, "error": 0})
            self.assertIsNotNone(m["finished_at"])

    def test_result_has_artifacts_and_latency(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")

            run_validate(run_dir)
            result = json.loads((run_dir / "cases" / "SMK-001" / "result.json").read_text())
            self.assertIn("latency_ms", result)
            self.assertIsNone(result["latency_ms"])
            artifacts = result["artifacts"]
            self.assertEqual(artifacts["case_snapshot"], "cases/SMK-001/case.json")
            self.assertEqual(artifacts["workdir"],       "cases/SMK-001/workdir")
            self.assertEqual(artifacts["changes_json"],  "cases/SMK-001/changes.json")
            self.assertEqual(artifacts["changes_diff"],  "cases/SMK-001/changes.diff")
            self.assertEqual(artifacts["transcript"],    "cases/SMK-001/transcript.txt")

    def test_changes_json_written(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")

            run_validate(run_dir)
            changes = json.loads((run_dir / "cases" / "SMK-001" / "changes.json").read_text())
            self.assertEqual(changes["created"], ["out/banner.txt"])
            self.assertEqual(changes["modified"], [])
            self.assertEqual(changes["deleted"], [])

    def test_changes_diff_written_for_new_text_file(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")

            run_validate(run_dir)
            diff_text = (run_dir / "cases" / "SMK-001" / "changes.diff").read_text()
            self.assertIn("HELLO-BENCHMARK-V1", diff_text)
            self.assertIn("+++ ", diff_text)

    def test_changes_diff_present_even_on_scope_violation(self):
        # The artifact must exist regardless of pass/fail so downstream analysis is uniform.
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "u", "--cases", "SMK-001", "--runs-dir", td)
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")
            (workdir / "rogue.txt").write_text("nope\n")
            run_validate(run_dir)
            self.assertTrue((run_dir / "cases" / "SMK-001" / "changes.diff").exists())
            self.assertTrue((run_dir / "cases" / "SMK-001" / "changes.json").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the test and confirm it fails**

Run: `python3 -m unittest tests.test_validate_script -v`
Expected: FAIL — `scripts.validate` missing.

- [ ] **Step 4: Implement `scripts/validate.py`**

```python
"""Run validators over a scaffolded run directory and record per-case results + artifacts."""
from __future__ import annotations

import argparse
import difflib
import json
import time
from pathlib import Path

from bench import baseline, runs
from validators import ALWAYS_ON, REGISTRY


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR_DEFAULT = REPO_ROOT / "fixtures"


def _status_from(declared: dict, apc: dict) -> str:
    all_ok = declared.get("ok", False) and apc.get("ok", False)
    if all_ok:
        return "pass"
    if not declared.get("ok") and "raised" in declared.get("detail", ""):
        return "error"
    return "fail"


def _compute_changes(workdir: Path) -> dict:
    """Return the spec §9.3 summary for this workdir."""
    sidecar = workdir / baseline.SIDECAR_DIRNAME / baseline.BASELINE_FILENAME
    base_files = json.loads(sidecar.read_text())["files"] if sidecar.exists() else {}
    current = baseline.walk(workdir)
    d = baseline.diff(base_files, current)
    return {
        "created":         d["created"],
        "modified":        d["modified"],
        "deleted":         d["deleted"],
        "unchanged_count": len(d["unchanged"]),
        "unsupported":     d["unsupported"],
    }


def _read_text_or_none(path: Path) -> list[str] | None:
    """Return splitlines(keepends=True) or None if the file is binary / missing."""
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines(keepends=True)
    except (UnicodeDecodeError, OSError):
        return None


def _write_changes_diff(workdir: Path, case: dict, changes: dict, out_path: Path,
                        fixtures_dir: Path) -> None:
    """Emit a unified diff of text changes. Always writes, even if empty."""
    fixture = case.get("fixture")
    fixture_basename = Path(fixture).name if fixture else None
    buf: list[str] = []

    def _diff(before: list[str] | None, after: list[str] | None, label_from: str, label_to: str) -> None:
        if before is None or after is None:
            buf.append(f"# skipped binary: {label_to or label_from}\n")
            return
        for line in difflib.unified_diff(before, after, fromfile=label_from, tofile=label_to):
            buf.append(line)

    def _fixture_source(rel: str) -> Path | None:
        if fixture_basename and rel.startswith(fixture_basename + "/"):
            inner = rel[len(fixture_basename) + 1:]
            return fixtures_dir / fixture / inner
        return None

    for rel in changes["created"]:
        after = _read_text_or_none(workdir / rel)
        _diff([], after, "/dev/null", f"workdir/{rel}")

    for rel in changes["modified"]:
        src = _fixture_source(rel)
        before = _read_text_or_none(src) if src else []
        after = _read_text_or_none(workdir / rel)
        _diff(before, after,
              f"fixture/{rel}" if src else "/dev/null",
              f"workdir/{rel}")

    for rel in changes["deleted"]:
        src = _fixture_source(rel)
        before = _read_text_or_none(src) if src else []
        _diff(before, [], f"fixture/{rel}" if src else "/dev/null", "/dev/null")

    out_path.write_text("".join(buf))


def _artifact_refs(run_dir: Path, case_dir: Path) -> dict:
    def rel(p: Path) -> str:
        return p.relative_to(run_dir).as_posix()
    return {
        "case_snapshot": rel(case_dir / runs.CASE_SNAPSHOT_NAME),
        "workdir":       rel(case_dir / "workdir"),
        "changes_json":  rel(case_dir / "changes.json"),
        "changes_diff":  rel(case_dir / "changes.diff"),
        "transcript":    rel(case_dir / "transcript.txt"),
    }


def _validate_one(case: dict, workdir: Path) -> tuple[dict, dict]:
    t0 = time.monotonic()
    validator_type = case["validator"]["type"]
    validator_mod = REGISTRY.get(validator_type)
    try:
        if validator_mod is None:
            declared = {"type": validator_type, "ok": False,
                        "detail": f"unknown validator type: {validator_type}"}
        else:
            declared = validator_mod.validate(case, workdir)
    except Exception as e:
        declared = {"type": validator_type, "ok": False,
                    "detail": f"validator raised: {e!r}"}

    try:
        apc = ALWAYS_ON.validate(case, workdir)
    except Exception as e:
        apc = {
            "type": "allowed_paths_check", "ok": False,
            "detail": f"apc raised: {e!r}",
            "violations": [],
            "counts": {"created": 0, "modified": 0, "deleted": 0, "unchanged": 0},
        }

    duration_ms = int((time.monotonic() - t0) * 1000)
    partial = {
        "validators": [declared],
        "allowed_paths_check": {
            "ok":         apc["ok"],
            "violations": apc.get("violations", []),
            "counts":     apc.get("counts", {}),
        },
        "status": _status_from(declared, apc),
        "duration_ms": duration_ms,
    }
    return partial, apc


def main() -> int:
    p = argparse.ArgumentParser(prog="validate")
    p.add_argument("--run", required=True)
    p.add_argument("--fixtures-dir", default=str(FIXTURES_DIR_DEFAULT))
    args = p.parse_args()

    run_dir = Path(args.run).resolve()
    fixtures_dir = Path(args.fixtures_dir)
    manifest = runs.read_manifest(run_dir)
    counts = {"total": 0, "passed": 0, "failed": 0, "error": 0}

    for case_id in manifest["cases"]:
        case_dir = run_dir / "cases" / case_id
        case = json.loads((case_dir / runs.CASE_SNAPSHOT_NAME).read_text())
        workdir = case_dir / "workdir"

        partial, _ = _validate_one(case, workdir)

        changes = _compute_changes(workdir)
        (case_dir / "changes.json").write_text(json.dumps(changes, indent=2))
        _write_changes_diff(workdir, case, changes, case_dir / "changes.diff", fixtures_dir)

        result = {
            "schema_version": 1,
            "case_id":        case["id"],
            "status":         partial["status"],
            "validators":     partial["validators"],
            "allowed_paths_check": partial["allowed_paths_check"],
            "duration_ms":    partial["duration_ms"],
            "latency_ms":     None,
            "artifacts":      _artifact_refs(run_dir, case_dir),
            "notes":          "",
        }
        runs.write_result(case_dir, result)

        counts["total"] += 1
        counts[{"pass": "passed", "fail": "failed",
                "error": "error", "skipped": "error"}[result["status"]]] += 1

    manifest["counts"] = counts
    manifest["finished_at"] = runs.utc_now_iso()
    runs.write_manifest(run_dir, manifest)

    return 0 if counts["total"] == counts["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the test and confirm it passes**

Run: `python3 -m unittest tests.test_validate_script -v`
Expected: PASS (8 tests).

- [ ] **Step 6: Commit**

```bash
git add scripts/validate.py validators/__init__.py tests/test_validate_script.py
git commit -m "feat(scripts): add validate.py that runs declared validators + allowed_paths_check"
```

---

### Task 17: Script `summarize.py`

**Files:**
- Create: `scripts/summarize.py`
- Test: `tests/test_summarize.py`

Reads `manifest.json` + each case's `result.json`. Writes `summary.md` with a fixed-shape table + footer.

- [ ] **Step 1: Write a failing test**

Create `tests/test_summarize.py`:

```python
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run_new(*args) -> Path:
    r = subprocess.run([sys.executable, "-m", "scripts.new_run", *args],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return Path(r.stdout.strip())


def run_validate(run_dir: Path) -> None:
    subprocess.run([sys.executable, "-m", "scripts.validate", "--run", str(run_dir)],
                   cwd=REPO, capture_output=True, text=True)


def run_summarize(run_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "scripts.summarize", "--run", str(run_dir)],
                          cwd=REPO, capture_output=True, text=True)


class TestSummarize(unittest.TestCase):
    def test_summary_header_and_table(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = run_new("--label", "s", "--cases", "SMK-001", "--runs-dir", td,
                              "--frontend", "claude-code",
                              "--model", "claude-opus-4-7",
                              "--provider", "anthropic",
                              "--local-or-cloud", "cloud")
            workdir = run_dir / "cases" / "SMK-001" / "workdir"
            (workdir / "out").mkdir()
            (workdir / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")
            run_validate(run_dir)

            r = run_summarize(run_dir)
            self.assertEqual(r.returncode, 0, r.stderr)
            text = (run_dir / "summary.md").read_text()

            # Case table header and row
            self.assertIn("| case | status | declared validator | allowed_paths | latency_ms | notes |", text)
            self.assertIn("| SMK-001 | pass | exact_text |", text)

            # Agent block
            self.assertIn("## Agent", text)
            self.assertIn("frontend: claude-code", text)
            self.assertIn("model: claude-opus-4-7", text)
            self.assertIn("provider: anthropic", text)
            self.assertIn("local_vs_cloud: cloud", text)

            # Environment block
            self.assertIn("## Environment", text)
            self.assertIn("host:", text)
            self.assertIn("python:", text)

            self.assertIn("Totals:", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `python3 -m unittest tests.test_summarize -v`
Expected: FAIL — script missing.

- [ ] **Step 3: Implement `scripts/summarize.py`**

```python
"""Emit summary.md from manifest.json + per-case result.json files (spec §9.5)."""
from __future__ import annotations

import argparse
from pathlib import Path

from bench import runs


TABLE_HEADER = "| case | status | declared validator | allowed_paths | latency_ms | notes |"
TABLE_SEP    = "|------|--------|--------------------|----------------|------------|-------|"


def _row(case_id: str, result: dict) -> str:
    validators = result.get("validators") or []
    declared = validators[0] if validators else {"type": ""}
    apc = result.get("allowed_paths_check", {})
    apc_cell = "ok" if apc.get("ok") else f"{len(apc.get('violations', []))} violation(s)"
    latency = result.get("latency_ms")
    latency_cell = "-" if latency is None else str(latency)
    notes = (result.get("notes") or "").replace("|", "\\|")
    return (f"| {case_id} | {result.get('status','?')} | {declared.get('type','')} | "
            f"{apc_cell} | {latency_cell} | {notes} |")


def _header_block(manifest: dict) -> list[str]:
    return [
        f"# Run {manifest['run_id']}",
        "",
        f"- timestamp: {manifest.get('timestamp') or '-'}",
        f"- started_at: {manifest.get('started_at') or '-'}",
        f"- finished_at: {manifest.get('finished_at') or '-'}",
        f"- label: {manifest.get('label','')}",
        f"- suite: {manifest.get('suite') or '-'}",
    ]


def _agent_block(agent: dict) -> list[str]:
    return [
        "",
        "## Agent",
        "",
        f"- frontend: {agent.get('frontend','')}",
        f"- model: {agent.get('model','')}",
        f"- provider: {agent.get('provider','')}",
        f"- local_vs_cloud: {agent.get('local_vs_cloud','')}",
        f"- runtime_base_url: {agent.get('runtime_base_url') or '-'}",
        f"- notes: {agent.get('notes','')}",
    ]


def _environment_block(env: dict, hw: dict) -> list[str]:
    return [
        "",
        "## Environment",
        "",
        f"- host: {env.get('host','')}",
        f"- os: {env.get('os','')}",
        f"- python: {env.get('python','')}",
        f"- arch: {env.get('arch','')}",
        f"- cpu_cores: {hw.get('cpu_cores')}",
        f"- memory_gb: {hw.get('memory_gb')}",
        f"- gpu: {hw.get('gpu') or '-'}",
    ]


def _table_block(run_dir: Path, manifest: dict) -> list[str]:
    lines = ["", "## Cases", "", TABLE_HEADER, TABLE_SEP]
    for case_id in manifest["cases"]:
        result = runs.read_result(run_dir / "cases" / case_id)
        lines.append(_row(case_id, result))
    return lines


def _footer_block(manifest: dict) -> list[str]:
    c = manifest["counts"]
    return [
        "",
        f"Totals: total={c['total']} passed={c['passed']} failed={c['failed']} error={c['error']}",
        f"Notes: {manifest.get('notes','') or '-'}",
    ]


def main() -> int:
    p = argparse.ArgumentParser(prog="summarize")
    p.add_argument("--run", required=True)
    args = p.parse_args()

    run_dir = Path(args.run).resolve()
    manifest = runs.read_manifest(run_dir)

    lines: list[str] = []
    lines += _header_block(manifest)
    lines += _agent_block(manifest.get("agent", {}))
    lines += _environment_block(manifest.get("environment", {}), manifest.get("hardware", {}))
    lines += _table_block(run_dir, manifest)
    lines += _footer_block(manifest)

    (run_dir / "summary.md").write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `python3 -m unittest tests.test_summarize -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/summarize.py tests/test_summarize.py
git commit -m "feat(scripts): add summarize.py producing summary.md table"
```

---

### Task 18: Script `compare.py` stub

**Files:**
- Create: `scripts/compare.py`
- Test: `tests/test_compare_stub.py`

v1 ships a `--help` stub only (spec §10, §12). Calling it with anything other than `--help` exits 2 with a clear "deferred to v1.1" message.

- [ ] **Step 1: Write failing test**

Create `tests/test_compare_stub.py`:

```python
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class TestCompareStub(unittest.TestCase):
    def test_help_works(self):
        r = subprocess.run([sys.executable, "-m", "scripts.compare", "--help"],
                           cwd=REPO, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("deferred to v1.1", r.stdout + r.stderr)

    def test_invocation_exits_nonzero(self):
        r = subprocess.run([sys.executable, "-m", "scripts.compare", "--a", "x", "--b", "y"],
                           cwd=REPO, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `python3 -m unittest tests.test_compare_stub -v`
Expected: FAIL.

- [ ] **Step 3: Implement `scripts/compare.py`**

```python
"""Compare two runs. Deferred to v1.1 — this is a --help stub."""
from __future__ import annotations

import argparse


STUB_MSG = (
    "scripts/compare.py is a stub in v1 — the actual diff view is deferred to v1.1.\n"
    "See docs/plans/v1-design.md §10 and §12."
)


def main() -> int:
    p = argparse.ArgumentParser(prog="compare", description=STUB_MSG)
    p.add_argument("--a", help="first run directory (not implemented in v1)")
    p.add_argument("--b", help="second run directory (not implemented in v1)")
    args = p.parse_args()

    if args.a or args.b:
        print(STUB_MSG)
        return 2

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `python3 -m unittest tests.test_compare_stub -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/compare.py tests/test_compare_stub.py
git commit -m "feat(scripts): add compare.py stub (deferred to v1.1)"
```

---

### Task 19: Docs pages

**Files:**
- Create: `docs/methodology.md`
- Create: `docs/case-authoring.md`
- Create: `docs/running.md`

Each is short. No tests; verify via a content spot-check.

- [ ] **Step 1: Create `docs/methodology.md`**

```markdown
# Methodology

`playground-agent-benchmark` is a practical, non-scientific playground for comparing agent behavior across a small, fixed set of deterministic cases. It is not a leaderboard.

## What v1 measures

- **Instruction discipline** — does the agent follow exact-output rules (SMK-001)?
- **Structured output** — does the agent emit valid, schema-respecting JSON (STR-001)?
- **Bounded reading** — can the agent extract structured data from a small fixture without touching it (RO-001)?
- **Scope discipline** — does the agent edit only what it is told to (EDT-002)?

## What v1 does NOT measure

Correctness under realistic load, latency, token cost, multi-turn reasoning, browser use, larger-project navigation. All explicitly deferred.

## Validation stance

All checks are objective and deterministic:
- byte-for-byte file comparison
- JSON parse validity
- key/type/regex/enum constraints
- presence/absence of files, substrings
- allowed-path scope discipline (always-on)

No model-graded scoring. No test execution inside fixtures (v1.1).

## Result interpretation

A pass/fail result on a v1 case tells you whether the agent followed the narrow contract of that case. Generalizations beyond that (e.g., "model X is better at refactors") need more cases than v1 ships.

## Known limitations (v1)

- **Unreadable workdir files abort validation.** If a file inside `workdir/` becomes unreadable (permissions, deleted-while-walking) between `new_run.py` and `validate.py`, the baseline walk raises `PermissionError` and the run errors out. Acceptable because workdirs are operator-controlled; no retry, no partial scoring.
- **`__unsupported__` is an internal marker.** Downstream code (including `allowed_paths_check`) keys off the `unsupported` bucket returned by `bench.baseline.diff`, not the string sentinel. Do not introspect it.
- **Symlinks and non-regular files** inside `workdir/` are always flagged as violations. v1 does not support symlinked outputs.
```

- [ ] **Step 2: Create `docs/case-authoring.md`**

```markdown
# Authoring a case

## File location

`cases/<suite>/<id>.json`, where `<id>` matches `^[A-Z]+-\d{3}$` (e.g. `SMK-001`, `EDT-007`).

## Required fields

See `schemas/case.schema.json`. Every v1 case must declare `schema_version: 1` and the full field set listed there.

## `mode` values

- `read-only` — agent reads the fixture copy; `allowed_paths` should cover only output artifacts.
- `plan-only` — same as read-only, but the output is a plan document.
- `write` — `allowed_paths` may include fixture-internal paths the agent should edit.

`mode` is documentary; enforcement is via `allowed_paths` + the always-on `allowed_paths_check`.

## `allowed_paths` syntax

Paths are relative to the case `workdir/`. Three forms:
- exact: `"out/banner.txt"`
- directory (trailing `/`): `"out/"` — matches any descendant at any depth
- single-segment glob: `"out/*.json"` — `*` and `?` match within one path segment only

Recursive `**` is **not supported** in v1, and using it is misleading: under the current matcher it collapses to a single-segment wildcard that cannot cross `/`. For recursive allowance, always use the directory form (`some/dir/`) instead.

## Case-insensitive filesystems

Path matching is byte-for-byte. Authors on macOS or Windows should not rely on filesystem case-folding.

## Validator args — v1 conventions

- Each validator reads its args from `case.validator.args`. Authoritative arg lists live in the validator modules under `validators/`.
- Unknown args are currently **silently ignored** (v1 convenience). Don't lean on this — post-v1 we may reject unknown args.
- **`exact_text` arg interaction worth calling out:** `strip=True` runs before the trailing-newline check, so `strip=True` + `trailing_newline=false` will accept files that end in whitespace or a newline (the strip eats them first). If you want strict "no trailing newline, and no surrounding whitespace either," leave `strip=false` (the default) and rely on the trailing-newline rule alone.
- **`json_file` is intentionally permissive about top-level type.** It accepts any valid JSON value — object, array, number, string, `true`/`false`/`null`. Shape policing (e.g. "top level must be an object with keys X, Y, Z") belongs to `keys_present`, not here.
- **`keys_present` tolerates extra keys.** Listing `required: ["name", "version"]` does NOT reject a JSON file that contains `{"name": "x", "version": "1.0.0", "surprise": true}`. v1 has no `additionalProperties: false` equivalent. If you need strict object shape, phrase the prompt precisely and accept that an "unexpected extra key" will currently not fail the case. v1 will not grow this validator further; if strict shape becomes necessary, we'll graduate to a real jsonschema dependency.

## Changing an existing case

If a change alters case meaning — the prompt, the expected output, the validator args — bump `schema_version`. This makes benchmark drift explicit and keeps historical runs re-scorable against their own snapshot.
```

- [ ] **Step 3: Create `docs/running.md`**

```markdown
# Running cases

v1 has no execution harness. The loop is manual:

## 1. Scaffold a run

```bash
python3 -m scripts.new_run \
  --label my-agent --suite smoke \
  --frontend claude-code --model claude-opus-4-7 --provider anthropic \
  --local-or-cloud cloud --notes "first smoke pass"
```

This prints the new run directory, e.g. `runs/20260421-180000-my-agent/`.

Required: `--label`. Everything else is optional but worth populating so the run is self-describing for later comparison.

Selection flags:
- `--cases SMK-001,RO-001` — explicit case list (overrides `--suite`).
- `--runs-dir some/path` — use a different runs root (useful in tests).

Agent metadata flags (all optional, populate the manifest for retrospective analysis):
- `--frontend` — tool name: `claude-code`, `codex`, `cursor`, `aider`, `ollama-cli`, ...
- `--model` — model identifier string.
- `--provider` — vendor/engine: `anthropic`, `openai`, `ollama`, `vllm`, ...
- `--local-or-cloud` — one of `local`, `cloud`, `unknown` (default `unknown`).
- `--runtime-base-url` — for local servers or custom proxies (e.g. `http://localhost:11434`).
- `--agent-notes` — freeform note attached to the agent block.
- `--notes` — freeform run-level note.
- `--gpu` — GPU description; stored under `hardware.gpu` (otherwise `null`).

`environment.{host, os, python, arch}` and `hardware.{cpu_cores, memory_gb}` are auto-collected.

Each case gets `runs/<run>/cases/<id>/workdir/` with the fixture copy (if any) and a `.bench/` sidecar containing `baseline.json` + `allowed_paths.json`.

## 2. Run the case against your agent

Feed `case.json` (or its `prompt` field) to your agent of choice. Whatever tool you use, the agent must place its outputs into the case's `workdir/`. Paths in the case's `allowed_paths` list are the only ones allowed.

## 3. Validate

```bash
python3 -m scripts.validate --run runs/20260421-180000-my-agent
```

Writes three artifacts per case — `result.json`, `changes.json`, `changes.diff` — and updates `manifest.json` (`counts`, `finished_at`). Exits `0` iff every case passed.

## 4. Summarize

```bash
python3 -m scripts.summarize --run runs/20260421-180000-my-agent
```

Writes `summary.md` — a one-page table plus run metadata.

## 5. Compare two runs (v1.1)

Deferred. `scripts/compare.py --help` describes the planned shape.

## Tests

```bash
python3 -m unittest discover -s tests -v
```
```

- [ ] **Step 4: Spot-check docs content**

Run:

```bash
python3 -c "
from pathlib import Path
for name in ['methodology.md', 'case-authoring.md', 'running.md']:
    assert (Path('docs') / name).read_text().count('\n') > 10, name
print('ok')
"
```

Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add docs/methodology.md docs/case-authoring.md docs/running.md
git commit -m "docs: add methodology, case-authoring, running pages"
```

---

### Task 20: End-to-end smoke + final checks

**Files:**
- Create: `tests/test_e2e_smoke.py`

End-to-end: scaffold → place canned outputs for all 4 v1 cases → validate → summarize → assert pass/fail markers in `summary.md`. This exercises the full v1 slice as a single integrated check.

- [ ] **Step 1: Write the end-to-end test**

Create `tests/test_e2e_smoke.py`:

```python
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def new_run(td: str, *flags) -> Path:
    r = subprocess.run([sys.executable, "-m", "scripts.new_run", "--runs-dir", td, *flags],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return Path(r.stdout.strip())


def validate(run_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "scripts.validate", "--run", str(run_dir)],
                          cwd=REPO, capture_output=True, text=True)


def summarize(run_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "scripts.summarize", "--run", str(run_dir)],
                          cwd=REPO, capture_output=True, text=True)


def populate_all_four_cases_to_pass(run_dir: Path) -> None:
    # SMK-001
    w = run_dir / "cases" / "SMK-001" / "workdir"
    (w / "out").mkdir()
    (w / "out" / "banner.txt").write_bytes(b"HELLO-BENCHMARK-V1")

    # STR-001
    w = run_dir / "cases" / "STR-001" / "workdir"
    (w / "out").mkdir()
    (w / "out" / "summary.json").write_text(json.dumps({
        "name": "playground", "version": "0.1.0", "tags": ["benchmark", "tiny", "demo"]
    }))

    # RO-001
    w = run_dir / "cases" / "RO-001" / "workdir"
    (w / "out").mkdir()
    (w / "out" / "routes.json").write_text(json.dumps([
        {"method": "GET",    "path": "/users",        "handler": "UserController@index"},
        {"method": "GET",    "path": "/users/{id}",   "handler": "UserController@show"},
        {"method": "POST",   "path": "/users",        "handler": "UserController@store"},
        {"method": "PUT",    "path": "/users/{id}",   "handler": "UserController@update"},
        {"method": "DELETE", "path": "/users/{id}",   "handler": "UserController@destroy"},
        {"method": "GET",    "path": "/products",     "handler": "ProductController@index"},
    ]))

    # EDT-002 — edit README.md in place, fixing the typo
    readme = run_dir / "cases" / "EDT-002" / "workdir" / "todo-py" / "README.md"
    readme.write_text(readme.read_text().replace("recieve", "receive"))


class TestE2ESmoke(unittest.TestCase):
    def test_full_v1_pipeline_all_pass(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = new_run(td, "--label", "e2e",
                              "--cases", "SMK-001,STR-001,RO-001,EDT-002",
                              "--frontend", "claude-code",
                              "--model", "claude-opus-4-7",
                              "--provider", "anthropic",
                              "--local-or-cloud", "cloud",
                              "--notes", "e2e smoke")
            populate_all_four_cases_to_pass(run_dir)

            v = validate(run_dir)
            self.assertEqual(v.returncode, 0, v.stderr)

            s = summarize(run_dir)
            self.assertEqual(s.returncode, 0, s.stderr)

            text = (run_dir / "summary.md").read_text()
            for cid in ["SMK-001", "STR-001", "RO-001", "EDT-002"]:
                self.assertIn(f"| {cid} | pass |", text, cid)

            m = json.loads((run_dir / "manifest.json").read_text())
            self.assertEqual(m["counts"], {"total": 4, "passed": 4, "failed": 0, "error": 0})
            self.assertIsNotNone(m["finished_at"])
            self.assertEqual(m["agent"]["frontend"], "claude-code")
            self.assertEqual(m["agent"]["model"], "claude-opus-4-7")
            self.assertIn("python", m["environment"])
            self.assertEqual(m["notes"], "e2e smoke")

            # Every case has artifact references and on-disk artifacts.
            for cid in ["SMK-001", "STR-001", "RO-001", "EDT-002"]:
                case_dir = run_dir / "cases" / cid
                result = json.loads((case_dir / "result.json").read_text())
                self.assertEqual(result["artifacts"]["case_snapshot"], f"cases/{cid}/case.json")
                self.assertIn("latency_ms", result)
                self.assertTrue((case_dir / "changes.json").exists(), cid)
                self.assertTrue((case_dir / "changes.diff").exists(), cid)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run just the e2e test**

Run: `python3 -m unittest tests.test_e2e_smoke -v`
Expected: PASS.

- [ ] **Step 3: Run the full suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: every test passes; no warnings about skipped tests.

- [ ] **Step 4: Sanity-run the scripts against the real `runs/` directory**

```bash
python3 -m scripts.new_run --label demo --suite smoke
# note the path printed
# manually place outputs under workdir/, then:
python3 -m scripts.validate --run runs/<printed-dir>
python3 -m scripts.summarize --run runs/<printed-dir>
cat runs/<printed-dir>/summary.md
```

Expected: runs under `runs/` succeed; summary.md renders. (This dir is gitignored; no commit needed.)

- [ ] **Step 5: Commit the e2e test**

```bash
git add tests/test_e2e_smoke.py
git commit -m "test: end-to-end smoke covering all four v1 cases"
```

- [ ] **Step 6: Push the branch**

```bash
git push -u origin feat/v1-benchmark-core
```

---

## Exit criterion verification

Spec §11 says: *"operator can run all four v1 cases (SMK-001, STR-001, RO-001, EDT-002) against two different agents and produce two `summary.md` files that meaningfully differentiate them."*

Task 20's e2e test proves the mechanical pipeline works. Meaningful differentiation between agents is an operator-side concern that doesn't need code — run the pipeline twice with different labels, diff the two `summary.md` files by eye.

## Coverage trace against spec

| Spec section          | Task(s)              |
|-----------------------|----------------------|
| §2 Dependency stance  | Task 1, 3            |
| §3 Repo structure     | Tasks 1, 2, 4–6, 15  |
| §4 Case format        | Tasks 2, 3, 6        |
| §5 First fixtures     | Tasks 4, 5           |
| §6 First cases        | Task 6               |
| §7 Validators         | Tasks 9, 10, 11, 12, 13 |
| §8 allowed_paths_check| Tasks 7, 8, 13, 15   |
| §9 Run/result format  | Tasks 2, 14, 15, 16  |
| §10 Script surface    | Tasks 15, 16, 17, 18 |
| §11 v1 slice          | All                  |
| §13 Risks             | Schemas in Task 2 (schema_version), snapshot in Task 15 |

## Notes for the executing engineer

- **Testing convention:** all tests use `unittest` and are discoverable via `python3 -m unittest discover -s tests -v`. No third-party runner.
- **Temp dirs:** tests use `tempfile.TemporaryDirectory()` extensively; they never touch the repo's own `runs/` directory by default. Scripts default to `runs/` only when invoked without `--runs-dir`.
- **File modification detection:** sha256 based, via `bench/baseline.py`. Rename shows up as one deleted + one created (intentional; v1 does not track renames).
- **Path separators:** every relative path stored or compared is POSIX-style (`/`). Windows users must normalize before comparing; not a v1 concern.
- **When in doubt, consult:** `docs/plans/v1-design.md`. That document is the authoritative spec. This plan executes it.
