---
schema_type: planning
title: "PR Workflow Improvement Plan"
status: published
owner: core-maintainer
purpose: "Documents the 22-item roadmap derived from multi-model evaluation of pr-review and pr-fix workflows."
component: Development-Tools
source: "GPT-5.2 subagent evaluation + PAL tiered consensus level 3"
---

> **Status**: Implemented
> **Version**: 1.0.0
> **Created**: 2026-04-13

## Background

Two PRs exercised the new pr-review and pr-fix workflows for the first time:

- `ByronWilliamsCPA/.claude#20`: required many follow-up cycles due to async Copilot timing
  and missing conflict-check before push
- `williaby/dna#1`: required 7 ClusterFuzzLite commits due to no CI dry-run before push

Three subagents evaluated the full workflow (pr.md, pr-review.md, pr-fix.md) against
senior-developer standards, then used `mcp__pal__chat` with `openai/gpt-5.2` to
validate each evaluation. A level-3 tiered consensus synthesized 22 specific
improvements into 4 tiers.

---

## Files in Scope

| File | Path |
| ---- | ---- |
| `pr.md` | `.claude/skills/git/workflows/pr.md` |
| `commit.md` | `.claude/skills/git/workflows/commit.md` |
| `pr-review.md` | `.claude/skills/pr-review/workflows/pr-review.md` |
| `pr-fix.md` | `.claude/skills/pr-review/workflows/pr-fix.md` |

---

## Tier 1: Critical Safety Gaps (implement first, highest defect cost)

### T1-1: Branch-Freshness Gate (`pr.md`)

**File**: `.claude/skills/git/workflows/pr.md`
**Section**: Step 0 (before "Confirm CI gates are green")

**Problem**: PR preparation runs `git merge-base` with no prior `git fetch`. If the
local copy of `origin/main` is stale, the diff may appear correct but diverge at push
time, causing a forced merge commit or conflicts.

**Change**: Insert a new sub-step at the top of Step 0:

```text
#### 0a. Fetch and freshness check

  git fetch origin
  BEHIND=$(git rev-list --count HEAD..origin/main)
  if [ "$BEHIND" -gt 0 ]; then
    echo "Branch is $BEHIND commit(s) behind origin. Rebase before continuing."
    git rebase origin/main
  fi

If rebase produces conflicts, stop here. Resolve conflicts and re-run `/git pr`.
```

**Dependencies**: None.

---

### T1-2: Mandatory Thread Replies for All Outcomes (`pr-fix.md`)

**File**: `.claude/skills/pr-review/workflows/pr-fix.md`
**Section**: Step 8, Option 1 (push changes)

**Problem**: The workflow only instructs posting a reply when fixing an issue. Reviewers
receive no signal when a finding is intentionally deferred or declined, leaving threads
open and reviewers guessing.

**Change**: In the "Reply to review threads" instruction within Option 1, replace the
current instruction with:

```text
For every finding in FINDINGS, post a reply to its GitHub thread:

  Outcome   | Reply format
  Fixed     | "Fixed in {commit SHA}: {one sentence description of what changed}"
  Deferred  | "Deferred: {reason}. Tracked in {ticket or follow-up issue number}."
  Declined  | "Declined: {reason}. This is intentional because {explanation}."

Never leave a thread without a reply. Reviewers must be able to mark threads resolved
without chasing context.
```

**Dependencies**: None.

---

### T1-3: Fix Scope-Restriction Language (`pr-fix.md`)

**File**: `.claude/skills/pr-review/workflows/pr-fix.md`
**Section**: Step 4, Priority 3 (scoping instruction)

**Problem**: The current instruction "do not fix anything outside the stated finding"
prevents fixing the root cause when the root cause lives in a different function than
the symptom reported. This has caused fixes that patch symptoms rather than causes.

**Change**: Replace the current Priority 3 scoping rule with:

