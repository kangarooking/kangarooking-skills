# 袋鼠帝 Skills 技能仓库

这里是袋鼠帝的 Skills 技能集合，每个子目录代表一个独立的技能。

## 目录结构

```
kangarooking-skills/
├── apimart-image-gen/       # APIMart GPT-Image-2 异步图片生成与下载
├── book-illustration-workflow/ # 书稿截图、配图、回填与 Feishu 同步工作流
├── reshape-your-life/        # 重塑人生技能
├── harness-engineering/      # Harness Engineering 框架一键初始化
├── task-harness/             # Agent 长任务方向盘
├── ai-article-daily/         # 公众号起号skill
├── multi-agent-image/        # 多 Agent 图片生成工作流
├── twitter-monitor/          # X/Twitter 博主推文抓取与可选飞书同步
├── video-downloader/         # 多平台视频下载、原始发布文案提取与 ASR 转写
├── scroll-promo-site-builder/ # 滚动电影式产品动效网站生成、连续性审核与本地交付
├── hy-3d-gen/                # 腾讯混元生3D TokenHub/OpenAI 兼容接口生成 3D 模型
├── viral-topic/              # 多平台起号选题与爆款内容发现
├── viral-title/              # 多平台爆款标题生成与自进化标题库
└── ...
```

## Skills 列表

### apimart-image-gen

APIMart GPT-Image-2 异步图片生成技能。

适用于：
- 文生图和带参考图的图生图
- 控制 `1k`、`2k`、`4k` 输出分辨率
- 控制 `16:9`、`21:9`、`1:1` 等比例或直接传像素尺寸
- 提交 APIMart 异步任务、轮询任务状态并下载图片结果
- 使用环境变量读取 API key，避免密钥进入 prompt、脚本或提交记录

附带：
- APIMart GPT-Image-2 API 参考
- 纯标准库 Python 命令行 helper
- Codex UI 元数据

使用：
- “用 apimart-image-gen 生成一张 16:9 的公众号封面”
- “用这两张参考图生成一张 2K 图片，并下载结果”
- “查询这个 APIMart task_id 的生成状态”

### book-illustration-workflow

书稿章节截图与配图工作流。

适用于：
- 梳理某一章需要哪些截图和成品图
- 逐步给出 Claude Code 的真实实操提示词
- 统一 `图号 -> 文件名 -> 原文位置`
- 把图片回填到本地 Markdown 正确位置
- 清理作者备注，生成读者版正文
- 按正文顺序同步到 Feishu 文档

附带：
- 章节截图总表模板
- 截图提示词模板
- 回填检查表

使用：直接说“按书稿截图流程来”或“帮我搞这一章的配图和截图”

### harness-engineering

基于 OpenAI (Codex)、Anthropic (三智能体架构)、LangChain (自验证循环) 的 Harness Engineering 框架。

在任意项目中一键初始化 Plan-Build-Verify 开发工作流：
- **4 个智能体**: Planner / Generator / Evaluator / Doc Gardener
- **4 个命令**: `/plan` / `/build` / `/qa` / `/sprint`
- **3 个 Hooks**: 循环检测 / 完成前检查 / 上下文注入
- **10 条黄金原则**: 无规格不编码、可测试验收标准、契约驱动等

使用: `/harness <项目描述>` 或说 "初始化 harness"

### reshape-your-life

重塑人生技能。

### task-harness

任务管理 Harness。

### multi-agent-image

独立的多 Agent 图片生成 skill。

适用于：
- 基于 `design-image-studio` 设计编译能力做更完整的图片生成工作流
- 使用 apimart `gpt-image-2` 做异步生成、轮询和下载
- 建立案例库并复用历史风格参考图
- 在 Hermes 中使用两阶段交互、批量生成和系列套图工作流

### twitter-monitor

X/Twitter 博主最新推文抓取技能。

适用于：
- 根据博主 ID、@handle 或主页 URL 抓取最近推文
- 配置 `twitterapi.io` API key 后执行一次性抓取
- 控制分页数，默认只抓 1 页
- 输出 JSON/CSV，包含内容、链接、作者、阅读量、点赞、转发、评论、收藏、是否回复、抓取时间等字段
- 按需通过 `feishu-cli` 同步到 Feishu/Lark 多维表格
- 抓取成功后按需引导 OpenClaw、Codex automation、cron 或 launchd 定时执行

### video-downloader

多平台视频素材下载与文案提取技能。

适用于：
- 输入抖音、B站、YouTube、小红书链接后下载原视频
- 提取平台原始发布文案、标题、描述、标签，保存为 `post_caption.txt`
- 下载后抽取音频，通过 SiliconFlow SenseVoiceSmall 或本地 Whisper 生成 `transcript.txt`
- 保存标准化 `metadata.json`，方便后续做内容分析、素材归档或接入其他 skill
- 给后续平台扩展预留 provider 入口

当前支持：
- 抖音：H5 解析为主线，失败时走 `yt-dlp` 备用路线
- B站：基于 `yt-dlp`
- YouTube：基于 `yt-dlp`
- 小红书：基于 `yt-dlp`
- 视频号：暂未直接支持。当前建议先在微信小程序「kg百宝箱」里粘贴视频号链接下载视频，再用本 skill 做本地 ASR 或后续处理

