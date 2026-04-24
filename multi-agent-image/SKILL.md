---
name: multi-agent-image
description: Independent multi-agent image generation skill for Hermes with GPT-Image-2 (apimart.ai), case library, interactive style-reference selection, and linear batch workflows.
version: 2.2.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [image-generation, multi-agent, gpt-image-2, apimart, design-compiler, case-library, agency, creative]
    related_skills: [design-image-studio, stable-diffusion]

---

# Multi-Agent Image v2

Build an independent multi-agent image generation workflow on Hermes.

## When to Use

- You want structured, multi-agent image generation on Hermes
- You're using **GPT-Image-2 (apimart.ai)** — async API with ratio-based sizing
- You want a **case library** so future generations can reference past styles (image-to-image)
- You want to integrate a **design compiler skill** (e.g., design-image-studio) for higher-quality prompts
- You want agents to remember preferences across sessions via file-based memory

## Architecture

```
User Request
    ↓
[Round 1] Hermes shows case library → user picks reference (or skips)
    ↓
[Prompt Engineer Agent]    → understands intent, extracts key elements
    ↓
[Style Scout Agent]        → chooses task + direction + aspect ratio
    ↓
[Image Generator Agent]    → calls design-image-studio compiler → GPT-Image-2 API
    │   Step 1: Run design_image.py --prompt-only → structured prompt
    │   Step 2: [Optional] Encode reference case as base64 → image_urls
    │   Step 3: POST api.apimart.ai/v1/images/generations → task_id
    │   Step 4: Poll GET /v1/tasks/{task_id} until completed
    │   Step 5: Download image from result URL
    ↓
[QA Bot Agent]             → scores output quality
    ↓
[Metadata Manager Agent]   → archives files + metadata
    ↓
[Case Library]             → auto-saves new image as referenceable case
    ↓
Deliver to user
```

## Setup

### 1. Install design-image-studio Skill (Required)

This skill **requires** the `design-image-studio` skill for prompt compilation.

**Check if already installed:**
```bash
ls ~/.hermes/hermes-agent/skills/design-image-studio/scripts/
# Should contain: design_image.py, generate.py
```

**If not installed**, download from GitHub:
```bash
cd ~/.hermes/hermes-agent/skills
git clone --depth 1 https://github.com/kangarooking/design-image-studio.git
```

**Verify key files exist:**
```
design-image-studio/
├── scripts/
│   ├── design_image.py          ← Design compiler (generate reasoning + brief + prompt)
│   └── generate.py              ← Original generator from the upstream design-image-studio skill
├── references/
│   ├── claude-design-sys-prompt-full.txt
│   ├── design-compiler.md
│   └── poster.md
└── SKILL.md
```

**Critical:** If `scripts/` or `references/` are empty, the git clone was incomplete. Download individual files via `raw.githubusercontent.com`.

### 2. Deploy Agency Code

The skill code lives in `~/.hermes/skills/multi-agent-image/scripts/`.
Copy it to the runtime working directory:

```bash
mkdir -p ~/.hermes/agents/multi-agent-image
cp ~/.hermes/skills/multi-agent-image/scripts/*.py ~/.hermes/agents/multi-agent-image/
```

Also create the agent role directories:
```bash
mkdir -p ~/.hermes/agents/multi-agent-image/{prompt_engineer,style_scout,image_generator,qa_bot,metadata_manager,refiner}
```

### 3. Set API Key

```bash
export OPENAI_API_KEY="sk-..."
```

This key is for **apimart.ai GPT-Image-2**, not OpenAI DALL-E.

### 4. Install Python Dependencies

```bash
pip install openai requests
```

## Core Components

### Component 1: Case Library (case_library.py)

**Purpose:** Save generated images as referenceable cases. Supports tags, ratings, and search.

**Auto-created structure:**
```
~/.hermes/agents/multi-agent-image/case_library/
├── poster/
│   └── case_001_BriefDescription/
│       ├── image.png
│       └── metadata.json
```

**Key functions:**
```python
from case_library import add_case, list_cases, search_cases, get_case_image_path

# After generation, auto-save:
add_case(
    image_path="/path/to/image.png",
    metadata={"brief": "...", "prompt": "...", "params": {...}, "rating": 9},
    task="poster",
    tags=["balanced", "orange", "business"]
)

# Query:
cases = list_cases("poster")              # All poster cases
results = search_cases("橙色", "poster")  # Keyword search
path = get_case_image_path("case_001")    # Get image path by ID
```

### Component 2: Case Selector (case_selector.py)

**Purpose:** Generate interactive selection text for Hermes dialogue rounds.

**Three-round Hermes workflow:**

```python
from case_selector import get_selection_text, parse_user_choice

# Round 1: Hermes shows options
text = get_selection_text(task="poster", brief="用户输入")
print(text)
# → Formatted list with [1], [2], ..., [n], [s] search, [n] skip

# Round 2: User replies (e.g., "1", "n", "搜索蓝色")
action, result = parse_user_choice(user_reply="1", task="poster")
# action="generate", result="/path/to/case_001/image.png"
# OR action="skip", result=None
```

### Component 3: Orchestrator v2 (orchestrator_v2.py)

**Purpose:** Unified entry point. Runs all 5 agents + design compiler + case library.

