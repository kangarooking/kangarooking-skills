# Viral Topic Platform Routing

## WeChat

Use `$wechat-viral-topic` for 公众号选题.

Default logic:

- Recent window: 7 days.
- Confirmed viral rule: `read_num >= 10000` and `read_num / month_read_avg >= 2`.
- `follower_count` is reference-only because the account-detail value is unstable.
- Default account exclusion: 新智元, 机器之心, 差评, 智东西, 极客公园, 量子位, CSDN.
- Best output use: article angle, headline structure, category-level account references.

## X

Use `$x-viral-topic` for X/Twitter topic mining.

Default logic:

- Recent window: 7 days.
- Low-follower filter: author followers at or below 50,000.
- Viral evidence: views or engagement are strong relative to followers.
- Best output use: sharp hooks, discourse signals, product/category trend language.

## Bilibili

Use `$bilibili-viral-topic` for B站视频选题.

Default logic:

- Recent window: 30 days.
- Low-follower filter: UP主粉丝 at or below 100,000.
- Viral evidence: plays at or above 10,000 and play/follower ratio at or above 2.
- Best output use: Chinese video angles, title phrasing, format and section structure.

## YouTube

Use `$youtube-viral-topic` for YouTube topic mining.

Default logic:

- Recent window: 30 days.
- No low-subscriber filter by default.
- Viral evidence: views at or above 10,000, then rank by viral score.
- Best output use: global topic validation, English hooks, format ideas, thumbnail/title patterns.
