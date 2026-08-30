#!/usr/bin/env python3
"""Validate required cover-skill files and pixel dimensions.

This script intentionally does not mutate files. It cannot validate copy accuracy,
face safety, line breaks, visual hierarchy, or design quality; those require manual QA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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

CONCEPT_SIZE = (1920, 1080)

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
    "concepts": {
        "candidate-A-480x270.png": (480, 270),
        "candidate-B-480x270.png": (480, 270),
        "candidate-C-480x270.png": (480, 270),
        "candidate-D-480x270.png": (480, 270),
    },
    "selected": {
        "cover-wechat-21x9-420x180.png": (420, 180),
        "cover-bilibili-16x9-480x270.png": (480, 270),
        "cover-douyin-9x16-270x480.png": (270, 480),
        "cover-landscape-4x3-400x300.png": (400, 300),
        "cover-portrait-3x4-360x480.png": (360, 480),
    },
}

QA_FIELDS = {
    "concepts": (
        "copy_checked",
        "face_safe",
        "thumbnail_readable",
        "required_assets_visible",
    ),
    "selected": (
        "copy_checked",
        "face_safe",
        "thumbnail_readable",
        "required_assets_visible",
        "native_recomposition_checked",
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


def inspect_manifest(
    path: Path,
    phase: str,
    expected_images: dict[str, tuple[int, int]],
) -> list[str]:
    payload, load_errors = load_manifest(path)
    if payload is None:
        return load_errors

    errors: list[str] = []
    if payload.get("phase") != phase:
        errors.append(f"invalid manifest field: phase: expected {phase!r}")
    require_string(payload, "topic_id", errors, nonempty=True)
    require_string(payload, "run_id", errors, nonempty=True)
    require_string(payload, "product_identity", errors, nonempty=True)
    require_string(payload, "title", errors, nonempty=True)
    require_string(payload, "summary", errors)
    require_string_list(payload, "semantic_groups", errors)
    assets = payload.get("assets")
    if not isinstance(assets, list):
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
        if expected_size is None:
            errors.append(f"unexpected manifest output file: {filename}")
        elif (
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
            for field in QA_FIELDS[phase]:
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
    source_contract_errors = inspect_manifest(
        source_manifest_path,
        "concepts",
        {name: CONCEPT_SIZE for name in CONCEPT_FILES},
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

    expected_images: dict[str, tuple[int, int]] = (
        {name: CONCEPT_SIZE for name in CONCEPT_FILES}
        if phase == "concepts"
        else SELECTED_FILES
    )
    for name, expected in expected_images.items():
        checked.append(name)
        errors.extend(inspect_png(directory / name, expected))

    contact_sheet, manifest = SUPPORT_FILES[phase]
    checked.append(contact_sheet)
    errors.extend(inspect_png(directory / contact_sheet, None))
    checked.append(manifest)
    errors.extend(inspect_manifest(directory / manifest, phase, expected_images))
    if phase == "selected":
        errors.extend(validate_source_binding(directory, source_manifest))
        if source_manifest is not None:
            checked.append(str(source_manifest))
    elif source_manifest is not None:
        errors.append("--source-manifest is only valid with --phase selected")

    thumbs_dir = directory / "thumbs"
    for name, expected in THUMB_FILES[phase].items():
        relative = f"thumbs/{name}"
        checked.append(relative)
        errors.extend(inspect_png(thumbs_dir / name, expected))

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
