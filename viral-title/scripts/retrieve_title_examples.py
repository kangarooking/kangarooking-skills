#!/usr/bin/env python3
"""Retrieve a small relevant slice from title libraries without loading everything."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import mechanism_lib

SKILL_DIR = Path(__file__).resolve().parents[1]
LIB_DIR = SKILL_DIR / "references" / "title-library"
WECHAT_JSON = LIB_DIR / "wechat-public-account-hot-titles.json"
WECHAT_AI_MD = LIB_DIR / "wechat-ai-curated-hot-titles.md"
X_HOOKS_MD = LIB_DIR / "x-hot-hooks.md"
YOUTUBE_TITLES_MD = LIB_DIR / "youtube-hot-titles.md"
BILIBILI_TITLES_MD = LIB_DIR / "bilibili-hot-titles.md"


def tokenize(text: str) -> list[str]:
    text = text.lower()
    latin = re.findall(r"[a-z0-9][a-z0-9.+#-]*", text)
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    pieces: list[str] = latin + chinese
    for chunk in chinese:
        if len(chunk) > 4:
            pieces.extend(chunk[i : i + 2] for i in range(len(chunk) - 1))
    return [p for p in pieces if p.strip()]


def score_text(text: str, query_terms: list[str], mechanism: str = "") -> int:
    lowered = text.lower()
    score = 0
    for term in query_terms:
        if term and term in lowered:
            score += 3 if len(term) > 2 else 1
    if mechanism:
        for word in mechanism_lib.keywords_for_query(mechanism):
            if word in lowered:
                score += 2
    return score


def load_wechat_json() -> list[dict[str, Any]]:
    if not WECHAT_JSON.exists():
        return []
    payload = json.loads(WECHAT_JSON.read_text(encoding="utf-8"))
    return list(payload.get("items", []))


def load_curated_md() -> list[dict[str, Any]]:
    if not WECHAT_AI_MD.exists():
        return []
    items: list[dict[str, Any]] = []
    section = ""
    for line in WECHAT_AI_MD.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if line.startswith("- "):
            title = line[2:].strip()
            if title:
                items.append({"title": title, "source": "wechat-ai-curated", "section": section})
    return items


def load_list_md(path: Path, source: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if line.startswith("- "):
            title = line[2:].strip()
            if title:
                items.append({"title": title, "source": source, "section": section})
    return items


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", default="wechat")
    parser.add_argument("--query", required=True)
    parser.add_argument("--category", default="")
    parser.add_argument("--mechanism", default="")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    limit = max(1, min(args.limit, 20))
    terms = tokenize(args.query)
    candidates: list[dict[str, Any]] = []

    platform = args.platform.lower()

    if platform in {"wechat", "公众号", "weixin", "wechat-public-account"}:
        for item in load_wechat_json():
            if args.category and item.get("category") != args.category:
                continue
            title = str(item.get("title") or "")
            score = score_text(title, terms, args.mechanism)
            if score:
                candidates.append({**item, "source": "wechat-api-library", "match_score": score})

        for item in load_curated_md():
            title = str(item.get("title") or "")
            score = score_text(title, terms, args.mechanism)
            if score:
                candidates.append({**item, "match_score": score})
    elif platform in {"x", "twitter", "推特"}:
        for item in load_list_md(X_HOOKS_MD, "x-hot-hooks"):
            title = str(item.get("title") or "")
            score = score_text(title, terms, args.mechanism)
            if score:
                candidates.append({**item, "match_score": score})
    elif platform in {"youtube", "yt", "油管"}:
        for item in load_list_md(YOUTUBE_TITLES_MD, "youtube-hot-titles"):
            title = str(item.get("title") or "")
            score = score_text(title, terms, args.mechanism)
            if score:
                candidates.append({**item, "match_score": score})
    elif platform in {"bilibili", "b站", "哔哩哔哩", "bili"}:
        for item in load_list_md(BILIBILI_TITLES_MD, "bilibili-hot-titles"):
            title = str(item.get("title") or "")
            score = score_text(title, terms, args.mechanism)
            if score:
                candidates.append({**item, "match_score": score})
    else:
        raise SystemExit(f"Unsupported platform: {args.platform}")

    candidates.sort(key=lambda item: (int(item.get("match_score") or 0), float(item.get("library_score") or 0)), reverse=True)
    results = candidates[:limit]

    if args.format == "json":
        print(json.dumps({"query": args.query, "count": len(results), "results": results}, ensure_ascii=False, indent=2))
    else:
        print(f"# Retrieved Title Examples\n\n- Query: {args.query}\n- Results: {len(results)}\n")
        for index, item in enumerate(results, 1):
            source = item.get("source") or item.get("platform") or "library"
            meta = []
            if item.get("category_name"):
                meta.append(str(item["category_name"]))
            if item.get("section"):
                meta.append(str(item["section"]))
            print(f"{index}. {item.get('title')}  ")
            print(f"   - source: {source}; score: {item.get('match_score')}; {'; '.join(meta)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
