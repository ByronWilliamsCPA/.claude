---
schema_type: planning
title: "Session-close commands (/close and /close-clean) Implementation Plan"
status: draft
owner: engineering
purpose: "Implementation plan for two global slash-command files, close.md and close-clean.md, under .claude/commands/. close runs a three-step wind-down (state snapshot, task-observer surfacing, conditional branch finish); close-clean adds a two-tier cleanup (silent regenerable artifacts, then a preview-and-confirm sweep of stale temp files, finished worktrees, and stale skill workspaces). The plan embeds the full verbatim content of both files plus behavioral verification against the current tree."
component: Development-Tools
source: "docs/superpowers/specs/2026-06-04-close-session-commands-design.md"
tags:
  - automation
  - tooling
  - skills
  - safety
  - guardrails
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Superseded code blocks:** This plan is a point-in-time implementation
> record. The command files were hardened after the embedded blocks below were
> written: commit `5c10f6b` fixed default-branch resolution, the skill-workspace
> prune set, the admin-merge guard, and mtime-based handoff selection, and a
> later PR-fix pass added a `git check-ignore` gate to Tier A, the `grep -vxF`
> whole-line exclusion, and a detached-HEAD guard in `close.md`. The shipped
> files in `.claude/commands/close.md` and `.claude/commands/close-clean.md` are
> authoritative. Do NOT regenerate the command files from the Task 1 / Task 2
> embedded blocks or the Task 3 verification snippets below, which preserve the
> original drafts for history.

**Goal:** Add two global slash commands, `/close` (full session wind-down) and `/close-clean` (wind-down plus two-tier cleanup), as natural-language command files under `.claude/commands/`.

**Architecture:** Both are prompt-style markdown files (no frontmatter, no code), matching the house style of `aggregate-observations.md` and `compliance-rollup.md`. `close.md` invokes the `task-observer` and `finishing-a-development-branch` skills in prose and runs read-only git snapshots. `close-clean.md` references `close.md` for the wind-down, then runs Tier A (silent removal of regenerable gitignored artifacts) and Tier B (preview-then-single-confirm removal of stale temp files, finished worktrees, and stale skill workspaces). Verification is behavioral, not unit-test based: the implementer runs each embedded discovery snippet against the current tree to confirm correct classification before relying on it.

**Tech Stack:** Markdown command files; Bash (git, find); the existing `task-observer` and `finishing-a-development-branch` skills.

## Conventions (verified during discovery)

- Command files live in `.claude/commands/` (write target) and are surfaced to the user via the `~/.claude/commands/` symlink. **No YAML frontmatter**; start with `# Title`.
- Structure: `# Title` -> intro paragraph(s) -> `## Steps` with numbered `### N.` substeps -> optional `## Hard rules`.
- Skill invocation is prose: "invoke the `task-observer` skill", not `/task-observer`.
- The `validate-front-matter` pre-commit hook is scoped `files: ^docs/.*\.md$` with `pass_filenames: false`. Staging only `.claude/commands/*.md` does **not** trigger it. `markdownlint` does apply to all `.md`, so all fenced blocks need a language.
- Known blocker for the **plan doc** commit only (Task 5): an unrelated pre-existing untracked file `docs/superpowers/plans/eventual-floating-pancake.md` has no frontmatter and fails the whole-tree front-matter scan. The command-file commit (Task 4) is unaffected. Use `SKIP=validate-front-matter` for the plan-doc commit, consistent with the earlier session decision, and do not modify the pancake file.

## File Structure

- Create: `/home/byron/dev/.claude/.claude/commands/close.md` -- the `/close` wind-down command.
- Create: `/home/byron/dev/.claude/.claude/commands/close-clean.md` -- the `/close-clean` command; references `close.md` for the wind-down, adds the two-tier cleanup.

No existing files are modified.

---

### Task 1: Author `close.md`

**Files:**
- Create: `/home/byron/dev/.claude/.claude/commands/close.md`

- [ ] **Step 1: Write the file with this exact content**

````markdown
# Close Session

Wind down the current session: snapshot state, complete the task-observer
process, and (on a feature branch) decide how to finish the branch. Use this at
the end of a working session before starting a fresh one. For a version that
also cleans up worktrees and stale content, use `/close-clean`.

This command never deletes anything and never integrates work without your
confirmation. The only step that can mutate the repo is the branch decision,
and it runs only on a feature branch and only on your choice.

## Steps

### 1. Snapshot session state (read-only)

Run and present a compact summary:

```bash
git branch --show-current
git status --short
git log --oneline -5
git worktree list
```

Also list any in-progress TodoWrite items from this session. From the current
branch name, decide whether this is a feature branch, defined as any branch
other than `main` or `master`. Report the branch and state whether Step 3 will
run.

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
````

