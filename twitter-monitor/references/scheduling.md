# Scheduling

Offer scheduling only after a one-shot fetch works or when the user explicitly asks for recurring monitoring.

Options:

- **OpenClaw**: Prefer this when the user already works in OpenClaw or asks for agent-run recurring jobs. Create a repeatable command that exports `TWITTER_API_KEY`, runs `scripts/twitter_monitor.py`, then performs any requested Feishu sync.
- **Codex automation**: Use when the current environment supports reminders/automations and the user wants the agent thread to wake up and run the job.
- **cron**: Use for simple Linux/macOS shell schedules.
- **launchd**: Use for persistent macOS user jobs when cron is not appropriate.

Before creating any schedule, confirm:

1. Account ids.
2. API key source, preferably an environment variable or secret manager.
3. Page count and time window.
4. Output destination.
5. Feishu target, if applicable.

Keep recurring commands idempotent by deduplicating on `推文ID` before appending to a durable destination.
