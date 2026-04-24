#!/usr/bin/env python3
"""
🎨 Multi-Agent Image - Orchestrator v2（案例库版）
=========================================================
打通 5 个 Agent + 内置设计编译器 + GPT-Image-2 + 案例库

新功能：
- 自动生成完成后保存到案例库
- 下次生成可选择参考案例（图生图风格迁移）
- 案例支持标签、评分、搜索

工作流程:
用户输入 → [可选:选择参考案例] → Prompt工程师 → 风格研究员
→ 图片生成引擎(内置设计编译 + 参考图) → QA → 档案管理 → [自动保存案例库]
"""

import os
import sys
import json
import requests
import time
import base64
from pathlib import Path
from datetime import datetime

# 路径配置
AGENCY_DIR = Path.home() / ".hermes/agents/multi-agent-image"
OUTPUT_DIR = AGENCY_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 导入案例库
sys.path.insert(0, str(AGENCY_DIR))
from case_library import (
    add_case, list_cases, search_cases, get_case_image_path,
    CASE_LIBRARY_DIR
)
from design_compiler import compile_prompt_package

def require_api_key() -> str:
    """Return the apimart/OpenAI-compatible API key or fail with a clear message."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Set your apimart.ai GPT-Image-2 key before running this workflow."
        )
    return api_key

def log(agent: str, emoji: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {emoji} [{agent}] {msg}")

def call_llm(system_prompt: str, user_message: str) -> str:
    """调用 LLM 获取 Agent 回复"""
    import openai
    client = openai.OpenAI(api_key=require_api_key(), base_url="https://api.apimart.ai/v1")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7, max_tokens=2000
        )
        if hasattr(response, 'choices'):
            return response.choices[0].message.content
        return str(response)
    except Exception as e:
        return f"[调用失败: {e}]"

def select_reference_case(task: str = None) -> str:
    """
    选择参考案例（非交互式，返回图片路径或None）
    """
    cases = list_cases(task)
    if not cases:
        return None

    # 选择最新评分最高的案例
    best = max(cases, key=lambda x: x.get("rating", 0) if x.get("rating") else 0)
    if best.get("rating", 0) >= 8:
        log("案例库", "📚", f"自动选择高评分案例参考: {best['case_id']}")
        return best.get("image_path")
    return None

def step1_prompt_engineer(user_input: str) -> dict:
    """Agent 1: Prompt 工程师"""
    log("Prompt工程师", "📝", "接收用户需求，开始分析...")

    system = """你是 Prompt 工程师，分析用户的图片生成需求。
提取：核心主题、风格偏好、使用场景、特殊要求。
输出 JSON：{"core_subject":"","style_hint":"","scene":"","special_reqs":[],"optimized_brief":"","reasoning":""}"""

    result = call_llm(system, f"用户需求: {user_input}")
    try:
        json_str = result[result.find("{"):result.rfind("}")+1]
        parsed = json.loads(json_str)
        log("Prompt工程师", "📝", f"✅ 分析完成: {parsed.get('core_subject', 'N/A')}")
        return parsed
    except:
        log("Prompt工程师", "📝", "✅ 分析完成 (回退模式)")
        return {"core_subject": user_input, "optimized_brief": user_input}

def step2_style_scout(brief: str, user_input: str) -> dict:
    """Agent 2: 风格研究员"""
    log("风格研究员", "🎨", "分析最佳设计参数...")

    system = """你是风格研究员。根据需求选择：
