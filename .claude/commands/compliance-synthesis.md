# Compliance Synthesis

Invoke the `compliance-synthesis` agent to produce a cross-session
synthesis report from the central master log. Runs on-demand;
scheduled invocations come from the weekly cron registration.

## Arguments (optional)

- `--since YYYY-MM-DD` -- override the synthesis window start.
- `--mode scheduled|on-demand` -- defaults to `on-demand` when invoked
  manually; the scheduler passes `scheduled`.

## Steps

### 1. Invoke the agent

Use the Agent tool with `subagent_type: "compliance-synthesis"` and
pass a prompt that supplies:

- `central_root`: `docs/compliance-reports/` (resolved by the agent
  via repo discovery)
- `synthesis_window_start`: from `--since`, the
  `state/last-synthesis-date.txt` content, or 90 days back
- `synthesis_window_end`: today (UTC)
- `invocation_mode`: from `--mode`, or `on-demand`

### 2. Review the output

The agent writes the synthesis to
`docs/compliance-reports/synthesis/<today>.md`. Read it:

```bash
ls -t docs/compliance-reports/synthesis/ | head -1 \
  | xargs -I{} cat docs/compliance-reports/synthesis/{}
```

### 3. Commit the synthesis report

```bash
git add docs/compliance-reports/synthesis/
git commit -m "docs(compliance): add synthesis report <today>"
```

## When to use

- Right after a fleet-wide audit sweep, to capture cross-session
  patterns while findings are fresh.
- Before quarterly compliance reviews, with `--since` set to the
  quarter start.
- After resolving a backlog of fleet actions, to verify the
  follow-through insight detects the changes correctly.

Scheduled invocations (Mondays 09:37 local) cover the routine cadence;
this command is for ad-hoc reports.
