# AGENTS.md

This repository is a practical playground for benchmarking coding and agent models.

It is intentionally lightweight and non-scientific.
The goal is to compare practical agent behavior in controlled small tasks.

## Mission

When working in this repository, optimize for:

- determinism
- repeatability
- small reviewable changes
- explicit validation
- practical comparability
- low ambiguity

Do not optimize for flashy demos, unnecessary complexity, or broad autonomous behavior.

## General rules

1. Keep changes small and reviewable.
2. Prefer deterministic benchmark cases over open-ended tasks.
3. Preserve clear separation between:
   - fixtures
   - cases
   - validators
   - scripts
   - run outputs
   - documentation
4. Do not silently change benchmark semantics.
5. If a benchmark case changes meaning, document it clearly.
6. Avoid benchmark drift.

## Repository priorities

When implementing or changing this repository, prefer this order:

1. repository structure
2. fixture creation
3. case format
4. validation logic
5. run/result format
6. execution scripts
7. comparison helpers
8. documentation polish

## Benchmark philosophy

This repository exists to compare practical agent quality, especially:

- instruction following
- exact output discipline
- structured artifact generation
- scope control
- bounded read-only understanding
- bounded edits
- small planning quality
- controlled multi-file changes

Early versions should strongly prefer:
- small fixtures
- strict schemas
- explicit contracts
- low ambiguity
- easy validation

Do not start with:
- giant repos
- browser-heavy tasks
- highly manual-only scoring
- vague “understand the whole project” cases
- provider-specific lock-in unless clearly isolated

## Fixture rules

Fixtures should be:
- small
- understandable
- high-signal
- cheap to run
- easy to validate

Prefer multiple small fixtures over one large complex fixture.

Do not add large fixtures without a clear reason.

## Case design rules

Each benchmark case should define, as clearly as possible:
- id
- title
- category
- prompt
- allowed_paths
- mode (`read-only`, `plan-only`, or `write`)
- expected_output
- validator
- tags
- difficulty

If a case is too ambiguous, tighten it before adding more.

## Validation rules

Validation should be as automatic as practical.

Prefer objective checks such as:
- exact text match
- valid JSON
- strict key/schema checks
- expected file existence
- expected file changes
- tests passing
- lint/format checks
- scope/path checks where practical

If human review is still needed, keep it explicit and limited.

## Result rules

Benchmark results should be easy to compare later.

Prefer:
- one run manifest
- one per-case result file
- one compact human-readable summary

Do not mix source benchmark definitions with generated outputs.

## Automation rules

Automation should start simple.

Useful first commands are things like:
- run a smoke suite
- run a structured-output suite
- run a bounded-edit suite
- compare two runs

Do not overengineer orchestration before the core loop works.

## Portability rules

Keep home and work usage in mind.

Unless explicitly asked otherwise:
- do not hardcode machine-specific paths
- do not add unnecessary network dependence
- do not make the benchmark core depend on one vendor
- do not add hidden magic

## Documentation expectations

When adding benchmark functionality, also update the relevant docs.

At minimum, document:
- what was added
- why it exists
- how to run it
- how to validate it
- what is intentionally deferred

## Implementation behavior

When asked to implement:
1. restate scope briefly
2. identify the smallest useful slice
3. implement only that slice
4. validate it
5. report exactly what was added
6. list deferred work explicitly

## Preferred style

- concrete
- explicit
- small-slice
- practical
- low-abstraction
- easy to review

## Definition of success

A good change in this repository makes benchmark results:
- easier to trust
- easier to reproduce
- easier to compare
- easier to extend carefully
