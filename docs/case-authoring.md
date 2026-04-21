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
- **`file_exists.contains` / `not_contains` are plain text-based substring matches.** The file is read via `Path.read_text()` (UTF-8) and compared with Python's `in`. No regex, no case folding, no Unicode normalization, no whitespace collapsing. If you need a pattern, phrase it as literal substring(s) — or express the requirement through a different validator.
- **`file_exists` with `exists: false` silently skips `contains` / `not_contains`.** If you want the file absent, content args are ignored (there's nothing to read). Don't rely on them being enforced when the file isn't expected to exist.

## Changing an existing case

If a change alters case meaning — the prompt, the expected output, the validator args — bump `schema_version`. This makes benchmark drift explicit and keeps historical runs re-scorable against their own snapshot.
