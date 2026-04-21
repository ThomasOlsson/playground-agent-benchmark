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
