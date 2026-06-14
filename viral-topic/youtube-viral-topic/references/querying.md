# YouTube Viral Topic Querying

## Default Window

Use `--days 30` by default. YouTube videos often need more time than X posts to accumulate enough views, while 30 days is still recent enough for topic selection.

## Query Shape

Use focused topic clusters rather than one broad query:

```bash
python3 scripts/search_youtube_viral_topic.py \
  --topic "AI agent,Claude Code,workflow automation" \
  --days 30 \
  --region-code US \
  --relevance-language en \
  --format markdown
```

For Chinese niches, run both Chinese and English terms when the topic naturally crosses markets.

## API Path

1. `search.list`: `part=snippet`, `type=video`, `order=viewCount`, `publishedAfter`, `q`.
2. `videos.list`: `part=snippet,statistics,contentDetails`, up to 50 ids per call.
3. `channels.list`: `part=snippet,statistics`, up to 50 ids per call.

`search.list` is the expensive step, so keep `--max-results-per-query` conservative and cache outputs when running broad research.

## Subscriber Context

Keep subscriber count in the output when available, but do not filter by it. Use it only for labels such as `small_channel_signal` or `views_exceed_subscribers`.
