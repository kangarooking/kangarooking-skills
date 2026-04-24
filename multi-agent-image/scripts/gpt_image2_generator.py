#!/usr/bin/env python3
"""
GPT-Image-2 图片生成器 (apimart.ai)
支持异步任务提交和轮询查询
"""

import os
import json
import time
import requests
from datetime import datetime
from pathlib import Path

API_BASE = "https://api.apimart.ai/v1"

def require_api_key(api_key: str = None) -> str:
    """Return the apimart/OpenAI-compatible API key or fail with a clear message."""
    resolved = api_key or os.environ.get("OPENAI_API_KEY")
    if not resolved:
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Set your apimart.ai GPT-Image-2 key before generating images."
        )
    return resolved

def submit_task(prompt: str, size: str = "1:1", api_key: str = None):
    """
    提交图片生成任务
    
    Args:
        prompt: 图片描述
        size: 图片比例 - "1:1", "16:9", "9:16", "4:3", "3:4", etc.
        api_key: API Key
    
    Returns:
        dict: 包含 task_id
    """
    api_key = require_api_key(api_key)
    
    url = f"{API_BASE}/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "size": size
    }
    
    print(f"   📤 提交任务...")
    print(f"   📝 Prompt: {prompt[:60]}...")
    print(f"   📐 Size: {size}")
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    
    if result.get("code") == 200:
        task_id = result["data"][0]["task_id"]
        print(f"   ✅ 任务已提交: {task_id}")
        return {"success": True, "task_id": task_id}
    else:
        error_msg = result.get("error", {}).get("message", "Unknown error")
        print(f"   ❌ 提交失败: {error_msg}")
        return {"success": False, "error": error_msg}

def query_task(task_id: str, api_key: str = None):
    """
    查询任务状态
    
    Returns:
        dict: 任务状态和结果
    """
    api_key = require_api_key(api_key)
    
    url = f"{API_BASE}/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    return response.json()

def wait_for_completion(task_id: str, api_key: str = None, 
                        initial_delay: int = 10, poll_interval: int = 5, 
                        max_wait: int = 120):
    """
    轮询等待任务完成
    
    Args:
        task_id: 任务ID
        api_key: API Key
        initial_delay: 首次查询前的等待时间（秒）
        poll_interval: 轮询间隔（秒）
        max_wait: 最大等待时间（秒）
    
    Returns:
        dict: 任务结果
    """
    print(f"\n   ⏳ 等待生成完成（首次等待 {initial_delay}s）...")
    time.sleep(initial_delay)
    
    start_time = time.time()
    attempts = 0
    
    while time.time() - start_time < max_wait:
        attempts += 1
        elapsed = int(time.time() - start_time)
        
        print(f"   🔄 第 {attempts} 次查询（已等待 {elapsed}s）...", end=" ")
        
        result = query_task(task_id, api_key)
        
        if result.get("code") != 200:
            error_msg = result.get("error", {}).get("message", "Query failed")
            print(f"❌ 查询错误: {error_msg}")
            return {"success": False, "error": error_msg}
        
        task_data = result["data"]
        status = task_data.get("status")
        progress = task_data.get("progress", 0)
        
        if status == "completed":
            print(f"✅ 完成!")
            return {"success": True, "data": task_data}
        elif status == "failed":
            error_msg = task_data.get("error", {}).get("message", "Task failed")
            print(f"❌ 失败: {error_msg}")
            return {"success": False, "error": error_msg}
        elif status in ["pending", "processing"]:
            print(f"⏳ {status} ({progress}%)")
            time.sleep(poll_interval)
        else:
            print(f"❓ 未知状态: {status}")
            time.sleep(poll_interval)
    
    print(f"\n   ⏰ 超时（超过 {max_wait}s）")
    return {"success": False, "error": "Timeout"}

def download_image(image_url: str, save_path: str):
    """下载图片到本地"""
    print(f"   📥 下载图片...")
    
    response = requests.get(image_url, timeout=60)
    response.raise_for_status()
    
    with open(save_path, 'wb') as f:
        f.write(response.content)
    
    file_size = os.path.getsize(save_path) / 1024
    print(f"   ✅ 已保存: {save_path} ({file_size:.1f} KB)")
    
    return save_path

def generate_image(prompt: str, size: str = "1:1", save_dir: str = None, 
                   api_key: str = None):
    """
    完整的图片生成流程（提交 + 轮询 + 下载）
    
    Returns:
        dict: 完整的生成结果
    """
    if save_dir is None:
        save_dir = os.path.expanduser("~/.hermes/agents/multi-agent-image/output")

    os.makedirs(save_dir, exist_ok=True)
    api_key = require_api_key(api_key)

    # 1. 提交任务
    submit_result = submit_task(prompt, size, api_key)
    if not submit_result["success"]:
        return {"status": "failed", "error": submit_result.get("error")}
    
    task_id = submit_result["task_id"]
    
    # 2. 等待完成
    wait_result = wait_for_completion(task_id, api_key)
    if not wait_result["success"]:
        return {"status": "failed", "error": wait_result.get("error")}
    
    task_data = wait_result["data"]
    
    # 3. 提取图片 URL
    images = task_data.get("result", {}).get("images", [])
    if not images or not images[0].get("url"):
        return {"status": "failed", "error": "No image URL in result"}
    
    image_url = images[0]["url"][0]
    expires_at = images[0].get("expires_at")
    
    # 4. 下载图片
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() else "_" for c in prompt[:20])
    filename = f"{timestamp}_{safe_name}.png"
    filepath = os.path.join(save_dir, filename)
    
    download_image(image_url, filepath)
    
    return {
        "status": "success",
        "filepath": filepath,
        "filename": filename,
        "image_url": image_url,
        "task_id": task_id,
        "generation_info": {
            "model": "gpt-image-2",
            "prompt": prompt,
            "size": size,
            "actual_time": task_data.get("actual_time"),
            "estimated_time": task_data.get("estimated_time"),
            "created": task_data.get("created"),
            "completed": task_data.get("completed"),
            "expires_at": expires_at
        }
    }

def main():
    """命令行入口"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python gpt_image2_generator.py 'prompt' [size]")
        print("Example: python gpt_image2_generator.py 'a cyberpunk cat' 16:9")
        sys.exit(1)
    
    prompt = sys.argv[1]
    size = sys.argv[2] if len(sys.argv) > 2 else "1:1"
    
    result = generate_image(prompt, size)
    print("\n" + "="*50)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