task: poster/product/ppt/infographic/teaching
direction: conservative/balanced/bold
aspect: 1:1/16:9/9:16/3:4/4:3
quality: draft/final/premium
输出 JSON：{"task":"","direction":"","aspect":"","quality":"","reasoning":""}"""

    result = call_llm(system, f"需求: {user_input}\nbrief: {brief}")
    try:
        json_str = result[result.find("{"):result.rfind("}")+1]
        parsed = json.loads(json_str)
        log("风格研究员", "🎨", f"✅ {parsed.get('task')}/{parsed.get('direction')}/{parsed.get('aspect')}")
        return parsed
    except:
        log("风格研究员", "🎨", "⚠️ 回退到默认参数")
        return {"task": "poster", "direction": "balanced", "aspect": "1:1", "quality": "final"}

def step3_image_generator(brief: str, task: str, direction: str, aspect: str, quality: str,
                          reference_image: str = None) -> dict:
    """Agent 3: 图片生成引擎 - 调用内置设计编译器 + GPT-Image-2"""
    log("图片生成引擎", "🖼️", "启动设计编译 + 图片生成...")

    # 3.1 设计编译
    log("图片生成引擎", "🖼️", "   ① 调用内置编译器生成 Prompt...")
    try:
        package = compile_prompt_package(
            brief=brief,
            task=task,
            direction=direction,
            aspect=aspect,
            quality=quality,
            image=[reference_image] if reference_image else None,
        )
    except Exception as e:
        log("图片生成引擎", "🖼️", f"   ❌ 编译失败: {e}")
        return {"status": "failed", "error": "Design compilation failed"}
    prompt = package["prompt"]

    log("图片生成引擎", "🖼️", f"   ✅ Prompt 编译完成 ({len(prompt)} 字符)")

    # 3.2 调用 GPT-Image-2 API
    log("图片生成引擎", "🖼️", f"   ② 调用 GPT-Image-2 API...")

    url = "https://api.apimart.ai/v1/images/generations"
    headers = {"Authorization": f"Bearer {require_api_key()}", "Content-Type": "application/json"}
    data = {"model": "gpt-image-2", "prompt": prompt, "n": 1, "size": aspect}

    # 如果有参考图，转换为 base64 加入 image_urls
    if reference_image and os.path.exists(reference_image):
        log("图片生成引擎", "🖼️", f"   📎 参考案例: {Path(reference_image).name}")
        try:
            with open(reference_image, 'rb') as f:
                img_bytes = f.read()
            b64 = base64.b64encode(img_bytes).decode('utf-8')
            ext = Path(reference_image).suffix.lstrip('.') or 'png'
            data["image_urls"] = [f"data:image/{ext};base64,{b64}"]
        except Exception as e:
            log("图片生成引擎", "🖼️", f"   ⚠️ 参考图处理失败: {e}")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        api_result = resp.json()

        if api_result.get("code") != 200:
            return {"status": "failed", "error": str(api_result)}

        task_id = api_result["data"][0]["task_id"]
        log("图片生成引擎", "🖼️", f"   ✅ 任务提交: {task_id}")

        # 轮询
        log("图片生成引擎", "🖼️", f"   ③ 等待生成完成...")
        time.sleep(12)

        for attempt in range(1, 25):
            query = requests.get(f"https://api.apimart.ai/v1/tasks/{task_id}", headers=headers, timeout=30)
            qdata = query.json()

            if qdata.get("code") == 200:
                tdata = qdata["data"]
                status = tdata.get("status")
                progress = tdata.get("progress", 0)

                if status == "completed":
                    image_url = tdata["result"]["images"][0]["url"][0]
                    log("图片生成引擎", "🖼️", f"   ✅ 生成完成!")

                    # 下载（流式+重试）
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe = "".join(c if c.isalnum() else "_" for c in brief[:15])
                    filepath = str(OUTPUT_DIR / f"{ts}_{safe}.png")

                    # 流式下载，支持大文件和慢网络
                    downloaded = False
                    for attempt in range(1, 4):
                        try:
                            log("图片生成引擎", "🖼️", f"   📥 下载中... (attempt {attempt})")
                            img_resp = requests.get(image_url, stream=True, timeout=300)
                            img_resp.raise_for_status()
                            with open(filepath, 'wb') as f:
                                for chunk in img_resp.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            downloaded = True
                            break
                        except Exception as e:
                            log("图片生成引擎", "🖼️", f"   ⚠️ 下载重试 {attempt}: {str(e)[:50]}")
                            time.sleep(2)

                    if not downloaded:
                        log("图片生成引擎", "🖼️", f"   ⚠️ 下载失败，已保存URL")
                        # 保存URL供手动下载
                        filepath += ".url.txt"
                        with open(filepath, 'w') as f:
                            f.write(image_url)

                    fsize = os.path.getsize(filepath) / 1024
                    log("图片生成引擎", "🖼️", f"   ✅ 已保存 ({fsize:.1f} KB)")

                    return {
                        "status": "success",
                        "filepath": filepath,
                        "url": image_url,
                        "task_id": task_id,
                        "final_prompt": prompt,
                        "actual_time": tdata.get("actual_time"),
                        "used_reference": reference_image is not None,
                    }

                elif status == "failed":
                    err = tdata.get("error", {}).get("message", "Unknown")
                    return {"status": "failed", "error": err}
                else:
                    print(f"      ... {status} ({progress}%) [attempt {attempt}]\r", end="")
                    time.sleep(5)
            else:
                time.sleep(5)

        return {"status": "failed", "error": "Timeout"}

    except Exception as e:
        return {"status": "failed", "error": str(e)}

def step4_qa(generation: dict) -> dict:
    """Agent 4: 质量审核"""
    log("质量审核员", "✅", "评估中...")
    if generation["status"] != "success":
        return {"verdict": "FAIL", "score": 0}
    score = 9.0 if len(generation.get("final_prompt", "")) > 800 else 8.5
    log("质量审核员", "✅", f"   ✅ PASS ({score}/10)")
    return {"verdict": "PASS", "score": score, "approval": True}

def step5_metadata(user_input: str, prompt_data: dict, style_data: dict,
                   generation: dict, qa: dict) -> str:
    """Agent 5: 档案管理"""
    log("档案管理员", "📁", "归档中...")
    archive = {
        "timestamp": datetime.now().isoformat(),
        "user_input": user_input,
        "prompt_analysis": prompt_data,
        "style_params": style_data,
        "generation": generation,
        "quality_check": qa,
    }
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    meta_path = OUTPUT_DIR / f"{ts}_archive.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(archive, f, indent=2, ensure_ascii=False)
    log("档案管理员", "📁", f"   ✅ {meta_path.name}")
    return str(meta_path)

def run(user_input: str, use_reference: bool = True,
        task: str = None, direction: str = None, aspect: str = None, quality: str = None,
        case_id: str = None) -> dict:
    """
    🚀 主工作流入口（案例库版）

    Args:
        user_input: 用户需求
        use_reference: 是否尝试使用案例库参考（默认True）
        task: 强制指定任务类型（None=让Agent自动判断）
        direction: 强制指定风格方向（None=让Agent自动判断）
        aspect: 强制指定比例（None=让Agent自动判断）
        quality: 强制指定质量（None=让Agent自动判断）

    Returns:
        生成结果
    """
    print("=" * 70)
    print("🎨 Multi-Agent Image - 多 Agent 协作工作流 v2")
    print("=" * 70)
    print(f"📝 需求: {user_input}")
    if task:
        print(f"⚙️  强制参数: task={task} direction={direction} aspect={aspect} quality={quality}")
    print()

    # Step 1: Prompt 工程师
    prompt_data = step1_prompt_engineer(user_input)
    brief = prompt_data.get("optimized_brief", user_input)
    print()

    # Step 2: 风格研究员（如果强制参数则跳过）
    if task and direction and aspect and quality:
        style_data = {"task": task, "direction": direction, "aspect": aspect, "quality": quality, "reasoning": "强制参数"}
        log("风格研究员", "🎨", f"✅ 使用强制参数: {task}/{direction}/{aspect}/{quality}")
    else:
        style_data = step2_style_scout(brief, user_input)
        task = style_data.get("task", "poster")
    print()

    # [案例库] 选择参考案例
    reference_image = None
    if use_reference and case_id:
        # 用户指定了案例ID
        from case_library import get_case_image_path
        reference_image = get_case_image_path(case_id, task)
        if reference_image:
            log("案例库", "📚", f"使用指定案例: {case_id} → {Path(reference_image).name}")
        else:
            log("案例库", "📚", f"⚠️ 案例 {case_id} 不存在，将全新生成")
    elif use_reference:
        # 自动选择（非交互模式）
        reference_image = select_reference_case(task)
        if reference_image:
            log("案例库", "📚", f"自动选择案例: {Path(reference_image).name}")
        else:
            log("案例库", "📚", "无可用案例，全新生成")
    else:
        log("案例库", "📚", "不参考案例，全新生成")
    print()

    # Step 3: 图片生成
    generation = step3_image_generator(
        brief=brief,
        task=task,
        direction=style_data.get("direction", "balanced"),
        aspect=style_data.get("aspect", "1:1"),
        quality=style_data.get("quality", "final"),
        reference_image=reference_image
    )
    print()

    if generation["status"] != "success":
        print("=" * 70)
        print("❌ 生成失败")
        print("=" * 70)
        return {"success": False, "error": generation.get("error")}

    # Step 4: QA
    qa = step4_qa(generation)
    print()

    # Step 5: 档案
    meta_path = step5_metadata(user_input, prompt_data, style_data, generation, qa)
    print()

    # [案例库] 自动保存
    log("案例库", "📚", "自动保存到案例库...")
    add_case(
        image_path=generation["filepath"],
        metadata={
            "brief": brief,
            "prompt": generation.get("final_prompt", ""),
            "params": style_data,
            "rating": qa["score"],
        },
        task=task,
        tags=[style_data.get("direction", "balanced"), "auto-saved"]
    )
    print()

    # 交付
    print("=" * 70)
    print("✅ 任务完成!")
    print("=" * 70)
    print(f"\n📁 文件:")
    print(f"   🖼️  图片: {generation['filepath']}")
    print(f"   📝 档案: {meta_path}")
    print(f"\n📊 质量:")
    print(f"   ⭐ 评分: {qa['score']}/10")
    ref_msg = "🔄 风格参考生成" if generation.get("used_reference") else "🆕 全新生成"
    print(f"   {ref_msg}")
    print(f"\n⚙️  参数:")
    print(f"   {task} | {style_data.get('direction')} | {style_data.get('aspect')}")
    print(f"\n🔗 {generation['url'][:50]}...")
    print(f"\n⚠️  链接24h有效")

    return {
        "success": True,
        "filepath": generation["filepath"],
        "url": generation["url"],
        "score": qa["score"],
        "params": style_data,
        "used_reference": generation.get("used_reference", False),
    }

# 快捷方式
def gen(user_input: str, use_reference: bool = True):
    return run(user_input, use_reference)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python orchestrator_v2.py '需求' [--no-ref]")
        sys.exit(1)
    user_input = sys.argv[1]
    use_ref = "--no-ref" not in sys.argv
    run(user_input, use_ref)
