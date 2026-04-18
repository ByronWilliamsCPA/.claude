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

## Configuration

PAL tool parameters used throughout this workflow. Edit these values to tune
model selection and consensus depth without touching the workflow logic.

```text
PAL_CHAT_MODEL:      google/gemini-2.5-pro-preview
PAL_TIERED_LEVEL:    1
PAL_TIERED_THINKING: auto
```

- `PAL_CHAT_MODEL`: model passed to `mcp__pal__chat` for targeted validations
- `PAL_TIERED_LEVEL`: level (1/2/3) for all `mcp__pal__tiered_consensus` calls;
  level 1 uses 3 free models, level 2 adds paid models (~$0.50), level 3 is
  comprehensive (~$5)
- `PAL_TIERED_THINKING`: thinking depth for tiered_consensus (`auto`, `low`,
  `high`)

---

## Step 0: Parse URL and fetch metadata

Extract owner, repo, and PR number from the URL:

```bash
PR_URL="$ARGUMENTS"
OWNER=$(echo "$PR_URL" | sed 's|https://github.com/||' | cut -d'/' -f1)
REPO=$(echo "$PR_URL" | sed 's|https://github.com/||' | cut -d'/' -f2)
PR_NUMBER=$(echo "$PR_URL" | grep -oE '[0-9]+$')
```

If values came from the calling pr-review workflow, skip parsing.

Fetch PR metadata via GitHub MCP `pull_request_read` method `get`:

```text
owner: OWNER, repo: REPO, pullNumber: PR_NUMBER
```

Store `HEAD_BRANCH`, `BASE_BRANCH`, `PR_TITLE`, `PR_BODY`.

Abort if: PR is closed, or metadata fetch fails.

---

## Step 1: Gather all issues (run sources in parallel)

Each source is independent. Launch them simultaneously.

### 1a. CI check failures

Use GitHub MCP `pull_request_read` method `get_check_runs`.

For each check with `conclusion` not `success` and not `neutral`, do the following:

- Record: check name, conclusion, run URL
- Fetch failed job logs: `gh run view {RUN_ID} --repo {OWNER}/{REPO} --log-failed`
  (truncate to last 100 lines per job)
- Classify by check name pattern:

| Pattern in check name | Type | Fix approach |
| --- | --- | --- |
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

- `get_review_comments`: inline review threads
- `get_reviews`: top-level review verdicts
- `get_comments`: conversation-level comments

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

## Step 2: Classify and present

Build the unified issue list. Present:

```text
PR Fix: {OWNER}/{REPO}#{PR_NUMBER}
Branch: {HEAD_BRANCH}

Issues found:

  CI Failures:        {N} ({list of failing check names})
  Review Comments:    {N} unresolved ({N_copilot} Copilot, {N_coderabbit} CodeRabbit, {N_human} human)
  SonarQube:          {N} findings
  Coverage:           {status or "not configured"}
  Agent Findings:     {N} from pr-review (if available)

Tier coverage (from pr-review findings):
  Critical:           {N} (all addressed)
  Important:          {N} (all addressed)
  Suggested:          {N} (all addressed)
  Informational:      {N} (addressed if single-file, low-risk; otherwise skipped)

Fixability:
  Auto-fixable:       {N}
  Agent-evaluated:    {N} (assigned to specialized agents — not deferred)
  Human-only:         {N} (design debates, security policy decisions — listed at end)

Proceed? (yes / review details / cancel)
```

If the user asks to review details, expand each category.
Wait for confirmation before proceeding.

## Step 3: Set up worktree

Create an isolated worktree on the PR branch:

```bash
git fetch origin {HEAD_BRANCH}
git worktree add .worktrees/fix-pr{PR_NUMBER} {HEAD_BRANCH}
```

Record `WORKTREE_PATH=.worktrees/fix-pr{PR_NUMBER}`.

All file edits happen inside `WORKTREE_PATH`. Never touch the main working tree.

**Error handling:**

