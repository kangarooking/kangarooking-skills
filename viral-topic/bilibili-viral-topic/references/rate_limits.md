# Bilibili Request Notes

Bilibili public JSON endpoints can reject non-browser-like traffic. Treat this skill as a careful public-web collector, not an official API client.

## Required Headers

Use browser-like headers:

```text
User-Agent: Chrome/Safari style desktop UA
Referer: https://search.bilibili.com/ or https://www.bilibili.com/
Origin: https://www.bilibili.com
Accept-Language: zh-CN,zh;q=0.9,en;q=0.8
```

Optional:

```text
Cookie: value from BILIBILI_COOKIE
```

## Defaults

- `--request-sleep 0.6`
- `--retries 2`
- `--cache-ttl-hours 24`
- `--pages 3`
- `--page-size 30`

## Failure Handling

- HTTP `412`: slow down, use browser-like headers, optionally add `BILIBILI_COOKIE`.
- JSON `code=-352`: treat as risk/rate-limit. Slow down or retry later.
- Missing follower data: keep the source status, and only include the result when `--include-unknown-followers` is set.
