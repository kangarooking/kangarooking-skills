"""Prepare bounded visual proxies for native-video model input."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

from media_probe import probe_video
from .cache import manifest_matches, source_fingerprint, write_manifest


MAX_PROXY_BYTES = 480_000_000


def create_visual_proxy(
    video_path: Path,
    output_dir: Path,
    *,
    max_width: int = 1280,
    max_height: int = 720,
    fps: int = 12,
    crf: int = 28,
) -> dict:
    if not video_path.exists():
        raise RuntimeError(f"Video file does not exist: {video_path}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to prepare a complete-video visual proxy.")
    vision_dir = output_dir / "vision"
    vision_dir.mkdir(parents=True, exist_ok=True)
    destination = vision_dir / "full-video-proxy.mp4"
    manifest_path = vision_dir / "full-video-proxy.manifest.json"
    manifest = {
        "schema_version": 1,
        "source": source_fingerprint(video_path),
        "encoding": {
            "max_width": max_width,
            "max_height": max_height,
            "fps": fps,
            "crf": crf,
            "video_codec": "libx264",
            "audio_codec": "aac",
            "audio_bitrate": "64k",
        },
    }
    if (
        destination.exists()
        and destination.stat().st_size > 0
        and manifest_matches(manifest_path, manifest)
    ):
        media_probe = probe_video(destination)
        if int(media_probe.get("size_bytes") or destination.stat().st_size) > MAX_PROXY_BYTES:
            raise RuntimeError(
                "Cached complete-video proxy exceeds the local 480 MB safety cap; "
                "remove the proxy and use agent-clips or stronger compression."
            )
        return {
            "path": str(destination),
            "reused": True,
            "media_probe": media_probe,
        }
    temporary = destination.with_name(f".{destination.stem}-{uuid.uuid4().hex}.tmp.mp4")
    scale = (
        f"scale=w='min({max_width},iw)':h='min({max_height},ih)':"
        "force_original_aspect_ratio=decrease:force_divisible_by=2,"
        f"fps={fps}"
    )
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        scale,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        "-movflags",
        "+faststart",
        str(temporary),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=3600,
        )
    except subprocess.TimeoutExpired as exc:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("ffmpeg visual proxy creation timed out after 3600 seconds.") from exc
    if completed.returncode != 0 or not temporary.exists() or temporary.stat().st_size <= 0:
        temporary.unlink(missing_ok=True)
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"ffmpeg visual proxy creation failed: {detail}")
    if temporary.stat().st_size > MAX_PROXY_BYTES:
        size = temporary.stat().st_size
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"Complete-video proxy is {size} bytes, above the local 480 MB safety cap. "
            "Use agent-clips or lower the source duration/resolution before native-video upload."
        )
    temporary.replace(destination)
    write_manifest(manifest_path, manifest)
    return {
        "path": str(destination),
        "reused": False,
        "media_probe": probe_video(destination),
    }
