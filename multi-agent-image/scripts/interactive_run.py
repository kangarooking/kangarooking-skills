#!/usr/bin/env python3
"""
🎛️ 交互式生成入口 (Interactive Run)
======================================
两阶段工作流：

阶段1: 用户提需求 → 系统查案例库 → 展示给用户 → 询问选择
阶段2: 用户回复选择 → 系统执行生成 → 交付图片

使用方式（在 Hermes 对话中）：

    # 阶段1: 用户说"帮我做张海报"
    from interactive_run import prepare
    text = prepare("帮我做张海报", task="poster")
    # Hermes 展示 text 给用户，等待回复

    # 阶段2: 用户回复"1"或"n"
    from interactive_run import execute
    result = execute("帮我做张海报", user_choice="1", task="poster")
"""

import os
import sys
import re
from pathlib import Path

AGENCY_DIR = Path.home() / ".hermes/agents/multi-agent-image"
sys.path.insert(0, str(AGENCY_DIR))

from case_selector import get_selection_text, parse_user_choice
from orchestrator_v2 import run

def prepare(user_input: str, task: str = None) -> str:
    """
    阶段1: 准备阶段
    查询案例库 + 返回展示文本

    Args:
        user_input: 用户原始需求
        task: 可选的任务类型过滤

    Returns:
        供 Hermes 展示给用户的文本
    """
    # 先简单分析需求，推荐可能的方向
    lines = []
    lines.append(f"📝 收到需求: {user_input}")
    lines.append("")

    # 获取案例库选择文本
    case_text = get_selection_text(task=task, brief=user_input)

    if "暂无案例" in case_text:
        lines.append("📚 案例库暂无相关案例，将直接生成新图片。")
        lines.append("")
        lines.append("确认生成请回复: **y**")
    else:
        lines.append(case_text)

    return "\n".join(lines)

def execute(user_input: str, user_choice: str, task: str = None,
            use_reference: bool = True) -> dict:
    """
    阶段2: 执行阶段
    根据用户选择执行生成

    Args:
        user_input: 用户原始需求
        user_choice: 用户回复（"1", "n", "y", "case_001" 等）
        task: 任务类型
        use_reference: 是否使用案例参考

    Returns:
        生成结果
    """
    choice = user_choice.strip().lower()

    # 解析用户选择
    if choice in ["y", "yes", "是", "确认", "生成", "直接生成"]:
        # 用户确认，全新生成
        return run(user_input, use_reference=False)

    elif choice in ["n", "no", "否", "不", "不用", "不参考"]:
        # 用户明确不参考
        return run(user_input, use_reference=False)

    else:
        # 尝试解析为案例选择
        action, result = parse_user_choice(user_choice, task)

        if action == "generate" and result:
            # 用户选择了案例，执行参考生成
            match = re.search(r"(case_\d+)", result)
            if match:
                return run(user_input, use_reference=True, case_id=match.group(1))
            return run(user_input, use_reference=True)
        else:
            # 其他情况，默认全新生成
            return run(user_input, use_reference=False)

# 快捷方式
def interactive(user_input: str, task: str = None) -> str:
    """快速获取交互文本"""
    return prepare(user_input, task)

if __name__ == "__main__":
    # 测试阶段1
    print(prepare("帮我做张AI训练营海报", task="poster"))
