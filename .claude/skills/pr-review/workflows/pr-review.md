# PR Review Workflow

Comprehensive pull request review orchestrated from a GitHub PR URL.
No local checkout. All context fetched via `gh` CLI and SonarQube MCP.

## Input

`$ARGUMENTS` contains the GitHub PR URL, e.g.:
`https://github.com/owner/repo/pull/123`

If `$ARGUMENTS` is empty, check if `gh pr view` resolves a PR for the current
branch. If neither works, ask the user for the PR URL before proceeding.

---

## Step 0 — Parse URL

Extract owner, repo, and PR number from the URL:

```bash
PR_URL="$ARGUMENTS"
OWNER=$(echo "$PR_URL" | sed 's|https://github.com/||' | cut -d'/' -f1)
REPO=$(echo "$PR_URL" | sed 's|https://github.com/||' | cut -d'/' -f2)
PR_NUMBER=$(echo "$PR_URL" | grep -oE '[0-9]+$')
```

Verify extraction succeeded. If any variable is empty, stop and ask the user
to confirm the URL format.

---

## Step 1 — Trigger GitHub Copilot Review (IMMEDIATE, do not wait)

Request a GitHub Copilot review before fetching any data. This fires the async
Copilot review so it runs in parallel with the rest of this workflow.

```bash
gh pr edit "$PR_NUMBER" --repo "$OWNER/$REPO" --add-reviewer "copilot"
```

If that command fails with "not found" or a permissions error, try the API:

```bash
gh api repos/"$OWNER"/"$REPO"/pulls/"$PR_NUMBER"/requested_reviewers \
  --method POST \
  --field "reviewers[]=copilot-pull-request-reviewer"
```

Record whether Copilot review was successfully triggered (yes/no/error) for
the final report. Do not block the rest of the workflow on this step.

---

## Step 2 — Fetch PR Metadata

```bash
gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" \
  --json title,body,state,isDraft,labels,baseRefName,headRefName,author,number
```

**Eligibility check (Haiku agent):**
Abort with a clear message if:
- `state` is `CLOSED`
- `isDraft` is `true` (note it in the report header but continue — drafts can
  be reviewed, user explicitly requested it)

```bash
# Fetch the full diff
gh pr diff "$PR_NUMBER" --repo "$OWNER/$REPO"

# Fetch file list with patch status
gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" --json files
```

Store:
- `PR_TITLE` — PR title
- `PR_BODY` — PR description
- `BASE_BRANCH` — baseRefName
- `HEAD_BRANCH` — headRefName
- `PR_DIFF` — full unified diff text
- `CHANGED_FILES` — list of file paths from the files JSON

---

## Step 3 — Classify Changes (Haiku agent)

Analyze `CHANGED_FILES` and the first 50 lines of `PR_DIFF` to classify:

| Signal | Agent(s) to Activate |
|--------|---------------------|
| `.py` files present | code-reviewer, silent-failure-hunter |
| `test_*.py` or `*_test.py` or `tests/` path | pr-test-analyzer |
| New `class` definitions or `TypeAlias` in diff | type-design-analyzer |
| `try:` / `except` / `raise` changes in diff | silent-failure-hunter (ensure) |
| Docstrings or `#` comment lines changed | comment-analyzer |
| `.sh` / `.bash` files present | code-reviewer (shell mode) |
| `.yml` / `.yaml` / `.json` / `.toml` / `.cfg` only | code-reviewer (config mode) |
| `.md` / `.rst` / `.txt` only | comment-analyzer only |

**Always active regardless of content:**
- `code-reviewer` (CLAUDE.md compliance + bugs)
- `git-history-agent` (blame + history context on modified files)
- `prior-pr-agent` (past review comments on same files)

**Size classification:**
- Small: < 100 lines changed
- Medium: 100–500 lines changed
- Large: > 500 lines changed (note in header; agents get first 500 lines of
  diff with a note about truncation)

---

## Step 4 — Fetch SonarQube Findings (parallel with Step 5)

### 4a. Detect organization

Check for org config in this order:
1. `.sonarlint/connectedMode.json` → `sonarCloudOrganization` field
2. `sonar-project.properties` → `sonar.organization` field
3. Infer from the GitHub owner: `byronwilliamscpa` or `williaby`

Route to the correct MCP server:

| Org | MCP Tool Prefix |
|-----|----------------|
| `byronwilliamscpa` | `mcp__sonarqube__` |
| `williaby` | `mcp__sonarqube-williaby__` |

