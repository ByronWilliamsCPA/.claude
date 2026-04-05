# Git Workflow Rules

Always run pre-commit hooks (`pre-commit run --all-files`) before committing.
Expect ruff-format, mypy, and lint checks to catch issues — fix proactively.

## Branch Strategy (MANDATORY)

Never commit directly to `main`, `master`, or `develop`. Always create a feature branch first.

```bash
git checkout main && git pull origin main
git checkout -b {type}/{descriptive-slug}
```

### Branch Type Mapping (Semantic Release)

| Branch Prefix | Commit Type | Version Impact | Use Case |
|---------------|-------------|----------------|----------|
| `feat/` | `feat:` | Minor (0.X.0) | New features |
| `fix/` | `fix:` | Patch (0.0.X) | Bug fixes |
| `docs/` | `docs:` | No release | Documentation |
| `refactor/` | `refactor:` | No release | Code restructuring |
| `perf/` | `perf:` | Patch (0.0.X) | Performance |
| `test/` | `test:` | No release | Tests |
| `chore/` | `chore:` | No release | Maintenance |
| `hotfix/` | `fix:` | Patch (0.0.X) | Critical fixes |

### Branch Naming Convention

Format: `{type}/{descriptive-slug}`

- Lowercase only: `feat/user-auth` not `feat/User-Auth`
- Hyphens: `feat/add-login-page` not `feat/add_login_page`
- Descriptive but concise: `feat/oauth-google` not `feat/add-oauth-integration-with-google-identity-provider`

### When to Create Branches (MANDATORY)

Always branch before:
1. Starting ANY implementation task
2. Each feature/fix TODO item with code changes
3. Multiple independent features (separate branches)
4. User explicitly requests a feature/fix
5. PR review reveals issues

### Automatic Branch Validation

```bash
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" || "$CURRENT_BRANCH" == "develop" ]]; then
    echo "ERROR: Cannot work directly on $CURRENT_BRANCH. Create a feature branch first."
    exit 1
fi
```

## Git Worktree Workflow

Use worktrees for parallel branch isolation (not a replacement for `tmp_cleanup/`).

```bash
# Create worktree for new feature
git worktree add ../{project}-worktrees/feature-name -b feature/feature-name
cd ../{project}-worktrees/feature-name && uv sync --all-extras

# Create worktree for PR review
git worktree add ../{project}-worktrees/pr-42 origin/feature/pr-branch

# List and cleanup
git worktree list
git worktree remove ../{project}-worktrees/feature-name
git worktree prune
```

Key points: worktrees share git history but NOT virtualenvs — run `uv sync` in each.
Use sibling directory: `../{project}-worktrees/`. Cleanup promptly after merging.

### When to Use Worktrees vs Simple Branches

| Scenario | Use Worktree |
|----------|--------------|
| Long-running feature (>1 session) | Yes |
| Parallel agent work | Yes |
| PR review while working | Yes |
| Hotfix during feature work | Yes |
| Experimentation/spike | Yes |
| Simple single task | No (branch is sufficient) |

## Project Plan Branch Strategy

**Single feature**: One branch `feat/implement-{name}`, multiple conventional commits, one PR.

**Multi-feature**: Independent `feat/feature-a`, `feat/feature-b` branches, or worktrees for parallelism.

**Phased**: One branch per phase `feat/phase-1-{description}`, commit each step, one PR per phase.

## Supervisor Branch Workflow

When starting a development task:
1. `git branch --show-current && git status`
2. If on main/develop: `git checkout -b {type}/{descriptive-slug}`
3. Add branch name to TodoWrite list
4. Commit frequently with conventional commit messages matching branch type
5. Never merge directly — always use PR workflow
