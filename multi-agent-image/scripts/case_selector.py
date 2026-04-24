#!/usr/bin/env python3
"""
🎛️ 案例选择器 (Case Selector)
=============================
用于 Hermes 对话系统的案例库交互工具

功能：
1. 查询案例库，生成格式化的选择列表
2. 解析用户的选择（编号、关键词、或不选）
3. 返回参考图路径或 None

使用方式（在 Hermes 对话中）：
    Step 1: 调用 get_selection_text(task) 获取展示文本
    Step 2: Hermes AI 展示文本，询问用户
    Step 3: 用户回复选择
    Step 4: 调用 parse_user_choice(user_reply, task) 获取图片路径
"""

import os
import sys
from pathlib import Path

AGENCY_DIR = Path.home() / ".hermes/agents/multi-agent-image"
sys.path.insert(0, str(AGENCY_DIR))

from case_library import list_cases, search_cases, get_case_image_path

def get_selection_text(task: str = None, brief: str = "") -> str:
    """
    生成供 Hermes 展示的案例选择文本

    Args:
        task: 任务类型 (poster/product/ppt/infographic/teaching)
        brief: 用户原始需求（用于智能推荐）

    Returns:
        格式化的选择文本，直接展示给用户
    """
    cases = list_cases(task)

    if not cases:
        return "📚 案例库暂无相关案例，将直接生成新图片。"

    lines = []
    lines.append("📚 案例库")
    lines.append("=" * 50)
    lines.append(f"找到 {len(cases)} 个{'相关' if task else ''}案例:\n")

    # 按评分排序
    sorted_cases = sorted(cases, key=lambda x: x.get("rating", 0), reverse=True)

    for i, case in enumerate(sorted_cases, 1):
        case_id = case.get("case_id", f"case_{i:03d}")
        brief_text = case.get("brief", "无标题")[:35]
        task_type = case.get("task", "unknown")
        rating = case.get("rating", 0)
        tags = ", ".join(case.get("tags", [])[:3])
        stars = "⭐" * int(rating) if rating else ""

        # 标记推荐（评分最高）
        recommend = " 👈 推荐" if i == 1 else ""

        lines.append(f"  [{i}] {case_id} [{task_type}]")
        lines.append(f"      {brief_text} {stars}{recommend}")
        if tags:
            lines.append(f"      🏷️  {tags}")
        lines.append("")

    # 智能推荐说明
    if brief:
        lines.append(f"💡 根据你的需求「{brief[:20]}...」，推荐选择 [{1}] 号案例作为风格参考。")
        lines.append("")

    lines.append("选项:")
    lines.append("  [1-N] 输入编号，使用该案例风格参考")
    lines.append("  [s]   搜索案例（输入关键词）")
    lines.append("  [n]   不参考案例，全新生成")
    lines.append("")
    lines.append("请回复你的选择:")

    return "\n".join(lines)

def parse_user_choice(user_reply: str, task: str = None) -> tuple:
    """
    解析用户的选择回复

    Args:
        user_reply: 用户的回复文本（如 "1"、"n"、"搜索橙色"）
        task: 任务类型

    Returns:
        (action, result)
        - action: "generate" | "search" | "skip"
        - result: 图片路径 或 搜索关键词 或 None
    """
    reply = user_reply.strip().lower()

    # 不选
    if reply in ["n", "no", "否", "不", "不用", "不需要", "直接生成", "全新"]:
        return "skip", None

    # 搜索
    if reply == "s" or "搜索" in reply:
        keyword = reply.replace("搜索", "").replace("s", "").strip()
        if not keyword:
            return "search", ""  # 需要进一步询问关键词
        results = search_cases(keyword, task)
        if results:
            return "generate", results[0].get("image_path")
        return "skip", None

    # 按编号选择
    cases = list_cases(task)
    sorted_cases = sorted(cases, key=lambda x: x.get("rating", 0), reverse=True)

    try:
        idx = int(reply) - 1
        if 0 <= idx < len(sorted_cases):
            selected = sorted_cases[idx]
            return "generate", selected.get("image_path")
    except ValueError:
        pass

    # 模糊匹配（用户可能直接说了案例编号）
    if "case_" in reply:
        case_id = [w for w in reply.split() if w.startswith("case_")][0]
        path = get_case_image_path(case_id, task)
        if path:
            return "generate", path

    # 默认不选
    return "skip", None

def get_case_preview(case_id: str, task: str = None) -> str:
    """
    获取案例预览信息（用于展示给用户）
    """
    path = get_case_image_path(case_id, task)
    if not path:
        return None

    cases = list_cases(task)
    for case in cases:
        if case.get("case_id") == case_id:
            return {
                "image_path": path,
                "brief": case.get("brief", ""),
                "rating": case.get("rating", 0),
                "tags": case.get("tags", []),
            }
    return {"image_path": path, "brief": "", "rating": 0, "tags": []}

# 测试
if __name__ == "__main__":
    print(get_selection_text("poster", "AI训练营海报"))
