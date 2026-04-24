# Multi-Agent Image

`multi-agent-image` 是一个面向 Hermes 的图片生成工作流 skill。

它的重点不是“再做一个单次生图脚本”，而是把图片生成这件事拆成更稳定的流程能力：

- 用多阶段工作流提升 prompt 和参数决策质量
- 用案例库沉淀历史结果，支持风格参考复用
- 支持两阶段交互，让用户先看参考再决定是否生成
- 支持批量生成和系列套图，适合内容矩阵和统一视觉产出
- 使用 apimart 的 `gpt-image-2` 作为当前图片生成通道

## 它适合什么场景

- 活动海报、课程海报、社群传播图
- 商品图、广告图、电商素材
- PPT 配图、章节封面、视觉方向稿
- 信息图风格视觉、教学演示图
- 系列内容图，例如海报 + Banner + 方图 + 详情页头图

如果你要的是“单张图快速生成”，它也能做；如果你要的是“围绕一组图建立持续复用的工作流”，这才是它更有价值的地方。

## 核心能力

### 1. 多阶段生成

默认流程大致是：

1. 分析用户需求
2. 选择任务类型、方向、比例和质量
3. 调用设计编译步骤生成更强的最终 prompt
4. 提交到 `gpt-image-2`
5. 轮询任务、下载结果
6. 做基础质量评分
7. 自动归档并写入案例库

也就是说，这个 skill 的重点不是把一句 prompt 直接发给模型，而是把“分析、编排、沉淀、复用”一起做掉。

### 2. 案例库

生成完成后，图片和元数据会自动保存到案例库中，后续可以：

- 按任务类型查看案例
- 按关键词搜索案例
- 用历史高分案例作为风格参考
- 在交互式流程中先展示给用户选择

适合反复做同一类视觉任务的人，比如课程海报、商品主图、内容封面、品牌社媒图。

### 3. 交互式两阶段生成

这个 skill 支持先展示案例，再让用户决定：

1. `prepare()` 负责生成选择文本
2. 用户回复编号或跳过
3. `execute()` 再执行真正的生成

这个模式特别适合 Hermes 这类对话环境，因为执行代码本身不能中途暂停等待用户输入。

### 4. 批量与系列套图

除了单张生成，还支持：

- 同一需求多风格 A/B 测试
- 同一需求多比例适配
- 多 brief 批量生成
- 先生成母图，再生成风格统一的系列子图

如果你要做一整套内容素材，而不是一张孤立图片，这部分会很有用。

## 目录结构

```text
multi-agent-image/
├── SKILL.md
├── README.md
├── scripts/
│   ├── install.py
│   ├── quick_start.py
│   ├── orchestrator_v2.py
│   ├── interactive_run.py
│   ├── case_library.py
│   ├── case_selector.py
│   ├── batch_generator_v2.py
│   ├── series_generator.py
│   └── gpt_image2_generator.py
├── references/
│   └── agents/
└── templates/
    └── linear_batch.py
```

## 依赖与边界

这里需要明确一点：

**当前版本不是完全自包含的。**

虽然 `multi-agent-image` 自己包含了工作流、交互、案例库、批量和系列生成逻辑，但“设计编译”这一步当前仍然依赖一个外部设计编译器运行时。也就是说：

- 图片生成编排在本 skill 内
- `gpt-image-2` 调用在本 skill 内
- 案例库和交互逻辑在本 skill 内
- 但最终 prompt 的设计编译步骤，当前不是完全内置的

所以如果你问“它和之前的 skill 是不是完全独立”：

- 从仓库组织上，现在它是独立 skill
- 从运行实现上，现在还不是完全独立运行时

这是当前实现状态，不是 README 叙事问题。

## 环境要求

- 已配置 `OPENAI_API_KEY`
- 已安装 Python 依赖：`openai`、`requests`
- Hermes 运行环境可用
- 本地存在可用的外部设计编译器运行时

## 安装

```bash
python3 ~/.hermes/skills/multi-agent-image/scripts/install.py
```

安装脚本会做这些事情：

- 把运行脚本复制到 `~/.hermes/agents/multi-agent-image/`
- 创建案例库、输出目录和各 agent 子目录
- 检查外部设计编译器运行时是否存在

## 配置 API Key

```bash
export OPENAI_API_KEY="sk-..."
```

这里使用的是 apimart 兼容接口下的 `gpt-image-2` 通道。

## 快速开始

### 方式 1：快速单次生成

```bash
cd ~/.hermes/agents/multi-agent-image
python3 quick_start.py "AI训练营招生海报，强调速度、增长、实战"
```

### 方式 2：完整工作流

```python
from orchestrator_v2 import run

run("AI训练营招生海报，强调速度增长实战")
```

### 方式 3：不参考历史案例，直接生成

```python
from orchestrator_v2 import run

run("赛博朋克猫咪黑客", use_reference=False)
```

## 交互式用法

### 第一步：展示可选案例

```python
from interactive_run import prepare

text = prepare("帮我做张 AI 训练营海报", task="poster")
print(text)
```

### 第二步：根据用户选择执行

```python
from interactive_run import execute

result = execute("帮我做张 AI 训练营海报", user_choice="1", task="poster")
```

支持的选择包括：

- `1`、`2`、`3` 这样的案例编号
- `n` 表示不参考案例，直接生成
- `y` 表示确认继续
- `case_001` 这样的案例 ID

## 批量生成

### 同需求多风格

```python
from batch_generator_v2 import batch_styles

batch_styles("AI训练营海报", task="poster")
```

### 同需求多比例

```python
from batch_generator_v2 import batch_aspects

batch_aspects("AI训练营海报", task="poster", aspects=["1:1", "16:9", "9:16"])
```

### 多需求批量

```python
from batch_generator_v2 import batch_briefs

batch_briefs(["海报A", "海报B", "海报C"], task="poster")
```

## 系列套图

```python
from series_generator import SeriesGenerator

sg = SeriesGenerator()
sg.create_series(
    master_brief="AI训练营系列视觉，科技蓝，专业商务感",
    items=[
        {"name": "主海报", "brief": "AI训练营招生主海报", "aspect": "3:4"},
        {"name": "Banner", "brief": "官网 Banner", "aspect": "16:9"},
        {"name": "朋友圈", "brief": "朋友圈推广方形图", "aspect": "1:1"},
    ],
    task="poster",
    direction="balanced"
)
```

这个模式适合统一一组图的视觉语言，而不是每张图都重新摸索。

## 输出内容

运行完成后，一般会得到：

- 生成图片文件
- 归档 JSON
- 案例库记录
- 批量或系列任务的汇总结果

默认输出目录通常在：

```text
~/.hermes/agents/multi-agent-image/output/
```

案例库目录通常在：

```text
~/.hermes/agents/multi-agent-image/case_library/
```

## 当前限制

- 当前版本仍依赖外部设计编译步骤，不是完全自包含 skill
- 目前图片通道主要围绕 `gpt-image-2`
- 系列生成仍然比较重，每张图都不是“毫秒级”工作流
- README 已避免写死上游 skill 名称，但代码层面的外部依赖仍然真实存在

## 后续可以继续做什么

如果后面要把它做成真正完全独立的 skill，下一步不是继续改 README，而是做代码级改造：

- 把设计编译逻辑内置进本仓库
- 去掉安装阶段对外部运行时的检查
- 去掉脚本里对外部 `design_image.py` 的直接调用

这样它才会从“独立仓库”真正变成“独立运行时”。

完整使用细节和长文档说明见 [SKILL.md](./SKILL.md)。
