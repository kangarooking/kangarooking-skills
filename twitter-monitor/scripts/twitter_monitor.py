#!/usr/bin/env python3
"""Fetch recent X/Twitter posts through twitterapi.io and write JSON or CSV."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any


API_BASE = "https://api.twitterapi.io/twitter/tweet/advanced_search"
UTC = timezone.utc

FIELDNAMES = [
    "推文内容",
    "日期",
    "推文链接",
    "推文ID",
    "作者",
    "作者ID",
    "阅读量",
    "点赞数",
    "转发数",
    "评论数",
    "收藏数",
    "是否回复",
    "抓取时间",
]


def normalize_account(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("empty account value")
    match = re.search(r"(?:x\.com|twitter\.com)/@?([A-Za-z0-9_]{1,15})", value)
    if match:
        return match.group(1)
    value = value.removeprefix("@").strip().strip("/")
    if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", value):
        raise ValueError(f"invalid X account id: {value!r}")
    return value


def parse_accounts(args: argparse.Namespace) -> list[str]:
    raw_values: list[str] = []
    if args.accounts:
        for chunk in args.accounts:
            raw_values.extend(part for part in chunk.split(",") if part.strip())
    if args.accounts_file:
        data = json.loads(Path(args.accounts_file).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("--accounts-file must contain a JSON list")
        for item in data:
            if isinstance(item, str):
                raw_values.append(item)
            else:
                raise ValueError("--accounts-file items must be strings")

    accounts: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        account = normalize_account(value)
        key = account.lower()
        if key not in seen:
            seen.add(key)
            accounts.append(account)
    if not accounts:
        raise ValueError("provide at least one account via --accounts or --accounts-file")
    return accounts


def parse_datetime(value: str, end_of_day: bool = False) -> datetime:
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        suffix = "23:59:59" if end_of_day else "00:00:00"
        return datetime.fromisoformat(f"{value}T{suffix}+00:00")
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def parse_tweet_time(value: Any) -> int | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def twitter_time(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%d_%H:%M:%S_UTC")


def build_query(account: str, args: argparse.Namespace) -> str:
    parts = [f"from:{account}"]
    if args.since_hours:
        parts.append(f"since:{twitter_time(datetime.now(UTC) - timedelta(hours=args.since_hours))}")
    if args.since_date:
        parts.append(f"since:{twitter_time(parse_datetime(args.since_date))}")
    if args.until_date:
        parts.append(f"until:{twitter_time(parse_datetime(args.until_date, end_of_day=True))}")
    if args.include_native_retweets:
        parts.append("include:nativeretweets")
    return " ".join(parts)


def get_json(url: str, api_key: str, params: dict[str, str], timeout: int) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_tweets(account: str, api_key: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    tweets: list[dict[str, Any]] = []
    cursor = None

    for page in range(1, args.pages + 1):
        params = {"query": build_query(account, args), "queryType": "Latest"}
        if cursor:
            params["cursor"] = cursor

        try:
            data = get_json(API_BASE, api_key, params, args.timeout)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"twitterapi.io HTTP {exc.code} for @{account}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"twitterapi.io request failed for @{account}: {exc.reason}") from exc

        page_tweets = data.get("tweets") or []
        if not isinstance(page_tweets, list):
            raise RuntimeError(f"unexpected tweets payload for @{account}: {type(page_tweets).__name__}")
        tweets.extend(page_tweets)

        if args.verbose:
            print(f"@{account}: fetched page {page}, tweets={len(page_tweets)}", file=sys.stderr)

        cursor = data.get("next_cursor") or data.get("nextCursor")
        if not data.get("has_next_page") or not cursor:
            break
        if page < args.pages:
            time.sleep(args.page_delay)

    return tweets


def format_record(tweet: dict[str, Any], account: str, fetched_at_ms: int) -> dict[str, Any]:
    tweet_id = str(tweet.get("id_str") or tweet.get("id") or "")
    author = tweet.get("author") if isinstance(tweet.get("author"), dict) else {}
    return {
        "推文内容": tweet.get("text", ""),
        "日期": parse_tweet_time(tweet.get("createdAt")),
        "推文链接": f"https://x.com/{account}/status/{tweet_id}" if tweet_id else "",
        "推文ID": tweet_id,
        "作者": author.get("name") or account,
        "作者ID": account,
        "阅读量": tweet.get("viewCount", 0),
        "点赞数": tweet.get("likeCount", 0),
        "转发数": tweet.get("retweetCount", 0),
        "评论数": tweet.get("replyCount", 0),
        "收藏数": tweet.get("bookmarkCount", 0),
        "是否回复": tweet.get("isReply", False),
        "抓取时间": fetched_at_ms,
    }


def dedupe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for record in records:
        tweet_id = str(record.get("推文ID") or "")
        if tweet_id and tweet_id in seen:
            continue
        if tweet_id:
            seen.add(tweet_id)
        unique.append(record)
    return unique


def write_output(records: list[dict[str, Any]], output: Path, fmt: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def default_output(fmt: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("outputs") / f"twitter-monitor-{stamp}.{fmt}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch recent X/Twitter posts through twitterapi.io.")
    parser.add_argument("--accounts", nargs="*", help="X account ids, @handles, URLs, or comma-separated values.")
    parser.add_argument("--accounts-file", help="JSON file containing a list of account ids.")
    parser.add_argument("--api-key", default=os.getenv("TWITTER_API_KEY"), help="twitterapi.io API key. Defaults to TWITTER_API_KEY.")
    parser.add_argument("--pages", type=int, default=1, help="Maximum cursor pages per account. Default: 1.")
    since_group = parser.add_mutually_exclusive_group()
    since_group.add_argument("--since-hours", type=int, help="Only fetch posts newer than this many hours.")
    since_group.add_argument("--since-date", help="UTC start date/datetime, for example 2026-04-27 or 2026-04-27T00:00:00+08:00.")
    parser.add_argument("--until-date", help="UTC end date/datetime, for example 2026-04-27 or 2026-04-27T23:59:59+08:00.")
    parser.add_argument("--include-native-retweets", action="store_true", help="Include native retweets in the advanced search query.")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format. Default: json.")
    parser.add_argument("--output", type=Path, help="Output file path. Defaults to outputs/twitter-monitor-<timestamp>.<format>.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds. Default: 20.")
    parser.add_argument("--page-delay", type=float, default=1.0, help="Delay between cursor pages. Default: 1.0.")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.api_key:
        parser.error("missing API key. Set TWITTER_API_KEY or pass --api-key.")
    if args.pages < 1:
        parser.error("--pages must be >= 1")
    if args.since_hours and args.since_hours < 1:
        parser.error("--since-hours must be >= 1")

    try:
        accounts = parse_accounts(args)
        fetched_at_ms = int(time.time() * 1000)
        records: list[dict[str, Any]] = []
        for account in accounts:
            for tweet in fetch_tweets(account, args.api_key, args):
                records.append(format_record(tweet, account, fetched_at_ms))
        records = dedupe(records)
        output = args.output or default_output(args.format)
        write_output(records, output, args.format)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {len(records)} records to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
