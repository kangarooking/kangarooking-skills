# Viral Title Evolution Rules

## Core Principle

Keep the hot path short. Store more experience over time, but load only the smallest relevant slice during title generation.

## Allowed Automatically

- Append title-generation sessions to `references/evolution/sessions.jsonl` when the content is not sensitive.
- Append user choices, edits, ratings, and comments to `references/evolution/feedback.jsonl`.
- Add candidate observations to `references/evolution/learning-candidates.md`.
- Retrieve up to 20 relevant title examples from libraries.
- Generate evaluation reports under temporary output paths.

## Requires User Confirmation

- Modify `SKILL.md`.
- Modify platform methodology files under `references/platforms/`.
- Promote candidate rules into `references/evolution/promoted-rules.md`.
- Add or remove large title-library files.
- Delete, rewrite, or compact historical logs.

## Never Do

- Load full session history during ordinary title generation.
- Load full title libraries when retrieval can return relevant examples.
- Promote a rule from a single user correction.
- Treat time-sensitive hotspot titles as timeless formulas.
- Store secrets, private credentials, or unpublished article drafts in permanent logs unless the user explicitly asks.
- Store full source articles or long unpublished drafts by default. Instead, store only titles, concise topic summaries, platform, ratings, tags, and feedback.

## Token Budget Guardrails

- `SKILL.md`: target under 150 lines.
- Platform method file: target under 200 lines.
- `promoted-rules.md`: keep at most 30 active rules.
- `anti-patterns.md`: keep at most 30 active anti-patterns.
- Retrieval: return 10 examples by default, 20 maximum.
- Evolution review: analyze batches of 5-20 sessions, then summarize.
