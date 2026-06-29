#!/usr/bin/env python3
"""Download videos, platform post captions, and audio transcripts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from asr import run_asr
from providers import detect_provider, planned_provider_for


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download a platform video and extract its original caption/metadata."
    )
    parser.add_argument("url", help="Video share URL or canonical video URL")
    parser.add_argument(
        "--output-dir",
        default="downloads",
        help="Root directory for saved artifacts. Default: downloads",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Extract metadata and caption without downloading the media file.",
    )
    parser.add_argument(
        "--ratio",
        default="1080p",
        help="Provider-specific preferred video ratio/quality. Douyin default: 1080p",
    )
    parser.add_argument(
        "--no-yt-dlp-fallback",
        action="store_true",
        help="Disable yt-dlp fallback for providers that support it.",
    )
    parser.add_argument(
        "--asr",
        choices=("auto", "siliconflow", "whisper", "none"),
        default="auto",
        help="Audio transcription backend. Default: auto",
    )
    parser.add_argument(
        "--asr-model",
        default="base",
        help=(
            "ASR model name. Default: base for Whisper; SiliconFlow maps base/auto "
            "to FunAudioLLM/SenseVoiceSmall."
        ),
    )
    parser.add_argument(
        "--asr-language",
        default="auto",
        help="Whisper language, e.g. Chinese, English, zh. Default: auto",
    )
    parser.add_argument(
        "--asr-prompt",
        default=None,
        help="Initial prompt for Whisper, e.g. ask for Simplified Chinese output.",
    )
    parser.add_argument(
        "--asr-max-seconds",
        type=float,
        default=None,
        help="Optional debug limit: transcribe only the first N seconds.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_root = Path(args.output_dir).expanduser().resolve()

    provider = detect_provider(args.url)
    if provider is None:
        planned = planned_provider_for(args.url)
        if planned:
            print(
                f"Provider '{planned}' is recognized but not implemented yet.",
                file=sys.stderr,
            )
            return 2
        print("No supported provider recognized for this URL.", file=sys.stderr)
        return 2

    result = provider.fetch(
        args.url,
        output_root,
        metadata_only=args.metadata_only,
        ratio=args.ratio,
        allow_yt_dlp_fallback=not args.no_yt_dlp_fallback,
    )
    if not args.metadata_only and args.asr != "none" and result.get("video_path"):
        asr_result = run_asr(
            Path(result["video_path"]),
            Path(result["output_dir"]),
            backend=args.asr,
            model=args.asr_model,
            language=args.asr_language,
            prompt=args.asr_prompt,
            max_seconds=args.asr_max_seconds,
        )
        result["audio_path"] = asr_result.get("audio_path")
        result["transcript_path"] = asr_result.get("transcript_path")
        result["asr"] = asr_result
        _merge_metadata_asr(result.get("metadata_path"), asr_result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _merge_metadata_asr(metadata_path: str | None, asr_result: dict) -> None:
    if not metadata_path:
        return
    path = Path(metadata_path)
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["asr"] = asr_result
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
