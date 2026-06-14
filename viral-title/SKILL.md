---
name: viral-title
description: Generate high-potential viral title candidates for content across WeChat public account articles, X/Twitter posts, YouTube videos, Bilibili videos, and similar content platforms. Use when the user needs headline/title ideation, batch title generation, platform-specific title adaptation, title-library reuse, title selection, title scoring, or a reusable title workflow based on universal formulas plus separated platform methods such as 公众号, X, YouTube, and B站.
---

# Viral Title

## Overview

Use this skill to generate and select viral title candidates. The current version implements Phase 1 universal methodology, WeChat public-account title reuse, X/Twitter hook generation, YouTube title-thumbnail packaging, Bilibili title-cover-tag packaging, and a lightweight evolution loop.

Phase 1 must generate 30 titles: 10 universal formulas x 3 variants per formula. Then score the candidates and recommend the single best title.

## Workflow

1. Clarify only if the content is too vague to title.
2. Identify the core material:
   - topic or content summary
   - target audience
   - platform if provided
   - strongest value, conflict, novelty, or emotional hook
   - hard facts, numbers, names, examples, and constraints that must remain true
3. Read `references/phase1-universal-methodology.md`.
4. If the user names a platform, load the matching platform reference from `references/platforms/`.
5. Read `references/evolution/promoted-rules.md` and `references/evolution/anti-patterns.md`.
6. Generate exactly 3 titles for each of the 10 Phase 1 formulas.
7. If a platform reference is implemented, generate platform-tuned candidates after the universal batch when the user asks for platform-specific titles.
8. If the user asks to reuse proven titles or says "套用标题库", retrieve relevant examples instead of loading full libraries.
9. Score the candidate pool with the Phase 1 scoring rubric plus any platform-specific rules.
10. Select one best title and briefly explain why.
11. End every substantial title-generation response with the feedback prompt from `Feedback Hook`.
12. If the user replies with a selected title, edit, rating, or critique, log it with `scripts/log_feedback.py`.

## Platform Routing

Use one platform file at a time:

| User says | Platform file | Status |
|---|---|---|
| 公众号, 微信公众号, WeChat article | `references/platforms/wechat-public-account.md` | Implemented |
| X, Twitter, 推特 | `references/platforms/x.md` | Implemented |
| YouTube, 油管 | `references/platforms/youtube.md` | Implemented |
| B站, Bilibili | `references/platforms/bilibili.md` | Implemented |

For title-library reuse, load only the current platform's library:

- `references/title-library/wechat-public-account-hot-titles.md` for summary and examples.
- `references/title-library/wechat-ai-curated-hot-titles.md` for user-curated AI/tech viral title patterns and hotspot-dependent examples.
- `references/title-library/wechat-public-account-hot-titles.json` only when many source titles are needed for matching or adaptation.
- `references/title-library/x-hot-hooks.md` for X/Twitter hook skeletons and reusable mechanisms.
- `references/title-library/youtube-hot-titles.md` for YouTube title-thumbnail packaging skeletons.
- `references/title-library/bilibili-hot-titles.md` for B站 title-cover-tag packaging skeletons.

For token-efficient retrieval, prefer:

```bash
python3 scripts/retrieve_title_examples.py --platform <wechat|x|youtube|bilibili> --query "<topic words>" --mechanism "<optional mechanism>" --limit 10
```

## Evolution Loop

Use the loop only when logging, feedback, review, or evaluation is useful. Do not load historical logs during ordinary title generation.

| Need | Command |
|---|---|
| Log a title session | `python3 scripts/log_title_session.py --platform <platform> --topic "..." --recommended-title "..."`
| Log user feedback | `python3 scripts/log_feedback.py --session-id "..." --platform <platform> --selected-title "..." --user-edit "..." --rating 5 --feedback "..."`
| Retrieve title examples | `python3 scripts/retrieve_title_examples.py --platform <wechat|x|youtube|bilibili> --query "AI Agent speed" --limit 10` |
| Review recent learning | `python3 scripts/analyze_feedback.py --recent 20` |
| Run seed evals | `python3 scripts/run_title_evals.py --evals references/evals/bilibili-ai-title-evals.json --case-id agent-speed-step37-bilibili --titles-json titles.json` |

Follow `meta/RULES.md`: append logs automatically, but require user confirmation before modifying core methodology or promoting rules.

## Feedback Hook

After every substantial title-generation response, append exactly one short feedback prompt:

```markdown
**反馈一下**
你最终会用哪个标题？如果你改了标题，把最终版发我；也可以给 1-5 分。我会用这次反馈优化下次标题。
```

Do not ask for feedback after pure research, implementation, explanation, or tiny one-off edits.

When feedback arrives:

1. Treat a chosen title, edited title, rating, or critique as evolution feedback.
2. Log feedback with the current platform when known.
3. Prefer `user_edit` over `selected_title` when both are provided.
4. Store titles, platform, rating, tags, and concise feedback only. Do not store full unpublished drafts by default.
5. After every 5-20 feedback records, run `scripts/analyze_feedback.py --recent 20` and summarize learning candidates.
6. Do not promote candidate observations into methodology files without user confirmation.

## Phase 1 Output Format

Use this structure:

```markdown
**内容判断**
核心对象：
目标人群：
主要点击理由：
真实约束：

**第一阶段：通用方法论标题池**

1. 结果承诺型
- ...
- ...
- ...

2. 问题解决型
- ...
- ...
- ...

[continue through all 10 formulas]

**最佳标题**
标题：
理由：

**备选 Top 3**
1. ...
2. ...
3. ...

**反馈一下**
你最终会用哪个标题？如果你改了标题，把最终版发我；也可以给 1-5 分。我会用这次反馈优化下次标题。
```

## Quality Rules

- Generate exactly 30 Phase 1 candidates unless the user explicitly asks for fewer.
- Each formula must contribute exactly 3 titles.
- Do not fabricate unsupported facts, names, numbers, or results.
- Prefer concrete nouns, visible stakes, and reader-facing benefits over abstract claims.
- Keep titles platform-neutral in Phase 1. Do not overfit to WeChat, X, YouTube, or Bilibili unless the user asks.
- Use Chinese titles by default when the user writes in Chinese. Use English when the source content or user request is English.
- Avoid empty hype such as "震惊", "必看", "全网最强", unless the user's style explicitly asks for it.
- Make the final recommendation decisive. Do not say "it depends" after scoring.

## Future Extension Points

- Add deeper live-sampled libraries for each platform as more user-approved data sources become available.
- Split Bilibili libraries by partition if a single library becomes too broad.
- Load only the platform or library reference needed for the current user request.
