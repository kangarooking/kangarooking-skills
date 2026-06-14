# WeChat Public Account Title Method

Use this file when the requested platform is `公众号` or WeChat public-account articles.

## Source Basis

The current platform method is derived from:

- `../title-library/wechat-public-account-hot-titles.md`
- `../title-library/wechat-ai-curated-hot-titles.md`

Snapshot:

- Source path: sibling project `account-growth/公众号.md` hot-articles API.
- Fetch time: 2026-06-14 11:14:47.
- Scope: 12 categories, 480 raw records, 394 cleaned title records.
- Filter: hot articles with `read_num >= 10000`, cleaned to title-like records of 4-80 characters.
- Curated AI supplement: user-provided AI/tech high-traffic title samples, including hotspot-dependent examples and reusable `xxx` skeletons.

## Platform Traits

WeChat public-account titles can be denser and more explicit than X or video-platform titles. They often work because the title itself carries the narrative, conflict, and reason to open.

Prioritize these traits:

1. **Concrete numbers**: money, dates, percentages, rankings, counts, ages, time limits.
2. **Event urgency**: `刚刚`, `突发`, `发布`, `官宣`, `今夜`, `最新`, only when genuinely time-sensitive.
3. **Information density**: use colon, pause, or `丨` to pack cause, result, and context.
4. **Strong nouns**: people, companies, products, roles, institutions, places, regulations.
5. **Visible stakes**: money lost, opportunity window, policy change, job impact, status change.
6. **Counterintuitive discovery**: `原来`, `难怪`, `不是...而是...`, `背后`, `真相`.
7. **Identity callout**: creators, founders,职场人, parents, developers, students, middle-aged readers.
8. **Case-led extraction**: name a live case first, then imply reusable lesson.
9. **Hotspot bridge**: connect AI to the live public topic already carrying attention, such as a product launch, movie, Olympics, cross-border platform migration, or company drama.
10. **Tool replacement shock**: make the old tool, old workflow, or old job feel obsolete because of a new AI capability.

Use emotional words sparingly. WeChat tolerates stronger words than many platforms, but the claim must still be true.

## Platform-Specific Formulas

Generate WeChat-specific titles from these formulas:

1. `刚刚/突发，[主体][动作]：[最大变化/结果]`
2. `[数字/金额/时间]，[主体][反常识结果]`
3. `[对象] 不是 [表象]，而是 [本质]`
4. `[案例] 爆了以后，我拆出了 [可复用规律]`
5. `[目标人群] 要不要 [动作]？先看 [判断标准]`
6. `[主体] 翻车/爆火/出圈，背后是 [机制]`
7. `从 [具体案例] 看懂 [大趋势/新机会]`
8. `[人群] 最容易忽略的 [关键变量]`
9. `[工具/产品/政策] 正式发布： [核心价值/影响]`
10. `别再 [常见做法]，现在真正有效的是 [新做法]`
11. `再见 [旧工具/旧流程]，[新工具/新能力] 出手了`
12. `[时间]！[工具组合] 直接生成 [完整交付物]（附 [教程/提示词/实测]）`
13. `[新技术/新产品] 的第一波受害者出现了`
14. `[热点事件] 越 [结果]，[AI对象] 越 [锋利/真实/荒诞]`
15. `我用 [极端测试/真实任务]，测出了 [产品/模型] 的 [强结论]`

## Title-Library Reuse

When the user asks for proven-title reuse:

1. Load `../title-library/wechat-public-account-hot-titles.md`.
2. For AI, prompt, Agent, model, coding-tool, AI image/video/audio, or AI workflow topics, also load `../title-library/wechat-ai-curated-hot-titles.md`.
3. Prefer `../../scripts/retrieve_title_examples.py` for token-efficient search before opening full JSON libraries.
4. Search the JSON library by topic words, category, subject type, and archetype only when the retrieval result is insufficient.
5. Search the curated AI library by mechanism: tool result shock, product replacement, first victim, era announcement, anti-skill skill, user experience proof, tutorial promise, public emotion, hotspot bridge, or template slot.
6. Select 10 source titles with similar mechanism, not merely similar nouns.
7. Convert each source title into a skeleton.
8. Replace the subject, claim, numbers, event, and conclusion with facts from the current content.
9. Do not copy unverifiable claims, sensitive events, or third-party accusations unchanged.

## Time-Sensitive Hotspot Rule

Some strong WeChat titles are strong because they ride a live traffic wave, not because the sentence pattern is universally strong.

Before using a hotspot-dependent title:

1. Identify the external traffic source: launch, celebrity/public figure, movie, policy, festival, platform migration, company crisis, sports event, or viral meme.
2. Ask whether the current content has the same timing advantage.
3. If the timing is gone, reuse only the structure, such as `热点事件 + AI interpretation`, not the specific claim.
4. Prefer a fresh equivalent current hotspot over an old stale hotspot.

## Output Add-On

When WeChat platform adaptation is requested, append:

```markdown
**公众号平台标题池**
- ...

**套用来源**
- 源标题骨架：
- 改写逻辑：
```
