"""Cut precise, upload-friendly video clips with ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

from media_probe import probe_video
from .cache import manifest_matches, source_fingerprint, write_manifest


def cut_clips(video_path: Path, output_dir: Path, clips: list[dict]) -> list[dict]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to cut Agent-selected video clips.")
    clips_dir = output_dir / "vision" / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    source = source_fingerprint(video_path)
    results = []
    for index, clip in enumerate(clips, start=1):
        start_ms = int(clip["start_ms"])
        end_ms = int(clip["end_ms"])
        if start_ms < 0 or end_ms <= start_ms:
            raise RuntimeError(f"Invalid clip bounds: {start_ms}–{end_ms} ms")
        stable_id = f"clip-{index:03d}"
        destination = clips_dir / f"{stable_id}-{start_ms:09d}-{end_ms:09d}.mp4"
        manifest_path = destination.with_suffix(".manifest.json")
        manifest = {
            "schema_version": 2,
            "source": source,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "encoding": {"max_resolution": "1280x720", "video_crf": 26, "audio_bitrate": "64k", "fps": 12, "preset": "veryfast"},
        }
        reusable = (
            destination.exists()
            and destination.stat().st_size > 0
            and manifest_matches(manifest_path, manifest)
        )
        if not reusable:
            temporary = destination.with_name(f".{destination.stem}-{uuid.uuid4().hex}.tmp.mp4")
            command = [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{start_ms / 1000:.3f}",
                "-i",
                str(video_path),
                "-t",
                f"{(end_ms - start_ms) / 1000:.3f}",
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-vf",
                (
                    "scale=w='min(1280,iw)':h='min(720,ih)':"
                    "force_original_aspect_ratio=decrease:force_divisible_by=2,fps=12"
                ),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "26",
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
                    timeout=1800,
                )
            except subprocess.TimeoutExpired as exc:
                temporary.unlink(missing_ok=True)
                raise RuntimeError(f"ffmpeg clip creation timed out for {stable_id}.") from exc
            if completed.returncode != 0 or not temporary.exists() or temporary.stat().st_size <= 0:
                temporary.unlink(missing_ok=True)
                detail = completed.stderr.strip() or completed.stdout.strip()
                raise RuntimeError(f"ffmpeg clip creation failed for {stable_id}: {detail}")
            temporary.replace(destination)
            write_manifest(manifest_path, manifest)
        media_probe = probe_video(destination)
        results.append(
            {
                **clip,
                "id": stable_id,
                "path": str(destination),
                "media_probe": media_probe,
            }
        )
    return results
