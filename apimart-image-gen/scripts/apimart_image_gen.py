#!/usr/bin/env python3
"""Submit APIMart GPT-Image-2 jobs, poll task status, and download images."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib import error, parse, request


API_BASE = os.environ.get("APIMART_BASE_URL", "https://api.apimart.ai").rstrip("/")
MODEL = "gpt-image-2"
VALID_SIZES = {
    "auto",
    "1:1",
    "3:2",
    "2:3",
    "4:3",
    "3:4",
    "5:4",
    "4:5",
    "16:9",
    "9:16",
    "2:1",
    "1:2",
    "3:1",
    "1:3",
    "21:9",
    "9:21",
}
VALID_RESOLUTIONS = {"1k", "2k", "4k"}
RUNNING_STATES = {"submitted", "pending", "processing", "in_progress"}
DONE_STATES = {"completed"}
FAILED_STATES = {"failed", "cancelled"}


class ApiError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


def get_api_key() -> str:
    token = os.environ.get("APIMART_API_KEY") or os.environ.get("APIMART_TOKEN")
    if not token:
        raise SystemExit(
            "Missing API key. Set APIMART_API_KEY, for example: export APIMART_API_KEY='...'"
        )
    return token


def is_valid_size(value: str) -> bool:
    return value in VALID_SIZES or re.fullmatch(r"[1-9][0-9]{1,4}x[1-9][0-9]{1,4}", value) is not None


def request_json(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed = parse_json_or_text(raw)
        message = extract_error_message(parsed) or f"HTTP {exc.code}: {raw}"
        raise ApiError(message, status=exc.code, payload=parsed) from exc
    except error.URLError as exc:
        raise ApiError(f"Network error: {exc}") from exc

    parsed = parse_json_or_text(raw)
    if not isinstance(parsed, dict):
        raise ApiError(f"Expected JSON object, got: {raw[:300]}")
    if "error" in parsed:
        raise ApiError(extract_error_message(parsed) or "API returned an error", payload=parsed)
    return parsed


def parse_json_or_text(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def extract_error_message(payload: Any) -> str | None:
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("type") or err)
        if "message" in payload:
            return str(payload["message"])
    return None


def local_file_to_data_uri(path: str) -> str:
    file_path = Path(path).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        raise SystemExit(f"Reference image file not found: {file_path}")
    mime = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def collect_image_urls(args: argparse.Namespace) -> list[str]:
    image_urls: list[str] = []
    image_urls.extend(args.image_url or [])
    image_urls.extend(local_file_to_data_uri(path) for path in (args.image_file or []))
    if len(image_urls) > 16:
        raise SystemExit("APIMart GPT-Image-2 accepts at most 16 reference images.")
    return image_urls


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    if not is_valid_size(args.size):
        raise SystemExit(f"Invalid size: {args.size}")
    if args.resolution not in VALID_RESOLUTIONS:
        raise SystemExit(f"Invalid resolution: {args.resolution}")

    payload: dict[str, Any] = {
        "model": MODEL,
        "prompt": args.prompt,
        "n": 1,
        "size": args.size,
        "resolution": args.resolution,
    }
    image_urls = collect_image_urls(args)
    if image_urls:
        payload["image_urls"] = image_urls
    if args.official_fallback:
        payload["official_fallback"] = True
    return payload


def extract_task_id(response: dict[str, Any]) -> str:
    data = response.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict) and data[0].get("task_id"):
        return str(data[0]["task_id"])
    raise ApiError(f"Could not find task_id in response: {json.dumps(response, ensure_ascii=False)}")


def submit_job(token: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    response = request_json("POST", f"{API_BASE}/v1/images/generations", token, payload)
    return extract_task_id(response), response


def get_task(token: str, task_id: str, language: str) -> dict[str, Any]:
    query = parse.urlencode({"language": language})
    return request_json("GET", f"{API_BASE}/v1/tasks/{parse.quote(task_id)}?{query}", token)


def poll_task(
    token: str,
    task_id: str,
    language: str,
    initial_delay: float,
    poll_interval: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    if initial_delay > 0:
        print(f"Waiting {initial_delay:g}s before first task query...", file=sys.stderr)
        time.sleep(initial_delay)

    deadline = time.time() + timeout_seconds
    last_response: dict[str, Any] | None = None
    while time.time() <= deadline:
        response = get_task(token, task_id, language)
        last_response = response
        data = response.get("data", {})
        status = str(data.get("status", "")).lower()
        progress = data.get("progress")
        print(f"Task {task_id}: {status or 'unknown'} {progress if progress is not None else ''}".strip(), file=sys.stderr)

        if status in DONE_STATES:
            return response
        if status in FAILED_STATES:
            message = extract_error_message(data) or json.dumps(data.get("error", data), ensure_ascii=False)
            raise ApiError(f"Task {task_id} ended with status {status}: {message}", payload=response)
        if status and status not in RUNNING_STATES:
            print(f"Unknown task state '{status}', continuing to poll.", file=sys.stderr)
        time.sleep(poll_interval)

    raise ApiError(
        f"Timed out after {timeout_seconds:g}s while waiting for task {task_id}",
        payload=last_response,
    )


def extract_image_urls(task_response: dict[str, Any]) -> list[str]:
    data = task_response.get("data", {})
    result = data.get("result", {}) if isinstance(data, dict) else {}
    images = result.get("images", []) if isinstance(result, dict) else []
    urls: list[str] = []
    for image in images:
        if not isinstance(image, dict):
            continue
        values = image.get("url", [])
        if isinstance(values, str):
            urls.append(values)
        elif isinstance(values, list):
            urls.extend(str(value) for value in values if value)
    return urls


def extension_from_url(url: str) -> str:
    path = parse.urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return suffix
    return ".png"


def download_images(urls: list[str], output_dir: str, task_id: str) -> list[str]:
    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    for index, url in enumerate(urls):
        ext = extension_from_url(url)
        out_path = out_dir / f"{task_id}_{index}{ext}"
        with request.urlopen(url, timeout=120) as resp:
            out_path.write_bytes(resp.read())
        files.append(str(out_path))
    return files


def output_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def generate(args: argparse.Namespace) -> None:
    payload = build_payload(args)
    if args.dry_run:
        output_json({"dry_run": True, "request": payload})
        return

    token = get_api_key()
    task_id, submit_response = submit_job(token, payload)
    if args.submit_only:
        output_json({"task_id": task_id, "submit_response": submit_response})
        return

    task_response = poll_task(
        token=token,
        task_id=task_id,
        language=args.language,
        initial_delay=args.initial_delay,
        poll_interval=args.poll_interval,
        timeout_seconds=args.timeout_seconds,
    )
    image_urls = extract_image_urls(task_response)
    files: list[str] = []
    if image_urls and not args.no_download:
        files = download_images(image_urls, args.output_dir, task_id)
    output_json(
        {
            "task_id": task_id,
            "status": task_response.get("data", {}).get("status"),
            "image_urls": image_urls,
            "files": files,
            "task_response": task_response,
        }
    )


def status(args: argparse.Namespace) -> None:
    token = get_api_key()
    task_response = get_task(token, args.task_id, args.language)
    image_urls = extract_image_urls(task_response)
    files: list[str] = []
    if args.download and image_urls:
        files = download_images(image_urls, args.output_dir, args.task_id)
    output_json(
        {
            "task_id": args.task_id,
            "status": task_response.get("data", {}).get("status"),
            "image_urls": image_urls,
            "files": files,
            "task_response": task_response,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate", help="Submit a GPT-Image-2 job and optionally wait for results")
    gen.add_argument("--prompt", required=True, help="Text prompt for image generation")
    gen.add_argument("--size", default="1:1", help="Aspect ratio or pixel size, e.g. 16:9 or 1881x836")
    gen.add_argument("--resolution", default="1k", choices=sorted(VALID_RESOLUTIONS))
    gen.add_argument("--image-url", action="append", help="Reference image URL; repeat for multiple images")
    gen.add_argument("--image-file", action="append", help="Local reference image file converted to base64 data URI")
    gen.add_argument("--official-fallback", action="store_true", help="Set APIMart official_fallback=true")
    gen.add_argument("--output-dir", default="./outputs/apimart-image-gen", help="Directory for downloaded images")
    gen.add_argument("--language", default="zh", choices=["zh", "en", "ko", "ja"], help="Task status language")
    gen.add_argument("--initial-delay", type=float, default=12, help="Seconds to wait before first poll")
    gen.add_argument("--poll-interval", type=float, default=4, help="Seconds between task polls")
    gen.add_argument("--timeout-seconds", type=float, default=180, help="Total polling timeout")
    gen.add_argument("--submit-only", action="store_true", help="Submit and print task_id without polling")
    gen.add_argument("--no-download", action="store_true", help="Return final image URLs without downloading")
    gen.add_argument("--dry-run", action="store_true", help="Print request payload without network access")
    gen.set_defaults(func=generate)

    stat = subparsers.add_parser("status", help="Query an existing task")
    stat.add_argument("--task-id", required=True)
    stat.add_argument("--language", default="zh", choices=["zh", "en", "ko", "ja"])
    stat.add_argument("--download", action="store_true", help="Download images if the task is completed")
    stat.add_argument("--output-dir", default="./outputs/apimart-image-gen")
    stat.set_defaults(func=status)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except ApiError as exc:
        error_payload: dict[str, Any] = {"error": str(exc)}
        if exc.status is not None:
            error_payload["status"] = exc.status
        if exc.payload is not None:
            error_payload["payload"] = exc.payload
        print(json.dumps(error_payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
