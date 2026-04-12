# PR Fix Workflow

Gathers all open issues on a PR from every source and resolves them.
Can run standalone (`/pr-fix <URL>`) or as a follow-up from `pr-review.md` Step 10.

## Input

**Standalone mode**: `$ARGUMENTS` contains the GitHub PR URL.
If empty, detect from the current branch via GitHub MCP `pull_request_read`
method `get`, or `gh pr view --json url`.

**From pr-review**: `FINDINGS`, `SONAR_FINDINGS`, `OWNER`, `REPO`,
`PR_NUMBER`, and `HEAD_BRANCH` are already in context from the review.

---

## Step 0 -- Parse URL and fetch metadata

Extract owner, repo, and PR number from the URL:

```bash
PR_URL="$ARGUMENTS"
OWNER=$(echo "$PR_URL" | sed 's|https://github.com/||' | cut -d'/' -f1)
REPO=$(echo "$PR_URL" | sed 's|https://github.com/||' | cut -d'/' -f2)
PR_NUMBER=$(echo "$PR_URL" | grep -oE '[0-9]+$')
```

If values came from the calling pr-review workflow, skip parsing.

Fetch PR metadata via GitHub MCP `pull_request_read` method `get`:

```
owner: OWNER, repo: REPO, pullNumber: PR_NUMBER
```

Store `HEAD_BRANCH`, `BASE_BRANCH`, `PR_TITLE`, `PR_BODY`.

Abort if: PR is closed, or metadata fetch fails.

---

## Step 1 -- Gather all issues (run sources in parallel)

Each source is independent. Launch them simultaneously.

### 1a. CI check failures

Use GitHub MCP `pull_request_read` method `get_check_runs`.

For each check with `conclusion` not `success` and not `neutral`:
- Record: check name, conclusion, run URL
- Fetch failed job logs: `gh run view {RUN_ID} --repo {OWNER}/{REPO} --log-failed`
  (truncate to last 100 lines per job)
- Classify by check name pattern:

| Pattern in check name | Type | Fix approach |
|---|---|---|
| Test, pytest | Test failure | Read output, fix test or impl |
| ruff, lint, Quality | Lint | `ruff check --fix`; manual for unfixable |
| format | Format | `ruff format` |
| basedpyright, type | Type-check | Fix annotations |
| Bandit, Security, security-analysis | Security | Fix flagged patterns |
| Dead Code, vulture | Dead code | Remove (confidence >= 90%) |
| Changelog | Changelog | Add entry from PR title |
| Link, lychee | Links | Fix broken doc links |
| REUSE, License | License | Add/fix headers |
| Compatibility | Py version | Fix 3.10+ incompatibilities |
| SBOM | SBOM | Fix dependency declarations |
| SonarCloud | Quality gate | Defer to Step 1c |
| GitGuardian | Secrets | Alert user only, never auto-fix |
| Docs, Build & Deploy | Doc build | Fix markdown/config |
| Core Validation, PR Validation | PR rules | Fix commits, description, etc. |

### 1b. Review comments

Use GitHub MCP `pull_request_read` with these methods (page with `perPage: 100`):
- `get_review_comments` -- inline review threads
- `get_reviews` -- top-level review verdicts
- `get_comments` -- conversation-level comments

For each item, record: author, body, file path, line, is_resolved,
is_outdated, thread/comment ID.

**Classify by author:**
- `copilot-pull-request-reviewer` --> Copilot
- `coderabbitai` or CodeRabbit markers --> CodeRabbit
- Contains `Generated with [Claude Code]` --> pr-review bot
- All others --> Human

**Filter out (non-actionable):**
- Resolved threads (`is_resolved: true`)
- Bot summary comments without inline suggestions (CodeRabbit walkthrough, etc.)
- Pure praise or acknowledgment

**Keep (actionable):**
- Unresolved threads with change requests
- Copilot suggestions (code blocks with `suggestion` markers)
- CodeRabbit inline suggestions
- Human change requests
- Bug reports, mismatch callouts, missing item flags

### 1c. SonarQube findings

Same detection as pr-review Step 4:

1. Detect org from `.sonarlint/connectedMode.json` `sonarCloudOrganization`
   or `sonar-project.properties` `sonar.organization`
2. Route: `byronwilliamscpa` --> `mcp__sonarqube__`,
   `williaby` --> `mcp__sonarqube-williaby__`
3. Resolve project key from config files or `search_my_sonarqube_projects`
4. Fetch: `search_sonar_issues_in_projects(projects: [KEY], pullRequest: PR_NUMBER)`
5. Fall back to branch issues if PR not analyzed

If `SONAR_FINDINGS` already in context from pr-review, skip this step.

For each finding, record: file, line, rule key, message, severity.
Call `show_rule` for any unfamiliar key to get remediation guidance.

### 1d. Codecov / coverage status

