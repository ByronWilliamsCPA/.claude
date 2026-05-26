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
| `spike/` | `chore:` | No release | Exploratory/throwaway; reduced gate set (see below) |

#### Manifest changes

Changes to `docs/standards-manifest.yaml` follow a refinement of this table. New
check IDs may be `feat:` or `fix:` depending on whether they close a documented
gap or add new enforcement; `override_eligible` inversions and check-ID removals
are `feat!:`. See `.claude/standards/manifest-changes.md` for the full decision
tree, examples, and PR-splitting guidance.

#### Spike branches

`spike/` branches are for time-boxed exploration. They trade review depth for speed.

**Retained gates**: linting (`/quality`), type checking, secrets detection, pre-commit hooks.

**Waived gates**: PR review pipeline (no `/pr-review`, no CodeRabbit, no Copilot), coverage
thresholds, OpenSSF baseline file requirements (LICENSE, SECURITY.md, CONTRIBUTING.md,
CHANGELOG.md), docstring coverage.

**Lifespan**: two weeks maximum. After that, either graduate to a `feat/` branch or delete.
Do not merge spike branches to main; cherry-pick or rewrite the findings into a proper branch.

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
- `GitHub Copilot`: ruleset-required reviewer; fires automatically when
  any PR targeting the default branch opens (the `copilot_code_review`
  rule lives in `<org>-default-branch-baseline` for both orgs).
  Configured via `.github/copilot-instructions.md` to focus on business
  logic, error handling, edge cases, concurrency, and security logic
  flaws that automated linters cannot catch. Leaves advisory comments
  only; not yet a merge blocker (see Phase 3.5 for blocking variant).
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

Use the review tier that matches the audience and risk of the change:

| Scenario | Review command | Time | When |
| --- | --- | --- | --- |
| Solo personal project | `/code-review` | ~5 min | Default for single-contributor repos |
| Production / OSS / client | `/pr-review <url>` | ~15 min | Multi-contributor, external users, or revenue-bearing code |
| Spike branch | None required | 0 min | Exploratory work only; no merge to main |

`/code-review` (5 parallel agents) is sufficient for personal projects. Reserve `/pr-review`
(8 agents + Copilot + SonarQube) for changes with external impact. CodeRabbit fires
automatically on PRs targeting `main`, `master`, or `develop`; its inline comments are
advisory for solo work and do not block merge.

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

## Merge queue and auto-merge

GitHub's merge queue batches compatible PRs so a single CI run validates the
combined HEAD, instead of one run per PR. Without it, N auto-merging Renovate
PRs cascade into N(N+1)/2 CI runs because each merge moves `main` forward and
puts the next PR into BEHIND state.

### When to enable

Enable the merge queue on any repo where these signals appear together:

- `automerge: true` in `renovate.json`, or `RENOVATE_AUTOMERGE=true`
- 5 or more dependency-bump PRs per week
- Required status checks slow enough that serial landing exceeds 30 minutes

The queue is the wrong tool for repos with rare merges, fast checks under
2 minutes, or PRs that frequently conflict on shared files; the speculative
build would just thrash.

### Two prerequisites

1. **Workflows must emit on `merge_group`** (standards-manifest CI-040). The
   queue blocks on required checks; if a required workflow has no `merge_group`
   trigger, the queue waits forever and times out.
2. **Ruleset must declare the queue** (CI-062). Configure on the main branch
   ruleset with `merge_method: SQUASH`, `max_entries_to_build: 5`,
   `min_entries_to_merge: 1`, and `min_entries_to_merge_wait_minutes: 5` so a
   lone PR does not pay the queue's overhead.

### Interaction with auto-merge

Auto-merge and the queue compose. A PR's auto-merge state survives queue
entry; once the speculative build passes, the queue lands the batch using
the auto-merge method. Use `squash` for dependency batches to keep the
default branch history clean.

### References

- GitHub docs:
  <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue>
- Cost incident motivating these checks: ByronWilliamsCPA/.github#154
- Standards: CI-040 (trigger), CI-062 (ruleset)

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
