"""Build Agent clip-selection prompts and validate untrusted time ranges."""

from __future__ import annotations

import math
import json
from pathlib import Path
from .cache import result_path, read_result, write_result


def build_selection_prompt(
    *,
    transcript_segments: list[dict],
    caption: str,
    duration_seconds: float,
    scene_timestamps: list[float],
    profile: str,
    custom_prompt: str | None,
    max_clips: int,
    max_total_seconds: float,
) -> str:
    transcript = "\n".join(
        json.dumps({'start_ms': item.get('start_ms'), 'end_ms': item.get('end_ms'),
                    'precision': item.get('timestamp_precision', 'segment'),
                    'text': str(item.get('text') or '').strip()}, ensure_ascii=False)
        for item in transcript_segments
        if str(item.get("text") or "").strip()
    ) or "（没有可用的时间戳转写。）"
    scenes = ", ".join(f"{float(value):.3f}s" for value in scene_timestamps) or "无"
    extra = f"\n额外要求：{custom_prompt}" if custom_prompt else ""
    return (
        "你是视频分析 Agent。请根据完整时间戳文案、平台文案、视频时长和场景切换时间点，"
        "选择最值得交给视觉模型复核的视频区间。不要只选口播密集处：没有口播的静默演示、"
        "B-roll、MV 表演、产品 UI、转场和画面反转也可能重要。必须覆盖开头钩子与结尾/CTA，"
        "除非候选区间已覆盖。不得虚构文案中没有的时间点。"
        "文案已提供原始毫秒数，选段直接引用对应内容的 start_ms/end_ms；不要凭记忆估计时间或把不同段落的证据错配。"
        "先检查完整文案中的独立制作技法、装置、操作演示与结果对比，每种关键方法应有代表片段；"
        "不要用重复产品卖点或普通口播挤掉不同方法的演示。开头与结尾保留必要上下文即可，"
        "重复广告只需选一次。区间不足时可合并相邻关联演示，不要为了凑满数量漏掉后半段新方法。"
        f"\n分析类型：{profile}"
        f"\n视频时长：{duration_seconds:.3f}s"
        f"\n最多区间：{max_clips}"
        f"\n总时长上限：{max_total_seconds:.3f}s（0表示不额外限制，按需选择重要区间）"
        f"\n平台文案：\n{caption or '（无）'}"
        f"\n场景切换时间点：{scenes}"
        f"\n完整时间戳文案：\n{transcript}"
        f"{extra}\n"
        "只返回 JSON，不要 Markdown："
        '{"clips":[{"start_ms":0,"end_ms":10000,"reason":"为什么重要",'
        '"evidence":"对应文案或场景信号","priority":1}]}。priority 为 1–10，10 最高。'
        '每段reason与evidence各用一句短句，不复制大段原文。带chunk时间精度的转写仅定位音频块，不能据此推断词句的精确时刻。'
    )


