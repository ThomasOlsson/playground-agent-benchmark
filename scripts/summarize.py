"""Emit summary.md from manifest.json + per-case result.json files (spec §9.5)."""
from __future__ import annotations

import argparse
from pathlib import Path

from bench import runs


TABLE_HEADER = "| case | status | declared validator | allowed_paths | latency_ms | notes |"
TABLE_SEP    = "|------|--------|--------------------|----------------|------------|-------|"


def _row(case_id: str, result: dict) -> str:
    validators = result.get("validators") or []
    declared = validators[0] if validators else {"type": ""}
    apc = result.get("allowed_paths_check", {})
    apc_cell = "ok" if apc.get("ok") else f"{len(apc.get('violations', []))} violation(s)"
    latency = result.get("latency_ms")
    latency_cell = "-" if latency is None else str(latency)
    notes = (result.get("notes") or "").replace("|", "\\|")
    return (f"| {case_id} | {result.get('status','?')} | {declared.get('type','')} | "
            f"{apc_cell} | {latency_cell} | {notes} |")


def _header_block(manifest: dict) -> list[str]:
    return [
        f"# Run {manifest['run_id']}",
        "",
        f"- timestamp: {manifest.get('timestamp') or '-'}",
        f"- started_at: {manifest.get('started_at') or '-'}",
        f"- finished_at: {manifest.get('finished_at') or '-'}",
        f"- label: {manifest.get('label','')}",
        f"- suite: {manifest.get('suite') or '-'}",
    ]


def _agent_block(agent: dict) -> list[str]:
    return [
        "",
        "## Agent",
        "",
        f"- frontend: {agent.get('frontend','')}",
        f"- model: {agent.get('model','')}",
        f"- provider: {agent.get('provider','')}",
        f"- local_vs_cloud: {agent.get('local_vs_cloud','')}",
        f"- runtime_base_url: {agent.get('runtime_base_url') or '-'}",
        f"- notes: {agent.get('notes','')}",
    ]


def _environment_block(env: dict, hw: dict) -> list[str]:
    return [
        "",
        "## Environment",
        "",
        f"- host: {env.get('host','')}",
        f"- os: {env.get('os','')}",
        f"- python: {env.get('python','')}",
        f"- arch: {env.get('arch','')}",
        f"- cpu_cores: {hw.get('cpu_cores')}",
        f"- memory_gb: {hw.get('memory_gb')}",
        f"- gpu: {hw.get('gpu') or '-'}",
    ]


def _table_block(run_dir: Path, manifest: dict) -> list[str]:
    lines = ["", "## Cases", "", TABLE_HEADER, TABLE_SEP]
    for case_id in manifest["cases"]:
        result = runs.read_result(run_dir / "cases" / case_id)
        lines.append(_row(case_id, result))
    return lines


def _footer_block(manifest: dict) -> list[str]:
    c = manifest["counts"]
    return [
        "",
        f"Totals: total={c['total']} passed={c['passed']} failed={c['failed']} error={c['error']}",
        f"Notes: {manifest.get('notes','') or '-'}",
    ]


def main() -> int:
    p = argparse.ArgumentParser(prog="summarize")
    p.add_argument("--run", required=True)
    args = p.parse_args()

    run_dir = Path(args.run).resolve()
    manifest = runs.read_manifest(run_dir)

    lines: list[str] = []
    lines += _header_block(manifest)
    lines += _agent_block(manifest.get("agent", {}))
    lines += _environment_block(manifest.get("environment", {}), manifest.get("hardware", {}))
    lines += _table_block(run_dir, manifest)
    lines += _footer_block(manifest)

    (run_dir / "summary.md").write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