**Usage:**
```python
execute_code("""
import sys
sys.path.insert(0, '/root/.hermes/agents/multi-agent-image')
from orchestrator_v2 import run, gen

# With automatic case reference (selects highest-rated matching case)
run("AI训练营招生海报，强调速度增长实战")

# Skip case reference, generate fresh
run("赛博朋克猫咪黑客", use_reference=False)

# Shorthand
gen("高端咖啡杯商品图")
""")
```

**What happens inside `run()`:**
1. Calls LLM as Prompt Engineer → extracts `optimized_brief`
2. Calls LLM as Style Scout → returns `task`, `direction`, `aspect`, `quality`
3. Selects best case from library (if `use_reference=True`)
4. Calls `design_image.py --prompt-only` → gets structured prompt (~2600 chars)
5. POST to `api.apimart.ai/v1/images/generations` with:
   - `prompt`: compiled prompt
   - `size`: aspect ratio (e.g., `3:4`)
   - `image_urls`: [base64 of reference case] (if selected)
6. Polls `GET /v1/tasks/{task_id}` every 5s
7. Downloads completed image
8. QA scoring
9. Archives metadata
10. Auto-saves to case library

### Component 4: Standalone API Tool (gpt_image2_generator.py)

For direct API calls without the full orchestrator:

```python
from gpt_image2_generator import generate_image

result = generate_image(
    prompt="a cyberpunk cat hacker, masterpiece, highly detailed",
    size="1:1",           # Ratio, not pixels
    save_dir="~/output"
)
# Returns: {"status": "success", "filepath": "...", "url": "...", "task_id": "..."}
```

## Design Compiler Integration (design-image-studio)

### What the Compiler Produces

Running `design_image.py --prompt-only` outputs three sections:

```
[design_reasoning]
├── task, direction, communication_goal, audience
├── visual_system: [base mode, direction bias, energy bias, composition bias, palette bias]
├── hierarchy_strategy: one clear hero idea
├── safe_zone_strategy: where text goes
├── lighting_strategy
├── palette_strategy
├── anti_filler_rules: every element must earn its place
└── anti_slop_rules: ban HUD overlays, gradient fog, floating debris

[compiled_brief]
├── visual_system (one-line)
├── hierarchy, composition, safe_zone, lighting, palette
├── detail_density
├── style_direction, mood
├── constraints, avoid
└── aspect

[prompt]
└── ~2600 character structured English prompt
```

### Adapting design-image-studio for apimart.ai

The skill was originally built for Volcengine Seedream. Three changes are required:

**1. Model config:**
```python
# OLD (Seedream)
QUALITY_MODEL = {
    "draft": "doubao-seedream-4-0-250828",
    "final": "doubao-seedream-5-0-lite-260128",
}

# NEW (apimart.ai)
def choose_model(quality):
    return "gpt-image-2"  # Fixed model
```

**2. Size format:**
```python
# OLD (pixels)
ASPECT_SIZES = {"1:1": {"2K": "2048x2048", "3K": "3072x3072"}}

# NEW (ratios)
SUPPORTED_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3",
                    "5:4", "4:5", "2:1", "1:2", "21:9", "9:21"]
```

**3. Run generation (call generate.py with minimal args):**
```python
# OLD (many args)
cmd = ["python3", "generate.py", "--prompt", p, "--model", m, "--size", s,
       "--response-format", "b64_json", "--output-format", "png"]

# NEW (minimal args)
cmd = ["python3", "generate.py", "--prompt", p, "--size", s]
```

### Testing the Compiler

Always test `--prompt-only` before generating:

```python
import subprocess

result = subprocess.run([
    "python3", "~/.hermes/hermes-agent/skills/design-image-studio/scripts/design_image.py",
    "--task", "poster",
    "--brief", "AI训练营招生海报，强调速度、增长、实战",
    "--direction", "balanced",
    "--aspect", "3:4",
    "--prompt-only"
], capture_output=True, text=True)

print(result.stdout)  # Inspect reasoning + brief + prompt quality
```

**Quality checkpoints:**
- `design_reasoning` has clear `communication_goal`?
- `safe_zone_strategy` exists for text placement?
- `anti_slop_rules` ban HUD, gradient fog, floating debris?
- Final `prompt` mentions hierarchy and whitespace?

## Case Library + Style Reference (Image-to-Image)

### How It Works

When `use_reference=True`, the orchestrator:

1. Queries `list_cases(task)` for matching cases
2. Selects highest-rated case (`rating >= 8`)
3. Reads the case image file
4. Encodes to base64: `data:image/png;base64,....`
5. Adds to API payload: `"image_urls": [base64_string]`
6. GPT-Image-2 uses it as style reference (not pixel-precise, but influences composition, lighting, palette)

### Interactive Selection (Hermes Dialogue)

```
[User]: 帮我做张新员工培训海报

[Hermes]:
📚 案例库
==================================================
找到 3 个相关案例:

  [1] case_001 [poster] AI训练营招生海报 ⭐9 👈 推荐
      🏷️  balanced, orange, business
  [2] case_002 [poster] AI进阶课海报 ⭐9
      🏷️  balanced, blue, tech
  [3] case_003 [poster] 新员工入职培训海报 ⭐9
      🏷️  balanced, tech, clean

选项:
  [1-N] 输入编号，使用该案例风格参考
  [s]   搜索案例
  [n]   不参考案例，全新生成

请回复你的选择:

[User]: 3

[Hermes]: ✅ 已选择 case_003，开始生成...
```

