#!/usr/bin/env python3
"""
🚀 Multi-Agent Image — Install Script
=============================================
One-command deployment from skill directory to runtime working directory.

Usage:
    python3 ~/.hermes/skills/multi-agent-image/scripts/install.py

What it does:
1. Copies all Python scripts to ~/.hermes/agents/multi-agent-image/
2. Creates agent role directories if missing
3. Prints next steps
"""

import os
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path.home() / ".hermes/skills/multi-agent-image"
AGENCY_DIR = Path.home() / ".hermes/agents/multi-agent-image"

def install():
    print("=" * 50)
    print("Multi-Agent Image — Install")
    print("=" * 50)

    # 2. Create directories
    AGENCY_DIR.mkdir(parents=True, exist_ok=True)
    for subdir in ["prompt_engineer", "style_scout", "image_generator",
                   "qa_bot", "metadata_manager", "refiner", "tools", "output"]:
        (AGENCY_DIR / subdir).mkdir(exist_ok=True)
    print(f"✅ Working directory ready: {AGENCY_DIR}")

    # 3. Copy scripts
    src_scripts = SKILL_DIR / "scripts"
    copied = 0
    for f in src_scripts.glob("*.py"):
        if f.name == "install.py":
            continue
        dst = AGENCY_DIR / f.name
        shutil.copy2(f, dst)
        copied += 1
    print(f"✅ Copied {copied} scripts to {AGENCY_DIR}")

    # 4. Copy agent roles (optional — only if memory.json doesn't exist yet)
    src_roles = SKILL_DIR / "references" / "agents"
    role_map = {
        "prompt_engineer.md": "prompt_engineer/role.md",
        "style_scout.md": "style_scout/role.md",
        "image_generator.md": "image_generator/role.md",
        "qa_bot.md": "qa_bot/role.md",
        "metadata_manager.md": "metadata_manager/role.md",
    }
    for src_name, dst_path in role_map.items():
        src = src_roles / src_name
        dst = AGENCY_DIR / dst_path
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            print(f"✅ Copied role: {dst_path}")

    # 5. Create empty memory.json files if missing
    for agent in ["prompt_engineer", "style_scout", "image_generator", "qa_bot", "metadata_manager", "refiner"]:
        mem = AGENCY_DIR / agent / "memory.json"
        if not mem.exists():
            mem.write_text("{}")

    print("\n" + "=" * 50)
    print("🎉 Install complete!")
    print("=" * 50)
    print(f"\nNext steps:")
    print(f"  1. Set API key: export OPENAI_API_KEY=sk-...")
    print(f"  2. Test the local compiler: cd {AGENCY_DIR} && python3 design_image.py --brief 'AI训练营招生海报' --prompt-only")
    print(f"  3. Or use orchestrator: python3 -c \"from orchestrator_v2 import run; run('test')\"")
    print(f"\nRuntime output dir: {AGENCY_DIR / 'output'}")
    print(f"Case library dir:   {AGENCY_DIR / 'case_library'}")

if __name__ == "__main__":
    install()