def select_important_ranges(
    *,
    transcript_segments: list[dict],
    caption: str,
    duration_seconds: float,
    scene_timestamps: list[float],
    model: str,
    profile: str,
    custom_prompt: str | None,
    padding_seconds: float = 2.0,
    min_seconds: float = 4.0,
    max_seconds: float = 600.0,
    max_clips: int = 8,
    max_total_seconds: float = 0.0,
    cache_dir: Path | None = None,
    force: bool = False,
    thinking: str = 'disabled',
    progress=None,
) -> tuple[list[dict], list[str], str]:
    """Ask Doubao to select ranges, with an honest scene-only fallback."""
    timestamped = [
        item
        for item in transcript_segments
        if isinstance(item.get("start_ms"), int)
        and isinstance(item.get("end_ms"), int)
        and item["end_ms"] > item["start_ms"]
        and str(item.get("text") or "").strip()
    ]
    if not timestamped:
        raw = [
            {
                "start_ms": max(0, int(round(seconds * 1000)) - 2500),
                "end_ms": int(round(seconds * 1000)) + 2500,
                "reason": "场景切换兜底候选",
                "evidence": f"scene@{seconds:.3f}s",
                "priority": 5,
            }
            for seconds in scene_timestamps
        ]
        clips, warnings = normalize_clip_ranges(
            raw,
            duration_seconds=duration_seconds,
            padding_seconds=0,
            min_seconds=min_seconds,
            max_seconds=max_seconds,
            max_clips=max_clips,
            max_total_seconds=max_total_seconds,
        )
        warnings.insert(
            0,
            "No timestamped transcript was available; clips were selected from scene changes and sentinels, not by the Agent model.",
        )
        return clips, warnings, "scene-fallback"
    prompt = build_selection_prompt(
        transcript_segments=timestamped,
        caption=caption,
        duration_seconds=duration_seconds,
        scene_timestamps=scene_timestamps,
        profile=profile,
        custom_prompt=custom_prompt,
        max_clips=max_clips,
        max_total_seconds=max_total_seconds,
    )
    from .doubao import request_text_json

    def request_selection(prompt_text):
        try:
            return request_text_json(prompt_text, model=model, thinking=thinking)
        except RuntimeError as exc:
            if 'not a valid JSON object' not in str(exc):
                raise
            if progress: progress('Agent：返回格式无效，按严格 JSON 格式重试一次')
            return request_text_json(prompt_text + '\n格式纠正：必须返回合法JSON；键名使用双引号，键值之间用冒号，'
                '例如 {"clips":[{"start_ms":0,"end_ms":1000,"reason":"演示","evidence":"原文","priority":9}]}。'
                '不要用等号代替冒号。只输出对象，不加解释。', model=model, thinking=thinking)

    checkpoint = result_path(cache_dir, {'model': model, 'prompt': prompt, 'thinking': thinking, 'version': 3}) if cache_dir else None
    payload = read_result(checkpoint) if checkpoint and not force else None
    if not payload:
        if progress: progress('Agent：分析完整文案，生成初步选段')
        payload = request_selection(prompt)
        # One bounded review only when the first plan leaves source time unexamined.
        # Review the same source text, not invented word-level evidence or a fixed time budget.
        initial = None
        raw = payload.get('clips')
        if isinstance(raw, list):
            initial, _ = normalize_clip_ranges(raw, duration_seconds=duration_seconds,
                padding_seconds=padding_seconds, min_seconds=min_seconds, max_seconds=max_seconds,
                max_clips=max_clips, max_total_seconds=max_total_seconds)
        if initial and sum(c['end_ms']-c['start_ms'] for c in initial) < int(duration_seconds*1000):
            if progress: progress('Agent：复核未选区间中的独立方法与演示，最多一次')
            audit_prompt = (prompt + '\n\n初步候选方案：' + json.dumps(raw, ensure_ascii=False) +
                '\n现在进行一次遗漏复核：检查候选之外的完整文案，特别是后半段，是否有尚未覆盖的独立制作技法、'
                '操作演示、道具制作、搭景或结果对比。优先用这些替换重复广告/纯口播片段，必要时合并相邻关联区间。'
                '不要无理由缩短或删去已有核心演示，不要求固定覆盖比例。返回复核后的完整clips方案（不是只返回新增项），'
                '仍遵守最多区间数和原有JSON格式。若无遗漏，原样返回初步方案。')
            reviewed = request_selection(audit_prompt)
            if not isinstance(reviewed.get('clips'), list) or not reviewed['clips']:
                raise RuntimeError('Agent coverage review did not return a complete clips plan.')
            payload = reviewed
            payload['coverage_reviewed'] = True
    elif progress:
        progress('Agent：复用已完成的选段及遗漏复核')
    raw_ranges = payload.get("clips")
    if not isinstance(raw_ranges, list):
        raise RuntimeError("Doubao Agent selection response did not include a clips array.")
    clips, warnings = normalize_clip_ranges(
        raw_ranges,
        duration_seconds=duration_seconds,
        padding_seconds=padding_seconds,
        min_seconds=min_seconds,
        max_seconds=max_seconds,
        max_clips=max_clips,
        max_total_seconds=max_total_seconds,
    )
    if not clips:
        raise RuntimeError("Doubao Agent selection did not produce any usable clip ranges.")
    if checkpoint:
        write_result(checkpoint, payload)
    return clips, warnings, "agent"


