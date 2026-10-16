#!/usr/bin/env python3
"""agent-guardrails: PreToolUse / PostToolUse hook for Claude Code.

Standard library only. Reads the hook JSON on stdin.

PreToolUse (Bash, Write, Edit, MultiEdit, NotebookEdit):
  1. Kill switch  - blocks every write while a STOP file exists
                    (<project>/.claude/STOP or ~/.claude/STOP) or AGENT_STOP=1.
  2. Deny rules   - blocks risky shell commands (force-push to main, rm -rf on
                    / or ~, piping curl into a shell, DROP DATABASE, ...).
                    Extend or relax them in <project>/.claude/guardrails.json.
  3. Daily caps   - optional: at most N matching Bash commands per day
                    (e.g. deploys or posts), counted in the ledger.
  4. Ledger       - appends an "attempt" row before the call.
PostToolUse: appends a "done" row, so an attempt without a done is visible.

Exit code 2 blocks the call and shows the reason to Claude.
Any internal error exits 0 (fail open) so a broken guard never bricks a session;
the error is written to the ledger as "guard_error".
"""
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

WRITE_TOOLS = {"Bash", "Write", "Edit", "MultiEdit", "NotebookEdit"}

DEFAULT_DENY = [
    {"id": "force-push-main", "pattern": r"git\s+push\b.*(--force\b|-f\b|--force-with-lease\b).*\b(main|master)\b",
     "reason": "force-push to main/master"},
    {"id": "rm-root-home", "pattern": r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\s+(/|~|\$HOME)(\s|$|/\*)",
     "reason": "recursive delete of / or home"},
    {"id": "curl-pipe-shell", "pattern": r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(sh|bash|zsh|python3?)\b",
     "reason": "piping a download straight into a shell"},
    {"id": "drop-database", "pattern": r"\bdrop\s+(database|schema)\b", "flags": "i",
     "reason": "DROP DATABASE/SCHEMA"},
    {"id": "git-reset-hard-remote", "pattern": r"git\s+reset\s+--hard\s+origin/(main|master)\b",
     "reason": "hard reset to remote main (discards local work)"},
    {"id": "chmod-777-recursive", "pattern": r"\bchmod\s+-R\s+777\b", "reason": "recursive chmod 777"},
]


def now():
    return dt.datetime.now().astimezone()


def project_dir(data):
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())


def load_config(proj):
    p = proj / ".claude" / "guardrails.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception as e:  # a broken config must be visible, not silently ignored
            return {"_config_error": f"{p}: {e}"}
    return {}


def ledger_path(proj):
    d = proj / ".claude" / "guardrails"
    d.mkdir(parents=True, exist_ok=True)
    return d / "ledger.jsonl"


def append(proj, row):
    row["at"] = now().isoformat(timespec="seconds")
    with ledger_path(proj).open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def summarize(tool, ti):
    if tool == "Bash":
        return (ti.get("command") or "")[:300]
    return str(ti.get("file_path") or ti.get("notebook_path") or "")[:300]


def stop_reason(proj):
    if os.environ.get("AGENT_STOP", "").strip() not in ("", "0", "false"):
        return "AGENT_STOP is set"
    for p in (proj / ".claude" / "STOP", Path.home() / ".claude" / "STOP"):
        if p.exists():
            return f"kill switch file exists: {p}"
    return None


def deny_reason(cmd, cfg):
    rules = [] if cfg.get("disable_default_deny") else list(DEFAULT_DENY)
    allow_ids = set(cfg.get("allow_ids", []))
    rules = [r for r in rules if r["id"] not in allow_ids] + list(cfg.get("deny", []))
    for r in rules:
        flags = re.I if "i" in r.get("flags", "") else 0
        if re.search(r["pattern"], cmd, flags):
            return f"{r.get('reason', r['pattern'])} (rule '{r.get('id', 'custom')}')"
    return None


def cap_reason(proj, cmd, cfg):
    caps = cfg.get("daily_caps", [])
    if not caps:
        return None
    lp = ledger_path(proj)
    today = now().date().isoformat()
    rows = []
    if lp.exists():
        for line in lp.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("event") == "attempt" and r.get("at", "").startswith(today):
                rows.append(r)
    for c in caps:
        pat = c["pattern"]
        if re.search(pat, cmd):
            used = sum(1 for r in rows if r.get("tool") == "Bash" and re.search(pat, r.get("summary", "")))
            if used >= int(c["max"]):
                return f"daily cap reached for '{c.get('id', pat)}': {used}/{c['max']} today"
    return None


def block(proj, tool, summary, reason):
    append(proj, {"event": "blocked", "tool": tool, "summary": summary, "reason": reason})
    print(f"agent-guardrails blocked this {tool} call: {reason}. "
          f"If this is intended, ask the user to change .claude/guardrails.json or remove the STOP file.",
          file=sys.stderr)
    sys.exit(2)


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name", "PreToolUse")
    tool = data.get("tool_name", "")
    if tool not in WRITE_TOOLS:
        return 0
    proj = project_dir(data)
    ti = data.get("tool_input") or {}
    summary = summarize(tool, ti)
    key = hashlib.sha256(json.dumps([tool, ti], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]

    if event == "PostToolUse":
        append(proj, {"event": "done", "tool": tool, "summary": summary, "key": key})
        return 0

    cfg = load_config(proj)
    if "_config_error" in cfg:
        block(proj, tool, summary, "guardrails.json is not valid JSON: " + cfg["_config_error"])
    r = stop_reason(proj)
    if r:
        block(proj, tool, summary, r)
    if tool == "Bash":
        cmd = ti.get("command") or ""
        r = deny_reason(cmd, cfg) or cap_reason(proj, cmd, cfg)
        if r:
            block(proj, tool, summary, r)
    append(proj, {"event": "attempt", "tool": tool, "summary": summary, "key": key})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # fail open, but leave a trace
        try:
            append(Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()),
                   {"event": "guard_error", "error": f"{type(e).__name__}: {e}"})
        except Exception:
            pass
        sys.exit(0)
