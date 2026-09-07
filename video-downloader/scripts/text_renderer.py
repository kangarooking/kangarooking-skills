"""Render downloader artifacts into a plain-text multimodal transcript."""

from __future__ import annotations

import json
from pathlib import Path


def render_multimodal_transcript(
    result: dict,
    output_dir: Path,
    *,
    asr_result: dict | None,
    vision_result: dict | None,
) -> Path:
    destination = output_dir / "multimodal_transcript.md"
    caption = _read_text(result.get("post_caption_path"))
    transcript = _read_text((asr_result or {}).get("transcript_path"))
    segments = _read_jsonl((asr_result or {}).get("segments_path"))
    notes = _read_jsonl((vision_result or {}).get("visual_notes_path"))
    clip_selection = _read_json((vision_result or {}).get("clip_selection_path"))
    title = caption.splitlines()[0].strip() if caption else result.get("id") or "视频资料"
    lines = [
        f"# {title}",
        "",
        "## 基本信息",
        "",
        f"- 平台：{result.get('platform') or 'unknown'}",
        f"- 作者：{result.get('author') or '未知'}",
        f"- 视频 ID：{result.get('id') or '未知'}",
        f"- 时长：{_duration(result.get('duration_seconds'))}",
        f"- 分辨率：{result.get('resolution') or '未知'}",
        f"- ASR 状态：{(asr_result or {}).get('status', '未运行')}",
        f"- 语音/字幕来源：{(asr_result or {}).get('backend', '未运行')}",
        f"- 视觉状态：{(vision_result or {}).get('status', '未运行')}",
        f"- 视觉模式：{(vision_result or {}).get('mode', '未指定')}",
        f"- 视觉模型：{(vision_result or {}).get('model', '未使用')}",
        f"- 分析类型：{(vision_result or {}).get('profile', '未指定')}",
        "",
    ]
    if caption:
        lines.extend(["## 平台原文案", "", caption, ""])
    lines.extend(["## 口播/对白", ""])
    lines.append(transcript or "（没有可用的音频转写。）")
    lines.extend(["", "## 视觉时间线", ""])
    if not notes:
        error = (vision_result or {}).get("error")
        lines.append(f"（没有可用的视觉理解结果。{error or ''}）")
    for note in notes:
        lines.extend(_render_note(note, output_dir, segments))
    clips = clip_selection.get("clips") if isinstance(clip_selection, dict) else None
    if isinstance(clips, list) and clips:
        lines.extend(["", "## Agent 选段", ""])
        lines.append(f"- 选段方式：{clip_selection.get('method') or '未知'}")
        for clip in clips:
            start_ms = int(clip.get("start_ms") or 0)
            end_ms = int(clip.get("end_ms") or start_ms)
            reasons = "；".join(clip.get("reasons") or []) or "未注明"
            lines.append(f"- {_timestamp(start_ms)}–{_timestamp(end_ms)}：{reasons}")
        duration_ms = int(float(result.get('duration_seconds') or 0) * 1000)
        gaps, cursor, covered = [], 0, 0
        for clip in sorted(clips, key=lambda c: c.get('start_ms', 0)):
            start = max(0, min(duration_ms, int(clip.get('start_ms') or 0)))
            end = max(start, min(duration_ms, int(clip.get('end_ms') or start)))
            if start > cursor:
                gaps.append((cursor, start))
            covered += max(0, end - max(cursor, start))
            cursor = max(cursor, end)
        if cursor < duration_ms:
            gaps.append((cursor, duration_ms))
        if duration_ms:
            lines.append(f"- 送入视觉模型的原视频范围：{covered / 1000:.2f} 秒，占全片 {covered / duration_ms:.1%}。这不是信息准确率或完整率。")
        if gaps:
            lines.extend(["", "### 未送入视觉模型的区间", "", "这些区间的文字仍可能包含在全文中，但画面没有经过本轮视觉核验；不能将无记录解释为无重要画面。", ""])
            lines.extend(f"- {_timestamp(start)}–{_timestamp(end)}" for start, end in gaps)
    errors = list((vision_result or {}).get("errors") or [])
    if result.get('scene_warning'):
        errors.append({'evidence_ids': ['场景扫描'], 'error': result['scene_warning']})
    if any(s.get('timestamp_precision') == 'chunk' for s in segments):
        errors.append({'evidence_ids': ['语音时间精度'], 'error': '云端ASR按音频块定位；同期口播包含重叠块的全文，不是词句级精确对齐。'})
    if (asr_result or {}).get('error'):
        errors.append({'evidence_ids': ['ASR'], 'error': asr_result['error']})
    for warning in (vision_result or {}).get('warnings') or []:
        errors.append({'evidence_ids': ['选段覆盖'], 'error': warning})
    for warning in (asr_result or {}).get('warnings') or []:
        errors.append({'evidence_ids': ['语音/字幕'], 'error': warning})
    if errors:
        lines.extend(["", "## 信息缺口", ""])
        for error in errors:
            evidence_ids = error.get("evidence_ids") or error.get("frame_ids") or []
            label = "、".join(evidence_ids)
            lines.append(f"- {label or '未知证据'}：{error.get('error') or '视觉分析失败'}")
    mode = (vision_result or {}).get("mode")
    evidence_description = {
        "keyframes": "“画面事实”“屏幕文字”“动作”来自对应时间点的关键帧。",
        "full-video": "“画面事实”“屏幕文字”“动作”来自压缩后的完整视频代理。",
        "agent-clips": "“画面事实”“屏幕文字”“动作”来自 Agent 选出的关键视频片段。",
    }.get(mode, "视觉观察来自对应的图片或视频证据。")
    lines.extend(
        [
            "",
            "## 证据与使用说明",
            "",
            f"- {evidence_description}",
            "- “模型推断”不是视频明示事实，后续使用时应结合原片复核。",
            "- 图片、片段与结构化记录仅用于追溯；下游可直接把本 Markdown 当普通文本处理。",
            "",
        ]
    )
    destination.write_text("\n".join(lines), encoding="utf-8")
    return destination


