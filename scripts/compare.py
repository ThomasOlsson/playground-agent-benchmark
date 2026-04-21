"""Compare two runs. Deferred to v1.1 — this is a --help stub."""
from __future__ import annotations

import argparse


STUB_MSG = (
    "scripts/compare.py is a stub in v1 — the actual diff view is deferred to v1.1.\n"
    "See docs/plans/v1-design.md §10 and §12."
)


def main() -> int:
    p = argparse.ArgumentParser(prog="compare", description=STUB_MSG)
    p.add_argument("--a", help="first run directory (not implemented in v1)")
    p.add_argument("--b", help="second run directory (not implemented in v1)")
    args = p.parse_args()

    if args.a or args.b:
        print(STUB_MSG)
        return 2

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