**Implementation:**
```python
# Round 1: Show options
from case_selector import get_selection_text
text = get_selection_text(task="poster", brief="新员工培训海报")
# Hermes prints text, user replies

# Round 2: Parse choice
from case_selector import parse_user_choice
action, ref_path = parse_user_choice(user_reply="3", task="poster")
# action="generate", ref_path="case_library/poster/case_003/.../image.png"

# Round 3: Generate with reference
from orchestrator_v2 import run
run("新员工培训海报", use_reference=True)
# orchestrator internally picks the best case
```

## API Reference (apimart.ai GPT-Image-2)

### Submit
```bash
POST https://api.apimart.ai/v1/images/generations
Authorization: Bearer $OPENAI_API_KEY
Content-Type: application/json

{
  "model": "gpt-image-2",
  "prompt": "...",
  "n": 1,
  "size": "3:4",
  "image_urls": ["data:image/png;base64,..."]  // Optional: style reference
}
```

**Response:**
```json
{"code": 200, "data": [{"status": "submitted", "task_id": "task_01K..."}]}
```

### Poll
```bash
GET https://api.apimart.ai/v1/tasks/{task_id}
Authorization: Bearer $OPENAI_API_KEY
```

**States:** `pending` → `processing` → `completed` | `failed`

### Download
```python
url = result["data"]["result"]["images"][0]["url"][0]
img = requests.get(url, timeout=60).content
```

**URL expiry:** `completed + 24h`

## Critical Differences from Standard DALL-E

| Feature | Standard DALL-E 3 | apimart.ai GPT-Image-2 |
|---------|-------------------|------------------------|
| Endpoint | `api.openai.com` | `api.apimart.ai` |
| Model | `dall-e-3` | `gpt-image-2` |
| Size | `1024x1024` (pixels) | `1:1`, `16:9`, etc. (ratios) |
| Quality | `standard` / `hd` | **Not supported** |
| Style | `vivid` / `natural` | **Not supported** |
| Response | Immediate URL | Async `task_id` → poll |
| Poll interval | N/A | 5s after 10s initial wait |
| Single image time | ~10s | ~30-60s |
| URL expiry | ~1h | 24h |
| Image reference | Not supported | Supported via `image_urls` |

## Agent Memory Pattern

Since `delegate_task` subagents don't persist, use **file-based memory**:

```python
import json
from pathlib import Path

AGENCY_DIR = Path.home() / ".hermes/agents/multi-agent-image"

def load_memory(agent_name):
    path = AGENCY_DIR / agent_name / "memory.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}

def save_memory(agent_name, data):
    path = AGENCY_DIR / agent_name / "memory.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
```

Each agent's context includes:
1. Its `role.md` (system prompt)
2. Its `memory.json` (accumulated experience)
3. Current workflow state
4. Instructions to return `memory_update` on completion

## Interactive Agent Chat

Users can chat with individual agents by mentioning them:

```
@PromptEngineer 帮我优化这个描述
@StyleScout 手机壁纸用什么比例？
@QABot 什么样的图算高质量？
```

Load the agent's `role.md` + `memory.json`, build a system prompt, and call the LLM.

## Batch & Series Generation

### Batch Generator (batch_generator_v2.py)

Generate multiple images in one call. Three modes:

```python
from batch_generator_v2 import batch_styles, batch_aspects, batch_briefs

# Mode 1: Same brief, multiple styles (A/B test)
batch_styles("AI训练营海报", task="poster")
# Generates: conservative + balanced + bold (3 images)

# Mode 2: Same brief, multiple aspects (multi-size)
batch_aspects("AI训练营海报", task="poster", aspects=["1:1", "16:9", "9:16"])

# Mode 3: Multiple briefs (content matrix)
batch_briefs(["海报A", "海报B", "海报C"], task="poster")
```

**Trade-off:** v2 runs the full 5-agent workflow for every image (~50s each). For faster bulk, use v1 (direct API, no agents).

### Series Generator (series_generator.py)

Generate a **style-unified set** (e.g., main poster + banner + social square) where all images share the same visual system.

**How it works:**
1. Generate a **master image** first
2. Extract `visual_system`, `palette`, `lighting`, `mood` from the design compiler output
3. Generate child images reusing the master style parameters

```python
from series_generator import SeriesGenerator

sg = SeriesGenerator()
sg.create_series(
    master_brief="AI训练营系列视觉，科技蓝，专业商务感",
    items=[
        {"name": "主海报", "brief": "AI训练营招生主海报", "aspect": "3:4"},
        {"name": "Banner", "brief": "官网Banner", "aspect": "16:9"},
        {"name": "朋友圈", "brief": "朋友圈推广方形图", "aspect": "1:1"},
    ],
    task="poster",
    direction="balanced"
)
```

**Critical implementation detail:** The `_call_api()` in series_generator.py must handle downloads robustly (see Download Timeout fix below). If the download times out, the entire series aborts even though the image was successfully generated on the server.

### Game Asset Generation Pattern

When generating a **set of game assets** (character idle + running, enemy idle + running, background), the proven workflow is:

