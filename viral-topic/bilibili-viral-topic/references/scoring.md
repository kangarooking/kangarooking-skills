# Bilibili Viral Topic Scoring

Use UP主 follower count as the scale denominator. The goal is videos whose playback and engagement traveled beyond the creator's audience size.

## Default Thresholds

| Option | Default |
|---|---:|
| `--days` | 30 |
| `--max-followers` | 100000 |
| `--min-play` | 10000 |
| `--min-play-follower-ratio` | 2.0 |
| `--limit` | 50 |

## Formulas

```text
engagement = like_count
           + coin_count * 3
           + save_count * 2
           + share_count * 3
           + comment_count * 2
           + danmaku_count

play_follower_ratio = view_count / max(follower_count, 1000)
engagement_follower_ratio = engagement / max(follower_count, 1000)

hot_score = view_count
          + like_count * 10
          + coin_count * 30
          + save_count * 20
          + share_count * 30
          + comment_count * 20
          + danmaku_count * 5

breakout_score = log1p(view_count) * 0.40
               + log1p(engagement) * 0.30
               + min(100, play_follower_ratio * 8) * 0.25
               + freshness_score * 0.05
```

## Evidence Labels

- `low_follower_author`: UP主粉丝数低于阈值。
- `plays_exceed_followers`: 播放量超过粉丝数。
- `high_play_follower_ratio`: 播放/粉丝比超过阈值。
- `high_engagement_per_follower`: 互动相对粉丝规模很强。
- `strong_save_coin_signal`: 收藏/投币信号强，适合做选题结构参考。
- `unknown_followers`: 粉丝数缺失；不能称为确认低粉爆款。
