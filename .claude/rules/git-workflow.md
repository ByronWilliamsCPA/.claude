# Git Workflow Rules

Always run pre-commit hooks (`pre-commit run --all-files`) before committing.
Expect ruff-format, basedpyright, and lint checks to catch issues; fix proactively.

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

## Force-Push Prohibition

Never run `git push --force` or `git push --force-with-lease` targeting `main`, `master`,
or `develop`. These branches are protected; force-pushing rewrites shared history and
cannot be safely undone once other contributors have pulled.

If a force-push seems necessary (e.g., to remove a secret accidentally committed), stop
and ask the user before proceeding.

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

**Layer 1 - Development gates (fire automatically):**
- `security-guidance` hook: PreToolUse on file edits: blocks writes containing known dangerous code patterns (XSS vectors, unsafe shell invocations, dangerous deserialization, GitHub Actions injection, etc.). Warning shows once per file per session.
- `py310-compat-check` hook: PostToolUse on file edits: catches Python 3.10 incompatibilities immediately after each write.
- `hookify` hooks: fire on every tool use: enforces any project-level rules defined in `.claude/hookify.*.local.md` files.

**Layer 2 - PR gates (automatic and manual, after PR creation):**
- `CodeRabbit`: fires automatically on every PR targeting `main`, `master`, or `develop`.
  Profile: assertive. Provides high-level summary, file-by-file walkthrough, inline
  comments, and suggested labels. Runs ruff, gitleaks, markdownlint, and yamllint as
  inline tools. No action required to trigger it.
- `GitHub Copilot`: triggered automatically by `/pr-review` (see below). Configured via
  `.github/copilot-instructions.md` to focus on business logic, error handling, edge
  cases, concurrency, and security logic flaws that automated linters cannot catch.
  Leaves advisory comments only; does not block merge. If running a review manually
  without `/pr-review`, request from the Reviewers menu on GitHub.
- `/pr-review <url>`: **primary review command.** Accepts a GitHub PR URL and
  orchestrates the full pipeline: triggers Copilot review immediately, fetches
  SonarQube PR-specific findings, runs up to 8 parallel Sonnet agents (CLAUDE.md
  compliance, bug scan, git-history context, prior PR comments, comment accuracy,
  silent failures, test coverage, type design), scores every finding, and outputs a
  tiered report (Critical / Important / Suggested / Informational). Nothing is
  filtered, all findings are categorized and reported. Optionally posts a consolidated
  comment back to the PR.
- `/pr-fix <url>`: **PR remediation command.** Independently gathers all open
  issues on a PR (CI failures, review comments from Copilot/CodeRabbit/humans,
  SonarQube findings, Codecov gaps, and pr-review agent findings), fixes them
  in an isolated worktree, verifies locally, pushes, and replies to addressed
  review comments. Can run standalone or as a follow-up to `/pr-review`.
- `/code-review`: legacy command. Runs 5 parallel agents and posts only issues >=80
  confidence. Use `/pr-review` instead for new reviews; retain `/code-review` for
  quick spot-checks on simple PRs where full pipeline overhead is unnecessary.

Use CodeRabbit for structural review (automatic), `/pr-review` as the primary review
command for all PRs (triggers Copilot + SonarQube + 8 agents in one pass),
`/pr-fix` to resolve all identified issues, and `/code-review` only for lightweight
spot-checks.

**Creating new gates with hookify:**
Use `/hookify <instruction>` to add a rule instantly, or `/hookify` with no args to analyze the current conversation for repeated corrections. Rules live in `.claude/hookify.*.local.md` and take effect on the next tool call; no restart required.

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

    # Bad: tag is mutable, can be rewritten after you reference it
    - uses: actions/checkout@v4

    # Good: SHA is immutable
    - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2

To find the SHA: navigate to the action's releases page on GitHub, click the commit link for
the version you want, and copy the full 40-character SHA. Add the version as a comment so the
pin stays human-readable.

Dependabot keeps SHA pins current when configured in `.github/dependabot.yml` with
`package-ecosystem: github-actions`.

## Git Worktrees

### Location (mandatory)

Always create worktrees inside the project at `.worktrees/<branch-slug>`:

```bash
git worktree add .worktrees/feat-my-feature feat/my-feature
```

Never create worktrees at global or user-config paths such as
`~/.config/superpowers/worktrees/` or any path outside the project root.
When no location is specified and no CLAUDE.md preference exists, default to
`.worktrees/` without prompting.

Rationale: worktrees at global paths are invisible to `git worktree list` from
a fresh clone, break `.gitignore` assumptions, and survive project deletion as
orphaned directories that are difficult to clean up later.

Ensure `.worktrees/` is in `.gitignore` (it is already present in this repo).

### Setup and cleanup

Use the `using-git-worktrees` superpowers skill to set up worktrees safely. It handles directory
selection, git-ignore verification, dependency installation, and baseline test confirmation.

Use the `finishing-a-development-branch` superpowers skill to complete work. It presents merge /
PR / keep / discard options and handles worktree cleanup.

> **Canonical conventional commits reference**: See `.claude/skills/git/context/conventional-commits.md`
>
> **Full branch strategy detail**: See `.claude/skills/git/context/branch-strategy.md`

### PR size calibration

Anthropic internal distribution (Boris Cherny, Mar 25 2026):

| Percentile | Lines changed |
| --- | --- |
| p50 | 118 |
| p90 | 498 |
| p99 | 2,978 |

PRs above 500 lines are in the top 10% of Anthropic's own internal distribution.
Prefer splitting features at a natural seam before crossing the p90 threshold.

Source: <https://x.com/bcherny/status/2038552880018538749>

## Session Forking

Claude Code supports two mechanisms for exploration that should not contaminate
the main session:

### `/branch` (in-session fork)

`/branch` creates a new session branch from the current conversation state. Use
when exploring a speculative approach, testing a hypothesis that may dead-end, or
preserving the current session state before a risky refactor.

The fork starts with the current conversation context and cache warm. If the
exploration fails, discard the fork. If it succeeds, the findings return as a
message in the parent.

### `--fork-session` (CLI flag)

`claude --fork-session <session-id>` creates a detached session from an existing
session ID. Use when parallelising two independent directions from the same starting
point, or running a long background investigation without blocking the parent.

### When to use worktree vs. fork

| Need | Use |
| --- | --- |
| Filesystem isolation (different branch, different files) | `git worktree` |
| Conversation-state preservation (same files, different direction) | `/branch` |
| Full isolation (new files AND new conversation) | worktree + new session |

Source: Boris Cherny, 15 hidden features (Mar 30 2026):
<https://x.com/bcherny/status/2038454336355999749>

## Sources

- Conventional Commits specification: <https://www.conventionalcommits.org/>
- Boris Cherny, PR size/squash (Mar 25 2026): <https://x.com/bcherny/status/2038552880018538749>
- Boris Cherny, session forking/hidden features (Mar 30 2026): <https://x.com/bcherny/status/2038454336355999749>
- Boris Cherny, CLAUDE.md loading semantics: <https://x.com/bcherny/status/2016339448863355206>
- Claude Code git worktrees: <https://code.claude.com/docs/en/worktrees>
