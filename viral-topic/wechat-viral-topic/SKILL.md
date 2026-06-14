---
name: wechat-viral-topic
description: Find WeChat public-account articles that break out above the account's average reads for account-growth topic selection. Use when the user asks to discover 公众号爆款, 微信低粉爆款, 平均阅读爆款, 起号选题, category-based WeChat hot articles, or article references filtered by month_read_avg rather than unstable follower_count.
---

# WeChat Viral Topic

Use this skill to find WeChat public-account articles that are hot relative to the account's average reads. Do not use `follower_count` as the default low-fan signal because the account-detail follower value is unstable.

## Quick Start

Run the bundled script from this skill directory:

```bash
python3 scripts/search_wechat_viral_topic.py --category ai --days 7 --min-read 10000 --min-read-month-avg-ratio 2 --limit 50 --format markdown
```

Required environment for live API calls:

```bash
export WECHAT_HOT_API_BASE="https://example.com"
export WECHAT_HOT_APP_ID="..."
export WECHAT_HOT_APP_SECRET="..."
```

If `WECHAT_HOT_ACCESS_TOKEN` is set, the script uses it and skips token creation. Never write app ids, secrets, or access tokens into skill files.

## Workflow

1. Select a platform category from `references/categories.md`.
2. Fetch hot articles from `/api/v2/hot/articles` with `category`, `read_num`, `published_at`, and pagination.
   - Send POST bodies as JSON with `Content-Type: application/json`.
   - Use datetime format for `published_at`, such as `2026-06-07T00:00:00`; the live API rejects plain `YYYY-MM-DD`.
3. Extract `__biz` from each `content_url`.
4. Enrich each account through `/api/v2/accounts/detail`, preferring `biz` over `nickname`.
5. Filter for average-read breakout candidates:
   - `read_num >= --min-read`
   - `read_num / month_read_avg >= --min-read-month-avg-ratio`
6. Rank by `breakout_score`, then by `read_month_avg_ratio`, then by `read_num`.
7. Return JSON for automation or Markdown for human topic review.

## Output Contract

Each result must preserve the source URL and average-read evidence:

```json
{
  "platform": "wechat",
  "content_id": "",
  "url": "",
  "title": "",
  "author_id": "",
  "author_name": "",
  "follower_count": 0,
  "month_read_avg": 0,
  "published_at": "",
  "view_count": 0,
  "like_count": 0,
  "share_count": 0,
  "hot_score": 0,
  "breakout_score": 0,
  "evidence": []
}
```

Read `references/scoring.md` before changing thresholds or comparing this output with other platforms.

## Guardrails

- Treat `follower_count` as an unstable reference field, not a filter.
- If account detail fails because the account is not yet collected, retry only when the user accepts the delay or `--account-retry-seconds` is set.
- If `month_read_avg` is missing, do not label the article as a confirmed average-read breakout.
- Use article URLs only for research and topic reference. Do not copy article content wholesale.
