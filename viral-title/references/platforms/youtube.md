# YouTube Title Method

Use this file when the requested platform is `YouTube`, `油管`, `Youtube video`, or when the user asks for video titles, title-thumbnail packaging, or long-form video hooks.

## Source Basis

The current platform method is derived from:

- `../title-library/youtube-hot-titles.md`
- YouTube Help title and thumbnail tips: keep titles accurate, succinct, front-load important words, limit all caps and emoji, and choose between searchable and intriguing titles.
- YouTube Help CTR guidance: packaging should be judged with impressions, CTR, traffic source, average view duration, and viewer fit; clickbait with low average view duration hurts recommendations.
- YouTube thumbnail policy: do not use thumbnail/title combinations that mislead viewers about what is in the video.

## Platform Positioning

On YouTube, the title is one half of the package. The title should create a clear promise; the thumbnail should create the visual question. Do not make the title and thumbnail say the same thing.

Default to a title that works on Home/Suggested unless the user explicitly asks for search SEO. For search videos, clarity beats curiosity. For discovery videos, curiosity must still be honest and quickly paid off in the video.

## Output Modes

Choose one mode from the user's request. If not specified, default to `discovery_title`.

1. `discovery_title`: Home/Suggested-oriented, curiosity plus payoff, target 45-70 characters in English or 14-28 Chinese characters.
2. `search_title`: tutorial/review/query-oriented, front-load keyword and outcome.
3. `challenge_title`: experiment, transformation, timed task, or extreme test.
4. `review_comparison_title`: product, model, tool, or service comparison.
5. `essay_title`: broader idea, documentary, or opinion video.
6. `shorts_title`: shorter and more direct; often result-first or question-first.

## Platform Traits

Prioritize these traits:

1. **Title-thumbnail gap**: title names the promise; thumbnail shows the visual contrast, result, or stakes.
2. **Front-loaded topic**: put the searchable noun, product, person, or conflict early.
3. **Retention-safe curiosity**: raise a question the video actually answers in the first 30-60 seconds.
4. **Clear viewer payoff**: make it obvious why the viewer should spend 5-20 minutes.
5. **Specific format signal**: `I Tried`, `I Tested`, `I Built`, `I Ranked`, `X vs Y`, `Beginner to Pro`, `Mistakes`, `Full Guide`.
6. **Human stakes**: money, time, skill, status, risk, embarrassment, taste, survival, or transformation.
7. **Search vs browse choice**: do not mix a dry SEO title with a curiosity thumbnail unless the video is search-led.
8. **Mobile readability**: avoid overly long titles; important words must survive truncation.
9. **No metadata fraud**: do not imply a celebrity, product result, or dramatic event that is not in the video.
10. **Series discipline**: put episode numbers, channel branding, and repeated series labels at the end or omit them.

## YouTube-Specific Formulas

Generate YouTube titles from these formulas. For YouTube platform batches, produce exactly 3 variants per formula unless the user asks for a smaller set.

1. `I tested`: `I Tested [tool/topic] for [time/task]`
2. `Unexpected result`: `[Subject] Was Not What I Expected`
3. `Transformation`: `I Turned [input] Into [output] With [method]`
4. `Extreme constraint`: `I Tried [task] With Only [constraint]`
5. `Before/after`: `From [old state] to [new state] in [time]`
6. `Comparison`: `[A] vs [B]: Which One Actually Wins?`
7. `Mistake warning`: `Stop Doing [common behavior] in [domain]`
8. `Beginner guide`: `[Topic] Explained for Beginners`
9. `Ranking/list`: `I Ranked [number] [tools/options] So You Do Not Have To`
10. `Hidden feature`: `[Tool/Product] Has a Feature Nobody Talks About`
11. `Myth bust`: `Everyone Is Wrong About [topic]`
12. `Documentary/essay`: `The Real Reason [trend/event] Is Happening`
13. `Challenge payoff`: `Can [tool/person] [hard task]?`
14. `Build in public`: `I Built [thing] in [time] Using [tool]`
15. `Cost/time result`: `I Spent [money/time] to Find Out If [claim] Is True`

## Title-Thumbnail Pairing

For each serious YouTube candidate, also draft thumbnail text. Use 1-5 words, not a subtitle.

Pairing rules:

1. If the title is clear/searchable, make the thumbnail emotionally visual.
2. If the title is curiosity-led, make the thumbnail concrete enough to avoid vagueness.
3. Do not duplicate the title in the thumbnail.
4. Use contrast pairs: `old/new`, `before/after`, `cheap/expensive`, `human/AI`, `slow/fast`, `fail/pass`.
5. Avoid thumbnail text that implies something not shown in the video.

## Title-Library Reuse

When the user asks for YouTube proven-title reuse:

1. Prefer `../../scripts/retrieve_title_examples.py` before opening the full library:

```bash
python3 ../../scripts/retrieve_title_examples.py --platform youtube --query "<topic words>" --mechanism "<optional mechanism>" --limit 10
```

2. Match by mechanism first, not nouns:
   - I tested it
   - unexpected result
   - transformation
   - extreme constraint
   - comparison
   - mistake warning
   - beginner guide
   - ranking/list
   - hidden feature
   - documentary/essay
3. Convert the source title into a skeleton.
4. Replace the subject, result, constraint, and payoff with facts from the current video.
5. Add thumbnail text only after the title promise is clear.

## Scoring Rubric

Score each YouTube candidate out of 10:

- 0-2: click promise and curiosity
- 0-2: topic clarity and front-loaded specificity
- 0-2: thumbnail pairing potential
- 0-2: retention safety and truthful payoff
- 0-2: platform-native voice

Penalize:

- `-3` if the title overpromises beyond the video.
- `-2` if it is too vague to understand before clicking.
- `-2` if it reads like a WeChat article title or X post.
- `-1` if the important topic appears only at the end.
- `-1` for unnecessary all caps, emoji, or episode branding.

## Output Add-On

When YouTube platform adaptation is requested, append:

```markdown
**YouTube 标题包装池**

模式：

1. I tested
- 标题：
  缩略图字：
  首屏承诺：

[continue through selected formulas]

**最佳 YouTube 标题**
标题：
缩略图字：
理由：

**A/B 测试备选**
1. ...
2. ...
3. ...
```
