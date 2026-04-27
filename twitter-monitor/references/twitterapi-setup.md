# twitterapi.io Setup

Use `twitterapi.io` advanced search for one-shot X/Twitter account fetches.

Required environment variable:

```bash
export TWITTER_API_KEY="..."
```

Default command:

```bash
python scripts/twitter_monitor.py --accounts sama --pages 1 --format json
```

Use `--pages` to cap cursor pagination. Keep the default at `1` unless the user asks for a deeper pull or confirms an API-cost tradeoff.

Useful variants:

```bash
python scripts/twitter_monitor.py --accounts sama,elonmusk --pages 2 --format csv
python scripts/twitter_monitor.py --accounts-file assets/accounts.example.json --since-hours 24
python scripts/twitter_monitor.py --accounts sama --since-date 2026-04-27 --until-date 2026-04-27
```

The script accepts handles with or without `@`, comma-separated lists, and `x.com` or `twitter.com` profile URLs.
