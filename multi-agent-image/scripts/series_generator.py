#!/usr/bin/env python3
"""
🎨 系列套图生成器 (Series Generator)
====================================
生成风格统一、内容不同的系列图片

核心逻辑：
1. 生成第1张（母图）→ 确定整体 visual_system
2. 提取母图的设计参数（风格、配色、构图逻辑）
3. 后续图复用母图风格 + 只改内容 brief

使用场景：
- 课程系列：海报 + Banner + 朋友圈 + 详情页
- 季节系列：春/夏/秋/冬（统一风格，不同主题）
- 活动系列：预热/倒计时/当天/回顾
- 产品系列：同款不同SKU

使用方式:
    from series_generator import SeriesGenerator
    
    sg = SeriesGenerator()
    
    # 定义系列
    series = sg.create_series(
        master_brief="AI训练营主视觉，科技蓝，专业感",
        items=[
            {"name": "主海报", "brief": "AI训练营招生主海报", "aspect": "3:4"},
            {"name": "Banner", "brief": "网站顶部Banner", "aspect": "16:9"},
            {"name": "朋友圈", "brief": "微信朋友圈方形图", "aspect": "1:1"},
            {"name": "详情页头图", "brief": "课程详情页顶部", "aspect": "16:9"},
        ],
        task="poster"
    )
"""

import os
import sys
import json
import requests
import base64
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict

AGENCY_DIR = Path.home() / ".hermes/agents/multi-agent-image"
OUTPUT_DIR = AGENCY_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(AGENCY_DIR))
from case_library import add_case
from design_compiler import compile_prompt_package

def require_api_key() -> str:
    """Return the apimart/OpenAI-compatible API key or fail with a clear message."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Set your apimart.ai GPT-Image-2 key before running series generation."
        )
    return api_key

def log(stage: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{stage}] {msg}")

class SeriesGenerator:
    """系列套图生成器"""

    def __init__(self):
        self.master_style = None  # 母图风格参数
        self.master_prompt = None  # 母图prompt模板
        self.series_results = []

    def generate_master(self, brief: str, task: str = "poster", direction: str = "balanced",
                        aspect: str = "1:1", quality: str = "final") -> dict:
        """
        生成母图，提取风格参数
        """
        log("母图生成", "🎨 生成母图，定义系列风格...")

        try:
            package = compile_prompt_package(
                brief=brief,
                task=task,
                direction=direction,
                aspect=aspect,
                quality=quality,
            )
        except Exception as e:
            log("母图生成", f"❌ 编译失败: {e}")
            return None
        compiled = package["compiled_brief"]
        prompt = package["prompt"]

        # 提取关键风格参数
        self.master_style = {
            "visual_system": compiled.get("visual_system", ""),
            "lighting": compiled.get("lighting", ""),
            "palette": compiled.get("palette", ""),
            "mood": compiled.get("mood", ""),
            "composition": compiled.get("composition", ""),
            "style_direction": compiled.get("style_direction", ""),
            "direction": direction,
            "task": task,
        }

        self.master_prompt = prompt

        log("母图生成", f"✅ 风格已定义")
        log("母图生成", f"   Visual: {self.master_style['visual_system'][:60]}...")
        log("母图生成", f"   Palette: {self.master_style['palette'][:40]}...")

        # 生成母图
        return self._call_api(prompt, aspect)

    def generate_child(self, item: dict) -> dict:
        """
        生成子图（复用母图风格 + 新内容）

        Args:
            item: {"name": "子图名称", "brief": "内容描述", "aspect": "1:1"}
        """
        name = item["name"]
        brief = item["brief"]
        aspect = item.get("aspect", "1:1")

        log(f"子图-{name}", f"🖼️ 生成: {brief[:40]}...")

        # 构建风格一致的 prompt
        # 保留母图的 visual_system + palette + lighting + mood
        # 替换 brief 内容
        style = self.master_style

        child_prompt = f"""Create a {style['task']} image. 
Brief: {brief}
Communication goal: attract and persuade the audience.

MUST maintain the SAME visual style as the series:
Visual system: {style['visual_system']}
Lighting: {style['lighting']}
Color palette: {style['palette']}
Mood: {style['mood']}
Composition: {style['composition']}
Style direction: {style['style_direction']}

Hierarchy: one clear hero idea supporting the brief.
Safe zone: reserve clean area for text if needed.
Aspect ratio: {aspect}

