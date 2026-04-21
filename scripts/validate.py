"""Run validators over a scaffolded run directory and record per-case results + artifacts."""
from __future__ import annotations

import argparse
import difflib
import json
import time
from pathlib import Path

from bench import baseline, runs
from validators import ALWAYS_ON, REGISTRY


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR_DEFAULT = REPO_ROOT / "fixtures"


def _status_from(declared: dict, apc: dict) -> str:
    all_ok = declared.get("ok", False) and apc.get("ok", False)
    if all_ok:
        return "pass"
    if not declared.get("ok") and "raised" in declared.get("detail", ""):
        return "error"
    return "fail"


def _compute_changes(workdir: Path) -> dict:
    """Return the spec §9.3 summary for this workdir."""
    sidecar = workdir / baseline.SIDECAR_DIRNAME / baseline.BASELINE_FILENAME
    base_files = json.loads(sidecar.read_text())["files"] if sidecar.exists() else {}
    current = baseline.walk(workdir)
    d = baseline.diff(base_files, current)
    return {
        "created":         d["created"],
        "modified":        d["modified"],
        "deleted":         d["deleted"],
        "unchanged_count": len(d["unchanged"]),
        "unsupported":     d["unsupported"],
    }


def _read_text_or_none(path: Path) -> list[str] | None:
    """Return splitlines(keepends=True) or None if the file is binary / missing."""
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines(keepends=True)
    except (UnicodeDecodeError, OSError):
        return None


def _write_changes_diff(workdir: Path, case: dict, changes: dict, out_path: Path,
                        fixtures_dir: Path) -> None:
    """Emit a unified diff of text changes. Always writes, even if empty."""
    fixture = case.get("fixture")
    fixture_basename = Path(fixture).name if fixture else None
    buf: list[str] = []

    def _diff(before: list[str] | None, after: list[str] | None, label_from: str, label_to: str) -> None:
        if before is None or after is None:
            buf.append(f"# skipped binary: {label_to or label_from}\n")
            return
        for line in difflib.unified_diff(before, after, fromfile=label_from, tofile=label_to):
            buf.append(line)

    def _fixture_source(rel: str) -> Path | None:
        if fixture_basename and rel.startswith(fixture_basename + "/"):
            inner = rel[len(fixture_basename) + 1:]
            return fixtures_dir / fixture / inner
        return None

    for rel in changes["created"]:
        after = _read_text_or_none(workdir / rel)
        _diff([], after, "/dev/null", f"workdir/{rel}")

    for rel in changes["modified"]:
        src = _fixture_source(rel)
        before = _read_text_or_none(src) if src else []
        after = _read_text_or_none(workdir / rel)
        _diff(before, after,
              f"fixture/{rel}" if src else "/dev/null",
              f"workdir/{rel}")

    for rel in changes["deleted"]:
        src = _fixture_source(rel)
        before = _read_text_or_none(src) if src else []
        _diff(before, [], f"fixture/{rel}" if src else "/dev/null", "/dev/null")

    out_path.write_text("".join(buf))


def _artifact_refs(run_dir: Path, case_dir: Path) -> dict:
    def rel(p: Path) -> str:
        return p.relative_to(run_dir).as_posix()
    return {
        "case_snapshot": rel(case_dir / runs.CASE_SNAPSHOT_NAME),
        "workdir":       rel(case_dir / "workdir"),
        "changes_json":  rel(case_dir / "changes.json"),
        "changes_diff":  rel(case_dir / "changes.diff"),
        "transcript":    rel(case_dir / "transcript.txt"),
    }


def _validate_one(case: dict, workdir: Path) -> tuple[dict, dict]:
    t0 = time.monotonic()
    validator_type = case["validator"]["type"]
    validator_mod = REGISTRY.get(validator_type)
    try:
        if validator_mod is None:
            declared = {"type": validator_type, "ok": False,
                        "detail": f"unknown validator type: {validator_type}"}
        else:
            declared = validator_mod.validate(case, workdir)
    except Exception as e:
        declared = {"type": validator_type, "ok": False,
                    "detail": f"validator raised: {e!r}"}

    try:
        apc = ALWAYS_ON.validate(case, workdir)
    except Exception as e:
        apc = {
            "type": "allowed_paths_check", "ok": False,
            "detail": f"apc raised: {e!r}",
            "violations": [],
            "counts": {"created": 0, "modified": 0, "deleted": 0, "unchanged": 0},
        }

    duration_ms = int((time.monotonic() - t0) * 1000)
    partial = {
        "validators": [declared],
        "allowed_paths_check": {
            "ok":         apc["ok"],
            "detail":     apc.get("detail", ""),
            "violations": apc.get("violations", []),
            "counts":     apc.get("counts", {}),
        },
        "status": _status_from(declared, apc),
        "duration_ms": duration_ms,
    }
    return partial, apc


def main() -> int:
    p = argparse.ArgumentParser(prog="validate")
    p.add_argument("--run", required=True)
    p.add_argument("--fixtures-dir", default=str(FIXTURES_DIR_DEFAULT))
    args = p.parse_args()

    run_dir = Path(args.run).resolve()
    fixtures_dir = Path(args.fixtures_dir)
    manifest = runs.read_manifest(run_dir)
    counts = {"total": 0, "passed": 0, "failed": 0, "error": 0}

    for case_id in manifest["cases"]:
        case_dir = run_dir / "cases" / case_id
        case = json.loads((case_dir / runs.CASE_SNAPSHOT_NAME).read_text())
        workdir = case_dir / "workdir"

        partial, _ = _validate_one(case, workdir)

        changes = _compute_changes(workdir)
        (case_dir / "changes.json").write_text(json.dumps(changes, indent=2))
        _write_changes_diff(workdir, case, changes, case_dir / "changes.diff", fixtures_dir)

        result = {
            "schema_version": 1,
            "case_id":        case["id"],
            "status":         partial["status"],
            "validators":     partial["validators"],
            "allowed_paths_check": partial["allowed_paths_check"],
            "duration_ms":    partial["duration_ms"],
            "latency_ms":     None,
            "artifacts":      _artifact_refs(run_dir, case_dir),
            "notes":          "",
        }
        runs.write_result(case_dir, result)

        counts["total"] += 1
        counts[{"pass": "passed", "fail": "failed",
                "error": "error", "skipped": "error"}[result["status"]]] += 1

    manifest["counts"] = counts
    manifest["finished_at"] = runs.utc_now_iso()
    runs.write_manifest(run_dir, manifest)

    return 0 if counts["total"] == counts["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