```text
Priority 3, scope: Fix the root cause of each finding, even if it lives in a
different function or file than where the symptom was reported. Keep the diff as small
as the root cause requires. Do not refactor unrelated code, rename variables for
style, or add features not requested. When the root cause fix touches more than 3 files
not in the original diff, pause and confirm with the user before proceeding.
```

**Dependencies**: None.

---

### T1-4: Surface PR URL Immediately (`pr.md`)

**File**: `.claude/skills/git/workflows/pr.md`
**Section**: Step 5, after `gh pr create`

**Problem**: Step 6 blocks on `/pr-review` completing before showing the user the PR
URL. If the review takes several minutes, the user has no link to share or monitor.

**Change**: After the `gh pr create` command in Step 5, add:

```text
Print the PR URL returned by `gh pr create` to the user immediately. Do not wait for
the review in Step 6 to complete before showing it.
```

Then update Step 6 to say "Run `/pr-review` after sharing the PR URL with the user"
rather than implying the URL is withheld until review completes.

**Dependencies**: None.

---

## Tier 2: Review Depth and Coverage Gaps (high value, moderate effort)

### T2-5: CI Status Ingestion (`pr-review.md`)

**File**: `.claude/skills/pr-review/workflows/pr-review.md`
**Section**: Step 2 (gather context), add as new sub-step 2c

**Problem**: The review assembles findings from code analysis but ignores CI check
results. A PR with a failing test suite passes through pr-review without any Critical
finding for the broken build.

**Change**: Add Step 2c before Step 3:

```text
#### 2c. CI status

  gh pr checks {PR_NUMBER} --repo {OWNER}/{REPO} \
    --json name,status,conclusion,detailsUrl \
    --jq '.[] | {name, status, conclusion, detailsUrl}'

Store as CI_CHECKS. For any check with conclusion != "success" and conclusion != null
(null means in-progress), emit a Critical finding:

  [Critical] CI: {check name}: {conclusion} ({detailsUrl})
  Confidence: 100 (objective CI result)

If any Critical CI finding exists, the report header must say:
BUILD FAILING: do not merge until CI is green.
```

**Dependencies**: None. Feeds into T4-20 (severity distribution) and T4-22 (URL
parser, since detailsUrl may contain query strings).

---

### T2-6: Agent I: Dedicated Security Pass (`pr-review.md`)

**File**: `.claude/skills/pr-review/workflows/pr-review.md`
**Section**: Step 5 (parallel agents), add Agent I after Agent H

**Problem**: Security findings are currently mixed into general agent outputs with no
guarantee of coverage. Injection, SSRF, and path traversal can appear anywhere in a
diff and require dedicated focus to catch reliably.

**Change**: Add Agent I specification:

```text
Agent I: Security Pass

Scope: The full diff (all files).

Checks (each must be explicitly evaluated, not skipped if "no match found"):
- SQL injection: string concatenation into queries, f-string queries, execute() with
  user-supplied input
- Command injection: subprocess calls, shell execution APIs (eval, exec) with
  user-supplied input
- Path traversal: file open operations without resolve() plus base-path check
- SSRF: outbound HTTP calls where the URL contains user-supplied hostname or path
- Authentication bypass: routes missing auth decorator, permission checks skipped by
  early return
- Secrets in code: API keys, tokens, passwords hardcoded or logged
- Insecure deserialization: unsafe deserialization of untrusted binary data,
  yaml.load without Loader=SafeLoader

For each check, output one of:
  [Critical] Security/{check}: {finding}     (if a vulnerability is found)
  [Info] Security/{check}: No issues found   (if clean; always emit, never skip)

Confidence scoring: Critical findings get 90 unless the vulnerability requires
attacker-controlled input that is demonstrably impossible, in which case 70.
```

**Dependencies**: None.

---

### T2-7: Agent J: PR Description vs Diff Validation (`pr-review.md`)

**File**: `.claude/skills/pr-review/workflows/pr-review.md`
**Section**: Step 5 (parallel agents), add Agent J after Agent I