**Step 1: Generate base assets sequentially (no reference)**
```python
# Character standing (base)
run("像素风游戏素材-主角：橙色小狐狸穿着蓝色背心，站立正面姿态，16-bit像素艺术，角色设计图，白色背景，色彩鲜艳", aspect="1:1")
# → Saved as case_008

# Enemy standing (base)
run("像素风游戏素材-敌人：红色蘑菇怪，白色斑点，愤怒表情，小短腿，16-bit像素艺术，角色设计图，白色背景", aspect="1:1")
# → Saved as case_011

# Background
run("像素风游戏素材-背景：绿色森林场景，16-bit像素艺术，横版卷轴背景", aspect="16:9")
# → Saved as case_009
```

**Step 2: Generate pose variants with case reference**
```python
# Character running — reference case_008 (standing) for style consistency
run("像素风游戏主角：橙色小狐狸穿着蓝色背心，奔跑跑步姿态，四肢迈开向前冲刺，16-bit像素艺术", 
    use_reference=True, case_id="case_008", aspect="1:1")

# Enemy running — reference case_011
run("像素风游戏敌人：红色蘑菇怪，奔跑跑步姿态，动感十足，16-bit像素艺术",
    use_reference=True, case_id="case_011", aspect="1:1")
```

**Key prompt pattern for pixel art game assets:**
- Always include: `16-bit像素艺术风格` or `8-bit像素艺术风格`
- Always include: `角色设计图，白色背景` (for sprites)
- Always include: `色彩鲜艳明亮` (for consistent palette)
- Specify pose clearly: `站立正面姿态` vs `奔跑跑步姿态，四肢迈开`
- Use `1:1` for sprites, `16:9` for backgrounds

**If series_generator fails due to download timeouts** (common with apimart.ai), fall back to the sequential `run()` approach above. It gives nearly the same style consistency because all images go through the same `design-image-studio` compiler with identical parameters.

## Interactive Two-Phase Workflow (interactive_run.py)

For Hermes dialogue integration where the AI should **ask the user** before generating:

```python
from interactive_run import prepare, execute

# Phase 1: Show case library, ask user
text = prepare("帮我做张海报", task="poster")
# Hermes prints text → user replies "1" or "n"

# Phase 2: Execute based on user choice
result = execute("帮我做张海报", user_choice="1", task="poster")
```

**Why this matters:** `execute_code()` cannot pause for user input. The two-phase pattern splits the workflow across Hermes dialogue turns.

**File location:** `~/.hermes/agents/multi-agent-image/interactive_run.py`

**Implementation:**
```python
# interactive_run.py
from case_selector import get_selection_text, parse_user_choice
from orchestrator_v2 import run

def prepare(user_input: str, task: str = None) -> str:
    """Phase 1: Returns formatted text for Hermes to show the user."""
    case_text = get_selection_text(task=task, brief=user_input)
    return f"📝 收到需求: {user_input}\n\n{case_text}"

def execute(user_input: str, user_choice: str, task: str = None) -> dict:
    """Phase 2: Parses user choice and runs generation."""
    action, result = parse_user_choice(user_choice, task)
    if action == "generate":
        return run(user_input, use_reference=True)
    return run(user_input, use_reference=False)
```

**Usage in Hermes dialogue:**
```
[User]: 帮我做张AI训练营海报

[Hermes]: (calls prepare() internally)
📚 案例库
找到 3 个相关案例:
  [1] case_001 AI训练营海报 ⭐9 👈 推荐
  [2] case_002 进阶课海报 ⭐9
  [n] 不参考案例，全新生成
请回复你的选择:

[User]: n

[Hermes]: (calls execute("帮我做张AI训练营海报", "n"))
✅ 生成完成: output/2026..._AI训练营海报.png
```

## Troubleshooting

**`NameError: name 'os' is not defined` in design_image.py:**
- The skill file may be missing `import os`. Add it to the imports.
- **Also check:** `import shlex` and `import json` — all three have been observed missing in partial clones.

**`NameError: name 'case_id' is not defined` in orchestrator_v2.py:**
- The `run()` function signature must include `case_id: str = None`:
```python
def run(user_input: str, use_reference: bool = True,
        task: str = None, direction: str = None, aspect: str = None, quality: str = None,
        case_id: str = None) -> dict:
```
- Without this, specifying `case_id="case_013"` in interactive workflows crashes.

**SSL errors (`SSLEOFError`) during polling:**
- The apimart.ai task polling endpoint occasionally drops SSL connections mid-request.
- **Fix:** Wrap the polling loop in try/except and retry the query. The task continues processing on the server even if the poll request fails.
```python
for attempt in range(1, 6):
    try:
        resp = requests.get(f"https://api.apimart.ai/v1/tasks/{task_id}",
                           headers=headers, timeout=30)
        data = resp.json()
        break
    except Exception as e:
        print(f"Poll retry {attempt}: {str(e)[:50]}")
        time.sleep(3)
```

**`Connection error`:**
- apimart.ai requires explicit base URL. Don't rely on OpenAI SDK defaults.

**`invalid size: 1024x1024`:**
- Use ratio format (`1:1`, `16:9`) not pixel dimensions.

**Skill directories empty after git clone:**
- Git clone may be interrupted in restricted environments
- Download individual files via `raw.githubusercontent.com`
- Check both `~/.hermes/skills/` and `~/.hermes/hermes-agent/skills/`

