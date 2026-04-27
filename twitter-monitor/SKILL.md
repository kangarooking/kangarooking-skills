---
name: twitter-monitor
description: Fetch recent posts from one or more X/Twitter accounts through twitterapi.io, output structured JSON/CSV records, optionally sync records to Feishu/Lark Bitable through feishu-cli, and optionally guide recurring execution through OpenClaw, Codex automations, cron, or launchd. Use when the user wants to monitor X bloggers, collect recent tweets, export tweet metrics, append tweets to Feishu Bitable, or set up a scheduled Twitter/X account tracking workflow.
---

# Twitter Monitor

## Workflow

Use this skill as an execution workflow, not as a long-running daemon. First complete a one-shot fetch, then offer optional Feishu sync and scheduling only when useful.

1. Ask for X/Twitter account ids when missing. Accept handles such as `sama`, `@sama`, profile URLs, or multiple comma-separated ids.
2. Ask the user to provide or configure a `twitterapi.io` API key when `TWITTER_API_KEY` is unavailable. Do not write API keys into files committed to a repository.
3. Confirm pagination depth. Default to `--pages 1`; use a larger number only when the user asks for more history or accepts higher API usage.
4. Run `scripts/twitter_monitor.py` and generate JSON or CSV output.
5. If the user wants Feishu/Lark Bitable output, follow `references/feishu-output.md`.
6. After the one-shot command works, ask whether they want recurring execution. If yes, follow `references/scheduling.md`, including OpenClaw when appropriate.

## Quick Start

From this skill directory:

```bash
export TWITTER_API_KEY="..."
python scripts/twitter_monitor.py --accounts sama --pages 1 --format json
```

For multiple accounts:

```bash
python scripts/twitter_monitor.py --accounts sama,elonmusk,OpenAI --pages 1 --format csv
```

For a JSON account list:

```bash
python scripts/twitter_monitor.py --accounts-file assets/accounts.example.json --pages 1
```

Read `references/twitterapi-setup.md` when the user needs API key setup, account input examples, or command variants.

## Output Schema

The script writes one record per tweet with these fields:

- `推文内容`
- `日期`
- `推文链接`
- `推文ID`
- `作者`
- `作者ID`
- `阅读量`
- `点赞数`
- `转发数`
- `评论数`
- `收藏数`
- `是否回复`
- `抓取时间`

Deduplicate by `推文ID` before appending to any durable destination.

## Feishu

Do not require Feishu configuration for normal fetches. Only enter the Feishu workflow when the user asks to write, append, or sync records to Feishu/Lark Bitable.

Prefer `feishu-cli` over hard-coded Feishu app credentials. If `feishu-cli` is missing, ask whether to install and configure it. See `references/feishu-output.md` for the field mapping and sync rules.

## Scheduling

Offer scheduling only after a successful one-shot fetch or when the user explicitly asks for ongoing monitoring.

Prefer OpenClaw when the user wants an agent-managed recurring job or already uses OpenClaw. Otherwise choose Codex automations, cron, or launchd based on the runtime environment. See `references/scheduling.md`.

## Safety

Never commit real API keys, Feishu tokens, output files containing private monitoring data, or local status caches. Keep secrets in environment variables, secret managers, or the user's existing CLI auth.