**Problem**: PR descriptions frequently claim changes that are not in the diff, or omit
changes that are in the diff. This misleads reviewers and creates merge risk.

**Change**: Add Agent J specification:

```text
Agent J: PR Description vs Diff Validation

Inputs: PR_BODY (full PR description text), CHANGED_FILES list, diff.

Checks:
1. For each component or change claimed in PR_BODY "## Changes" section: verify a
   corresponding file or function change exists in the diff. Flag as Important if
   not found.
2. For each file in CHANGED_FILES: verify it is mentioned (directly or by implication)
   in PR_BODY. Flag as Suggested if a changed file is not referenced.
3. Check that PR_BODY contains a "## Why" or equivalent motivation section. Flag as
   Suggested if absent.
4. Check that PR_BODY references an issue number (Fixes #N, Closes #N, or Relates to
   #N) if the PR is labeled as a bug fix. Flag as Suggested if absent.

Output findings as:
  [Important] PRDesc: {finding}   (for case 1)
  [Suggested] PRDesc: {finding}   (for cases 2, 3, 4)
```

**Dependencies**: T3-10 (template rewrite adds "## Why"; this agent checks for it).
Implement T3-10 first or make the "## Why" check conditional on whether the template
was already updated.

---

### T2-8: File Context Fetching for Agents B, F, G (`pr-review.md`)

**File**: `.claude/skills/pr-review/workflows/pr-review.md`
**Section**: Step 5, preamble before individual agent listings

**Problem**: Agents receive only the patch (zero context lines). A bug that only
manifests through interaction with a calling function, or a test that only makes sense
in the context of the class it tests, requires surrounding context to evaluate
correctly.

**Change**: In the Step 5 preamble (before listing individual agents), add:

```text
#### File context fetch (run before spawning agents)

For each file in CHANGED_FILES that has more than 10 lines changed:

  gh api repos/{OWNER}/{REPO}/contents/{FILE_PATH}?ref={HEAD_SHA} \
    --jq '.content' | base64 -d > /tmp/context_{FILE_SLUG}.txt

Store as CONTEXT_FILES map: {file_path: full_file_content}.

Agents B, F, and G receive CONTEXT_FILES in addition to the diff. Their instructions
should say: "When evaluating a changed function, read the surrounding 200 lines from
CONTEXT_FILES to understand callers and callees before issuing findings."
```

**Dependencies**: None. Increases token cost per review; monitor for cost regression.

---

### T2-9: Self-Review Diff Scan (`pr.md`)

**File**: `.claude/skills/git/workflows/pr.md`
**Section**: New Step 1b, inserted after Step 1 (gather context) and before Step 2
(analyze changes)

**Problem**: PR authors submit debug prints, TODO comments, hardcoded test values, and
scope-crept changes without noticing them. A self-review step catches these before a
reviewer sees them.

**Change**: Insert Step 1b:

```text
### 1b. Self-review diff scan

Before writing the description, scan the diff for common authoring mistakes:

  git diff $(git merge-base HEAD main)..HEAD | grep -n \
    -e 'print(' \
    -e 'console\.log' \
    -e 'TODO\|FIXME\|HACK\|XXX' \
    -e 'debugger' \
    -e 'pdb\.set_trace\|breakpoint()' \
    -e 'password\s*=\s*[...non-placeholder value...]' \
    -e 'api_key\s*=\s*[...non-placeholder value...]'

If any match is found, report it to the user:
  "Self-review found: {list of matches with file:line}. Confirm these are intentional
  before continuing."

Do not block if the user confirms. Do block (stop and ask) for any apparent secret
(pattern matching password = or api_key = with a non-placeholder value).
```

**Dependencies**: None. Should run before T3-10 (description template) so the
description reflects a clean diff.

---

## Tier 3: Process Completeness (closes common senior-dev gaps)

### T3-10 + T4-17: PR Description Template Rewrite and Testing Checklist (`pr.md`)

**File**: `.claude/skills/git/workflows/pr.md`
**Section**: Step 3 (generate PR description), template block