**Duplicate case entries (e.g., case_009 and case_010):**
- `add_case()` auto-increments by counting existing directories. If a previous run partially failed or was retried, duplicates may occur.
- **Fix:** Deduplicate by `brief` hash before saving, or clean up duplicates manually.
- **Quick cleanup:** `rm -rf case_library/poster/case_010` if it's an exact duplicate of case_009.

**Case library not auto-saving:**
- Ensure `OUTPUT_DIR` exists and is writable
- Check that `add_case()` is called after successful generation

**Download timeouts from apimart.ai CDN:**
- `generate.py` may fail with `TimeoutError` or `urllib.error.URLError` during image download even though generation succeeded
- The image URL is valid for 24h; re-download manually with `curl -C -` (resume) or Python chunked range requests
- Python workaround: split download into 64KB chunks with `Range` headers, 15s timeout per chunk, auto-retry on failure
- Alternative: use `wget -c` or `requests.get(url, timeout=300, stream=True)` with resume logic

**Background process output buffering:**
- When running batch generation via `python3 script.py` in background, stdout may not appear in process logs due to Python output buffering
- Fix: use `python3 -u script.py` (unbuffered) or add `sys.stdout.reconfigure(line_buffering=True)` at the top of the script

**Style reference not working:**
- Ensure base64 encoding is correct: `data:image/png;base64,{b64}`
- apimart.ai supports up to 16 reference images
- Reference influence is subtle (composition/lighting/palette), not pixel-precise

**Image download timeout (`Read timed out` / incomplete PNG):**
- **Symptom:** Generation completes (`status: completed`) but downloading the image URL fails with `HTTPSConnectionPool ... Read timed out`, or produces a truncated PNG without the `IEND` trailer.
- **Cause:** apimart.ai image URLs can be extremely slow and unreliable to transfer, especially for large files (>1MB). The connection may drop to 0 B/s mid-transfer and never recover.
- **Most robust: HTTP Range request chunking (proven in production).** After repeated failures with `stream=True + timeout=300`, the only reliable pattern for apimart.ai's extremely slow and unreliable CDN is:
  - Small chunks: **64 KB per request**
  - Short per-chunk timeout: **10-15 seconds**
  - Retry failed chunks individually
  - Verify PNG `IEND` trailer after completion

```python
import requests, os

def robust_download(url, output_path, total_size, chunk_size=64*1024, timeout=15):
    downloaded = os.path.getsize(output_path) if os.path.exists(output_path) else 0
    mode = "ab" if downloaded > 0 else "wb"
    with open(output_path, mode) as f:
        while downloaded < total_size:
            end = min(downloaded + chunk_size - 1, total_size - 1)
            headers = {"Range": f"bytes={downloaded}-{end}"}
            try:
                r = requests.get(url, headers=headers, timeout=timeout)
                if r.status_code in (200, 206):
                    f.write(r.content)
                    downloaded += len(r.content)
                else:
                    print(f"HTTP {r.status_code}, retrying...")
            except Exception as e:
                print(f"Chunk failed at {downloaded}, retrying... ({str(e)[:40]})")
    # Verify PNG integrity
    with open(output_path, "rb") as f:
        f.seek(-12, 2)
        return f.read().endswith(b"IEND\xaeB`\x82")
```
**Why this works:** A single `requests.get(url, timeout=300)` often hangs mid-transfer when speed drops to 0 KB/s. Range requests treat each 64KB chunk as an independent transaction—if one chunk hangs, only that chunk is retried, not the entire 2MB file.

**Fallback (if Range requests also fail):**
```python
def download_with_retry(image_url, filepath, max_attempts=3):
    """Download with stream + retry + fallback URL saving."""
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"📥 Downloading... (attempt {attempt})")
            resp = requests.get(image_url, stream=True, timeout=300)
            resp.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed: {str(e)[:50]}")
            time.sleep(2)

    # Fallback: save URL for manual download
    filepath += ".url.txt"
    with open(filepath, 'w') as f:
        f.write(image_url)
    print(f"⚠️ Saved URL to {filepath}")
    return False
```

- **Verification:** Always check the PNG trailer (`IEND\xaeB\x60\x82`). A missing trailer means the file is truncated and will be rejected by vision tools (`Error code: 400 — failed to decode image: invalid or unsupported image format`).
- **Fallback:** If even Range requests fail, save the URL to a `.url.txt` file so the user can download manually when the CDN is less congested.

**Monitoring progress via filesystem (stdout buffering workaround):**
When running batch generation as a background process via `terminal(background=True)`, `process(action="poll")` may show empty `output_preview` due to Python stdout buffering—even with `python3 -u`. The reliable monitoring method is filesystem polling:
```bash
# Check every 30-60s for new files
ls -lt ~/.hermes/agents/multi-agent-image/output/dracula_taobao_detail/
```
Combine with `ps aux | grep generate.py` to confirm the current image being processed.

**When to use standalone download recovery:**
If the orchestrator's built-in download still times out (e.g., due to upstream network issues), manually query and download:
```python
import requests
from pathlib import Path
from datetime import datetime

task_id = "task_01K..."  # From the failed run's output
API_KEY = os.environ["OPENAI_API_KEY"]

# Query status
resp = requests.get(f"https://api.apimart.ai/v1/tasks/{task_id}",
                    headers={"Authorization": f"Bearer {API_KEY}"})
data = resp.json()

