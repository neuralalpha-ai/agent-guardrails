---
name: stop-agent
description: Turn the agent-guardrails kill switch on or off, or show its status. Use when the user says stop, pause, freeze, kill switch, or resume for agent writes in this project.
argument-hint: "[on|off|status]"
---

The agent-guardrails plugin blocks every Bash, Write and Edit call while the file `.claude/STOP` exists in the project (or `~/.claude/STOP` for all projects, or the env var `AGENT_STOP=1`).

- `on` (default): create `.claude/STOP` in the project root with one line saying who stopped it and when. After that, tell the user writes are frozen. Note: creating the file is itself a Write call, so if the switch is already on, just report it.
- `off`: the switch blocks your own writes, so you cannot remove it. Tell the user to delete `.claude/STOP` themselves (Windows: `del .claude\STOP`, macOS/Linux: `rm .claude/STOP`). Never try to bypass the guard.
- `status`: report whether `.claude/STOP` or `~/.claude/STOP` exists, and show the last 10 rows of `.claude/guardrails/ledger.jsonl`, pointing out any `attempt` without a matching `done` (a call that may not have finished).
