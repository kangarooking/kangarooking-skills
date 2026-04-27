# 袋鼠帝 Skills 技能仓库

这里是袋鼠帝的 Skills 技能集合，每个子目录代表一个独立的技能。

## 目录结构

```
kangarooking-skills/
├── book-illustration-workflow/ # 书稿截图、配图、回填与 Feishu 同步工作流
├── reshape-your-life/        # 重塑人生技能
├── harness-engineering/      # Harness Engineering 框架一键初始化
├── task-harness/             # Agent 长任务方向盘
├── ai-article-daily/         # 公众号起号skill
├── multi-agent-image/        # 多 Agent 图片生成工作流
├── twitter-monitor/          # X/Twitter 博主推文抓取与可选飞书同步
└── ...
```

## Skills 列表

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

## 如何贡献

欢迎提交新的 Skills！请确保每个技能包含：
- `SKILL.md` - 技能定义文档
- `references/` - 相关参考资料（可选）

## 许可

MIT License
