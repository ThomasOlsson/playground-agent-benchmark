# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status: bootstrap

There is no source code, build system, or test runner yet. Do not invent commands — if the user asks "how do I run tests?", the honest answer is "nothing to run yet." When implementing, build only the smallest useful slice and say so.

## Authoritative guidance

`AGENTS.md` governs behavior in this repo and takes precedence over general defaults. Read it before making non-trivial changes. Key rules worth surfacing here:

- **Implementation protocol** (AGENTS.md §Implementation behavior): restate scope → identify the smallest useful slice → implement only that slice → validate → report exactly what was added → list deferred work explicitly.
- **Repository priority order** for new work: structure → fixtures → case format → validators → run/result format → execution scripts → comparison helpers → docs. Don't get ahead of this order.
- **Never silently change benchmark semantics.** If a case's meaning shifts, document it — benchmark drift invalidates cross-run comparison, which is the whole point of the repo.
- **Keep generated outputs separate from source.** Benchmark definitions (`fixtures/`, `cases/`, `validators/`) must not be mixed with run artifacts.

## Architecture (planned)

The repo is expected to evolve toward this layout (from README §Proposed repository structure):

- `fixtures/` — small test projects
- `cases/` — benchmark case definitions
- `validators/` — validation scripts and schemas
- `scripts/` — run/compare commands
- `docs/` — methodology notes
- `runs/`, `reports/`, `artifacts/` — **already exist but are gitignored** (only `.gitkeep` is tracked). Treat these as local-only output sinks. Never commit contents.

## Case schema

Each benchmark case must define (AGENTS.md §Case design rules):

`id`, `title`, `category`, `prompt`, `allowed_paths`, `mode` (`read-only` | `plan-only` | `write`), `expected_output`, `validator`, `tags`, `difficulty`.

Tighten ambiguous cases before adding more. One-off tasks without this shape aren't benchmark cases.

## Result shape

For a run, produce: one run manifest + one per-case result file + one compact human-readable summary. Keep this consistent across runs so two result sets can be compared mechanically.

## What this repo is not

Not a scientific benchmark suite, not a leaderboard, not a place for giant real-world repos or vague "understand the whole project" tasks. The value is practical comparability across models in bounded, deterministic cases. Flashy additions that compromise determinism or reviewability work against the project.
