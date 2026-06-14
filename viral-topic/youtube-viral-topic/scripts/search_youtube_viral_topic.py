#!/usr/bin/env python3
"""Find recent viral YouTube videos via YouTube Data API v3."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


API_BASE = "https://www.googleapis.com/youtube/v3"
USER_AGENT = "account-growth-youtube-viral-topic/0.1"


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default=os.getenv("YOUTUBE_API_KEY", ""))
    parser.add_argument("--topic", default="", help="Comma-separated topic terms.")
    parser.add_argument("--query", action="append", default=[], help="Explicit YouTube query. Can be repeated.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--min-views", type=int, default=10_000)
    parser.add_argument("--min-engagement", type=int, default=0, help="likes + comments * 2 threshold. Default disables it.")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--max-results-per-query", type=int, default=50)
    parser.add_argument("--region-code", default="US")
    parser.add_argument("--relevance-language", default="")
    parser.add_argument("--video-duration", choices=["any", "short", "medium", "long"], default="any")
    parser.add_argument("--small-channel-threshold", type=int, default=100_000, help="Only used for evidence labels, not filtering.")
    parser.add_argument("--input-json", help="Load a YouTube API-like payload or normalized list from a local JSON file.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def redacted_args(args: argparse.Namespace) -> dict[str, Any]:
    values = vars(args).copy()
    if values.get("api_key"):
        values["api_key"] = "***redacted***"
    return values


def published_after(days: int) -> str:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def split_terms(topic: str) -> list[str]:
    parts = [part.strip() for part in topic.replace("，", ",").split(",") if part.strip()]
    if parts:
        return parts[:10]
    value = topic.strip()
    return [value] if value else []


def build_queries(args: argparse.Namespace) -> list[str]:
    if args.query:
        return [query.strip() for query in args.query if query.strip()]
    terms = split_terms(args.topic)
    if not terms:
        raise RuntimeError("Provide --topic or --query")
    return terms


def get_json(endpoint: str, params: dict[str, Any], api_key: str) -> dict[str, Any]:
    clean_params = {key: value for key, value in params.items() if value not in (None, "")}
    clean_params["key"] = api_key
    url = f"{API_BASE}/{endpoint}?" + urllib.parse.urlencode(clean_params)
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from YouTube {endpoint}: {detail[:300]}") from exc


def chunks(values: list[str], size: int = 50) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def search_videos(args: argparse.Namespace, api_key: str, query: str) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "part": "snippet",
        "type": "video",
        "q": query,
        "order": "viewCount",
        "publishedAfter": published_after(args.days),
        "maxResults": min(args.max_results_per_query, 50),
        "regionCode": args.region_code,
        "relevanceLanguage": args.relevance_language,
    }
    if args.video_duration != "any":
        params["videoDuration"] = args.video_duration
    payload = get_json("search", params, api_key)
    results: list[dict[str, Any]] = []
    for item in payload.get("items", []):
        video_id = ((item.get("id") or {}).get("videoId") or "").strip()
        if not video_id:
            continue
        snippet = item.get("snippet") if isinstance(item.get("snippet"), dict) else {}
        results.append({"video_id": video_id, "source_query": query, "search_snippet": snippet})
    return results


def fetch_video_details(video_ids: list[str], api_key: str) -> dict[str, dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    for batch in chunks(video_ids, 50):
        payload = get_json(
            "videos",
            {"part": "snippet,statistics,contentDetails", "id": ",".join(batch)},
            api_key,
        )
        for item in payload.get("items", []):
            details[str(item.get("id") or "")] = item
    return details


def fetch_channel_details(channel_ids: list[str], api_key: str) -> dict[str, dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    unique_ids = list(dict.fromkeys(cid for cid in channel_ids if cid))
    for batch in chunks(unique_ids, 50):
        payload = get_json(
            "channels",
            {"part": "snippet,statistics", "id": ",".join(batch)},
            api_key,
        )
        for item in payload.get("items", []):
            details[str(item.get("id") or "")] = item
    return details


def parse_duration_seconds(value: str) -> int:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return 0
    hours, minutes, seconds = match.groups()
    return int(hours or 0) * 3600 + int(minutes or 0) * 60 + int(seconds or 0)


def freshness_score(published_at: str, days: int) -> float:
    try:
        published = dt.datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    age_days = max(0.0, (dt.datetime.now(dt.timezone.utc) - published).total_seconds() / 86400)
    if days <= 0:
        return 0.0
    return max(0.0, min(100.0, (1.0 - age_days / days) * 100.0))


def normalize_item(
    video: dict[str, Any],
    channel: dict[str, Any],
    source_query: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    snippet = video.get("snippet") if isinstance(video.get("snippet"), dict) else {}
    stats = video.get("statistics") if isinstance(video.get("statistics"), dict) else {}
    content = video.get("contentDetails") if isinstance(video.get("contentDetails"), dict) else {}
    channel_stats = channel.get("statistics") if isinstance(channel.get("statistics"), dict) else {}
    channel_snippet = channel.get("snippet") if isinstance(channel.get("snippet"), dict) else {}

    video_id = str(video.get("id") or "")
    channel_id = str(snippet.get("channelId") or channel.get("id") or "")
    views = as_int(stats.get("viewCount"))
    likes = as_int(stats.get("likeCount"))
    comments = as_int(stats.get("commentCount"))
    hidden_subscribers = bool(channel_stats.get("hiddenSubscriberCount"))
    subscribers = None if hidden_subscribers else as_int(channel_stats.get("subscriberCount"), 0)
    if subscribers == 0 and "subscriberCount" not in channel_stats:
        subscribers = None

    engagement = likes + comments * 2
    view_subscriber_ratio = views / max(subscribers, 1000) if subscribers else None
    engagement_subscriber_ratio = engagement / max(subscribers, 1000) if subscribers else None
    like_view_rate = likes / max(views, 1)
    comment_view_rate = comments / max(views, 1)
    hot_score = views + likes * 20 + comments * 40
    viral_score = (
        math.log1p(max(views, 0)) * 0.45
        + math.log1p(max(engagement, 0)) * 0.25
        + min(100.0, like_view_rate * 1000.0) * 0.12
        + min(100.0, comment_view_rate * 3000.0) * 0.08
        + freshness_score(str(snippet.get("publishedAt") or ""), args.days) * 0.10
    )

    evidence: list[str] = []
    if views >= args.min_views:
        evidence.append(f"high_views:{views}")
    if engagement >= args.min_engagement and args.min_engagement > 0:
        evidence.append(f"high_engagement:{engagement}")
    if like_view_rate >= 0.03 and likes >= 100:
        evidence.append(f"strong_like_view_rate:{like_view_rate:.3f}")
    if comment_view_rate >= 0.002 and comments >= 50:
        evidence.append(f"active_discussion:{comment_view_rate:.3f}")
    if subscribers is not None and subscribers <= args.small_channel_threshold:
        evidence.append(f"small_channel_signal:{subscribers}")
    if view_subscriber_ratio is not None and view_subscriber_ratio >= 1:
        evidence.append(f"views_exceed_subscribers:{view_subscriber_ratio:.2f}x")
    if hidden_subscribers or subscribers is None:
        evidence.append("unknown_subscribers")

    return {
        "platform": "youtube",
        "content_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": str(snippet.get("title") or ""),
        "description": str(snippet.get("description") or "")[:500],
        "author_id": channel_id,
        "author_name": str(snippet.get("channelTitle") or channel_snippet.get("title") or ""),
        "follower_count": subscribers,
        "subscriber_count": subscribers,
        "hidden_subscriber_count": hidden_subscribers,
        "published_at": str(snippet.get("publishedAt") or ""),
        "view_count": views,
        "like_count": likes,
        "comment_count": comments,
        "share_count": 0,
        "save_count": 0,
        "duration_seconds": parse_duration_seconds(str(content.get("duration") or "")),
        "hot_score": round(float(hot_score), 2),
        "viral_score": round(float(viral_score), 2),
        "breakout_score": round(float(viral_score), 2),
        "view_subscriber_ratio": round(view_subscriber_ratio, 5) if view_subscriber_ratio is not None else None,
        "engagement_subscriber_ratio": round(engagement_subscriber_ratio, 5) if engagement_subscriber_ratio is not None else None,
        "like_view_rate": round(like_view_rate, 5),
        "comment_view_rate": round(comment_view_rate, 5),
        "source_query": source_query,
        "evidence": evidence,
        "raw": {"video": video, "channel": channel},
    }


def passes_filters(item: dict[str, Any], args: argparse.Namespace) -> bool:
    if as_int(item.get("view_count")) < args.min_views:
        return False
    if args.min_engagement > 0:
        engagement = as_int(item.get("like_count")) + as_int(item.get("comment_count")) * 2
        if engagement < args.min_engagement:
            return False
    return True


def extract_video_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("items", "videos", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    data = payload.get("data")
    if isinstance(data, dict):
        return extract_video_records(data)
    return []


def load_input_json(path: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    records = extract_video_records(payload)
    normalized: list[dict[str, Any]] = []
    for record in records:
        if record.get("platform") == "youtube" and ("viral_score" in record or "breakout_score" in record):
            normalized.append(record)
            continue
        video = record.get("video") if isinstance(record.get("video"), dict) else record
        channel = record.get("channel") if isinstance(record.get("channel"), dict) else {}
        source_query = str(record.get("source_query") or record.get("keyword") or "")
        normalized.append(normalize_item(video, channel, source_query, args))
    return normalized


def collect_live(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not args.api_key:
        raise RuntimeError("Set YOUTUBE_API_KEY or pass --api-key")

    searches: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    for query in build_queries(args):
        try:
            items = search_videos(args, args.api_key, query)
            searches.extend(items)
            statuses.append({"source": "youtube_search", "query": query, "ok": True, "count": len(items), "error": ""})
        except Exception as exc:
            statuses.append({"source": "youtube_search", "query": query, "ok": False, "count": 0, "error": str(exc)})

    by_id: dict[str, dict[str, Any]] = {}
    for item in searches:
        by_id.setdefault(item["video_id"], item)
    video_ids = list(by_id.keys())
    video_details = fetch_video_details(video_ids, args.api_key) if video_ids else {}
    channel_ids = [
        str((video.get("snippet") or {}).get("channelId") or "")
        for video in video_details.values()
        if isinstance(video.get("snippet"), dict)
    ]
    channel_details = fetch_channel_details(channel_ids, args.api_key) if channel_ids else {}

    normalized: list[dict[str, Any]] = []
    for video_id, source in by_id.items():
        video = video_details.get(video_id)
        if not video:
            continue
        snippet = video.get("snippet") if isinstance(video.get("snippet"), dict) else {}
        channel = channel_details.get(str(snippet.get("channelId") or ""), {})
        normalized.append(normalize_item(video, channel, str(source.get("source_query") or ""), args))
    statuses.append({"source": "youtube_videos", "ok": True, "count": len(video_details), "error": ""})
    statuses.append({"source": "youtube_channels", "ok": True, "count": len(channel_details), "error": ""})
    return normalized, statuses


def render_markdown(output: dict[str, Any]) -> str:
    lines = [
        "# YouTube Viral Topic Results",
        "",
        f"- Run at: {output['run_at']}",
        f"- Window: last {output['config']['days']} days",
        f"- Results: {output['summary']['returned']} / {output['summary']['candidates']}",
        "",
    ]
    for index, item in enumerate(output["results"], 1):
        subscribers = item.get("subscriber_count")
        sub_text = "unknown" if subscribers is None else f"{subscribers:,}"
        ratio = item.get("view_subscriber_ratio")
        ratio_text = "n/a" if ratio is None else f"{ratio:.2f}x"
        lines.extend(
            [
                f"## {index}. {item['title']}",
                "",
                f"- URL: {item['url']}",
                f"- Channel: {item['author_name']} ({sub_text} subscribers)",
                f"- Published: {item['published_at']}",
                f"- Views: {item['view_count']:,}; Likes: {item['like_count']:,}; Comments: {item['comment_count']:,}",
                f"- View/subscriber ratio: {ratio_text}",
                f"- Viral score: {item['viral_score']}",
                f"- Evidence: {', '.join(item['evidence'])}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    if args.dry_run:
        print(json.dumps({"dry_run": True, "args": redacted_args(args), "queries": build_queries(args)}, ensure_ascii=False, indent=2))
        return 0

    statuses: list[dict[str, Any]] = []
    if args.input_json:
        candidates = load_input_json(args.input_json, args)
        statuses.append({"source": "input_json", "ok": True, "count": len(candidates), "error": ""})
    else:
        candidates, statuses = collect_live(args)

    filtered = [item for item in candidates if passes_filters(item, args)]
    filtered.sort(
        key=lambda item: (
            float(item.get("viral_score") or item.get("breakout_score") or 0),
            as_int(item.get("view_count")),
            float(item.get("like_view_rate") or 0),
        ),
        reverse=True,
    )
    results = filtered[: args.limit]
    output = {
        "platform": "youtube",
        "run_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "version": "v1",
        "config": {
            "queries": build_queries(args) if not args.input_json else [],
            "days": args.days,
            "min_views": args.min_views,
            "min_engagement": args.min_engagement,
            "limit": args.limit,
            "region_code": args.region_code,
            "relevance_language": args.relevance_language,
            "video_duration": args.video_duration,
            "small_channel_threshold": args.small_channel_threshold,
        },
        "summary": {
            "candidates": len(candidates),
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
