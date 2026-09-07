"""Small, privacy-safe cache manifests for derived video artifacts."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path


FINGERPRINT_CHUNK_BYTES = 1024 * 1024


def source_fingerprint(path: Path) -> dict:
    """Identify source replacement without persisting its absolute local path."""
    resolved = path.expanduser().resolve()
    stat = resolved.stat()
    digest = hashlib.sha256()
    digest.update(str(stat.st_size).encode("ascii"))
    with resolved.open("rb") as handle:
        digest.update(handle.read(FINGERPRINT_CHUNK_BYTES))
        if stat.st_size > FINGERPRINT_CHUNK_BYTES:
            handle.seek(max(0, stat.st_size - FINGERPRINT_CHUNK_BYTES))
            digest.update(handle.read(FINGERPRINT_CHUNK_BYTES))
    return {
        "name": resolved.name,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "edge_sha256": digest.hexdigest(),
    }


def manifest_matches(path: Path, expected: dict) -> bool:
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return current == expected


def write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def result_path(directory: Path, identity: dict) -> Path:
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return directory / f'{digest}.json'


def read_result(path: Path) -> dict | None:
    try:
        envelope = json.loads(path.read_text(encoding='utf-8'))
        result = envelope['result']
        digest = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return result if isinstance(result, dict) and envelope.get('sha256') == digest else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def write_result(path: Path, result: dict) -> None:
    digest = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    write_manifest(path, {'result': result, 'sha256': digest})
