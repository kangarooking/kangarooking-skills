#!/usr/bin/env python3
"""
📦 批量图片生成器 v2 (多Agent版)
=================================
每张图都走完整的 5-Agent 工作流！

支持三种批量模式：
1. 同需求多风格 (A/B 测试)
2. 同需求多比例 (多尺寸适配)
3. 多需求批量 (内容矩阵)

使用方式:
    from batch_generator_v2 import BatchGeneratorV2
    
    bg = BatchGeneratorV2()
    
    # 模式1: 同需求多风格
    bg.batch_styles("AI训练营海报", task="poster")
    
    # 模式2: 同需求多比例
    bg.batch_aspects("AI训练营海报", task="poster")
    
    # 模式3: 多需求批量
    bg.batch_briefs(["海报A", "海报B", "海报C"], task="poster")
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict

AGENCY_DIR = Path.home() / ".hermes/agents/multi-agent-image"
sys.path.insert(0, str(AGENCY_DIR))

from orchestrator_v2 import run

class BatchGeneratorV2:
    """批量图片生成器（多Agent版）"""

    def __init__(self):
        self.results = []
        self.start_time = None

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [批量生成] {msg}")

    def batch_styles(self, brief: str, task: str = "poster", aspect: str = "1:1",
                     quality: str = "final", use_reference: bool = True) -> List[dict]:
        """
        模式1: 同需求多风格（A/B 测试）
        同一个 brief，让 Agent 生成保守/平衡/大胆三个版本
        """
        directions = ["conservative", "balanced", "bold"]
        self.log(f"启动多风格批量生成（多Agent）: {brief[:30]}...")
        self.log(f"将生成 {len(directions)} 个版本")

        self.results = []
        self.start_time = time.time()

        for i, direction in enumerate(directions):
            print(f"\n{'='*70}")
            print(f"🎨 批量 [{i+1}/{len(directions)}] 风格: {direction}")
            print(f"{'='*70}")

            # 走完整多Agent工作流，但强制指定 direction
            result = run(
                user_input=brief,
                use_reference=use_reference,
                task=task,
                direction=direction,
                aspect=aspect,
                quality=quality
            )
            result["batch_mode"] = "style"
            result["batch_param"] = direction
            result["batch_index"] = i
            self.results.append(result)

        self._print_summary()
        return self.results

    def batch_aspects(self, brief: str, task: str = "poster", direction: str = "balanced",
                      aspects: List[str] = None, quality: str = "final",
                      use_reference: bool = True) -> List[dict]:
        """
        模式2: 同需求多比例（多尺寸适配）
        同一个 brief，生成多个比例
        """
        if aspects is None:
            aspects = ["1:1", "16:9", "9:16"]

        self.log(f"启动多比例批量生成（多Agent）: {brief[:30]}...")
        self.log(f"将生成 {len(aspects)} 个比例")

        self.results = []
        self.start_time = time.time()

        for i, aspect in enumerate(aspects):
            print(f"\n{'='*70}")
            print(f"📐 批量 [{i+1}/{len(aspects)}] 比例: {aspect}")
            print(f"{'='*70}")

            result = run(
                user_input=brief,
                use_reference=use_reference,
                task=task,
                direction=direction,
                aspect=aspect,
                quality=quality
            )
            result["batch_mode"] = "aspect"
            result["batch_param"] = aspect
            result["batch_index"] = i
            self.results.append(result)

        self._print_summary()
        return self.results

    def batch_briefs(self, briefs: List[str], task: str = "poster", direction: str = "balanced",
                     aspect: str = "1:1", quality: str = "final",
                     use_reference: bool = True) -> List[dict]:
        """
        模式3: 多需求批量（内容矩阵）
        多个不同的 brief，每张都走完整 Agent 工作流
        """
        self.log(f"启动多需求批量生成（多Agent）: {len(briefs)} 张")
        self.results = []
        self.start_time = time.time()

        for i, brief in enumerate(briefs):
            print(f"\n{'='*70}")
            print(f"🎨 批量 [{i+1}/{len(briefs)}] {brief[:40]}...")
            print(f"{'='*70}")

            # 走完整多Agent工作流（让Agent自己判断参数）
            result = run(
                user_input=brief,
                use_reference=use_reference
            )
            result["batch_mode"] = "brief"
            result["batch_param"] = brief[:30]
            result["batch_index"] = i
            self.results.append(result)

        self._print_summary()
        return self.results

    def _print_summary(self):
        """打印批量生成摘要"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        total = len(self.results)
        success = sum(1 for r in self.results if r.get("success"))
        failed = total - success

        print("\n" + "=" * 70)
        print("📦 批量生成完成!（多Agent版）")
        print("=" * 70)
        print(f"\n📊 统计:")
        print(f"   总计: {total} 张")
        print(f"   ✅ 成功: {success} 张")
        print(f"   ❌ 失败: {failed} 张")
        print(f"   ⏱️  总耗时: {elapsed:.1f} 秒")
        print(f"   ⚡ 平均: {elapsed/max(total,1):.1f} 秒/张")

        print(f"\n📁 成功文件:")
        for r in self.results:
            if r.get("success"):
                mode = r.get("batch_mode", "")
                param = r.get("batch_param", "")
                filepath = r.get("filepath", "")
                score = r.get("score", 0)
                if filepath:
                    print(f"   ✅ [{mode}/{param}] {Path(filepath).name} ⭐{score}")
            else:
                print(f"   ❌ [{r.get('batch_index', '?')}] {r.get('error', 'Unknown')}")

        # 案例库统计
        from case_library import list_cases
        total_cases = len(list_cases())
        print(f"\n📚 案例库: 共 {total_cases} 个案例")
        print()

# 快捷函数
def batch_styles(brief: str, **kwargs):
    """同需求多风格（多Agent）"""
    return BatchGeneratorV2().batch_styles(brief, **kwargs)

def batch_aspects(brief: str, **kwargs):
    """同需求多比例（多Agent）"""
    return BatchGeneratorV2().batch_aspects(brief, **kwargs)

def batch_briefs(briefs: List[str], **kwargs):
    """多需求批量（多Agent）"""
    return BatchGeneratorV2().batch_briefs(briefs, **kwargs)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法:")
        print('  python batch_generator_v2.py styles "AI训练营海报"')
        print('  python batch_generator_v2.py aspects "AI训练营海报"')
        print('  python batch_generator_v2.py briefs "海报A" "海报B" "海报C"')
        sys.exit(1)

    mode = sys.argv[1]
    brief = sys.argv[2] if len(sys.argv) > 2 else "测试海报"

    bg = BatchGeneratorV2()
    if mode == "styles":
        bg.batch_styles(brief)
    elif mode == "aspects":
        bg.batch_aspects(brief)
    elif mode == "briefs":
        bg.batch_briefs(sys.argv[2:])
