#!/usr/bin/env python3
"""Build a normalized review video from a JSON clip manifest."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def resolve(project: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project / path


def duration(path: Path) -> float:
    command = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return float(completed.stdout.strip())


def main() -> int:
    args = parse_args()
    project = Path(args.project).expanduser().resolve()
    manifest_path = resolve(project, args.manifest).resolve()
    output = resolve(project, args.output).resolve()
    config = json.loads(manifest_path.read_text(encoding="utf-8"))

    clips = config.get("clips", [])
    if not clips:
        raise SystemExit("Manifest must contain at least one clip")

    width = int(config.get("width", 1280))
    height = int(config.get("height", 720))
    fps = int(config.get("fps", 30))
    crf = int(config.get("crf", 20))
    paths = [resolve(project, item["path"]).resolve() for item in clips]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise SystemExit("Missing clips:\n" + "\n".join(missing))

    durations = [duration(path) for path in paths]
    command = ["ffmpeg", "-loglevel", "error", "-y"]
    for path in paths:
        command.extend(["-i", str(path)])

    filters: list[str] = []
    for index in range(len(paths)):
        filters.append(
            f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"fps={fps},format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[v{index}]"
        )

    fades = [float(item.get("transition_after", 0) or 0) for item in clips[:-1]]
    if any(value > 0 for value in fades):
        current = "v0"
        accumulated = durations[0]
        for index in range(1, len(paths)):
            requested = fades[index - 1]
            fade = requested if requested > 0 else min(1 / fps, 0.04)
            fade = min(fade, durations[index - 1] / 2, durations[index] / 2)
            offset = max(accumulated - fade, 0)
            out = f"x{index}"
            filters.append(
                f"[{current}][v{index}]xfade=transition=fade:duration={fade:.6f}:"
                f"offset={offset:.6f}[{out}]"
            )
            current = out
            accumulated += durations[index] - fade
        final_label = current
    else:
        inputs = "".join(f"[v{index}]" for index in range(len(paths)))
        filters.append(f"{inputs}concat=n={len(paths)}:v=1:a=0[outv]")
        final_label = "outv"

    output.parent.mkdir(parents=True, exist_ok=True)
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", f"[{final_label}]", "-an",
        "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ])
    subprocess.run(command, check=True)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
