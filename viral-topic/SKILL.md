---
name: viral-topic
description: Route viral topic discovery across platform-specific account-growth skills. Use when the user asks for 起号选题, low-follower viral references, recent viral content, cross-platform topic mining, or does not specify whether to search WeChat, X, Bilibili, or YouTube.
---

# Viral Topic

Use this skill as the control layer for finding topic references across platforms. It does not fetch data itself; it routes the request to the platform skill whose collection logic matches the platform.

## Package Layout

This repository publishes `viral-topic/` as one skill package:

```text
viral-topic/
├── SKILL.md
├── references/platforms.md
├── wechat-viral-topic/
├── x-viral-topic/
├── bilibili-viral-topic/
└── youtube-viral-topic/
```

The root `SKILL.md` is the controller. The platform directories are child skills/adapters with their own `SKILL.md`, `references/`, `agents/`, and scripts.

## Platform Routing

Read `references/platforms.md` before deciding which child skills to run.

Implemented child skills:

- `$wechat-viral-topic`: WeChat public-account articles that exceed the account's average reads.
- `$x-viral-topic`: X/Twitter posts from low-follower authors that outperform their audience size.
- `$bilibili-viral-topic`: B站 videos from low-follower UP主 that outperform their follower base.
- `$youtube-viral-topic`: recent high-performing YouTube videos without low-subscriber filtering.

If the user gives no platform, default to the implemented set: WeChat, X, Bilibili, and YouTube. If the user asks for 小红书 or 抖音, explain that those adapters are not implemented yet and propose the available API/browser-automation path before building it.

## Workflow

1. Normalize the user's niche into 3-8 focused search terms.
2. Choose platforms from the request. For "全平台" or "各个平台", run all implemented child skills.
3. Run each platform skill independently with its own defaults:
   - WeChat: `--days 7`, `--min-read 10000`, `--min-read-month-avg-ratio 2`
   - X: `--days 7`, `--max-followers 50000`, `--min-engagement 100`
   - Bilibili: `--days 30`, `--max-followers 100000`, `--min-play 10000`
   - YouTube: `--days 30`, `--min-views 10000`
4. Preserve source URLs, author/account metrics, timing, and evidence labels.
5. Merge outputs into a cross-platform topic table only after preserving each platform's original evidence.
6. Label confidence carefully:
   - WeChat confirms average-read breakout, not low-follower breakout.
   - X and Bilibili can confirm low-follower viral only when follower counts are present.
   - YouTube confirms viral strength, not low-subscriber breakout.

## Output Shape

When combining platforms, use this compact table first:

```text
platform | title | author | published_at | main_metric | scale_metric | breakout_reason | url
```

Then add a short synthesis:

- reusable topic angle
- title/hook pattern
- format pattern
- why it likely worked
- whether the evidence is confirmed or proxy-only

## Guardrails

- Do not collapse all platforms into one scoring formula without keeping platform-specific evidence.
- Do not call YouTube results low-fan by default.
- Do not use WeChat `follower_count` as the default low-fan signal; compare article reads with `month_read_avg`.
- Never write API keys, cookies, app secrets, or access tokens into skill files or outputs.
- Use results as topic references and structure inspiration. Do not copy posts, articles, video scripts, captions, or thumbnails wholesale.