def _render_note(note: dict, output_dir: Path, segments: list[dict]) -> list[str]:
    timestamp_ms = int(note.get("timestamp_ms") or note.get("start_ms") or 0)
    end_ms = int(note.get("end_ms") or timestamp_ms)
    heading = _timestamp(timestamp_ms)
    if end_ms > timestamp_ms:
        heading += f"–{_timestamp(end_ms)}"
    lines = [f"### {heading}", ""]
    speech = _nearby_speech(timestamp_ms, segments, end_ms=end_ms)
    if speech:
        lines.extend(["**同期口播**", "", speech, ""])
    sections = (
        ("画面事实", note.get("visible_facts")),
        ("屏幕文字", note.get("screen_text")),
        ("动作", note.get("actions")),
        ("镜头与剪辑观察", note.get("shot_notes")),
        ("模型推断（需复核）", note.get("inferences")),
    )
    for heading, values in sections:
        if not values:
            continue
        lines.extend([f"**{heading}**", ""])
        lines.extend(f"- {value}" for value in values)
        lines.append("")
    evidence_value = note.get("frame_path") or note.get("video_path") or ""
    evidence_path = Path(str(evidence_value))
    if evidence_path.is_absolute():
        try:
            display_path = evidence_path.resolve().relative_to(output_dir.resolve())
        except (ValueError, OSError):
            display_path = Path(evidence_path.name)
    else:
        display_path = evidence_path
    confidence = note.get("confidence")
    suffix = f"；置信度 {confidence:.2f}" if isinstance(confidence, (int, float)) else ""
    evidence_kind = "视频" if note.get("evidence_kind") == "video" or note.get("video_path") else "关键帧"
    lines.extend([f"证据（{evidence_kind}）：`{display_path}`{suffix}", ""])
    return lines


def _nearby_speech(timestamp_ms: int, segments: list[dict], *, end_ms: int | None = None) -> str | None:
    # Video observations cover intervals; include every overlapping ASR segment.
    # A keyframe is a point, so retain the original one-second tolerance for it.
    interval = end_ms is not None and end_ms > timestamp_ms
    matches = []
    for segment in segments:
        start, end = segment.get("start_ms"), segment.get("end_ms")
        if not isinstance(start, int) or not isinstance(end, int) or end <= start:
            continue
        overlaps = start < end_ms and end > timestamp_ms if interval else start - 1000 <= timestamp_ms <= end + 1000
        if overlaps:
            text = str(segment.get("text") or "").strip()
            if text:
                matches.append((start, text))
            if not interval:
                break
    return "\n\n".join(text for _, text in sorted(matches, key=lambda item: item[0])) or None


def _read_text(value: str | None) -> str:
    if not value:
        return ""
    try:
        return Path(value).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _read_jsonl(value: str | None) -> list[dict]:
    if not value:
        return []
    records = []
    try:
        lines = Path(value).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _read_json(value: str | None) -> dict:
    if not value:
        return {}
    try:
        payload = json.loads(Path(value).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _timestamp(timestamp_ms: int) -> str:
    total_seconds = timestamp_ms // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = timestamp_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def _duration(value) -> str:
    try:
        return _timestamp(int(round(float(value) * 1000)))
    except (TypeError, ValueError):
        return "未知"
