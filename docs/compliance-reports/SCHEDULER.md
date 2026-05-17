---
schema_type: common
title: Compliance Synthesis Scheduler Registration
status: published
owner: engineering
purpose: "Operational instructions for registering and verifying the weekly compliance synthesis cron job."
tags:
  - compliance
---

The compliance synthesis agent runs weekly via Claude Code's scheduler.
Registration is a one-time setup step after this feature branch lands
on main. The agent re-registers itself on every successful run, so the
cadence is self-perpetuating thereafter.

## When to register

After `feat/compliance-aggregation` merges to main and the agent files
(`compliance-synthesis.md`, `compliance-rollup.md`, the renderer and
reconciler scripts) are present on the trunk branch. Registering
earlier means the scheduler fires `/compliance-synthesis` against a
trunk that does not have the agent yet, and the invocation will fail
silently each week.

## How to register

In any Claude Code session, invoke the `CronCreate` tool with:

| Parameter | Value |
|---|---|
| `cron` | `37 9 * * 1` |
| `prompt` | `/compliance-synthesis --mode scheduled` |
| `recurring` | `true` |
| `durable` | `true` |

Notes:

- `37 9` is an off-peak minute. Avoid `0 9` to keep fleet-wide load
  distributed across the hour.
- `durable: true` writes to `.claude/scheduled_tasks.json` so the
  registration survives session restarts. If your runtime reports
  "Session-only" despite passing `durable: true`, the durable mode is
  not active in your environment; register again from a durable
  session.
- The Claude Code scheduler expires all jobs after seven days. The
  synthesis agent re-registers itself as its final workflow step, so
  the cadence self-heals as long as runs succeed. A failed run breaks
  the chain and stops the cadence cleanly until manually re-registered.

After registration, record the returned job ID for reference:

```bash
# Replace <job-id> with the value CronCreate returned.
echo "<job-id>" > docs/compliance-reports/state/scheduler-registered.txt
```

`state/scheduler-registered.txt` is gitignored (per the runtime state
policy); it is local-only.

## How to verify

```bash
# In a Claude Code session, invoke the CronList tool. The job named
# above should appear with the cron expression and the prompt body.
```

## How to cancel

```bash
# Use CronDelete with the job ID stored in state/scheduler-registered.txt.
```

## What happens on a failed scheduled run

The synthesis agent re-registers the next run only on success. A
crash, an expected-but-empty insight window, or a write failure during
report generation will stop the cadence after the seven-day expiry.
Restart by re-running this registration procedure manually.
