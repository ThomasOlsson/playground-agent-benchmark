from __future__ import annotations

import json
from pathlib import Path


def validate(case: dict, workdir: Path) -> dict:
    rel = case["validator"]["args"]["path"]
    p = workdir / rel
    if not p.exists():
        return {"type": "json_file", "ok": False, "detail": f"missing file: {rel}"}
    try:
        parsed = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        return {"type": "json_file", "ok": False, "detail": f"invalid JSON: {e}"}
    return {"type": "json_file", "ok": True, "detail": "parsed OK", "observed": parsed}