- [ ] **Step 2: Lint the file**

Run: `cd /home/byron/dev/.claude && npx markdownlint-cli --config .markdownlint.json .claude/commands/close.md`
Expected: no output (pass). If it reports MD040 (fenced code language), confirm every ` ``` ` opener inside the file has `bash` or `text`; if it reports line-length, reflow prose to match the repo limit.

- [ ] **Step 3: Verify content against the spec checklist**

Read the file back and confirm: three numbered steps in order (snapshot, task-observer, branch finish); feature-branch defined as not `main`/`master`; Step 2 invokes `task-observer` and preserves "log, don't act"; Step 3 is gated on feature branch and invokes `finishing-a-development-branch`; Hard rules forbid bypass flags. No em-dash characters anywhere.

- [ ] **Step 4: Commit**

```bash
cd /home/byron/dev/.claude
git add .claude/commands/close.md
git commit -S -m "feat(commands): add /close session wind-down command"
```

Expected: commit succeeds and is signed. The `validate-front-matter` hook is skipped automatically (no staged `docs/` file); `markdownlint` and `no-em-dash` run and pass.

---

### Task 2: Author `close-clean.md`

**depends-on: Task1 [completion]** (references `close.md`; needs that file to exist on the branch, but does not transform its content).

**Files:**
- Create: `/home/byron/dev/.claude/.claude/commands/close-clean.md`

- [ ] **Step 1: Write the file with this exact content**

````markdown
# Close and Clean Session

Run the full `/close` wind-down, then clean up regenerable artifacts, finished
worktrees, and stale scratch content in the current repository. Use this when
you also want the working tree tidied at session end.

Cleanup runs in two tiers. Tier A removes always-regenerable gitignored
artifacts silently. Tier B previews everything else and removes nothing without
a single confirmation. Real work is never at risk.

## Steps

### 1. Run the full close wind-down

Perform the entire `/close` procedure first (its definition is in `close.md` in
this directory): snapshot state, complete the task-observer process, and finish
the branch if on a feature branch. Complete all of it before cleaning.

### 2. Tier A: remove regenerable artifacts (silent)

Remove the following gitignored, always-regenerable paths from the current repo
without prompting, then report a one-line summary of what was removed. This
prunes `.git`, `.venv`, `.submodules`, and `.worktrees` so it never descends
into other checkouts or expensive-to-rebuild environments:

```bash
find . \( -path ./.git -o -path ./.venv -o -path ./.submodules -o -path ./.worktrees \) -prune \
  -o -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .nox -o -name .hypothesis \) -print -exec rm -rf {} + 2>/dev/null
rm -f .coverage coverage.xml coverage-*.xml 2>/dev/null
```

`.venv` is intentionally preserved: it is gitignored but costly to rebuild and
is not session cruft.

### 3. Tier B: build the preview (delete nothing yet)

Build a single grouped preview with per-category counts and sizes, then ask
once: **proceed all / pick categories / cancel.** Remove nothing before the
answer. Omit any category that is empty.

**Stale temp files** -- `tmp_cleanup/.tmp-*` and root-level `.tmp-*` with an
mtime older than 14 days, always preserving the single most recent handoff doc:

```bash
newest_handoff=$(ls -t .tmp-handoff-* tmp_cleanup/.tmp-handoff-* 2>/dev/null | head -1)
find . tmp_cleanup -maxdepth 1 -name '.tmp-*' -type f -mtime +14 2>/dev/null \
  | grep -vF "${newest_handoff:-/no/such/path}"