**Problem**: The current template lacks "Why" (motivation), "Acceptance Criteria"
(definition of done), and "Migration/Rollback" (operational safety). The testing
checklist only covers pytest and ruff, missing format checks and type checking.
These two items share the same template block and must be implemented together.

**Change**: Replace the entire template block in Step 3 with:

```markdown
## Summary

[1-3 sentences: what changed and why, including the business or technical motivation]

## Why

[1-2 sentences: what problem this solves, what risk this mitigates, or what user need
this addresses. Link to issue or ticket if applicable. `Fixes #N` / `Closes #N`]

## Changes

- **[Component]**: [What changed and why, specific enough that a reviewer can
  find the change in the diff]
- **[Component]**: [What changed and why]

## Acceptance Criteria

- [ ] [Specific, testable condition that must be true when this PR is merged]
- [ ] [Another condition]

## Impact

- [Key benefit or outcome]
- [Another benefit]
- No breaking changes / Breaking change: [describe migration path]

## Migration and Rollback

[If no migration is needed: "No migration required."]
[If a migration is needed: describe the steps, the rollback procedure, and any
 data loss risk]

## Testing

- [ ] Tests pass (`uv run pytest`)
- [ ] Format clean (`uv run ruff format --check`)
- [ ] Lint clean (`uv run ruff check`)
- [ ] Type check clean (`uv run basedpyright`)
- [ ] CHANGELOG updated (for feat/fix/perf/breaking changes)

## Notes

[Optional: known issues, follow-up work, dependencies, reviewer focus areas]
```

**Note on CHANGELOG**: The "CHANGELOG updated" checkbox covers T4-17 (expanded
testing checklist). The explicit check in Step 2 (T3-11a) covers automated detection.

**Dependencies**: T2-7 (Agent J checks for "## Why"); implement this template before
or at the same time as Agent J. T4-17 is merged into this item.

---

### T3-11a: CHANGELOG Check in PR Preparation (`pr.md`)

**File**: `.claude/skills/git/workflows/pr.md`
**Section**: Step 2 (analyze changes), end of section

**Problem**: CHANGELOG updates are frequently omitted for feat/fix/perf/breaking
changes. No current step verifies it before the PR is created.

**Change**: Add to the end of Step 2:

```text
#### CHANGELOG check

  git diff $(git merge-base HEAD main)..HEAD -- CHANGELOG.md

If the output is empty AND the commit history contains any feat:, fix:, perf:, or !
(breaking) commit, emit a warning:

  "CHANGELOG.md has not been updated. For feat/fix/perf/breaking changes, add an entry
  before creating the PR."

Do not auto-generate the CHANGELOG entry from the commit message. Present the relevant
commits and ask the user to author the entry.
```

**Dependencies**: Coordinates with T3-11b (pr-review checks it) and T3-11c (pr-fix
validates it). All three should be implemented together.

---

### T3-11b: CHANGELOG Check in Agent A (`pr-review.md`)

**File**: `.claude/skills/pr-review/workflows/pr-review.md`
**Section**: Step 5, Agent A (CLAUDE.md compliance) instructions

**Problem**: Agent A checks for CLAUDE.md compliance but does not verify CHANGELOG
updates, which are required by the OpenSSF baseline in CLAUDE.md.

**Change**: In Agent A's instruction block, add a check:

```text
- CHANGELOG: If CHANGED_FILES contains feat/fix/perf/breaking commits (check
  git log {BASE}..HEAD --oneline for commit type prefixes), verify that CHANGELOG.md
  appears in CHANGED_FILES. If absent:
    [Important] CLAUDE.md: CHANGELOG.md not updated for feat/fix/perf/breaking change
