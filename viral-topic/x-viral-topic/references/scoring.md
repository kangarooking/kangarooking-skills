# X Viral Topic Scoring

Use author follower count as the scale denominator. The goal is not simply high likes; it is posts that traveled beyond the author's normal reach.

## Default Thresholds

| Option | Default |
|---|---:|
| `--max-followers` | 50000 |
| `--min-views` | 10000 |
| `--min-engagement` | 100 |
| `--min-faves` | 20 |

## Formulas

```text
engagement = like_count + repost_count * 3 + reply_count * 2 + bookmark_count * 2 + view_count / 1000
engagement_follower_ratio = engagement / max(follower_count, 500)
view_follower_ratio = view_count / max(follower_count, 500)
bookmark_like_ratio = bookmark_count / max(like_count, 1)
hot_score = engagement
breakout_score = log1p(engagement) * 0.45
               + min(100, engagement_follower_ratio * 60) * 0.25
               + min(100, view_follower_ratio * 8) * 0.20
               + min(100, bookmark_like_ratio * 100) * 0.10
```

## Evidence Labels

- `low_follower_author`: author followers are under threshold.
- `views_exceed_followers`: views are higher than author followers.
- `high_engagement_per_follower`: engagement traveled beyond account size.
- `save_intent`: bookmark/like ratio is strong.
- `unknown_followers`: author follower count was missing; do not call this confirmed low-fan.
