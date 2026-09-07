"""Make persisted metadata portable and safe to share for review."""

from __future__ import annotations

import re
from pathlib import Path

from providers.safety import sanitize_url


AUTHORIZATION_RE = re.compile(
    r"(?i)\bauthorization\s*:\s*bearer\s+[^\s,;]+|\bauthorization\s*:\s*[^\s,;]+"
)
BEARER_RE = re.compile(r"(?i)\bbearer\s+[^\s,;]+")
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"hy_user|hy_token|token|cookie|secret)\b\s*[:=]?\s*[^\s,;]+"
)
URL_RE = re.compile(r"https?://[^\s<>'\"]+", re.IGNORECASE)


def sanitize_metadata_tree(value, *, artifact_root: Path, key: str = ""):
    """Recursively remove local directories and credentials from JSON metadata."""
    if isinstance(value, dict):
        return {
            item_key: sanitize_metadata_tree(item_value, artifact_root=artifact_root, key=item_key)
            for item_key, item_value in value.items()
            if item_key != "raw_ytdlp_metadata"
        }
    if isinstance(value, list):
        return [sanitize_metadata_tree(item, artifact_root=artifact_root, key=key) for item in value]
    if isinstance(value, str):
        if key == "error" or key.endswith("_error"):
            return redact_error_text(value)
        if key == "path" or key.endswith("_path"):
            return portable_path(value, artifact_root)
        if key in {"url", "uri"} or key.endswith("_url") or key.endswith("_uri"):
            return sanitize_url(value)
    return value


def portable_path(value: str, artifact_root: Path) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(artifact_root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.name


def redact_error_text(value: str) -> str:
    redacted = AUTHORIZATION_RE.sub("Authorization: [REDACTED]", value)
    redacted = BEARER_RE.sub("Bearer [REDACTED]", redacted)
    redacted = SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)

    def replace_url(match: re.Match[str]) -> str:
        sanitized = sanitize_url(match.group(0).rstrip(".,);]"))
        return sanitized or "[REDACTED-URL]"

    return URL_RE.sub(replace_url, redacted)[:1000]
