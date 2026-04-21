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
