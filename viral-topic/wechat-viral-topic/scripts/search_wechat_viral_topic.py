#!/usr/bin/env python3
"""Find WeChat public-account articles that beat account average reads."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


USER_AGENT = "account-growth-wechat-average-read-viral/0.2"
DEFAULT_EXCLUDED_ACCOUNTS = ["新智元", "机器之心", "差评", "智东西", "极客公园", "量子位", "CSDN"]


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("WECHAT_HOT_API_BASE", ""))
    parser.add_argument("--access-token", default=os.getenv("WECHAT_HOT_ACCESS_TOKEN", ""))
    parser.add_argument("--app-id", default=os.getenv("WECHAT_HOT_APP_ID", ""))
    parser.add_argument("--app-secret", default=os.getenv("WECHAT_HOT_APP_SECRET", ""))
    parser.add_argument("--category", default="ai")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--min-read", type=int, default=10_000)
    parser.add_argument("--max-followers", type=int, default=50_000, help="Deprecated compatibility option; not used for filtering.")
    parser.add_argument("--min-read-follower-ratio", type=float, default=1.0, help="Deprecated compatibility option; not used for filtering.")
    parser.add_argument("--min-read-month-avg-ratio", type=float, default=2.0)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--account-retry-seconds", type=float, default=0.0)
    parser.add_argument("--include-unknown-followers", action="store_true", help="Deprecated compatibility option; average-read data is required.")
    parser.add_argument(
        "--exclude-account",
        action="append",
        default=[],
        help="Account name to exclude from results. Can be repeated.",
    )
    parser.add_argument(
        "--exclude-accounts",
        default="",
        help="Comma-separated account names to exclude in addition to the default organization/media account list.",
    )
    parser.add_argument(
        "--no-default-excluded-accounts",
        action="store_true",
        help="Disable the built-in organization/media account exclusion list.",
    )
    parser.add_argument("--skip-enrich", action="store_true")
    parser.add_argument("--input-json", help="Load hot-article payload from a local JSON file instead of calling the API.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--dry-run", action="store_true", help="Print planned request parameters without calling the API.")
    return parser.parse_args()


def redacted_args(args: argparse.Namespace) -> dict[str, Any]:
    values = vars(args).copy()
    for key in ("access_token", "app_id", "app_secret"):
        if values.get(key):
            values[key] = "***redacted***"
    return values


def split_account_names(value: str) -> list[str]:
    names: list[str] = []
    for part in re.split(r"[,，\n]", value or ""):
        name = part.strip()
        if name:
            names.append(name)
    return names


def excluded_account_names(args: argparse.Namespace) -> list[str]:
    names: list[str] = []
    if not args.no_default_excluded_accounts:
        names.extend(DEFAULT_EXCLUDED_ACCOUNTS)
    names.extend(split_account_names(args.exclude_accounts))
    names.extend(name.strip() for name in args.exclude_account if name and name.strip())

    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        key = normalize_account_name(name)
        if key and key not in seen:
            seen.add(key)
            unique.append(name)
    return unique


def normalize_account_name(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def matching_excluded_account(result: dict[str, Any], excluded_names: list[str]) -> str:
    if not excluded_names:
        return ""
    candidates = [
        result.get("author_name"),
        result.get("account_username"),
        (result.get("raw") or {}).get("article", {}).get("nickname"),
        (result.get("raw") or {}).get("account", {}).get("nickname"),
        (result.get("raw") or {}).get("account", {}).get("username"),
    ]
    normalized_candidates = [normalize_account_name(candidate) for candidate in candidates if candidate]
    for excluded in excluded_names:
        normalized_excluded = normalize_account_name(excluded)
        if not normalized_excluded:
            continue
        for candidate in normalized_candidates:
            if candidate == normalized_excluded or normalized_excluded in candidate:
                return excluded
    return ""


def api_url(base_url: str, path: str, query: dict[str, Any] | None = None) -> str:
    if not base_url:
        raise RuntimeError("WECHAT_HOT_API_BASE or --base-url is required for live API calls")
    url = base_url.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
    return url


def post_json(url: str, body: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail[:300]}") from exc
    return json.loads(data)


def get_access_token(args: argparse.Namespace) -> str:
    if args.access_token:
        return args.access_token
    if not args.app_id or not args.app_secret:
        raise RuntimeError("Set WECHAT_HOT_ACCESS_TOKEN or both WECHAT_HOT_APP_ID and WECHAT_HOT_APP_SECRET")
    payload = post_json(
        api_url(args.base_url, "/api/v2/token"),
        {"app_id": args.app_id, "app_secret": args.app_secret},
    )
    token = ((payload.get("data") or {}).get("access_token") or "").strip()
    if not token:
        raise RuntimeError(f"Token response did not include access_token: {payload}")
    return token


def published_after(days: int) -> str:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    # The docs call this a date, but the live API rejects YYYY-MM-DD and accepts datetime.
    return cutoff.strftime("%Y-%m-%dT00:00:00")


def extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    items = data.get("items") if isinstance(data, dict) else None
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def fetch_hot_articles(args: argparse.Namespace, access_token: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_items: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    last_id: int | None = None
    for page in range(1, args.max_pages + 1):
        body: dict[str, Any] = {
            "category": args.category,
            "read_num": args.min_read,
            "published_at": published_after(args.days),
        }
        if last_id:
            body["last_id"] = last_id
        payload = post_json(api_url(args.base_url, "/api/v2/hot/articles", {"access_token": access_token}), body)
        items = extract_items(payload)
        statuses.append({"source": "wechat_hot_articles", "page": page, "ok": True, "count": len(items), "error": ""})
        all_items.extend(items)
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        next_last_id = as_int(data.get("last_id"), 0)
        if not next_last_id or next_last_id == last_id or len(all_items) >= args.limit * 3:
            break
        last_id = next_last_id
    return all_items, statuses


def extract_biz(content_url: str) -> str:
    if not content_url:
        return ""
    parsed = urllib.parse.urlparse(content_url)
    query = urllib.parse.parse_qs(parsed.query)
    value = (query.get("__biz") or [""])[0]
    if value:
        return value
    match = re.search(r"[?&]__biz=([^&#]+)", content_url)
    return urllib.parse.unquote(match.group(1)) if match else ""


def fetch_account_detail(
    args: argparse.Namespace,
    access_token: str,
    biz: str,
    nickname: str,
) -> tuple[dict[str, Any], str]:
    body: dict[str, Any] = {}
    if biz:
        body["biz"] = biz
    elif nickname:
        body["nickname"] = nickname
    else:
        return {}, "missing biz and nickname"

    url = api_url(args.base_url, "/api/v2/accounts/detail", {"access_token": access_token})
    first = post_json(url, body)
    if as_int(first.get("code"), 0) == 200 and isinstance(first.get("data"), dict):
        return first["data"], ""

    if args.account_retry_seconds > 0:
        time.sleep(args.account_retry_seconds)
        second = post_json(url, body)
        if as_int(second.get("code"), 0) == 200 and isinstance(second.get("data"), dict):
            return second["data"], ""
        return {}, str(second.get("msg") or second)[:300]
    return {}, str(first.get("msg") or first)[:300]


def enrich_accounts(
    args: argparse.Namespace,
    access_token: str,
    items: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    accounts: dict[str, dict[str, Any]] = {}
    statuses: list[dict[str, Any]] = []
    for item in items:
        biz = extract_biz(str(item.get("content_url") or ""))
        nickname = str(item.get("nickname") or "")
        key = biz or f"nickname:{nickname}"
        if not key or key in accounts:
            continue
        try:
            detail, error = fetch_account_detail(args, access_token, biz, nickname)
            accounts[key] = detail
            statuses.append({"source": "wechat_account_detail", "biz": biz, "nickname": nickname, "ok": not error, "error": error})
        except Exception as exc:  # Keep other articles usable.
            accounts[key] = {}
            statuses.append({"source": "wechat_account_detail", "biz": biz, "nickname": nickname, "ok": False, "error": str(exc)})
    return accounts, statuses


def score_item(item: dict[str, Any], account: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    read_num = as_int(item.get("read_num"))
    like_num = as_int(item.get("like_num"))
    old_like_num = as_int(item.get("old_like_num"))
    share_num = as_int(item.get("share_num"))
    follower_count = as_int(account.get("follower_count"), 0)
    month_read_avg = as_int(account.get("month_read_avg"), 0)
    engagement = like_num + old_like_num + share_num * 3
    hot_score = read_num + like_num * 20 + old_like_num * 8 + share_num * 30
    read_month_avg_ratio = read_num / max(month_read_avg, 1000) if month_read_avg else 0.0
    breakout_score = (
        math.log1p(read_num) * 0.45
        + math.log1p(engagement) * 0.20
        + min(100.0, read_month_avg_ratio * 30.0) * 0.30
        + min(100.0, share_num * 2.0) * 0.05
    )

    evidence: list[str] = []
    if month_read_avg and read_month_avg_ratio >= args.min_read_month_avg_ratio:
        evidence.append(f"above_monthly_average:{read_month_avg_ratio:.2f}x")
    if read_num >= args.min_read:
        evidence.append(f"high_read:{read_num}")
    if share_num >= 20:
        evidence.append(f"strong_share_signal:{share_num}")
    if not month_read_avg:
        evidence.append("unknown_month_read_avg")
    if follower_count:
        evidence.append(f"follower_count_reference:{follower_count}")

    biz = extract_biz(str(item.get("content_url") or "")) or str(account.get("biz") or "")
    return {
        "platform": "wechat",
        "content_id": str(item.get("id") or ""),
        "url": item.get("content_url") or "",
        "title": item.get("title") or "",
        "author_id": biz,
        "author_name": account.get("nickname") or item.get("nickname") or "",
        "account_username": account.get("username") or "",
        "follower_count": follower_count or None,
        "month_read_avg": month_read_avg or None,
        "published_at": item.get("published_at") or "",
        "view_count": read_num,
        "like_count": like_num + old_like_num,
        "share_count": share_num,
        "save_count": None,
        "comment_count": None,
        "hot_score": round(float(hot_score), 2),
        "breakout_score": round(float(breakout_score), 2),
        "read_month_avg_ratio": round(read_month_avg_ratio, 4) if month_read_avg else None,
        "evidence": evidence,
        "raw": {"article": item, "account": account},
    }


def passes_filters(result: dict[str, Any], args: argparse.Namespace) -> bool:
    if as_int(result.get("view_count")) < args.min_read:
        return False
    month_avg = result.get("month_read_avg")
    month_ratio = result.get("read_month_avg_ratio")
    if not month_avg or month_ratio is None:
        return False
    if float(month_ratio) < args.min_read_month_avg_ratio:
        return False
    return True


def format_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# WeChat Average-Read Viral Results",
        "",
        f"- Category: {payload['query'].get('category')}",
        f"- Window days: {payload['query'].get('days')}",
        f"- Results: {len(payload['results'])}",
        f"- Excluded accounts: {', '.join(payload['query'].get('excluded_accounts') or []) or 'none'}",
        "",
    ]
    for index, item in enumerate(payload["results"], 1):
        followers = item.get("follower_count") if item.get("follower_count") is not None else "unknown"
        lines.extend(
            [
                f"## {index}. {item['title']}",
                "",
                f"- URL: {item['url']}",
                f"- Account: {item.get('author_name') or ''} ({item.get('author_id') or 'unknown biz'})",
                f"- Followers reference: {followers}; month_read_avg: {item.get('month_read_avg') or 'unknown'}",
                f"- Reads: {item['view_count']}; likes: {item['like_count']}; shares: {item['share_count']}",
                f"- Score: {item['breakout_score']}; evidence: {', '.join(item['evidence'])}",
                "",
            ]
        )
    if payload.get("source_status"):
        lines.extend(["## Source Status", ""])
        for status in payload["source_status"]:
            lines.append(f"- {status.get('source')}: ok={status.get('ok')} count={status.get('count', '')} error={status.get('error', '')}")
    if payload.get("excluded_counts"):
        lines.extend(["", "## Excluded Accounts", ""])
        for name, count in sorted(payload["excluded_counts"].items(), key=lambda pair: (-pair[1], pair[0])):
            lines.append(f"- {name}: {count}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    excluded_names = excluded_account_names(args)
    if args.dry_run:
        print(json.dumps({"planned": redacted_args(args), "published_at": published_after(args.days), "excluded_accounts": excluded_names}, ensure_ascii=False, indent=2))
        return 0

    source_status: list[dict[str, Any]] = []
    if args.input_json:
        with open(args.input_json, "r", encoding="utf-8") as handle:
            raw_payload = json.load(handle)
        items = extract_items(raw_payload)
        source_status.append({"source": "input_json", "ok": True, "count": len(items), "error": ""})
        access_token = args.access_token
    else:
        access_token = get_access_token(args)
        items, statuses = fetch_hot_articles(args, access_token)
        source_status.extend(statuses)

    accounts: dict[str, dict[str, Any]] = {}
    if not args.skip_enrich:
        if not access_token:
            source_status.append({"source": "wechat_account_detail", "ok": False, "error": "No access token; skipped enrichment"})
        else:
            enriched, statuses = enrich_accounts(args, access_token, items)
            accounts.update(enriched)
            source_status.extend(statuses)

    results: list[dict[str, Any]] = []
    excluded_counts: dict[str, int] = {}
    for item in items:
        biz = extract_biz(str(item.get("content_url") or ""))
        key = biz or f"nickname:{item.get('nickname') or ''}"
        account = accounts.get(key) or {
            "biz": biz,
            "nickname": item.get("nickname"),
            "follower_count": item.get("follower_count"),
            "month_read_avg": item.get("month_read_avg"),
        }
        scored = score_item(item, account, args)
        excluded_by = matching_excluded_account(scored, excluded_names)
        if excluded_by:
            excluded_counts[excluded_by] = excluded_counts.get(excluded_by, 0) + 1
            continue
        if passes_filters(scored, args):
            results.append(scored)

    results.sort(
        key=lambda item: (
            float(item.get("breakout_score") or 0),
            float(item.get("read_month_avg_ratio") or 0),
            int(item.get("view_count") or 0),
        ),
        reverse=True,
    )
    payload = {
        "query": {
            "category": args.category,
            "days": args.days,
            "min_read": args.min_read,
            "min_read_month_avg_ratio": args.min_read_month_avg_ratio,
            "excluded_accounts": excluded_names,
        },
        "source_status": source_status,
        "excluded_counts": excluded_counts,
        "results": results[: args.limit],
    }
    if args.format == "markdown":
        print(format_markdown(payload), end="")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
