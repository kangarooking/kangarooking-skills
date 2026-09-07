"""Hybrid interval and scene-change keyframe extraction with ffmpeg."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


PTS_TIME_RE = re.compile(r"pts_time:([0-9.]+)")


def sample_frames(
    video_path: Path,
    output_dir: Path,
    *,
    interval_seconds: float = 10.0,
    max_frames: int = 24,
    scene_threshold: float = 0.32,
) -> tuple[list[dict], dict]:
    if interval_seconds <= 0:
        raise RuntimeError("Vision frame interval must be greater than zero.")
    if max_frames <= 0:
        raise RuntimeError("Vision max frames must be greater than zero.")
    duration = probe_duration(video_path)
    interval_times = _interval_timestamps(duration, interval_seconds)
    scene_times = detect_scene_timestamps(video_path, scene_threshold=scene_threshold)
    candidates = _merge_candidates(interval_times, scene_times, duration)
    selected = _uniform_cap(candidates, max_frames)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for index, item in enumerate(selected, start=1):
        timestamp_ms = int(round(item["seconds"] * 1000))
        path = frames_dir / f"kf-{index:04d}-{timestamp_ms:010d}.jpg"
        extract_frame(video_path, item["seconds"], path)
        frames.append(
            {
                "id": f"kf-{index:04d}",
                "index": index,
                "timestamp_ms": timestamp_ms,
                "timestamp_seconds": round(item["seconds"], 3),
                "path": str(path),
                "sampling_reason": item["reason"],
            }
        )
    report = {
        "duration_seconds": duration,
        "interval_seconds": interval_seconds,
        "scene_threshold": scene_threshold,
        "interval_candidates": len(interval_times),
        "scene_candidates": len(scene_times),
        "scene_timestamps": scene_times,
        "selected_frames": len(frames),
        "max_frames": max_frames,
    }
    return frames, report


def probe_duration(video_path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required for frame extraction but was not found.")
    try:
        completed = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("ffprobe duration check timed out after 60 seconds.") from exc
    if completed.returncode != 0:
        raise RuntimeError(f"ffprobe duration check failed: {completed.stderr.strip()}")
    try:
        duration = float((json.loads(completed.stdout).get("format") or {}).get("duration"))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not determine video duration for frame extraction.") from exc
    if duration <= 0:
        raise RuntimeError("Video duration must be greater than zero.")
    return duration


def detect_scene_timestamps(video_path: Path, *, scene_threshold: float,
                            cache_dir: Path | None = None, force: bool = False) -> list[float]:
    from .cache import result_path, read_result, write_result, source_fingerprint
    checkpoint = result_path(cache_dir, {'source': source_fingerprint(video_path),
        'threshold': scene_threshold, 'width': 384, 'fps': 4, 'schema': 1}) if cache_dir else None
    cached = read_result(checkpoint) if checkpoint and not force else None
    if cached is not None and isinstance(cached.get('timestamps'), list):
        return cached['timestamps']
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for scene detection but was not found.")
    threshold = min(max(scene_threshold, 0.05), 0.95)
    try:
        completed = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-i",
                str(video_path),
                "-an",
                "-vf",
                f"fps=4,scale=384:-2,select='gt(scene,{threshold})',showinfo",
                "-f",
                "null",
                "-",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("ffmpeg scene detection timed out after 600 seconds.") from exc
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg scene detection failed: {completed.stderr.strip()}")
    timestamps = sorted({round(float(value), 3) for value in PTS_TIME_RE.findall(completed.stderr)})
    if checkpoint:
        write_result(checkpoint, {'timestamps': timestamps})
    return timestamps


def extract_frame(video_path: Path, seconds: float, destination: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for frame extraction but was not found.")
    try:
        completed = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{seconds:.3f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-vf",
                "scale=min(1280\\,iw):-2",
                "-q:v",
                "3",
                str(destination),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        destination.unlink(missing_ok=True)
        raise RuntimeError("ffmpeg keyframe extraction timed out after 120 seconds.") from exc
    if completed.returncode != 0 or not destination.exists():
        raise RuntimeError(f"ffmpeg keyframe extraction failed: {completed.stderr.strip()}")


def _interval_timestamps(duration: float, interval: float) -> list[float]:
    first = min(0.5, max(duration / 2, 0.0))
    values = [first]
    current = interval
    while current < duration:
        values.append(round(current, 3))
        current += interval
    if duration > 1.5:
        values.append(round(max(0.0, duration - 0.5), 3))
    return sorted(set(values))


def _merge_candidates(interval_times: list[float], scene_times: list[float], duration: float) -> list[dict]:
    merged: list[dict] = []
    for seconds, reason in sorted(
        [(value, "interval") for value in interval_times] + [(value, "scene") for value in scene_times]
    ):
        if seconds < 0 or seconds >= duration:
            continue
        if merged and abs(merged[-1]["seconds"] - seconds) < 0.75:
            if reason not in merged[-1]["reason"]:
                merged[-1]["reason"] += f"+{reason}"
            continue
        merged.append({"seconds": seconds, "reason": reason})
    return merged


def _uniform_cap(items: list[dict], limit: int) -> list[dict]:
    if len(items) <= limit:
        return items
    if limit == 1:
        return [items[len(items) // 2]]
    indexes = {round(index * (len(items) - 1) / (limit - 1)) for index in range(limit)}
    return [item for index, item in enumerate(items) if index in indexes]
