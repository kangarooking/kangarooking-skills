# X Platform Hook Method

Use this file when the requested platform is `X`, `Twitter`, `推特`, or when the user asks for tweet/post/thread hooks.

## Source Basis

The current platform method is derived from:

- `../title-library/x-hot-hooks.md`
- X Help Center post and thread constraints: standard posts are typically 280 characters; threads connect multiple posts.
- Public hook-writing references sampled on 2026-06-14, including Ship 30 for 30, Write With AI, OpenTweet, and Sprout Social.

## Platform Positioning

On X, the "title" is usually the first line or first post. It must stop the scroll, create a reason to reply/repost/bookmark, and still sound like a human wrote it.

Do not write X hooks like WeChat headlines. Avoid dense Chinese headline punctuation, long stacked claims, and complete article summaries. X works better when the first line creates tension and the next line pays it off.

## Output Modes

Choose one mode from the user's request. If not specified, default to `single_post_hook`.

1. `single_post_hook`: one post opening line or short post, target 80-220 characters.
2. `thread_opener`: first post of a thread, target 120-260 characters, should imply the thread payoff.
3. `quote_post_frame`: short framing line for quote posting another post, target 30-140 characters.

## Platform Traits

Prioritize these traits:

1. **First-line tension**: the first 8-14 words should contain the take, surprise, or stakes.
2. **Conversational clarity**: sound like a sharp person thinking out loud, not a media headline.
3. **Reply potential**: leave a debatable edge, concrete question, or identity tension.
4. **Bookmark value**: promise a useful breakdown, checklist, ranking, teardown, or repeatable lesson.
5. **Proof over hype**: pair strong claims with evidence words such as `I tested`, `data`, `screenshots`, `examples`, `breakdown`, or `receipts`.
6. **Specific audience**: call out builders, founders, creators, devs, AI operators, marketers, or students when useful.
7. **One idea per hook**: do not cram launch, tutorial, opinion, and conclusion into one post.
8. **Whitespace rhythm**: 1-3 short lines beat one dense paragraph.
9. **Low hashtag dependence**: use zero or one hashtag only when it adds discovery value.
10. **Currentness without fake urgency**: use `today`, `just shipped`, or `this week` only when true.

## X-Specific Formulas

Generate X hooks from these formulas. For X platform batches, produce exactly 3 variants per formula unless the user asks for a smaller set.

1. `Hot take + proof`: `[Strong opinion]. I have [evidence] to prove it.`
2. `Everyone is wrong`: `Everyone is doing [thing] wrong. The real move is [insight].`
3. `I tested it`: `I spent [time] testing [tool/topic]. The surprising part: [finding].`
4. `Before/after`: `[Old way] is dead. [New way] is what works now.`
5. `Audience callout`: `If you are [specific audience], you should pay attention to [thing].`
6. `Hidden mechanic`: `Most people missed the important part of [event/product]: [mechanic].`
7. `Mistake confession`: `My biggest mistake with [topic]: [mistake].`
8. `Contrarian lesson`: `The lesson from [case] is not [obvious lesson]. It is [real lesson].`
9. `Receipts thread`: `[Claim]. Here are [number] examples/receipts.`
10. `Tool replacement`: `I used to use [old tool/workflow] for [job]. Now I use [new tool/workflow].`
11. `Question bait, not clickbait`: `What happens when [new force] meets [old workflow]? I tried it.`
12. `Quote-post frame`: `This is the part everyone is underestimating.`

## Title-Library Reuse

When the user asks for X proven-title reuse:

1. Prefer `../../scripts/retrieve_title_examples.py` before opening the full library:

```bash
python3 ../../scripts/retrieve_title_examples.py --platform x --query "<topic words>" --mechanism "<optional mechanism>" --limit 10
```

2. Match by mechanism first, not nouns:
   - hot take with proof
   - contrarian lesson
   - build-in-public proof
   - tool replacement
   - thread promise
   - founder/operator lesson
   - reply-provoking question
   - quote-post frame
3. Convert the source hook into a skeleton.
4. Replace the subject, proof, audience, and payoff with facts from the current content.
5. Keep the hook native to X: shorter, more conversational, and less conclusive than a WeChat headline.

## Scoring Rubric

Score each X candidate out of 10:

- 0-2: first-line stop power
- 0-2: specificity and proof
- 0-2: reply/repost/bookmark potential
- 0-2: platform-native voice
- 0-2: truthfulness and content fit

Penalize:

- `-2` if it sounds like a WeChat article title.
- `-2` if it makes an unsupported absolute claim.
- `-1` if it exceeds 260 characters for a standard post opener.
- `-1` if it needs more than one hashtag to work.

## Output Add-On

When X platform adaptation is requested, append:

```markdown
**X 平台 Hook 池**

模式：

1. Hot take + proof
- ...
- ...
- ...

[continue through selected formulas]

**最佳 X Hook**
Hook：
理由：

**可直接发的首帖版本**
...
```
