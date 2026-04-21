# playground-agent-benchmark — v1 design

Status: approved for implementation (2026-04-21).
Scope: validator-first v1 slice.

## 1. Goals and non-goals

### Goals

- Author a benchmark case once, run it manually against any agent frontend, score the result deterministically, and eyeball two runs side-by-side.
- Honor `AGENTS.md`: small, explicit, reviewable, no silent benchmark drift, no vendor lock-in.
- Keep the core dependency-free in v1 (Python 3 stdlib only).
- Produce a result format that is easy to diff and extend.

### Non-goals (v1)

- Executing agents automatically. No harness in v1.
- Running tests inside fixtures as part of validation.
- Browser-automation cases.
- Big fixtures.
- Cross-run aggregation, leaderboards, cost/latency tracking.

## 2. Dependency stance

Python 3 stdlib only. No PyYAML, no jsonschema, no pytest dep in the core v1 slice. Case files are JSON so the load path is stdlib `json`.

Tradeoff: JSON prompts lose YAML's block-scalar ergonomics. Mitigations:
- v1 prompts are short (~2–4 lines each); escaped `\n` is acceptable.
- If a prompt outgrows comfortable inline JSON, migrate that case to a sibling `.prompt.md` file and set `"prompt": {"$file": "SMK-001.prompt.md"}`. That migration is trivial and opt-in per case; v1 does **not** ship with it.

## 3. Repository structure

```
fixtures/
  routes-php/                  # routes-only PHP, never executed
  todo-py/                     # ~3-file Python module, no runtime needed in v1
cases/
  smoke/
  structured/
  bounded-edit/
validators/
  __init__.py
  exact_text.py
  json_file.py
  keys_present.py
  file_exists.py
  allowed_paths_check.py
schemas/
  case.schema.json
  run-manifest.schema.json
  case-result.schema.json
runs/                          # gitignored; .gitkeep already in place
scripts/
  new_run.py
  validate.py
  summarize.py
  compare.py                   # --help stub in v1
docs/
  methodology.md
  case-authoring.md
  running.md
  plans/
    v1-design.md               # this document
```

Notes:
- `schemas/` is top-level (authoritative spec, not validator internals).
- No `core/` or `lib/`; too small for an abstraction layer.
- Each fixture owns a short `README.md` describing its shape and what cases use it.

## 4. Case format (JSON)

One JSON file per case at `cases/<suite>/<id>.json`. Every case carries `schema_version: 1` for future migration safety.

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

Field semantics:
- `mode` is documentary metadata describing intent. Actual enforcement is entirely via `allowed_paths` + the always-on `allowed_paths_check`; the loader does not gate behavior on mode. Meanings:
  - `read-only` — agent may read the fixture copy; `allowed_paths` should cover only output artifacts (no fixture paths).
  - `plan-only` — same as `read-only`, but the output artifact is expected to be a plan document, not executable code. Purely a label for humans and reports.
  - `write` — `allowed_paths` may legitimately include fixture-internal paths the agent is expected to edit.
- `fixture` is a path relative to `fixtures/`, or `null`. When non-null, `new_run.py` copies the fixture tree into `workdir/<fixture-basename>/` regardless of mode.
- `allowed_paths` entries are always relative to `workdir/`. Each entry is one of:
  - an exact relative path: `"out/banner.txt"`
  - a directory path ending in `/`: `"out/"` (matches any descendant at any depth — this is the way to express "everything under this tree")
  - a single-segment glob pattern: `"out/*.json"` (matched via stdlib `fnmatch.fnmatchcase`; `*` and `?` match within one segment and do **not** cross `/`)
- Recursive-glob syntax like `**/*.py` is **not** supported in v1. Use a directory entry (`"some/dir/"`) for recursive coverage. This keeps the matcher to stdlib `fnmatch` with no custom walker.
- `validator` is a single object in v1. Schema is forward-compatible with a future `validators: [ ... ]` list; v1 loader accepts only the singular form.

`schemas/case.schema.json` is the source of truth; it is validated in `scripts/validate.py` at case-load time via a hand-written stdlib check (no `jsonschema` dep).

## 5. First fixtures

