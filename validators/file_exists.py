from __future__ import annotations

from pathlib import Path


def validate(case: dict, workdir: Path) -> dict:
    args = case["validator"]["args"]
    rel = args["path"]
    want_exists = args.get("exists", True)
    contains = args.get("contains")
    not_contains = args.get("not_contains")

    p = workdir / rel
    exists = p.exists()

    if exists != want_exists:
        return {
            "type": "file_exists",
            "ok": False,
            "detail": f"exists={exists}, required exists={want_exists} for {rel}",
        }

    if not exists:
        return {"type": "file_exists", "ok": True, "detail": f"{rel} absent as required"}

    if contains is None and not_contains is None:
        return {"type": "file_exists", "ok": True, "detail": f"{rel} present"}

    content = p.read_text()
    if contains is not None and contains not in content:
        return {"type": "file_exists", "ok": False,
                "detail": f"{rel} is missing required substring {contains!r}"}
    if not_contains is not None and not_contains in content:
        return {"type": "file_exists", "ok": False,
                "detail": f"{rel} still contains forbidden substring {not_contains!r}"}
    return {"type": "file_exists", "ok": True, "detail": f"{rel} present and content checks pass"}
