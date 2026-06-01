---
name: git
description: >
  Git workflow management: branch creation/validation, conventional commit message
  preparation, and PR description generation. Auto-activates on: git, branch, commit,
  pull request, PR, merge, rebase, conventional commits, stage and commit, ready to
  commit, commit message, commit this, prepare commit, write commit, prepare PR,
  create PR, draft PR, write PR, ready for PR
---

# Git Workflow Skill

Git workflow management including branch validation, conventional commit preparation,
PR description generation, and repository health checks.

## Routing

| Activation Context | Workflow File |
|--------------------|---------------|
| Commit-related (`commit`, `stage and commit`, `commit message`, etc.) | `workflows/commit.md` |
| PR-related (`prepare PR`, `create PR`, `draft PR`, `pull request`, etc.) | `workflows/pr.md` |
| Branch-related (`branch`, `checkout`, `branch strategy`) | `context/branch-strategy.md` |

## Reference Files

- **`context/conventional-commits.md`**: Full type table with version impact
- **`context/branch-strategy.md`**: Branch naming format, semantic release mapping, validation

## Quick Reference

### Branch Status

```bash
git branch --show-current
git status
```

### Semantic Release Mapping

| Branch Prefix | Commit Type | Version Impact |
|---------------|-------------|----------------|
| `feat/` | `feat:` | Minor (0.X.0) |
| `fix/` | `fix:` | Patch (0.0.X) |
| `docs/` | `docs:` | No release |
| `refactor/` | `refactor:` | No release |
| `perf/` | `perf:` | Patch (0.0.X) |
| `test/` | `test:` | No release |
| `chore/` | `chore:` | No release |
| `hotfix/` | `fix:` | Patch (0.0.X) |

### Branch Format

```text
{type}/{descriptive-slug}
```

Examples: `feat/user-authentication`, `fix/null-pointer-api`, `docs/installation-guide`

## Common Hazards

Real-world failure patterns collected from production sessions.

### Squash-merge branch cleanup (Obs 43/44/118/125)

`git ancestry` tools (`git branch -d`, `git log origin/main..HEAD`, `git cherry`) are unreliable in squash-merge repos because squash creates a new SHA on main. For "is this branch merged?" checks, use PR state plus content diff rather than ancestry:

```bash
# Check PR state
gh pr list --head <branch> --state all

# Authoritative supersession test (three-dot diff)
git diff main...origin/<branch>
```

Three-dot diff `git diff main...origin/<branch>` is the authoritative test for branch supersession. If the diff is empty, the branch content is already on main regardless of ancestry.

### git stash is global, not per-branch (Obs 128)

`git stash` shares a stack across all branches. Popping "the stash" may apply another branch's WIP to your current tree, contaminating it with unrelated changes.

For "is this failure pre-existing?" comparisons, use `git show ref:path | <tool>` or a throwaway worktree instead of stash-and-restore:

```bash
# Safe: read a file at a specific ref without touching working tree
git show origin/main:path/to/file.py | python3 -m pytest --collect-only -q -

# Safe: throwaway worktree for baseline comparison
git worktree add .worktrees/baseline-check origin/main
```

### Shared-clone staging safety (Obs 111)

In a shared (non-worktree) clone with concurrent agent sessions, `git add <file>` stages the entire working-tree file, including another session's uncommitted edits. A commit reporting unexpectedly large changes (e.g., "140 insertions" for a 1-line fix) is the signal.

Always verify staged diff before committing:

```bash
git diff --cached   # review exactly what will be committed
```

Use `.worktrees/<branch-slug>` for isolation whenever concurrent agent sessions are active.

### History purge: GitHub retains unreachable objects (Obs 139)

After `git filter-repo` and force-push, purged commits remain resolvable by SHA via GitHub's API and via `refs/pull/*` until GitHub Support runs GC. Treat exposed data as already compromised; rotate secrets rather than relying on purge.

Also: force-push guards that pattern-match on `git push` adjacency are bypassable by alternate git invocation forms:

```bash
# These bypass naive push-guard pattern matching:
git -C <dir> push --force main
git --git-dir=<path> push --force main
```

### Always diff against fetched remote, not local main (Obs 141)

`git fetch` updates remote-tracking refs but not local branch refs. Local `main` is routinely stale. For branch reviews and comparisons, always run `git fetch` first and diff against `origin/<default>`, not local `main`:

```bash
git fetch origin

# Establish ahead/behind counts early
git rev-list --left-right --count origin/main...HEAD

# Diff against fresh remote state
git diff origin/main...<branch>
```

### secrets.baseline generated_at conflict (Obs 104)

The `generated_at` field in `.secrets.baseline` conflicts whenever two branches both run the detect-secrets hook. The correct resolution is: keep the newer timestamp. No manual inspection of the secrets entries is needed unless the conflict extends beyond that line.

```bash
# Accept the newer timestamp from either side, then stage
git add .secrets.baseline
```
