# Bilibili Title Method

Use this file when the requested platform is `B站`, `Bilibili`, `哔哩哔哩`, or when the user asks for B站视频标题、封面字、标签、分区语感.

## Source Basis

The current platform method is derived from:

- `../title-library/bilibili-hot-titles.md`
- Bilibili UP主创作手册: viewers decide quickly, title and cover are both important, title should be concise, front-load key information, avoid too many adjectives, and target 25 Chinese characters or fewer.
- Prior project memory: B站 public web surfaces and UP pages are workable; 收藏 and 投币 are often better topic-value proxies than likes.

## Platform Positioning

B站标题要像“视频入口”，不是公众号文章标题，也不是 YouTube 英文包装。它需要让用户一眼知道：谁/什么东西，在干什么，有什么亮点，属于哪个分区语境。

Default to a title-cover-tag package:

- 标题：25 字以内优先，重点前置。
- 封面字：1-6 个字，宁少勿多，最好和标题互补。
- 标签：类型标签 + 特色标签 + 热点/活动标签。
- 互动价值：知识类重收藏，体验/测评类重投币，娱乐类重弹幕和转发。

## Output Modes

Choose one mode from the user's request. If not specified, default to `standard_bilibili_video`.

1. `standard_bilibili_video`: 中视频标题，适合知识、科技、生活、娱乐。
2. `knowledge_title`: 知识区/科技区/教程类，重信息密度和收藏价值。
3. `review_title`: 数码、AI工具、模型、游戏、软件测评，重实测和结论。
4. `challenge_title`: 挑战、实验、整活、极限任务，重过程悬念。
5. `reaction_title`: 反应、吐槽、锐评、看完后感，重情绪和观点。
6. `series_title`: 系列内容，系列名后置或弱化，不抢主题。
7. `story_mode_title`: 竖屏/短视频，更短、更口语、更结果前置。

## Platform Traits

Prioritize these traits:

1. **25字以内**: titles longer than this risk truncation and comprehension loss.
2. **重点前置**: put product,人物,热点,事件,or result at the front.
3. **三元素组合**: choose at least three from `热点/人物/事件/类型/亮点`.
4. **分区语感**: 科技区讲实测、效率、工具链; 知识区讲看懂、拆解、避坑; 游戏区讲版本、角色、机制、挑战; 生活区讲真实体验和反差; 鬼畜娱乐讲梗和情绪。
5. **封面互补**: cover text should not repeat the title; it should sharpen the click question.
6. **收藏/投币价值**: tutorials, workflows, and tool lists should imply usefulness worth saving.
7. **B站口语**: allow `离谱`, `太猛了`, `绷不住`, `看傻了`, `这也行`, but only when tone fits.
8. **避免公众号腔**: avoid long clauses, policy-news density, and article-style conclusions.
9. **避免标题党伤害完播**: curiosity must be paid off early.
10. **社区感**: where natural, title can imply UP主亲测、踩坑、复盘、求三连价值.

## Bilibili-Specific Formulas

Generate B站 titles from these formulas. For B站 platform batches, produce exactly 3 variants per formula unless the user asks for a smaller set.

1. `实测结论`: `实测[对象]，[核心结论]`
2. `我用/我让`: `我让[工具/对象][完成任务]`
3. `挑战约束`: `只用[限制]，能做出[结果]吗？`
4. `反差发现`: `[对象]最离谱的不是[表象]`
5. `避坑提醒`: `别再这样用[工具/方法]了`
6. `教程收藏`: `[任务]保姆级教程`
7. `效率结果`: `[时间]做完[交付物]`
8. `对比测评`: `[A] vs [B]，谁更适合[场景]？`
9. `热点借势`: `[热点/新品]来了，我先测了[任务]`
10. `分区梗感`: `[人群]看完直接[情绪/动作]`
11. `隐藏玩法`: `[工具/产品]这个功能太容易被低估`
12. `复盘拆解`: `拆完[案例]，我发现[规律]`
13. `失败反转`: `我以为会翻车，结果[反转]`
14. `收藏清单`: `[数量]个[工具/技巧]，建议收藏`
15. `UP主体验`: `用了[时间]，我终于懂了[对象]`

## Title-Cover-Tag Pairing

For each serious B站 candidate, also draft cover text and tags.

Pairing rules:

1. 封面字控制在 1-6 个字，突出情绪或结果。
2. 标题说清楚对象和任务，封面展示反差、结果、失败、速度、爽点。
3. 标签至少给 6 个，其中前三个最重要。
4. 标签分三类:
   - 类型: AI, 科技, 数码, 编程, 教程, 学习, 游戏, 生活, VLOG.
   - 特色: 工具名, 模型名, UP主系列名, 工作流名.
   - 热点/活动: 新品发布, 热门模型, 节日, 平台活动.
5. If the content is tutorial/workflow, make one title version explicitly collectible.

## Title-Library Reuse

When the user asks for B站 proven-title reuse:

1. Prefer `../../scripts/retrieve_title_examples.py` before opening the full library:

```bash
python3 ../../scripts/retrieve_title_examples.py --platform bilibili --query "<topic words>" --mechanism "<optional mechanism>" --limit 10
```

2. Match by mechanism first, not nouns:
   - 实测结论
   - 我用/我让
   - 挑战约束
   - 避坑提醒
   - 教程收藏
   - 对比测评
   - 隐藏玩法
   - 复盘拆解
   - 失败反转
   - 收藏清单
3. Convert the source title into a skeleton.
4. Replace object, task, result, tone, and cover text with facts from the current video.
5. Avoid stale memes and old hotspot wording unless the current B站 audience still recognizes it.

## Scoring Rubric

Score each B站 candidate out of 10:

- 0-2: 一眼看懂对象和任务
- 0-2: 点击欲和封面互补
- 0-2: 分区语感和社区感
- 0-2: 收藏/投币/弹幕价值
- 0-2: 真实、不过度标题党

Penalize:

- `-2` if it exceeds 30 Chinese characters without a reason.
- `-2` if it sounds like a WeChat article title.
- `-2` if it copies YouTube English structure too directly.
- `-2` if the title promises a result not shown in the video.
- `-1` if it uses too many adjectives instead of concrete nouns.

## Output Add-On

When B站 platform adaptation is requested, append:

```markdown
**B站标题包装池**

模式：

1. 实测结论
- 标题：
  封面字：
  标签：
  互动价值：

[continue through selected formulas]

**最佳 B站标题**
标题：
封面字：
前三标签：
理由：

**A/B 测试备选**
1. ...
2. ...
3. ...
```
