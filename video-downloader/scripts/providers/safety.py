"""Helpers for keeping provider metadata safe to persist or publish."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def sanitize_url(value: object) -> str | None:
    """Keep only a public HTTP(S) origin and path.

    User information, query parameters, and fragments may carry cookies,
    signatures, or short-lived media tokens, so they are never persisted.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = urlsplit(value.strip())
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not host:
        return None
    rendered_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    netloc = f"{rendered_host}:{port}" if port is not None else rendered_host
    return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "", "", ""))


def artifact_basename(value: str | Path | None) -> str | None:
    """Return a portable artifact name without exposing its local directory."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.replace("\\", "/").rsplit("/", 1)[-1] or None
