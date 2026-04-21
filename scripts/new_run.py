"""Scaffold a new run directory for manual case execution."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from bench import baseline, loader, runs


REPO_ROOT = Path(__file__).resolve().parent.parent


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="new_run", description="Scaffold a run directory.")
    p.add_argument("--label", required=True)
    p.add_argument("--suite", default=None)
    p.add_argument("--cases", default=None, help="Comma-separated case IDs (overrides --suite).")
    p.add_argument("--runs-dir", default=str(REPO_ROOT / "runs"))
    p.add_argument("--cases-dir", default=str(REPO_ROOT / "cases"))
    p.add_argument("--fixtures-dir", default=str(REPO_ROOT / "fixtures"))

    # Agent metadata (all optional; defaults preserve key presence with empty/null values)
    p.add_argument("--frontend", default="", help="Agent tool name: claude-code, codex, cursor, aider, ollama-cli, ...")
    p.add_argument("--model", default="", help="Model identifier string.")
    p.add_argument("--provider", default="", help="Vendor/engine name: anthropic, openai, ollama, vllm, ...")
    p.add_argument("--local-or-cloud", default="unknown", choices=["local", "cloud", "unknown"])
    p.add_argument("--runtime-base-url", default="", help="Non-empty for local servers or custom proxies.")
    p.add_argument("--agent-notes", default="", help="Freeform note attached to the agent block.")

    # Run-level metadata
    p.add_argument("--notes", default="", help="Freeform run-level note.")
    p.add_argument("--gpu", default=None, help="GPU description; stored as null if omitted.")
    return p.parse_args()


def _load_all_cases(cases_dir: Path) -> list[dict]:
    out = []
    for path in runs.list_cases(cases_dir):
        out.append(loader.load_case(path))
    return out


def _scaffold_case(case: dict, case_dir: Path, fixtures_dir: Path) -> None:
    workdir = case_dir / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case.json").write_text(json.dumps(case, indent=2))

    fixture = case.get("fixture")
    if fixture:
        src = fixtures_dir / fixture
        dst = workdir / Path(fixture).name
        if not src.exists():
            raise SystemExit(f"fixture not found: {src}")
        shutil.copytree(src, dst)

    baseline.capture(workdir)
    (workdir / baseline.SIDECAR_DIRNAME / baseline.ALLOWED_PATHS_FILENAME).write_text(
        json.dumps(case.get("allowed_paths", []), indent=2)
    )


def _build_manifest(args: argparse.Namespace, run_dir: Path, case_ids: list[str]) -> dict:
    now_iso = runs.utc_now_iso()
    base_url = args.runtime_base_url.strip() or None
    return {
        "schema_version": 1,
        "run_id":      run_dir.name,
        "timestamp":   now_iso,
        "started_at":  now_iso,
        "finished_at": None,
        "label":       args.label,
        "suite":       args.suite,
        "cases":       case_ids,
        "agent": {
            "frontend":         args.frontend,
            "model":            args.model,
            "provider":         args.provider,
            "local_vs_cloud":   args.local_or_cloud,
            "runtime_base_url": base_url,
            "notes":            args.agent_notes,
        },
        "environment": runs.collect_environment(),
        "hardware":    runs.collect_hardware(gpu=args.gpu),
        "counts":      {"total": len(case_ids), "passed": 0, "failed": 0, "error": 0},
        "notes":       args.notes,
    }


def main() -> int:
    args = _parse_args()
    cases_dir = Path(args.cases_dir)
    fixtures_dir = Path(args.fixtures_dir)
    runs_dir = Path(args.runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)

    explicit = [c.strip() for c in args.cases.split(",")] if args.cases else None
    all_cases = _load_all_cases(cases_dir)
    selected = runs.filter_by_suite(all_cases, suite=args.suite, explicit_ids=explicit)
    if not selected:
        raise SystemExit("no cases matched the selection")

    now = datetime.now(timezone.utc)
    run_dir = runs.new_run_dir(runs_dir, args.label, now=now)
    case_ids = [c["id"] for c in selected]

    runs.write_manifest(run_dir, _build_manifest(args, run_dir, case_ids))

    for case in selected:
        case_dir = run_dir / "cases" / case["id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        _scaffold_case(case, case_dir, fixtures_dir)

    print(str(run_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
