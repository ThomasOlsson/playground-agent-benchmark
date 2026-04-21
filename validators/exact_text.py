from __future__ import annotations

from pathlib import Path


def validate(case: dict, workdir: Path) -> dict:
    args = case["validator"]["args"]
    rel = args["path"]
    expect = args["expect"]
    trailing_nl = args.get("trailing_newline", True)
    strip = args.get("strip", False)

    p = workdir / rel
    if not p.exists():
        return {"type": "exact_text", "ok": False, "detail": f"missing file: {rel}"}

    data = p.read_bytes()
    if strip:
        data = data.strip()

    if trailing_nl:
        if not data.endswith(b"\n"):
            return {"type": "exact_text", "ok": False, "detail": "missing required trailing newline"}
        data = data[:-1]
    else:
        if data.endswith(b"\n"):
            return {"type": "exact_text", "ok": False, "detail": "unexpected trailing newline"}

    try:
        observed = data.decode("utf-8")
    except UnicodeDecodeError:
        return {"type": "exact_text", "ok": False, "detail": "file is not valid UTF-8"}

    if observed == expect:
        return {"type": "exact_text", "ok": True, "detail": "bytes match"}
    return {
        "type": "exact_text",
        "ok": False,
        "detail": "byte mismatch",
        "observed": observed,
        "expected": expect,
    }
