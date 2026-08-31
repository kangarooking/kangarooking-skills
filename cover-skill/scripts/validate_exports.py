#!/usr/bin/env python3
"""Validate required cover-skill files and pixel dimensions.

This script intentionally does not mutate files. It cannot validate copy accuracy,
face safety, line breaks, visual hierarchy, or design quality; those require manual QA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - environment-dependent message
    raise SystemExit(
        "Pillow is required. Install it in the active workspace runtime before validating."
    ) from exc


CONCEPT_FILES = {
    "candidate-A.png": "A",
    "candidate-B.png": "B",
    "candidate-C.png": "C",
    "candidate-D.png": "D",
}

STAGE1_TARGETS = {
    "wechat": {
        "ratio": "21:9",
        "size": (2100, 900),
        "thumb_size": (420, 180),
    },
    "bilibili": {
        "ratio": "16:9",
        "size": (1920, 1080),
        "thumb_size": (480, 270),
    },
    "douyin": {
        "ratio": "9:16",
        "size": (1080, 1920),
        "thumb_size": (270, 480),
    },
    "landscape-4x3": {
        "ratio": "4:3",
        "size": (1600, 1200),
        "thumb_size": (400, 300),
    },
    "portrait-3x4": {
        "ratio": "3:4",
        "size": (1200, 1600),
        "thumb_size": (360, 480),
    },
    "generic-16x9": {
        "ratio": "16:9",
        "size": (1920, 1080),
        "thumb_size": (480, 270),
    },
}

STAGE1_TARGET_FIELDS = {"key", "ratio", "origin"}
STAGE1_TARGET_ORIGINS = {"explicit-platform", "explicit-ratio", "default"}

SELECTED_FILES = {
    "cover-wechat-21x9.png": (2100, 900),
    "cover-bilibili-16x9.png": (1920, 1080),
    "cover-douyin-9x16.png": (1080, 1920),
    "cover-landscape-4x3.png": (1600, 1200),
    "cover-portrait-3x4.png": (1200, 1600),
}

SUPPORT_FILES = {
    "concepts": ("contact-sheet.png", "manifest.json"),
    "selected": ("platform-contact-sheet.png", "manifest.json"),
}

THUMB_FILES = {
    "selected": {
        "cover-wechat-21x9-420x180.png": (420, 180),
        "cover-bilibili-16x9-480x270.png": (480, 270),
        "cover-douyin-9x16-270x480.png": (270, 480),
        "cover-landscape-4x3-400x300.png": (400, 300),
        "cover-portrait-3x4-360x480.png": (360, 480),
    },
}

QA_REPORT_FILE = "qa-review.md"

EXPRESSION_INTENTS = {
    "surprised",
    "questioning",
    "surprised-questioning",
    "user-specified-neutral",
}

PET_CONTACT_FIELDS = {
    "support_surface",
    "paws_or_body_occlusion",
    "contact_shadow_or_compression",
    "lighting_perspective_match",
}

QA_REPORT_GATES = (
    "Exact copy",
    "Expression",
    "Face safe",
    "Pet pose natural",
    "Pet contact",
    "No pasted source",
    "Center anchor",
    "Text depth",
    "Product Logo",
    "Thumbnail readability",
)
QA_REPORT_RESULT_COLUMN = "Overall"

QA_FIELDS = {
    "concepts": (
        "copy_checked",
        "face_safe",
        "thumbnail_readable",
        "required_assets_visible",
        "portrait_expression_checked",
        "mascot_integrated",
        "pet_pose_natural_checked",
        "pet_contact_checked",
        "no_sticker_treatment_checked",
        "text_subject_integrated",
        "product_logo_integrated",
        "personal_signature_checked",
    ),
    "selected": (
        "copy_checked",
        "face_safe",
        "thumbnail_readable",
        "required_assets_visible",
        "native_recomposition_checked",
        "portrait_expression_checked",
        "mascot_integrated",
        "pet_pose_natural_checked",
        "pet_contact_checked",
        "no_sticker_treatment_checked",
        "text_subject_integrated",
        "product_logo_integrated",
        "personal_signature_checked",
    ),
}


def is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_recorded_path(base_dir: Path, recorded: str) -> Path:
    path = Path(recorded).expanduser()
    return path.resolve() if path.is_absolute() else (base_dir / path).resolve()


def canonical_topic_id(payload: dict) -> str | None:
    title = payload.get("title")
    summary = payload.get("summary")
    product_identity = payload.get("product_identity")
    assets = payload.get("assets")
    if (
        not isinstance(title, str)
        or not isinstance(summary, str)
        or not isinstance(product_identity, str)
        or not isinstance(assets, list)
    ):
        return None
    topic_hashes: list[str] = []
    for asset in assets:
        if isinstance(asset, dict) and asset.get("topic_key") is True:
            sha256 = asset.get("sha256")
            if not is_sha256(sha256):
                return None
            topic_hashes.append(sha256)
    basis = {
        "title": title,
        "summary": summary,
        "product_identity": product_identity,
        "topic_asset_sha256": sorted(topic_hashes),
    }
    canonical = json.dumps(
        basis, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_manifest(path: Path) -> tuple[dict | None, list[str]]:
    if not path.is_file():
        return None, [f"missing file: {path}"]
    if path.stat().st_size <= 0:
        return None, [f"empty file: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, [f"invalid JSON: {path}: {exc}"]
    if not isinstance(payload, dict):
        return None, [f"invalid manifest root: {path}: expected a JSON object"]
    return payload, []


def inspect_png(path: Path, expected: tuple[int, int] | None) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"missing file: {path.name}"]
    if path.stat().st_size <= 0:
        return [f"empty file: {path.name}"]
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            actual = image.size
            image_format = image.format
    except Exception as exc:  # Pillow exposes several decoder-specific errors
        return [f"unreadable image: {path.name}: {exc}"]
    if image_format != "PNG":
        errors.append(f"wrong format: {path.name}: expected PNG, got {image_format}")
    if expected is not None and actual != expected:
        errors.append(
            f"wrong dimensions: {path.name}: expected {expected[0]}x{expected[1]}, "
            f"got {actual[0]}x{actual[1]}"
        )
    return errors


def inspect_qa_report(path: Path, expected_outputs: set[str]) -> list[str]:
    """Check that a manually written visual-review table covers every output."""
    if not path.is_file():
        return [f"missing file: {path.name}"]
    if path.stat().st_size <= 0:
        return [f"empty file: {path.name}"]
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return [f"unreadable QA report: {path.name}: {exc}"]

    errors: list[str] = []

    def cells(line: str) -> list[str]:
        values = [value.strip() for value in line.strip().split("|")]
        if values and not values[0]:
            values = values[1:]
        if values and not values[-1]:
            values = values[:-1]
        return values

    expected_header = [
        "Output",
        QA_REPORT_RESULT_COLUMN,
        *QA_REPORT_GATES,
    ]
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if cells(line) == expected_header
        ),
        None,
    )
    if header_index is None:
        errors.append(
            "QA report must contain the exact table header: "
            + " | ".join(expected_header)
        )
        return errors

    rows: dict[str, list[str]] = {}
    for line in lines[header_index + 1 :]:
        row = cells(line)
        if not row:
            continue
        if all(re.fullmatch(r":?-{3,}:?", value) for value in row):
            continue
        if len(row) != len(expected_header):
            if "candidate-" in line or "cover-" in line:
                errors.append("QA report row has the wrong number of columns: " + line)
            continue
        filename = row[0].strip("`")
        if filename in expected_outputs:
            if filename in rows:
                errors.append(f"QA report has duplicate output row: {filename}")
            rows[filename] = row

    for filename in sorted(expected_outputs):
        row = rows.get(filename)
        if row is None:
            errors.append(f"QA report missing output row: {filename}")
            continue
        result_cells = row[1:]
        if any(
            not value.upper().startswith("PASS") or "FAIL" in value.upper()
            for value in result_cells
        ):
            errors.append(f"QA report output is not PASS: {filename}")
    return errors


def require_string(
    payload: dict, key: str, errors: list[str], *, nonempty: bool = False
) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or (nonempty and not value.strip()):
        qualifier = "non-empty string" if nonempty else "string"
        errors.append(f"invalid manifest field: {key}: expected {qualifier}")


def require_string_list(payload: dict, key: str, errors: list[str]) -> None:
    value = payload.get(key)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        errors.append(f"invalid manifest field: {key}: expected a non-empty string array")


def inspect_stage1_target(payload: dict, errors: list[str]) -> dict | None:
    target = payload.get("stage1_target")
    if not isinstance(target, dict):
        errors.append("invalid manifest field: stage1_target: expected an object")
        return None

    actual_fields = set(target)
    if actual_fields != STAGE1_TARGET_FIELDS:
        missing = sorted(STAGE1_TARGET_FIELDS - actual_fields)
        extra = sorted(actual_fields - STAGE1_TARGET_FIELDS)
        errors.append(
            "invalid manifest field: stage1_target keys: "
            f"missing={missing}, extra={extra}"
        )

    key = target.get("key")
    target_spec = STAGE1_TARGETS.get(key) if isinstance(key, str) else None
    if target_spec is None:
        errors.append(
            "invalid manifest field: stage1_target.key: expected one of "
            + ", ".join(sorted(STAGE1_TARGETS))
        )
        return None

    if target.get("ratio") != target_spec["ratio"]:
        errors.append(
            f"invalid manifest field: stage1_target.ratio: expected "
            f"{target_spec['ratio']!r} for {key!r}"
        )

    origin = target.get("origin")
    if not isinstance(origin, str) or origin not in STAGE1_TARGET_ORIGINS:
        errors.append(
            "invalid manifest field: stage1_target.origin: expected "
            "'explicit-platform', 'explicit-ratio', or 'default'"
        )
    elif origin == "default" and key != "generic-16x9":
        errors.append(
            "invalid manifest field: stage1_target.origin: "
            "'default' is only valid for 'generic-16x9'"
        )

    return target_spec


def concept_image_files(target_spec: dict | None) -> dict[str, tuple[int, int] | None]:
    size = target_spec["size"] if target_spec is not None else None
    return {name: size for name in CONCEPT_FILES}


def concept_thumb_files(target_spec: dict | None) -> dict[str, tuple[int, int]]:
    if target_spec is None:
        return {}
    width, height = target_spec["thumb_size"]
    return {
        f"candidate-{concept_id}-{width}x{height}.png": (width, height)
        for concept_id in CONCEPT_FILES.values()
    }


def inspect_manifest(
    path: Path,
    phase: str,
    expected_images: dict[str, tuple[int, int] | None],
) -> list[str]:
    payload, load_errors = load_manifest(path)
    if payload is None:
        return load_errors

    errors: list[str] = []
    if payload.get("phase") != phase:
        errors.append(f"invalid manifest field: phase: expected {phase!r}")
    if phase == "concepts":
        target_spec = inspect_stage1_target(payload, errors)
        expected_images = concept_image_files(target_spec)
    if payload.get("personal_signature_applies") is not True:
        errors.append("invalid manifest field: personal_signature_applies: expected true")
    if not isinstance(payload.get("product_logo_required"), bool):
        errors.append("invalid manifest field: product_logo_required: expected boolean")
    require_string(payload, "topic_id", errors, nonempty=True)
    require_string(payload, "run_id", errors, nonempty=True)
    require_string(payload, "product_identity", errors, nonempty=True)
    require_string(payload, "title", errors, nonempty=True)
    require_string(payload, "summary", errors)
    require_string_list(payload, "semantic_groups", errors)

    portrait_master = payload.get("portrait_expression_master")
    if not isinstance(portrait_master, dict):
        errors.append(
            "invalid manifest field: portrait_expression_master: expected an object"
        )
    else:
        master_path = portrait_master.get("path")
        master_sha256 = portrait_master.get("sha256")
        master_expression = portrait_master.get("expression_intent")
        if not isinstance(master_path, str) or not master_path.strip():
            errors.append("invalid manifest field: portrait_expression_master.path")
        if not is_sha256(master_sha256):
            errors.append("invalid manifest field: portrait_expression_master.sha256")
        if master_expression not in EXPRESSION_INTENTS:
            errors.append(
                "invalid manifest field: portrait_expression_master.expression_intent"
            )
        if isinstance(master_path, str) and master_path.strip():
            actual_master_path = resolve_recorded_path(path.parent, master_path)
            if not actual_master_path.is_file():
                errors.append(
                    f"missing portrait expression master: {actual_master_path}"
                )
            elif is_sha256(master_sha256):
                if sha256_file(actual_master_path) != master_sha256:
                    errors.append("portrait expression master SHA-256 mismatch")

    pet_companion_masters = payload.get("pet_companion_masters")
    pet_master_hash_by_pose: dict[str, str] = {}
    pet_master_source_ip_hashes: set[str] = set()
    if not isinstance(pet_companion_masters, list) or not pet_companion_masters:
        errors.append(
            "invalid manifest field: pet_companion_masters: expected a non-empty array"
        )
    else:
        for index, pet_master in enumerate(pet_companion_masters):
            label = f"pet_companion_masters[{index}]"
            if not isinstance(pet_master, dict):
                errors.append(f"invalid manifest field: {label}: expected an object")
                continue
            pose = pet_master.get("pose")
            if pose not in {"shoulder", "head"}:
                errors.append(f"invalid manifest field: {label}.pose")
            elif pose in pet_master_hash_by_pose:
                errors.append(f"duplicate pet companion master pose: {pose}")
            recorded_path = pet_master.get("path")
            recorded_sha256 = pet_master.get("sha256")
            if not isinstance(recorded_path, str) or not recorded_path.strip():
                errors.append(f"invalid manifest field: {label}.path")
            if not is_sha256(recorded_sha256):
                errors.append(f"invalid manifest field: {label}.sha256")
            elif pose in {"shoulder", "head"}:
                pet_master_hash_by_pose[pose] = recorded_sha256
            if pet_master.get("integration_method") != "generated-integrated":
                errors.append(
                    f"invalid manifest field: {label}.integration_method: "
                    "expected 'generated-integrated'"
                )
            source_ip_sha256 = pet_master.get("source_ip_sha256")
            if not is_sha256(source_ip_sha256):
                errors.append(f"invalid manifest field: {label}.source_ip_sha256")
            else:
                pet_master_source_ip_hashes.add(source_ip_sha256)
                if is_sha256(recorded_sha256) and recorded_sha256 == source_ip_sha256:
                    errors.append(
                        f"pet companion master may not be the raw source IP bitmap: {label}"
                    )
            source_portrait_sha256 = pet_master.get("source_portrait_sha256")
            if not is_sha256(source_portrait_sha256):
                errors.append(
                    f"invalid manifest field: {label}.source_portrait_sha256"
                )
            elif isinstance(portrait_master, dict) and source_portrait_sha256 != portrait_master.get(
                "sha256"
            ):
                errors.append(
                    f"pet companion master is not bound to portrait_expression_master: {label}"
                )
            elif is_sha256(recorded_sha256) and recorded_sha256 == source_portrait_sha256:
                errors.append(
                    f"pet companion master does not contain a re-posed pet: {label}"
                )
            if not isinstance(pet_master.get("generation_notes"), str) or not pet_master.get(
                "generation_notes", ""
            ).strip():
                errors.append(f"invalid manifest field: {label}.generation_notes")
            if isinstance(recorded_path, str) and recorded_path.strip():
                actual_pet_master_path = resolve_recorded_path(path.parent, recorded_path)
                if not actual_pet_master_path.is_file():
                    errors.append(
                        f"missing pet companion master: {actual_pet_master_path}"
                    )
                else:
                    errors.extend(
                        f"{label}: {error}"
                        for error in inspect_png(actual_pet_master_path, None)
                    )
                    if is_sha256(recorded_sha256) and sha256_file(
                        actual_pet_master_path
                    ) != recorded_sha256:
                        errors.append(f"pet companion master SHA-256 mismatch: {label}")
    assets = payload.get("assets")
    if not isinstance(assets, list) or not assets:
        errors.append("invalid manifest field: assets: expected an array")
    else:
        for index, asset in enumerate(assets):
            label = f"assets[{index}]"
            if not isinstance(asset, dict):
                errors.append(f"invalid manifest field: {label}: expected an object")
                continue
            for field in ("role", "path"):
                if not isinstance(asset.get(field), str) or not asset.get(field):
                    errors.append(f"invalid manifest field: {label}.{field}")
            if asset.get("usage") not in {"required-visible", "reference-only"}:
                errors.append(f"invalid manifest field: {label}.usage")
            if not isinstance(asset.get("topic_key"), bool):
                errors.append(f"invalid manifest field: {label}.topic_key")
            if not is_sha256(asset.get("sha256")):
                errors.append(f"invalid manifest field: {label}.sha256")
            recorded_path = asset.get("path")
            if isinstance(recorded_path, str) and recorded_path:
                actual_path = resolve_recorded_path(path.parent, recorded_path)
                if not actual_path.is_file():
                    errors.append(f"missing asset file: {label}.path: {actual_path}")
                elif is_sha256(asset.get("sha256")):
                    actual_sha256 = sha256_file(actual_path)
                    if actual_sha256 != asset["sha256"]:
                        errors.append(f"asset SHA-256 mismatch: {label}: {actual_path}")

        all_roles = {
            str(asset.get("role", "")).casefold()
            for asset in assets
            if isinstance(asset, dict)
        }
        required_roles = {
            str(asset.get("role", "")).casefold()
            for asset in assets
            if isinstance(asset, dict) and asset.get("usage") == "required-visible"
        }
        personal_ip_hashes = {
            str(asset.get("sha256"))
            for asset in assets
            if isinstance(asset, dict)
            and any(
                token in str(asset.get("role", "")).casefold()
                for token in ("personal_ip", "kangaroo", "mascot")
            )
            and is_sha256(asset.get("sha256"))
        }
        if not any("portrait" in role for role in required_roles):
            errors.append("personal signature requires a required-visible portrait asset")
        if not any(
            "personal_ip" in role
            or "kangaroo" in role
            or "mascot" in role
            or "pet_master" in role
            for role in required_roles
        ):
            errors.append(
                "personal signature requires a required-visible integrated portrait-pet master"
            )
        if not any(
            "personal_ip" in role or "kangaroo" in role or "mascot" in role
            for role in all_roles
        ):
            errors.append("personal signature requires a source kangaroo/IP asset")
        if pet_master_source_ip_hashes and not pet_master_source_ip_hashes.issubset(
            personal_ip_hashes
        ):
            errors.append(
                "pet companion masters are not bound to the recorded source kangaroo/IP asset"
            )
        if payload.get("product_logo_required") is True and not any(
            "product_logo" in role or "product logo" in role for role in required_roles
        ):
            errors.append("product_logo_required is true but no required-visible product Logo asset exists")
        if payload.get("product_logo_required") is False and any(
            "product_logo" in role or "product logo" in role for role in all_roles
        ):
            errors.append(
                "a product Logo asset exists, so product_logo_required must be true"
            )

    expected_topic_id = canonical_topic_id(payload)
    if expected_topic_id is None:
        errors.append("cannot derive topic_id from manifest content and topic-key assets")
    elif payload.get("topic_id") != expected_topic_id:
        errors.append(
            f"topic_id mismatch: expected canonical SHA-256 {expected_topic_id}"
        )

    panels = payload.get("contact_sheet_panels")
    if (
        not isinstance(panels, list)
        or not all(isinstance(panel, str) for panel in panels)
        or set(panels) != set(expected_images)
    ):
        errors.append(
            "invalid manifest field: contact_sheet_panels must list each primary output exactly once"
        )
    elif len(panels) != len(expected_images):
        errors.append("invalid manifest field: contact_sheet_panels contains duplicates")

    outputs = payload.get("outputs")
    if not isinstance(outputs, list):
        errors.append("invalid manifest field: outputs: expected an array")
        return errors

    expected_count = 4 if phase == "concepts" else 5
    if len(outputs) != expected_count:
        errors.append(
            f"invalid manifest field: outputs: expected {expected_count} records, "
            f"got {len(outputs)}"
        )

    expected_ids = set(CONCEPT_FILES.values())
    expected_platforms = {
        "wechat",
        "bilibili",
        "douyin",
        "landscape-4x3",
        "portrait-3x4",
    }
    seen_ids: set[str] = set()
    seen_platforms: set[str] = set()
    seen_files: set[str] = set()
    seen_expression_intents: set[str] = set()

    for index, output in enumerate(outputs):
        label = f"outputs[{index}]"
        if not isinstance(output, dict):
            errors.append(f"invalid manifest field: {label}: expected an object")
            continue
        filename = output.get("file")
        if not isinstance(filename, str):
            errors.append(f"invalid manifest field: {label}.file: expected a string")
            continue
        seen_files.add(filename)
        expected_size = expected_images.get(filename)
        if filename not in expected_images:
            errors.append(f"unexpected manifest output file: {filename}")
        elif expected_size is not None and (
            output.get("width") != expected_size[0]
            or output.get("height") != expected_size[1]
        ):
            errors.append(
                f"wrong manifest dimensions: {filename}: expected "
                f"{expected_size[0]}x{expected_size[1]}"
            )

        recorded_sha256 = output.get("sha256")
        if not is_sha256(recorded_sha256):
            errors.append(f"invalid manifest field: {label}.sha256")
        output_path = path.parent / filename
        if output_path.is_file() and is_sha256(recorded_sha256):
            if sha256_file(output_path) != recorded_sha256:
                errors.append(f"output SHA-256 mismatch: {filename}")

        if not isinstance(output.get("font"), str) or not output.get("font"):
            errors.append(f"invalid manifest field: {label}.font")
        expression_intent = output.get("expression_intent")
        if expression_intent not in EXPRESSION_INTENTS:
            errors.append(f"invalid manifest field: {label}.expression_intent")
        else:
            seen_expression_intents.add(expression_intent)
        for field in (
            "subject_anchor",
            "mascot_relationship",
            "text_subject_integration",
            "logo_integration",
        ):
            if not isinstance(output.get(field), str) or not output.get(field).strip():
                errors.append(f"invalid manifest field: {label}.{field}")

        subject_anchor = output.get("subject_anchor")
        if isinstance(subject_anchor, str) and subject_anchor.strip():
            normalized_anchor = subject_anchor.casefold()
            if not any(
                token in normalized_anchor for token in ("center", "中心", "居中")
            ):
                errors.append(
                    f"personal signature requires a centered subject anchor: {label}.subject_anchor"
                )

        mascot_relationship = output.get("mascot_relationship")
        if isinstance(mascot_relationship, str) and mascot_relationship.strip():
            normalized_mascot = mascot_relationship.casefold()
            has_head_or_shoulder = bool(
                re.search(r"\b(?:shoulder|head)\b", normalized_mascot)
            ) or any(token in normalized_mascot for token in ("肩", "头部", "头顶"))
            if not has_head_or_shoulder:
                errors.append(
                    f"personal signature requires a shoulder/head kangaroo connection: {label}.mascot_relationship"
                )
        pet_pose = output.get("pet_pose")
        if pet_pose not in {"shoulder", "head"}:
            errors.append(f"invalid manifest field: {label}.pet_pose")
        elif isinstance(mascot_relationship, str):
            normalized_mascot = mascot_relationship.casefold()
            expected_tokens = (
                ("shoulder", "肩") if pet_pose == "shoulder" else ("head", "hair", "crown", "头", "发")
            )
            if not any(token in normalized_mascot for token in expected_tokens):
                errors.append(
                    f"pet_pose and mascot_relationship disagree: {label}"
                )
        pet_master_sha256 = output.get("pet_master_sha256")
        if not is_sha256(pet_master_sha256):
            errors.append(f"invalid manifest field: {label}.pet_master_sha256")
        elif pet_pose in {"shoulder", "head"}:
            approved_hash = pet_master_hash_by_pose.get(pet_pose)
            if approved_hash is None:
                errors.append(
                    f"output refers to a missing approved {pet_pose} pet companion master: {label}"
                )
            elif pet_master_sha256 != approved_hash:
                errors.append(
                    f"output is not bound to the approved {pet_pose} pet companion master: {label}"
                )
        pet_contact_evidence = output.get("pet_contact_evidence")
        if not isinstance(pet_contact_evidence, dict):
            errors.append(
                f"invalid manifest field: {label}.pet_contact_evidence: expected an object"
            )
        else:
            actual_evidence_fields = set(pet_contact_evidence)
            if actual_evidence_fields != PET_CONTACT_FIELDS:
                errors.append(
                    f"invalid manifest field: {label}.pet_contact_evidence keys: "
                    f"expected={sorted(PET_CONTACT_FIELDS)}, got={sorted(actual_evidence_fields)}"
                )
            for field in PET_CONTACT_FIELDS:
                if not isinstance(pet_contact_evidence.get(field), str) or not pet_contact_evidence.get(
                    field, ""
                ).strip():
                    errors.append(
                        f"invalid manifest field: {label}.pet_contact_evidence.{field}"
                    )
        if not isinstance(output.get("line_groups"), list) or not output.get(
            "line_groups"
        ):
            errors.append(
                f"invalid manifest field: {label}.line_groups: expected a non-empty array"
            )
        elif not all(
            isinstance(group, str) and group for group in output["line_groups"]
        ):
            errors.append(
                f"invalid manifest field: {label}.line_groups: expected non-empty strings"
            )

        qa = output.get("qa")
        if not isinstance(qa, dict):
            errors.append(f"invalid manifest field: {label}.qa: expected an object")
        else:
            required_qa_fields = set(QA_FIELDS[phase])
            actual_qa_fields = set(qa)
            if actual_qa_fields != required_qa_fields:
                missing = sorted(required_qa_fields - actual_qa_fields)
                extra = sorted(actual_qa_fields - required_qa_fields)
                errors.append(
                    f"invalid manifest field: {label}.qa keys: missing={missing}, extra={extra}"
                )
            for field in required_qa_fields:
                if qa.get(field) is not True:
                    errors.append(
                        f"failed or missing QA attestation: {label}.qa.{field}"
                    )

        if phase == "concepts":
            concept_id = output.get("id")
            if concept_id not in expected_ids:
                errors.append(f"invalid manifest field: {label}.id")
            else:
                seen_ids.add(concept_id)
            if not isinstance(output.get("prompt_notes"), str) or not output.get(
                "prompt_notes"
            ):
                errors.append(f"invalid manifest field: {label}.prompt_notes")
        else:
            platform = output.get("platform")
            if platform not in expected_platforms:
                errors.append(f"invalid manifest field: {label}.platform")
            else:
                seen_platforms.add(platform)
            if not isinstance(output.get("layout_notes"), str) or not output.get(
                "layout_notes"
            ):
                errors.append(f"invalid manifest field: {label}.layout_notes")

    if seen_files != set(expected_images):
        errors.append("manifest outputs do not match the required output filenames exactly")
    if len(seen_expression_intents) != 1:
        errors.append(
            "all outputs must preserve exactly one shared expression_intent"
        )
    elif isinstance(portrait_master, dict):
        master_expression = portrait_master.get("expression_intent")
        if master_expression not in seen_expression_intents:
            errors.append(
                "output expression_intent does not match portrait_expression_master"
            )
    if phase == "concepts" and seen_ids != expected_ids:
        errors.append("manifest concept ids must be exactly A, B, C, and D")
    if phase == "selected":
        if seen_platforms != expected_platforms:
            errors.append("manifest platforms do not match the five required targets exactly")
        source_concept_id = payload.get("source_concept_id")
        if source_concept_id not in expected_ids | {"external", "custom"}:
            errors.append(
                "invalid manifest field: source_concept_id must be A-D, external, or custom"
            )
        require_string(payload, "source_run_id", errors, nonempty=True)
        require_string(payload, "source_path", errors, nonempty=True)
        if not is_sha256(payload.get("source_sha256")):
            errors.append("invalid manifest field: source_sha256")
        if source_concept_id == "custom":
            parent_ids = payload.get("parent_concept_ids")
            if (
                not isinstance(parent_ids, list)
                or not parent_ids
                or not all(parent_id in expected_ids for parent_id in parent_ids)
                or len(parent_ids) != len(set(parent_ids))
            ):
                errors.append(
                    "invalid manifest field: parent_concept_ids must be unique A-D ids"
                )
        if (
            source_concept_id in expected_ids | {"custom"}
            and payload.get("source_run_id") != payload.get("run_id")
        ):
            errors.append(
                "selected source_run_id must match run_id for an A-D or custom selection"
            )

    return errors


def required_asset_fingerprint(payload: dict) -> list[tuple[str, str, bool]]:
    assets = payload.get("assets")
    if not isinstance(assets, list):
        return []
    return sorted(
        (
            str(asset.get("role")),
            str(asset.get("sha256")),
            bool(asset.get("topic_key")),
        )
        for asset in assets
        if isinstance(asset, dict) and asset.get("usage") == "required-visible"
    )


def validate_source_binding(
    selected_dir: Path, source_manifest_path: Path | None
) -> list[str]:
    selected_payload, selected_load_errors = load_manifest(selected_dir / "manifest.json")
    if selected_payload is None:
        return selected_load_errors

    errors: list[str] = []
    source_concept_id = selected_payload.get("source_concept_id")
    recorded_source_path = selected_payload.get("source_path")
    source_path = (
        resolve_recorded_path(selected_dir, recorded_source_path)
        if isinstance(recorded_source_path, str) and recorded_source_path
        else None
    )
    recorded_source_sha256 = selected_payload.get("source_sha256")

    if source_path is None or not source_path.is_file():
        errors.append(f"selected source_path does not exist: {source_path}")
    elif is_sha256(recorded_source_sha256):
        if sha256_file(source_path) != recorded_source_sha256:
            errors.append("selected source_sha256 does not match source_path")

    expected_ids = set(CONCEPT_FILES.values())
    if source_concept_id == "external":
        return errors

    if source_manifest_path is None:
        errors.append(
            "--source-manifest is required when source_concept_id is A-D or custom"
        )
        return errors

    source_manifest_path = source_manifest_path.resolve()
    source_payload, source_load_errors = load_manifest(source_manifest_path)
    if source_payload is None:
        errors.extend(source_load_errors)
        return errors
    source_target_spec = inspect_stage1_target(source_payload, [])
    source_contract_errors = inspect_manifest(
        source_manifest_path,
        "concepts",
        concept_image_files(source_target_spec),
    )
    errors.extend(f"source manifest: {error}" for error in source_contract_errors)
    if source_payload.get("phase") != "concepts":
        errors.append("source manifest phase must be 'concepts'")

    comparisons = (
        ("topic_id", "topic_id"),
        ("run_id", "run_id"),
        ("title", "title"),
        ("summary", "summary"),
        ("semantic_groups", "semantic_groups"),
        ("product_identity", "product_identity"),
        ("personal_signature_applies", "personal_signature_applies"),
        ("product_logo_required", "product_logo_required"),
        ("portrait_expression_master", "portrait_expression_master"),
        ("pet_companion_masters", "pet_companion_masters"),
    )
    for selected_field, source_field in comparisons:
        if selected_payload.get(selected_field) != source_payload.get(source_field):
            errors.append(
                f"selected/source manifest mismatch: {selected_field} != {source_field}"
            )
    if selected_payload.get("source_run_id") != source_payload.get("run_id"):
        errors.append("selected source_run_id does not match source manifest run_id")
    if required_asset_fingerprint(selected_payload) != required_asset_fingerprint(
        source_payload
    ):
        errors.append("selected/source required-visible assets do not match")

    if source_concept_id == "custom":
        parent_ids = selected_payload.get("parent_concept_ids")
        source_ids = {
            output.get("id")
            for output in source_payload.get("outputs", [])
            if isinstance(output, dict)
        }
        if isinstance(parent_ids, list) and not set(parent_ids).issubset(source_ids):
            errors.append("custom parent_concept_ids are missing from source manifest")
        return errors

    source_outputs = source_payload.get("outputs")
    source_output = None
    if isinstance(source_outputs, list):
        source_output = next(
            (
                output
                for output in source_outputs
                if isinstance(output, dict) and output.get("id") == source_concept_id
            ),
            None,
        )
    if source_output is None:
        errors.append(f"source manifest has no concept {source_concept_id}")
        return errors

    selected_outputs = selected_payload.get("outputs")
    selected_expression_intents = {
        output.get("expression_intent")
        for output in selected_outputs
        if isinstance(output, dict)
    } if isinstance(selected_outputs, list) else set()
    if selected_expression_intents != {source_output.get("expression_intent")}:
        errors.append(
            "selected output expression_intent does not match the source concept"
        )
    selected_pet_poses = {
        output.get("pet_pose")
        for output in selected_outputs
        if isinstance(output, dict)
    } if isinstance(selected_outputs, list) else set()
    if selected_pet_poses != {source_output.get("pet_pose")}:
        errors.append("selected output pet_pose does not match the source concept")
    selected_pet_master_hashes = {
        output.get("pet_master_sha256")
        for output in selected_outputs
        if isinstance(output, dict)
    } if isinstance(selected_outputs, list) else set()
    if selected_pet_master_hashes != {source_output.get("pet_master_sha256")}:
        errors.append(
            "selected output pet_master_sha256 does not match the source concept"
        )

    expected_filename = f"candidate-{source_concept_id}.png"
    expected_source_path = (source_manifest_path.parent / expected_filename).resolve()
    if source_output.get("file") != expected_filename:
        errors.append(f"source concept {source_concept_id} has the wrong filename")
    if source_path is not None and source_path != expected_source_path:
        errors.append(
            f"selected source_path must resolve to {expected_source_path}, got {source_path}"
        )
    if source_output.get("sha256") != recorded_source_sha256:
        errors.append("selected source_sha256 does not match source concept SHA-256")

    return errors


def validate(
    directory: Path, phase: str, source_manifest: Path | None = None
) -> dict:
    errors: list[str] = []
    checked: list[str] = []

    target_spec = None
    if phase == "concepts":
        manifest_payload, _ = load_manifest(directory / "manifest.json")
        if manifest_payload is not None:
            target_spec = inspect_stage1_target(manifest_payload, [])
        expected_images = concept_image_files(target_spec)
        expected_thumbs = concept_thumb_files(target_spec)
    else:
        expected_images = SELECTED_FILES
        expected_thumbs = THUMB_FILES[phase]
    for name, expected in expected_images.items():
        checked.append(name)
        errors.extend(inspect_png(directory / name, expected))

    contact_sheet, manifest = SUPPORT_FILES[phase]
    checked.append(contact_sheet)
    errors.extend(inspect_png(directory / contact_sheet, None))
    checked.append(manifest)
    errors.extend(inspect_manifest(directory / manifest, phase, expected_images))
    checked.append(QA_REPORT_FILE)
    errors.extend(inspect_qa_report(directory / QA_REPORT_FILE, set(expected_images)))
    if phase == "selected":
        errors.extend(validate_source_binding(directory, source_manifest))
        if source_manifest is not None:
            checked.append(str(source_manifest))
    elif source_manifest is not None:
        errors.append("--source-manifest is only valid with --phase selected")

    thumbs_dir = directory / "thumbs"
    for name, expected in expected_thumbs.items():
        relative = f"thumbs/{name}"
        checked.append(relative)
        errors.extend(inspect_png(thumbs_dir / name, expected))

    if phase == "concepts" and target_spec is not None:
        actual_thumbs = {
            path.name for path in thumbs_dir.glob("candidate-*.png") if path.is_file()
        }
        if actual_thumbs != set(expected_thumbs):
            extras = sorted(actual_thumbs - set(expected_thumbs))
            missing = sorted(set(expected_thumbs) - actual_thumbs)
            if extras:
                errors.append(f"unexpected thumbnail files: {', '.join(extras)}")
            if missing:
                errors.append(f"missing thumbnail files: {', '.join(missing)}")

    pattern = "candidate-*.png" if phase == "concepts" else "cover-*.png"
    actual_primary = {path.name for path in directory.glob(pattern) if path.is_file()}
    if actual_primary != set(expected_images):
        extras = sorted(actual_primary - set(expected_images))
        missing = sorted(set(expected_images) - actual_primary)
        if extras:
            errors.append(f"unexpected primary files: {', '.join(extras)}")
        if missing:
            errors.append(f"missing primary files: {', '.join(missing)}")

    if phase == "concepts":
        digests: dict[str, list[str]] = {}
        for name in expected_images:
            path = directory / name
            if path.is_file():
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                digests.setdefault(digest, []).append(name)
        duplicates = [names for names in digests.values() if len(names) > 1]
        for names in duplicates:
            errors.append(
                "byte-identical concept files are not distinct: " + ", ".join(names)
            )

    return {
        "ok": not errors,
        "phase": phase,
        "directory": str(directory.resolve()),
        "checked": checked,
        "errors": errors,
        "manual_qa_required": [
            "exact title and summary",
            "semantic line breaks and readability",
            "face safety and glyph recognizability",
            "surprised/questioning portrait expression",
            "pet kangaroo naturally bears weight on the shoulder/head",
            "pet paws/body occlusion, contact shadow, and material compression",
            "no cropped or pasted source kangaroo bitmap",
            "centered or center-weighted subject",
            "Logo, portrait, and APP fidelity",
            "visual distinction or cross-ratio consistency",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("concepts", "selected"), required=True)
    parser.add_argument("--dir", type=Path, required=True, dest="directory")
    parser.add_argument(
        "--source-manifest",
        type=Path,
        help="Required for an A-D or current-run custom Stage 2 source",
    )
    args = parser.parse_args()

    report = validate(args.directory, args.phase, args.source_manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
