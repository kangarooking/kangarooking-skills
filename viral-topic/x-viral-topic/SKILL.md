---
name: x-viral-topic
description: Find low-follower viral posts on X/Twitter for account-growth topic selection. Use when the user asks for X low-fan hits, Twitter low follower viral posts, 起号选题 from X, niche tweet inspiration, or viral posts ranked by author followers, views, bookmarks, likes, reposts, and replies.
---

# X Viral Topic

Use this skill to find X posts that significantly outperform the author's follower base.

## Quick Start

Run the bundled script from this skill directory:

```bash
python3 scripts/search_x_viral_topic.py --topic "AI agent" --days 7 --max-followers 50000 --min-engagement 100 --limit 50 --format markdown
```

Required environment:

```bash
export TWITTERAPI_IO_KEY="..."
```

`TWITTER_API_KEY` is also accepted for compatibility with existing `ai-trend-search` workflows.

## Workflow

1. Convert the user's niche into short query clusters. Prefer exact phrases and product/category terms.
2. Search `twitterapi.io` advanced search using both `Top` and `Latest`.
3. Keep broad authority-account search off by default; low-fan discovery should not be dominated by official or celebrity accounts.
4. Extract tweet metrics and author follower count.
5. Filter:
   - `author_followers <= --max-followers`
   - `views >= --min-views` or `engagement >= --min-engagement`
6. Rank by breakout evidence:
   - engagement per follower
   - views per follower
   - bookmarks per like when bookmarks are present
   - freshness inside the requested window
7. Return JSON for automation or Markdown for topic review.

## Query Pattern

Use this shape unless the user gives a specific query:

```text
("keyword one" OR "keyword two") lang:en since:YYYY-MM-DD -filter:replies min_faves:20
```

For Chinese niches, use both English product terms and Chinese terms when relevant. Keep each query short; many focused queries beat one huge query.

## Output Contract

Each result must preserve source and author evidence:

```json
{
  "platform": "x",
  "content_id": "",
  "url": "",
  "title": "",
  "author_id": "",
  "author_name": "",
  "author_handle": "",
  "follower_count": 0,
  "published_at": "",
  "view_count": 0,
  "like_count": 0,
  "comment_count": 0,
  "share_count": 0,
  "save_count": 0,
  "hot_score": 0,
  "breakout_score": 0,
  "evidence": []
}
```

Read `references/scoring.md` before changing thresholds or combining X results with other platforms.

## Guardrails

- Do not treat a post as low-fan if the author follower count is missing unless the user explicitly allows unknown followers.
- The API can return empty or malformed responses for over-broad queries; narrow the topic and preserve `source_status`.
- Avoid scraping logged-in browser sessions for X unless the user explicitly asks. The script uses the API path.
- Use posts as topic signals and hooks; do not copy thread content wholesale.
