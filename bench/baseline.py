"""Baseline capture + diff per spec §8."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SIDECAR_DIRNAME = ".bench"
BASELINE_FILENAME = "baseline.json"
ALLOWED_PATHS_FILENAME = "allowed_paths.json"
_UNSUPPORTED_MARKER = "__unsupported__"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(workdir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in sorted(workdir.rglob("*")):
        rel_parts = p.relative_to(workdir).parts
        if rel_parts and rel_parts[0] == SIDECAR_DIRNAME:
            continue
        if p.is_dir():
            continue
        rel = "/".join(rel_parts)
        if p.is_symlink() or not p.is_file():
            out[rel] = {"sha256": _UNSUPPORTED_MARKER, "size": 0}
            continue
        out[rel] = {"sha256": _sha256(p), "size": p.stat().st_size}
    return out


def capture(workdir: Path) -> dict:
    files = walk(workdir)
    data = {
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "files": files,
    }
    sidecar = workdir / SIDECAR_DIRNAME
    sidecar.mkdir(parents=True, exist_ok=True)
    (sidecar / BASELINE_FILENAME).write_text(json.dumps(data, indent=2))
    return data


def diff(baseline: dict, current: dict) -> dict:
    b_files = baseline.get("files", baseline) if "files" in baseline else baseline
    all_paths = set(b_files) | set(current)
    created, modified, deleted, unchanged, unsupported = [], [], [], [], []
    for path in sorted(all_paths):
        b = b_files.get(path)
        c = current.get(path)
        if c and c.get("sha256") == _UNSUPPORTED_MARKER:
            unsupported.append(path)
            continue
        if b is None:
            created.append(path)
        elif c is None:
            deleted.append(path)
        elif b.get("sha256") == c.get("sha256"):
            unchanged.append(path)
        else:
            modified.append(path)
    return {
        "created": created,
        "modified": modified,
        "deleted": deleted,
        "unchanged": unchanged,
        "unsupported": unsupported,
    }
