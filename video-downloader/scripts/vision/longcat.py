"""LongCat-2.5 OpenAI-compatible multimodal client.

Images are sent inline as data URLs. Videos must be reachable by LongCat over
HTTP(S); local prepared clips are uploaded to Uguu's public temporary hosting.
"""

from __future__ import annotations

import json
import mimetypes
import os
import socket
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .cache import read_result, result_path, source_fingerprint, write_result
from .doubao import (
    _data_url,
    _parse_json_object,
    _parse_notes,
    _parse_video_notes,
    _prompt,
    _video_prompt,
)


LONGCAT_CHAT_URL = "https://api.longcat.ai/openai/v1/chat/completions"
UGUU_UPLOAD_URL = "https://uguu.se/upload"
LONGCAT_DEFAULT_MODEL = "LongCat-2.5"
MAX_IMAGE_BYTES = 10_000_000
MAX_IMAGES_PER_REQUEST = 50
MAX_VIDEO_BYTES = 100_000_000
MAX_VIDEO_SECONDS = 3600


def analyze_frames(
    frames: list[dict],
    *,
    model: str = LONGCAT_DEFAULT_MODEL,
    profile: str = "knowledge",
    custom_prompt: str | None = None,
    batch_size: int = 4,
    timeout: int = 180,
) -> tuple[list[dict], list[dict]]:
    api_key = _api_key()
    if batch_size <= 0 or batch_size > MAX_IMAGES_PER_REQUEST:
        raise RuntimeError("LongCat image batch size must be between 1 and 50.")
    notes: list[dict] = []
    errors: list[dict] = []
    for offset in range(0, len(frames), batch_size):
        batch = frames[offset : offset + batch_size]
        try:
            for frame in batch:
                path = Path(frame["path"])
                if path.stat().st_size > MAX_IMAGE_BYTES:
                    raise RuntimeError(f"LongCat image exceeds the 10 MB limit: {path.name}")
            content: list[dict] = [{"type": "text", "text": _prompt(batch, profile, custom_prompt)}]
            content.extend(
                {
                    "type": "image_url",
                    "image_url": {"url": _data_url(Path(frame["path"]))},
                }
                for frame in batch
            )
            response = _chat(
                api_key=api_key,
                model=model,
                content=content,
                timeout=timeout,
                max_tokens=8192,
            )
            parsed = _parse_notes(
                {"status": "completed", "output_text": _chat_text(response)},
                batch,
                model=model,
                profile=profile,
            )
            for note in parsed:
                note["backend"] = "longcat"
            notes.extend(parsed)
        except (RuntimeError, OSError, ValueError, TypeError) as exc:
            errors.append({"frame_ids": [frame.get("id") for frame in batch], "error": str(exc)})
    return notes, errors


def request_text_json(
    prompt: str,
    *,
    model: str = LONGCAT_DEFAULT_MODEL,
    timeout: int = 600,
    thinking: str = "disabled",
) -> dict:
    del thinking  # LongCat's documented OpenAI-compatible request has no thinking field.
    response = _chat(
        api_key=_api_key(),
        model=model,
        content=[{"type": "text", "text": prompt}],
        timeout=timeout,
        max_tokens=3072,
    )
    return _parse_json_object(_chat_text(response))


