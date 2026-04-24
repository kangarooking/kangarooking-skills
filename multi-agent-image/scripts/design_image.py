#!/usr/bin/env python3
"""
Standalone design compiler for multi-agent-image.

It keeps the original prompt-compilation workflow available locally while using
the repo's own GPT-Image-2 runtime instead of an external generator.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from design_compiler import compile_prompt_package
from gpt_image2_generator import generate_image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile a design-led image brief and optionally generate with GPT-Image-2."
    )
    parser.add_argument("--task", default="auto", choices=["auto", "poster", "product", "ppt", "infographic", "teaching"])
    parser.add_argument("--brief", required=True, help="User brief or request")
    parser.add_argument("--audience", default=None, help="Target audience")
    parser.add_argument("--usage", default=None, help="Where the image will be used")
    parser.add_argument("--brand", default=None, help="Brand tone or reference context")
    parser.add_argument("--style", default=None, help="Preferred visual style override")
    parser.add_argument("--mood", default=None, help="Preferred mood override")
    parser.add_argument("--goal", default=None, help="Specific communication goal override")
    parser.add_argument("--composition", default=None, help="Composition override")
    parser.add_argument("--constraints", default=None, help="Must-have constraints")
    parser.add_argument("--avoid", default=None, help="Things to avoid")
    parser.add_argument("--aspect", default=None, help="Aspect ratio such as 1:1, 3:4, 16:9")
    parser.add_argument("--direction", default="balanced", choices=["conservative", "balanced", "bold"])
    parser.add_argument("--safe-zone", default=None, help="Safe-zone strategy override")
    parser.add_argument("--lighting", default=None, help="Lighting strategy override")
    parser.add_argument("--palette", default=None, help="Palette strategy override")
    parser.add_argument("--quality", default="final", choices=["draft", "final", "premium"])
    parser.add_argument("--model-override", default=None, help="Explicit model id override")
    parser.add_argument("--image", nargs="+", default=None, help="Reference image path(s) or URL(s)")
    parser.add_argument("--output", "-o", default=None, help="Output filename")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--prompt-only", action="store_true", help="Only print design reasoning, compiled brief, and the final prompt")
    return parser.parse_args()


def print_package(package: dict) -> None:
    print("[design_reasoning]")
    print(json.dumps(package["design_reasoning"], ensure_ascii=False, indent=2))
    print("\n[compiled_brief]")
    print(json.dumps(package["compiled_brief"], ensure_ascii=False, indent=2))
    print("\n[prompt]")
    print(package["prompt"])

    settings = package["settings"]
    print(
        "\n[settings]\n"
        f"model={settings['model']}\n"
        f"size={settings['size']}\n"
        f"aspect={settings['aspect']}\n"
        f"direction={settings['direction']}\n"
        f"quality={settings['quality']}"
    )


def main() -> int:
    args = parse_args()
    package = compile_prompt_package(
        brief=args.brief,
        task=args.task,
        direction=args.direction,
        aspect=args.aspect,
        quality=args.quality,
        audience=args.audience,
        usage=args.usage,
        brand=args.brand,
        style=args.style,
        mood=args.mood,
        goal=args.goal,
        composition=args.composition,
        constraints=args.constraints,
        avoid=args.avoid,
        safe_zone=args.safe_zone,
        lighting=args.lighting,
        palette=args.palette,
        image=args.image,
        model_override=args.model_override,
    )
    print_package(package)
    sys.stdout.flush()

    if args.prompt_only:
        return 0

    save_dir = args.output_dir
    if args.output:
        output_path = Path(args.output)
        if output_path.parent != Path("."):
            save_dir = str(output_path.parent)

    result = generate_image(
        prompt=package["prompt"],
        size=package["settings"]["aspect"],
        save_dir=save_dir,
    )
    if result.get("status") == "success" and args.output:
        target_dir = Path(save_dir) if save_dir else Path(result["filepath"]).parent
        target_path = target_dir / Path(args.output).name
        Path(result["filepath"]).replace(target_path)
        result["filepath"] = str(target_path)
        result["filename"] = target_path.name

    print("\n[result]")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
