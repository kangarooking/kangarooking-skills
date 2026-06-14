# YouTube Viral Topic Scoring

Use recent video performance as the primary signal. Subscriber count is useful context, but it is not the default selection rule.

## Default Thresholds

| Option | Default |
|---|---:|
| `--days` | 30 |
| `--min-views` | 10000 |
| `--min-engagement` | 0 |
| `--limit` | 50 |
| `--small-channel-threshold` | 100000 |

## Formulas

```text
engagement = like_count + comment_count * 2
like_view_rate = like_count / max(view_count, 1)
comment_view_rate = comment_count / max(view_count, 1)
hot_score = view_count + like_count * 20 + comment_count * 40
viral_score = log1p(view_count) * 0.45
            + log1p(engagement) * 0.25
            + min(100, like_view_rate * 1000) * 0.12
            + min(100, comment_view_rate * 3000) * 0.08
            + freshness_score * 0.10
```

## Evidence Labels

- `high_views`: video passed the view threshold.
- `high_engagement`: video passed an explicit engagement threshold.
- `strong_like_view_rate`: like/view rate suggests topic fit, not just accidental reach.
- `active_discussion`: comments are strong relative to views.
- `small_channel_signal`: channel subscribers are under the annotation threshold; this is only context.
- `views_exceed_subscribers`: views are higher than subscribers; this is only context.
- `unknown_subscribers`: channel hides subscriber count or channel data was unavailable.