使用：
- “用 video-downloader 下载这个抖音视频，并提取文案”
- “把这个 B站/YouTube/小红书链接下载下来，不做 ASR”
- “下载后用 SiliconFlow 免费 ASR 转成简体中文文案”

### hy-3d-gen

腾讯混元生3D模型生成技能。

适用于：
- 用文本描述生成 3D 模型
- 用图片 URL 或 Base64 参考图生成 3D 模型
- 多视角图生 3D、PBR 材质、白模、草图生成、智能拓扑生成
- 默认通过 TokenHub/OpenAI 兼容接口调用，必要时显式回退腾讯云 SDK

使用：
- “用 hy-3d-gen 生成一个水晶中国龙 3D 模型”
- “用这张图片作为参考，生成 GLB 模型”
- “查询这个混元 3D JobId 的结果”

### scroll-promo-site-builder

滚动电影式产品动效网站生成技能。

**定位：面向产品发布、软件产品和 AI/Agent 项目的动效网站生产工作流。核心关键词：动效、网站。**

适用于：
- 把产品资料、参考网站或视频、品牌素材转成 4–7 幕连续视觉故事
- 直接使用 `image2.0` 生成角色、设备、关键视觉和首尾帧
- 直接使用 `Seedance 2.0` 生成场景视频与连接段
- 用相邻视频真实渲染的首尾帧检查连续性，并选择直连、连接段、短溶解或重生成
- 将审核后的连续视频映射到页面滚动进度，向下滚动前进、向上滚动倒放
- 生成 Vite + React + TypeScript 动效网站，并提供静态移动端、减少动效和视频失败降级
- 输出源码、本地预览包、macOS/Windows 启动脚本和验收清单

与 [`oso95/scroll-world`](https://github.com/oso95/scroll-world) 的关系：
- 本 Skill 借鉴了其滚动驱动视频、真实边界帧连接、短 GOP 编码等核心方法
- `scroll-world` 更偏 Higgsfield 驱动的可滚动 3D 世界和多片段原生 JS 引擎
- 本 Skill 更偏产品叙事、直接模型调用、React 单视频时间线、项目审核与本地交付
- 上游采用 MIT License；本目录保留了完整来源、版权和许可声明

使用：
- “用 scroll-promo-site-builder 把这个产品做成有电影感的动效网站”
- “参考这个视频，做一个滚动控制画面前进和倒放的产品网站”
- “检查这些场景视频的首尾帧，补齐连接段并打包本地预览”

### viral-topic

多平台起号选题与爆款内容发现技能。

适用于：
- 从公众号、X/Twitter、B站、YouTube 找近期爆款内容作为选题参考
- 公众号按“阅读数超过账号月均阅读 2 倍且阅读量不低于 1 万”判断爆款
- X/Twitter 与 B站保留低粉爆款逻辑，优先找内容表现明显超过作者粉丝规模的样本
- YouTube 只做近期爆款筛选，不默认做低订阅过滤
- 输出跨平台选题表，保留来源链接、账号/作者指标、时间窗口和爆款证据

内含子 skill：
- `wechat-viral-topic`
- `x-viral-topic`
- `bilibili-viral-topic`
- `youtube-viral-topic`

使用：
- “用 viral-topic 找 AI Agent 最近的起号选题”
- “帮我找公众号和 X 的低粉爆款参考”
- “看一下 B站和 YouTube 最近有什么爆款选题”

### viral-title

多平台爆款标题生成技能。

适用于：
- 给公众号、X/Twitter、YouTube、B站内容批量生成标题或首帖 Hook
- 按统一方法论生成第一阶段 30 个标题，并推荐最佳标题
- 按平台调性生成差异化标题：公众号标题、X Hook、YouTube 标题+缩略图字、B站标题+封面字+标签
- 从本地爆款标题库里检索相似标题骨架，套用到当前内容
- 根据用户最终选择、改稿、评分和反馈持续进化

附带：
- 公众号、X、YouTube、B站平台方法论
- 公众号 AI/科技爆款标题库与多平台标题骨架库
- 标题样本检索脚本
- 标题会话记录、反馈记录、反馈分析和种子评估脚本
- 共享机制关键词表，避免脚本关键词漂移

使用：
- “用 viral-title 给这篇公众号文章起标题”
- “给这个 YouTube 视频生成标题和缩略图字”
- “把这篇内容改成 B站标题包装”
- “套用标题库，给我 10 个 X Hook”

## 关联项目

### cangjie-skill

[cangjie-skill](https://github.com/kangarooking/cangjie-skill) 是把书的方法论蒸馏成可调用 AI Skills 的生成器工作流。

它适用于：
- 把一本书从普通摘要变成可触发、可组合、可测试的 skill 工具包
- 使用 RIA-TV++ 流水线完成整书理解、并行提取、三重验证、RIA++ 构造、Zettelkasten 链接和压力测试
- 为高价值书籍生成 `BOOK_OVERVIEW.md`、`INDEX.md`、多个独立 `SKILL.md` 和测试 prompts
- 作为更大的 skill 生态中的“蒸馏书”模块，与蒸馏人的 `nuwa-skill`、进化 skill 的 `darwin-skill` 配合使用

## 如何贡献

欢迎提交新的 Skills！请确保每个技能包含：
- `SKILL.md` - 技能定义文档
- `references/` - 相关参考资料（可选）

## 许可

MIT License
