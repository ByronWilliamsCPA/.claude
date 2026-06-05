---
schema_type: common
title: Session-close commands (/close and /close-clean)
status: draft
owner: engineering
tags: [automation, tooling, skills, safety, guardrails]
purpose: Design for two global slash commands that wind down a Claude Code session. /close runs a three-step full wind-down (read-only state snapshot, task-observer surfacing, and a conditional finishing-a-development-branch decision on feature branches). /close-clean performs the entire /close procedure, then runs a two-tier cleanup, where Tier A silently removes regenerable gitignored artifacts and Tier B previews stale temp files, finished worktrees, and stale skill workspaces for a single confirm before deletion. Both commands enforce hard safety invariants that never discard uncommitted tracked work, never remove dirty or unmerged worktrees, and never bypass commit signing or verification.
---

## Context

A recent global standard (CLAUDE.md "Session length") instructs Claude to flag
long-running sessions and recommend a clean break before starting a new task.
That guidance works, but it has increased session count, and each session needs
a deliberate close so the task-observer skill completes its end-of-session
surfacing and so accumulated worktrees and scratch content get cleaned up. Today
that wind-down is manual and ad hoc: the operator must remember to invoke
task-observer surfacing, decide what to do with the working branch, and
periodically sweep stale worktrees and temp files by hand.

This design adds two global slash commands that make the wind-down a single
deterministic action.

### What "the task observer completes its process" means

The task-observer skill (`~/.claude/skills/task-observer/SKILL.md`) defines a
**Surfacing Protocol** (SKILL.md:852). At end of session it:

1. Runs a five-point self-enforcement check (observations logged throughout the
   session, logged silently, correct Issue/Suggested-improvement/Principle
   format, correct open-source/internal type, section references for
   existing-skill improvements, no client-identifying info in open-source
   Principles).
2. Presents the session's logged observations as a grouped summary: improvements
   grouped by skill name, new-skill candidates listed separately, each tagged
   open-source or internal.
3. Asks which (if any) the user wants to act on, handing accepted items to
   skill-creator.

Crucially, task-observer's default outside a comprehensive review is **"log,
don't act"** (SKILL.md "Acting on Observations"). `/close` therefore surfaces
and asks; it does not silently rewrite skills.

### Relationship to existing skills

- `handoff` writes a continuity document. Not invoked by these commands; the
  operator runs `/handoff` separately when a resumable doc is wanted.
- `finishing-a-development-branch` presents the merge / PR / keep / discard
  decision and cleans up **the current branch's own worktree**. `/close`
  invokes it conditionally. The `/close-clean` "finished worktrees" sweep is
  complementary: it removes **other** already-finished worktrees, not the one
  the current branch lives in.

Neither existing skill triggers task-observer surfacing, so these commands fill
a real gap rather than duplicating one.

## Goals

- Single-keystroke session wind-down that reliably completes task-observer
  surfacing.
- An opt-in cleaning variant that removes accumulated cruft without ever
  endangering real work.
- Generic across repositories: both commands operate on the current repo,
  discovered via git, so categories that do not apply in a given repo are simply
  empty.

## Non-goals

- Automatically applying or rewriting skills (task-observer's "log, don't act"
  default is preserved).
- Generating a handoff document (that remains `/handoff`).
- Any destructive git operation, force-push, or signing/verification bypass.
- Cleaning content outside the current repo's tree.

## Form factor

Two global command files in `~/.claude/commands/` (symlinked from
`~/dev/.claude/.claude/commands/`):

- `close.md` defines the full wind-down procedure.
- `close-clean.md` instructs Claude to run the complete `/close` procedure (by
  reference to `close.md`), then perform Tier A + Tier B cleanup, with the
  cleanup spec inline.

The wind-down procedure lives in one place (`close.md`); the cleanup procedure
lives only in `close-clean.md`. There is no substantive duplication.

## `/close` behavior

Three steps, in order. Each is read-mostly before any mutating action; the only
step that can mutate or delete is placed last.

### Step 1 - State snapshot (read-only)

Run and present a compact summary of:

```bash
git branch --show-current
git status --short
git log --oneline -5
git worktree list
```

Also surface any in-progress TodoWrite items from the session. From the current
branch, determine whether this is a **feature branch**, defined as a branch
whose name is not `main` and not `master`. This gates Step 3.

### Step 2 - Task-observer surfacing

Invoke the task-observer Surfacing Protocol described in Context: run the
five-point self-enforcement check, present grouped observations (improvements by
skill, new-skill candidates separately, each tagged open-source/internal), and
ask which to act on. Respect the "log, don't act" default: surface and ask, do
not auto-edit skills.

### Step 3 - Branch decision (conditional)

