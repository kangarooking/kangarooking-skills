---
name: hy-3d-gen
description: >
  输入文字或图片，通过腾讯混元生3D TokenHub/OpenAI 兼容接口或腾讯云 SDK 生成3D模型。支持文生3D、图生3D、多视图生3D、PBR、白模、草图生3D、智能拓扑生3D；当用户要求生成或查询混元3D模型时使用。
---

# 腾讯混元生3D Skill

本版本基于 ClawHub `@neck-cn/hy-3d-generation` 的本地安装副本改造，发布名为 `hy-3d-gen`。主要改造点是默认走 TokenHub/OpenAI 兼容 HTTP 接口，并保留腾讯云 SDK 作为显式回退后端。

## 本地 Codex 安全说明

此安装副本已做安全化处理：脚本不会自动执行 `pip install`。默认优先使用 TokenHub 的 OpenAI 兼容 HTTP 接口，使用 Python 标准库发起请求，不需要额外依赖；如显式使用 `--provider tencent`，缺少 `tencentcloud-sdk-python` 时脚本会退出并提示用户先在明确选择的 Python 环境中手动安装。生成任务会把 prompt、图片 URL 或 Base64 图片数据发送到腾讯混元生3D接口。

本地测试凭证可放在 skill 根目录的 `.env` 文件中，权限应为 `600`。脚本只会读取 `HY3D_OPENAI_API_KEY`、`TENCENT_MAAS_API_KEY`、`TOKENHUB_API_KEY`、`TENCENTCLOUD_SECRET_ID`、`TENCENTCLOUD_SECRET_KEY`、`TENCENTCLOUD_TOKEN`，并且不会覆盖进程中已经存在的同名环境变量。

## 功能描述

本 Skill 提供**混元生3D**能力，基于腾讯混元大模型，将文本描述或图片智能生成 3D 模型。默认使用 TokenHub OpenAI 兼容协议，可手动回退腾讯云 SDK。支持多视角图片输入、PBR 材质、自定义面数、多种输出格式。

| 场景 | 脚本 | 说明 |
|------|------|------|
| 一站式生成 | `main.py` | 提交任务 + 自动轮询，推荐使用 |
| 仅提交任务 | `submit_job.py` | 仅提交，返回 JobId |
| 仅查询任务 | `query_job.py` | 根据 JobId 查询/轮询结果 |
| 共享客户端 | `hy3d_api.py` | TokenHub + 腾讯云 SDK 双后端封装，不直接手动运行 |

### 🎯 选择规则

```
用户要求生成3D模型  →  main.py（一站式，最简单推荐）
用户要求提交后自行查询  →  submit_job.py + query_job.py（分步操作）
用户已有 JobId 要查结果  →  query_job.py（单独查询）
```

> 如果用户未指定使用哪种模式，Agent 应默认使用 `main.py` 一站式脚本。

### 支持特性

- **文生3D**：支持文本描述生成 3D 模型（最多 1024 字符）
- **图生3D**：支持输入图片 URL 或 Base64 生成 3D 模型
- **多视角图片**：支持 left/right/back/top/bottom/left_front/right_front 多视角输入
- **PBR 材质**：支持开启 PBR 材质生成
- **自定义面数**：支持 10000-1500000 面数范围
- **多种生成类型**：Normal（带纹理）、LowPoly（智能拓扑）、Geometry（白模）、Sketch（草图生成）
- **多种输出格式**：默认 obj+glb，可选 STL、USDZ、FBX
- **模型版本选择**：支持 3.0 和 3.1 版本
- **OpenAI 兼容接口**：优先使用 TokenHub `https://tokenhub.tencentmaas.com/v1/api/3d/submit` 与 `/query`
- **双后端选择**：`--provider auto` 默认优先 TokenHub；`--provider tokenhub` 强制 TokenHub；`--provider tencent` 强制腾讯云 SDK
- **显式安装依赖**：TokenHub 后端无需额外依赖；腾讯云 SDK 后端需要用户在明确选择的 Python 环境中安装所需 SDK
- **智能凭证检测**：优先从环境变量获取密钥，未配置时提示用户开通

