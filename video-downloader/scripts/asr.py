"""Audio extraction and ASR helpers for video-downloader."""

from __future__ import annotations

import json
import hashlib
import os
import socket
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
    video_path: Path, output_dir: Path, *, backend: str = 'auto', model: str = 'base',
    language: str = 'auto', prompt: str | None = None, max_seconds: float | None = None,
    force: bool = False,
    chunk_seconds: float = 0, concurrency: int = 4,
    allow_local_fallback: bool = False, progress=None,
) -> dict:
    # Import lazily: vision's package initializer also imports pipeline helpers.
    from vision.cache import source_fingerprint, result_path, read_result, write_result
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        identity = {'source': source_fingerprint(video_path), 'backend': backend, 'model': model,
                    'language': language, 'prompt': prompt or default_prompt_for(language),
                    'max_seconds': max_seconds, 'cloud_available': bool(os.environ.get('SILICONFLOW_API_KEY')),
                    'chunk_seconds': chunk_seconds, 'allow_local_fallback': allow_local_fallback, 'schema': 2}
        checkpoint = result_path(output_dir / 'asr-cache', identity)
        cached = read_result(checkpoint) if not force else None
        if cached:
            valid = all(Path(path).is_file() and hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
                        for path, digest in cached.get('artifacts', {}).items())
            if cached.get('artifacts') and valid:
                if progress: progress('ASR：复用已完成文本和时间戳')
                return {**cached['processing'], 'reused': True}
        if backend in ('auto', 'siliconflow') and not os.environ.get('SILICONFLOW_API_KEY') and not (backend == 'auto' and allow_local_fallback):
            return {'status': 'pending', 'backend': 'siliconflow',
                    'action_required': 'choose_asr_backend',
                    'choices': ['configure_siliconflow', 'local_whisper'],
                    'error': 'SILICONFLOW_API_KEY is missing. Ask the user to provide a SiliconFlow key or explicitly choose local Whisper (slowest).'}
        if progress: progress(f'ASR：开始 {_select_backend(backend)} 语音识别')
        result = _run_asr_once(video_path, output_dir, backend=backend, model=model,
                               language=language, prompt=prompt, max_seconds=max_seconds,
                               chunk_seconds=chunk_seconds, concurrency=concurrency, force=force, progress=progress)
        if allow_local_fallback and backend == 'auto' and result.get('status') == 'failed' and result.get('backend') == 'siliconflow' and shutil.which('whisper'):
            cloud_error = result.get('error')
            whisper_models = {'tiny', 'base', 'small', 'medium', 'large', 'turbo', 'large-v1', 'large-v2', 'large-v3', 'tiny.en', 'base.en', 'small.en', 'medium.en'}
            result = _run_asr_once(video_path, output_dir, backend='whisper',
                                  model=model if model in whisper_models else 'base',
                                  language=language, prompt=prompt, max_seconds=max_seconds)
            result['warnings'] = [f'SiliconFlow failed; attempted local Whisper: {cloud_error}']
        if result.get('status') == 'done':
            artifacts = {result[field]: hashlib.sha256(Path(result[field]).read_bytes()).hexdigest()
                         for field in ('transcript_path', 'segments_path', 'raw_json_path')}
            write_result(checkpoint, {'processing': result, 'artifacts': artifacts})
        return {**result, 'reused': False}
    except (RuntimeError, OSError, ValueError) as exc:
        return {'status': 'failed', 'backend': backend, 'error': str(exc),
                'transcript_path': None, 'segments_path': None}


