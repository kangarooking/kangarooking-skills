"""Audio extraction and ASR helpers for video-downloader."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SILICONFLOW_TRANSCRIPTION_URL = "https://api.siliconflow.cn/v1/audio/transcriptions"
SILICONFLOW_DEFAULT_MODEL = "FunAudioLLM/SenseVoiceSmall"


def run_asr(
    video_path: Path,
    output_dir: Path,
    *,
    backend: str = "auto",
    model: str = "base",
    language: str = "auto",
    prompt: str | None = None,
    max_seconds: float | None = None,
) -> dict:
    selected_backend = _select_backend(backend)
    if selected_backend is None:
        return {
            "status": "pending",
            "backend": backend,
            "audio_path": None,
            "transcript_path": None,
            "error": (
                "No ASR backend is available. Set SILICONFLOW_API_KEY, "
                "install openai-whisper, or run with --asr none."
            ),
        }

    audio_path = output_dir / ("audio.mp3" if selected_backend == "siliconflow" else "audio.m4a")
    transcript_path = output_dir / "transcript.txt"
    whisper_json_path = output_dir / "transcript.whisper.json"
    siliconflow_json_path = output_dir / "transcript.siliconflow.json"

    try:
        extract_audio(video_path, audio_path, max_seconds=max_seconds)
        if selected_backend == "siliconflow":
            resolved_model = _resolve_model(selected_backend, model)
            transcribe_with_siliconflow(
                audio_path,
                transcript_path,
                siliconflow_json_path,
                model=resolved_model,
            )
            raw_json_path = siliconflow_json_path
        else:
            resolved_model = _resolve_model(selected_backend, model)
            transcribe_with_whisper(
                audio_path,
                output_dir,
                transcript_path,
                whisper_json_path,
                model=resolved_model,
                language=language,
                prompt=prompt,
            )
            raw_json_path = whisper_json_path
    except RuntimeError as exc:
        return {
            "status": "failed",
            "backend": selected_backend,
            "audio_path": str(audio_path),
            "transcript_path": None,
            "error": str(exc),
        }

    return {
        "status": "done",
        "backend": selected_backend,
        "model": resolved_model,
        "language": language,
        "prompt": prompt or default_prompt_for(language),
        "audio_path": str(audio_path),
        "transcript_path": str(transcript_path),
        "raw_json_path": str(raw_json_path),
    }


def extract_audio(video_path: Path, audio_path: Path, *, max_seconds: float | None = None) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for audio extraction but was not found on PATH.")

    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
    ]
    if audio_path.suffix.lower() == ".mp3":
        command.extend(["-codec:a", "libmp3lame"])
    if max_seconds is not None:
        command.extend(["-t", str(max_seconds)])
    command.append(str(audio_path))
    _run(command, "ffmpeg audio extraction failed")


def transcribe_with_whisper(
    audio_path: Path,
    output_dir: Path,
    transcript_path: Path,
    whisper_json_path: Path,
    *,
    model: str,
    language: str,
    prompt: str | None,
) -> None:
    whisper = shutil.which("whisper")
    if not whisper:
        raise RuntimeError("whisper CLI was not found on PATH.")

    with tempfile.TemporaryDirectory(dir=str(output_dir)) as temp_dir:
        command = [
            whisper,
            str(audio_path),
            "--model",
            model,
            "--output_dir",
            temp_dir,
            "--output_format",
            "json",
            "--task",
            "transcribe",
            "--fp16",
            "False",
            "--verbose",
            "False",
        ]
        if language and language.lower() != "auto":
            command.extend(["--language", language])
        initial_prompt = prompt or default_prompt_for(language)
        if initial_prompt:
            command.extend(["--initial_prompt", initial_prompt])
        _run(command, "whisper transcription failed", timeout=3600)

        source_json = Path(temp_dir) / f"{audio_path.stem}.json"
        if not source_json.exists():
            raise RuntimeError("whisper finished but did not produce JSON output.")

        data = json.loads(source_json.read_text(encoding="utf-8"))
        transcript = (data.get("text") or "").strip()
        transcript_path.write_text(transcript + ("\n" if transcript else ""), encoding="utf-8")
        data["prompt"] = initial_prompt
        whisper_json_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def transcribe_with_siliconflow(
    audio_path: Path,
    transcript_path: Path,
    raw_json_path: Path,
    *,
    model: str,
) -> None:
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        raise RuntimeError("SILICONFLOW_API_KEY is required for ASR backend 'siliconflow'.")

    body, content_type = _multipart_body(
        fields={"model": model},
        file_field="file",
        file_path=audio_path,
        file_content_type="audio/mpeg",
    )
    request = Request(
        SILICONFLOW_TRANSCRIPTION_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": content_type,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=600) as response:
            response_text = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"SiliconFlow transcription failed: HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"SiliconFlow transcription failed: {exc}") from exc

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"SiliconFlow returned non-JSON response: {response_text[:500]}") from exc

    transcript = (data.get("text") or "").strip()
    if not transcript:
        raise RuntimeError("SiliconFlow transcription response did not include text.")
    transcript_path.write_text(transcript + "\n", encoding="utf-8")
    data["model"] = model
    raw_json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def default_prompt_for(language: str) -> str | None:
    if language and language.lower() in {"chinese", "zh", "mandarin"}:
        return "请使用简体中文转写，不要使用繁体中文。保留专有名词、英文缩写和产品名称。"
    return None


def _select_backend(backend: str) -> str | None:
    if backend == "siliconflow":
        if not os.environ.get("SILICONFLOW_API_KEY"):
            raise RuntimeError("ASR backend 'siliconflow' requested but SILICONFLOW_API_KEY is not set.")
        return "siliconflow"
    if backend == "whisper":
        if not shutil.which("whisper"):
            raise RuntimeError("ASR backend 'whisper' requested but whisper CLI was not found.")
        return "whisper"
    if backend == "auto":
        if os.environ.get("SILICONFLOW_API_KEY"):
            return "siliconflow"
        return "whisper" if shutil.which("whisper") else None
    raise RuntimeError(f"Unsupported ASR backend: {backend}")


def _resolve_model(backend: str, model: str) -> str:
    if backend == "siliconflow" and model in {"auto", "base", ""}:
        return SILICONFLOW_DEFAULT_MODEL
    if backend == "whisper" and model in {"auto", ""}:
        return "base"
    return model


def _multipart_body(
    *,
    fields: dict[str, str],
    file_field: str,
    file_path: Path,
    file_content_type: str,
) -> tuple[bytes, str]:
    boundary = f"----video-downloader-{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    parts.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{file_path.name}"\r\n'
            ).encode("utf-8"),
            f"Content-Type: {file_content_type}\r\n\r\n".encode("utf-8"),
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _run(command: list[str], error_message: str, *, timeout: int = 600) -> None:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"{error_message}: {detail}")