Two fixtures, both tiny.

- `fixtures/routes-php/` — Laravel-style `routes/web.php` (~30 lines) plus 2–3 stub controller files. Never executed. Used for routes-parsing cases and small route-addition edits.
- `fixtures/todo-py/` — `todo.py` (Todo class + TodoList with `add`, `complete`, `list`), `test_todo.py` (3 pytest tests — not invoked in v1), `README.md` with a deliberate typo for the negative-scope edit case.

Each fixture README states its intended shape and the cases that depend on it. Any change to a fixture that changes case meaning is benchmark drift and must bump `schema_version` on affected cases.

## 6. First cases (v1 ships 4)

1. **SMK-001** — `exact-output`, no fixture, `exact_text`. Write exact banner string to `out/banner.txt`, no trailing newline.
2. **STR-001** — `structured-json`, no fixture, `json_file` + `keys_present`. Write `out/summary.json` with `{name, version, tags}` where `tags` is a 3-element list of strings matching `^[a-z][a-z0-9-]*$`.
3. **RO-001** — `read-only-understanding`, `routes-php`, `json_file` + `keys_present`. "List every route in the fixture as a JSON array of `{method, path, handler}` at `out/routes.json`." Mode: `read-only`.
4. **EDT-002** — `bounded-edit-negative`, `todo-py`, `file_exists` + `allowed_paths_check`. "Fix the typo in `README.md`. Do not edit any `.py` files." Validator confirms `README.md` changed and no `.py` file touched.

Deferred to v1.1: **PLN-001** (plan-only planning task) and **EDT-001** (positive bounded edit with structural check → later `test_pass`).

v1 cases exercise two validators per case max. Only one validator is declared in each case's `validator` field; the always-on `allowed_paths_check` is the implicit second check everywhere.

Suites are expressed via `tags`:
- `smoke`: SMK-001, STR-001
- `structured-output`: STR-001, RO-001
- `bounded-edit`: EDT-002

## 7. Validators

Five modules, all stdlib Python. Each exposes:

```python
def validate(case: dict, workdir: Path) -> ValidatorResult
```

`ValidatorResult` is a dataclass serializable to:

```json
{ "ok": true, "detail": "…", "observed": "…", "expected": "…" }
```

- **`exact_text`** — byte-compare a file. Args: `path`, `expect`, `trailing_newline: bool = true`, `strip: bool = false`.
- **`json_file`** — file at `path` exists and parses as JSON. Returns parsed value in `observed` for reuse.
- **`keys_present`** — lightweight schema check against a parsed JSON value. Args: `required: [keys]`, optional `constraints: {key: {type?, regex?, enum?, len?}}`. No `jsonschema` dep.
- **`file_exists`** — path presence/absence. Args: `path`, `exists: bool`. Supports globs via `fnmatch`.
- **`allowed_paths_check`** — always-on, not user-specified. See §8 for full design.

Case pass ⇔ declared validator `ok: true` **and** `allowed_paths_check.ok`.

## 8. `allowed_paths_check` — tightened design

Goal: detect any `created`, `modified`, or `deleted` file inside the case's `workdir/` whose path is not covered by `allowed_paths`, without flagging untouched fixture files or per-run scoring artifacts.

### 8.1 Baseline capture (at `new_run.py` time)

When a run is scaffolded, for each case `new_run.py`:

1. Creates `runs/<run>/cases/<id>/workdir/`.
2. If `case.fixture` is non-null, copies the fixture tree to `workdir/<fixture-basename>/`. For write-mode cases this gives the agent a working copy.
3. Walks `workdir/` excluding `workdir/.bench/`, computes sha256 + byte size per file, and writes:

   ```
   workdir/.bench/baseline.json
   ```

   Shape:

   ```json
   {
     "captured_at": "2026-04-21T18:00:00Z",
     "files": {
       "todo-py/todo.py":   { "sha256": "…", "size": 123 },
       "todo-py/test_todo.py": { "sha256": "…", "size": 456 }
     }
   }
   ```

   For no-fixture cases, `files` is `{}`.

4. Writes `workdir/.bench/allowed_paths.json` — a copy of the case's `allowed_paths` so validation is reproducible from `workdir` alone.

