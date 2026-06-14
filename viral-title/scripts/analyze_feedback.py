#!/usr/bin/env python3
"""Summarize recent title sessions and feedback into learning candidates."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
EVOLUTION_DIR = SKILL_DIR / "references" / "evolution"
DEFAULT_SESSIONS = EVOLUTION_DIR / "sessions.jsonl"
DEFAULT_FEEDBACK = EVOLUTION_DIR / "feedback.jsonl"
DEFAULT_OUTPUT = EVOLUTION_DIR / "learning-candidates.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", default=str(DEFAULT_SESSIONS))
    parser.add_argument("--feedback", default=str(DEFAULT_FEEDBACK))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--recent", type=int, default=20)
    parser.add_argument("--append", action="store_true")
    return parser.parse_args()


def chosen_title(row: dict[str, Any]) -> str:
    return str(row.get("user_edit") or row.get("selected_title") or "").strip()


def match_candidate(title: str, candidates: Any) -> dict[str, Any] | None:
    """Find the session candidate that produced the chosen title.

    Tries an exact match first, then a substring match so that lightly edited
    titles still resolve back to their originating formula/mechanism.
    """
    if not title or not isinstance(candidates, list):
        return None
    normalized = title.strip().lower()
    items = [c for c in candidates if isinstance(c, dict) and c.get("title")]
    for candidate in items:
        if str(candidate["title"]).strip().lower() == normalized:
            return candidate
    for candidate in items:
        cand_title = str(candidate["title"]).strip().lower()
        if cand_title and (cand_title in normalized or normalized in cand_title):
            return candidate
    return None


def main() -> int:
    args = parse_args()
    sessions = read_jsonl(Path(args.sessions))[-args.recent :]
    feedback = read_jsonl(Path(args.feedback))[-args.recent :]
    selected = [row.get("user_edit") or row.get("selected_title") for row in feedback if row.get("user_edit") or row.get("selected_title")]
    tags = Counter(tag for row in feedback for tag in row.get("tags", []))
    platforms = Counter(row.get("platform") for row in sessions + feedback if row.get("platform"))

    session_index = {row.get("session_id"): row for row in read_jsonl(Path(args.sessions)) if row.get("session_id")}
    formula_wins: Counter[str] = Counter()
    mechanism_wins: Counter[str] = Counter()
    platform_formula_wins: Counter[str] = Counter()
    unresolved = 0
    for row in feedback:
        title = chosen_title(row)
        if not title:
            continue
        session = session_index.get(row.get("session_id"))
        candidate = match_candidate(title, session.get("candidates")) if session else None
        if not candidate:
            unresolved += 1
            continue
        formula = str(candidate.get("formula") or "unknown")
        mechanism = str(candidate.get("mechanism") or "")
        platform = str(row.get("platform") or (session.get("platform") if session else "") or "unknown")
        formula_wins[formula] += 1
        platform_formula_wins[f"{platform}/{formula}"] += 1
        if mechanism:
            mechanism_wins[mechanism] += 1

    lines = [
        "## Auto Review",
        "",
        f"- Sessions analyzed: {len(sessions)}",
        f"- Feedback records analyzed: {len(feedback)}",
        f"- Platforms: {dict(platforms)}",
        f"- Frequent feedback tags: {dict(tags.most_common(10))}",
        "",
        "### Candidate Observations",
        "",
    ]
    if selected:
        lines.append("- User-selected or edited titles indicate these phrasing directions:")
        for title in selected[-10:]:
            lines.append(f"  - {title}")
    else:
        lines.append("- No selected-title feedback yet. Keep collecting choices before promoting rules.")

    lines.extend(
        [
            "",
            "### Winning Formulas (feedback joined to session candidates)",
            "",
        ]
    )
    if formula_wins:
        lines.append(f"- Formula win counts: {dict(formula_wins.most_common())}")
        if mechanism_wins:
            lines.append(f"- Mechanism win counts: {dict(mechanism_wins.most_common())}")
        if platform_formula_wins:
            lines.append(f"- Platform x formula win counts: {dict(platform_formula_wins.most_common())}")
        if unresolved:
            lines.append(f"- Unresolved feedback (no matching session candidate): {unresolved}")
    else:
        lines.append("- No feedback could be joined to session candidates yet.")
        lines.append("- Tip: log sessions with candidates as objects, e.g. {\"title\": \"...\", \"formula\": \"结果承诺型\", \"mechanism\": \"tool replacement\"}, so wins resolve back to a formula.")
        if unresolved:
            lines.append(f"- Feedback rows with a chosen title but no matching candidate: {unresolved}")

    lines.extend(
        [
            "",
            "### Suggested Next Step",
            "",
            "- Promote nothing automatically. Compare repeated feedback patterns against eval cases first.",
            "",
        ]
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines)
    if args.append and output.exists():
        output.write_text(output.read_text(encoding="utf-8").rstrip() + "\n\n" + text + "\n", encoding="utf-8")
    else:
        output.write_text("# Learning Candidates\n\n" + text + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "sessions": len(sessions), "feedback": len(feedback), "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
