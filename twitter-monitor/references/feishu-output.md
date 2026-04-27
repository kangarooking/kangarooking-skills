# Feishu Output

Only use Feishu when the user asks to write or sync results to Feishu/Lark Bitable.

Preferred workflow:

1. Run `twitter_monitor.py` first and produce JSON or CSV.
2. Check whether `feishu-cli` is installed.
3. If it is missing, ask whether to install and configure it.
4. Use the user's existing Feishu CLI auth/session and target app/table details.

Recommended Bitable fields:

| Field | Type |
| --- | --- |
| 推文内容 | Text |
| 日期 | Date/time |
| 推文链接 | URL |
| 推文ID | Text |
| 作者 | Text |
| 作者ID | Text |
| 阅读量 | Number |
| 点赞数 | Number |
| 转发数 | Number |
| 评论数 | Number |
| 收藏数 | Number |
| 是否回复 | Checkbox |
| 抓取时间 | Date/time |

Deduplicate by `推文ID` before appending records when the target table already contains prior fetches.

Do not ask users for Feishu app secrets unless `feishu-cli` cannot support their target operation and the user explicitly chooses API-based setup.
