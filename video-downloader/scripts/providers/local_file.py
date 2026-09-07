"""Local-file provider for ASR and visual processing without platform download."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from time import strftime

from media_probe import probe_video
from .safety import artifact_basename


PLATFORM = "local_file"
SUPPORTED_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}


def supports(source: str) -> bool:
    path = Path(source).expanduser()
    return path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES


def fetch(source: str, output_root: Path, *, metadata_only: bool = False, **options) -> dict:
    path = Path(source).expanduser().resolve()
    if not supports(str(path)):
        raise RuntimeError(f"Unsupported or missing local video file: {path}")
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:10]
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", path.stem).strip("-") or "video"
    folder = output_root / f"local-{safe_stem[:60]}-{digest}"
    folder.mkdir(parents=True, exist_ok=True)
    probe = probe_video(path)
    caption = str(options.get("local_caption") or "").strip()
    caption_path = folder / "post_caption.txt"
    caption_path.write_text(caption + ("\n" if caption else ""), encoding="utf-8")
    metadata = {
        "platform": PLATFORM,
        "source_path": artifact_basename(path),
        "fetched_at": strftime("%Y-%m-%dT%H:%M:%S%z"),
        "id": f"{safe_stem}-{digest}",
        "caption": caption,
        "video": probe,
        "download": {"method": "local_file", "metadata_only": metadata_only},
    }
    metadata_path = folder / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "platform": PLATFORM,
        "id": metadata["id"],
        "output_dir": str(folder),
        "video_path": None if metadata_only else str(path),
        "post_caption_path": str(caption_path),
        "caption_path": str(caption_path),
        "metadata_path": str(metadata_path),
        "post_caption": caption,
        "caption": caption,
        "author": options.get("local_author"),
        "duration_seconds": probe.get("duration_seconds"),
        "resolution": probe.get("resolution"),
        "download_method": "local_file",
    }