`workdir/.bench/` is the sidecar and is **never** compared, traversed, or flagged. Agents are told not to write inside it; if they do, that's a validator-enforced violation via path matching (see §8.3).

### 8.2 Create-vs-modify detection (at `scripts/validate.py` time)

1. Load `workdir/.bench/baseline.json` into `baseline`.
2. Walk `workdir/` excluding `workdir/.bench/`. Compute `current: {relpath: sha256}` for every regular file.
3. Classify every path observed in `baseline ∪ current`:
   - in `current` only → `created`
   - in both, hashes differ → `modified`
   - in both, hashes equal → `unchanged` (ignored)
   - in `baseline` only → `deleted`

Symlinks and non-regular files in `current` → immediate violation (`kind: "unsupported"`).

### 8.3 Allowed-path matching

`allowed_paths` (from the case, snapshotted into `workdir/.bench/allowed_paths.json`) is evaluated per classified path:

- `created` or `modified` path is allowed iff it matches at least one entry.
- `deleted` path is allowed iff it matches at least one entry **and** the case declares `"allow_deletions": true` (default `false`; not used by v1 cases).
- `unchanged` is always allowed.

Matching rules per entry (see §4 for the authoritative syntax spec):
- exact relative path → match iff equal.
- path ending in `/` → match iff the candidate is equal to it or lies beneath it at any depth.
- pattern containing `*` or `?` → match via `fnmatch.fnmatchcase`. These wildcards match within a single path segment only and do not cross `/`. Recursive coverage is expressed via the directory form above.

### 8.4 Violations and result shape

`allowed_paths_check.validate` returns:

```json
{
  "ok": false,
  "violations": [
    { "path": "todo-py/todo.py", "kind": "modified" },
    { "path": "out/extra.log",    "kind": "created"  }
  ],
  "counts": { "created": 1, "modified": 1, "deleted": 0, "unchanged": 3 }
}
```

`ok` is `true` iff `violations` is empty. Counts are informational and always included.

### 8.5 `runs/` false-positive exclusion

- Validation traverses **only** `runs/<run>/cases/<id>/workdir/`. Per-run scoring artifacts — `runs/<run>/manifest.json`, `runs/<run>/cases/<id>/case.json`, `result.json`, `transcript.txt`, `summary.md` — live above `workdir/` and are never traversed, so they can never produce a violation.
- `workdir/.bench/` is excluded from both baseline capture and current-state walks.
- Agents are contractually told: "every output path goes under `workdir/`, and must be listed in `allowed_paths`." This is the complete surface.

### 8.6 Edge cases

- A case with `fixture: null` and no `allowed_paths` → any `created` file is a violation. That is intentional; cases must declare what they produce.
- Empty files in `current` that are also empty in `baseline` (hash-equal) count as `unchanged`.
- Case-insensitive filesystems: path comparison is byte-for-byte; agents targeting Windows/macOS need to match case exactly. Documented in `docs/case-authoring.md`.

## 9. Run/result format

One run per directory `runs/<YYYYMMDD-HHMMSS>-<label>/`.

```
runs/20260421-180000-local-llama/
  manifest.json
  cases/
    SMK-001/
      case.json            # snapshot of the case at run time
      workdir/
        .bench/
          baseline.json
          allowed_paths.json
        out/
          banner.txt
      result.json
      transcript.txt       # optional, free-form
  summary.md
```

### `manifest.json`

```json
{
  "schema_version": 1,
  "run_id": "20260421-180000-local-llama",
  "started_at": "2026-04-21T18:00:00Z",
  "finished_at": "2026-04-21T18:03:11Z",
  "label": "local-llama",
  "agent": { "name": "…", "model": "…", "notes": "…" },
  "suite": "smoke",
  "cases": ["SMK-001", "STR-001"],
  "counts": { "total": 2, "passed": 2, "failed": 0, "error": 0 }
}
```

### `result.json` (per case)