If neither org is detected, skip SonarQube and note "SonarQube: not configured
for this repository" in the report. Do not block the rest of the workflow.

### 4b. Resolve project key

Check in order:
1. `.sonarlint/connectedMode.json` → `projectKey`
2. `sonar-project.properties` → `sonar.projectKey`

If not found, use `search_my_sonarqube_projects` to list projects and match
by repo name.

### 4c. Fetch PR-specific issues

```
search_sonar_issues_in_projects(
  projects: [PROJECT_KEY],
  pullRequest: PR_NUMBER   ← PR-specific analysis only
)
```

If the PR has not been analyzed yet (empty result), fall back to branch issues:

```
search_sonar_issues_in_projects(
  projects: [PROJECT_KEY],
  branch: HEAD_BRANCH
)
```

Note in the report whether results are PR-specific or branch-level.

### 4d. Store SonarQube findings for the fix step

SonarQube findings are deterministic — they have clear, prescribed fixes and
do not require human judgment. Do not include them in the review report.
Store them as `SONAR_FINDINGS` and pass them to the fix workflow.

For each finding record: file, line, rule key, message, severity. Run a
`show_rule` lookup for any unfamiliar rule key so the fix step has
remediation guidance ready.

The review report shows only a one-line summary: "SonarQube: {N} findings
queued for auto-fix." The fix step resolves them without further review.

---

## Step 5 — Run Parallel Review Agents

Launch all applicable agents simultaneously using the Agent tool. Each agent
receives its context inline (no local git state — all from `gh` output).

**Critical instruction for all agents:**
> Do NOT dismiss any finding as trivial, a nitpick, or "would be caught by
> a linter." Report everything you observe. Categorize it — do not omit it.
> The user reviews all tiers. Confidence scoring happens after you return.

### Agent A — CLAUDE.md Compliance (Sonnet)

```
You are reviewing a GitHub pull request for project standards compliance.

PR: {PR_TITLE} ({OWNER}/{REPO}#{PR_NUMBER})
Base branch: {BASE_BRANCH}

CLAUDE.md content:
{contents of all CLAUDE.md files in the repo, fetched via gh}

PR diff:
{PR_DIFF}

Review the diff against CLAUDE.md. Find every violation — large and small.
Do NOT filter anything as trivial. Report each issue with: file, approximate
line, description, which CLAUDE.md rule it violates.
```

### Agent B — Bug Scan (Sonnet)

```
You are scanning a pull request diff for bugs.

PR diff:
{PR_DIFF}

Scan only the changed lines (additions and modifications). Find:
- Logic errors
- Null/None dereferences
- Off-by-one errors
- Incorrect conditionals
- Missing error handling
- Data integrity risks
- Security vulnerabilities in the changed code

Do NOT filter anything as trivial. Report every issue you find, regardless
of how minor. Include: file, approximate line, description, severity
estimate (Critical / Important / Suggested / Informational).
```

### Agent C — Git History Context (Sonnet)

```
You are reviewing a pull request in the context of the repo's git history.

PR: {OWNER}/{REPO}#{PR_NUMBER}
Changed files: {CHANGED_FILES}

For each changed file:
1. Run: gh api repos/{OWNER}/{REPO}/commits?path={file}&per_page=10
   to see recent commit history on the file
2. Look for patterns: recent reverts, repeated fixes to the same area,
   known fragile code, or prior bugs in the same function

Report any issues the diff introduces that are concerning in light of
the file's history. Include: file, concern, relevant historical context.
```

### Agent D — Prior PR Comments (Sonnet)

```
You are checking whether past review comments apply to a new pull request.

PR: {OWNER}/{REPO}#{PR_NUMBER}
Changed files: {CHANGED_FILES}

For each changed file, search for recent closed PRs that touched it:
  gh pr list --repo {OWNER}/{REPO} --state closed --json number,title,files \
    | jq '[.[] | select(.files[].path == "{file}")][:5]'

For any matching PRs, fetch their review comments:
  gh api repos/{OWNER}/{REPO}/pulls/{found_number}/comments

Report any review comments from those PRs that also apply to the current
changes. Include: original PR number, comment text, why it still applies.
```

### Agent E — Code Comment Accuracy (Sonnet)
*Run only if comment-analyzer is activated in Step 3.*

