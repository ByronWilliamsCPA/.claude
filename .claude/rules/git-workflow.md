# Git Workflow Rules

Always run pre-commit hooks (`pre-commit run --all-files`) before committing.
Expect ruff-format, basedpyright, and lint checks to catch issues — fix proactively.

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

> **Breaking changes**: Append `!` after the type for any breaking change (`feat!:`, `fix!:`,
> `refactor!:`). This triggers a Major version bump regardless of branch prefix. Document breaking
> changes in the commit footer with `BREAKING CHANGE: <description>`.

### Branch Naming Convention

Format: `{type}/{descriptive-slug}`

- Lowercase only: `feat/user-auth` not `feat/User-Auth`
- Hyphens: `feat/add-login-page` not `feat/add_login_page`
- Descriptive but concise: `feat/oauth-google` not `feat/add-oauth-integration-with-google-identity-provider`

## Gate System

Two layers of automated gates enforce quality throughout the workflow:

**Layer 1 — Development gates (fire automatically):**
- `security-guidance` hook: PreToolUse on file edits — blocks writes containing known dangerous code patterns (XSS vectors, unsafe shell invocations, dangerous deserialization, GitHub Actions injection, etc.). Warning shows once per file per session.
- `py310-compat-check` hook: PostToolUse on file edits — catches Python 3.10 incompatibilities immediately after each write.
- `hookify` hooks: fire on every tool use — enforces any project-level rules defined in `.claude/hookify.*.local.md` files.

**Layer 2 — PR gates (run manually after PR creation):**
- `/code-review`: runs 5 parallel agents (CLAUDE.md compliance x2, bug scan, git-history context, comment compliance), scores each issue 0-100, and posts only issues ≥80 confidence as a PR comment.

**Creating new gates with hookify:**
Use `/hookify <instruction>` to add a rule instantly, or `/hookify` with no args to analyze the current conversation for repeated corrections. Rules live in `.claude/hookify.*.local.md` and take effect on the next tool call — no restart required.

```bash
/hookify Don't delete files without asking me first
/hookify-list          # view all active rules
/hookify-configure     # enable/disable rules interactively
```

## Git Worktrees

Use the `using-git-worktrees` superpowers skill to set up worktrees safely. It handles directory
selection, git-ignore verification, dependency installation, and baseline test confirmation.

Use the `finishing-a-development-branch` superpowers skill to complete work — it presents merge /
PR / keep / discard options and handles worktree cleanup.

> **Canonical conventional commits reference**: See `.claude/skills/git/context/conventional-commits.md`
>
> **Full branch strategy detail**: See `.claude/skills/git/context/branch-strategy.md`
