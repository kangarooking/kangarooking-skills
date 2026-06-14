#!/usr/bin/env python3
"""Find low-follower viral posts on X/Twitter via twitterapi.io."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


API_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"
USER_AGENT = "account-growth-x-viral-topic/0.1"


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default=os.getenv("TWITTERAPI_IO_KEY") or os.getenv("TWITTER_API_KEY") or "")
    parser.add_argument("--topic", default="")
    parser.add_argument("--query", action="append", default=[], help="Advanced-search query. Can be repeated.")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--max-followers", type=int, default=50_000)
    parser.add_argument("--min-views", type=int, default=10_000)
    parser.add_argument("--min-engagement", type=float, default=100.0)
    parser.add_argument("--min-faves", type=int, default=20)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--query-types", default="Top,Latest")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--include-replies", action="store_true")
    parser.add_argument("--include-unknown-followers", action="store_true")
    parser.add_argument("--input-json", help="Load a twitterapi.io response or list of tweets from a local JSON file.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def redacted_args(args: argparse.Namespace) -> dict[str, Any]:
    values = vars(args).copy()
    if values.get("api_key"):
        values["api_key"] = "***redacted***"
    return values


def since_date(days: int) -> str:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    return cutoff.date().isoformat()


def topic_terms(topic: str) -> list[str]:
    raw = [part.strip() for part in topic.replace("，", ",").split(",") if part.strip()]
    if raw:
        return raw[:8]
    words = topic.strip()
    return [words] if words else []


def quote_term(term: str) -> str:
    term = term.strip()
    if not term:
        return ""
    if " " in term and not (term.startswith('"') and term.endswith('"')):
        return f'"{term}"'
    return term


def build_queries(args: argparse.Namespace) -> list[str]:
    if args.query:
        return [query.strip() for query in args.query if query.strip()]
    terms = [quote_term(term) for term in topic_terms(args.topic)]
    terms = [term for term in terms if term]
    if not terms:
        raise RuntimeError("Provide --topic or --query")
    term_expr = " OR ".join(terms[:6])
    parts = [f"({term_expr})", f"since:{since_date(args.days)}", f"min_faves:{args.min_faves}"]
    if args.lang:
        parts.insert(1, f"lang:{args.lang}")
    if not args.include_replies:
        parts.append("-filter:replies")
    return [" ".join(parts)]


def fetch_query(api_key: str, query: str, query_type: str) -> dict[str, Any]:
    params = urllib.parse.urlencode({"query": query, "queryType": query_type})
    request = urllib.request.Request(
        f"{API_URL}?{params}",
        headers={"X-API-Key": api_key, "Accept": "application/json", "User-Agent": USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:300]}") from exc
    return json.loads(data)


def extract_tweets(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("tweets", "data", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = value.get("tweets") or value.get("items")
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []


def author_handle(tweet: dict[str, Any]) -> str:
    author = tweet.get("author") if isinstance(tweet.get("author"), dict) else {}
    return str(
        author.get("userName")
        or author.get("username")
        or author.get("screen_name")
        or tweet.get("authorUsername")
        or ""
    ).lstrip("@")


def author_followers(tweet: dict[str, Any]) -> int:
    author = tweet.get("author") if isinstance(tweet.get("author"), dict) else {}
    for key in ("followers", "followersCount", "followers_count", "follower_count"):
        value = author.get(key)
        if value is not None:
            return as_int(value)
    public_metrics = author.get("public_metrics") if isinstance(author.get("public_metrics"), dict) else {}
    return as_int(public_metrics.get("followers_count"))


def tweet_id(tweet: dict[str, Any]) -> str:
    return str(tweet.get("id_str") or tweet.get("id") or tweet.get("tweet_id") or "")


def tweet_text(tweet: dict[str, Any]) -> str:
    return str(tweet.get("text") or tweet.get("full_text") or tweet.get("content") or "")


def metric(tweet: dict[str, Any], *keys: str) -> int:
    for key in keys:
        if key in tweet:
            return as_int(tweet.get(key))
    metrics = tweet.get("public_metrics") if isinstance(tweet.get("public_metrics"), dict) else {}
    for key in keys:
        if key in metrics:
            return as_int(metrics.get(key))
    return 0


def normalize_tweet(tweet: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    tid = tweet_id(tweet)
    handle = author_handle(tweet)
    author = tweet.get("author") if isinstance(tweet.get("author"), dict) else {}
    followers = author_followers(tweet)
    likes = metric(tweet, "likeCount", "favorite_count", "like_count")
    reposts = metric(tweet, "retweetCount", "retweet_count", "repost_count")
    replies = metric(tweet, "replyCount", "reply_count")
    views = metric(tweet, "viewCount", "view_count", "impression_count")
    bookmarks = metric(tweet, "bookmarkCount", "bookmark_count")
    engagement = likes + reposts * 3 + replies * 2 + bookmarks * 2 + views / 1000
    engagement_follower_ratio = engagement / max(followers, 500) if followers else 0.0
    view_follower_ratio = views / max(followers, 500) if followers else 0.0
    bookmark_like_ratio = bookmarks / max(likes, 1) if bookmarks else 0.0
    breakout_score = (
        math.log1p(max(engagement, 0)) * 0.45
        + min(100.0, engagement_follower_ratio * 60.0) * 0.25
        + min(100.0, view_follower_ratio * 8.0) * 0.20
        + min(100.0, bookmark_like_ratio * 100.0) * 0.10
    )

    evidence: list[str] = []
    if followers and followers <= args.max_followers:
        evidence.append(f"low_follower_author:{followers}")
    if followers and views >= followers:
        evidence.append(f"views_exceed_followers:{view_follower_ratio:.2f}x")
    if followers and engagement_follower_ratio >= 0.02:
        evidence.append(f"high_engagement_per_follower:{engagement_follower_ratio:.3f}")
    if bookmark_like_ratio >= 0.15:
        evidence.append(f"save_intent:{bookmark_like_ratio:.2f}")
    if not followers:
        evidence.append("unknown_followers")

    url = tweet.get("url") or (f"https://x.com/{handle}/status/{tid}" if handle and tid else f"https://x.com/i/web/status/{tid}")
    text = tweet_text(tweet)
    return {
        "platform": "x",
        "content_id": tid,
        "url": url,
        "title": text[:120],
        "summary": text,
        "author_id": str(author.get("id") or author.get("rest_id") or handle),
        "author_name": author.get("name") or handle,
        "author_handle": handle,
        "follower_count": followers or None,
        "published_at": tweet.get("createdAt") or tweet.get("created_at") or "",
        "view_count": views,
        "like_count": likes,
        "comment_count": replies,
        "share_count": reposts,
        "save_count": bookmarks,
        "hot_score": round(float(engagement), 2),
        "breakout_score": round(float(breakout_score), 2),
        "engagement_follower_ratio": round(engagement_follower_ratio, 5) if followers else None,
        "view_follower_ratio": round(view_follower_ratio, 5) if followers else None,
        "bookmark_like_ratio": round(bookmark_like_ratio, 5) if bookmarks else None,
        "evidence": evidence,
        "raw": tweet,
    }


def passes_filters(item: dict[str, Any], args: argparse.Namespace) -> bool:
    followers = item.get("follower_count")
    if followers is None:
        if not args.include_unknown_followers:
            return False
    elif int(followers) > args.max_followers:
        return False
    if as_int(item.get("view_count")) >= args.min_views:
        return True
    if float(item.get("hot_score") or 0) >= args.min_engagement:
        return True
    return False


def load_input(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return extract_tweets(payload)


def collect_tweets(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    queries = build_queries(args)
    if args.input_json:
        tweets = load_input(args.input_json)
        return tweets, [{"source": "input_json", "ok": True, "count": len(tweets), "error": ""}], queries
    if not args.api_key:
        raise RuntimeError("Set TWITTERAPI_IO_KEY or TWITTER_API_KEY, or use --input-json")

    query_types = [item.strip() for item in args.query_types.split(",") if item.strip()]
    statuses: list[dict[str, Any]] = []
    tweets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        for query_type in query_types:
            try:
                payload = fetch_query(args.api_key, query, query_type)
                batch = extract_tweets(payload)
                statuses.append({"source": "twitterapi.io", "query": query, "query_type": query_type, "ok": True, "count": len(batch), "error": ""})
                for tweet in batch:
                    tid = tweet_id(tweet)
                    key = tid or json.dumps(tweet, sort_keys=True)[:200]
                    if key not in seen:
                        seen.add(key)
                        tweets.append(tweet)
            except Exception as exc:
                statuses.append({"source": "twitterapi.io", "query": query, "query_type": query_type, "ok": False, "count": 0, "error": str(exc)})
    return tweets, statuses, queries


def format_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# X Viral Topic Results",
        "",
        f"- Queries: {' | '.join(payload['query'].get('queries') or [])}",
        f"- Window days: {payload['query'].get('days')}",
        f"- Results: {len(payload['results'])}",
        "",
    ]
    for index, item in enumerate(payload["results"], 1):
        followers = item.get("follower_count") if item.get("follower_count") is not None else "unknown"
        lines.extend(
            [
                f"## {index}. @{item.get('author_handle') or ''}",
                "",
                f"- URL: {item['url']}",
                f"- Text: {item.get('summary') or item.get('title')}",
                f"- Followers: {followers}; views: {item['view_count']}; likes: {item['like_count']}; reposts: {item['share_count']}; replies: {item['comment_count']}; bookmarks: {item['save_count']}",
                f"- Score: {item['breakout_score']}; evidence: {', '.join(item['evidence'])}",
                "",
            ]
        )
    if payload.get("source_status"):
        lines.extend(["## Source Status", ""])
        for status in payload["source_status"]:
            lines.append(
                f"- {status.get('source')} {status.get('query_type', '')}: ok={status.get('ok')} count={status.get('count', '')} error={status.get('error', '')}"
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    queries = build_queries(args)
    if args.dry_run:
        print(json.dumps({"queries": queries, "args": redacted_args(args)}, ensure_ascii=False, indent=2))
        return 0

    tweets, source_status, queries = collect_tweets(args)
    results = [normalize_tweet(tweet, args) for tweet in tweets]
    results = [item for item in results if passes_filters(item, args)]
    results.sort(
        key=lambda item: (
            float(item.get("breakout_score") or 0),
            float(item.get("engagement_follower_ratio") or 0),
            float(item.get("hot_score") or 0),
        ),
        reverse=True,
    )
    payload = {
        "query": {
            "topic": args.topic,
            "queries": queries,
            "days": args.days,
            "max_followers": args.max_followers,
            "min_views": args.min_views,
            "min_engagement": args.min_engagement,
        },
        "source_status": source_status,
        "results": results[: args.limit],
    }
    if args.format == "markdown":
        print(format_markdown(payload), end="")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
