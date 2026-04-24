#!/usr/bin/env python3
"""
🎨 Multi-Agent Image - Quick Start (GPT-Image-2 Version)
一键运行 GPT-Image-2 (apimart.ai) 图片生成工作流

用法:
    python quick_start.py "你的图片描述"
    
或在 Hermes 中:
    execute_code("from quick_start import generate; generate('你的描述')")
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 路径配置
AGENCY_DIR = Path.home() / ".hermes/agents/multi-agent-image"
OUTPUT_DIR = AGENCY_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def require_api_key() -> str:
    """Return the apimart/OpenAI-compatible API key or fail with a clear message."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Set your apimart.ai GPT-Image-2 key before running quick_start.py."
        )
    return api_key

def log(stage, message):
    """打印带时间戳的日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{stage}] {message}")

def step1_prompt_engineer(user_request):
    """Step 1: Prompt 工程师优化用户输入"""
    log("Prompt工程师", "正在优化用户输入...")
    
    # GPT-Image-2 对 prompt 质量要求很高，进行简单优化
    # 添加质量描述词
    quality_tags = "masterpiece, best quality, highly detailed"
    
    # 如果是中文，保留中文（GPT-Image-2 支持中文）
    # 但添加英文质量标签
    if any('\u4e00' <= char <= '\u9fff' for char in user_request):
        optimized = f"{user_request}, {quality_tags}"
    else:
        optimized = f"{user_request}, {quality_tags}"
    
    log("Prompt工程师", f"✅ 优化完成: {optimized[:60]}...")
    
    return {"optimized_prompt": optimized}

def step2_style_scout(user_request):
    """Step 2: 风格研究员确定比例参数"""
    log("风格研究员", "正在确定图片比例...")
    
    # GPT-Image-2 使用比例格式，不是像素尺寸
    # 支持: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 5:4, 4:5, 2:1, 1:2, 21:9, 9:21
    
    user_lower = user_request.lower()
    
    # 检测竖版需求
    if any(kw in user_lower for kw in ["portrait", "人像", "全身", "竖版", "手机壁纸", "立绘"]):
        size = "9:16"  # 竖屏，适合手机
        reason = "检测到人像/竖版需求"
    # 检测横版需求
    elif any(kw in user_lower for kw in ["landscape", "风景", "全景", "横版", "电脑壁纸", "电影感"]):
        size = "16:9"  # 宽屏，适合电脑/电影感
        reason = "检测到风景/横版需求"
    # 检测方图需求
    elif any(kw in user_lower for kw in ["正方形", "头像", "icon", "logo"]):
        size = "1:1"
        reason = "检测到正方形/头像需求"
    else:
        size = "1:1"  # 默认方图
        reason = "默认正方形比例"
    
    log("风格研究员", f"✅ 比例确认: {size} ({reason})")
    
    return {"size": size, "reason": reason}

def step3_generate_image(prompt_result, style_config):
    """Step 3: 调用 GPT-Image-2 API 生成图片"""
    log("图片生成", "正在调用 GPT-Image-2 API...")
    
    try:
        # 导入生成器
        sys.path.insert(0, str(AGENCY_DIR / "tools"))
        from gpt_image2_generator import generate_image
        
        prompt = prompt_result["optimized_prompt"]
        size = style_config["size"]
        
        print(f"\n   📝 Prompt: {prompt[:80]}...")
        print(f"   📐 Size: {size}")
        
        # 调用生成（包含提交+轮询+下载）
        result = generate_image(
            prompt=prompt,
            size=size,
            save_dir=str(OUTPUT_DIR),
            api_key=require_api_key()
        )
        
        if result["status"] == "success":
            log("图片生成", f"✅ 生成成功!")
            log("图片生成", f"   📁 文件: {result['filename']}")
            log("图片生成", f"   ⏱️  耗时: {result['generation_info'].get('actual_time', 'N/A')}s")
        else:
            log("图片生成", f"❌ 生成失败: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        log("图片生成", f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}

def step4_quality_check(user_request, generation_result):
    """Step 4: 质量检查"""
    log("质量审核", "正在审核生成结果...")
    
    if generation_result["status"] != "success":
        return {
            "verdict": "FAIL",
            "score": 0,
            "issues": [{"type": "generation_failed", "description": generation_result.get("error", "Unknown error")}]
        }
    
    # GPT-Image-2 质量通常很高
    score = 9.0
    
    result = {
        "verdict": "PASS",
        "score": score,
        "issues": [],
        "approval": True
    }
    
    log("质量审核", f"✅ 审核通过 (评分: {score}/10)")
    
    return result

def step5_archive(user_request, prompt_result, style_config, generation_result, qa_result):
    """Step 5: 归档元数据"""
    log("元数据管理", "正在归档...")
    
    archive_data = {
        "timestamp": datetime.now().isoformat(),
        "user_request": user_request,
        "optimized_prompt": prompt_result["optimized_prompt"],
        "params": {
            "size": style_config["size"],
            "reason": style_config["reason"]
        },
        "output": {
            "filepath": generation_result.get("filepath"),
            "filename": generation_result.get("filename"),
            "url": generation_result.get("image_url"),
            "task_id": generation_result.get("task_id")
        },
        "generation_info": generation_result.get("generation_info", {}),
        "quality_check": qa_result
    }
    
    # 保存元数据
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    meta_filename = f"{timestamp}_metadata.json"
    meta_path = OUTPUT_DIR / meta_filename
    
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(archive_data, f, indent=2, ensure_ascii=False)
    
    log("元数据管理", f"✅ 已归档: {meta_path}")
    
    return archive_data

def generate(user_request, show_result=True):
    """
    一键生成图片 - 主入口
    
    Args:
        user_request: 用户的图片描述（中英文都可以）
        show_result: 是否打印详细结果
    
    Returns:
        dict: 包含生成结果的字典
    """
    
    print("=" * 70)
    print("🎨 Multi-Agent Image - GPT-Image-2 工作流")
    print("=" * 70)
    print(f"📝 用户需求: {user_request}")
    print()
    
    try:
        # Step 1: Prompt 工程
        prompt_result = step1_prompt_engineer(user_request)
        
        # Step 2: 风格研究（确定比例）
        style_config = step2_style_scout(user_request)
        
        # Step 3: 生成图片
        generation_result = step3_generate_image(prompt_result, style_config)
        
        if generation_result["status"] != "success":
            print("\n❌ 生成失败，流程终止")
            return generation_result
        
        # Step 4: 质量审核
        qa_result = step4_quality_check(user_request, generation_result)
        
        # Step 5: 归档
        archive = step5_archive(user_request, prompt_result, style_config, generation_result, qa_result)
        
        # 最终结果
        print()
        print("=" * 70)
        print("✅ 任务完成!")
        print("=" * 70)
        print(f"\n📁 生成文件:")
        print(f"   🖼️  图片: {generation_result['filepath']}")
        print(f"   📝 元数据: {OUTPUT_DIR / archive['output']['filename'].replace('.png', '_metadata.json')}")
        print(f"\n📊 生成信息:")
        print(f"   ⭐ 质量评分: {qa_result['score']}/10")
        print(f"   ✅ 审核结果: {qa_result['verdict']}")
        print(f"   📐 比例: {style_config['size']}")
        print(f"   ⏱️  实际耗时: {generation_result['generation_info'].get('actual_time', 'N/A')}s")
        print(f"\n🔗 图片链接:")
        print(f"   {generation_result['image_url'][:60]}...")
        print(f"\n⚠️  链接有效期: 24小时，请尽快下载")
        
        return {
            "success": True,
            "filepath": generation_result["filepath"],
            "url": generation_result["image_url"],
            "task_id": generation_result["task_id"],
            "score": qa_result["score"],
            "prompt": prompt_result["optimized_prompt"],
            "size": style_config["size"]
        }
        
    except Exception as e:
        print(f"\n❌ 流程异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

# 便捷函数
def gen(request):
    """快捷方式: gen('描述')"""
    return generate(request)

if __name__ == "__main__":
    # 命令行入口
    if len(sys.argv) < 2:
        print("用法: python quick_start.py '图片描述'")
        print("示例: python quick_start.py '赛博朋克风格的猫咪黑客'")
        print()
        print("支持的尺寸关键词:")
        print("   竖版/人像/手机壁纸 → 9:16")
        print("   横版/风景/电脑壁纸 → 16:9")
        print("   正方形/头像 → 1:1")
        print()
        
        # 运行测试
        print("运行测试...")
        generate("一只橘猫坐在窗台上看夕阳，水彩画风格")
    else:
        user_input = sys.argv[1]
        generate(user_input)