def analyze_video_files(
    video_items: list[dict],
    *,
    model: str = LONGCAT_DEFAULT_MODEL,
    profile: str = "knowledge",
    custom_prompt: str | None = None,
    fps: float = 0.5,
    upload_timeout: int = 900,
    response_timeout: int = 600,
    concurrency: int = 2,
    progress: Callable[[str], None] | None = None,
    cache_dir: Path | None = None,
    force: bool = False,
    thinking: str = "disabled",
) -> tuple[list[dict], list[dict]]:
    del fps, thinking  # LongCat controls its own video sampling.
    api_key = _api_key()
    if concurrency <= 0:
        raise RuntimeError("LongCat video concurrency must be greater than zero.")
    if not video_items:
        return [], []
    total = len(video_items)
    results: list[tuple[list[dict], list[dict]] | None] = [None] * total
    with ThreadPoolExecutor(
        max_workers=min(concurrency, total), thread_name_prefix="longcat-video"
    ) as executor:
        futures = {
            executor.submit(
                _analyze_one_video,
                item,
                index=index,
                total=total,
                api_key=api_key,
                model=model,
                profile=profile,
                custom_prompt=custom_prompt,
                upload_timeout=upload_timeout,
                response_timeout=response_timeout,
                progress=progress,
                cache_dir=cache_dir,
                force=force,
            ): index
            for index, item in enumerate(video_items)
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    notes: list[dict] = []
    errors: list[dict] = []
    for result in results:
        if result:
            notes.extend(result[0])
            errors.extend(result[1])
    notes.sort(key=lambda note: (note["start_ms"], note["end_ms"], note["id"]))
    return notes, errors


def _analyze_one_video(
    item: dict,
    *,
    index: int,
    total: int,
    api_key: str,
    model: str,
    profile: str,
    custom_prompt: str | None,
    upload_timeout: int,
    response_timeout: int,
    progress: Callable[[str], None] | None,
    cache_dir: Path | None,
    force: bool,
) -> tuple[list[dict], list[dict]]:
    path = Path(item["path"])
    label = str(item.get("id") or f"video-{index + 1}")
    prefix = f"[{index + 1}/{total}] {label}"
    checkpoint = None
    response = None
    uploaded = None
    notes: list[dict] = []
    errors: list[dict] = []
    try:
        _validate_video(path, item)
        prompt = _video_prompt(item, profile, custom_prompt)
        if cache_dir:
            checkpoint = result_path(
                cache_dir,
                {
                    "backend": "longcat",
                    "source": source_fingerprint(path),
                    "id": label,
                    "prompt": prompt,
                    "model": model,
                    "schema": 1,
                },
            )
            cached = read_result(checkpoint) if not force else None
            if cached:
                try:
                    parsed = _parse_longcat_video(cached, item, model=model, profile=profile)
                except RuntimeError:
                    pass
                else:
                    _notify(progress, f"{prefix}：复用已完成结果，未上传")
                    return parsed, errors
        _notify(progress, f"{prefix}：上传到 Uguu 公网临时空间")
        uploaded = _resolve_video_url(path, item=item, timeout=upload_timeout)
        _notify(progress, f"{prefix}：临时 URL 已就绪，正在请求 LongCat-2.5")
        response = _chat(
            api_key=api_key,
            model=model,
            content=[
                {"type": "text", "text": prompt},
                {"type": "video_url", "video_url": {"url": uploaded["url"]}},
            ],
            timeout=response_timeout,
            max_tokens=16384,
        )
        normalized = {"status": "completed", "output_text": _chat_text(response)}
        try:
            notes = _parse_longcat_video(normalized, item, model=model, profile=profile)
        except RuntimeError as exc:
            if "timestamps" not in str(exc) and "time_base" not in str(exc):
                raise
            duration_ms = int(item.get("end_ms") or 0) - int(item.get("start_ms") or 0)
            correction = (
                prompt
                + f"\n格式纠正：只用相对毫秒，必须满足 0 <= start_ms < end_ms <= {duration_ms}，"
                "time_base 固定为 relative。只返回完整 JSON。"
            )
            response = _chat(
                api_key=api_key,
                model=model,
                content=[
                    {"type": "text", "text": correction},
                    {"type": "video_url", "video_url": {"url": uploaded["url"]}},
                ],
                timeout=response_timeout,
                max_tokens=16384,
            )
            normalized = {"status": "completed", "output_text": _chat_text(response)}
            notes = _parse_longcat_video(normalized, item, model=model, profile=profile)
        if checkpoint:
            write_result(checkpoint, normalized)
        _notify(progress, f"{prefix}：收到 {len(notes)} 条视觉记录")
        if uploaded.get("storage") == "uguu-public-temporary":
            _notify(progress, f"{prefix}：Uguu 公网临时文件将由服务在约 3 小时后自动删除")
        return notes, errors
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        errors.append({"evidence_ids": [label], "error": str(exc)})
        return notes, errors
    finally:
        if uploaded and uploaded.get("cleanup"):
            try:
                uploaded["cleanup"]()
                _notify(progress, f"{prefix}：云端临时对象已删除")
            except Exception as exc:  # cleanup is best-effort and must not expose credentials
                _notify(progress, f"{prefix}：临时对象清理失败（{type(exc).__name__}）")
                errors.append(
                    {
                        "evidence_ids": [label],
                        "error": f"Temporary object cleanup failed: {type(exc).__name__}",
                    }
                )


def _parse_longcat_video(response: dict, item: dict, *, model: str, profile: str) -> list[dict]:
    notes = _parse_video_notes(response, item, model=model, profile=profile)
    for note in notes:
        note["backend"] = "longcat"
    return notes


def _validate_video(path: Path, item: dict) -> None:
    if not path.is_file():
        raise RuntimeError(f"Prepared video does not exist: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise RuntimeError(f"Prepared video is empty: {path}")
    if size > MAX_VIDEO_BYTES:
        raise RuntimeError(
            f"LongCat video {path.name} is {size} bytes, above the 100 MB per-video limit. "
            "Reduce --vision-max-clip-seconds or use keyframes."
        )
    duration = float(item.get("duration_seconds") or 0)
    if duration and duration >= MAX_VIDEO_SECONDS:
        raise RuntimeError("LongCat requires every video to be shorter than 3600 seconds.")


def _resolve_video_url(path: Path, *, item: dict, timeout: int) -> dict:
    direct = str(item.get("public_url") or "").strip()
    if direct:
        _validate_public_url(direct)
        return {"url": direct, "cleanup": None, "storage": "provided"}
    return _upload_to_uguu(path, timeout=timeout)


def _upload_to_uguu(path: Path, *, timeout: int) -> dict:
    """Upload one video to Uguu without buffering the whole file in memory."""
    body, content_type = _multipart_upload_body(path)
    request = Request(
        UGUU_UPLOAD_URL,
        data=body,
        headers={"Content-Type": content_type, "Content-Length": str(body.content_length)},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"Uguu upload returned HTTP {exc.code}; response body was redacted.") from exc
    except URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise RuntimeError("Uguu upload timed out.") from exc
        raise RuntimeError(f"Could not reach Uguu upload: {type(exc.reason).__name__}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError("Uguu upload timed out.") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Uguu upload returned non-JSON data; response body was redacted.") from exc
    files = payload.get("files") if isinstance(payload, dict) else None
    first = files[0] if isinstance(files, list) and files and isinstance(files[0], dict) else None
    url = str(first.get("url") or "") if first else ""
    if not payload.get("success") or not url:
        raise RuntimeError("Uguu upload did not return a usable file URL.")
    _validate_public_url(url)
    return {"url": url, "storage": "uguu-public-temporary", "cleanup": None}


class _MultipartUploadBody:
    """Replayable multipart iterator that streams the file in bounded chunks."""

    def __init__(self, prefix: bytes, path: Path, suffix: bytes, *, chunk_bytes: int = 1024 * 1024):
        self.prefix = prefix
        self.path = path
        self.suffix = suffix
        self.chunk_bytes = chunk_bytes
        self.content_length = len(prefix) + path.stat().st_size + len(suffix)

    def __iter__(self):
        yield self.prefix
        with self.path.open("rb") as handle:
            while True:
                chunk = handle.read(self.chunk_bytes)
                if not chunk:
                    break
                yield chunk
        yield self.suffix


def _multipart_upload_body(path: Path) -> tuple[_MultipartUploadBody, str]:
    boundary = f"----video-downloader-{uuid.uuid4().hex}"
    safe_name = path.name.replace('"', "_").replace("\r", "_").replace("\n", "_")
    mime_type = mimetypes.guess_type(safe_name)[0] or "video/mp4"
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files[]"; filename="{safe_name}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode()
    suffix = f"\r\n--{boundary}--\r\n".encode()
    return _MultipartUploadBody(prefix, path, suffix), f"multipart/form-data; boundary={boundary}"


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("LongCat video_url must be a publicly reachable HTTP(S) URL; oss:// is unsupported.")


def _api_key() -> str:
    value = os.environ.get("LONGCAT_API_KEY")
    if not value:
        raise RuntimeError("LONGCAT_API_KEY is required for LongCat-2.5 visual understanding.")
    return value


def _chat(
    *,
    api_key: str,
    model: str,
    content: list[dict],
    timeout: int,
    max_tokens: int,
) -> dict:
    request = Request(
        LONGCAT_CHAT_URL,
        data=json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": content}],
                "max_tokens": max_tokens,
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    return _open_json(request, timeout=timeout)


def _chat_text(response: dict) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeError("LongCat response did not include choices[0].")
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        values = [
            str(block.get("text") or "").strip()
            for block in content
            if isinstance(block, dict) and block.get("type") in {"text", "output_text"}
        ]
        if any(values):
            return "\n".join(value for value in values if value)
    raise RuntimeError("LongCat response did not include assistant text content.")


class _RetryableLongCatError(RuntimeError):
    pass


def _open_json(request: Request, *, timeout: int) -> dict:
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8", errors="replace")
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise RuntimeError("LongCat returned an unexpected JSON value.")
            return payload
        except HTTPError as exc:
            error_type = _RetryableLongCatError if exc.code in {429, 500, 502, 503, 504} else RuntimeError
            try:
                body = json.loads(exc.read(16384).decode("utf-8", errors="replace"))
                code = body.get("error", {}).get("code") if isinstance(body, dict) else None
            except Exception:
                code = None
            error = error_type(f"LongCat API returned HTTP {exc.code}" + (f" (code={code})" if code else ""))
            if not isinstance(error, _RetryableLongCatError) or attempt == 2:
                raise error from exc
        except URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise RuntimeError("LongCat API timed out.") from exc
            raise RuntimeError(f"Could not reach LongCat API: {type(exc.reason).__name__}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError("LongCat API timed out.") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("LongCat API returned non-JSON data; response body was redacted.") from exc
        time.sleep(2**attempt)
    raise RuntimeError("Unreachable LongCat retry state")


def _notify(progress: Callable[[str], None] | None, message: str) -> None:
    if progress:
        progress(message)
