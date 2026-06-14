#!/usr/bin/env python3
"""Shared loader for references/mechanisms.json.

Both retrieve_title_examples.py and run_title_evals.py read the mechanism ->
keyword mapping from here, so the keyword lists live in exactly one place.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parents[1]
MECHANISMS_PATH = SKILL_DIR / "references" / "mechanisms.json"


@lru_cache(maxsize=1)
def load_data() -> dict[str, Any]:
    if not MECHANISMS_PATH.exists():
        return {"mechanisms": {}, "strong_markers": []}
    return json.loads(MECHANISMS_PATH.read_text(encoding="utf-8"))


def mechanisms() -> dict[str, list[str]]:
    return load_data().get("mechanisms", {})


def strong_markers() -> list[str]:
    return list(load_data().get("strong_markers", []))


def keywords_for_query(mechanism: str) -> list[str]:
    """Keywords for a free-text query mechanism (retrieval).

    Matches loosely: a query like "tool" or "复盘" pulls in every mechanism
    whose name overlaps as a substring in either direction. Returns a
    de-duplicated, order-preserving list.
    """
    mech = (mechanism or "").strip().lower()
    if not mech:
        return []
    collected: list[str] = []
    seen: set[str] = set()
    for name, words in mechanisms().items():
        key = name.lower()
        if mech in key or key in mech:
            for word in words:
                if word not in seen:
                    seen.add(word)
                    collected.append(word)
    return collected


def keywords_for_name(name: str) -> list[str]:
    """Keywords for a named mechanism (evals).

    Prefers an exact key match; falls back to loose substring matching so that
    eval cases stay robust to minor naming differences.
    """
    target = (name or "").strip().lower()
    if not target:
        return []
    for key, words in mechanisms().items():
        if key.lower() == target:
            return list(words)
    return keywords_for_query(name)
