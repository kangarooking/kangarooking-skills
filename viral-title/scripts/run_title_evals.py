#!/usr/bin/env python3
"""Lightweight evaluator for generated title candidates against seed cases."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import mechanism_lib

SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_EVALS = SKILL_DIR / "references" / "evals" / "wechat-ai-title-evals.json"


def tokenize(text: str) -> set[str]:
    lowered = text.lower()
    latin = re.findall(r"[a-z0-9][a-z0-9.+#-]*", lowered)
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", lowered)
    tokens: set[str] = {t for t in latin if len(t) > 1}
    for chunk in chinese:
        tokens.update(chunk[i : i + 2] for i in range(len(chunk) - 1))
    return tokens


def ideal_similarity(title: str, ideal_directions: list[str]) -> tuple[float, str]:
    """Best Jaccard-style overlap between the title and any ideal direction."""
    title_tokens = tokenize(title)
    if not title_tokens:
        return 0.0, ""
    best_ratio = 0.0
    best_ref = ""
    for ideal in ideal_directions:
        ideal_tokens = tokenize(str(ideal))
        if not ideal_tokens:
            continue
        overlap = len(title_tokens & ideal_tokens)
        ratio = overlap / len(ideal_tokens)
        if ratio > best_ratio:
            best_ratio = ratio
            best_ref = str(ideal)
    return best_ratio, best_ref


def load_json(path_or_json: str) -> Any:
    stripped = path_or_json.strip()
    if stripped.startswith(("{", "[")):
        return json.loads(stripped)
    path = Path(path_or_json)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(stripped)


def score_title(title: str, case: dict[str, Any]) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []
    lowered = title.lower()
    topic = str(case.get("topic", "")).lower()
    for token in topic.replace("/", " ").replace("-", " ").split():
        if len(token) > 2 and token in lowered:
            score += 2
            reasons.append(f"topic:{token}")
    for mechanism in case.get("preferred_mechanisms", []):
        mechanism_text = str(mechanism).lower()
        if mechanism_text in lowered:
            score += 2
            reasons.append(f"mechanism:{mechanism}")
        else:
            expanded = mechanism_lib.keywords_for_name(mechanism_text)
            hit = next((word for word in expanded if word in lowered), None)
            if hit:
                score += 1
                reasons.append(f"mechanism~{mechanism}:{hit}")
    for marker in mechanism_lib.strong_markers():
        if marker in lowered:
            score += 1
            reasons.append(f"marker:{marker}")
    ideal_directions = case.get("ideal_directions", [])
    if ideal_directions:
        ratio, ref = ideal_similarity(title, ideal_directions)
        if ratio > 0:
            bonus = round(min(ratio, 1.0) * 3, 2)
            score += bonus
            reasons.append(f"ideal:{ratio:.2f}->{ref}")
    for bad in case.get("avoid", []):
        if str(bad).lower() in lowered:
            score -= 3
            reasons.append(f"avoid:{bad}")
    return {"title": title, "score": round(score, 2), "reasons": reasons}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evals", default=str(DEFAULT_EVALS))
    parser.add_argument("--case-id", default="")
    parser.add_argument("--titles-json", required=True, help="JSON array/object, or path. Object may contain a 'titles' or 'candidates' array.")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evals = load_json(args.evals)
    cases = evals.get("cases", [])
    if args.case_id:
        cases = [case for case in cases if case.get("id") == args.case_id]
        if not cases:
            raise SystemExit(f"No eval case matched --case-id: {args.case_id}")
    titles_payload = load_json(args.titles_json)
    if isinstance(titles_payload, dict):
        titles = titles_payload.get("titles") or titles_payload.get("candidates") or []
    else:
        titles = titles_payload
    titles = [str(item.get("title") if isinstance(item, dict) else item) for item in titles]

    results = []
    for case in cases:
        scored = [score_title(title, case) for title in titles]
        scored.sort(key=lambda item: item["score"], reverse=True)
        results.append({"case_id": case.get("id"), "top": scored[:5]})

    if args.format == "json":
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    else:
        print("# Title Eval Results\n")
        for result in results:
            print(f"## {result['case_id']}\n")
            for item in result["top"]:
                print(f"- score={item['score']} title={item['title']}")
                if item["reasons"]:
                    print(f"  - reasons: {', '.join(item['reasons'])}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
