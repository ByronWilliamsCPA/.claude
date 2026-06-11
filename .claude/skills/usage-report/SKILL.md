---
description: >
  Model and token usage reporting via ccusage. Summarizes per-project,
  per-model, and per-session token spend from local Claude Code transcripts,
  and checks the current five-hour billing block for loop safeguards.
  Triggers on: usage report, token usage, usage this week, how much have I
  used, model spend, cost report, five-hour block, usage blocks, /usage-report.
tools: ["Bash", "Read"]
---

# Usage Report Skill

Summarize Claude Code model and token usage from local JSONL transcripts using
[ccusage](https://github.com/ryoppippi/ccusage). No daemon, no telemetry
backend; ccusage parses `~/.claude/projects/**/*.jsonl` on each run.

Background and tool selection rationale:
[usage-monitoring-survey.md](../../../docs/reference/usage-monitoring-survey.md).

## Invocation

```text
/usage-report [daily|weekly|monthly|session|blocks] [extra ccusage flags]
```

Default mode when no argument is given: `daily` for the last 7 days, grouped
by project.

## Workflow

1. Map the requested mode to a ccusage command (pin the version; do not use
   `@latest`):

   | Mode | Command |
   | --- | --- |
   | daily (default) | `npx -y ccusage@20.0.9 daily --instances --since <YYYYMMDD> --json` |
   | weekly | `npx -y ccusage@20.0.9 weekly --json` |
   | monthly | `npx -y ccusage@20.0.9 monthly --json` |
   | session | `npx -y ccusage@20.0.9 session --json` |
   | blocks | `npx -y ccusage@20.0.9 blocks --active --json` |

   For daily mode, compute `<YYYYMMDD>` first with a separate command:
   `date -d '7 days ago' +%Y%m%d` (GNU date); on BSD/macOS use
   `date -v-7d +%Y%m%d`. Substitute the literal result into `--since`;
   do not embed the `date` command inside the ccusage invocation.

2. Run the command with Bash. Append extra user-supplied flags only when they
   match documented ccusage reporting options: long-form `--flag` or
   `--flag value` where the value is alphanumeric, a date, or a simple path
   (a relative path containing no `..` components, or an absolute path under
   `~/.claude/` or `/tmp/`). Never pass `--config`: it points ccusage at an
   arbitrary local file and is not a reporting flag. Never interpolate free
   text into the command line; reject any argument containing shell
   metacharacters (`;`, `|`, `&`, `$`, `>`, `<`, `(`, `)`, backslashes,
   single or double quotes, backticks, newlines) and say why.

3. Summarize the JSON. Lead with totals, then the top contributors:
   - Total tokens (input, output, cache read, cache creation) and estimated
     cost for the period.
   - Top 5 projects by token volume (daily/monthly modes).
   - Per-model split: tokens and estimated cost by model id. Flag any result
     that contradicts the CLAUDE.md Model Selection policy (for example, Opus
     spend on read-only exploration work).
   - For `blocks`: current block elapsed/remaining time, tokens consumed,
     and burn rate.

4. Always state the cost caveat once: ccusage costs are estimates against API
   list pricing; on a Max subscription they are a relative spend signal, not
   a bill.

## Loop circuit breaker check

When invoked as part of `/loop` safeguards (see
`.claude/rules/loop-recipes.md`), run the `blocks` mode and report:

- tokens consumed in the active five-hour block,
- projected tokens at the current burn rate,
- a clear PASS/STOP line: STOP if the projection exceeds the block limit
  ccusage reports (or the user-specified budget passed as an argument).

## Output

Terminal summary only; do not write report files unless the user asks.
Keep the summary under 30 lines: totals, top projects, per-model table,
one caveat line.
