# agent-guardrails for Claude Code

A small Claude Code plugin that puts guardrails on the tool calls that change things: `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`.

- **Kill switch**: create `.claude/STOP` (or `~/.claude/STOP`, or set `AGENT_STOP=1`) and every write is blocked until you remove it.
- **Deny rules for risky shell commands**: force-push to main, `rm -rf ~`, `curl … | sh`, `DROP DATABASE`, `git reset --hard origin/main`, `chmod -R 777`. Relax or extend them per project.
- **Daily caps**: e.g. at most 2 runs of your deploy or post script per day.
- **Ledger**: every write gets an `attempt` row before it runs and a `done` row after, in `.claude/guardrails/ledger.jsonl`. An `attempt` without a `done` is a call that may not have finished. Check it before re-running anything.

Python standard library only. One script, 11 tests. MIT.

## Install

In Claude Code:

```
/plugin marketplace add neuralalpha-ai/agent-guardrails
/plugin install agent-guardrails@neuralalpha
```

Requires `python3` on PATH. On Windows, if only `python` exists, install Python from python.org (it provides the `py` launcher) or add a `python3` alias; otherwise the hook fails open (it never blocks, and Claude Code shows a hook error).

## Use

- `/agent-guardrails:stop-agent on` – freeze writes in this project. `status` shows the switch and the last ledger rows.
- `/agent-guardrails:preflight-review` – review this project's bots and scheduled jobs against a 7-area pre-flight checklist.
- Blocked calls show the reason to Claude, and are logged as `blocked`.

## Configure (optional)

`.claude/guardrails.json` in your project:

```json
{
  "allow_ids": ["curl-pipe-shell"],
  "deny": [
    { "id": "no-prod-deploy", "pattern": "deploy.*--env\\s+prod", "reason": "prod deploys go through CI" }
  ],
  "daily_caps": [
    { "id": "posts", "pattern": "post_once\\.py", "max": 2 }
  ]
}
```

Add `.claude/guardrails/` to your `.gitignore` if you do not want the ledger committed.

A config that isn't valid JSON blocks writes (so a typo can't silently switch your rules off). Any other internal error fails open and is logged as `guard_error`.

## What it is not

A guard on Claude Code's own tool calls. It does not watch scripts that run outside Claude Code (cron, CI, your own bots). Not security advice. Read `scripts/guard.py` (about 170 lines) before relying on it.

## More

- Free 1-page pre-flight checklist (25 items): https://neuralalpha.gumroad.com/l/agent-ops-preflight?utm_source=github&utm_medium=readme
- Guardrails for the scripts themselves (write ledger, kill switch, caps, identity check, heartbeat, spend meter, reproducible release ZIPs, with tests): [Agent Ops Guardrails Kit](https://neuralalpha.gumroad.com/l/agent-ops-guardrails-kit?utm_source=github&utm_medium=readme)
- Free single-file write ledger: https://github.com/neuralalpha-ai/agent-write-ledger
- Weekly notes: https://neuralalphaai.substack.com/?utm_source=github&utm_medium=readme

## 日本語

Claude Code の書き込み系ツール（Bash・Write・Edit など）にガードを掛けるプラグインです。

- `.claude/STOP` を置くと、すべての書き込みを止める（緊急停止）
- main への force-push、`rm -rf ~`、`curl | sh`、`DROP DATABASE` などの危険なコマンドを止める
- 1日あたりの回数上限（デプロイ・投稿スクリプトなど）
- 実行前に `attempt`、実行後に `done` を記録（`.claude/guardrails/ledger.jsonl`）。`done` のない `attempt` は、完了したか分からない呼び出しです

インストールは上の2行のコマンドです。日本語のチェックリスト（無料）：https://neuralalpha.gumroad.com/l/agent-ops-preflight-ja?utm_source=github&utm_medium=readme
