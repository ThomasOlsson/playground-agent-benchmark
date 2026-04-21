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
