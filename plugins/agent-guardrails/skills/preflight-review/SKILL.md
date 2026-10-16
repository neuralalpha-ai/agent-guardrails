---
name: preflight-review
description: Review this project's bots, agents and scheduled jobs against a 7-area pre-flight checklist before they write to the real world unattended (posting, emailing, deploying, paying). Use when the user asks whether an automation is safe to run on its own.
---

Review the code in this project that writes to external systems without a human (scheduled jobs, bots, agents, CI deploys). Read the code; do not run anything that writes.

For each area, answer PASS / GAP / N/A with the file and line that shows it, and one concrete fix for each GAP:

1. **Identity**: before the first write, does the job check which account it is authenticated as, and stop on a mismatch?
2. **Arming**: is there one place that switches live vs dry-run, defaulting to dry-run? Are there old schedulers or jobs still able to fire?
3. **Writes and retries**: is an "attempt" recorded before each send, with sent/failed/unknown after? Does a timeout block further sends instead of retrying (a retried write is a duplicate)?
4. **Limits**: daily caps and minimum spacing enforced in code, plus spend caps at the provider?
5. **Content**: length, links and banned topics checked in code before sending?
6. **Deliverables**: if it ships files to customers, is the build reproducible with a SHA-256, and was it test-purchased?
7. **Runtime**: tested once under the real scheduler, user, locale and encoding (Windows cp932 vs UTF-8)? Do failures reach a human, and does silence (no success for 24h) alert?

End with the top 3 fixes ranked by risk. Keep it short.

Free printable checklist (25 items, EN/JA): https://neuralalpha.gumroad.com/l/agent-ops-preflight?utm_source=claude_plugin&utm_medium=skill