```

**Dependencies**: T3-11a (preparation check), T3-11c (fix validation).

---

### T3-11c: CHANGELOG Validation in PR Fix (`pr-fix.md`)

**File**: `.claude/skills/pr-review/workflows/pr-fix.md`
**Section**: Step 4, Priority 1 (Critical findings)

**Problem**: When pr-fix addresses Critical findings, it does not check whether
CHANGELOG was updated as part of the fix batch.

**Change**: Add to Priority 1 instructions:

```text
After addressing all Critical findings, verify CHANGELOG.md has been updated if
the branch contains feat/fix/perf/breaking commits:

  git diff origin/main..HEAD -- CHANGELOG.md | head -5

If empty and commits require a CHANGELOG entry, ask the user to provide the entry text
rather than generating it automatically. Do not invent version numbers or release dates.
```

**Dependencies**: T3-11a, T3-11b.

---

### T3-12: Unify Test Policy (`pr-fix.md`)

**File**: `.claude/skills/pr-review/workflows/pr-fix.md`
**Section**: Step 4, Priority 3 and Priority 4

**Problem**: Priority 3 says "add a proof-of-fix test" while Priority 4 contradicts by
implying tests are optional ("if time permits"). The contradiction causes inconsistent
behavior depending on which priority the agent processes last.

**Change**: Remove the Priority 3/Priority 4 test-policy language and replace with a
single unified block at the end of Step 4:

```text
#### Test requirement for all findings

For every Critical or Important finding that is fixed:
- Add or update a test that would have caught the finding before the fix.
- The test must fail on the pre-fix code and pass on the post-fix code.
- If a test is impossible (e.g., finding is a doc update or a config style issue),
  note "No test required: {reason}" in the commit message.

For Suggested or Informational findings:
- Add a test if one can be written in under 15 minutes.
- Otherwise, note the finding is addressed without a test and explain why.

Never skip tests for Critical findings without explicit user approval.
```

**Dependencies**: None.

---

### T3-13: Demote Unsafe SonarQube Auto-Fixes (`pr-fix.md`)

**File**: `.claude/skills/pr-review/workflows/pr-fix.md`
**Section**: Step 4, SonarQube auto-fix instructions (wherever auto-apply logic exists)

**Problem**: The workflow currently auto-applies SonarQube suggestions without
confirmation for fixes that carry semantic risk: regex rewrites, shell if-merge
patterns, permission scoping changes, and dead-code removal. These have caused
regressions in other projects.

**Change**: Add a "require confirmation" gating rule before any SonarQube auto-fix:

```text
The following SonarQube rule categories require propose-and-confirm rather than
auto-apply:

  Category              | Examples                                    | Risk
  Regex rewrites        | Simplifying character classes, rm escapes   | Changes match behavior
  Shell if-merge        | Combining nested if into single condition   | Logic equivalence not guaranteed
  Permission scoping    | Narrowing file permissions                  | May break runtime behavior
  Dead-code removal     | Removing functions flagged as unreachable   | May have dynamic callers
  Serialization changes | Changing JSON field names, removing fields  | Wire-format breaking change

For these categories, present the proposed change and ask "Apply this fix? (y/n)"
before making any edit.

Auto-apply is safe for: import ordering, whitespace, missing docstrings, unused
import removal (when no __all__ exports), explicit None return types.
```

**Dependencies**: None.

---

### T3-14: Replace Large-PR Truncation (`pr-review.md`)

**File**: `.claude/skills/pr-review/workflows/pr-review.md`
**Section**: Step 3 or wherever diff loading/truncation logic is specified

**Problem**: The current workflow silently truncates diffs larger than 500 lines,
meaning agents may never see the second half of a large PR. This creates false
confidence in review completeness.

**Change**: Replace the truncation logic with one of two explicit strategies:

```text
#### Large-PR handling

If the total diff exceeds 500 lines:

Strategy A: Per-file chunking (preferred for PRs with many small files):
Split CHANGED_FILES into batches of 10 files each. Run all agents once per batch.
Merge findings across batches before assembling the report. Label each finding with
the batch file that produced it.