## 环境配置指引

### 密钥配置

本 Skill 默认需要 TokenHub OpenAI 兼容 API key；腾讯云 SDK 后端需要腾讯云 API 密钥。

#### TokenHub / OpenAI 兼容接口（默认）

```bash
export HY3D_OPENAI_API_KEY="你的 TokenHub API key"
```

也可使用 `TENCENT_MAAS_API_KEY` 或 `TOKENHUB_API_KEY`。不要把 key 写进脚本源码。

#### 腾讯云 SDK 后端（可选回退）

Step 1: 开通混元3D服务

🔗 **[腾讯云3D视觉创作控制台](https://console.cloud.tencent.com/ai3d)**

Step 2: 获取 API 密钥

🔗 **[腾讯云 API 密钥管理](https://console.cloud.tencent.com/cam/capi)**

Step 3: 设置环境变量

**Linux / macOS：**
```bash
export TENCENTCLOUD_SECRET_ID="你的SecretId"
export TENCENTCLOUD_SECRET_KEY="你的SecretKey"
```

如需持久化：
```bash
echo 'export TENCENTCLOUD_SECRET_ID="你的SecretId"' >> ~/.zshrc
echo 'export TENCENTCLOUD_SECRET_KEY="你的SecretKey"' >> ~/.zshrc
source ~/.zshrc
```

**Windows (PowerShell)：**
```powershell
$env:TENCENTCLOUD_SECRET_ID = "你的SecretId"
$env:TENCENTCLOUD_SECRET_KEY = "你的SecretKey"
```

> ⚠️ **安全提示**：切勿将密钥硬编码在代码中。

## Agent 执行指令（必读）

> **本节是 Agent（AI 模型）的核心执行规范。当用户请求生成 3D 模型时，Agent 必须严格按照以下步骤执行。依赖安装、持久化环境变量、上传敏感图片或扩大本机环境改动前，需要用户明确确认。**

### 🔑 通用执行规则

1. **触发条件**：用户提供了文本描述或图片，且意图为生成 3D 模型。
2. **受控执行原则**：依赖与凭证已经配置、且用户明确要生成 3D 模型时，Agent 可直接执行脚本；不得自动安装依赖或改写 shell 配置。
3. **自动选择脚本**：默认使用 `main.py`（一站式），除非用户明确要求分步操作。默认 `--provider auto`，如果存在 TokenHub key 会优先走 OpenAI 兼容接口。
4. **⛔ 禁止使用大模型自身能力替代 3D 生成（最高优先级规则）**：
   - Agent 严禁自行编造 3D 文件 URL 或描述生成结果。
   - 如果调用失败，Agent **必须**向用户返回清晰的错误说明。

---

### 📌 脚本一：一站式生成 `main.py`（推荐）

**适用场景**：用户请求生成 3D 模型，自动提交并等待结果

```bash
# 文生3D
python3 <SKILL_DIR>/scripts/main.py --prompt "文本描述"

# 图生3D
python3 <SKILL_DIR>/scripts/main.py --image-url "https://example.com/image.jpg"

# 强制使用 TokenHub OpenAI 兼容接口
python3 <SKILL_DIR>/scripts/main.py --provider tokenhub --model hy-3d-3.0 --prompt "一只小狗"

# 强制使用腾讯云 SDK 回退
python3 <SKILL_DIR>/scripts/main.py --provider tencent --model 3.0 --prompt "一只小狗"
```

**可选参数**：
- `--prompt <TEXT>`：文本描述，中文推荐，最多 1024 字符（与 image-url/image-base64 二选一）
- `--image-url <URL>`：输入图片 URL（与 prompt 二选一）
- `--image-base64 <BASE64>`：输入图片 Base64 数据（与 prompt 二选一）
- `--multi-view <JSON>`：多视角图片 JSON，如 `'[{"ViewType":"back","ViewImageUrl":"https://..."}]'`
- `--model <VERSION>`：模型版本，默认 `hy-3d-3.0`，可选 `3.0` / `3.1` / `hy-3d-3.0` / `hy-3d-3.1`
- `--enable-pbr`：开启 PBR 材质生成
- `--face-count <N>`：面数，默认 500000，范围 10000-1500000
- `--generate-type <TYPE>`：生成类型：Normal / LowPoly / Geometry / Sketch
- `--polygon-type <TYPE>`：多边形类型（仅 LowPoly）：triangle / quadrilateral
- `--result-format <FMT>`：输出格式：STL / USDZ / FBX（默认 obj+glb）
- `--provider <auto|tokenhub|tencent>`：后端选择，默认 auto
- `--no-poll`：仅提交任务不等待结果（返回 JobId）

**输出示例**：
```json
{
  "job_id": "job-xxxxxxxxxxxx",
  "status": "success",
  "result_files": [
    {
      "type": "glb",
      "url": "https://ai3d-xxx.cos.ap-guangzhou.myqcloud.com/xxx.glb",
      "preview_image_url": "https://ai3d-xxx.cos.ap-guangzhou.myqcloud.com/xxx.png"
    },
    {
      "type": "obj",
      "url": "https://ai3d-xxx.cos.ap-guangzhou.myqcloud.com/xxx.obj"
    }
  ]
}
```

> **注意**：生成的文件 URL 有效期为 **24 小时**，请及时保存。3D 生成通常需要 1~5 分钟。

---

### 📌 脚本二：仅提交任务 `submit_job.py`

**适用场景**：仅需提交任务获取 JobId，后续手动查询

```bash
python3 <SKILL_DIR>/scripts/submit_job.py --prompt "文本描述"
```

**可选参数**：与 `main.py` 相同（除 `--poll-interval`、`--max-poll-time`、`--no-poll` 外）

**输出示例**：
```json
{
  "job_id": "job-xxxxxxxxxxxx",
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "message": "Task submitted successfully. Use query_job.py to poll for results."
}
```

---

### 📌 脚本三：查询任务 `query_job.py`

**适用场景**：根据 JobId 查询任务状态和结果

```bash
python3 <SKILL_DIR>/scripts/query_job.py "job-xxxxxxxxxxxx" --model hy-3d-3.0
```

**可选参数**：
- `--poll-interval <N>`：轮询间隔秒数，默认 10
- `--max-poll-time <N>`：最大轮询时间秒数，默认 600（10min）
- `--no-poll`：仅查询一次，不轮询
- `--provider <auto|tokenhub|tencent>`：后端选择，默认 auto
- `--model <VERSION>`：TokenHub 查询需要与提交时一致的模型，默认 hy-3d-3.0

**输出示例**：
```json
{
  "job_id": "job-xxxxxxxxxxxx",
  "status": "success",
  "result_files": [
    {
      "type": "glb",
      "url": "https://ai3d-xxx.cos.ap-guangzhou.myqcloud.com/xxx.glb",
      "preview_image_url": "https://ai3d-xxx.cos.ap-guangzhou.myqcloud.com/xxx.png"
    }
  ]
}
```

---

### 📋 完整调用示例

```bash
# 文生3D（基础）
python3 /path/to/scripts/main.py --prompt "一只可爱的卡通猫咪"

# 图生3D
python3 /path/to/scripts/main.py --image-url "https://example.com/cat.jpg"

# 使用 3.1 版本 + PBR 材质
python3 /path/to/scripts/main.py --prompt "一个精致的茶壶" --model 3.1 --enable-pbr

# 自定义面数
python3 /path/to/scripts/main.py --prompt "一辆跑车" --face-count 300000

# LowPoly 模式
python3 /path/to/scripts/main.py --prompt "一棵树" --generate-type LowPoly --polygon-type quadrilateral

# 白模（Geometry）
python3 /path/to/scripts/main.py --prompt "一个机器人" --generate-type Geometry

# 草图生成
python3 /path/to/scripts/main.py --image-url "https://example.com/sketch.png" --generate-type Sketch --prompt "一把椅子"

# 指定输出格式为 FBX
python3 /path/to/scripts/main.py --prompt "一只恐龙" --result-format FBX

# 多视角输入
python3 /path/to/scripts/main.py --image-url "https://example.com/front.jpg" --multi-view '[{"ViewType":"back","ViewImageUrl":"https://example.com/back.jpg"},{"ViewType":"left","ViewImageUrl":"https://example.com/left.jpg"}]'

# 仅提交任务
python3 /path/to/scripts/main.py --prompt "一座城堡" --no-poll

# 查询已有任务
python3 /path/to/scripts/query_job.py "job-xxxxxxxxxxxx"

# 通过 stdin 传入 JSON 参数
echo '{"prompt":"一只猫"}' | python3 /path/to/scripts/main.py --stdin
```

### 📐 SubmitHunyuanTo3DProJob 参数说明

| 参数 | 类型 | 必选 | 说明 |
|------|------|------|------|
| Model | String | 否 | 模型版本，默认 3.0，可选 3.0/3.1。3.1 版本不支持 LowPoly |
| Prompt | String | 三选一 | 文生3D描述，中文推荐，最多 1024 字符 |
| ImageUrl | String | 三选一 | 输入图 URL，分辨率 128~5000，大小 ≤ 8MB |
| ImageBase64 | String | 三选一 | 输入图 Base64，分辨率 128~5000，大小 ≤ 6MB |
| MultiViewImages | Array | 否 | 多视角图片，视角：left/right/back/top/bottom/left_front/right_front |
| EnablePBR | Boolean | 否 | 开启 PBR 材质，默认 false |
| FaceCount | Integer | 否 | 面数，默认 500000，范围 10000~1500000 |
| GenerateType | String | 否 | Normal/LowPoly/Geometry/Sketch，默认 Normal |
| PolygonType | String | 否 | 仅 LowPoly：triangle/quadrilateral，默认 triangle |
| ResultFormat | String | 否 | STL/USDZ/FBX，默认返回 obj+glb |

### 📐 QueryHunyuanTo3DProJob 响应说明

| 字段 | 类型 | 说明 |
|------|------|------|
| Status | String | WAIT：等待中，RUN：执行中，FAIL：失败，DONE：成功 |
| ErrorCode | String | 错误码 |
| ErrorMessage | String | 错误信息 |
| ResultFile3Ds | Array of File3D | 生成的 3D 文件数组 |

**File3D 结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| Type | String | 文件格式（如 glb、obj） |
| Url | String | 文件 URL，有效期 24 小时 |
| PreviewImageUrl | String | 预览图 URL |

### ❌ Agent 须避免的行为

- 只打印脚本路径而不执行
- 向用户询问"是否要执行 3D 生成"——应直接执行
- 自动安装依赖或改写全局环境——如需腾讯云 SDK 后端，必须由用户明确选择安装环境
- 忘记读取输出结果中的 `result_files` URL 并返回给用户
- 3D 生成失败时，自行编造文件 URL
- 忘记提醒用户文件 URL 有效期为 24 小时

## API 参考

- TokenHub submit endpoint：`https://tokenhub.tencentmaas.com/v1/api/3d/submit`
- TokenHub query endpoint：`https://tokenhub.tencentmaas.com/v1/api/3d/query`
- TokenHub 鉴权：`Authorization: Bearer <HY3D_OPENAI_API_KEY>`
- TokenHub 模型名：`hy-3d-3.0` / `hy-3d-3.1`
- 腾讯云 SDK 模块：`tencentcloud.ai3d.v20250513`
- 腾讯云 SDK 提交任务：`SubmitHunyuanTo3DProJob`
- 腾讯云 SDK 查询任务：`QueryHunyuanTo3DProJob`
- 腾讯云 SDK endpoint：`ai3d.tencentcloudapi.com`

## 核心脚本

- `scripts/main.py` — 一站式生成，提交任务 + 自动轮询等待结果
- `scripts/submit_job.py` — 仅提交任务，返回 JobId
- `scripts/query_job.py` — 根据 JobId 查询/轮询任务状态和结果

## 依赖

- Python 3.7+
- TokenHub 后端无需第三方 Python 依赖
- `tencentcloud-sdk-python`（仅 `--provider tencent` 需要，需包含 ai3d 模块）

安装腾讯云 SDK 依赖（可选）：
```bash
pip install tencentcloud-sdk-python
```
