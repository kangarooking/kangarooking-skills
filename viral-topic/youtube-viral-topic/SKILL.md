---
name: youtube-viral-topic
description: Find recent viral YouTube videos for account-growth topic selection. Use when the user asks for YouTube 爆款, YouTube hot videos, 起号选题 from YouTube, niche video references, recent high-view videos, or videos ranked by views, likes, comments, freshness, and topic relevance without low-follower filtering.
---

# YouTube Viral Topic

Use this skill to find recent YouTube videos that are already performing strongly in a niche. Do not make low-subscriber status the default logic.

## Quick Start

Run the bundled script from this skill directory:

```bash
python3 scripts/search_youtube_viral_topic.py --topic "AI agent,Claude Code" --days 30 --min-views 10000 --limit 50 --format markdown
```

Required environment for live API calls:

```bash
export YOUTUBE_API_KEY="..."
```

You can also pass `--api-key` explicitly for one-off runs. Never write API keys into skill files or output artifacts.

## Workflow

1. Convert the user's niche into concise query clusters.
2. Call YouTube `search.list` with `type=video`, `order=viewCount`, and `publishedAfter` for the requested recent window.
3. Deduplicate video ids across queries.
4. Batch-enrich videos through `videos.list` for statistics and metadata.
5. Batch-enrich channels through `channels.list` for public subscriber counts.
6. Filter only by viral strength:
   - `view_count >= --min-views`
   - `like_count + comment_count * 2 >= --min-engagement` only when the user sets `--min-engagement`
7. Rank by `viral_score`, then `view_count`, then `like_view_rate`.
8. Return JSON for automation or Markdown for human topic review.

## Output Contract

Each result must preserve the source URL, video metrics, and optional channel context:

```json
{
  "platform": "youtube",
  "content_id": "",
  "url": "",
  "title": "",
  "author_id": "",
  "author_name": "",
  "subscriber_count": 0,
  "published_at": "",
  "view_count": 0,
  "like_count": 0,
  "comment_count": 0,
  "hot_score": 0,
  "viral_score": 0,
  "evidence": []
}
```

For cross-platform tables, `follower_count` is still populated with YouTube channel subscribers when available, but it is not a default filter.

Read `references/scoring.md` before changing thresholds or combining YouTube results with other platforms.

## Guardrails

- Do not call the default output "low-fan" or "low-subscriber" results.
- Treat `subscriberCount` as public rounded/abbreviated subscriber data, useful only as context.
- If `hiddenSubscriberCount` is true or subscriber count is missing, keep the video eligible as long as it passes the viral filters.
- Prefer API collection over browser scraping. Browser sessions should only be used when the user explicitly asks.
- Use videos as topic signals, structure references, and hook references. Do not copy scripts or captions wholesale.