Strategy B: Hard stop (preferred for PRs with one or two very large files):
Emit a Critical finding:
  [Critical] Review: Diff exceeds 500 lines ({actual count} lines). Review requires
  manual split or per-section analysis. pr-review cannot guarantee complete coverage
  of diffs this large.

Then continue with the first 500 lines, clearly labeling the report:
  "WARNING: Review covers lines 1-500 only. Lines 501 onward were not analyzed."

Never silently truncate. Always tell the user what was and was not reviewed.
```

**Dependencies**: T2-8 (file context fetching); coordinate so context files for
chunked batches are fetched per-batch, not all upfront.

---

### T3-15: Agent K: Performance Review (`pr-review.md`)

**File**: `.claude/skills/pr-review/workflows/pr-review.md`
**Section**: Step 5 (parallel agents), add Agent K after Agent J

**Problem**: No agent currently checks for performance anti-patterns. N+1 queries,
blocking I/O in async context, and quadratic-complexity loops have shipped undetected.

**Change**: Add Agent K specification:

```text
Agent K: Performance Review

Scope: The full diff (all files) plus CONTEXT_FILES for files with more than 10 lines
changed.

Checks:
- N+1 queries: ORM calls inside loops (e.g., for item in queryset: item.related.all())
- Blocking I/O in async context: synchronous HTTP calls or file reads inside async def
- Unbounded loops: while True or iteration with a database/network call and no limit
- Quadratic complexity: nested loops where both iterables grow with user input
- Missing pagination: list endpoints returning unbounded result sets
- Large in-memory loads: loading entire files or tables without streaming

For each issue found:
  [Important] Perf/{category}: {finding}; estimated impact: {brief impact statement}

If no issues found:
  [Info] Perf: No performance issues detected in diff
```

**Dependencies**: T2-8 (file context fetching, needed for N+1 detection in callers).

---

## Tier 4: Polish and Robustness

### T4-16: Fix `git add .` Default in Commit Workflow (`commit.md`)

**File**: `.claude/skills/git/workflows/commit.md`
**Section**: Step 4 (handle staging), staging options list

**Problem**: The current workflow lists "Stage all changes? (`git add .`)" as the
first option, making it the default. `git add .` can accidentally stage secrets,
build artifacts, or unrelated work-in-progress files.

**Change**: Reorder the staging options so file-by-file is first:

```text
If there are unstaged changes, choose a staging strategy:

1. Stage specific files (recommended):
     git add path/to/file1 path/to/file2

2. Review changes first (if uncertain what to include):
     git diff --stat
     git diff path/to/file

3. Stage all changes (use with caution -- verify no secrets or build artifacts):
     git add .
     git status   # review the staged list before committing

   Always run git status after git add . to confirm only intended files are staged.
```

**Dependencies**: None.

---

### T4-18: PR Size and Split Heuristic (`pr.md`)

**File**: `.claude/skills/git/workflows/pr.md`
**Section**: Step 2 (analyze changes), after the existing "Identify" block

**Problem**: PRs larger than 400 lines or spanning 3 or more unrelated functional
domains are harder to review, more likely to cause merge conflicts, and statistically
more likely to introduce bugs. No current step surfaces this to the author.

**Change**: Add to Step 2 after the identify block:

```text
#### PR size check

  LINES_CHANGED=$(git diff $(git merge-base HEAD main)..HEAD --stat | \
    tail -1 | grep -oP '\d+ insertion' | grep -oP '\d+')
  DOMAINS=$(git diff $(git merge-base HEAD main)..HEAD --name-only | \
    cut -d/ -f1 | sort -u | wc -l)

If LINES_CHANGED > 400 or DOMAINS >= 3:
  "This PR is large ({LINES_CHANGED} lines changed, {DOMAINS} top-level directories).
  Consider splitting into smaller PRs by logical area. Suggested splits:
  {list CHANGED_FILES grouped by top-level directory}

  Continue as a single PR? (y/n)"

