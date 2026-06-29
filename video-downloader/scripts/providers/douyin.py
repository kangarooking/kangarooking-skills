"""Douyin provider using the H5 share page SSR payload."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from time import strftime
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


PLATFORM = "douyin"

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)

HEADERS = {
    "User-Agent": MOBILE_UA,
    "Referer": "https://www.iesdouyin.com/",
}


def supports(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(domain in host for domain in ("douyin.com", "iesdouyin.com"))


def fetch(url: str, output_root: Path, *, metadata_only: bool = False, **options) -> dict:
    allow_yt_dlp_fallback = options.get("allow_yt_dlp_fallback", True)
    provider_options = dict(options)
    provider_options.pop("allow_yt_dlp_fallback", None)
    try:
        return _fetch_h5(
            url,
            output_root,
            metadata_only=metadata_only,
            allow_yt_dlp_fallback=allow_yt_dlp_fallback,
            **provider_options,
        )
    except RuntimeError as exc:
        if allow_yt_dlp_fallback:
            return _fetch_with_ytdlp(
                url,
                output_root,
                metadata_only=metadata_only,
                primary_error=str(exc),
            )
        raise


def _fetch_h5(
    url: str,
    output_root: Path,
    *,
    metadata_only: bool = False,
    allow_yt_dlp_fallback: bool = True,
    **options,
) -> dict:
    ratio = options.get("ratio") or "1080p"
    html, final_url = _download_text(url)
    router_data = _extract_router_data(html)
    item = _extract_item(router_data)
    video_info = item.get("video") or {}
    play_addr = video_info.get("play_addr") or {}
    play_url = _first(play_addr.get("url_list"))
    video_resource_id = _extract_video_resource_id(play_url) or play_addr.get("uri")
    aweme_id = str(item.get("aweme_id") or _extract_aweme_id(final_url) or "unknown")

    if not video_resource_id:
        raise RuntimeError("Could not find Douyin video resource ID in share page payload.")

    folder = output_root / f"douyin-{aweme_id}"
    folder.mkdir(parents=True, exist_ok=True)

    caption = item.get("desc") or ""
    post_caption_path = folder / "post_caption.txt"
    post_caption_path.write_text(caption, encoding="utf-8")

    metadata = _normalize_metadata(
        source_url=url,
        final_url=final_url,
        item=item,
        video_resource_id=video_resource_id,
        ratio=ratio,
    )

    video_path = None
    if not metadata_only:
        filename = _safe_filename(caption, aweme_id)
        video_path = folder / filename
        try:
            _download_binary(_build_nowm_url(video_resource_id, ratio), video_path)
            download_method = "douyin_h5_nowm"
            download_error = None
        except RuntimeError as exc:
            if not allow_yt_dlp_fallback:
                raise
            video_path = _download_with_ytdlp(url, folder, filename)
            download_method = "yt_dlp_fallback"
            download_error = str(exc)
        metadata["download"] = {
            "video_path": str(video_path),
            "method": download_method,
            "primary_error": download_error,
            "endpoint": "https://aweme.snssdk.com/aweme/v1/play/"
            if download_method == "douyin_h5_nowm"
            else None,
            "ratio": ratio,
        }
    else:
        metadata["download"] = {
            "video_path": None,
            "metadata_only": True,
            "ratio": ratio,
        }

    metadata_path = folder / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "platform": PLATFORM,
        "id": aweme_id,
        "output_dir": str(folder),
        "video_path": str(video_path) if video_path else None,
        "post_caption_path": str(post_caption_path),
        "caption_path": str(post_caption_path),
        "metadata_path": str(metadata_path),
        "post_caption": caption,
        "caption": caption,
        "author": metadata.get("author", {}).get("nickname"),
        "duration_seconds": metadata.get("video", {}).get("duration_seconds"),
        "resolution": metadata.get("video", {}).get("resolution"),
        "download_method": metadata.get("download", {}).get("method"),
    }


def _fetch_with_ytdlp(
    url: str,
    output_root: Path,
    *,
    metadata_only: bool,
    primary_error: str,
) -> dict:
    metadata = _extract_metadata_with_ytdlp(url)
    aweme_id = str(metadata.get("id") or _extract_aweme_id(metadata.get("webpage_url", "")) or "unknown")
    folder = output_root / f"douyin-{aweme_id}"
    folder.mkdir(parents=True, exist_ok=True)

    caption = metadata.get("description") or metadata.get("title") or ""
    post_caption_path = folder / "post_caption.txt"
    post_caption_path.write_text(caption, encoding="utf-8")

    video_path = None
    if not metadata_only:
        video_path = _download_with_ytdlp(url, folder, _safe_filename(caption, aweme_id))

    normalized = {
        "platform": PLATFORM,
        "source_url": url,
        "final_url": metadata.get("webpage_url"),
        "fetched_at": strftime("%Y-%m-%dT%H:%M:%S%z"),
        "id": aweme_id,
        "caption": caption,
        "author": {
            "nickname": metadata.get("uploader") or metadata.get("channel"),
            "unique_id": metadata.get("uploader_id"),
        },
        "video": {
            "width": metadata.get("width"),
            "height": metadata.get("height"),
            "resolution": _resolution(metadata.get("width"), metadata.get("height")),
            "duration_seconds": metadata.get("duration"),
        },
        "download": {
            "method": "yt_dlp_fallback",
            "video_path": str(video_path) if video_path else None,
            "metadata_only": metadata_only,
            "primary_error": primary_error,
        },
        "raw_ytdlp_metadata": metadata,
    }

    metadata_path = folder / "metadata.json"
    metadata_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "platform": PLATFORM,
        "id": aweme_id,
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
        "download_method": "yt_dlp_fallback",
    }


def _download_text(url: str) -> tuple[str, str]:
    request = Request(url, headers=HEADERS)
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            return body, response.geturl()
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Failed to fetch Douyin share page: {exc}") from exc


def _download_binary(url: str, destination: Path) -> None:
    request = Request(url, headers=HEADERS)
    try:
        with urlopen(request, timeout=60) as response:
            suffix = destination.suffix or ".mp4"
            with tempfile.NamedTemporaryFile(
                "wb",
                delete=False,
                dir=str(destination.parent),
                suffix=suffix,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                shutil.copyfileobj(response, temp_file)
        temp_path.replace(destination)
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Failed to download Douyin video: {exc}") from exc


def _extract_metadata_with_ytdlp(url: str) -> dict:
    yt_dlp = _require_ytdlp()
    commands = [
        [yt_dlp, "--no-playlist", "--dump-single-json", url],
        [yt_dlp, "--cookies-from-browser", "chrome", "--no-playlist", "--dump-single-json", url],
    ]
    return json.loads(_run_first_successful(commands))


def _download_with_ytdlp(url: str, folder: Path, filename: str) -> Path:
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
    _run_first_successful(commands)
    if output_path.exists():
        return output_path

    matches = sorted(folder.glob(f"{output_path.stem}.*"))
    if matches:
        return matches[0]
    raise RuntimeError("yt-dlp reported success but no downloaded video file was found.")


def _run_first_successful(commands: list[list[str]]) -> str:
    errors = []
    for command in commands:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if completed.returncode == 0:
            return completed.stdout
        errors.append(completed.stderr.strip() or completed.stdout.strip())
    raise RuntimeError("yt-dlp fallback failed: " + " | ".join(errors))


def _require_ytdlp() -> str:
    yt_dlp = shutil.which("yt-dlp")
    if yt_dlp:
        return yt_dlp
    raise RuntimeError("yt-dlp fallback requested but yt-dlp is not installed or not on PATH.")


def _extract_router_data(html: str) -> dict:
    match = re.search(r"window\._ROUTER_DATA\s*=\s*(\{.*?\})</script>", html, re.S)
    if not match:
        raise RuntimeError("Could not find window._ROUTER_DATA in Douyin share page.")
    return json.loads(match.group(1))


def _extract_item(router_data: dict) -> dict:
    loader_data = (router_data.get("loaderData") or {})
    for key, value in loader_data.items():
        if "video" not in key or not isinstance(value, dict):
            continue
        video_info = value.get("videoInfoRes") or {}
        item_list = video_info.get("item_list") or []
        if item_list:
            return item_list[0]
    raise RuntimeError("Could not find Douyin item_list in router data.")


def _normalize_metadata(
    *,
    source_url: str,
    final_url: str,
    item: dict,
    video_resource_id: str,
    ratio: str,
) -> dict:
    author = item.get("author") or {}
    music = item.get("music") or {}
    video = item.get("video") or {}
    duration_ms = video.get("duration")
    width = video.get("width")
    height = video.get("height")

    return {
        "platform": PLATFORM,
        "source_url": source_url,
        "final_url": final_url,
        "fetched_at": strftime("%Y-%m-%dT%H:%M:%S%z"),
        "id": str(item.get("aweme_id") or ""),
        "group_id": str(item.get("group_id_str") or ""),
        "post_caption": item.get("desc") or "",
        "caption": item.get("desc") or "",
        "create_time": item.get("create_time"),
        "author": {
            "nickname": author.get("nickname"),
            "unique_id": author.get("unique_id"),
            "short_id": author.get("short_id"),
            "sec_uid": author.get("sec_uid"),
            "signature": author.get("signature"),
        },
        "music": {
            "id": music.get("mid"),
            "title": music.get("title"),
            "author": music.get("author"),
            "duration": music.get("duration"),
        },
        "video": {
            "resource_id": video_resource_id,
            "preferred_ratio": ratio,
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}" if width and height else None,
            "duration_ms": duration_ms,
            "duration_seconds": round(duration_ms / 1000, 3)
            if isinstance(duration_ms, (int, float))
            else None,
            "play_addr": video.get("play_addr"),
            "cover": video.get("cover"),
        },
        "statistics": item.get("statistics") or {},
        "risk_infos": item.get("risk_infos") or {},
        "hashtags": [
            extra.get("hashtag_name")
            for extra in (item.get("text_extra") or [])
            if extra.get("hashtag_name")
        ],
    }


def _build_nowm_url(video_resource_id: str, ratio: str) -> str:
    return (
        "https://aweme.snssdk.com/aweme/v1/play/"
        f"?video_id={video_resource_id}&ratio={ratio}&line=0"
    )


def _extract_video_resource_id(play_url: str | None) -> str | None:
    if not play_url:
        return None
    parsed = urlparse(play_url)
    return _first(parse_qs(parsed.query).get("video_id"))


def _extract_aweme_id(url: str) -> str | None:
    match = re.search(r"/(?:video|share/video)/(\d+)", url)
    return match.group(1) if match else None


def _first(value):
    if isinstance(value, list) and value:
        return value[0]
    return value


def _resolution(width, height) -> str | None:
    return f"{width}x{height}" if width and height else None


def _safe_filename(caption: str, aweme_id: str) -> str:
    stem = re.sub(r"\s+", " ", caption).strip()[:60] or "douyin-video"
    stem = re.sub(r'[\\/:*?"<>|#]+', "-", stem).strip(" .-")
    return f"{stem}-{aweme_id}.mp4"