Only when Step 1 identified a feature branch, invoke
`finishing-a-development-branch` (verify tests, then merge / PR / keep / discard,
then clean up that branch's own worktree). On `main` or `master`, skip this step
and state that it was skipped.

## `/close-clean` behavior

1. Perform the **entire `/close` procedure** (Steps 1 to 3 above, by reference to
   `close.md`).
2. Run cleanup against the **current repo** in two tiers.

### Tier A - auto-safe, removed silently

Regenerable, gitignored artifacts removed without prompting, then reported as a
single after-the-fact summary line:

- `__pycache__/` (recursively)
- `.pytest_cache/`
- `.ruff_cache/`
- `.nox/`
- `.hypothesis/`
- `.coverage`, `coverage.xml`, `coverage-*.xml`

### Tier B - preview then single confirm

Build one grouped preview with per-category counts and sizes, then ask once:
**proceed all / pick categories / cancel**. Nothing in Tier B is deleted before
that confirm.

- **Stale temp files**: files matching `tmp_cleanup/.tmp-*` and root-level
  `.tmp-*` with an mtime older than **14 days**. The single most-recent handoff
  document (most recent `.tmp-handoff-*`) is always preserved regardless of age.
- **Finished worktrees**: from `git worktree list`, a worktree qualifies only
  when **all** of these hold:
  - its branch is merged into `main`, **or** its branch no longer exists;
  - its working tree has no uncommitted changes;
  - it has no commits absent from `main` (no unmerged work).
  A detached-HEAD worktree qualifies only if its HEAD is an ancestor of `main`.
  Any worktree with unique commits or a dirty tree is listed under "needs
  review, not removed" and is never auto-deleted. Removal uses
  `git worktree remove` (plain, no `--force`).
- **Stale skill workspaces**: gitignored directories matching `*-workspace/` and
  `*-workspace-r2/` (and similar `*-workspace*` benchmark remnants) located under
  any `skills/` directory in the repo. Empty in repos that have none.

## Hard safety invariants (both commands)

1. Never delete, discard, stash-drop, or overwrite uncommitted tracked changes.
2. Never remove a worktree with a dirty tree or unmerged commits; never use
   `git worktree remove --force`.
3. Never run `git` with `--no-verify`, `--no-gpg-sign`, or any force-push /
   `--admin` merge flag (these remain blocked by the existing bash-pre-hook
   guard regardless).
4. Tier B deletes nothing without the explicit single confirm. The cancel option
   leaves the tree untouched.
5. Cleanup operates only within the current repository tree; no global or
   user-config paths are touched.

## Data flow

```text
/close ─┬─ Step 1: read git + todos ─────────────► state summary (stdout)
        ├─ Step 2: task-observer Surfacing ───────► grouped observations + prompt
        └─ Step 3: if feature branch ────────────► finishing-a-development-branch

/close-clean ─┬─ run /close (Steps 1-3) ──────────► (as above)
              ├─ Tier A: rm regenerable artifacts ► one-line summary
              └─ Tier B: build preview ──► confirm ─► remove approved categories
```

## Error handling

- **Not a git repo**: Steps 1 and 3 and the worktree category degrade to "n/a";
  task-observer surfacing and the file-based cleanup categories still run.
- **Tests fail in Step 3**: `finishing-a-development-branch` already halts before
  merge/PR; `/close` surfaces the failure and does not proceed with integration.
- **No observations logged this session**: Step 2 reports "no observations to
  surface" and continues.
- **A Tier B category is empty**: it is omitted from the preview rather than
  shown as an empty group.
- **User cancels Tier B**: report what would have been removed and exit cleanly;
  the wind-down from `/close` has already completed and is not rolled back.

## Testing / verification

These are prompt-style command files, not code, so verification is behavioral:

1. **`/close` on `main`** (current state): Step 3 is skipped with an explicit
   message; Steps 1 and 2 run.
2. **`/close` on a feature branch**: Step 3 invokes
   finishing-a-development-branch.
3. **`/close-clean` dry-state check**: Tier A summary lists only regenerable
   paths; Tier B preview correctly classifies the existing
   `.worktrees/license-gate-improvements` worktree (detached HEAD) as either
   removable or "needs review" per the ancestor-of-`main` test, and lists the
   stale `tmp_cleanup/.tmp-*` files and the `*-workspace*` skill dirs.
4. **Safety check**: with uncommitted tracked changes present (as now), confirm
   neither command stages, discards, or commits them.

## Open defaults (confirmed)

- Stale-temp threshold: **14 days**, most-recent handoff always preserved.
- Feature branch: any branch other than `main` / `master`.
- Finished-worktree criteria: merged-or-gone branch, clean tree, no unmerged
  commits; detached HEAD only if ancestor of `main`.