If the user says yes, continue. If no, help them identify split boundaries using the
directory grouping above.
```

**Dependencies**: None.

---

### T4-19: Repo-Driven CI Gate Command (`pr-fix.md`)

**File**: `.claude/skills/pr-review/workflows/pr-fix.md`
**Section**: Step 5 (CI gate / pre-push verification)

**Problem**: Step 5 hardcodes `uv run pytest && uv run ruff check && uv run ruff
format --check`. Projects using `nox`, `tox`, `make ci`, or a `scripts/ci.sh` runner
fail this step because the hardcoded commands do not match the project's actual CI
entrypoint.

**Change**: Replace the hardcoded CI command with a detection-first sequence:

```text
#### 5a. Detect CI entrypoint

Check in order:

1. noxfile.py exists and uv run nox --list succeeds:
     use: uv run nox -s lint tests
2. tox.ini or pyproject.toml [tool.tox] section exists:
     use: uv run tox
3. Makefile with a ci target (grep -q '^ci:' Makefile):
     use: make ci
4. scripts/ci.sh or scripts/test.sh exists:
     use: bash scripts/ci.sh
5. Fallback:
     use: uv run pytest && uv run ruff check && uv run ruff format --check && uv run basedpyright

Store the detected command as CI_CMD. Always echo "Using CI entrypoint: {CI_CMD}"
before running so the user can verify.
```

**Dependencies**: None. Required by T4-21.

---

### T4-20: SonarQube Severity Distribution in Report (`pr-review.md`)

**File**: `.claude/skills/pr-review/workflows/pr-review.md`
**Section**: Step 9 (assemble report), report header template

**Problem**: The report lists SonarQube findings inline but gives no summary count by
severity, making it hard to gauge overall SonarQube health at a glance.

**Change**: In the report header block (the summary table before the findings list),
add a SonarQube row:

```text
| SonarQube | Blocker: {N} | Critical: {N} | Major: {N} | Minor: {N} | Info: {N} |
```

Populate counts from SONAR_FINDINGS. If SonarQube is not configured or returned no
findings, show:

```text
| SonarQube | Not configured / No findings |
```

**Dependencies**: T2-5 (CI status); coordinate report header layout so CI status
and SonarQube distribution appear in adjacent rows.

---

### T4-21: Restrict Known-Failures Commit Gate (`pr-fix.md`)

**File**: `.claude/skills/pr-review/workflows/pr-fix.md`
**Section**: Step 8, Option 4 (commit with known CI failures) or equivalent

**Problem**: The current workflow allows committing when CI is failing without checking
whether those failures are pre-existing or newly introduced by the fix. This can ship
new regressions under the cover of pre-existing failures.

**Change**: Replace the unrestricted "commit with known failures" option with:

```text
Option 4: Commit with pre-existing CI failures (restricted):

Before using this option:

  git stash
  {CI_CMD} 2>&1 | grep -E 'FAILED|ERROR' > /tmp/pre_pr_failures.txt
  git stash pop
  {CI_CMD} 2>&1 | grep -E 'FAILED|ERROR' > /tmp/post_pr_failures.txt
  diff /tmp/pre_pr_failures.txt /tmp/post_pr_failures.txt

If diff shows new failures not present before the PR: do not commit. Fix the
new failures first.

If failures are identical to pre-PR baseline: allowed to commit, but must:
1. Post a PR comment: "Known pre-existing CI failures: {list}. These failures existed
   before this branch was created and are not caused by changes in this PR."
2. Link to or create a tracking issue for each pre-existing failure.
```

**Dependencies**: T4-19 (CI_CMD detection must run first).

---

### T4-22: Fix URL Parser (`pr-review.md`)

**File**: `.claude/skills/pr-review/workflows/pr-review.md`
**Section**: Step 1 (parse PR URL, extract OWNER/REPO/PR_NUMBER)

**Problem**: The URL parser fails on trailing slashes and query strings (e.g.,
`https://github.com/owner/repo/pull/123?diff=unified`). This causes downstream
failures when OWNER, REPO, or PR_NUMBER is parsed incorrectly.

