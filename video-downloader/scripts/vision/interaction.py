"""User interaction and privacy gates for cloud visual analysis."""

from __future__ import annotations

import sys
from typing import Callable, TextIO


VISION_MODES = ("keyframes", "full-video", "agent-clips")


class VisionInteractionError(RuntimeError):
    """Raised when a safe visual-analysis choice cannot be obtained."""


def choose_vision_mode(
    requested: str | None,
    *,
    interactive: bool | None = None,
    input_fn: Callable[[str], str] = input,
    output: TextIO | None = None,
) -> str:
    """Resolve a visual mode without silently choosing one for automation."""
    if requested:
        if requested not in VISION_MODES:
            raise VisionInteractionError(f"Unsupported visual mode: {requested}")
        return requested
    if interactive is None:
        interactive = sys.stdin.isatty()
    if not interactive:
        raise VisionInteractionError(
            "Visual analysis requires an explicit --vision-mode: "
            "keyframes, full-video, or agent-clips (recommended)."
        )
    stream = output or sys.stderr
    stream.write(
        "请选择视频视觉提取方案：\n"
        "  1. keyframes   只上传关键帧，成本最低，可能漏掉动态信息\n"
        "  2. full-video  上传压缩后的完整视频代理，信息更全、成本最高\n"
        "  3. agent-clips Agent 先读时间戳文案并选择关键片段（推荐）\n"
    )
    mapping = {
        "1": "keyframes",
        "keyframes": "keyframes",
        "2": "full-video",
        "full-video": "full-video",
        "3": "agent-clips",
        "agent-clips": "agent-clips",
        "": "agent-clips",
    }
    while True:
        try:
            answer = input_fn("请输入 1/2/3（回车选择推荐项 3）：").strip().lower()
        except (EOFError, KeyboardInterrupt) as exc:
            raise VisionInteractionError("Visual mode selection was cancelled; no cloud upload started.") from exc
        selected = mapping.get(answer)
        if selected:
            return selected
        stream.write("无法识别该选项，请输入 1、2 或 3。\n")


def format_upload_preview(plan: dict) -> str:
    """Render a concise upload preview suitable for stderr."""
    scope = plan.get("upload_scope") or {}
    mode = plan.get("mode") or "unknown"
    lines = [
        "即将把以下内容发送到火山方舟/豆包：",
        f"- 模式：{mode}",
        f"- 阶段：{plan.get('stage') or 'vision'}",
        f"- 模型：{plan.get('model') or 'unknown'}",
        f"- 文件数：{int(scope.get('file_count') or 0)}",
        f"- 文件总大小：{int(scope.get('total_bytes') or 0)} bytes",
        f"- 视频总时长：{float(scope.get('media_seconds') or 0):.2f} 秒",
        f"- 文案字符数：{int(scope.get('transcript_characters') or 0)}",
    ]
    audio_files = int(scope.get("audio_file_count") or 0)
    if audio_files:
        lines.append(f"- 其中包含音轨的视频文件：{audio_files}")
    fps_values = scope.get("preprocess_fps") or []
    if fps_values:
        lines.append("- 视频预处理采样率：" + "、".join(f"{float(value):g} fps" for value in fps_values))
    if mode == "full-video":
        lines.append("- 上传的是压缩视觉代理，不是原始视频文件。")
    if mode == "agent-clips" and (plan.get("stage") or "") == "selection":
        limits = plan.get("limits") or {}
        lines.append(
            "- 本阶段会上传时间戳文案、平台文案和场景时间点用于选段；"
            f"最多选择 {int(limits.get('max_clips') or 0)} 个候选区间，再按单段上限切分；"
            + (f"总预算 {float(limits['max_total_seconds']):.0f} 秒。" if limits.get('max_total_seconds') else "不额外限制总时长。")
        )
    lines.append(f"- 隐私提醒：{plan.get('privacy_warning') or '上传内容将离开本机。'}")
    limitations = plan.get("limitations") or []
    for limitation in limitations:
        lines.append(f"- 限制：{limitation}")
    return "\n".join(lines)


def confirm_cloud_upload(
    plan: dict,
    *,
    confirmed: bool,
    plan_only: bool,
    interactive: bool | None = None,
    input_fn: Callable[[str], str] = input,
    output: TextIO | None = None,
) -> bool:
    """Show the upload scope and return True only after explicit permission."""
    stream = output or sys.stderr
    stream.write(format_upload_preview(plan) + "\n")
    if plan_only:
        stream.write("当前是 --vision-plan-only：已停止，未发起云端请求。\n")
        return False
    if confirmed:
        stream.write("已通过 --confirm-cloud-upload 明确授权本次云端请求。\n")
        return True
    if interactive is None:
        interactive = sys.stdin.isatty()
    if not interactive:
        raise VisionInteractionError(
            "Non-interactive cloud analysis requires --confirm-cloud-upload. "
            "Use --vision-plan-only to inspect the upload plan without uploading."
        )
    try:
        answer = input_fn("确认上传上述内容？[y/N]：").strip().lower()
    except (EOFError, KeyboardInterrupt) as exc:
        raise VisionInteractionError("Cloud upload confirmation was cancelled; nothing was uploaded.") from exc
    if answer in {"y", "yes", "是", "确认"}:
        return True
    stream.write("用户未确认：已停止，未发起云端请求。\n")
    return False
