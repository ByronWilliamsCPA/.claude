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

## Remote Verification

Before pushing to a remote you have not used in this session, verify you are targeting
the correct organization:

    git remote -v

Check that the `origin` URL matches the expected GitHub org and repo before running
`git push`. Wrong-org pushes are difficult to retract once a PR or CI run is triggered.

If the remote URL is wrong:

    git remote set-url origin git@github.com:correct-org/repo-name.git

## Branch Workflow Override

The branch-first rule (never commit directly to `main`) applies in all standard cases.
When a legitimate exception exists (hotfix to an unprotected repo, solo maintenance
commit, CI config tweak), document the override with three elements before proceeding:

1. **Rule overridden**: which rule is being bypassed (e.g., "branch-first commit rule")
2. **Reason**: why the exception applies in this specific context
3. **Compensating control**: what replaces the protection the rule normally provides
   (e.g., "PR is not required; commit is reviewed via pair programming before push")

Record this as a comment in the commit message footer:

    Override: branch-first commit rule
    Reason: hotfix to unprotected solo repo, no CI gating
    Compensating control: manual review of diff before push

## Gate System

Two layers of automated gates enforce quality throughout the workflow:

**Layer 1 — Development gates (fire automatically):**
- `security-guidance` hook: PreToolUse on file edits — blocks writes containing known dangerous code patterns (XSS vectors, unsafe shell invocations, dangerous deserialization, GitHub Actions injection, etc.). Warning shows once per file per session.
- `py310-compat-check` hook: PostToolUse on file edits — catches Python 3.10 incompatibilities immediately after each write.
- `hookify` hooks: fire on every tool use — enforces any project-level rules defined in `.claude/hookify.*.local.md` files.

**Layer 2 — PR gates (automatic and manual, after PR creation):**
- `CodeRabbit`: fires automatically on every PR targeting `main`, `master`, or `develop`.
  Profile: assertive. Provides high-level summary, file-by-file walkthrough, inline
  comments, and suggested labels. Runs ruff, gitleaks, markdownlint, and yamllint as
  inline tools. No action required to trigger it.
- `GitHub Copilot`: request manually from the Reviewers menu on GitHub. Configured via
  `.github/copilot-instructions.md` to focus on business logic, error handling, edge
  cases, concurrency, and security logic flaws that automated linters cannot catch.
  Leaves advisory comments only; does not block merge.
- `/code-review`: runs 5 parallel agents (CLAUDE.md compliance x2, bug scan,
  git-history context, comment compliance), scores each issue 0-100, and posts only
  issues ≥80 confidence as a PR comment. Run manually after PR creation.

Use CodeRabbit for holistic structural review, GitHub Copilot for deep logic review on
complex PRs, and `/code-review` for project-standards enforcement.

**Creating new gates with hookify:**
Use `/hookify <instruction>` to add a rule instantly, or `/hookify` with no args to analyze the current conversation for repeated corrections. Rules live in `.claude/hookify.*.local.md` and take effect on the next tool call — no restart required.

```bash
/hookify Don't delete files without asking me first
/hookify-list          # view all active rules
/hookify-configure     # enable/disable rules interactively
```

## Security Practices

### GitHub Actions: Pin to Commit SHAs

Never reference GitHub Actions by mutable version tags. Tags can be rewritten by the action
author after the fact, enabling supply chain attacks via tag mutation.

Always pin to the full commit SHA:

    # Bad — tag is mutable, can be rewritten after you reference it
    - uses: actions/checkout@v4

    # Good — SHA is immutable
    - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2

To find the SHA: navigate to the action's releases page on GitHub, click the commit link for
the version you want, and copy the full 40-character SHA. Add the version as a comment so the
pin stays human-readable.

Dependabot keeps SHA pins current when configured in `.github/dependabot.yml` with
`package-ecosystem: github-actions`.

## Git Worktrees

Use the `using-git-worktrees` superpowers skill to set up worktrees safely. It handles directory
selection, git-ignore verification, dependency installation, and baseline test confirmation.

Use the `finishing-a-development-branch` superpowers skill to complete work — it presents merge /
PR / keep / discard options and handles worktree cleanup.

> **Canonical conventional commits reference**: See `.claude/skills/git/context/conventional-commits.md`
>
> **Full branch strategy detail**: See `.claude/skills/git/context/branch-strategy.md`
