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
