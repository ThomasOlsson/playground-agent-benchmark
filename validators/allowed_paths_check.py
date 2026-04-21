from __future__ import annotations

import json
from pathlib import Path

from bench import baseline, paths


def validate(case: dict, workdir: Path) -> dict:
    sidecar = workdir / baseline.SIDECAR_DIRNAME
    try:
        baseline_data = json.loads((sidecar / baseline.BASELINE_FILENAME).read_text())
        allowed = json.loads((sidecar / baseline.ALLOWED_PATHS_FILENAME).read_text())
    except FileNotFoundError as e:
        return {
            "type": "allowed_paths_check",
            "ok": False,
            "detail": f"missing sidecar file: {e.filename}",
            "violations": [],
            "counts": {"created": 0, "modified": 0, "deleted": 0, "unchanged": 0},
        }

    current = baseline.walk(workdir)
    d = baseline.diff(baseline_data["files"], current)
    allow_deletions = bool(case.get("allow_deletions", False))

    violations: list[dict] = []

    for path in d["created"]:
        if not paths.any_match(path, allowed):
            violations.append({"path": path, "kind": "created"})
    for path in d["modified"]:
        if not paths.any_match(path, allowed):
            violations.append({"path": path, "kind": "modified"})
    for path in d["deleted"]:
        if not (allow_deletions and paths.any_match(path, allowed)):
            violations.append({"path": path, "kind": "deleted"})
    for path in d["unsupported"]:
        violations.append({"path": path, "kind": "unsupported"})

    return {
        "type": "allowed_paths_check",
        "ok": not violations,
        "detail": "no violations" if not violations else f"{len(violations)} violation(s)",
        "violations": violations,
        "counts": {
            "created":   len(d["created"]),
            "modified":  len(d["modified"]),
            "deleted":   len(d["deleted"]),
            "unchanged": len(d["unchanged"]),
        },
    }