```

**Finished worktrees** -- from `git worktree list`, a worktree qualifies for
removal only when its tree is clean AND (its branch is fully merged into `main`,
OR its branch is gone, OR, for a detached HEAD, its HEAD is an ancestor of
`main`). List any worktree with a dirty tree or commits absent from `main` under
"needs review, not removed". Check each candidate worktree at path `$WT` with
branch `$BR` (or detached commit `$SHA`):

```bash
git -C "$WT" status --porcelain                          # must be empty: clean tree
git branch --merged main --format='%(refname:short)' | grep -qx "$BR"  # branch merged
git merge-base --is-ancestor "$SHA" main                 # detached HEAD: ancestor of main
```

**Stale skill workspaces** -- gitignored benchmark remnants under any `skills/`
directory:

```bash
find . -path ./.git -prune -o -type d \( -name '*-workspace' -o -name '*-workspace-r2' \) -path '*/skills/*' -print
```

### 4. Remove confirmed Tier B items and report

After the single confirmation, remove only the approved categories:

- Temp files and skill workspaces: `rm -rf` the listed paths.
- Worktrees: `git worktree remove "$WT"` for each approved worktree (plain, never
  `--force`).

Print a final summary: artifacts cleaned (Tier A), temp files removed,
worktrees removed, worktrees skipped for review, skill workspaces removed.

## Hard rules

- Tier B deletes nothing without the explicit confirmation; cancel leaves the
  tree untouched.
- Never remove a worktree with a dirty tree or unmerged commits; never use
  `git worktree remove --force`.
- Never delete or discard uncommitted tracked changes; Tier A targets only
  gitignored regenerable paths.
- Operate only within the current repository tree; never touch global or
  user-config paths.
- Never run `git` with `--no-verify`, `--no-gpg-sign`, or `--force`.
````

- [ ] **Step 2: Lint the file**

Run: `cd /home/byron/dev/.claude && npx markdownlint-cli --config .markdownlint.json .claude/commands/close-clean.md`
Expected: no output (pass). Every fenced block uses `bash`; fix MD040 or line-length as in Task 1.

- [ ] **Step 3: Verify content against the spec checklist**

Read the file back and confirm: Step 1 references `close.md` and runs the full wind-down first; Tier A prunes `.git`/`.venv`/`.submodules`/`.worktrees` and preserves `.venv`; Tier B is preview-then-single-confirm with the three categories (stale temp >14 days preserving newest handoff, finished worktrees with the clean+merged/ancestor criteria, stale skill workspaces); worktree removal is plain (no `--force`); Hard rules present. No em-dash characters anywhere.

- [ ] **Step 4: Commit**

```bash
cd /home/byron/dev/.claude
git add .claude/commands/close-clean.md
git commit -S -m "feat(commands): add /close-clean wind-down plus cleanup command"
```

Expected: signed commit; `validate-front-matter` skipped (no staged `docs/` file); `markdownlint`/`no-em-dash` pass.

---

### Task 3: Behavioral verification against the current tree

**depends-on: Task2 [completion]** (verifies the discovery snippets the two files rely on; no artifact transform).

This task does not modify the commands. It runs each embedded discovery snippet against the live repo to confirm it classifies the current tree correctly before anyone trusts the commands.

- [ ] **Step 1: Confirm the feature-branch gate logic**

Run:

```bash
cd /home/byron/dev/.claude
b=$(git branch --show-current); echo "branch=$b"; \
  case "$b" in main|master) echo "Step 3 SKIPPED (default branch)";; *) echo "Step 3 RUNS (feature branch)";; esac
```

Expected (current state): `branch=main` and `Step 3 SKIPPED (default branch)`. This proves `/close` is a safe no-op for the branch step on `main`.

- [ ] **Step 2: Confirm Tier A targets only regenerable paths (dry list, no deletion)**

Run the Tier A `find` with `-print` only (no `-exec rm`):

```bash
cd /home/byron/dev/.claude
find . \( -path ./.git -o -path ./.venv -o -path ./.submodules -o -path ./.worktrees \) -prune \
  -o -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .nox -o -name .hypothesis \) -print 2>/dev/null | head -20
