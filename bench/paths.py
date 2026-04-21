"""Allowed-path matching per spec §4 and §8.3.

Entries are one of:
  * exact relative path       -> equal compare
  * path ending in '/'        -> self or any descendant
  * fnmatch glob (*, ?)       -> fnmatch.fnmatchcase within a single segment;
                                 wildcards do NOT cross '/' boundaries

Recursive ** globs are intentionally not supported in v1.
"""
from __future__ import annotations

import fnmatch


def _is_glob(pattern: str) -> bool:
    return any(ch in pattern for ch in "*?[")


def matches(candidate: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        stem = pattern[:-1]
        return candidate == stem or candidate.startswith(stem + "/")

    if not _is_glob(pattern):
        return candidate == pattern

    # Segment-aware glob: the candidate must have the same number of '/' segments
    # as the pattern, and each segment must fnmatch the corresponding one.
    pat_parts = pattern.split("/")
    cand_parts = candidate.split("/")
    if len(pat_parts) != len(cand_parts):
        return False
    return all(fnmatch.fnmatchcase(c, p) for c, p in zip(cand_parts, pat_parts))


def any_match(candidate: str, patterns: list[str]) -> bool:
    return any(matches(candidate, p) for p in patterns)