- If `.worktrees/fix-pr{PR_NUMBER}` exists: `git worktree remove --force` first
- If branch not found: check that the branch exists on origin with `git fetch origin`

---

## Step 4: Execute fixes in priority order

Work through issues in this order. CI failures first because they block merge
and may cause cascading issues.

### Priority 1: CI failures

For each failing check, apply the fix strategy from the Step 1a table.
After each category, verify locally before moving on:

- Lint fixes: `cd {WORKTREE_PATH} && uv run ruff check .`
- Format fixes: `cd {WORKTREE_PATH} && uv run ruff format --check .`
- Test fixes: `cd {WORKTREE_PATH} && uv run pytest -x`
- Type fixes: `cd {WORKTREE_PATH} && uv run basedpyright src/`

**Changelog enforcement:** Check whether any commit on this branch (since
`git merge-base HEAD origin/{BASE_BRANCH}`) uses type `feat`, `fix`, `perf`, or
includes `!` (breaking change). If yes, generate an entry from the PR title,
commit messages, and changed files, and place it under `[Unreleased]` in
CHANGELOG.md. If no such commits exist, note "CHANGELOG not required: no
feat/fix/perf/breaking changes on this branch" and skip.

**Python version compatibility:** Check for `datetime.UTC` (use
`datetime.timezone.utc`), `tomllib` without fallback, `match/case` syntax,
`ExceptionGroup` without backport. Apply 3.10-compatible equivalent.

### Priority 2: SonarQube findings

**Auto-fix** (no user prompt needed): mechanical, low-risk changes:

| SonarQube pattern | Fix |
| --- | --- |
| Missing explicit `return` (shell:S7682) | Add `return 0` or `return` |
| Redundant exception type (python:S5713) | Remove subclass from tuple |
| Security hotspot | Apply prescribed remediation; call `show_rule` for guidance |
| Single-bracket conditional (shelldre:S7688) | Replace `[ ... ]` with `[[ ... ]]` only if the script shebang is `#!/bin/bash` or `#!/usr/bin/env bash`; skip if `#!/bin/sh` or no shebang |
| Missing default case in `case` (shelldre:S131) | Add `*) ;;` default case to `case` statements |
| Error message to stdout (shelldre:S7677) | Redirect error messages to stderr: `echo "..." >&2` |
| Positional parameter not named (shelldre:S7679) | Assign positional parameters to named local variables at function start |
| Constant boolean expression in test (python:S5914) | Remove the trivially-true assertion or replace with a meaningful assertion for what the test actually verifies; use `assertIsNotNone` only when the test intent is specifically a non-None check |
| Float equality check (python:S1244) | Replace float equality check with `math.isclose()` in production code, or `pytest.approx()` in test code |

**Propose and confirm** (show the proposed change, wait for user approval before
applying): these touch logic, security policy, or refactoring:

For each propose-and-confirm finding, before presenting the proposed fix to
the user, call `mcp__pal__chat` to validate the fix:

```text
mcp__pal__chat(
  model:  PAL_CHAT_MODEL,
  prompt: "A SonarQube finding requires a propose-and-confirm fix before I
           show it to the user. Validate the proposed fix is correct and safe.

           Finding: {rule key}: {message}
           File: {file path}, line {line}
           Current code:
           {10 lines of context around the finding}

           Proposed fix:
           {description of the planned change}

           Questions:
           1. Is the proposed fix semantically correct (does it preserve the
              original behavior for all non-vulnerable inputs)?
           2. Does the fix introduce any new risks (e.g., regression, changed
              semantics, security implications)?
           3. Is there a better fix?

           Reply with: APPROVE, REVISE (with suggested revision), or
           REJECT (with reason). One word verdict on the first line."
)
```

If PAL returns REVISE or REJECT, update the proposed fix before showing it
to the user. Do not block on this call; if the PAL tool is unavailable,
proceed with the original proposed fix and note "PAL validation skipped" in
the presentation.

