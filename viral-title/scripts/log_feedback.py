#!/usr/bin/env python3
"""Append user feedback for a title-generation session."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LOG = SKILL_DIR / "references" / "evolution" / "feedback.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--session-id", default="")
    parser.add_argument("--platform", default="")
    parser.add_argument("--selected-title", default="")
    parser.add_argument("--user-edit", default="")
    parser.add_argument("--rating", type=int, choices=range(1, 6), default=None)
    parser.add_argument("--feedback", default="")
    parser.add_argument("--tags", default="", help="Comma-separated tags, e.g. too-flat,wechat-fit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": args.session_id,
        "platform": args.platform,
        "selected_title": args.selected_title,
        "user_edit": args.user_edit,
        "rating": args.rating,
        "feedback": args.feedback,
        "tags": [tag.strip() for tag in args.tags.split(",") if tag.strip()],
    }
    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, "log": str(log_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
