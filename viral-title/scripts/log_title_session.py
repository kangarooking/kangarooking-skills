#!/usr/bin/env python3
"""Append a title-generation session to the viral-title evolution log."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LOG = SKILL_DIR / "references" / "evolution" / "sessions.jsonl"


def load_json_arg(value: str | None) -> Any:
    if not value:
        return None
    if value == "-":
        import sys

        return json.load(sys.stdin)
    stripped = value.strip()
    if stripped.startswith(("{", "[")):
        return json.loads(stripped)
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(stripped)


def compact_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--record-json", help="JSON object, path to JSON file, or '-' for stdin. Merged with CLI fields.")
    parser.add_argument("--platform", default="")
    parser.add_argument("--topic", default="")
    parser.add_argument("--content-summary", default="")
    parser.add_argument("--recommended-title", default="")
    parser.add_argument("--selected-title", default="")
    parser.add_argument(
        "--candidates-json",
        help=(
            "JSON array/object, path to JSON file, or '-' for stdin. "
            "For the feedback loop to learn which formula wins, use objects like "
            '{"title": "...", "formula": "结果承诺型", "mechanism": "tool replacement"}.'
        ),
    )
    parser.add_argument("--notes", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = load_json_arg(args.record_json) or {}
    if not isinstance(base, dict):
        raise SystemExit("--record-json must be a JSON object")

    candidates = load_json_arg(args.candidates_json)
    record: dict[str, Any] = {
        **base,
        "created_at": base.get("created_at") or datetime.now(timezone.utc).isoformat(),
        "platform": args.platform or base.get("platform", ""),
        "topic": args.topic or base.get("topic", ""),
        "content_summary": args.content_summary or base.get("content_summary", ""),
        "recommended_title": args.recommended_title or base.get("recommended_title", ""),
        "selected_title": args.selected_title or base.get("selected_title", ""),
        "notes": args.notes or base.get("notes", ""),
    }
    if candidates is not None:
        record["candidates"] = candidates
    record["session_id"] = base.get("session_id") or compact_hash(record)

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, "session_id": record["session_id"], "log": str(log_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
