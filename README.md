<h1 align="center">🧰 Kangarooking Skills</h1>

<p align="center"><strong>我自己平时跑通工作流沉淀的一些 Agent Skill，都开源在这里了。有需要的朋友自取，别忘了点个Star。</strong></p>

<p align="center">
  <a href="https://github.com/kangarooking/kangarooking-skills/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/kangarooking/kangarooking-skills?style=for-the-badge&logo=github&color=ffb000"></a>
  <img alt="Skills" src="https://img.shields.io/badge/Skills-13-10b981?style=for-the-badge">
  <img alt="Agent Skills" src="https://img.shields.io/badge/Agent_Skills-Standard-7c3aed?style=for-the-badge">
</p>

<p align="center">
  <img alt="Claude Code Skill" src="https://img.shields.io/badge/Claude_Code-Skill-d97706?style=flat-square">
  <img alt="Codex Skill" src="https://img.shields.io/badge/Codex-Skill-10b981?style=flat-square">
  <img alt="Agent Compatible" src="https://img.shields.io/badge/Agent-Compatible-3b82f6?style=flat-square">
</p>

每个目录都是 Agent 可以直接读取的结构化工作流，包含 `SKILL.md`，复杂任务还会配套脚本、参考资料和可复用模板。

适用于 Claude Code、Codex，以及其他支持 [Agent Skills](https://agentskills.io/) 开放标准的 Agent。

---

## 📋 目录

| 名字 | 一句话 | 分类 |
| --- | --- | --- |
| 🎨 [apimart-image-gen](./apimart-image-gen) | 通过 APIMart 调用 GPT-Image-2，生成、轮询并下载图片 | 图片生成 |
| 🧩 [multi-agent-image](./multi-agent-image) | 用设计编译、多 Agent 协作和案例库完成系列图片生产 | 图片生成 |
| 🐉 [hy-3d-gen](./hy-3d-gen) | 通过腾讯混元生成文生 3D、图生 3D 和 PBR 模型 | 3D 生成 |
| 🎬 [scroll-promo-site-builder](./scroll-promo-site-builder) | 把产品做成滚动控制、电影感强的动效网站 | 动效网站 |
| ✍️ [ai-article-daily](./ai-article-daily) | 从 AI 热点选题到公众号文章日更的一套完整流程 | 内容生产 |
| 🔥 [viral-topic](./viral-topic) | 跨公众号、X、B站和 YouTube 寻找近期爆款选题 | 内容增长 |
| 🧲 [viral-title](./viral-title) | 为公众号、X、YouTube 和 B站批量生成高潜标题 | 内容增长 |
| 🐦 [twitter-monitor](./twitter-monitor) | 抓取 X/Twitter 博主动态并按需同步到飞书多维表格 | 信息监控 |
| 🎥 [video-downloader](./video-downloader) | 下载多平台原视频，提取原始文案、元数据和 ASR 转写 | 素材处理 |
| 📚 [book-illustration-workflow](./book-illustration-workflow) | 管理书稿截图、配图、回填和飞书同步 | 写书工作流 |
| 🏗️ [harness-engineering](./harness-engineering) | 为项目初始化 Plan-Build-Verify Harness Engineering 框架 | Agent 工程 |
| 🧭 [task-harness](./task-harness) | 把长任务拆成可追踪、可验证、可恢复的任务系统 | Agent 工程 |
| 🌱 [reshape-your-life](./reshape-your-life) | 从使命、身份到行动，重新梳理人生方向 | 个人成长 |

---

## 📦 安装方式

### 直接让 Agent 安装

在 Claude Code、Codex 等支持 Agent Skills 的工具里，直接说：

```text
帮我安装这个 skill：https://github.com/kangarooking/kangarooking-skills/tree/main/<skill-name>
```

把 `<skill-name>` 换成目录里的名称，例如 `viral-title`、`video-downloader` 或 `scroll-promo-site-builder`。

### 手动安装

```bash
git clone https://github.com/kangarooking/kangarooking-skills.git

# Codex
mkdir -p ~/.codex/skills
cp -R kangarooking-skills/<skill-name> ~/.codex/skills/

# Claude Code
mkdir -p ~/.claude/skills
cp -R kangarooking-skills/<skill-name> ~/.claude/skills/
```

如果你的 Agent 暂时不支持 Skill 安装，也可以把对应目录的 `SKILL.md` 和它引用的资源放进项目，让 Agent 按照其中的流程执行。

---

## ✨ Skills

### 🎨 [apimart-image-gen](./apimart-image-gen)

> 一句话调用 APIMart GPT-Image-2，支持文生图、参考图、分辨率与比例控制，并自动等待和下载结果。

- 支持 `1k`、`2k`、`4k` 和常见画面比例
- 支持 URL、本地图片与多张参考图
- API Key 只从环境变量读取，不写入代码和提交记录

**适合说：**“生成一张 2K、16:9 的公众号封面，并把结果下载下来。”

### 🧩 [multi-agent-image](./multi-agent-image)

> 把设计分析、参考图选择、GPT-Image-2 生成和系列一致性组织成多 Agent 图片工作流。

- 内置设计编译能力和案例库复用
- 支持批量生成、系列套图和风格一致性
- 适合 Hermes 等需要多阶段交互的 Agent 环境

**适合说：**“参考这套风格，生成 6 张视觉统一的系列配图。”

### 🐉 [hy-3d-gen](./hy-3d-gen)

> 输入文字或图片，通过腾讯混元生成可下载的 3D 模型。

- 支持文生 3D、图生 3D 和多视图生 3D
- 支持 PBR、白模、草图生成和智能拓扑
- 默认走 TokenHub/OpenAI 兼容接口，可显式回退腾讯云 SDK

**适合说：**“用这张龙的图片生成一个带 PBR 材质的 GLB 模型。”

### 🎬 [scroll-promo-site-builder](./scroll-promo-site-builder)

> 把产品资料变成滚动驱动、电影感强、可本地交付的动效网站。

- 用 `image2.0` 和 `Seedance 2.0` 生成连续视觉故事
- 检查真实首尾帧，处理连接段、短溶解和视频连续性
- 输出 Vite + React 网站、移动端降级和本地预览包
- 借鉴 [`oso95/scroll-world`](https://github.com/oso95/scroll-world) 的滚动视频与边界帧方法，并保留完整 MIT 归属说明

**适合说：**“把这个产品做成滚动时画面前进、回滚时画面倒放的动效网站。”

### ✍️ [ai-article-daily](./ai-article-daily)

> 围绕 AI 热点完成选题、研究、写作和公众号日更。

- 从热点发现进入文章选题
- 组织资料、观点、结构和正文
- 适合定时写作与持续内容运营

**适合说：**“根据今天的 AI 热点，帮我完成一篇公众号文章。”

### 🔥 [viral-topic](./viral-topic)

> 在多个内容平台寻找近期爆款和低粉高表现样本，为起号提供选题参考。

- 覆盖公众号、X/Twitter、B站和 YouTube
- 保留来源链接、账号指标、时间窗口和爆款证据
- 根据平台调用对应的选题采集逻辑

**适合说：**“找一下最近一周 AI Agent 方向的跨平台爆款选题。”

### 🧲 [viral-title](./viral-title)

> 用通用机制和平台方法论批量生成标题，并从候选中推荐最值得发布的一个。

- 覆盖公众号、X/Twitter、YouTube 和 B站
- 支持本地标题库检索与相似骨架复用
- 记录选择与反馈，让标题方法持续迭代

**适合说：**“给这篇公众号文章生成 30 个标题，并推荐最佳标题。”

### 🐦 [twitter-monitor](./twitter-monitor)

> 按账号抓取 X/Twitter 最新动态，输出结构化数据并按需同步飞书。

- 接受用户 ID、`@handle` 或主页 URL
- 输出 JSON/CSV 和互动指标
- 支持飞书多维表格及后续定时运行指导

**适合说：**“抓取这 5 个 X 博主的最新推文，整理成 CSV。”

### 🎥 [video-downloader](./video-downloader)

> 把视频平台链接整理成原视频、发布文案、音频转写和标准化元数据。

- 支持抖音、B站、YouTube 和小红书
- 区分平台原始文案与视频 ASR 转写
- 视频号暂用微信小程序「kg百宝箱」作为下载前置

**适合说：**“下载这个抖音视频，同时提取原始文案和口播稿。”

### 📚 [book-illustration-workflow](./book-illustration-workflow)

> 把一章书稿的截图规划、图号命名、正文回填和飞书同步串成稳定流程。

- 生成章节截图总表和实操提示词
- 统一图号、文件名与原文插入位置
- 清理作者备注并同步读者版正文

**适合说：**“按书稿截图流程，把这一章需要的图全部规划出来。”

### 🏗️ [harness-engineering](./harness-engineering)

> 为新项目一键建立规划、生成、评估和文档维护协同的开发框架。

- 初始化 Plan-Build-Verify 工作流
- 提供 Agent、命令、Hooks 和项目文档结构
- 适合长周期、需要自验证的 AI 开发任务

**适合说：**“给这个项目初始化 Harness Engineering。”

### 🧭 [task-harness](./task-harness)

> 把复杂需求拆成有验收标准和状态记录的长任务系统，减少 Agent 跑偏和断档。

- 生成结构化任务清单与唯一状态文件
- 强调测试、提交和可恢复执行
- 适合多会话开发与持续任务追踪

**适合说：**“把这个需求拆成一个能让 Agent 连续执行的任务系统。”

### 🌱 [reshape-your-life](./reshape-your-life)

> 从使命、身份、信念、能力、行为和环境六个层次重新梳理人生方向。

- 适合迷茫、方向不明或陷入重复执行循环时使用
- 从顶层使命向下落到具体行动
- 使用 NLP 理解层次进行结构化引导

**适合说：**“我最近很忙但没有方向，帮我重新梳理人生。”

---

## 🔗 关联项目

### [cangjie-skill](https://github.com/kangarooking/cangjie-skill)

把书的方法论蒸馏成可触发、可组合、可测试的 AI Skills。它负责“从书里生产 Skill”，这里负责集中收纳和开源已经跑通的 Skill。

---

## 🤝 贡献

欢迎提交新的 Skill。建议每个目录至少包含：

- `SKILL.md`：技能定义和执行流程
- `references/`：需要按需加载的参考资料（可选）
- `scripts/`：需要稳定复用的自动化脚本（可选）
- `assets/`：模板和交付资源（可选）

## 📄 许可

除各 Skill 另有说明外，本仓库原创内容按 MIT License 开源；引用或改编的第三方内容以对应目录中的 `LICENSE`、`NOTICE` 或归属说明为准。