def normalize_clip_ranges(
    raw_ranges: list[dict],
    *,
    duration_seconds: float,
    padding_seconds: float = 2.0,
    min_seconds: float = 4.0,
    max_seconds: float = 600.0,
    merge_gap_seconds: float = 1.0,
    max_clips: int = 8,
    max_total_seconds: float = 0.0,
    add_sentinels: bool = True,
) -> tuple[list[dict], list[str]]:
    """Clamp, pad, merge, split and budget untrusted Agent ranges."""
    limits = (duration_seconds, padding_seconds, min_seconds, max_seconds,
              merge_gap_seconds, max_total_seconds)
    if (any(not math.isfinite(value) for value in limits)
            or min_seconds <= 0 or max_seconds < min_seconds
            or max_total_seconds < 0 or max_clips < 1):
        raise RuntimeError("Invalid clip limits: require finite positive limits, and total seconds >= 0 (0 means unlimited).")
    duration_ms = max(0, int(round(float(duration_seconds) * 1000)))
    if duration_ms <= 0:
        raise RuntimeError("Video duration must be greater than zero for Agent clip selection.")
    padding_ms = max(0, int(round(padding_seconds * 1000)))
    min_ms = max(1, int(round(min_seconds * 1000)))
    max_ms = max(min_ms, int(round(max_seconds * 1000)))
    merge_gap_ms = max(0, int(round(merge_gap_seconds * 1000)))
    budget_ms = duration_ms if max_total_seconds == 0 else int(round(max_total_seconds * 1000))
    if not math.isfinite(max_seconds) or max_seconds < min_seconds or max_clips < 1 or budget_ms <= 0:
        raise RuntimeError("Invalid clip limits: require positive limits, and total seconds >= 0 (0 means unlimited).")
    warnings: list[str] = []
    candidates: list[dict] = []
    for index, raw in enumerate(raw_ranges):
        if not isinstance(raw, dict):
            warnings.append(f"clip[{index}] was not an object and was ignored")
            continue
        start = _finite_number(raw.get("start_ms"))
        end = _finite_number(raw.get("end_ms"))
        if start is None or end is None or start >= end:
            warnings.append(f"clip[{index}] had invalid bounds and was ignored")
            continue
        raw_start_ms = int(round(start))
        raw_end_ms = int(round(end))
        if raw_end_ms <= 0 or raw_start_ms >= duration_ms:
            warnings.append(f"clip[{index}] was completely outside the video and was ignored")
            continue
        start_ms = max(0, min(duration_ms, raw_start_ms - padding_ms))
        end_ms = max(0, min(duration_ms, raw_end_ms + padding_ms))
        start_ms, end_ms = _ensure_minimum(start_ms, end_ms, min_ms, duration_ms)
        if start_ms >= end_ms:
            warnings.append(f"clip[{index}] became empty after normalization and was ignored")
            continue
        candidates.append(
            {
                "start_ms": start_ms,
                "end_ms": end_ms,
                "reasons": _string_values(raw.get("reason")),
                "evidence": _string_values(raw.get("evidence")),
                "priority": _priority(raw.get("priority")),
                "sentinel": False,
            }
        )
    candidates.sort(key=lambda item: (item["start_ms"], item["end_ms"]))
    merged = _merge_ranges(candidates, merge_gap_ms)
    if add_sentinels:
        sentinel_ms = min(max_ms, max(min_ms, min(8000, duration_ms)))
        if not any(item["start_ms"] <= min(2000, duration_ms) for item in merged):
            merged.append(_sentinel(0, sentinel_ms, "开头哨兵"))
        if not any(item["end_ms"] >= max(0, duration_ms - 2000) for item in merged):
            merged.append(_sentinel(max(0, duration_ms - sentinel_ms), duration_ms, "结尾哨兵"))
        merged = _merge_ranges(sorted(merged, key=lambda item: item["start_ms"]), merge_gap_ms)
    # Limit candidate intervals before splitting; execution chunks must not be dropped.
    budgeted = _apply_budget(merged, max_clips=max_clips, budget_ms=budget_ms, min_ms=min_ms)
    for item in merged:
        covered = sorted((max(item['start_ms'], x['start_ms']), min(item['end_ms'], x['end_ms']))
                         for x in budgeted if x['end_ms'] > item['start_ms'] and x['start_ms'] < item['end_ms'])
        cursor = item['start_ms']
        for start, end in covered:
            if start > cursor:
                warnings.append(f"Unselected by explicit duration/candidate limits: {cursor}–{start} ms")
            cursor = max(cursor, end)
        if cursor < item['end_ms']:
            warnings.append(f"Unselected by explicit duration/candidate limits: {cursor}–{item['end_ms']} ms")
    selected = []
    for item in budgeted:
        selected.extend(_split_range(item, min_ms=min_ms, max_ms=max_ms))
    selected.sort(key=lambda item: (item["start_ms"], item["end_ms"]))
    result = []
    for index, item in enumerate(selected, start=1):
        result.append(
            {
                "id": f"clip-{index:03d}",
                "start_ms": item["start_ms"],
                "end_ms": item["end_ms"],
                "duration_ms": item["end_ms"] - item["start_ms"],
                "reasons": item["reasons"],
                "evidence": item["evidence"],
                "priority": item["priority"],
                "sentinel": bool(item.get("sentinel")),
            }
        )
    return result, warnings