```

Expected: only cache/build directories are listed; no `.venv`, no paths under `.submodules/` or `.worktrees/`, no source directories. If anything outside the cache set appears, stop and fix the prune list before trusting Tier A.

- [ ] **Step 3: Confirm the stale-temp candidate list preserves the newest handoff**

```bash
cd /home/byron/dev/.claude
newest_handoff=$(ls -t .tmp-handoff-* tmp_cleanup/.tmp-handoff-* 2>/dev/null | head -1); echo "preserving: $newest_handoff"
find . tmp_cleanup -maxdepth 1 -name '.tmp-*' -type f -mtime +14 2>/dev/null | grep -vF "${newest_handoff:-/no/such/path}"
```

Expected: the printed `preserving:` path does NOT appear in the candidate list below it; the listed candidates are all `.tmp-*` files older than 14 days (the April/May `.tmp-*` scratch files in `tmp_cleanup/`).

- [ ] **Step 4: Confirm the finished-worktree classification on the real worktree**

The repo currently has `.worktrees/license-gate-improvements` in detached HEAD. Classify it:

```bash
cd /home/byron/dev/.claude
WT=.worktrees/license-gate-improvements
echo "dirty:"; git -C "$WT" status --porcelain | head
SHA=$(git -C "$WT" rev-parse HEAD); echo "head=$SHA"
git merge-base --is-ancestor "$SHA" main && echo "ANCESTOR OF MAIN -> removable (if clean)" || echo "HAS UNIQUE COMMITS -> needs review, NOT removed"
```

Expected: a definitive classification. If `git -C "$WT" status --porcelain` is non-empty (dirty) OR the HEAD is not an ancestor of `main`, the worktree must land in "needs review, not removed". Record which bucket it falls in; this is the exact decision `/close-clean` Tier B must reproduce.

- [ ] **Step 5: Confirm the stale-skill-workspace list**

```bash
cd /home/byron/dev/.claude
find . -path ./.git -prune -o -type d \( -name '*-workspace' -o -name '*-workspace-r2' \) -path '*/skills/*' -print
```

Expected: lists the known gitignored remnants (`.claude/skills/test-coverage-workspace`, `.claude/skills/testing-workspace-r2`, `.claude/skills/writing-workspace`) and nothing tracked.

- [ ] **Step 6: Record results**

No commit (read-only task). Note in the execution log which worktree bucket Step 4 produced and confirm Steps 2, 3, 5 listed only intended targets. If any snippet over-matched, fix the corresponding command file (Task 1 or 2) and re-commit before proceeding.

---

### Task 4: Manual smoke test of `/close` on `main`

**depends-on: Task1 [completion]**

- [ ] **Step 1: Invoke the command**

In a Claude Code session at `/home/byron/dev/.claude` (currently on `main`), run `/close`.

Expected behavior: Step 1 prints the state snapshot; Step 2 invokes task-observer surfacing (or reports no observations); Step 3 reports it is skipped because the branch is `main`. No files are modified, nothing is deleted, no branch decision is prompted.

- [ ] **Step 2: Record the outcome**

Confirm the three steps ran in order and Step 3 was correctly skipped. If Step 3 prompted a branch decision on `main`, the branch gate in `close.md` is wrong; fix Task 1 Step 1 and re-commit.

---

### Task 5: Commit the plan document

**depends-on: Task3 [completion]** (plan is final once verification confirms the snippets).

- [ ] **Step 1: Validate the plan's own frontmatter in isolation**

Run: `cd /home/byron/dev/.claude && pre-commit run validate-front-matter --files docs/superpowers/plans/2026-06-04-close-session-commands.md 2>&1 | grep "close-session-commands"`
Expected: `...2026-06-04-close-session-commands.md: OK`. (The hook also scans the whole tree and will report the unrelated `eventual-floating-pancake.md: ISSUES`; that is the pre-existing blocker, not this file.)

- [ ] **Step 2: Commit with the front-matter hook skipped for the unrelated blocker**

```bash
cd /home/byron/dev/.claude
git add docs/superpowers/plans/2026-06-04-close-session-commands.md
SKIP=validate-front-matter git commit -S -m "docs(plans): implementation plan for /close and /close-clean"
```

Expected: signed commit. `SKIP` skips only the front-matter hook (not `--no-verify`); every other hook runs. This file passed the hook in isolation in Step 1, so nothing in it is masked; the skip only avoids the pre-existing untracked `eventual-floating-pancake.md` failure. Do not modify the pancake file.

---

## Self-Review

**Spec coverage:** `/close` three-step wind-down (Task 1) -> spec "`/close` behavior"; task-observer surfacing with "log, don't act" (Task 1 Step 2) -> spec Step 2; conditional branch finish (Task 1 Step 3) -> spec Step 3; Tier A silent (Task 2 Step 2) -> spec "Tier A"; Tier B preview+confirm with three categories (Task 2 Step 3) -> spec "Tier B"; hard safety invariants (both files' Hard rules) -> spec "Hard safety invariants"; generic-across-repos (find-based discovery, empty categories omitted) -> spec Goals. Worktree-complementarity (Step 3 finishes current branch's worktree; Tier B sweeps others) is preserved per the approved spec. All spec sections map to a task.

**Placeholder scan:** No TBD/TODO/"handle appropriately". Both command files were given in full as original drafts; all bash is concrete; expected outputs are stated. The shipped files were subsequently hardened (see the "Superseded code blocks" note at the top); the embedded blocks here are the pre-hardening drafts.

**Type/name consistency:** File names `close.md` / `close-clean.md` and the `$WT`/`$BR`/`$SHA` shell variables are used consistently across Tasks 2 and 3. The Tier A prune set was identical in Task 2 Step 2 and Task 3 Step 2 at authoring time; the shipped Tier A later gained a `git check-ignore` gate (see the supersession note), so the shipped file, not these drafts, is authoritative.

**Shell command environment:** All commands prefix `cd /home/byron/dev/.claude`; no script imports its own package, so no `PYTHONPATH` is needed. `git -C "$WT"` is used for worktree-scoped checks rather than relying on cwd.

**markdownlint:** Every fenced block in both authored files declares `bash` (or `text`); the authoring steps include an explicit markdownlint run so MD040 cannot slip through.

**Commit-trigger correctness:** Verified that staging only `.claude/commands/*.md` does not match the hook's `^docs/.*\.md$` filter, so Tasks 4-command commits need no SKIP; only the plan-doc commit (Task 5) does.