```
You are reviewing whether code comments and docstrings in a PR are accurate.

PR diff:
{PR_DIFF}

For every docstring, inline comment, or TODO added or modified in the diff:
1. Check whether it accurately describes the surrounding code
2. Identify comment rot (comment says X but code does Y)
3. Flag missing docstrings on new public functions/classes
4. Flag outdated parameter descriptions

Report ALL issues — do not skip anything because it seems minor. Include:
file, line, the comment text, the discrepancy.
```

### Agent F — Silent Failure / Error Handling (Sonnet)
*Run only if silent-failure-hunter is activated in Step 3.*

```
You are reviewing a pull request for silent failures and error handling issues.

PR diff:
{PR_DIFF}

Find every place where errors could be swallowed silently:
- Bare except clauses
- except Exception: pass or similar
- catch blocks that log but don't propagate
- Missing error handling on IO, network, or DB operations
- Fallback values that hide the real error
- Async errors that are not awaited or caught

Do NOT dismiss anything as minor. Report every case: file, line, pattern,
what failure scenario it silences, recommended fix.
```

### Agent G — Test Coverage Quality (Sonnet)
*Run only if pr-test-analyzer is activated in Step 3.*

```
You are reviewing test coverage quality in a pull request.

PR diff:
{PR_DIFF}

For every new or modified function/method/class in the diff:
1. Check whether the PR includes tests for it
2. Identify missing edge cases, boundary conditions, negative tests
3. Flag tests that are too implementation-coupled (test internals, not behavior)
4. Flag missing tests for error conditions introduced in the diff

Rate each gap 1–10 (10 = critical, will cause production failures without it).
Report ALL gaps — do not skip low-rated ones. Include: what's untested,
what failure it could allow, the criticality rating.
```

### Agent H — Type Design (Sonnet)
*Run only if type-design-analyzer is activated in Step 3.*

```
You are reviewing type design in a pull request.

PR diff:
{PR_DIFF}

For every new type definition (class, TypeAlias, TypedDict, dataclass,
Protocol) added in the diff:
1. Evaluate encapsulation: does the type hide implementation details?
2. Evaluate invariants: does the type prevent invalid states?
3. Evaluate usefulness: does it express domain concepts clearly?
4. Check for anemic types (pure data containers with no behavior)
5. Check for types that allow invalid combinations of fields

Rate each dimension 1–10. Report ALL issues — do not skip low scores.
Include: type name, dimension, rating, specific concern.
```

---

## Step 6 — Confidence Scoring (parallel Haiku agents)

For each finding returned by Agents A–H, launch a parallel Haiku agent with:

```
Score this code review finding on a scale of 0–100.

Finding: {finding description}
File: {file}
Agent source: {A|B|C|D|E|F|G|H}
PR diff context: {10 lines of diff around the finding}

Scoring rubric:
- 0:  False positive that doesn't survive basic scrutiny, or pre-existing issue
      unrelated to this PR's changes.
- 25: Might be real, hard to confirm. Speculative.
- 50: Verifiably real, but low impact — affects edge cases rarely hit.
- 75: Real and impactful — will affect users or functionality in normal use.
      Or: directly called out in CLAUDE.md.
- 100: Certain, frequent impact. Direct evidence in the diff confirms it.

Additional constraint: If the agent source is C (Git History) or D (Prior PR
Comments) AND the finding does not point to a specific, fixable line in the
diff — it describes historical context, file churn, or past review patterns
rather than an issue in the changed code — cap the score at 20 regardless of
the rubric above.

Return ONLY a JSON object:
{"score": <number>, "rationale": "<one sentence>"}
```

**Tier assignment from score:**

| Score | Tier |
|-------|------|
| 75–100 | Critical |
| 50–74 | Important |
| 25–49 | Suggested |
| 0–24 | Informational |

**Do not discard any finding.** All four tiers appear in the output.
The old practice of dropping findings below 80 does NOT apply here.

---

## Step 7 — Deduplicate (Haiku agent)

Pass all scored findings from all agents to a single Haiku agent:

```
You are deduplicating a list of code review findings from multiple agents.

Findings:
{all findings as JSON array with agent source, file, line, description, score}

Instructions:
- If two findings describe the same issue at the same location, keep the
  one with the higher score. Add both agent names as sources.
- If two findings describe related but distinct aspects of the same issue,
  keep both but mark them as related.
- Do not merge findings at different files or different lines.
- Preserve all findings — deduplication only removes exact duplicates.

Return a JSON array of deduplicated findings with all original fields preserved.
```

