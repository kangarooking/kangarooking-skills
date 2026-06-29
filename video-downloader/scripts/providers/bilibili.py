"""Bilibili provider backed by yt-dlp."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from time import strftime
from urllib.parse import urlparse


PLATFORM = "bilibili"


def supports(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(domain in host for domain in ("bilibili.com", "b23.tv"))


def fetch(url: str, output_root: Path, *, metadata_only: bool = False, **options) -> dict:
    metadata = _extract_metadata(url)
    item_id = _item_id(metadata)
    folder = output_root / f"bilibili-{item_id}"
    folder.mkdir(parents=True, exist_ok=True)

    caption = _post_caption(metadata)
    post_caption_path = folder / "post_caption.txt"
    post_caption_path.write_text(caption, encoding="utf-8")

    video_path = None
    if not metadata_only:
        video_path = _download_video(url, folder, _safe_filename(metadata.get("title"), item_id))

    normalized = _normalize_metadata(
        url,
        metadata,
        item_id=item_id,
        caption=caption,
        video_path=video_path,
        metadata_only=metadata_only,
    )
    metadata_path = folder / "metadata.json"
    metadata_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "platform": PLATFORM,
        "id": item_id,
        "output_dir": str(folder),
        "video_path": str(video_path) if video_path else None,
        "post_caption_path": str(post_caption_path),
        "caption_path": str(post_caption_path),
        "metadata_path": str(metadata_path),
        "post_caption": caption,
        "caption": caption,
        "author": normalized.get("author", {}).get("nickname"),
        "duration_seconds": normalized.get("video", {}).get("duration_seconds"),
        "resolution": normalized.get("video", {}).get("resolution"),
        "download_method": normalized.get("download", {}).get("method"),
    }


def _extract_metadata(url: str) -> dict:
    yt_dlp = _require_ytdlp()
    commands = [
        [yt_dlp, "--no-playlist", "--dump-single-json", url],
        [yt_dlp, "--cookies-from-browser", "chrome", "--no-playlist", "--dump-single-json", url],
    ]
    return json.loads(_run_first_successful(commands))


def _download_video(url: str, folder: Path, filename: str) -> Path:
    yt_dlp = _require_ytdlp()
    output_path = folder / filename
    commands = [
        [
            yt_dlp,
            "--no-playlist",
            "-f",
            "bv*+ba/b",
            "--merge-output-format",
            "mp4",
            "-o",
            str(output_path),
            url,
        ],
        [
            yt_dlp,
            "--cookies-from-browser",
            "chrome",
            "--no-playlist",
            "-f",
            "bv*+ba/b",
            "--merge-output-format",
            "mp4",
            "-o",
            str(output_path),
            url,
        ],
    ]
    _run_first_successful(commands, timeout=900)
    if output_path.exists():
        return output_path

    matches = sorted(folder.glob(f"{output_path.stem}.*"))
    if matches:
        return matches[0]
    raise RuntimeError("yt-dlp reported success but no downloaded Bilibili video file was found.")


def _normalize_metadata(
    source_url: str,
    metadata: dict,
    *,
    item_id: str,
    caption: str,
    video_path: Path | None,
    metadata_only: bool,
) -> dict:
    width = metadata.get("width")
    height = metadata.get("height")
    return {
        "platform": PLATFORM,
        "source_url": source_url,
        "final_url": metadata.get("webpage_url") or metadata.get("original_url"),
        "fetched_at": strftime("%Y-%m-%dT%H:%M:%S%z"),
        "id": item_id,
        "caption": caption,
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "tags": metadata.get("tags") or [],
        "author": {
            "nickname": metadata.get("uploader") or metadata.get("channel"),
            "id": metadata.get("uploader_id") or metadata.get("channel_id"),
        },
        "video": {
            "width": width,
            "height": height,
            "resolution": _resolution(width, height),
            "duration_seconds": metadata.get("duration"),
            "view_count": metadata.get("view_count"),
            "like_count": metadata.get("like_count"),
            "comment_count": metadata.get("comment_count"),
        },
        "download": {
            "method": "yt_dlp",
            "video_path": str(video_path) if video_path else None,
            "metadata_only": metadata_only,
        },
        "raw_ytdlp_metadata": metadata,
    }


def _post_caption(metadata: dict) -> str:
    parts = []
    title = (metadata.get("title") or "").strip()
    description = (metadata.get("description") or "").strip()
    if title:
        parts.append(title)
    if description and description != title:
        parts.append(description)
    return "\n\n".join(parts)


def _item_id(metadata: dict) -> str:
    for key in ("id", "display_id", "webpage_url_basename"):
        value = metadata.get(key)
        if value:
            return _safe_id(str(value))
    return "unknown"


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "unknown"


def _safe_filename(title: str | None, item_id: str) -> str:
    stem = title or item_id
    stem = re.sub(r"[\\/:*?\"<>|\n\r\t]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    stem = stem[:80].strip() or item_id
    return f"{stem}-{item_id}.mp4"


def _resolution(width: int | None, height: int | None) -> str | None:
    if width and height:
        return f"{width}x{height}"
    return None


def _run_first_successful(commands: list[list[str]], *, timeout: int = 240) -> str:
    errors = []
    for command in commands:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if completed.returncode == 0:
            return completed.stdout
        errors.append(completed.stderr.strip() or completed.stdout.strip())
    raise RuntimeError("yt-dlp Bilibili route failed: " + " | ".join(errors))


def _require_ytdlp() -> str:
    yt_dlp = shutil.which("yt-dlp")
    if yt_dlp:
        return yt_dlp
    raise RuntimeError("Bilibili provider requires yt-dlp, but yt-dlp is not installed or not on PATH.")