Maintain consistent visual language, color temperature, and rendering quality with the series.
Do not deviate from the established palette and lighting strategy."""

        log(f"子图-{name}", f"   Prompt: {child_prompt[:80]}...")

        # 生成
        result = self._call_api(child_prompt, aspect, name)
        result["series_name"] = name
        result["series_brief"] = brief
        return result

    def create_series(self, master_brief: str, items: List[dict],
                      task: str = "poster", direction: str = "balanced",
                      aspect: str = "1:1", quality: str = "final") -> List[dict]:
        """
        生成完整系列套图

        Args:
            master_brief: 母图需求（定义整体风格）
            items: 子图列表 [{"name": "", "brief": "", "aspect": ""}, ...]
            task: 任务类型
            direction: 风格方向
            aspect: 母图比例
            quality: 质量

        Returns:
            所有生成结果（母图+子图）
        """
        print("=" * 70)
        print("🎨 系列套图生成器")
        print("=" * 70)
        print(f"📝 母图需求: {master_brief}")
        print(f"📦 子图数量: {len(items)} 张")
        print(f"📋 子图列表:")
        for item in items:
            print(f"   - {item['name']}: {item['brief'][:30]} ({item.get('aspect', '1:1')})")
        print()

        self.series_results = []
        start_time = time.time()

        # Step 1: 生成母图
        log("系列", "开始生成母图...")
        master_result = self.generate_master(master_brief, task, direction, aspect, quality)

        if not master_result or not master_result.get("success"):
            log("系列", "❌ 母图生成失败，终止")
            return []

        master_result["is_master"] = True
        master_result["series_name"] = "母图"
        self.series_results.append(master_result)

        log("系列", f"✅ 母图完成: {master_result.get('filepath', 'N/A')}")
        print()

        # Step 2: 生成子图
        log("系列", f"开始生成 {len(items)} 张子图...")
        for i, item in enumerate(items):
            print(f"\n{'='*60}")
            print(f"🖼️ [{i+1}/{len(items)}] {item['name']}")
            print(f"{'='*60}")

            child_result = self.generate_child(item)
            child_result["is_master"] = False
            self.series_results.append(child_result)

            if child_result.get("success"):
                log("系列", f"✅ {item['name']} 完成")
            else:
                log("系列", f"❌ {item['name']} 失败: {child_result.get('error')}")

        # Step 3: 汇总
        elapsed = time.time() - start_time
        success_count = sum(1 for r in self.series_results if r.get("success"))

        print("\n" + "=" * 70)
        print("🎉 系列套图生成完成!")
        print("=" * 70)
        print(f"\n📊 统计:")
        print(f"   总计: {len(self.series_results)} 张（1母图 + {len(items)}子图）")
        print(f"   ✅ 成功: {success_count} 张")
        print(f"   ⏱️  总耗时: {elapsed:.1f} 秒")
        print(f"\n📁 文件列表:")
        for r in self.series_results:
            marker = "[母图]" if r.get("is_master") else "[子图]"
            name = r.get("series_name", "unknown")
            if r.get("success"):
                filepath = r.get("filepath", "N/A")
                print(f"   ✅ {marker} {name}: {Path(filepath).name}")
            else:
                print(f"   ❌ {marker} {name}: {r.get('error', 'failed')}")

        # 保存系列元数据
        series_meta = {
            "timestamp": datetime.now().isoformat(),
            "master_brief": master_brief,
            "master_style": self.master_style,
            "items": items,
            "results": [{"name": r.get("series_name"), "success": r.get("success"),
                        "filepath": r.get("filepath"), "url": r.get("url")} for r in self.series_results]
        }

        meta_path = OUTPUT_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_series_meta.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(series_meta, f, indent=2, ensure_ascii=False)

        print(f"\n📝 系列元数据: {meta_path}")
        print()

        return self.series_results

    def _call_api(self, prompt: str, aspect: str, label: str = "") -> dict:
        """调用 GPT-Image-2 API"""
        url = "https://api.apimart.ai/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {require_api_key()}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-image-2",
            "prompt": prompt,
            "n": 1,
            "size": aspect
        }

        try:
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            api_result = resp.json()

            if api_result.get("code") != 200:
                return {"status": "failed", "error": str(api_result)}

            task_id = api_result["data"][0]["task_id"]
            log("API", f"   任务提交: {task_id}")

            # 轮询
            time.sleep(12)
            for attempt in range(1, 25):
                q = requests.get(f"https://api.apimart.ai/v1/tasks/{task_id}", headers=headers, timeout=30)
                qdata = q.json()

                if qdata.get("code") == 200:
                    tdata = qdata["data"]
                    status = tdata.get("status")
                    progress = tdata.get("progress", 0)

                    if status == "completed":
                        image_url = tdata["result"]["images"][0]["url"][0]
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        safe = label or "img"
                        safe = "".join(c if c.isalnum() else "_" for c in safe[:15])
                        filepath = str(OUTPUT_DIR / f"{ts}_{safe}.png")

                        # 流式下载+重试
                        downloaded = False
                        for dl_attempt in range(1, 4):
                            try:
                                img_resp = requests.get(image_url, stream=True, timeout=300)
                                img_resp.raise_for_status()
                                with open(filepath, 'wb') as f:
                                    for chunk in img_resp.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                downloaded = True
                                break
                            except Exception as e:
                                log("API", f"   ⚠️ 下载重试 {dl_attempt}: {str(e)[:50]}")
                                time.sleep(2)

                        if not downloaded:
                            filepath += ".url.txt"
                            with open(filepath, 'w') as f:
                                f.write(image_url)
                            log("API", f"   ⚠️ 下载失败，已保存URL")

                        return {
                            "status": "success" if downloaded else "partial",
                            "filepath": filepath,
                            "url": image_url,
                            "task_id": task_id,
                            "prompt": prompt,
                        }

                    elif status == "failed":
                        return {"status": "failed", "error": "Task failed"}
                    else:
                        print(f"      ... {status} ({progress}%)\r", end="")
                        time.sleep(5)
                else:
                    time.sleep(5)

            return {"status": "failed", "error": "Timeout"}

        except Exception as e:
            return {"status": "failed", "error": str(e)}

# 快捷函数
def series(master_brief: str, items: List[dict], **kwargs):
    """快速生成系列套图"""
    return SeriesGenerator().create_series(master_brief, items, **kwargs)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 示例运行
        sg = SeriesGenerator()
        sg.create_series(
            master_brief="AI训练营系列视觉，科技蓝，专业商务感",
            items=[
                {"name": "主海报", "brief": "AI训练营招生主海报，强调实战", "aspect": "3:4"},
                {"name": "Banner", "brief": "官网Banner，展示课程优势", "aspect": "16:9"},
                {"name": "朋友圈", "brief": "朋友圈推广方形图", "aspect": "1:1"},
            ],
            task="poster",
            direction="balanced"
        )