| SonarQube pattern | Proposed fix |
| --- | --- |
| ReDoS regex (python:S5852) | Show current pattern and proposed replacement; explain why it is vulnerable; apply only after approval |
| Nested `if` in shell (shelldre:S1066) | Show merged condition; note whether `set -e`/`errexit` affects error-handling semantics; apply only after approval |
| Nested `if` in Python (python:S1066) | Show merged condition using `and`; apply only after approval |
| Unused local variable (shelldre:S1481) | Show variable and usage context; confirm intent before removing (may be an intentional placeholder) |
| Repeated string literal (python:S1192) | Show proposed constant name and extraction site; apply only after approval |
| Broad workflow permissions (githubactions:S8234) | Read job steps, derive minimum permission set, show diff; apply only after approval |
| Workflow-level permissions (githubactions:S8233) | Show proposed per-job permissions block; apply only after approval |

### Priority 3: Review comments

For each unresolved actionable comment:

1. Read the referenced file in the worktree (20 lines of surrounding context)
2. Apply the requested change
3. Record: thread ID, file, description of fix (for reply in Step 7)
4. Fix the root cause of the finding, even if it lives in a different function or file
   than where the symptom was reported. Keep the diff as small as the root cause
   requires. Do not refactor unrelated code, rename variables for style, or add
   features not requested. When the root cause fix touches more than 3 files not in
   the original diff, pause and confirm with the user before proceeding.

**Handling by finding category:**

| Category | Fix approach |
| --- | --- |
| Shell script error handling (`set -e` before `$?`, wrong exit code) | Fix specific line; match repo hook contract |
| Bare python calls (`python` vs `uv run python`) | Replace; check pyproject.toml/uv.lock first |
| Hard-coded absolute paths (`/home/user/...`) | Replace with `~`, `$HOME`, or relative path |
| Documentation accuracy (see sub-categories below) | Read the authoritative source, update docs to match |
| Broken relative links | Compute correct path from source to target |
| Diagram/config drift (PUML vs actual settings) | Read actual config, update diagram source |
| Markdown table formatting (extra pipes, missing spaces) | Fix table syntax |
| Closure scope capture (implicit outer vars) | Make parameter explicit |
| Assert in production (`assert x is not None`) | Replace with `if x is None: raise RuntimeError(...)` |
| Em-dash violations | Replace with comma, semicolon, colon, or restructured sentence |
| `== None` / `!= None` | Replace with `is None` / `is not None` |
| Bare `except:` | Replace with `except Exception:` |
| Docstring parameter mismatch | Update docstring to match function signature |
| `jq` invoked without presence guard (with `set -euo pipefail`) | Add `command -v jq >/dev/null 2>&1 \|\| { echo "jq not found" >&2; exit 1; }` before first `jq` call; in Claude Code hooks, omit `>&2` so Claude can surface the error (see hook block message row) |
| Hook block message written to stderr instead of stdout | Change `>&2` redirect to stdout so Claude surfaces the block reason; this applies to hook scripts only, not general shell scripts |
| `grep -nP` used (requires GNU grep / PCRE) | Replace with POSIX-compatible `grep -n` plus equivalent pattern, or note BSD incompatibility inline |
| PowerShell single-quote escaping in bash | Mark "requires manual fix": escaping logic is error-prone to auto-patch |

**Documentation accuracy sub-categories:**

| Sub-category | Fix approach |
| --- | --- |
| Docs reference wrong Python version | Read `requires-python` from `pyproject.toml`, update docs to match |
| Docs describe wrong pre-commit hook exclude list | Read `.pre-commit-config.yaml`, update docs to match actual excludes |
| Spec frontmatter `status` conflicts with body `Status:` blockquote | Frontmatter `status` is schema-validated (`draft \| in-review \| published`); update the body blockquote to be consistent in spirit with the frontmatter value; never change frontmatter to a non-schema value |
| Architecture section asserts a hook is wired in `settings.json` but it is not | Update doc to say "not yet wired" rather than asserting it is wired |
| Design spec missing required metadata blockquote (Date / Status / Scope) | Add the blockquote using the same format as other specs in the same directory |
| Skill SKILL.md intro says "N modes" but body documents N+1 modes | Count the documented modes and update the intro sentence to match |
| Collaboration document (e.g., `COWORK.md`) says filename is "or similar" but README specifies exact filename | Read the README for the canonical filename and update the collaboration document to match |

