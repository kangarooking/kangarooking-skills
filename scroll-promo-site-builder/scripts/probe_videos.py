#!/usr/bin/env python3
"""Probe promo video files and emit a portable JSON inventory."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Project root")
    parser.add_argument("--input", default="assets/video", help="Video directory, relative to project unless absolute")
    parser.add_argument("--output", required=True, help="JSON report path, relative to project unless absolute")
    return parser.parse_args()


def resolve(project: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project / path


def probe(path: Path) -> dict:
    command = [
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    data = json.loads(completed.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    fmt = data.get("format", {})
    return {
        "path": str(path),
        "codec": video.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": video.get("avg_frame_rate") or video.get("r_frame_rate"),
        "pixel_format": video.get("pix_fmt"),
        "duration": float(fmt.get("duration", 0) or 0),
        "size_bytes": int(fmt.get("size", path.stat().st_size) or 0),
        "audio_streams": len(audio),
    }


def main() -> int:
    args = parse_args()
    project = Path(args.project).expanduser().resolve()
    input_dir = resolve(project, args.input).resolve()
    output = resolve(project, args.output).resolve()

    if not input_dir.is_dir():
        raise SystemExit(f"Input directory not found: {input_dir}")

    files = sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES)
    records: list[dict] = []
    errors: list[dict] = []
    for path in files:
        try:
            records.append(probe(path))
        except (subprocess.CalledProcessError, json.JSONDecodeError, OSError) as exc:
            errors.append({"path": str(path), "error": str(exc)})

    mismatches: dict[str, list[str]] = {}
    for field in ("codec", "width", "height", "fps", "pixel_format"):
        values = {str(item.get(field)) for item in records}
        if len(values) > 1:
            mismatches[field] = sorted(values)

    report = {
        "project": str(project),
        "input": str(input_dir),
        "video_count": len(records),
        "videos": records,
        "mismatches": mismatches,
        "errors": errors,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output} ({len(records)} videos, {len(errors)} errors)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
