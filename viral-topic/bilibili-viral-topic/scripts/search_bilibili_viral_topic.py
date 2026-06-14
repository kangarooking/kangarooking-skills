#!/usr/bin/env python3
"""Find low-follower viral Bilibili videos via public JSON endpoints."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests


BASE = "https://api.bilibili.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        if isinstance(value, str):
            value = value.replace(",", "").strip()
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default="", help="Comma-separated Bilibili keywords.")
    parser.add_argument("--keyword", action="append", default=[], help="Explicit keyword. Can be repeated.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--max-followers", type=int, default=100_000)
    parser.add_argument("--min-play", type=int, default=10_000)
    parser.add_argument("--min-play-follower-ratio", type=float, default=2.0)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--page-size", type=int, default=30)
    parser.add_argument("--orders", default="pubdate,click", help="Search orders, comma-separated.")
    parser.add_argument("--ranking-rids", default="", help="Optional ranking rids, e.g. '0,188'. Empty disables ranking.")
    parser.add_argument("--request-sleep", type=float, default=0.6)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--cache-path", default=str(Path.home() / ".cache/account-growth/bilibili_followers.json"))
    parser.add_argument("--cache-ttl-hours", type=float, default=24.0)
    parser.add_argument("--include-unknown-followers", action="store_true")
    parser.add_argument("--input-json", help="Load Bilibili API-like payload or normalized list from a local JSON file.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def keywords_from_args(args: argparse.Namespace) -> list[str]:
    values: list[str] = []
    values.extend(args.keyword)
    values.extend(part.strip() for part in args.topic.replace("，", ",").split(","))
    deduped = [value for value in dict.fromkeys(v.strip() for v in values if v.strip())]
    if not deduped:
        raise RuntimeError("Provide --topic or --keyword")
    return deduped[:12]


def strip_html(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def to_iso_from_ts(value: Any) -> str:
    timestamp = as_int(value)
    if not timestamp:
        return ""
    return dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).isoformat()


def is_recent(pubdate: Any, days: int) -> bool:
    if days <= 0:
        return True
    timestamp = as_int(pubdate)
    if not timestamp:
        return False
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    published = dt.datetime.fromtimestamp(timestamp, dt.timezone.utc)
    return published >= cutoff


def freshness_score(pubdate: Any, days: int) -> float:
    if days <= 0:
        return 0.0
    timestamp = as_int(pubdate)
    if not timestamp:
        return 0.0
    published = dt.datetime.fromtimestamp(timestamp, dt.timezone.utc)
    age_days = max(0.0, (dt.datetime.now(dt.timezone.utc) - published).total_seconds() / 86400)
    return max(0.0, min(100.0, (1.0 - age_days / days) * 100.0))


def make_session() -> requests.Session:
    session = requests.Session()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://www.bilibili.com",
        "Connection": "keep-alive",
    }
    cookie = os.getenv("BILIBILI_COOKIE", "").strip()
    if cookie:
        headers["Cookie"] = cookie
    session.headers.update(headers)
    return session


def bili_get(
    session: requests.Session,
    path: str,
    params: dict[str, Any],
    referer: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    url = BASE + path
    last_error = ""
    for attempt in range(args.retries + 1):
        try:
            response = session.get(url, params=params, headers={"Referer": referer}, timeout=20)
            if response.status_code == 412:
                raise RuntimeError("HTTP 412 Precondition Failed")
            response.raise_for_status()
            payload = response.json()
            if as_int(payload.get("code"), 0) != 0:
                raise RuntimeError(f"Bilibili code={payload.get('code')} message={payload.get('message')}")
            return payload
        except Exception as exc:
            last_error = str(exc)
            if attempt >= args.retries:
                break
            time.sleep(args.request_sleep * (attempt + 1) * 2)
    raise RuntimeError(last_error)


def normalize_search_item(item: dict[str, Any], source: str, source_query: str) -> dict[str, Any]:
    return {
        "platform": "bilibili",
        "content_id": str(item.get("bvid") or item.get("aid") or ""),
        "aid": str(item.get("aid") or item.get("id") or ""),
        "url": f"https://www.bilibili.com/video/{item.get('bvid')}" if item.get("bvid") else str(item.get("arcurl") or ""),
        "title": strip_html(item.get("title")),
        "author_id": str(item.get("mid") or ""),
        "author_name": strip_html(item.get("author")),
        "published_at": to_iso_from_ts(item.get("pubdate")),
        "pubdate_ts": as_int(item.get("pubdate")),
        "view_count": as_int(item.get("play")),
        "like_count": as_int(item.get("like")),
        "comment_count": as_int(item.get("review")),
        "share_count": as_int(item.get("share")),
        "save_count": as_int(item.get("favorites")),
        "coin_count": as_int(item.get("coin")),
        "danmaku_count": as_int(item.get("video_review") or item.get("danmaku")),
        "duration": str(item.get("duration") or ""),
        "tag": str(item.get("tag") or ""),
        "source": source,
        "source_query": source_query,
        "raw": item,
    }


def normalize_ranking_item(item: dict[str, Any], source: str, source_query: str) -> dict[str, Any]:
    owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
    stat = item.get("stat") if isinstance(item.get("stat"), dict) else {}
    bvid = str(item.get("bvid") or "")
    return {
        "platform": "bilibili",
        "content_id": bvid or str(item.get("aid") or ""),
        "aid": str(item.get("aid") or ""),
        "url": f"https://www.bilibili.com/video/{bvid}" if bvid else "",
        "title": strip_html(item.get("title")),
        "author_id": str(owner.get("mid") or ""),
        "author_name": strip_html(owner.get("name")),
        "published_at": to_iso_from_ts(item.get("pubdate")),
        "pubdate_ts": as_int(item.get("pubdate")),
        "view_count": as_int(stat.get("view") or stat.get("vv")),
        "like_count": as_int(stat.get("like")),
        "comment_count": as_int(stat.get("reply")),
        "share_count": as_int(stat.get("share")),
        "save_count": as_int(stat.get("favorite")),
        "coin_count": as_int(stat.get("coin")),
        "danmaku_count": as_int(stat.get("danmaku")),
        "duration": str(item.get("duration") or ""),
        "tag": "",
        "source": source,
        "source_query": source_query,
        "raw": item,
    }


def fetch_search(session: requests.Session, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    orders = [order.strip() for order in args.orders.split(",") if order.strip()]
    for keyword in keywords_from_args(args):
        for order in orders:
            for page in range(1, args.pages + 1):
                params = {
                    "search_type": "video",
                    "keyword": keyword,
                    "order": order,
                    "page": page,
                    "page_size": min(args.page_size, 50),
                }
                try:
                    payload = bili_get(
                        session,
                        "/x/web-interface/search/type",
                        params,
                        "https://search.bilibili.com/video?keyword="
                        + urllib.parse.quote(keyword, safe=""),
                        args,
                    )
                    items = (payload.get("data") or {}).get("result") or []
                    normalized = [
                        normalize_search_item(item, f"search:{order}", keyword)
                        for item in items
                        if isinstance(item, dict)
                    ]
                    results.extend(normalized)
                    statuses.append({"source": "bilibili_search", "keyword": keyword, "order": order, "page": page, "ok": True, "count": len(normalized), "error": ""})
                    if not normalized:
                        break
                except Exception as exc:
                    statuses.append({"source": "bilibili_search", "keyword": keyword, "order": order, "page": page, "ok": False, "count": 0, "error": str(exc)})
                    break
                time.sleep(args.request_sleep)
    return results, statuses


def fetch_rankings(session: requests.Session, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    rids = [rid.strip() for rid in args.ranking_rids.split(",") if rid.strip()]
    for rid in rids:
        try:
            payload = bili_get(
                session,
                "/x/web-interface/ranking/v2",
                {"rid": rid, "type": "all"},
                "https://www.bilibili.com/v/popular/rank/all",
                args,
            )
            items = (payload.get("data") or {}).get("list") or []
            normalized = [
                normalize_ranking_item(item, "ranking", f"rid:{rid}")
                for item in items
                if isinstance(item, dict)
            ]
            results.extend(normalized)
            statuses.append({"source": "bilibili_ranking", "rid": rid, "ok": True, "count": len(normalized), "error": ""})
        except Exception as exc:
            statuses.append({"source": "bilibili_ranking", "rid": rid, "ok": False, "count": 0, "error": str(exc)})
        time.sleep(args.request_sleep)
    return results, statuses


def load_cache(path: str) -> dict[str, Any]:
    cache_path = Path(path)
    if not cache_path.exists():
        return {}
    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def save_cache(path: str, cache: dict[str, Any]) -> None:
    cache_path = Path(path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=2)


def cached_follower(cache: dict[str, Any], mid: str, ttl_hours: float) -> int | None:
    item = cache.get(mid)
    if not isinstance(item, dict):
        return None
    fetched_at = as_int(item.get("fetched_at"))
    if not fetched_at:
        return None
    age_hours = (time.time() - fetched_at) / 3600
    if age_hours > ttl_hours:
        return None
    return as_int(item.get("follower"))


def fetch_follower(session: requests.Session, mid: str, args: argparse.Namespace) -> int:
    payload = bili_get(
        session,
        "/x/relation/stat",
        {"vmid": mid},
        f"https://space.bilibili.com/{mid}",
        args,
    )
    return as_int((payload.get("data") or {}).get("follower"))


def enrich_followers(
    session: requests.Session,
    items: list[dict[str, Any]],
    args: argparse.Namespace,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    cache = load_cache(args.cache_path)
    followers: dict[str, int] = {}
    statuses: list[dict[str, Any]] = []
    mids = list(dict.fromkeys(str(item.get("author_id") or "") for item in items if item.get("author_id")))
    changed = False
    for mid in mids:
        cached = cached_follower(cache, mid, args.cache_ttl_hours)
        if cached is not None:
            followers[mid] = cached
            statuses.append({"source": "bilibili_relation_stat", "mid": mid, "ok": True, "cached": True, "follower": cached, "error": ""})
            continue
        try:
            follower = fetch_follower(session, mid, args)
            followers[mid] = follower
            cache[mid] = {"follower": follower, "fetched_at": int(time.time())}
            changed = True
            statuses.append({"source": "bilibili_relation_stat", "mid": mid, "ok": True, "cached": False, "follower": follower, "error": ""})
        except Exception as exc:
            statuses.append({"source": "bilibili_relation_stat", "mid": mid, "ok": False, "cached": False, "follower": None, "error": str(exc)})
        time.sleep(args.request_sleep)
    if changed:
        save_cache(args.cache_path, cache)
    return followers, statuses


def score_item(item: dict[str, Any], follower_count: int | None, args: argparse.Namespace) -> dict[str, Any]:
    views = as_int(item.get("view_count"))
    likes = as_int(item.get("like_count"))
    comments = as_int(item.get("comment_count"))
    shares = as_int(item.get("share_count"))
    saves = as_int(item.get("save_count"))
    coins = as_int(item.get("coin_count"))
    danmaku = as_int(item.get("danmaku_count"))
    engagement = likes + coins * 3 + saves * 2 + shares * 3 + comments * 2 + danmaku
    hot_score = views + likes * 10 + coins * 30 + saves * 20 + shares * 30 + comments * 20 + danmaku * 5

    play_follower_ratio = None
    engagement_follower_ratio = None
    if follower_count:
        denominator = max(follower_count, 1000)
        play_follower_ratio = views / denominator
        engagement_follower_ratio = engagement / denominator

    breakout_score = (
        math.log1p(max(views, 0)) * 0.40
        + math.log1p(max(engagement, 0)) * 0.30
        + min(100.0, (play_follower_ratio or 0.0) * 8.0) * 0.25
        + freshness_score(item.get("pubdate_ts"), args.days) * 0.05
    )

    evidence: list[str] = []
    if follower_count is not None and follower_count <= args.max_followers:
        evidence.append(f"low_follower_author:{follower_count}")
    if follower_count and views >= follower_count:
        evidence.append(f"plays_exceed_followers:{views / max(follower_count, 1):.2f}x")
    if play_follower_ratio is not None and play_follower_ratio >= args.min_play_follower_ratio:
        evidence.append(f"high_play_follower_ratio:{play_follower_ratio:.2f}x")
    if engagement_follower_ratio is not None and engagement_follower_ratio >= 0.1:
        evidence.append(f"high_engagement_per_follower:{engagement_follower_ratio:.3f}")
    if (saves + coins) / max(views, 1) >= 0.02 and (saves + coins) >= 100:
        evidence.append("strong_save_coin_signal")
    if follower_count is None:
        evidence.append("unknown_followers")

    output = dict(item)
    output.update(
        {
            "follower_count": follower_count,
            "hot_score": round(float(hot_score), 2),
            "breakout_score": round(float(breakout_score), 2),
            "engagement": round(float(engagement), 2),
            "play_follower_ratio": round(play_follower_ratio, 5) if play_follower_ratio is not None else None,
            "engagement_follower_ratio": round(engagement_follower_ratio, 5) if engagement_follower_ratio is not None else None,
            "evidence": evidence,
        }
    )
    return output


def passes_filters(item: dict[str, Any], args: argparse.Namespace) -> bool:
    follower = item.get("follower_count")
    if follower is None:
        if not args.include_unknown_followers:
            return False
    elif int(follower) > args.max_followers:
        return False
    if as_int(item.get("view_count")) < args.min_play:
        return False
    ratio = item.get("play_follower_ratio")
    if follower is not None and ratio is not None and float(ratio) < args.min_play_follower_ratio:
        return False
    return True


def extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("results", "items", "videos"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    data = payload.get("data")
    if isinstance(data, dict):
        if isinstance(data.get("result"), list):
            return [item for item in data["result"] if isinstance(item, dict)]
        if isinstance(data.get("list"), list):
            return [item for item in data["list"] if isinstance(item, dict)]
    return []


def load_input_json(path: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    records = extract_records(payload)
    normalized: list[dict[str, Any]] = []
    for record in records:
        if record.get("platform") == "bilibili" and "breakout_score" in record:
            normalized.append(record)
        elif "stat" in record and "owner" in record:
            normalized.append(normalize_ranking_item(record, "input_json", ""))
        else:
            normalized.append(normalize_search_item(record, "input_json", ""))
    return normalized


def collect_live(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    session = make_session()
    search_items, search_statuses = fetch_search(session, args)
    ranking_items, ranking_statuses = fetch_rankings(session, args)
    all_items = search_items + ranking_items

    by_id: dict[str, dict[str, Any]] = {}
    for item in all_items:
        content_id = str(item.get("content_id") or item.get("aid") or "")
        if not content_id:
            continue
        existing = by_id.get(content_id)
        if not existing or as_int(item.get("view_count")) > as_int(existing.get("view_count")):
            by_id[content_id] = item

    recent_items = [item for item in by_id.values() if is_recent(item.get("pubdate_ts"), args.days)]
    followers, follower_statuses = enrich_followers(session, recent_items, args)
    scored = [
        score_item(item, followers.get(str(item.get("author_id") or "")), args)
        for item in recent_items
    ]
    statuses = search_statuses + ranking_statuses + follower_statuses
    statuses.append({"source": "dedupe_recent", "ok": True, "count": len(recent_items), "error": ""})
    return scored, statuses


def render_markdown(output: dict[str, Any]) -> str:
    lines = [
        "# Bilibili Viral Topic Results",
        "",
        f"- Run at: {output['run_at']}",
        f"- Window: last {output['config']['days']} days",
        f"- Results: {output['summary']['returned']} / {output['summary']['candidates']}",
        "",
    ]
    for index, item in enumerate(output["results"], 1):
        followers = item.get("follower_count")
        follower_text = "unknown" if followers is None else f"{followers:,}"
        ratio = item.get("play_follower_ratio")
        ratio_text = "n/a" if ratio is None else f"{ratio:.2f}x"
        lines.extend(
            [
                f"## {index}. {item['title']}",
                "",
                f"- URL: {item['url']}",
                f"- UP主: {item['author_name']} ({follower_text} followers)",
                f"- Published: {item['published_at']}",
                f"- Plays: {item['view_count']:,}; Likes: {item['like_count']:,}; Coins: {item['coin_count']:,}; Saves: {item['save_count']:,}; Comments: {item['comment_count']:,}; Danmaku: {item['danmaku_count']:,}",
                f"- Play/follower ratio: {ratio_text}",
                f"- Breakout score: {item['breakout_score']}",
                f"- Evidence: {', '.join(item['evidence'])}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    if args.dry_run:
        planned = {
            "dry_run": True,
            "keywords": keywords_from_args(args),
            "orders": [order.strip() for order in args.orders.split(",") if order.strip()],
            "ranking_rids": [rid.strip() for rid in args.ranking_rids.split(",") if rid.strip()],
            "args": vars(args),
            "cookie": "***redacted***" if os.getenv("BILIBILI_COOKIE") else "",
        }
        if "BILIBILI_COOKIE" in planned["args"]:
            planned["args"]["BILIBILI_COOKIE"] = "***redacted***"
        print(json.dumps(planned, ensure_ascii=False, indent=2))
        return 0

    if args.input_json:
        candidates = load_input_json(args.input_json, args)
        scored = [
            item if "breakout_score" in item else score_item(item, item.get("follower_count"), args)
            for item in candidates
            if is_recent(item.get("pubdate_ts") or 0, args.days) or item.get("published_at")
        ]
        statuses = [{"source": "input_json", "ok": True, "count": len(scored), "error": ""}]
    else:
        scored, statuses = collect_live(args)

    filtered = [item for item in scored if passes_filters(item, args)]
    filtered.sort(
        key=lambda item: (
            float(item.get("breakout_score") or 0),
            float(item.get("play_follower_ratio") or 0),
            as_int(item.get("view_count")),
        ),
        reverse=True,
    )
    results = filtered[: args.limit]
    output = {
        "platform": "bilibili",
        "run_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "version": "v1",
        "config": {
            "keywords": [] if args.input_json else keywords_from_args(args),
            "days": args.days,
            "max_followers": args.max_followers,
            "min_play": args.min_play,
            "min_play_follower_ratio": args.min_play_follower_ratio,
            "limit": args.limit,
            "pages": args.pages,
            "page_size": args.page_size,
            "orders": args.orders,
            "ranking_rids": args.ranking_rids,
        },
        "summary": {
            "candidates": len(scored),
            "matched": len(filtered),
            "returned": len(results),
        },
        "source_status": statuses,
        "results": results,
    }
    if args.format == "markdown":
        print(render_markdown(output))
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