**Assign to specialized agent (cannot auto-fix):**

For each of the following, launch the named agent to evaluate the finding and
produce a concrete fix recommendation or draft fix. Run agent evaluations in
parallel after all auto-fixes are applied (Step 4 end). Include agent outputs
in the Step 6 commit options and Step 8 PR summary.

| Finding type | Agent to invoke | What to ask it |
| --- | --- | --- |
| Test coverage gaps (from review comments) | `test-writer` | Generate minimal tests covering the flagged uncovered lines |
| Type design issues | `type-design-analyzer` | Evaluate the type and rate encapsulation/invariant expression; propose improvements |
| Cognitive complexity (python:S3776) | `code-reviewer` | Propose the minimal refactor to reduce complexity below the threshold |
| Complex logic bugs | `code-reviewer` | Evaluate the reported bug; propose a safe, targeted fix |
| Security vulnerabilities (non-secret) | `security-auditor` | Assess severity, propose a remediation that does not change calling contracts |
| Path from user-controlled data (pythonsecurity:S2083) | `owasp-web` | Evaluate the injection risk, propose input validation or path sanitization |
| SVG regeneration | `diagram-maintenance-agent` | Regenerate SVG from the updated PlantUML source |
| PlantUML diagram accuracy | `diagram-maintenance-agent` | Cross-reference settings files, update diagram source, regenerate SVG |
| Force-push guard bypass | `security-auditor` | Evaluate the bypass vector, propose a configuration or hook-based guard |

**Always mark human-only (no agent can resolve):**

| Finding type | Reason |
| --- | --- |
| Design debates from prior PRs | Unresolved architectural decisions requiring stakeholder input |
| GitGuardian secret detected | Alert user immediately; never auto-patch or agent-patch |
| Reversing a deliberate product decision | Requires explicit product owner approval |

### Priority 4: Coverage gaps

**Unified test policy:** Tests are generated automatically only when Codecov
is failing and specific uncovered lines can be identified from the coverage
report. Never add tests in response to review comments alone. If a review
comment requests better test coverage but Codecov is not failing, mark the
item "requires manual fix" and include it in the skipped list.

If Codecov is failing:

- Identify uncovered new/modified lines from coverage report
- Use test-writer agent pattern to generate minimal tests that cover only
  those specific lines; do not pad coverage by testing unrelated code
- Run tests in worktree to verify
- Before confirming with the user, validate the generated tests are not
  tautological:

```text
mcp__pal__chat(
  model:  PAL_CHAT_MODEL,
  prompt: "Review these generated tests for tautological failures (tests that
           will pass regardless of whether the code under test is correct).

           Tests to review:
           {generated test code}

           Code under test:
           {relevant function/method being tested}

           For each test, answer:
           1. Would this test catch a wrong return value?
           2. Would this test catch a missing branch?
           3. Does this test assert behavior, or does it just call the function
              and assert it does not throw?

           Flag any test that is tautological. Suggest a minimal fix for each
           flagged test. If all tests are sound, say 'All tests are behaviorally
           meaningful.'"
)
```

  If PAL flags tautological tests, revise them before presenting to the user.
  Note any tests that could not be made non-tautological in the confirmation
  prompt.

- Confirm with the user before committing generated tests

If no Codecov integration, skip entirely.

### Priority 5: Agent findings (from pr-review)

If `FINDINGS` from pr-review are in context, apply fixes using the same
category rules from Priority 3 above. The "requires manual fix" skip list
is the same.

---

## Step 5: Verify

### 5a. Local gate sequence

Before running individual tools, detect the project's CI entry point in this
order and use the first one found:

1. `nox` session: check `noxfile.py` for a `ci` or `lint` session and run
   `cd {WORKTREE_PATH} && nox -s ci` (or the matching session name)
