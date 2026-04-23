# frontends/ — adapter layer

Thin wrappers that invoke a coding-agent frontend against a single benchmark case.
The benchmark core (`scripts/`, `bench/`, `schemas/`, `validators/`) is not aware of
any of this — wrappers exist entirely outside that surface.

## Contract

Each adapter is a single `invoke.sh` at `frontends/<tool>/invoke.sh`.

Invocation:

```
bash frontends/<tool>/invoke.sh <case_json_path> <workdir>
```

- `<case_json_path>` — path to a case JSON file (caller-relative is fine).
- `<workdir>` — path to the pre-scaffolded workdir `new_run.py` created for this case
  (e.g. `runs/<run-id>/cases/<CASE-ID>/workdir`). Caller-relative is fine.

Requirements:

- Resolve any paths that must outlive a directory change **before** `cd`.
- Run the frontend one-shot, non-interactive, with CWD inside `$workdir`.
- Write all frontend artifacts into a `.frontend/` directory at the **case level**
  (sibling of `$workdir/`, i.e. `$(dirname "$workdir")/.frontend/`). This is
  outside the baselined workdir so it doesn't register as an `allowed_paths`
  violation. Required files:
  - `stdout` — raw frontend stdout
  - `stderr` — raw frontend stderr
  - `exit_code` — the frontend's exit code
  - `env.extra.json` — sidecar capturing what the core manifest doesn't
    (model digest, Ollama version, pinned params, permission matrix,
    frontend version, ISO timestamp)
- Do not modify anything outside `$workdir`.
- Exit non-zero on tool failure (but still after writing the three `.frontend/`
  files above, so the validator and diff can still run).

## Scope boundaries

- `allowed_paths` from the case JSON is **not** a frontend input heuristic.
  Validators enforce scope after the fact via diffs; the wrapper does not
  restrict filesystem access and does not feed `allowed_paths` to the tool.
- For Aider, the wrapper may in future honor an optional
  `cases/<suite>/<CASE-ID>.files.txt` sidecar (one workdir-relative path per
  line) and pass the entries as `--file` args. Absent the sidecar, no `--file`
  args are passed. This is a design seam; it is not wired up in the first pass.
