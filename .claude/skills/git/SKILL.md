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

```
{type}/{descriptive-slug}
```

Examples: `feat/user-authentication`, `fix/null-pointer-api`, `docs/installation-guide`
