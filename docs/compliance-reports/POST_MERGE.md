---
schema_type: common
title: Post-Merge Steps for Compliance Aggregation
status: published
owner: engineering
purpose: "One-time operational steps required after the compliance retrospective aggregation feature merges to main."
tags:
  - compliance
---

When `feat/compliance-aggregation` merges to main, two manual cleanup
steps land outside the branch's commits. Run them once on the merging
checkout to finish consolidating the central root.

## 1. Migrate legacy session retrospectives

The pre-existing `docs/compliance-retrospectives/` directory holds
ad-hoc session retrospectives that pre-date the new central root. The
gitignore policy keeps them local-only. The spec's canonical layout
relocates them under `docs/compliance-reports/archive/sessions/`,
which is also gitignored. The move is filesystem-only; no commits.

Run from the project root:

```bash
mkdir -p docs/compliance-reports/archive/sessions
mv docs/compliance-retrospectives/*.md docs/compliance-reports/archive/sessions/ 2>/dev/null || true
rmdir docs/compliance-retrospectives 2>/dev/null || true
```

The `|| true` guards keep the script idempotent on re-run. After the
move, `docs/compliance-retrospectives/` should be empty or absent.

## 2. Register the weekly synthesis scheduler

See `docs/compliance-reports/SCHEDULER.md`. Briefly: invoke
`CronCreate` with `cron='37 9 * * 1'`, `prompt='/compliance-synthesis --mode scheduled'`,
`recurring=true`, `durable=true`. The synthesis agent re-registers
itself on every successful run, so this is a one-time setup.

## Verification

After both steps:

- `ls docs/compliance-retrospectives/` returns "No such file or directory"
  or shows the directory is empty.
- `ls docs/compliance-reports/archive/sessions/` shows the migrated
  Markdown files alongside `.gitkeep`.
- `cat docs/compliance-reports/state/scheduler-registered.txt` shows
  the cron job ID returned by CronCreate.