2. `tox`: check `tox.ini` or `pyproject.toml [tool.tox]` and run
   `cd {WORKTREE_PATH} && tox`
3. `make ci`: check `Makefile` for a `ci` target and run
   `cd {WORKTREE_PATH} && make ci`
4. `scripts/ci.sh`: check for the file and run
   `cd {WORKTREE_PATH} && bash scripts/ci.sh`
5. Fallback: run individual tools:

```bash
cd {WORKTREE_PATH}
uv run ruff format --check .
uv run ruff check .
pre-commit run --all-files
uv run pytest          # if tests exist
uv run bandit -r src/ -c pyproject.toml  # if configured
```

If any gate fails: fix the regression and re-run. Up to 3 retry cycles.

If still failing after 3 attempts: check whether the failures existed before
this fix session started (see pre-existing failure policy below). Report
remaining failures and ask the user whether to commit or stop.

**Pre-existing failure policy:**

Before beginning any fixes, record which CI checks were already failing
(from the Step 1a findings). Label these `PREEXISTING`.

After 3 retry cycles, compare remaining local failures against `PREEXISTING`:

- If the remaining failure is in `PREEXISTING`: offer to commit with a
  mandatory PR comment: "Known pre-existing failure: {check name}. Not
  introduced by this fix session. Tracked separately."
- If the remaining failure is NOT in `PREEXISTING` (i.e., it was introduced
  during the fix session): do NOT offer to commit. Stop and require the user
  to decide how to proceed. Committing a regression is not an option.

### 5b. CI dry-run: validate GitHub Actions configs locally

After local gates pass, scan `.github/workflows/*.yml` in the worktree and
run any checks that can be validated locally. This catches the class of CI
failures (wrong file paths, missing extensions, bad action versions) that
only surface after pushing.

**Checks that CAN run locally:**

| CI check | Local validation command |
| --- | --- |
| REUSE compliance | `cd {WORKTREE_PATH} && reuse lint` (if `reuse` installed) |
| pip-audit | `cd {WORKTREE_PATH} && uv run pip-audit` |
| bandit | `cd {WORKTREE_PATH} && uv run bandit -r src/ -c pyproject.toml` |
| FIPS check | Run project's FIPS script if it exists |
| shellcheck | `shellcheck {WORKTREE_PATH}/scripts/*.sh` (if `.sh` files changed) |

**Checks that CANNOT run locally (validate config statically instead):**

| CI check | Static validation |
| --- | --- |
| ClusterFuzzLite | For each fuzz target declared in workflow: verify file exists at the declared path, has the correct extension (`.py` for Python), and compiles with `python3 -m py_compile {target}` |
| Dependency Review | Verify the action version pin resolves (check format: `actions/dependency-review-action@vN`) |
| SARIF upload | If workflow references a SARIF file path, verify the generating step would produce it (check step ordering and output paths) |
| SonarCloud | Verify `sonar-project.properties` has non-placeholder values for `sonar.organization` and `sonar.projectKey` |
| Codecov | If `codecov.yml` exists, verify it parses as valid YAML and references existing flag names |

**Error handling:** If a local validation tool is not installed (e.g., `reuse`),
skip it and note "REUSE: not installed locally, will be validated by CI."
Do not fail the step for missing optional tools.

Report all findings before proceeding to Step 6. If any static validation
fails, fix the issue in the worktree and re-run the affected check.

---

## Step 6: Commit and present options

Group fixes into logical commits using conventional commit format.
One concern per commit. Sign each: `git -C {WORKTREE_PATH} commit -S -m "..."`.

| Group | Type | Example message |
| --- | --- | --- |
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

## Step 7: Rebase check and push

Before pushing in any option, check whether the base branch has diverged:

```bash
git -C {WORKTREE_PATH} fetch origin {BASE_BRANCH}
if ! git -C {WORKTREE_PATH} merge-base --is-ancestor \
    origin/{BASE_BRANCH} HEAD; then
  echo "Base branch has diverged since this branch was created."
fi
```

