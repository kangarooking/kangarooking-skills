# Multi-Agent Image

独立的多 Agent 图片生成 skill。

它建立在 `design-image-studio` 的设计编译能力之上，补充了：

- apimart `gpt-image-2` 生成通道
- 案例库与风格参考复用
- 两阶段交互式生成
- 批量生成与系列套图工作流

## 目录结构

```text
multi-agent-image/
├── SKILL.md
├── scripts/
├── references/agents/
└── templates/
```

## 依赖

- 已安装 `design-image-studio`
- 已设置 `OPENAI_API_KEY`（用于 apimart `gpt-image-2`）
- Python 依赖：`openai`、`requests`

## 快速开始

```bash
python3 ~/.hermes/skills/multi-agent-image/scripts/install.py
export OPENAI_API_KEY="sk-..."
cd ~/.hermes/agents/multi-agent-image
python3 quick_start.py "AI训练营招生海报，强调速度、增长、实战"
```

完整使用方式见 [SKILL.md](./SKILL.md)。
