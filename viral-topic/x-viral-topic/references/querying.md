# X Querying Notes

Use `twitterapi.io` advanced search with concise queries. The API follows X advanced-search-like syntax well enough for:

```text
("AI agent" OR "Claude Code") lang:en since:2026-06-06 -filter:replies min_faves:20
```

## Query Construction

- Prefer 2-5 terms per query.
- Use exact quoted phrases for product names and content formats.
- Run both `Top` and `Latest`.
- Keep `min_faves` low enough to catch small accounts; 20 is a good default.
- Avoid authority-only queries such as `from:OpenAI`; they defeat low-fan discovery.

## Source Status

If a query returns no tweets, keep the query in `source_status` with `count: 0`. If the API response is malformed or missing tweets, keep the error message and continue with other queries.