If diverged, present the user with options:

```text
Base branch ({BASE_BRANCH}) has new commits since this branch diverged.
Pushing without rebasing may cause merge conflicts later.

1. Rebase onto origin/{BASE_BRANCH} before pushing (recommended)
2. Push as-is (merge conflict risk)
3. Keep worktree for manual resolution

Which option?
```

If the user selects rebase: run `git -C {WORKTREE_PATH} rebase origin/{BASE_BRANCH}`.
If conflicts occur, report them and offer Option 3 (keep worktree).
If rebase succeeds, continue with the selected push option below.

---

## Step 8: Execute chosen option

### Option 1: Push, reply, and summarize

**Push:**

```bash
git -C {WORKTREE_PATH} push origin {HEAD_BRANCH}
```

**Reply to all threads:**

For every open finding in the unified issue list, whether fixed, deferred, or declined,
post a reply to its GitHub thread via GitHub MCP `add_pull_request_review_comment`
(or `create_pull_request_review`). Note: exact method name depends on the GitHub MCP
server version; confirm with `gh api` if the MCP call fails.

| Outcome | Reply format |
| --- | --- |
| Fixed | `Fixed in {commit SHA}: {one sentence description of what changed}` |
| Deferred | `Deferred: {reason}. Tracked in {ticket or follow-up issue number}.` |
| Declined | `Declined: {reason}. This is intentional because {explanation}.` |

Never leave a thread without a reply. Reviewers must be able to mark threads resolved
without chasing context.

Mark addressed review threads as resolved via GitHub MCP if the server supports
a resolve method (method name varies by version; check server docs).

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

**Continue to Step 9 (watch-and-refix loop).**

### Option 2: Push only

```bash
git -C {WORKTREE_PATH} push origin {HEAD_BRANCH}
```

**Continue to Step 9 (watch-and-refix loop).**

### Option 3: Keep worktree

Report:

```text
Worktree preserved at {WORKTREE_PATH} on branch {HEAD_BRANCH}.
Push when ready: git -C {WORKTREE_PATH} push origin {HEAD_BRANCH}
```

Do not clean up. Skip Step 9.

### Option 4: Discard

Confirm: ask the user to type "discard". If confirmed:

```bash
git worktree remove --force {WORKTREE_PATH}
```

Do not delete `{HEAD_BRANCH}` itself. Skip Step 9.

---

## Step 9: Watch-and-refix loop

After pushing (Options 1 or 2), enter a bounded watch loop that monitors CI
and review bots. This eliminates the manual "push, wait, come back, re-run"
cycle that dominated both PR #20 and dna#1.

### Phase A: Wait for CI + reviewer stabilization (up to 10 minutes)

Poll in parallel every 60 seconds:

1. **CI checks:** `gh run list --branch {HEAD_BRANCH} --repo {OWNER}/{REPO} --limit 5 --json status,conclusion,name`
   - Track: all checks reach a terminal state (`completed`, `cancelled`, `skipped`)
2. **Review comments:** `gh api repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/comments --jq 'length'`
   - Track: comment count stabilizes (same count for 2 consecutive polls)

Exit the wait when both conditions are met, or after 10 minutes (whichever
comes first).

### Phase B: Assess results

Classify the outcome:

| CI status | New comments | Action |
| --- | --- | --- |
| All green | None | Report success, clean up worktree, done |
| All green | New comments arrived | Enter Phase C (re-fix pass) |
| Failures | Any | Enter Phase C (re-fix pass) |
| Timed out | Any | Report current state, offer manual options |

### Phase C: Automatic re-fix pass (up to 2 cycles)

**Completion conditions (exit the loop immediately when any are met):**

- Phase A returns all-green with no new comments: report success, clean up worktree, done.
- User declines a re-fix pass: report remaining items, keep worktree, done.
- User selects "stop" in the delta prompt: same as decline above.
- Cycle count reaches 2 and issues remain: run stuck-loop diagnosis, present final options, done.