```json
{
  "schema_version": 1,
  "case_id": "SMK-001",
  "status": "pass",
  "validators": [
    { "type": "exact_text", "ok": true, "detail": "bytes match" }
  ],
  "allowed_paths_check": {
    "ok": true,
    "violations": [],
    "counts": { "created": 1, "modified": 0, "deleted": 0, "unchanged": 0 }
  },
  "duration_ms": 0,
  "notes": ""
}
```

`status` ∈ {`pass`, `fail`, `error`, `skipped`}. `error` covers validator exceptions (missing workdir, malformed JSON in a `json_file` target that crashed the parse, etc.); `fail` covers expected-shape-but-wrong-content.

### `summary.md`

One-page table, one row per case:

| case | status | declared validator | allowed_paths | notes |
|------|--------|--------------------|----------------|-------|

Footer: totals, run label, agent metadata, run duration. Kept plain so two summaries diff cleanly.

## 10. Script surface (v1)

Four CLI scripts under `scripts/`. All Python 3 stdlib + `argparse`. All read/write JSON only.

- **`scripts/new_run.py --label <l> --suite <s> [--cases id,id]`**
  Creates `runs/<stamp>-<label>/` with a stub `manifest.json`. For each selected case: copies the case JSON to `cases/<id>/case.json`, creates `workdir/`, optionally copies `fixture` tree, writes `workdir/.bench/baseline.json` and `workdir/.bench/allowed_paths.json`.

- **`scripts/validate.py --run runs/<stamp>-<label>`**
  Walks `cases/*/case.json`. For each: runs the declared validator and `allowed_paths_check` against `workdir/`. Writes `result.json` per case. Updates `manifest.json` counts. Exits non-zero iff any case's `status != "pass"`.

- **`scripts/summarize.py --run runs/<stamp>-<label>`**
  Reads `manifest.json` + `result.json`s, writes `summary.md`. Pure function of the run directory.

- **`scripts/compare.py --a <run> --b <run>`** — **`--help` stub in v1**. Real diff view is v1.1.

Scripts do not invoke any agent. The intended usage loop is:

1. `new_run.py --label my-model --suite smoke` → run dir ready.
2. Operator runs each case against their agent of choice. Agent output goes into the case's `workdir/`.
3. `validate.py --run <run>` → per-case results.
4. `summarize.py --run <run>` → one-page report.

## 11. v1 shipping slice

- Full repo structure in §3.
- Two fixtures (§5).
- Four cases (§6): SMK-001, STR-001, RO-001, EDT-002.
- Five validators (§7).
- Three JSON schemas (§4, §9).
- Three scripts plus a stub (§10).
- Three docs pages: `docs/methodology.md`, `docs/case-authoring.md`, `docs/running.md` (each ≤1 page).

**Exit criterion**: operator can run all four v1 cases (SMK-001, STR-001, RO-001, EDT-002) against two different agents and produce two `summary.md` files that meaningfully differentiate them.

## 12. Deferred (post-v1)

- Execution harness / `$BENCH_AGENT_CMD` wrapper
- `test_pass` validator (adds pytest dep + subprocess contract)
- `jsonschema` dep + richer schema validator
- Frontend fixture
- Multi-validator per case (`validators: [...]`) beyond the accepted singular shape
- `compare.py` real diff view
- CI workflow
- Suite definition files (tags suffice at this scale)
- Difficulty weighting / aggregate scoring
- Per-model config files
- Cost / latency / token tracking
- Retry / sampling logic
- Result archival / remote storage
- Leaderboard or multi-run aggregates
- Browser-automation cases (explicitly out of scope)
- PLN-001 and EDT-001 cases

## 13. Risks and mitigations

- **Regrettable case format.** Mitigated by `schema_version: 1` on every case + schema file committed under `schemas/`.
- **Runner coupling to one vendor.** Mitigated by deferring the runner entirely. Operators wire their own agent invocation.
- **Fixture drift silently changing case meaning.** Mitigated by: fixture README stating intended shape; any change that alters case semantics must bump `schema_version` on affected cases; `case.json` is snapshotted into each run so historical runs remain re-scorable against their own baseline.
- **Hash-based baseline missing directory-only changes.** Accepted: v1 only cares about regular files; empty directories do not count.

## 14. Suggested branch

`feat/v1-benchmark-core`