1. Check repo root for `codecov.yml` or `.codecov.yml`
2. Check CI check runs for "codecov" in the name
3. If present and failing: note coverage delta and affected files
4. If not configured: record "not configured", skip

### 1e. pr-review agent findings

If `FINDINGS` from the calling pr-review workflow exists in context,
incorporate directly (already scored and tiered).
If standalone invocation, this source is empty.

---

## Step 2 -- Classify and present

Build the unified issue list. Present:

```
PR Fix: {OWNER}/{REPO}#{PR_NUMBER}
Branch: {HEAD_BRANCH}

Issues found:

  CI Failures:        {N} ({list of failing check names})
  Review Comments:    {N} unresolved ({N_copilot} Copilot, {N_coderabbit} CodeRabbit, {N_human} human)
  SonarQube:          {N} findings
  Coverage:           {status or "not configured"}
  Agent Findings:     {N} from pr-review (if available)

Fixability:
  Auto-fixable:       {N}
  Needs judgment:     {N} (will be skipped, listed at end)

Proceed? (yes / review details / cancel)
```

If the user asks to review details, expand each category.
Wait for confirmation before proceeding.

## Step 3 -- Set up worktree

Create an isolated worktree on the PR branch:

```bash
git fetch origin {HEAD_BRANCH}
git worktree add .worktrees/fix-pr{PR_NUMBER} {HEAD_BRANCH}
```

Record `WORKTREE_PATH=.worktrees/fix-pr{PR_NUMBER}`.

All file edits happen inside `WORKTREE_PATH`. Never touch the main working tree.

**Error handling:**
- If `.worktrees/fix-pr{PR_NUMBER}` exists: `git worktree remove --force` first
- If branch not found: ensure `git fetch origin` ran

---

## Step 4 -- Execute fixes in priority order

Work through issues in this order. CI failures first because they block merge
and may cause cascading issues.

### Priority 1: CI failures

For each failing check, apply the fix strategy from the Step 1a table.
After each category, verify locally before moving on:

- Lint fixes: `cd {WORKTREE_PATH} && uv run ruff check .`
- Format fixes: `cd {WORKTREE_PATH} && uv run ruff format --check .`
- Test fixes: `cd {WORKTREE_PATH} && uv run pytest -x`
- Type fixes: `cd {WORKTREE_PATH} && uv run basedpyright src/`

**Changelog enforcement:** Generate entry from PR title, commit messages, and
file changes. Place under `[Unreleased]` in CHANGELOG.md.

**Python version compatibility:** Check for `datetime.UTC` (use
`datetime.timezone.utc`), `tomllib` without fallback, `match/case` syntax,
`ExceptionGroup` without backport. Apply 3.10-compatible equivalent.

### Priority 2: SonarQube findings

Deterministic fixes; no user prompt needed:

| SonarQube pattern | Fix |
|---|---|
| Missing explicit `return` (shelldre:S7682) | Add `return 0` or `return` |
| Redundant exception type (python:S5713) | Remove subclass from tuple |
| Cognitive complexity (python:S3776) | Extract helper functions |
| ReDoS regex (python:S5852) | Replace with substring match or anchored pattern |
| Security hotspot | Apply prescribed remediation; call `show_rule` for guidance |

### Priority 3: Review comments

For each unresolved actionable comment:

1. Read the referenced file in the worktree (20 lines of surrounding context)
2. Apply the requested change
3. Record: thread ID, file, description of fix (for reply in Step 7)
4. Do not fix anything outside the stated finding

**Handling by finding category:**

| Category | Fix approach |
|---|---|
| Shell script error handling (`set -e` before `$?`, wrong exit code) | Fix specific line; match repo hook contract |
| Bare python calls (`python` vs `uv run python`) | Replace; check pyproject.toml/uv.lock first |
| Hard-coded absolute paths (`/home/user/...`) | Replace with `~`, `$HOME`, or relative path |
| Version mismatches (docs vs pyproject.toml) | Read pyproject.toml, update docs to match |
| Broken relative links | Compute correct path from source to target |
| Diagram/config drift (PUML vs actual settings) | Read actual config, update diagram source |
| Markdown table formatting (double `||`, etc.) | Fix table syntax |
| Closure scope capture (implicit outer vars) | Make parameter explicit |
| Assert in production (`assert x is not None`) | Replace with `if x is None: raise RuntimeError(...)` |
| Em-dash violations | Replace with comma, semicolon, colon, or restructured sentence |
| `== None` / `!= None` | Replace with `is None` / `is not None` |
| Bare `except:` | Replace with `except Exception:` |
| Docstring parameter mismatch | Update docstring to match function signature |

**Always skip (mark "requires manual fix"):**

| Finding type | Reason |
|---|---|
| Test coverage gaps | Writing tests requires understanding intent |
| Type design issues | Architectural judgment |
| Complex logic bugs | Algorithm/business logic needs human review |
| Security vulnerabilities | Must not be auto-patched without review |
| Design debates from prior PRs | Unresolved architectural decisions |
| SVG regeneration | Requires plantuml.jar; note source was updated |

