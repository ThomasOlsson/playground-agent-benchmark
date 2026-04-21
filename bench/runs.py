"""Run-dir layout, manifest and result I/O, case filtering, env/hardware collection."""
from __future__ import annotations

import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path


MANIFEST_NAME = "manifest.json"
RESULT_NAME = "result.json"
CASE_SNAPSHOT_NAME = "case.json"


def new_run_id(label: str, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{label}"


def new_run_dir(runs_root: Path, label: str, now: datetime | None = None) -> Path:
    rid = new_run_id(label, now=now)
    d = runs_root / rid
    (d / "cases").mkdir(parents=True, exist_ok=True)
    return d


def write_manifest(run_dir: Path, manifest: dict) -> None:
    (run_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2))


def read_manifest(run_dir: Path) -> dict:
    return json.loads((run_dir / MANIFEST_NAME).read_text())


def write_result(case_dir: Path, result: dict) -> None:
    (case_dir / RESULT_NAME).write_text(json.dumps(result, indent=2))


def read_result(case_dir: Path) -> dict:
    return json.loads((case_dir / RESULT_NAME).read_text())


def list_cases(cases_root: Path) -> list[Path]:
    return sorted(cases_root.rglob("*.json"))


def filter_by_suite(cases: list[dict], suite: str | None, explicit_ids: list[str] | None) -> list[dict]:
    if explicit_ids:
        wanted = set(explicit_ids)
        return [c for c in cases if c["id"] in wanted]
    if suite:
        return [c for c in cases if suite in c.get("tags", [])]
    return list(cases)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect_environment() -> dict:
    return {
        "host":   platform.node() or "unknown",
        "os":     platform.platform() or "unknown",
        "python": platform.python_version() or "unknown",
        "arch":   platform.machine() or "unknown",
    }


def _read_memory_gb() -> float | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    try:
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                return round(kb / 1024 / 1024, 1)
    except (OSError, ValueError, IndexError):
        return None
    return None


def collect_hardware(gpu: str | None = None) -> dict:
    return {
        "cpu_cores": os.cpu_count(),
        "memory_gb": _read_memory_gb(),
        "gpu":       gpu,
    }
