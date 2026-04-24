#!/usr/bin/env python3
"""
📦 Linear Batch Generator Template
====================================
Copy this file, edit the `scenes` list, and run.

Features:
- Sequential execution (no parallelization)
- Auto style-reference propagation from first image
- Resume support (skips already-generated files)
- Unbuffered stdout for background monitoring

Usage:
    python3 -u /tmp/my_batch.py

Monitoring (stdout may buffer in background):
    ls -lt ~/.hermes/agents/multi-agent-image/output/my_project/
"""

import subprocess
import os
import sys

sys.stdout.reconfigure(line_buffering=True)  # Critical for background monitoring

output_dir = "/root/.hermes/agents/multi-agent-image/output/my_project"
os.makedirs(output_dir, exist_ok=True)

style_prefix = "Your unified style description here"

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
