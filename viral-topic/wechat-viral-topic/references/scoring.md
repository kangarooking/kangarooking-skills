# WeChat Average-Read Viral Scoring

Use `month_read_avg` as the account-size baseline. Do not use `follower_count` for default filtering because the current account-detail follower value is unstable.

## Default Thresholds

| Option | Default |
|---|---:|
| `--min-read` | 10000 |
| `--min-read-month-avg-ratio` | 2.0 |
| `--limit` | 50 |

## Required Viral Rule

```text
read_num >= 10000
read_num / month_read_avg >= 2
```

If `month_read_avg` is missing, the article is not a confirmed average-read breakout.

## Account Exclusion

Exclude institution/media accounts before returning results because they are weak references for users who are starting or growing a new account. The default exclusion list is:

```text
新智元, 机器之心, 差评, 智东西, 极客公园, 量子位, CSDN
```

Use `--exclude-account` or `--exclude-accounts` to add more accounts for a niche. Use `--no-default-excluded-accounts` only when the user explicitly wants institution/media accounts included.

## Formulas

```text
engagement = like_num + old_like_num + share_num * 3
hot_score = read_num + like_num * 20 + old_like_num * 8 + share_num * 30
read_month_avg_ratio = read_num / max(month_read_avg, 1000)
breakout_score = log1p(read_num) * 0.45
               + log1p(engagement) * 0.20
               + min(100, read_month_avg_ratio * 30) * 0.30
               + min(100, share_num * 2) * 0.05
```

## Evidence Labels

- `above_monthly_average`: reads are at least threshold times the account's average reads.
- `high_read`: reads passed the absolute read threshold.
- `strong_share_signal`: share count contributes materially to hot score.
- `unknown_month_read_avg`: average-read baseline was missing; do not call this confirmed breakout.
- `follower_count_reference`: follower count is present but is only shown as a reference.
