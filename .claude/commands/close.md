# Close Session

Wind down the current session: snapshot state, complete the task-observer
process, and (on a feature branch) decide how to finish the branch. Use this at
the end of a working session before starting a fresh one. For a version that
also cleans up worktrees and stale content, use `/close-clean`.

If you want a resumable handoff, run `/handoff` first: it writes a durable doc
and a paste-ready kickoff prompt to `~/.claude/logs/handoffs/` (gitignored, not
committed, outside this repo's cleanup sweep). `/close` does not generate one.

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

The primary checkout's `git branch --show-current` is a starting point, not
the answer: this session's actual commits may have landed in a different
worktree, or a concurrent session may have moved HEAD on the branch shown
here. Cross-check `git worktree list` against which worktree (if any)
actually received this session's commits or edits, and if they differ, report
both and route Step 3 to the session's own branch, or skip Step 3 and say why,
rather than defaulting to the primary checkout. Also check for an in-flight
operation before Step 3 runs: `git rev-parse --git-dir` then look for
`rebase-merge`, `rebase-apply`, `MERGE_HEAD`, or `CHERRY_PICK_HEAD`; if any is
present, stop and report it rather than proceeding, since finishing an
in-flight operation this session did not start is not this step's job.

For any untracked file matching a secret-shaped pattern (`.env*`, `*.pem`,
`*_secret*`), run `git check-ignore -v <file>` and flag it prominently if NOT
covered by `.gitignore`. Also classify each dirty path from `git status
--short`: user/concurrent-session work (preserve untouched), agent-caused
index state from a read-intended command (restore to HEAD and disclose), or
unknown (surface and ask). Note that `git checkout <tree> -- <path>` is a
write, not a read, and can misattribute an agent's read-intended command as
user work; prefer `git show <tree>:<path>` when the intent is only to read.

Also capture session usage via the `usage-report` skill (or directly:
`npx -y ccusage@20.0.9 blocks --active --json`). Include in the summary the
active five-hour block's tokens, estimated cost, and per-model split, then
append one line to `~/.claude/logs/session-usage.log`, keyed to the block id
ccusage returns (e.g. `2026-08-09T13:00:00.000Z`) so a machine running
concurrent sessions writes at most one row per block rather than
double-counting: `block_id|branch|input|output|cache_read|cache_create|est_cost_usd|models`.
This file is an attribution record, not an additive ledger; do not sum its
token columns across rows as if they were independent. The log is a gitignored
runtime file (the same pattern as `track-mcp-usage.sh`), so this does not
mutate the repo. If ccusage is unavailable (for example, offline), note that
and continue; usage capture never blocks the wind-down.

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
skill and follow it against the session's own branch identified in Step 1 (not
necessarily the primary checkout's current branch): verify tests pass, then
present the merge / PR / keep / discard options, then clean up that branch's
own worktree per the choice.

If Step 1 found an in-flight rebase, merge, or cherry-pick on that branch,
skip this step and report it instead; do not attempt to finish an operation
this session did not start.

Do not short-circuit the skill's pre-PR check: before offering the PR or merge
option it fetches `origin` and diffs the branch against the base to detect work
that already landed through another channel (Obs 296). A local branch with
unpushed commits is not proof the work is unlanded. If the branch's changes are
already present on the base, surface that and offer rescope-or-skip rather than
defaulting to a duplicate PR.

If the current branch is `main` or `master`, skip this step and say so. Do not
prompt for a branch decision on the default branch.

## Hard rules

- Never discard, stash-drop, or overwrite uncommitted tracked changes.
- Never run `git` with `--no-verify`, `--no-gpg-sign`, `--force`, or
  `gh pr merge --admin`.
- The only mutating step is Step 3, and only on a feature branch with an
  explicit choice.
