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
into other checkouts or expensive-to-rebuild environments. Every candidate is
gated through `git check-ignore` so only paths Git actually ignores are deleted:
a tracked file that happens to match a cache name (a committed `coverage.xml`, a
checked-in `.nox/`) is never removed. Stderr is not suppressed on the deletion,
so any failure (permission denied, read-only mount) surfaces in the summary
rather than being silently swallowed:

```bash
find . \( -path ./.git -o -path ./.venv -o -path ./.submodules -o -path ./.worktrees \) -prune \
  -o -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .nox -o -name .hypothesis \) -print0 2>/dev/null \
  | git check-ignore -z --stdin | xargs -0 -r rm -rf
for f in .coverage coverage.xml coverage-*.xml; do
  [ -e "$f" ] && git check-ignore -q "$f" && rm -f "$f"
done
```

`.venv` is intentionally preserved: it is gitignored but costly to rebuild and
is not session cruft.

### 3. Tier B: build the preview (delete nothing yet)

Build a single grouped preview with per-category counts and sizes, then ask
once: **proceed all / pick categories / cancel.** Remove nothing before the
answer. Omit any category that is empty. If all three categories are empty,
skip the confirmation and report `0 items to clean`.

**Stale temp files:** `tmp_cleanup/.tmp-*` and root-level `.tmp-*` with an mtime
older than 14 days, always preserving the single most recent handoff doc. Both
sides use `find` so the paths share the same `./` prefix and the newest handoff
is reliably excluded:

```bash
newest_handoff=$(find . tmp_cleanup -maxdepth 1 -name '.tmp-handoff-*' -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
find . tmp_cleanup -maxdepth 1 -name '.tmp-*' -type f -mtime +14 2>/dev/null \
  | grep -vxF "${newest_handoff:-/no/such/path}"
```

**Finished worktrees:** from `git worktree list`, a worktree qualifies for
removal only when its tree is clean AND (its branch is fully merged into the
default branch, OR its branch is gone, OR, for a detached HEAD, its HEAD is an
ancestor of the default branch). List any worktree with a dirty tree or commits
absent from the default branch under "needs review, not removed". First resolve
the default branch, then check each candidate worktree at path `$WT` with branch
`$BR` (or detached commit `$SHA`). `$WT`, `$BR`, and `$SHA` are filled per
worktree from the parsed `git worktree list` output, not predefined shell
variables:

```bash
DEFAULT=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
DEFAULT=${DEFAULT:-$(git show-ref --verify --quiet refs/heads/main && echo main || echo master)}
git -C "$WT" status --porcelain                                  # must be empty: clean tree
git branch --merged "$DEFAULT" --format='%(refname:short)' | grep -qx "$BR"  # branch merged
git merge-base --is-ancestor "$SHA" "$DEFAULT"                   # detached HEAD: ancestor of default
```

**Stale skill workspaces:** gitignored benchmark remnants under any `skills/`
directory:

```bash
find . \( -path ./.git -o -path ./.venv -o -path ./.submodules -o -path ./.worktrees \) -prune \
  -o -type d \( -name '*-workspace' -o -name '*-workspace-r2' \) -path '*/skills/*' -print
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
- Never run `git` with `--no-verify`, `--no-gpg-sign`, `--force`, or
  `gh pr merge --admin`.