**Change**: Replace the current URL parsing instruction with:

```text
#### 1. Parse PR URL

Strip trailing slashes and query strings before parsing:

  CLEAN_URL=$(echo "{PR_URL}" | sed 's|[?#].*||' | sed 's|/\+$||')
  OWNER=$(echo "$CLEAN_URL" | cut -d/ -f4)
  REPO=$(echo "$CLEAN_URL" | cut -d/ -f5)
  PR_NUMBER=$(echo "$CLEAN_URL" | cut -d/ -f7)

Echo the resolved values for verification:
  Resolved: {OWNER}/{REPO}#{PR_NUMBER}

If any value is empty, stop and report:
  "Could not parse PR URL: {PR_URL}. Expected format:
   https://github.com/owner/repo/pull/123"
```

**Dependencies**: T2-5 (CI status) uses `detailsUrl` from gh output which may
contain query strings. Apply the same cleaning pattern there.

---

## Implementation Order

| Order | Item | File | Tier | Est. Size |
| ----- | ---- | ---- | ---- | --------- |
| 1 | T1-1 | pr.md | 1 | Small |
| 2 | T1-2 | pr-fix.md | 1 | Small |
| 3 | T1-3 | pr-fix.md | 1 | Small |
| 4 | T1-4 | pr.md | 1 | Small |
| 5 | T4-22 | pr-review.md | 4 | Small |
| 6 | T2-5 | pr-review.md | 2 | Medium |
| 7 | T3-14 | pr-review.md | 3 | Medium |
| 8 | T2-8 | pr-review.md | 2 | Medium |
| 9 | T2-6 | pr-review.md | 2 | Large |
| 10 | T2-7 | pr-review.md | 2 | Medium |
| 11 | T3-15 | pr-review.md | 3 | Medium |
| 12 | T3-11b | pr-review.md | 3 | Small |
| 13 | T4-20 | pr-review.md | 4 | Small |
| 14 | T2-9 | pr.md | 2 | Medium |
| 15 | T3-11a | pr.md | 3 | Small |
| 16 | T3-10+17 | pr.md | 3 | Medium |
| 17 | T4-18 | pr.md | 4 | Small |
| 18 | T3-12 | pr-fix.md | 3 | Small |
| 19 | T3-13 | pr-fix.md | 3 | Medium |
| 20 | T3-11c | pr-fix.md | 3 | Small |
| 21 | T4-19 | pr-fix.md | 4 | Small |
| 22 | T4-21 | pr-fix.md | 4 | Medium |
| 23 | T4-16 | commit.md | 4 | Small |

---

## Cross-Item Dependencies

```text
T3-11a (pr.md CHANGELOG check) --> T3-11b (pr-review Agent A CHANGELOG check)
                               --> T3-11c (pr-fix CHANGELOG validation)

T3-10 (template rewrite) --> T2-7 (Agent J checks for ## Why section)
T4-17 merged into T3-10 (testing checklist is part of the template)

T2-8 (context fetch preamble) --> T2-6 (Agent I can use CONTEXT_FILES)
                             --> T3-14 (per-batch context fetch coordination)
                             --> T3-15 (Agent K uses CONTEXT_FILES)

T4-19 (CI_CMD detection) --> T4-21 (uses CI_CMD for pre/post failure diff)

T2-5 (CI status ingestion) --> T4-20 (report header layout)
T4-22 (URL parser) should precede T2-5 (both handle URLs with query strings)
```

---

## Implementation Notes

- All items in `pr-review.md` must not break the existing Step numbering (Steps 1-11
  after the polling gate was added in the prior session).
- No em-dashes in any content added. Use commas, semicolons, or restructured sentences.
- All fenced code blocks must be surrounded by blank lines (MD031 requirement).
- After implementing each item, run `pre-commit run --all-files` on the modified file
  before marking the TODO complete.
- Items in the same file should be batched into a single editing session where possible
  to reduce re-read overhead.
