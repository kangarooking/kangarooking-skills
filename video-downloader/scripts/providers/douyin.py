"""Douyin video acquisition through H5, Jingxuan, and yt-dlp."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from http.client import HTTPException
from pathlib import Path
from time import strftime
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from media_probe import probe_video

from .safety import artifact_basename, sanitize_url


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
JINGXUAN_ORIGIN = "https://jingxuan.douyin.com"
JINGXUAN_HEADERS = {
    "User-Agent": MOBILE_UA.replace(" Version/17.0", ""),
    "Referer": f"{JINGXUAN_ORIGIN}/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def supports(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(domain in host for domain in ("douyin.com", "iesdouyin.com"))


def fetch(url: str, output_root: Path, *, metadata_only: bool = False, **options) -> dict:
    ratio = options.get("ratio")
    aweme_id = _extract_aweme_id(url)
    try:
        html, final_url = _download_text(url)
        aweme_id = _extract_aweme_id(final_url) or aweme_id
        return _fetch_h5(
            url,
            output_root,
            html=html,
            final_url=final_url,
            metadata_only=metadata_only,
            ratio=ratio or "1080p",
        )
    except RuntimeError as exc:
        errors = [f"H5: {exc}"]
        last_error = exc
        if isinstance(exc.__cause__, HTTPError):
            aweme_id = _extract_aweme_id(exc.__cause__.geturl()) or aweme_id

    if aweme_id:
        try:
            return _fetch_jingxuan(url, output_root, aweme_id, metadata_only=metadata_only, ratio=ratio)
        except RuntimeError as exc:
            errors.append(f"Jingxuan: {exc}")
            last_error = exc

    if options.get("allow_yt_dlp_fallback", True):
        try:
            return _fetch_with_ytdlp(url, output_root, metadata_only=metadata_only, primary_error=errors[0])
        except RuntimeError as exc:
            errors.append(str(exc))
            last_error = exc

    raise RuntimeError("Douyin acquisition failed: " + " | ".join(errors)) from last_error


def _fetch_h5(
    url: str,
    output_root: Path,
    *,
    html: str,
    final_url: str,
    metadata_only: bool,
    ratio: str,
) -> dict:
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
    caption = item.get("desc") or ""

    metadata = _normalize_metadata(
        source_url=url,
        final_url=final_url,
        item=item,
        video_resource_id=video_resource_id,
        ratio=ratio,
    )

    video_path = None
    if not metadata_only:
        folder.mkdir(parents=True, exist_ok=True)
        video_path = folder / _safe_filename(caption, aweme_id)
        _download_binary(_build_nowm_url(video_resource_id, ratio), video_path)
        metadata["download"] = {
            "video_path": artifact_basename(video_path),
            "method": "douyin_h5_nowm",
            "primary_route_failed": False,
            "endpoint": "https://aweme.snssdk.com/aweme/v1/play/",
            "ratio": ratio,
        }
    else:
        metadata["download"] = {
            "video_path": None,
            "metadata_only": True,
            "ratio": ratio,
        }

    return _save_result(folder, aweme_id, caption, metadata, video_path)


def _fetch_jingxuan(
    url: str,
    output_root: Path,
    aweme_id: str,
    *,
    metadata_only: bool,
    ratio: str | None,
) -> dict:
    page_url = f"{JINGXUAN_ORIGIN}/m/video/{aweme_id}"
    html, _ = _download_text(page_url, headers=JINGXUAN_HEADERS)
    item, model = _extract_jingxuan_video(html, aweme_id)
    streams = [
        stream for stream in model.get("video_list") or []
        if isinstance(stream, dict)
        and isinstance(stream.get("video_meta"), dict)
        and stream["video_meta"].get("vtype") == "mp4"
        and all(isinstance(stream["video_meta"].get(key), int) and stream["video_meta"][key] > 0
                for key in ("vwidth", "vheight", "size"))
        and any(_is_https_url(stream.get(key)) for key in ("main_url", "backup_url"))
    ]
    if not streams:
        raise RuntimeError("No MP4 streams found on the Jingxuan page.")

    def quality(stream: dict) -> tuple[bool, int, int]:
        media = stream["video_meta"]
        height = media["vheight"]
        preferred = ratio and ratio.lower() in (str(media.get("definition", "")).lower(), f"{height}p")
        bitrate = media.get("bitrate")
        return bool(preferred), height * media["vwidth"], bitrate if isinstance(bitrate, int) else 0

    streams.sort(key=quality, reverse=True)
    folder = output_root / f"douyin-{aweme_id}"
    caption = item.get("abstract") or item.get("title") or ""
    video_path = None
    selected = streams[0]["video_meta"]
    if not metadata_only:
        folder.mkdir(parents=True, exist_ok=True)
        video_path = folder / _safe_filename(caption, aweme_id)
        selected = _download_jingxuan_stream(streams, video_path)

    width, height = selected["vwidth"], selected["vheight"]
    metadata = {
        "platform": PLATFORM,
        "source_url": sanitize_url(url),
        "final_url": page_url,
        "fetched_at": strftime("%Y-%m-%dT%H:%M:%S%z"),
        "id": aweme_id,
        "caption": caption,
        "post_caption": caption,
        "create_time": item.get("publish_time"),
        "author": {"nickname": (item.get("media_user") or {}).get("screen_name")},
        "video": {
            "width": width,
            "height": height,
            "resolution": _resolution(width, height),
            "duration_seconds": model.get("video_duration"),
        },
        "download": {
            "method": "douyin_jingxuan",
            "video_path": artifact_basename(video_path),
            "metadata_only": metadata_only,
            "primary_route_failed": True,
            "ratio": selected.get("definition") or f"{height}p",
        },
    }
    return _save_result(folder, aweme_id, caption, metadata, video_path)


def _extract_jingxuan_video(html: str, aweme_id: str) -> tuple[dict, dict]:
    marker = re.search(r"window\._SSR_DATA\s*=\s*", html)
    if not marker:
        raise RuntimeError("Could not find Jingxuan video page data.")
    try:
        data, _ = json.JSONDecoder().raw_decode(html, marker.end())
        item = data["data"]["storeState"]["detail"]["videoData"]["result"]
        model = item["video_model"]
        if isinstance(model, str):
            model = json.loads(model)
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not read Jingxuan video data.") from exc
    if str(item.get("gid")) != aweme_id or not isinstance(model, dict):
        raise RuntimeError("Jingxuan did not return data for the requested video ID.")
    return item, model


def _download_jingxuan_stream(streams: list[dict], destination: Path) -> dict:
    for stream in streams:
        media = stream["video_meta"]
        urls = dict.fromkeys(url for url in (stream.get("main_url"), stream.get("backup_url")) if _is_https_url(url))
        for url in urls:
            try:
                _download_binary(
                    url,
                    destination,
                    headers=JINGXUAN_HEADERS,
                    expected_size=media["size"],
                    expected_hash=media.get("file_hash"),
                )
            except RuntimeError:
                continue
            return media
    raise RuntimeError("Could not download a valid MP4 from the Jingxuan playback URLs.")


def _is_https_url(url: object) -> bool:
    if not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and bool(parsed.hostname)
    except ValueError:
        return False


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
    video_path = None
    if not metadata_only:
        video_path = _download_with_ytdlp(url, folder, _safe_filename(caption, aweme_id))

    normalized = {
        "platform": PLATFORM,
        "source_url": sanitize_url(url),
        "final_url": sanitize_url(metadata.get("webpage_url")),
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
            "video_path": artifact_basename(video_path),
            "metadata_only": metadata_only,
            "primary_route_failed": bool(primary_error),
        },
    }

    return _save_result(folder, aweme_id, caption, normalized, video_path)


def _save_result(folder: Path, aweme_id: str, caption: str, metadata: dict, video_path: Path | None) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    post_caption_path = folder / "post_caption.txt"
    post_caption_path.write_text(caption, encoding="utf-8")
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


def _download_text(url: str, *, headers: dict = HEADERS) -> tuple[str, str]:
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            return body, response.geturl()
    except (URLError, HTTPException, TimeoutError, ConnectionError) as exc:
        raise RuntimeError(f"Failed to fetch Douyin share page: {exc}") from exc


def _download_binary(
    url: str,
    destination: Path,
    *,
    headers: dict = HEADERS,
    expected_size: int | None = None,
    expected_hash: str | None = None,
) -> None:
    request = Request(url, headers=headers)
    temp_path = None
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
        if expected_size is not None and temp_path.stat().st_size != expected_size:
            raise RuntimeError("Downloaded MP4 does not match the platform file size.")
        if isinstance(expected_hash, str) and re.fullmatch(r"[0-9a-fA-F]{32}", expected_hash):
            digest = hashlib.md5(usedforsecurity=False)
            with temp_path.open("rb") as downloaded:
                for block in iter(lambda: downloaded.read(1024 * 1024), b""):
                    digest.update(block)
            if digest.hexdigest() != expected_hash.lower():
                raise RuntimeError("Downloaded MP4 does not match the platform checksum.")
        probe_video(temp_path)
        temp_path.replace(destination)
    except (URLError, HTTPException, TimeoutError, ConnectionError) as exc:
        raise RuntimeError("Failed to download Douyin video stream.") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


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
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Could not read the Douyin share page data.") from exc


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
        "source_url": sanitize_url(source_url),
        "final_url": sanitize_url(final_url),
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
