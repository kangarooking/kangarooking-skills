"""Orchestrate the three approved visual-analysis modes."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Callable, TextIO

from .clip_selector import select_important_ranges, normalize_clip_ranges
from .clipper import cut_clips
from .doubao import (
    DOUBAO_DEFAULT_MODEL,
    DOUBAO_DEFAULT_VIDEO_MODEL,
    analyze_frames,
    analyze_video_files,
)
from .frame_sampler import detect_scene_timestamps, probe_duration, sample_frames
from .interaction import confirm_cloud_upload
from .planner import build_vision_plan, update_plan_confirmation, write_vision_plan
from .video_preparer import create_visual_proxy


def run_vision(
    video_path: Path,
    output_dir: Path,
    *,
    backend: str = "auto",
    mode: str = "keyframes",
    model: str = DOUBAO_DEFAULT_MODEL,
    video_model: str = DOUBAO_DEFAULT_VIDEO_MODEL,
    profile: str = "knowledge",
    interval_seconds: float = 10.0,
    max_frames: int = 24,
    scene_threshold: float = 0.32,
    batch_size: int = 4,
    prompt: str | None = None,
    video_fps: float = 0.5,
    duration_seconds: float | None = None,
    transcript_segments_path: Path | str | None = None,
    caption: str = "",
    max_clips: int = 8,
    max_clip_seconds: float = 600.0,
    max_total_clip_seconds: float = 0.0,
    clip_padding_seconds: float = 2.0,
    video_concurrency: int = 2,
    upload_confirmed: bool = False,
    plan_only: bool = False,
    interactive: bool | None = None,
    input_fn: Callable[[str], str] = input,
    output: TextIO | None = None,
    force: bool = False,
    thinking: str = 'disabled',
    precomputed_scene_times: list[float] | None = None,
) -> dict:
    if backend == "none":
        return {"status": "skipped", "backend": "none", "mode": mode, "frame_count": 0}
    selected_backend = "doubao" if backend == "auto" else backend
    if selected_backend != "doubao":
        return {
            "status": "failed",
            "backend": selected_backend,
            "mode": mode,
            "error": f"Unsupported vision backend: {selected_backend}",
        }
    stream = output or sys.stderr
    if mode == "keyframes":
        return _run_keyframes(
            video_path,
            output_dir,
            backend=selected_backend,
            model=model,
            profile=profile,
            interval_seconds=interval_seconds,
            max_frames=max_frames,
            scene_threshold=scene_threshold,
            batch_size=batch_size,
            prompt=prompt,
            upload_confirmed=upload_confirmed,
            plan_only=plan_only,
            interactive=interactive,
            input_fn=input_fn,
            output=stream,
        )
    if mode == "full-video":
        return _run_full_video(
            video_path,
            output_dir,
            backend=selected_backend,
            model=video_model,
            profile=profile,
            prompt=prompt,
            video_fps=video_fps,
            max_clip_seconds=max_clip_seconds,
            video_concurrency=video_concurrency,
            duration_seconds=duration_seconds,
            force=force,
            thinking=thinking,
            upload_confirmed=upload_confirmed,
            plan_only=plan_only,
            interactive=interactive,
            input_fn=input_fn,
            output=stream,
        )
    if mode == "agent-clips":
        return _run_agent_clips(
            video_path,
            output_dir,
            backend=selected_backend,
            selection_model=model,
            video_model=video_model,
            profile=profile,
            prompt=prompt,
            video_fps=video_fps,
            scene_threshold=scene_threshold,
            duration_seconds=duration_seconds,
            transcript_segments_path=transcript_segments_path,
            caption=caption,
            max_clips=max_clips,
            max_clip_seconds=max_clip_seconds,
            max_total_clip_seconds=max_total_clip_seconds,
            clip_padding_seconds=clip_padding_seconds,
            video_concurrency=video_concurrency,
            force=force,
            thinking=thinking,
            precomputed_scene_times=precomputed_scene_times,
            upload_confirmed=upload_confirmed,
            plan_only=plan_only,
            interactive=interactive,
            input_fn=input_fn,
            output=stream,
        )
    return {
        "status": "failed",
        "backend": selected_backend,
        "mode": mode,
        "error": f"Unsupported vision mode: {mode}",
    }


def _run_keyframes(
    video_path: Path,
    output_dir: Path,
    *,
    backend: str,
    model: str,
    profile: str,
    interval_seconds: float,
    max_frames: int,
    scene_threshold: float,
    batch_size: int,
    prompt: str | None,
    upload_confirmed: bool,
    plan_only: bool,
    interactive: bool | None,
    input_fn: Callable[[str], str],
    output: TextIO,
) -> dict:
    try:
        frames, sampling = sample_frames(
            video_path,
            output_dir,
            interval_seconds=interval_seconds,
            max_frames=max_frames,
            scene_threshold=scene_threshold,
        )
    except RuntimeError as exc:
        return {"status": "failed", "backend": backend, "mode": "keyframes", "error": str(exc), "frame_count": 0}
    frames_path = output_dir / "frames.jsonl"
    _write_jsonl(frames_path, _portable_records(frames, output_dir))
    upload_items = [
        {
            "kind": "image",
            "id": frame.get("id"),
            "path": frame.get("path"),
            "size_bytes": _size(frame.get("path")),
            "duration_seconds": 0,
            "start_ms": frame.get("timestamp_ms"),
            "end_ms": frame.get("timestamp_ms"),
        }
        for frame in frames
    ]
    if prompt:
        upload_items.append(
            {"kind": "text", "label": "custom vision prompt", "character_count": len(prompt)}
        )
    plan = build_vision_plan(
        mode="keyframes",
        backend=backend,
        model=model,
        profile=profile,
        source_path=video_path,
        upload_items=upload_items,
        limitations=["关键帧之间的动作、转场和短暂画面可能缺失。"],
    )
    plan_path = write_vision_plan(output_dir, plan)
    base = {
        "backend": backend,
        "mode": "keyframes",
        "model": model,
        "profile": profile,
        "frame_count": len(frames),
        "frames_path": str(frames_path),
        "vision_plan_path": str(plan_path),
        "sampling": sampling,
    }
    if plan_only:
        confirm_cloud_upload(
            plan,
            confirmed=upload_confirmed,
            plan_only=True,
            interactive=interactive,
            input_fn=input_fn,
            output=output,
        )
        update_plan_confirmation(plan, confirmed=False, status="planned")
        write_vision_plan(output_dir, plan)
        return {**base, "status": "planned", "visual_notes_path": None}
    if not os.environ.get("ARK_API_KEY"):
        return {
            **base,
            "status": "partial",
            "visual_notes_path": None,
            "error": "ARK_API_KEY is not set; keyframes and the upload plan were created, but nothing was uploaded.",
        }
    allowed = confirm_cloud_upload(
        plan,
        confirmed=upload_confirmed,
        plan_only=plan_only,
        interactive=interactive,
        input_fn=input_fn,
        output=output,
    )
    if not allowed:
        status = "planned" if plan_only else "skipped"
        update_plan_confirmation(plan, confirmed=False, status=status)
        write_vision_plan(output_dir, plan)
        return {**base, "status": status, "visual_notes_path": None}
    update_plan_confirmation(plan, confirmed=True, status="in_progress")
    write_vision_plan(output_dir, plan)
    notes, errors = analyze_frames(
        frames,
        model=model,
        profile=profile,
        custom_prompt=prompt,
        batch_size=batch_size,
    )
    notes_path = output_dir / "visual_notes.jsonl"
    _write_jsonl(notes_path, _portable_records(notes, output_dir))
    status = _analysis_status(notes, errors)
    update_plan_confirmation(plan, confirmed=True, status=status)
    write_vision_plan(output_dir, plan)
    return {
        **base,
        "status": status,
        "analyzed_frame_count": len(notes),
        "visual_notes_path": str(notes_path),
        "errors": errors,
    }


def _run_full_video(
    video_path: Path,
    output_dir: Path,
    *,
    backend: str,
    model: str,
    profile: str,
    prompt: str | None,
    video_fps: float,
    upload_confirmed: bool,
    plan_only: bool,
    interactive: bool | None,
    input_fn: Callable[[str], str],
    output: TextIO,
    max_clip_seconds: float = 600,
    video_concurrency: int = 2,
    duration_seconds: float | None = None,
    force: bool = False,
    thinking: str = 'disabled',
) -> dict:
    try:
        duration = float(duration_seconds or probe_duration(video_path))
        if duration > max_clip_seconds:
            ranges, _ = normalize_clip_ranges(
                [{'start_ms': 0, 'end_ms': round(duration * 1000), 'reason': '完整视频覆盖'}],
                duration_seconds=duration, padding_seconds=0, max_seconds=max_clip_seconds,
                max_total_seconds=0, add_sentinels=False)
            chunks = cut_clips(video_path, output_dir, ranges)
            proxy = {'path': None, 'chunked': True}
        else:
            proxy = create_visual_proxy(video_path, output_dir)
            chunks = [{'id': 'full-video-proxy', 'path': proxy['path'],
                       'start_ms': 0, 'end_ms': round(duration * 1000),
                       'media_probe': proxy.get('media_probe') or {}}]
    except RuntimeError as exc:
        return {"status": "failed", "backend": backend, "mode": "full-video", "model": model, "error": str(exc)}
    items = []
    for chunk in chunks:
        media = chunk.get('media_probe') or {}
        items.append({**chunk, 'kind': 'video', 'size_bytes': media.get('size_bytes') or _size(chunk['path']),
                      'duration_seconds': media.get('duration_seconds') or (chunk['end_ms']-chunk['start_ms'])/1000,
                      'contains_audio': bool(media.get('has_audio')), 'preprocess_fps': video_fps})
    upload_items = list(items)
    if prompt:
        upload_items.append(
            {"kind": "text", "label": "custom vision prompt", "character_count": len(prompt)}
        )
    plan = build_vision_plan(
        mode="full-video",
        backend=backend,
        model=model,
        profile=profile,
        source_path=video_path,
        upload_items=upload_items,
        limits={'max_clip_seconds': max_clip_seconds, 'video_concurrency': video_concurrency},
        limitations=[
            "上传的是 720p H.264 视觉代理；源视频含音轨时保留 AAC。压缩可能损失微小文字或极快动作细节。",
            f"模型预处理按 {video_fps:g} fps 采样，不等于逐帧观看，短动作与快速转场仍可能缺失。",
        ],
    )
    plan_path = write_vision_plan(output_dir, plan)
    base = {
        "backend": backend,
        "mode": "full-video",
        "model": model,
        "profile": profile,
        "proxy_path": proxy["path"],
        "proxy": proxy,
        "clip_count": len(items),
        "video_concurrency": video_concurrency,
        "vision_plan_path": str(plan_path),
        "frame_count": 0,
    }
    if plan_only:
        confirm_cloud_upload(
            plan,
            confirmed=upload_confirmed,
            plan_only=True,
            interactive=interactive,
            input_fn=input_fn,
            output=output,
        )
        update_plan_confirmation(plan, confirmed=False, status="planned")
        write_vision_plan(output_dir, plan)
        return {**base, "status": "planned", "visual_notes_path": None}
    if not os.environ.get("ARK_API_KEY"):
        return {
            **base,
            "status": "partial",
            "visual_notes_path": None,
            "error": "ARK_API_KEY is not set; the complete-video proxy and upload plan were created, but nothing was uploaded.",
        }
    allowed = confirm_cloud_upload(
        plan,
        confirmed=upload_confirmed,
        plan_only=plan_only,
        interactive=interactive,
        input_fn=input_fn,
        output=output,
    )
    if not allowed:
        status = "planned" if plan_only else "skipped"
        update_plan_confirmation(plan, confirmed=False, status=status)
        write_vision_plan(output_dir, plan)
        return {**base, "status": status, "visual_notes_path": None}
    update_plan_confirmation(plan, confirmed=True, status="in_progress")
    write_vision_plan(output_dir, plan)
    notes, errors = analyze_video_files(
        items,
        model=model,
        profile=profile,
        custom_prompt=prompt,
        fps=video_fps,
        concurrency=video_concurrency,
        cache_dir=output_dir / 'vision' / 'analysis-cache',
        force=force,
        thinking=thinking,
        progress=lambda message: print(message, file=output, flush=True),
    )
    notes_path = output_dir / "visual_notes.jsonl"
    _write_jsonl(notes_path, _portable_records(notes, output_dir))
    status = _analysis_status(notes, errors)
    update_plan_confirmation(plan, confirmed=True, status=status)
    write_vision_plan(output_dir, plan)
    return {**base, "status": status, "visual_notes_path": str(notes_path), "errors": errors}


def _run_agent_clips(
    video_path: Path,
    output_dir: Path,
    *,
    backend: str,
    selection_model: str,
    video_model: str,
    profile: str,
    prompt: str | None,
    video_fps: float,
    scene_threshold: float,
    duration_seconds: float | None,
    transcript_segments_path: Path | str | None,
    caption: str,
    max_clips: int,
    max_clip_seconds: float,
    max_total_clip_seconds: float,
    clip_padding_seconds: float,
    video_concurrency: int,
    upload_confirmed: bool,
    plan_only: bool,
    interactive: bool | None,
    input_fn: Callable[[str], str],
    output: TextIO,
    force: bool = False,
    thinking: str = 'disabled',
    precomputed_scene_times: list[float] | None = None,
) -> dict:
    timings = {}
    started = time.monotonic()
    try:
        duration = float(duration_seconds or probe_duration(video_path))
        scene_times = precomputed_scene_times if precomputed_scene_times is not None else detect_scene_timestamps(
            video_path, scene_threshold=scene_threshold, cache_dir=output_dir / 'vision' / 'scene-cache', force=force)
        timings['scene_seconds'] = round(time.monotonic() - started, 3)
    except RuntimeError as exc:
        return {"status": "failed", "backend": backend, "mode": "agent-clips", "error": str(exc)}
    segments = _read_jsonl(transcript_segments_path)
    timestamped = [
        item
        for item in segments
        if isinstance(item.get("start_ms"), int)
        and isinstance(item.get("end_ms"), int)
        and item["end_ms"] > item["start_ms"]
        and str(item.get("text") or "").strip()
    ]
    transcript_chars = sum(len(str(item.get("text") or "")) for item in timestamped)
    limits = {
        "max_clips": max_clips,
        "max_clip_seconds": max_clip_seconds,
        "max_total_seconds": max_total_clip_seconds,
        "padding_seconds": clip_padding_seconds,
        "video_concurrency": video_concurrency,
    }
    selection_items = []
    limitations = []
    if timestamped:
        limitations.append("初选有未覆盖区间时，最多追加一次使用相同来源文案的遗漏复核；不是全片逐帧核验。")
        selection_items.extend(
            [
                {"kind": "transcript", "label": "timestamped transcript", "character_count": transcript_chars},
                {"kind": "caption", "label": "platform caption", "character_count": len(caption)},
                {"kind": "text", "label": "scene timestamps", "character_count": len(json.dumps(scene_times))},
            ]
        )
        if prompt:
            selection_items.append(
                {"kind": "text", "label": "custom vision prompt", "character_count": len(prompt)}
            )
    else:
        limitations.append("没有可靠的时间戳文案；将使用场景切换与首尾哨兵做本地兜底选段。")
    selection_plan = build_vision_plan(
        mode="agent-clips",
        stage="selection",
        backend=backend,
        model=selection_model,
        profile=profile,
        source_path=video_path,
        upload_items=selection_items,
        limits=limits,
        limitations=limitations,
    )
    selection_plan_path = write_vision_plan(output_dir, selection_plan, filename="vision_selection_plan.json")
    base = {
        "backend": backend,
        "mode": "agent-clips",
        "model": video_model,
        "selection_model": selection_model,
        "profile": profile,
        "stage": "selection",
        "selection_plan_path": str(selection_plan_path),
        "frame_count": 0,
    }
    if plan_only and timestamped:
        confirm_cloud_upload(
            selection_plan,
            confirmed=upload_confirmed,
            plan_only=True,
            interactive=interactive,
            input_fn=input_fn,
            output=output,
        )
        update_plan_confirmation(selection_plan, confirmed=False, status="planned")
        write_vision_plan(output_dir, selection_plan, filename="vision_selection_plan.json")
        return {**base, "status": "planned", "vision_plan_path": str(selection_plan_path), "visual_notes_path": None}
    if timestamped:
        if not os.environ.get("ARK_API_KEY"):
            return {
                **base,
                "status": "partial",
                "vision_plan_path": str(selection_plan_path),
                "visual_notes_path": None,
                "error": "ARK_API_KEY is not set; the Agent selection plan was created, but the timestamped transcript was not uploaded.",
            }
        selection_allowed = confirm_cloud_upload(
            selection_plan,
            confirmed=upload_confirmed,
            plan_only=False,
            interactive=interactive,
            input_fn=input_fn,
            output=output,
        )
        if not selection_allowed:
            update_plan_confirmation(selection_plan, confirmed=False, status="skipped")
            write_vision_plan(output_dir, selection_plan, filename="vision_selection_plan.json")
            return {**base, "status": "skipped", "vision_plan_path": str(selection_plan_path), "visual_notes_path": None}
        update_plan_confirmation(selection_plan, confirmed=True, status="in_progress")
        write_vision_plan(output_dir, selection_plan, filename="vision_selection_plan.json")
    try:
        started = time.monotonic()
        clips, warnings, selection_method = select_important_ranges(
            transcript_segments=segments,
            caption=caption,
            duration_seconds=duration,
            scene_timestamps=scene_times,
            model=selection_model,
            profile=profile,
            custom_prompt=prompt,
            padding_seconds=clip_padding_seconds,
            max_seconds=max_clip_seconds,
            max_clips=max_clips,
            max_total_seconds=max_total_clip_seconds,
            cache_dir=output_dir / 'vision' / 'selection-cache',
            force=force,
            thinking=thinking,
            progress=lambda message: print(message, file=output, flush=True),
        )
        timings['selection_seconds'] = round(time.monotonic() - started, 3)
        print(f"选段完成（{timings['selection_seconds']}秒），开始准备 {len(clips)} 个本地视频片段", file=output, flush=True)
        started = time.monotonic()
        clip_items = cut_clips(video_path, output_dir, clips)
        timings['clip_preparation_seconds'] = round(time.monotonic() - started, 3)
        print(f"切片准备完成（{timings['clip_preparation_seconds']}秒）", file=output, flush=True)
    except RuntimeError as exc:
        if timestamped:
            update_plan_confirmation(selection_plan, confirmed=True, status="failed")
            write_vision_plan(output_dir, selection_plan, filename="vision_selection_plan.json")
        return {**base, "status": "failed", "vision_plan_path": str(selection_plan_path), "error": str(exc)}
    if timestamped:
        update_plan_confirmation(selection_plan, confirmed=True, status="done")
        write_vision_plan(output_dir, selection_plan, filename="vision_selection_plan.json")
    else:
        update_plan_confirmation(selection_plan, confirmed=False, status="done")
        write_vision_plan(output_dir, selection_plan, filename="vision_selection_plan.json")
    selection_path = output_dir / "clip_selection.json"
    selection_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "method": selection_method,
                "scene_timestamps": scene_times,
                "warnings": warnings,
                "clips": _portable_records(clip_items, output_dir),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    upload_items = []
    for item in clip_items:
        media = item.get("media_probe") or {}
        upload_items.append(
            {
                "kind": "video",
                "id": item.get("id"),
                "path": item.get("path"),
                "size_bytes": media.get("size_bytes") or _size(item.get("path")),
                "duration_seconds": media.get("duration_seconds") or item.get("duration_ms", 0) / 1000,
                "start_ms": item.get("start_ms"),
                "end_ms": item.get("end_ms"),
                "contains_audio": bool(media.get("has_audio")),
                "preprocess_fps": video_fps,
            }
        )
    if prompt:
        upload_items.append(
            {"kind": "text", "label": "custom vision prompt", "character_count": len(prompt)}
        )
    plan = build_vision_plan(
        mode="agent-clips",
        stage="clip-analysis",
        backend=backend,
        model=video_model,
        profile=profile,
        source_path=video_path,
        upload_items=upload_items,
        limits=limits,
        limitations=[
            *warnings,
            f"视频片段在源含音轨时保留 AAC；模型预处理按 {video_fps:g} fps 采样，不等于逐帧观看。",
            f"最多同时分析 {video_concurrency} 个视频片段；每个片段仍独立上传、分析和删除。",
        ],
    )
    plan_path = write_vision_plan(output_dir, plan)
    prepared = {
        **base,
        "timings": timings,
        "selected_duration_seconds": sum(c['end_ms'] - c['start_ms'] for c in clips) / 1000,
        "selection_coverage": round(sum(c['end_ms'] - c['start_ms'] for c in clips) / (duration * 1000), 4),
        "stage": "clip-analysis",
        "selection_method": selection_method,
        "clip_count": len(clip_items),
        "clip_selection_path": str(selection_path),
        "vision_plan_path": str(plan_path),
        "warnings": warnings,
        "video_concurrency": video_concurrency,
    }
    if plan_only:
        confirm_cloud_upload(
            plan,
            confirmed=upload_confirmed,
            plan_only=True,
            interactive=interactive,
            input_fn=input_fn,
            output=output,
        )
        update_plan_confirmation(plan, confirmed=False, status="planned")
        write_vision_plan(output_dir, plan)
        return {**prepared, "status": "planned", "visual_notes_path": None}
    if not os.environ.get("ARK_API_KEY"):
        return {
            **prepared,
            "status": "partial",
            "visual_notes_path": None,
            "error": "ARK_API_KEY is not set; clips were prepared locally but not uploaded.",
        }
    clips_allowed = confirm_cloud_upload(
        plan,
        confirmed=upload_confirmed,
        plan_only=False,
        interactive=interactive,
        input_fn=input_fn,
        output=output,
    )
    if not clips_allowed:
        update_plan_confirmation(plan, confirmed=False, status="skipped")
        write_vision_plan(output_dir, plan)
        return {**prepared, "status": "skipped", "visual_notes_path": None}
    update_plan_confirmation(plan, confirmed=True, status="in_progress")
    write_vision_plan(output_dir, plan)
    notes, errors = analyze_video_files(
        clip_items,
        model=video_model,
        profile=profile,
        custom_prompt=prompt,
        fps=video_fps,
        concurrency=video_concurrency,
        cache_dir=output_dir / 'vision' / 'analysis-cache',
        force=force,
        thinking=thinking,
        progress=lambda message: print(message, file=output, flush=True),
    )
    notes_path = output_dir / "visual_notes.jsonl"
    _write_jsonl(notes_path, _portable_records(notes, output_dir))
    status = _analysis_status(notes, errors)
    update_plan_confirmation(plan, confirmed=True, status=status)
    write_vision_plan(output_dir, plan)
    return {**prepared, "status": status, "visual_notes_path": str(notes_path), "errors": errors}


def _analysis_status(notes: list[dict], errors: list[dict]) -> str:
    if notes and not errors:
        return "done"
    if notes:
        return "partial"
    return "failed"


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path | str | None) -> list[dict]:
    if not path:
        return []
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    records = []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _size(path: str | Path | None) -> int:
    if not path:
        return 0
    try:
        return Path(path).stat().st_size
    except OSError:
        return 0


def _portable_records(records: list[dict], output_dir: Path) -> list[dict]:
    normalized = []
    for record in records:
        item = dict(record)
        for key in ("path", "frame_path", "video_path"):
            value = item.get(key)
            if not value:
                continue
            path = Path(str(value))
            try:
                item[key] = path.resolve().relative_to(output_dir.resolve()).as_posix()
            except (OSError, ValueError):
                item[key] = path.name
        normalized.append(item)
    return normalized
