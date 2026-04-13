# 袋鼠帝 Skills 技能仓库

这里是袋鼠帝的 Skills 技能集合，每个子目录代表一个独立的技能。

## 目录结构

```
kangarooking-skills/
├── reshape-your-life/        # 重塑人生技能
├── harness-engineering/      # Harness Engineering 框架一键初始化
├── task-harness/             # Agent 长任务方向盘
├── ai-article-daily/         # 公众号起号skill
└── ...
```

## Skills 列表

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

## 如何贡献

欢迎提交新的 Skills！请确保每个技能包含：
- `SKILL.md` - 技能定义文档
- `references/` - 相关参考资料（可选）

## 许可

MIT License
