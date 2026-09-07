#!/usr/bin/env python3
"""Download videos, platform post captions, and audio transcripts."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from asr import run_asr
from asr_config import load_saved_environment, choose_missing_key_backend
from artifact_metadata import sanitize_metadata_tree
from media_probe import probe_video
from providers import detect_local_provider, detect_provider, planned_provider_for
from text_renderer import render_multimodal_transcript
from vision import run_vision
from vision.doubao import DOUBAO_DEFAULT_VIDEO_MODEL
from vision.frame_sampler import detect_scene_timestamps
from subtitles import use_platform_subtitles
from vision.interaction import VisionInteractionError, choose_vision_mode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download or open a video, transcribe audio, and recover key visual information."
    )
    parser.add_argument("source", help="Video URL or local video file path")
    parser.add_argument('--download-quality', choices=('1080p', '720p', '480p', 'best'), default='1080p',
                        help='Prefer this exact quality; if absent use highest available. Default: 1080p')
    parser.add_argument('--no-platform-subtitles', action='store_true', help='Transcribe audio even if usable platform captions exist.')
    parser.add_argument('--allow-local-asr-fallback', action='store_true', help='Allow auto ASR to fall back to slow local Whisper.')
    parser.add_argument('--asr-chunk-seconds', type=float, default=60, help='Cloud ASR audio chunk duration. Default: 60')
    parser.add_argument('--asr-concurrency', type=int, choices=range(1, 5), default=4)
    parser.add_argument('--vision-thinking', choices=('disabled', 'auto', 'enabled'), default='disabled',
                        help='Doubao selection/native-video reasoning mode. Default: disabled')
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
        "--force-redownload",
        action="store_true",
        help="Download platform media again even when a validated local file already exists.",
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
        "--local-caption",
        default=None,
        help="Optional caption/title for a local video file.",
    )
    parser.add_argument(
        "--local-author",
        default=None,
        help="Optional author for a local video file.",
    )
    parser.add_argument(
        "--wechat-api-url",
        default=None,
        help="Compatible WeChat Channels parser API. Defaults to WX_CHANNELS_API_URL.",
    )
    parser.add_argument(
        "--wechat-api-token",
        default=None,
        help="Bearer token for the parser API. Prefer WX_CHANNELS_API_TOKEN to avoid shell history.",
    )
    parser.add_argument(
        "--wechat-cookie-file",
        default=None,
        help=(
            "Yuanbao session file. Defaults to WX_CHANNELS_COOKIE_FILE or "
            "~/.config/kangarooking-skills/video-downloader/yuanbao-cookies.json."
        ),
    )
    parser.add_argument(
        "--wechat-login",
        action="store_true",
        help="Open Yuanbao authorization even when a saved session exists.",
    )
    parser.add_argument(
        "--no-wechat-auto-login",
        action="store_true",
        help="Do not open a browser when Yuanbao authorization is missing or expired.",
    )
    parser.add_argument(
        "--wechat-login-timeout",
        type=float,
        default=300,
        help="Seconds to wait for interactive Yuanbao authorization. Default: 300",
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
    parser.add_argument(
        "--vision",
        choices=("auto", "doubao", "none"),
        default="auto",
        help="Visual understanding backend. auto uses Doubao when ARK_API_KEY is set.",
    )
    parser.add_argument(
        "--vision-mode",
        choices=("keyframes", "full-video", "agent-clips"),
        default=None,
        help=(
            "Visual extraction strategy: keyframes, full-video, or agent-clips "
            "(recommended). Interactive runs show a menu when omitted."
        ),
    )
    parser.add_argument(
        "--vision-plan-only",
        action="store_true",
        help=(
            "Prepare and print the visual upload plan without calling Doubao visual or "
            "selection models. Earlier SiliconFlow ASR, if selected, is unaffected."
        ),
    )
    parser.add_argument(
        "--confirm-cloud-upload",
        action="store_true",
        help=(
            "Explicitly authorize the planned Doubao upload in non-interactive runs. "
            "Inspect --vision-plan-only first when handling sensitive media."
        ),
    )
    parser.add_argument(
        "--vision-model",
        default="doubao-seed-evolving",
        help="Doubao keyframe and Agent-selection model. Default: doubao-seed-evolving",
    )
    parser.add_argument(
        "--vision-video-model",
        default=os.environ.get("DOUBAO_VIDEO_MODEL", DOUBAO_DEFAULT_VIDEO_MODEL),
        help=(
            "Doubao native-video model for full-video and agent-clips. "
            f"Default: DOUBAO_VIDEO_MODEL or {DOUBAO_DEFAULT_VIDEO_MODEL}"
        ),
    )
    parser.add_argument(
        "--vision-video-fps",
        type=float,
        default=0.5,
        help="Files API video preprocessing sample rate, from 0.2 to 5. Default: 0.5",
    )
    parser.add_argument(
        "--profile",
        choices=("knowledge", "tech", "vlog", "mv", "short-video"),
        default="knowledge",
        help="Visual observation profile. Default: knowledge",
    )
    parser.add_argument(
        "--vision-frame-interval",
        type=float,
        default=10.0,
        help="Fallback keyframe interval in seconds. Default: 10",
    )
    parser.add_argument(
        "--vision-max-frames",
        type=int,
        default=24,
        help="Maximum keyframes sent to the visual model. Default: 24",
    )
    parser.add_argument(
        "--vision-scene-threshold",
        type=float,
        default=0.32,
        help="ffmpeg scene-change threshold from 0.05 to 0.95. Default: 0.32",
    )
    parser.add_argument(
        "--vision-batch-size",
        type=int,
        default=4,
        help="Keyframes per Doubao request. Default: 4",
    )
    parser.add_argument(
        "--vision-prompt",
        default=None,
        help="Optional extra visual-analysis instruction.",
    )
    parser.add_argument(
        "--vision-max-clips",
        type=int,
        default=8,
        help="Maximum Agent candidate intervals before chunking. Default: 8",
    )
    parser.add_argument(
        "--vision-max-clip-seconds",
        type=float,
        default=600.0,
        help="Maximum video chunk duration for full-video and agent-clips. Default: 600",
    )
    parser.add_argument(
        "--vision-max-total-clip-seconds",
        type=float,
        default=0.0,
        help="Optional total Agent-selection budget. Default: 0 (no extra cap)",
    )
    parser.add_argument(
        "--vision-concurrency",
        type=int,
        choices=range(1, 5),
        default=4,
        metavar="1-4",
        help="Concurrent native-video chunks in full-video and agent-clips. Default: 4",
    )
    parser.add_argument(
        "--vision-clip-padding-seconds",
        type=float,
        default=2.0,
        help="Context padding added around Agent-selected ranges. Default: 2",
    )
    parser.add_argument('--force-reprocess', action='store_true', help='Ignore ASR and vision result caches for this run.')
    return parser


def main(argv: list[str] | None = None) -> int:
    run_started = time.monotonic()
    timings = {}
    def progress(message):
        print(f'[{time.monotonic()-run_started:.1f}s] {message}', file=sys.stderr, flush=True)
    args = build_parser().parse_args(argv)
    try:
        load_saved_environment()
    except (OSError, RuntimeError, ValueError) as exc:
        print(f'ASR credential configuration could not be loaded: {type(exc).__name__}', file=sys.stderr)
        return 2
    import math
    if (not math.isfinite(args.vision_max_clip_seconds) or args.vision_max_clip_seconds < 4
        or not math.isfinite(args.vision_max_total_clip_seconds) or args.vision_max_total_clip_seconds < 0
        or not 0.2 <= args.vision_video_fps <= 5 or args.vision_max_clips < 1
        or not math.isfinite(args.asr_chunk_seconds) or args.asr_chunk_seconds < 10):
        print('Invalid visual limits: chunk >=4s, total >=0, candidates >=1, fps 0.2–5.', file=sys.stderr)
        return 2
    output_root = Path(args.output_dir).expanduser().resolve()

    provider = detect_local_provider(args.source) or detect_provider(args.source)
    if provider is None:
        planned = planned_provider_for(args.source)
        if planned:
            print(
                f"Provider '{planned}' is recognized but not implemented yet.",
                file=sys.stderr,
            )
            return 2
        print("No supported provider recognized for this URL.", file=sys.stderr)
        return 2

    vision_mode = args.vision_mode
    if not args.metadata_only and args.vision != "none":
        try:
            vision_mode = choose_vision_mode(args.vision_mode)
        except VisionInteractionError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    progress(f'下载与字幕检查：优先 {args.download_quality}')
    stage_started = time.monotonic()
    result = provider.fetch(
        args.source,
        output_root,
        metadata_only=args.metadata_only,
        force_download=args.force_redownload,
        ratio=args.ratio,
        download_quality=args.download_quality,
        prefer_subtitles=not args.no_platform_subtitles and args.asr == 'auto',
        asr_language=args.asr_language,
        allow_yt_dlp_fallback=not args.no_yt_dlp_fallback,
        local_caption=args.local_caption,
        local_author=args.local_author,
        wechat_api_url=args.wechat_api_url,
        wechat_api_token=args.wechat_api_token,
        wechat_cookie_file=args.wechat_cookie_file,
        wechat_auto_login=not args.no_wechat_auto_login,
        wechat_force_login=args.wechat_login,
        wechat_login_timeout=args.wechat_login_timeout,
    )
    timings['download_and_subtitles_seconds'] = round(time.monotonic()-stage_started, 3)
    progress(f'下载阶段完成，耗时 {timings["download_and_subtitles_seconds"]}秒')
    media_probe = None
    if not args.metadata_only and result.get("video_path"):
        media_probe = probe_video(Path(result["video_path"]))
        result["media_probe"] = media_probe
        result["duration_seconds"] = media_probe.get("duration_seconds")
        result["resolution"] = media_probe.get("resolution")
    asr_result = {"status": "skipped", "backend": "none"}
    scene_times = None
    # Scene signals do not depend on speech; execute alongside ASR instead of after it.
    scene_pool = ThreadPoolExecutor(max_workers=1)
    scene_future = None
    can_start_speech = (args.asr in ('none', 'whisper') or args.allow_local_asr_fallback
                        or bool(os.environ.get('SILICONFLOW_API_KEY'))
                        or (result.get('platform_subtitles') or {}).get('status') == 'done')
    if can_start_speech and not args.metadata_only and args.vision != 'none' and vision_mode == 'agent-clips' and result.get('video_path'):
        def scan_scenes():
            start = time.monotonic()
            progress('辅助场景扫描：384px / 4fps，优先复用缓存')
            values = detect_scene_timestamps(Path(result['video_path']), scene_threshold=args.vision_scene_threshold,
                                            cache_dir=Path(result['output_dir'])/'vision'/'scene-cache', force=args.force_reprocess)
            timings['scene_scan_seconds'] = round(time.monotonic()-start, 3)
            progress(f'场景扫描完成，耗时 {timings["scene_scan_seconds"]}秒')
            return values
        scene_future = scene_pool.submit(scan_scenes)
    stage_started = time.monotonic()
    if not args.metadata_only and args.asr != "none" and result.get("video_path"):
        subtitle = result.get('platform_subtitles') or {}
        if args.asr == 'auto' and subtitle.get('status') == 'done' and not args.no_platform_subtitles:
            asr_result = use_platform_subtitles(Path(subtitle['path']), Path(result['output_dir']))
            progress('已复用平台字幕及其时间戳')
        else:
            asr_result = run_asr(
                Path(result["video_path"]), Path(result["output_dir"]),
                backend=args.asr, model=args.asr_model, language=args.asr_language,
                prompt=args.asr_prompt, max_seconds=args.asr_max_seconds, force=args.force_reprocess,
                chunk_seconds=args.asr_chunk_seconds, concurrency=args.asr_concurrency,
                allow_local_fallback=args.allow_local_asr_fallback, progress=progress,
            )
            if asr_result.get('action_required') == 'choose_asr_backend':
                selected = choose_missing_key_backend()
                if selected:
                    selected_model = 'base' if selected == 'whisper' and '/' in args.asr_model else args.asr_model
                    asr_result = run_asr(Path(result['video_path']), Path(result['output_dir']),
                        backend=selected, model=selected_model, language=args.asr_language,
                        prompt=args.asr_prompt, max_seconds=args.asr_max_seconds, force=args.force_reprocess,
                        chunk_seconds=args.asr_chunk_seconds, concurrency=args.asr_concurrency,
                        allow_local_fallback=False, progress=progress)
        result["audio_path"] = asr_result.get("audio_path")
        result["transcript_path"] = asr_result.get("transcript_path")
    result["asr"] = asr_result
    timings['speech_seconds'] = round(time.monotonic()-stage_started, 3)
    progress(f'语音阶段 {asr_result["status"]}，耗时 {timings["speech_seconds"]}秒')
    try:
        if scene_future:
            scene_times = scene_future.result()
    except RuntimeError as exc:
        # Scene signals are auxiliary; a usable transcript can still drive selection.
        scene_times = []
        result['scene_warning'] = str(exc)
        progress('场景扫描失败；将用已有时间戳文案选段，并记录缺口')
    finally:
        scene_pool.shutdown(wait=True)
    stage_started = time.monotonic()
    vision_result = {"status": "skipped", "backend": "none", "frame_count": 0}
    agent_waits_for_asr = (
        vision_mode == 'agent-clips'
        and args.asr != 'none'
        and asr_result.get('status') != 'done'
    )
    if asr_result.get('action_required') or agent_waits_for_asr:
        if args.vision != 'none':
            reason = ('等待用户选择语音识别渠道' if asr_result.get('action_required')
                      else 'Agent 模式等待完整 ASR；恢复语音阶段后再选段')
            vision_result = {
                'status': 'pending',
                'backend': args.vision,
                'mode': vision_mode,
                'blocked_by': 'asr',
                'error': f'{reason}，未发起视觉模型请求。',
                'frame_count': 0,
            }
    elif not args.metadata_only and args.vision != "none" and result.get("video_path"):
        try:
            vision_result = run_vision(
                Path(result["video_path"]),
                Path(result["output_dir"]),
                backend=args.vision,
                mode=vision_mode or "keyframes",
                model=args.vision_model,
                video_model=args.vision_video_model,
                profile=args.profile,
                interval_seconds=args.vision_frame_interval,
                max_frames=args.vision_max_frames,
                scene_threshold=args.vision_scene_threshold,
                batch_size=args.vision_batch_size,
                prompt=args.vision_prompt,
                video_fps=args.vision_video_fps,
                duration_seconds=result.get("duration_seconds"),
                transcript_segments_path=asr_result.get("segments_path"),
                caption=_caption_text(result),
                max_clips=args.vision_max_clips,
                max_clip_seconds=args.vision_max_clip_seconds,
                max_total_clip_seconds=args.vision_max_total_clip_seconds,
                clip_padding_seconds=args.vision_clip_padding_seconds,
                video_concurrency=args.vision_concurrency,
                upload_confirmed=args.confirm_cloud_upload,
                plan_only=args.vision_plan_only,
                force=args.force_reprocess,
                thinking=args.vision_thinking,
                precomputed_scene_times=scene_times,
            )
        except VisionInteractionError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    result["vision"] = vision_result
    timings['vision_seconds'] = round(time.monotonic()-stage_started, 3)
    timings['total_seconds'] = round(time.monotonic()-run_started, 3)
    result['timings'] = timings
    requested = [] if args.metadata_only else [stage for enabled, stage in (
        (args.asr != 'none', asr_result), (args.vision != 'none', vision_result)) if enabled]
    statuses = [stage.get('status') for stage in requested]
    result['status'] = ('failed' if 'failed' in statuses else
                        'partial' if any(s in ('partial', 'pending') for s in statuses) else
                        'planned' if 'planned' in statuses else
                        'skipped' if 'skipped' in statuses else 'done')
    if not args.metadata_only and result.get("video_path"):
        transcript_path = render_multimodal_transcript(
            result,
            Path(result["output_dir"]),
            asr_result=asr_result,
            vision_result=vision_result,
        )
        result["multimodal_transcript_path"] = str(transcript_path)
    _merge_metadata_processing(
        result.get("metadata_path"),
        asr_result,
        vision_result,
        result.get("multimodal_transcript_path"),
        media_probe,
        result['status'],
    )
    timings['total_seconds'] = round(time.monotonic()-run_started, 3)
    timing_path = Path(result['output_dir']) / 'timings.json'
    if timing_path.parent.is_dir():
        timing_path.write_text(json.dumps({'wall_clock': timings, 'vision_stages': vision_result.get('timings', {}),
            'status': result['status'], 'target_seconds': 600,
            'within_target': result['status'] == 'done' and timings['total_seconds'] <= 600}, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result['status'] == 'failed':
        return 1
    if result['status'] == 'partial':
        return 3
    return 0


def _merge_metadata_processing(
    metadata_path: str | None,
    asr_result: dict,
    vision_result: dict,
    multimodal_transcript_path: str | None,
    media_probe: dict | None,
    status: str | None = None,
) -> None:
    if not metadata_path:
        return
    path = Path(metadata_path)
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["asr"] = asr_result
    data["vision"] = vision_result
    if status is not None:
        data['status'] = status
    data["multimodal_transcript_path"] = multimodal_transcript_path
    if media_probe:
        data["media_probe"] = media_probe
        data['video'] = {**(data.get('video') or {}), **media_probe}
    data = sanitize_metadata_tree(data, artifact_root=path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _caption_text(result: dict) -> str:
    caption = str(result.get("post_caption") or result.get("caption") or "").strip()
    if caption:
        return caption
    value = result.get("post_caption_path") or result.get("caption_path")
    if not value:
        return ""
    try:
        return Path(value).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
