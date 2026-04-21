# playground-agent-benchmark

A small, practical benchmark repository for comparing coding and agent models across environments.

This is intentionally **not** a scientific benchmark suite.
It is a hands-on playground for testing how models behave in realistic small tasks:
- instruction following
- exact output
- structured file output
- bounded repo understanding
- small edits
- small planning tasks

The goal is to compare **practical usefulness**, not produce academic leaderboard claims.

## Why this exists

This repository is meant to answer questions like:

- Which model follows instructions most precisely?
- Which model leaks extra text when strict output is required?
- Which model can write valid JSON artifacts reliably?
- Which model respects scope and file boundaries?
- Which model handles small edits safely?
- Which model is useful as a bounded helper versus a primary coding agent?

The same repository should be usable:
- at home
- at work
- with local models
- with cloud models
- with different coding-agent frontends where practical

## Benchmark philosophy

This project is deliberately lightweight and practical.

It should favor:
- small fixtures
- deterministic cases
- explicit validation
- repeatable runs
- easy comparison
- low setup friction

It should avoid, especially in early versions:
- giant real-world repos
- vague “understand the whole project” tasks
- benchmark theater
- heavy vendor lock-in
- unnecessary complexity

## What should be benchmarked

The first useful benchmark slices should focus on:

- **instruction discipline**
- **exact output**
- **structured JSON/file output**
- **read-only bounded understanding**
- **small planning tasks**
- **bounded code edits**
- **small refactors**
- **controlled multi-file changes**

Browser-heavy or larger-context tasks can be added later if they are still practical and reviewable.

## Proposed repository structure

The repository is expected to evolve into something like:

- `fixtures/` — small test projects and mini codebases
- `cases/` — benchmark case definitions
- `validators/` — validation scripts and schemas
- `runs/` — stored outputs and summaries from benchmark runs
- `scripts/` — commands to run and compare benchmarks
- `docs/` — notes about methodology, scoring, and usage
- `AGENTS.md` — instructions for coding agents working in this repo

## What a good benchmark case looks like

A good case should usually have:
- a clear task
- clear allowed paths
- a clear output contract
- a clear validation method
- low ambiguity
- a small enough scope that multiple models can realistically attempt it

## What success looks like

The first version is successful if it can:
- run a small smoke suite
- run a structured-output suite
- run a bounded-edit suite
- store results in a consistent format
- compare two result sets in a useful way

Thin and useful beats big and unfinished.

## Notes

This repository is for **practical agent comparison**.
It is not meant to be a formal scientific benchmark, and results should be interpreted with that in mind.

The value is in:
- shared fixtures
- repeatable prompts
- consistent validators
- comparable outputs
- learning where different models are useful or weak

## Status

Bootstrap / planning stage.

Initial implementation should focus on:
- repo structure
- a few small fixtures
- a few benchmark cases
- simple validators
- minimal run/result format
- lightweight execution scripts