### Priority 4: Coverage gaps

If Codecov is failing:
- Identify uncovered new/modified lines from coverage report
- Use test-writer agent pattern to generate minimal tests
- Run tests in worktree to verify

If no Codecov integration, skip.

### Priority 5: Agent findings (from pr-review)

If `FINDINGS` from pr-review are in context, apply fixes using the same
category rules from Priority 3 above. The "requires manual fix" skip list
is the same.

---

## Step 5 -- Verify

Run the ci-fix gate sequence inside the worktree:

```bash
cd {WORKTREE_PATH}
uv run ruff format --check .
uv run ruff check .
pre-commit run --all-files
uv run pytest          # if tests exist
uv run bandit -r src/ -c pyproject.toml  # if configured
```

If any gate fails: fix the regression and re-run. Up to 3 retry cycles.

If still failing after 3 attempts: report remaining failures and ask the
user whether to commit with known issues or stop.

---

## Step 6 -- Commit and present options

Group fixes into logical commits using conventional commit format.
One concern per commit. Sign each: `git -C {WORKTREE_PATH} commit -S -m "..."`.

| Group | Type | Example message |
|---|---|---|
| CI lint/format fixes | `fix(lint)` | `fix(lint): resolve ruff violations and format issues` |
| Shell script bugs | `fix(hooks)` | `fix(hooks): correct exit codes and stdin reading pattern` |
| SonarQube findings | `fix(quality)` | `fix(quality): add explicit returns, remove redundant exceptions` |
| Review comment fixes | `fix(review)` | `fix(review): address Copilot findings on PR #{N}` |
| Documentation fixes | `docs` | `docs: correct Python version and fix broken links` |
| Test additions | `test` | `test: add coverage for uncovered functions` |
| Config portability | `fix(config)` | `fix(config): replace hard-coded paths with portable alternatives` |
| Em-dash removal | `fix(writing)` | `fix(writing): replace em-dashes per project style rules` |

Present completion options:

```text
Fixes applied. {N_fixed} of {N_total} issues resolved.
{N_skipped} items require manual review.

Skipped (manual review needed):
- {item}: {reason}

Options:
1. Push, reply to review comments, and post PR summary
2. Push only (no PR interaction)
3. Keep worktree for manual review
4. Discard all fixes

Which option?
```

---

## Step 7 -- Execute chosen option

### Option 1 -- Push, reply, and summarize

**Push:**

```bash
git -C {WORKTREE_PATH} push origin {HEAD_BRANCH}
```

**Reply to addressed comments:**

For each review comment that was fixed, post a concise reply (one sentence)
via GitHub MCP `add_reply_to_pull_request_comment` explaining what was done.

Resolve addressed review threads via GitHub MCP `resolve_review_thread`.

**Post summary comment** via GitHub MCP `add_issue_comment`:

```markdown
### PR Fix Summary

Addressed {N} findings:

**CI Fixes**: {bullet list}
**Review Comments**: {bullet list with thread refs}
**SonarQube**: {bullet list}

**Remaining (manual review needed)**:
- {items with reasons}

Pre-commit passing locally. CI re-run triggered by push.
```

**Offer to watch for results:**

```text
Push complete. Watch for CI results and new review comments? (yes/no)
```

If yes: use `subscribe_pr_activity`. When CI results arrive, if any fail,
offer to run another pr-fix pass.

Clean up: `git worktree remove {WORKTREE_PATH}`.

### Option 2 -- Push only

```bash
git -C {WORKTREE_PATH} push origin {HEAD_BRANCH}
git worktree remove {WORKTREE_PATH}
```

### Option 3 -- Keep worktree

Report:

```text
Worktree preserved at {WORKTREE_PATH} on branch {HEAD_BRANCH}.
Push when ready: git -C {WORKTREE_PATH} push origin {HEAD_BRANCH}
```

Do not clean up.

### Option 4 -- Discard

Confirm: ask the user to type "discard". If confirmed:

```bash
git worktree remove --force {WORKTREE_PATH}
```

Do not delete `{HEAD_BRANCH}` itself.

---

## Error Handling

| Situation | Action |
|---|---|
| `gh` / GitHub MCP not authenticated | Stop. Print auth instructions. |
| PR not found or closed | Stop with clear message. |
| Worktree already exists | Remove with `--force` and re-create. |
| Pre-commit fails after 3 attempts | Report failures, ask commit anyway or stop. |
| Finding cannot be auto-fixed | Mark "requires manual fix", skip, continue. |
| Push rejected (protected/diverged) | Report error. Offer Option 3 (keep worktree). |
| SonarQube MCP unreachable | Log "SonarQube: MCP offline", continue without. |
| No Codecov configured | Log "Coverage: not configured", continue. |
| GitGuardian secret detected | Alert user immediately, never auto-fix. |
