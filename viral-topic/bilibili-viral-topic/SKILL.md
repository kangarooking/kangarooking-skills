---
name: bilibili-viral-topic
description: Find low-follower viral Bilibili videos for account-growth topic selection. Use when the user asks for B站低粉爆款, Bilibili low-fan hits, 起号选题 from B站, niche Bilibili references, or videos ranked by UP主粉丝数, 播放, 点赞, 投币, 收藏, 分享, 评论, 弹幕, and 播放粉丝比.
---

# Bilibili Viral Topic

Use this skill to find B站 videos that significantly outperform the UP主's follower base.

## Quick Start

Run the bundled script from this skill directory:

```bash
python3 scripts/search_bilibili_viral_topic.py --topic "AI工具,大模型,AI编程" --days 30 --max-followers 100000 --min-play 10000 --limit 50 --format markdown
```

No API key is required. The script uses public Bilibili JSON endpoints with browser-like headers, conservative rate limits, retries, and a local follower cache.

Optional environment:

```bash
export BILIBILI_COOKIE="..."
```

Only set `BILIBILI_COOKIE` if public requests are repeatedly rate-limited. Never write cookies into skill files or output artifacts.

## Workflow

1. Convert the user's niche into focused Chinese and product-name keywords.
2. Search B站 videos through `x/web-interface/search/type` with `order=pubdate` and `order=click`.
3. Optionally supplement with `x/web-interface/ranking/v2` when the user asks for broader platform signals.
4. Deduplicate by `bvid`.
5. Filter to the requested recent window using `pubdate`.
6. Enrich each unique `mid` through `x/relation/stat?vmid=<mid>` and cache follower counts.
7. Filter:
   - `follower_count <= --max-followers`
   - `view_count >= --min-play`
   - `view_count / follower_count >= --min-play-follower-ratio`
8. Rank by `breakout_score`, then `play_follower_ratio`, then `view_count`.
9. Return JSON for automation or Markdown for topic review.

## Output Contract

Each result must preserve source and UP主 evidence:

```json
{
  "platform": "bilibili",
  "content_id": "",
  "url": "",
  "title": "",
  "author_id": "",
  "author_name": "",
  "follower_count": 0,
  "published_at": "",
  "view_count": 0,
  "like_count": 0,
  "comment_count": 0,
  "share_count": 0,
  "save_count": 0,
  "coin_count": 0,
  "danmaku_count": 0,
  "hot_score": 0,
  "breakout_score": 0,
  "evidence": []
}
```

Read `references/scoring.md` before changing thresholds or combining B站 results with other platforms. Read `references/rate_limits.md` before increasing pages, ranking rids, or request speed.

## Guardrails

- Do not scrape B站 HTML pages when the JSON endpoints are enough.
- Use browser-like headers. Naked script user agents can trigger `-352` or HTTP `412`.
- Keep request speed conservative. Default `--request-sleep 0.6` is intentional.
- Cache follower counts for at least 24 hours. Re-querying the same `mid` repeatedly increases risk and adds little value.
- Do not call a video confirmed low-fan if follower count is missing unless the user explicitly allows unknown followers.
- Use videos as topic signals, hook references, title structures, and format references. Do not copy full scripts or captions wholesale.