---

## Step 8 — Assemble and Output Report

Present the following report in the terminal. Do NOT post to GitHub
automatically — the user can decide whether to post.

```markdown
# PR Review: {PR_TITLE}
{OWNER}/{REPO}#{PR_NUMBER} | {BASE_BRANCH} ← {HEAD_BRANCH}
{DRAFT WARNING if isDraft}

## Review Status
- **GitHub Copilot**: {Requested / Failed — check manually} — check GitHub
  Reviewers section for results
- **SonarQube**: {N} findings queued for auto-fix
  *(PR-specific / branch-level / not configured)*
- **Agents run**: {list of agents that fired}
- **Agent findings**: {N} ({critical} Critical, {important} Important,
  {suggested} Suggested, {informational} Informational)

---

## Review Agent Findings ({N})

### Critical (must fix before merge)
- **[{agent}]** `{file}:{line}` — {description}
  *(Score: {score} — {rationale})*

### Important (should fix)
- **[{agent}]** `{file}:{line}` — {description}
  *(Score: {score} — {rationale})*

### Suggested (consider addressing)
- **[{agent}]** `{file}:{line}` — {description}
  *(Score: {score} — {rationale})*

### Informational (noted, low priority)
- **[{agent}]** `{file}:{line}` — {description}
  *(Score: {score} — {rationale})*

---

## Recommended Action

1. {First action, starting with Critical fixes}
2. {Second action}
...

---

## Post to GitHub?

To post this review as a PR comment, run:
  /pr-review post
Or confirm now and I will post it immediately.
```

---

## Step 9 — Next Steps Prompt

After the report is output, present exactly these options. Do not add
explanation — keep the prompt concise.

```
Review complete. What would you like to do?

1. Post review to GitHub only
2. Run /pr-fix (gathers CI failures, review comments, SonarQube, coverage,
   and agent findings; fixes all in an isolated worktree)
3. Post to GitHub, then run /pr-fix
4. Done, no further action

Which option?
```

Do not proceed until the user responds. Record the choice as `NEXT_ACTION`.

---

## Step 10 — Execute Next Steps

### Option 1 or 3 — Post to GitHub

Get the HEAD commit SHA:

```bash
gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" --json headRefOid \
  --jq '.headRefOid'
```

Post the condensed review comment:

```bash
gh pr comment "$PR_NUMBER" --repo "$OWNER/$REPO" --body "$(cat <<'EOF'
### PR Review

{condensed report — Critical and Important findings only, with full
SHA-anchored file links:
https://github.com/{OWNER}/{REPO}/blob/{HEAD_SHA}/{file}#L{start}-L{end}}

{SonarQube summary line if findings exist}

Copilot review requested — see Reviewers section for results.

🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

Use the full 40-character SHA in every file link. Never use branch names —
they are mutable.

After posting, if `NEXT_ACTION` is 3, continue to the fix workflow below.
If `NEXT_ACTION` is 1, stop here.

### Option 2 or 3 — Run /pr-fix

Load `workflows/pr-fix.md` and execute it. Pass forward:

- `OWNER`, `REPO`, `PR_NUMBER`
- `HEAD_BRANCH` (the branch to check out in the worktree)
- `FINDINGS` — the full deduplicated, scored findings list from Step 7
- `SONAR_FINDINGS` — SonarQube findings from Step 4 (if any)

The pr-fix workflow runs its own gather step for CI check failures,
review comments, and Codecov status (data that pr-review did not collect),
supplementing the FINDINGS and SONAR_FINDINGS already in context.

---

## Error Handling

| Situation | Action |
|-----------|--------|
| `gh` not authenticated | Stop. Print: "Run `gh auth login` first." |
| PR not found | Stop. Verify the URL and repo access. |
| PR is closed | Stop. Note: "PR #{number} is closed. Provide an open PR URL." |
| PR is draft | Continue with a warning banner in the report header. |
| Copilot reviewer add fails | Log "Copilot: request failed — add manually via GitHub UI." Continue. |
| SonarQube MCP unreachable | Log "SonarQube: MCP server offline — run `/sonarcloud check`." Continue. |
| SonarQube project not found | Log "SonarQube: project not configured for this repo." Continue. |
| Large PR (> 500 lines) | Truncate diff to 500 lines per agent. Note truncation in report header. |
| Agent returns no findings | Include: "{Agent}: No issues found." in the relevant tier section. |
