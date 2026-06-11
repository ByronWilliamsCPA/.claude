# Close Session

Wind down the current session: snapshot state, complete the task-observer
process, and (on a feature branch) decide how to finish the branch. Use this at
the end of a working session before starting a fresh one. For a version that
also cleans up worktrees and stale content, use `/close-clean`.

This command never deletes anything and never integrates work without your
confirmation. The only step that can mutate the repo is the branch decision,
and it runs only on a feature branch and only on your choice.

## Steps

### 1. Snapshot session state (read-only, plus one local usage-log line)

Run and present a compact summary:

```bash
git branch --show-current
git status --short
git log --oneline -5
git worktree list
```

Also capture session usage via the `usage-report` skill (or directly:
`npx -y ccusage@20.0.9 blocks --active --json`). Include in the summary the
active five-hour block's tokens, estimated cost, and per-model split, then
append one line to `~/.claude/logs/session-usage.log` in the form
`timestamp|branch|tokens|est_cost_usd|models`. The log is a gitignored runtime
file (the same pattern as `track-mcp-usage.sh`), so this does not mutate the
repo. If ccusage is unavailable (for example, offline), note that and
continue; usage capture never blocks the wind-down.

Also list any in-progress TodoWrite items from this session. From the current
branch name, decide whether this is a feature branch, defined as any branch
other than `main` or `master`. A detached HEAD (empty `git branch
--show-current` output) is not a feature branch: treat it as non-feature and
skip Step 3, so the branch decision never runs on a detached checkout. Report
the branch and state whether Step 3 will run.

### 2. Complete the task-observer process

Invoke the `task-observer` skill and run its Surfacing Protocol for this
session:

- Run the five-point self-enforcement check on the session's observations.
- Present logged observations grouped by skill (improvements), with new-skill
  candidates listed separately, each tagged open-source or internal.
- Ask which, if any, to act on.

Honor the skill's default of "log, don't act": surface and ask; do not rewrite
any skill unless the user asks you to here. If no observations were logged this
session, say so and continue.

### 3. Finish the branch (feature branches only)

If Step 1 found a feature branch, invoke the `finishing-a-development-branch`
skill and follow it: verify tests pass, then present the merge / PR / keep /
discard options, then clean up that branch's own worktree per the choice.

If the current branch is `main` or `master`, skip this step and say so. Do not
prompt for a branch decision on the default branch.

## Hard rules

- Never discard, stash-drop, or overwrite uncommitted tracked changes.
- Never run `git` with `--no-verify`, `--no-gpg-sign`, `--force`, or
  `gh pr merge --admin`.
- The only mutating step is Step 3, and only on a feature branch with an
  explicit choice.