If Phase B indicates issues:

1. Gather the new failures and comments (same as Step 1 sources)
2. Present a delta summary (format below)
3. If the user confirms: apply fixes (same rules as Step 4), verify (Step 5),
   commit (Step 6), push, and re-enter Phase A
4. If the user declines or selects "stop": report remaining items and offer to keep the worktree; exit the loop

Delta summary format:

```text
Post-push findings (cycle {N}/2):
  CI failures:     {list}
  New comments:    {N} ({authors})

Auto-fix these? (yes / review details / stop)
```

**Cycle limit:** Maximum 2 automatic re-fix cycles. After 2 cycles, if issues
remain, run a stuck-loop diagnosis before stopping:

```text
mcp__pal__tiered_consensus(
  level:          PAL_TIERED_LEVEL,
  domain:         "code_review",
  thinking_mode:  PAL_TIERED_THINKING,
  prompt: "A PR fix workflow has completed 2 automatic re-fix cycles but CI
           failures or review comments still remain unresolved. Diagnose why
           the fix attempts are not clearing and suggest a resolution path.

           Remaining failures after 2 cycles:
           {list of remaining CI failures with error output}

           Fixes attempted in each cycle:
           Cycle 1: {summary of fixes applied}
           Cycle 2: {summary of fixes applied}

           Questions:
           1. Are the remaining failures fixable by further automated attempts,
              or do they require human judgment?
           2. Is there a root cause being missed that is causing the same
              symptoms to recur?
           3. What is the most likely path to resolution?

           Return only a JSON object with this shape (no surrounding prose):

             {
               \"can_retry\": <bool>,
               \"root_cause\": \"<one paragraph>\",
               \"blocker\": \"<specific reason automation cannot resolve this; required when can_retry is false>\",
               \"proposed_fix\": \"<specific targeted fix to attempt; required when can_retry is true>\"
             }

           Example can_retry=true response:
             {\"can_retry\": true, \"root_cause\": \"flaky network call\", \"blocker\": \"\", \"proposed_fix\": \"add retry with backoff\"}
           Example can_retry=false response:
             {\"can_retry\": false, \"root_cause\": \"test asserts business rule now intentionally changed\", \"blocker\": \"requires product decision\", \"proposed_fix\": \"\"}"
)
```

Use the `can_retry` field to drive the exit presentation:

- If `can_retry: true`: present `proposed_fix` as Option 1 for a targeted third attempt
- If `can_retry: false`: surface `blocker` as the reason automation is exhausted

Include the PAL diagnosis in the report presented to the user, then stop:

```text
Completed 2 re-fix cycles. Remaining issues:
  {list with reasons}

PAL diagnosis:
  Root cause:    {root_cause from tiered_consensus}
  Can retry:     {yes, proposed fix: {proposed_fix} | no, blocker: {blocker}}

Options:
1. {If can_retry: "Apply targeted fix: {proposed_fix}" / If not: "Keep worktree for manual work"}
2. Push current state and stop
3. Discard all changes
```

**Worktree cleanup:** Clean up the worktree only after the loop completes
with all-green status, or when the user explicitly chooses to discard.

```bash
git worktree remove {WORKTREE_PATH}
```

---

## Error Handling

| Situation | Action |
| --- | --- |
| `gh` / GitHub MCP not authenticated | Stop. Print auth instructions. |
| PR not found or closed | Stop with clear message. |
| Worktree already exists | Remove with `--force` and re-create. |
| Pre-commit fails after 3 attempts | Report failures, ask commit anyway or stop. |
| Finding cannot be auto-fixed | Assign to the appropriate specialized agent (see Priority 3 agent table). Mark "human-only" only when no agent applies. |
| Push rejected (protected/diverged) | Report error. Offer Option 3 (keep worktree). |
| SonarQube MCP unreachable | Log "SonarQube: MCP offline", continue without. |
| No Codecov configured | Log "Coverage: not configured", continue. |
| GitGuardian secret detected | Alert user immediately, never auto-fix. |