def _merge_ranges(items: list[dict], gap_ms: int) -> list[dict]:
    merged: list[dict] = []
    for item in items:
        if not merged or item["start_ms"] > merged[-1]["end_ms"] + gap_ms:
            merged.append({**item})
            continue
        previous = merged[-1]
        previous["end_ms"] = max(previous["end_ms"], item["end_ms"])
        previous["reasons"] = _dedupe([*previous["reasons"], *item["reasons"]])
        previous["evidence"] = _dedupe([*previous["evidence"], *item["evidence"]])
        previous["priority"] = max(previous["priority"], item["priority"])
        previous["sentinel"] = bool(previous.get("sentinel") or item.get("sentinel"))
    return merged


def _split_range(item: dict, *, min_ms: int, max_ms: int) -> list[dict]:
    duration = item["end_ms"] - item["start_ms"]
    if duration <= max_ms:
        return [{**item}]
    boundaries = [item["start_ms"]]
    while item["end_ms"] - boundaries[-1] > max_ms:
        boundaries.append(boundaries[-1] + max_ms)
    boundaries.append(item["end_ms"])
    final_duration = boundaries[-1] - boundaries[-2]
    if final_duration < min_ms and len(boundaries) > 2:
        borrow = min_ms - final_duration
        previous_duration = boundaries[-2] - boundaries[-3]
        if previous_duration - borrow >= min_ms:
            boundaries[-2] -= borrow
    children = []
    for index in range(len(boundaries) - 1):
        child = {
            **item,
            "start_ms": boundaries[index],
            "end_ms": boundaries[index + 1],
            "reasons": [*item["reasons"], f"长区间第 {index + 1} 段"],
        }
        children.append(child)
    return children


def _apply_budget(items: list[dict], *, max_clips: int, budget_ms: int, min_ms: int) -> list[dict]:
    ordered = sorted(
        items,
        key=lambda item: (
            0 if item.get("sentinel") else 1,
            -int(item.get("priority") or 0),
            item["start_ms"],
        ),
    )
    selected: list[dict] = []
    used = 0
    candidate_count = 0
    for item in ordered:
        if not item.get('sentinel') and candidate_count >= max(1, max_clips):
            continue
        duration = item["end_ms"] - item["start_ms"]
        remaining = budget_ms - used
        if remaining <= 0:
            break
        if duration > remaining:
            if remaining < min_ms:
                continue
            item = {**item, "end_ms": item["start_ms"] + remaining}
            duration = remaining
        selected.append(item)
        if not item.get('sentinel'):
            candidate_count += 1
        used += duration
    return selected


def _ensure_minimum(start_ms: int, end_ms: int, minimum_ms: int, duration_ms: int) -> tuple[int, int]:
    if end_ms - start_ms >= minimum_ms or duration_ms <= minimum_ms:
        return start_ms, end_ms
    missing = minimum_ms - (end_ms - start_ms)
    before = min(start_ms, missing // 2)
    start_ms -= before
    missing -= before
    end_ms = min(duration_ms, end_ms + missing)
    if end_ms - start_ms < minimum_ms:
        start_ms = max(0, end_ms - minimum_ms)
    return start_ms, end_ms


def _sentinel(start_ms: int, end_ms: int, reason: str) -> dict:
    return {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "reasons": [reason],
        "evidence": ["首尾覆盖规则"],
        "priority": 10,
        "sentinel": True,
    }


def _finite_number(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _priority(value) -> int:
    number = _finite_number(value)
    if number is None:
        return 5
    return min(max(int(round(number)), 1), 10)


def _string_values(value) -> list[str]:
    if isinstance(value, list):
        values = value
    else:
        values = [value]
    return [str(item).strip() for item in values if item is not None and str(item).strip()]


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _timestamp(value) -> str:
    number = _finite_number(value)
    if number is None:
        return "??:??:??.???"
    total_ms = max(0, int(round(number)))
    total_seconds, milliseconds = divmod(total_ms, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
