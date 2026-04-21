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
