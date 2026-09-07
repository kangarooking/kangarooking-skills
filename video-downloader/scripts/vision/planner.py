"""Build auditable, secret-free plans for visual-model uploads."""

from __future__ import annotations

import json
from pathlib import Path


PRIVACY_WARNING = "所列文案、图片或视频会离开本机并发送给第三方模型服务；请确认上传权限，并检查隐私与敏感信息。"


def build_vision_plan(
    *,
    mode: str,
    backend: str,
    model: str,
    profile: str,
    source_path: Path,
    upload_items: list[dict],
    stage: str = "vision",
    limits: dict | None = None,
    limitations: list[str] | None = None,
) -> dict:
    normalized_items = [_normalize_item(item) for item in upload_items]
    file_items = [item for item in normalized_items if item.get("path")]
    transcript_characters = sum(
        int(item.get("character_count") or 0)
        for item in normalized_items
        if item.get("kind") in {"transcript", "caption", "text"}
    )
    return {
        "schema_version": 1,
        "mode": mode,
        "stage": stage,
        "backend": backend,
        "model": model,
        "profile": profile,
        "source": {
            "name": source_path.name,
            "original_uploaded": False,
        },
        "upload_items": normalized_items,
        "upload_scope": {
            "file_count": len(file_items),
            "total_bytes": sum(int(item.get("size_bytes") or 0) for item in file_items),
            "media_seconds": round(
                sum(float(item.get("duration_seconds") or 0) for item in file_items), 3
            ),
            "transcript_characters": transcript_characters,
            "data_kinds": sorted({str(item.get("kind") or "unknown") for item in normalized_items}),
            "audio_file_count": sum(
                1 for item in file_items if item.get("contains_audio") is True
            ),
            "preprocess_fps": sorted(
                {
                    float(item["preprocess_fps"])
                    for item in file_items
                    if isinstance(item.get("preprocess_fps"), (int, float))
                    and not isinstance(item.get("preprocess_fps"), bool)
                }
            ),
        },
        "limits": dict(limits or {}),
        "cloud_upload": {
            "required": bool(normalized_items),
            "confirmed": False,
            "status": "not_started",
        },
        "privacy_warning": PRIVACY_WARNING,
        "limitations": list(limitations or []),
    }


def write_vision_plan(output_dir: Path, plan: dict, *, filename: str = "vision_plan.json") -> Path:
    destination = output_dir / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def update_plan_confirmation(plan: dict, *, confirmed: bool, status: str) -> dict:
    plan["cloud_upload"] = {
        **(plan.get("cloud_upload") or {}),
        "confirmed": bool(confirmed),
        "status": status,
    }
    return plan


def _normalize_item(item: dict) -> dict:
    allowed = {
        "kind",
        "label",
        "path",
        "size_bytes",
        "duration_seconds",
        "character_count",
        "start_ms",
        "end_ms",
        "id",
        "contains_audio",
        "preprocess_fps",
    }
    normalized = {key: value for key, value in item.items() if key in allowed}
    if normalized.get("path"):
        normalized["path"] = str(normalized["path"]).replace("\\", "/").rsplit("/", 1)[-1]
    return normalized