def _run_asr_once(
    video_path: Path,
    output_dir: Path,
    *,
    backend: str = "auto",
    model: str = "base",
    language: str = "auto",
    prompt: str | None = None,
    max_seconds: float | None = None,
    chunk_seconds: float = 0, concurrency: int = 4, force: bool = False, progress=None,
) -> dict:
    selected_backend = _select_backend(backend)
    if selected_backend is None:
        return {
            "status": "pending",
            "backend": backend,
            "audio_path": None,
            "transcript_path": None,
            "segments_path": None,
            "error": (
                "No ASR backend is available. Set SILICONFLOW_API_KEY, "
                "install openai-whisper, or run with --asr none."
            ),
        }

    audio_path = output_dir / ("audio.mp3" if selected_backend == "siliconflow" else "audio.m4a")
    transcript_path = output_dir / "transcript.txt"
    segments_path = output_dir / "transcript.segments.jsonl"
    whisper_json_path = output_dir / "transcript.whisper.json"
    siliconflow_json_path = output_dir / "transcript.siliconflow.json"

    try:
        from vision.cache import source_fingerprint, manifest_matches, write_manifest
        audio_manifest = audio_path.with_suffix('.manifest.json')
        identity = {'source': source_fingerprint(video_path), 'max_seconds': max_seconds,
                    'codec': audio_path.suffix, 'sample_rate': 16000, 'schema': 1}
        if not audio_path.is_file() or not manifest_matches(audio_manifest, identity):
            extract_audio(video_path, audio_path, max_seconds=max_seconds)
            if audio_path.is_file(): write_manifest(audio_manifest, identity)
        if selected_backend == "siliconflow":
            resolved_model = _resolve_model(selected_backend, model)
            if chunk_seconds:
                from asr_chunks import transcribe_chunks
                transcribe_chunks(audio_path, transcript_path, siliconflow_json_path, model=resolved_model,
                                  chunk_seconds=chunk_seconds, concurrency=concurrency, force=force, progress=progress)
            else:
                transcribe_with_siliconflow(audio_path, transcript_path, siliconflow_json_path, model=resolved_model)
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
            "segments_path": None,
            "error": str(exc),
        }

    _write_normalized_segments(raw_json_path, transcript_path, segments_path, selected_backend)
    return {
        "status": "done",
        "backend": selected_backend,
        "model": resolved_model,
        "language": language,
        "prompt": prompt or default_prompt_for(language),
        "audio_path": str(audio_path),
        "transcript_path": str(transcript_path),
        "segments_path": str(segments_path),
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
    timeout: int = 120,
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
        with urlopen(request, timeout=timeout) as response:
            response_text = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise RuntimeError(
            f"SiliconFlow transcription failed: HTTP {exc.code}; provider response body was redacted."
        ) from exc
    except URLError as exc:
        reason = "timeout" if isinstance(exc.reason, (TimeoutError, socket.timeout)) else type(exc.reason).__name__
        raise RuntimeError(f"SiliconFlow transcription failed: {reason}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError("SiliconFlow transcription failed: timeout") from exc

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("SiliconFlow returned a non-JSON response; response body was redacted.") from exc

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


def _write_normalized_segments(
    raw_json_path: Path,
    transcript_path: Path,
    segments_path: Path,
    backend: str,
) -> None:
    try:
        payload = json.loads(raw_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    source_segments = payload.get("segments")
    records = []
    if isinstance(source_segments, list):
        for index, item in enumerate(source_segments, start=1):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            start = _seconds_to_ms(item.get("start"))
            end = _seconds_to_ms(item.get("end"))
            records.append(
                {
                    "id": f"asr-{index:04d}",
                    "start_ms": start,
                    "end_ms": end,
                    "speaker": item.get("speaker"),
                    "text": text,
                    "confidence": item.get("confidence"),
                    "backend": backend,
                    "timestamp_precision": item.get('timestamp_precision') or ("segment" if start is not None and end is not None else "document"),
                }
            )
    if not records:
        transcript = transcript_path.read_text(encoding="utf-8").strip()
        if transcript:
            records.append(
                {
                    "id": "asr-0001",
                    "start_ms": None,
                    "end_ms": None,
                    "speaker": None,
                    "text": transcript,
                    "confidence": None,
                    "backend": backend,
                    "timestamp_precision": "document",
                }
            )
    with segments_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _seconds_to_ms(value) -> int | None:
    try:
        return int(round(float(value) * 1000))
    except (TypeError, ValueError, OverflowError):
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
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{error_message}: timed out after {timeout} seconds") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"{error_message}: {detail}")
