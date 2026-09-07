"""Media validation and ffprobe helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def probe_video(path: Path) -> dict:
    """Validate a video file and return normalized stream metadata."""
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"Video file does not exist: {path}")
    if path.stat().st_size <= 0:
        raise RuntimeError(f"Video file is empty: {path}")
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required for media validation but was not found on PATH.")
    try:
        completed = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration,size,format_name:stream=index,codec_type,codec_name,width,height,r_frame_rate",
                "-of",
                "json",
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("ffprobe media validation timed out after 60 seconds.") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Downloaded file is not a valid readable video: {detail}")
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ffprobe returned invalid JSON.") from exc
    video_stream = next(
        (stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"),
        None,
    )
    if not video_stream:
        raise RuntimeError("Downloaded media does not contain a video stream.")
    audio_stream = next(
        (stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"),
        None,
    )
    format_data = data.get("format") or {}
    duration = _as_float(format_data.get("duration"))
    width = _as_int(video_stream.get("width"))
    height = _as_int(video_stream.get("height"))
    return {
        "duration_seconds": duration,
        "width": width,
        "height": height,
        "resolution": f"{width}x{height}" if width and height else None,
        "video_codec": video_stream.get("codec_name"),
        "has_audio": audio_stream is not None,
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
        "frame_rate": video_stream.get("r_frame_rate"),
        "format_name": format_data.get("format_name"),
        "size_bytes": path.stat().st_size,
    }


def _as_float(value) -> float | None:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _as_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