if data.get("code") == 200 and data["data"].get("status") == "completed":
    url = data["data"]["result"]["images"][0]["url"][0]
    # Stream download with long timeout
    r = requests.get(url, stream=True, timeout=300)
    with open(f"{datetime.now():%Y%m%d_%H%M%S}_recovery.png", 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
```

## User Preferences & Workflow Rules

**Always ask before generating.** The user explicitly corrected the agent when images were generated without asking. The mandatory flow is:

```
User says: "帮我做张XX图"
    ↓
Hermes calls prepare() → shows case library → asks user to choose
    ↓
User replies: "1" / "n" / "13"
    ↓
Hermes calls execute() or run() with the user's choice
    ↓
Deliver image
```

**Never skip the asking step.** Even if the user seems impatient, show the case library options and ask. In this session, the user said: "我要的批量生成是生成系列套图" and later "你生成的在哪里" after images were generated without consultation. The two-phase `prepare() → execute()` pattern in `interactive_run.py` is the enforcement mechanism.

**When the case library has no relevant matches, explicitly say so.** If the user requests "千禧年画质小猫" and the library only contains "商务海报/像素游戏/军事人物", state clearly that no matching cases exist and recommend `n` (fresh generation). Do not force a reference to an irrelevant case.

**Linear execution for series/game assets.** When generating multiple related images (character standing → running, main poster → banner → social), the user explicitly prefers sequential/linear execution over parallel batch generation:
- `"不要并行，线性来"` — do not parallelize, process in linear order
- This preserves style consistency via image-to-image reference chaining
- Use `run()` sequentially in a loop, not `ThreadPoolExecutor`

**Aspect ratio confirmation.** The user cares about exact aspect ratios and will call out mismatches (e.g., 1:1 vs 16:9). Always confirm the ratio before running, especially for:
- Game character sprites → `1:1`
- Game backgrounds / wallpapers → `16:9`
- Social media posts → `9:16` or `1:1`
- Posters → `3:4`

## Interior Design Before/After Pattern

When generating **renovation / home staging** content (e.g., raw room → finished room), the proven workflow is:

**Step 1: Generate the raw room (毛坯房)**
```python
run("客厅毛坯房效果图：一间未装修的客厅，裸露的水泥墙面和地面，可见电线管线，空旷的空间，大窗户透进自然光，写实摄影风格", aspect="16:9")
# → Saved as case_015
```

**Step 2: Generate the renovated room with `case_id` reference**
```python
run("同一间客厅的装修后效果图：基于毛坯房原样进行温暖风格装修，铺设浅色木地板，墙面刷成米白色，摆放米白色布艺沙发和原木茶几，落地窗挂上白色纱帘，整体温馨舒适，写实渲染",
    use_reference=True, case_id="case_015", aspect="16:9")
# → Saved as case_016
```

**Why `case_id` matters here:** Without the reference, GPT-Image-2 may generate a completely different room layout (different window position, different proportions). Passing the raw room as `image_urls` locks the spatial structure—AI will preserve the same walls, window placement, and room shape while adding flooring, furniture, and decor.

**Key prompt pattern:**
- Raw room: Emphasize `裸露的水泥墙面`, `空旷的空间`, `未装修`
- Renovated room: Start with `同一间客厅的装修后效果图`, `基于毛坯房原样`
- Both use identical `aspect` (usually `16:9` for interior shots)
- Both use `direction="balanced"` and `quality="final"` for photorealism

**Follow-up variants:** Once the raw room case exists, generate other rooms (bedroom, kitchen, bathroom) in the same apartment:
```python
run("同一间公寓的卧室装修后效果图：温暖风格，浅色木地板，米白色墙面，舒适大床，落地窗，写实渲染",
    use_reference=True, case_id="case_015", aspect="16:9")
```

## Social Media Content Calendar Pattern

When generating **weekly content calendars** for platforms like Xiaohongshu (小红书), the proven pattern is:

**Format:** `9:16` vertical (Xiaohongshu standard)  
**Execution:** Strictly linear (one at a time) to maintain tonal consistency  
**Prompt structure:** `平台 + 主题 + 场景描述 + 摄影风格 + 配文空间`

```python
# Monday — Morning coffee / motivation
run("小红书风格竖版图：周一早安主题，一杯热咖啡和一本打开的书放在木质桌面上，暖色自然光从窗户照进来，温馨治愈的氛围，浅色调，生活方式摄影风格，配文空间在上方", aspect="9:16")

# Wednesday — Product / skincare review
run("小红书风格竖版图：周三护肤好物分享主题，白色大理石桌面上摆放着几瓶精致护肤品和化妆刷，旁边有一支鲜花，柔和的自然光，清新干净的色调，生活方式摄影风格，配文空间在上方", aspect="9:16")

# Friday — Weekend outing / lifestyle
run("小红书风格竖版图：周五周末出游主题，一个女生背着帆布包站在开满野花的草地上，远处是蓝天白云和绿色山丘，阳光明媚，自由轻松的氛围，胶片摄影色调，生活方式摄影风格，配文空间在上方", aspect="9:16")

# Sunday — Home organization / self-care
run("小红书风格竖版图：周日居家整理主题，一个整洁温馨的卧室角落，床上铺着白色亚麻床单，旁边有一个藤编收纳筐和一盆绿植，阳光透过窗帘洒进来，宁静舒适的氛围，日系简约风格，生活方式摄影风格，配文空间在上方", aspect="9:16")
```

**Key prompt patterns for Xiaohongshu:**
- Always include: `小红书风格竖版图`
- Always include: `生活方式摄影风格`
- Always include: `配文空间在上方` ( reserves clean area for Chinese text overlay )
- Use warm, soft lighting: `暖色自然光`, `柔和的自然光`
- Use shallow depth of field / film tones: `胶片摄影色调`, `浅色调`
- Aspect: strictly `9:16`
- Execution: linear/sequential. Never parallel—the user explicitly prefers `"线性来"` for content series to maintain consistent color temperature and lighting style.

**Case library value:** After generating the first week's set, future weeks can reference the highest-rated case (e.g., the Monday coffee shot) to maintain the same visual identity for the account.

## Retro CCD / Y2K Photography Style Pattern

When users request **千禧年画质** (millennium-era image quality) or **CCD camera style**, the proven prompt pattern is:

```python
run("中国千禧年CCD画质的小猫，低像素噪点复古色调，场景在千禧年的家里，中国老式小区房，浅色木制家具，老式沙发和电视柜，复古温馨氛围，电脑横屏壁纸", aspect="16:9")
```

**Key prompt elements:**
- `千禧年CCD画质` or `2000年代傻瓜相机` or `CCD相机风格`
- `低像素噪点复古色调`
- `四周暗角` (vignetting for retro lens feel)
- `暖黄/暖棕色调` (early digital camera color cast)
- Scene context: `中国老式小区房`, `浅色木制家具`, `老式沙发和电视柜`, `CRT电视`, `白色蕾丝沙发巾`

**Military / FPS Game Character Pattern**

For **使命召唤风格** (Call of Duty-style) character portraits:

```python
# Character 1 — Assault
run("中国特战队的类使命召唤游戏人物图：一名中国特种部队士兵，身穿迷彩战术装备，头戴夜视仪，手持突击步枪，严肃表情，写实3D渲染风格，像使命召唤游戏角色选择界面，深色背景，电影级光影", aspect="16:9")

# Character 2 — Medic (reference character 1 for style consistency)
run("中国特战队医疗兵，类使命召唤游戏人物图：一名中国特种部队医疗兵，身穿迷彩战术装备，头戴红色十字医疗臂章，背着医疗背包，手持冲锋枪，写实3D渲染风格，像使命召唤游戏角色选择界面，深色背景，电影级光影",
    use_reference=True, case_id="case_013", aspect="16:9")
```

**Key elements:**
- `写实3D渲染风格`, `像使命召唤游戏角色选择界面`
- `深色背景`, `电影级光影`
- Military gear details: `迷彩战术装备`, `夜视仪`, `突击步枪`, `医疗臂章`
- Aspect: `16:9` (character selection screen feel)
- Use `case_id` reference to ensure all characters look like they're from the same game

## Post-Processing: Text Overlay with PIL

After generating images, users often request adding text (prices, slogans, titles). **Always use `terminal` to run PIL scripts**, never `execute_code`:

```bash
# 1. Ensure Pillow is available
apt-get install -y python3-pil

# 2. Write script via write_file, then run via terminal
python3 /tmp/add_text.py
```

**Why `execute_code` fails:** The sandbox environment used by `execute_code` is isolated and may not share the system Python packages. `terminal` runs in the same shell where `python3-pil` was installed.

**Typical workflow:**
1. Generate image via `generate.py` → save to `output.png`
2. `write_file` a PIL script that loads the image, draws translucent overlay bars, renders Chinese text with WenQuanYi Zen Hei (`/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`), and saves
3. Run the script via `terminal`
4. Deliver the final image to the user

## Linear Batch Generation Script Template

For projects where you need to generate **multiple related images one at a time** (e.g., fairy tale illustrations, e-commerce detail pages, UI screen sets), use this lightweight script pattern instead of the full orchestrator.

**Why this over `batch_generator_v2.py`?**
- Simpler: no agents, direct API call
- Observable: each generation prints progress
- Resumable: if interrupted, re-run and it skips already-generated files
- Style-consistent: auto-propagates `--image` reference from the first successful image

```python
import subprocess
import os
import time
import sys

sys.stdout.reconfigure(line_buffering=True)  # Critical for background monitoring

output_dir = "/root/.hermes/agents/multi-agent-image/output/my_project"
os.makedirs(output_dir, exist_ok=True)

style_prefix = "Your unified style description here, e.g., Apple iOS native style with Liquid Glass"

scenes = [
    ("01_scene_name", "Detailed scene description for image 1..."),
    ("02_scene_name", "Detailed scene description for image 2..."),
    ("03_scene_name", "Detailed scene description for image 3..."),
]

reference_image = None

for idx, (name, scene_desc) in enumerate(scenes, 1):
    prompt = f"{style_prefix}. {scene_desc}"
    output_file = f"{name}.png"
    output_path = os.path.join(output_dir, output_file)
    
    # Resume support: skip if already exists
    if os.path.exists(output_path) and os.path.getsize(output_path) > 100000:
        print(f"[{idx}/{len(scenes)}] SKIP: {output_file} already exists")
        reference_image = reference_image or output_path
        continue
    
    print(f"\n[{idx}/{len(scenes)}] Generating: {name}")
    
    cmd = [
        "python3", "scripts/generate.py",
        "--prompt", prompt,
        "--size", "9:16",  # or 16:9, 3:4, 1:1
        "--output-dir", output_dir,
        "--output", output_file
    ]
    
    if reference_image and os.path.exists(reference_image):
        cmd.extend(["--image", reference_image])
        print("Using style reference.")
    
    result = subprocess.run(cmd, capture_output=True, text=True,
                           cwd="/root/.hermes/hermes-agent/skills/design-image-studio")
    
    if os.path.exists(output_path) and os.path.getsize(output_path) > 100000:
        size_mb = os.path.getsize(output_path) / (1024*1024)
        print(f"  OK: {output_file} ({size_mb:.2f} MB)")
        if idx == 1:
            reference_image = output_path
            print("  -> Set as style reference.")
    else:
        print(f"  FAILED: {output_file}")
        print(result.stdout[-600:] if len(result.stdout) > 600 else result.stdout)

print(f"\nDone. Saved to: {output_dir}")
```

**Execution:**
```bash
# Run in background with filesystem monitoring
python3 -u /tmp/my_batch_script.py
```

**Monitoring progress (stdout buffering workaround):**
When running as a background process, `process(action="poll")` often shows empty output due to Python buffering. Monitor via filesystem instead:
```bash
ls -lt ~/.hermes/agents/multi-agent-image/output/my_project/
```

**Resume after interruption:**
If the process is killed (e.g., user sends a new message mid-generation), the script above will **skip already-generated files** on re-run because it checks `os.path.exists(output_path)`. The only manual recovery needed is for the *current* image being generated when interrupted—check if its file is complete (valid PNG trailer), and delete it if truncated before re-running.

## UI Design Iteration Workflow

When generating **mobile app UI mockups**, the user typically expects multiple style iterations. The proven 3-pass workflow from this session:

**Pass 1 — Initial draft:** Generate v1 with a general description (e.g., "Apple iOS minimal"). Collect feedback.

**Pass 2 — Pivot to specific design system:** Research the actual design system (e.g., browse `developer.apple.com/design` to discover Liquid Glass, SF Symbols 7, new iOS 18 aesthetics). Regenerate with precise terminology from the source.

**Pass 3 — Radical style pivot:** If the user wants a completely different aesthetic (e.g., from Apple minimal → dark kawaii cartoon), regenerate the entire set with a new `style_prefix` while keeping the same `scenes` list.

**Key rule:** Always keep the same `scenes` tuple structure across passes. Only change `style_prefix` and scene descriptions. This ensures page-to-page consistency within each pass.

**UI-specific prompt patterns that work:**
- `Mobile app UI design screenshot, Apple iOS 18 native style with Liquid Glass material design, large whitespace, pure white and deep space gray palette, subtle translucent glassmorphism cards with light refraction, soft system blue accents, clean SF Pro typography, premium native iOS aesthetic, high fidelity mockup`
- `Mobile app UI design screenshot, cute kawaii cartoon style, dark night theme with deep indigo and midnight blue background, soft glowing stars and crescent moon accents, rounded bubbly shapes, hand-drawn illustration feel, dreamy cute aesthetic, warm soft glow effects, not Apple style, playful and whimsical`
- Always include: `iPhone frame` in the scene description
- Always include: aspect `9:16` for full-screen UI shots
- Logo rule: If the user says "logo要有艺术感", do NOT render the Chinese character directly as a text element. Use abstract graphic symbols (crescent moon, star orbits, glass sphere, cloud shapes) instead.

**Apple Design research tip:** When a user references `developer.apple.com/design`, quickly scan for:
- `Liquid Glass` — Apple's new glass material system (translucency + refraction)
- `SF Symbols` — system icon library
- `新功能指南` / `What's New` — latest platform design updates
- `设计资源` — official Figma/Sketch templates and color guides

Incorporate 1-2 specific terms from the page into the `style_prefix` for authenticity.

## Version History

- **v1.0.0** — Initial multi-agent agency with GPT-Image-2 support
- **v2.0.0** — Added design-image-studio integration, case library, interactive selection, image-to-image style reference
- **v2.1.0** — Added robust download retry (stream + 300s timeout + 3 retries + URL fallback), SSL poll retry, `case_id` parameter fix, standalone download recovery pattern, user-interaction rules (ask before generating, linear execution for series)
- **v2.1.1** — Added e-commerce detail page generation pattern (7-image Taobao sequence), filesystem progress monitoring workaround, PIL text overlay post-processing rules
- **v2.1.2** — Added interior design before/after pattern (raw room → renovation with spatial consistency via case_id), social media content calendar pattern (Xiaohongshu 9:16 weekly sets), retro CCD/Y2K photography style pattern, military/FPS game character pattern. Validated across 20+ live generations including pixel art game assets, interior design, and lifestyle content.
- **v2.1.3** — Added Linear Batch Generation Script Template (resumable, filesystem-monitored, auto-reference-propagation), UI Design Iteration Workflow (3-pass pivot pattern with Apple Design research), and logo abstraction rule (avoid direct Chinese character rendering when user requests artistic logo).
- **v2.2.0** — Packaged as Hermes skill. Core scripts moved to `~/.hermes/skills/multi-agent-image/scripts/`. Added `install.py` for one-command deployment to `~/.hermes/agents/multi-agent-image/`.
