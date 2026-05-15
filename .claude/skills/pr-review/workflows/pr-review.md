# PR Review Workflow

Comprehensive pull request review orchestrated from a GitHub PR URL.
No local checkout. All context fetched via `gh` CLI and SonarQube MCP.

## Input

`$ARGUMENTS` contains the GitHub PR URL, e.g.:
`https://github.com/owner/repo/pull/123`

If `$ARGUMENTS` is empty, check if `gh pr view` resolves a PR for the current
branch. If neither works, ask the user for the PR URL before proceeding.

---

## Configuration

PAL tool parameters used throughout this workflow. Edit these values to tune
model selection and consensus depth without touching the workflow logic.

```text
PAL_CHAT_MODEL:        google/gemini-2.5-pro-preview
PAL_CONSENSUS_MODELS:  ["google/gemini-2.5-pro-preview", "openai/gpt-4o"]
PAL_TIERED_LEVEL:      1
PAL_TIERED_THINKING:   auto
```

- `PAL_CHAT_MODEL`: model passed to `mcp__pal__chat` for targeted validations
- `PAL_CONSENSUS_MODELS`: model list passed to `mcp__pal__consensus` for Agent L
- `PAL_TIERED_LEVEL`: level (1/2/3) for all `mcp__pal__tiered_consensus` calls;
  level 1 uses 3 free models, level 2 adds paid models (~$0.50), level 3 is
  comprehensive (~$5)
- `PAL_TIERED_THINKING`: thinking depth for tiered_consensus (`auto`, `low`,
  `high`)

---

## Step 0: Parse URL

Extract owner, repo, and PR number from the URL:

```bash
PR_URL="$ARGUMENTS"
CLEAN_URL=$(echo "$PR_URL" | sed 's|[?#].*||' | sed 's|/\+$||')
OWNER=$(echo "$CLEAN_URL" | cut -d'/' -f4)
REPO=$(echo "$CLEAN_URL" | cut -d'/' -f5)
PR_NUMBER=$(echo "$CLEAN_URL" | cut -d'/' -f7)
```

Echo the resolved values for verification:

```text
Resolved: {OWNER}/{REPO}#{PR_NUMBER}
```

If any variable is empty, stop and report: "Could not parse PR URL: {PR_URL}. Expected
format: `https://github.com/owner/repo/pull/123`"

---

### Step 1: Confirm GitHub Copilot Review is queued

Copilot is enrolled as an automatic reviewer via the `copilot_code_review`
rule in the org ruleset (`<ORG>-default-branch-baseline` in both
ByronWilliamsCPA and williaby). It is requested when the PR opens.
No API call from this workflow is needed.

Verify it landed (one-line, non-blocking):

```bash
gh api repos/"$OWNER"/"$REPO"/pulls/"$PR_NUMBER" \
  --jq '.requested_reviewers[].login' | grep -q copilot-pull-request-reviewer \
  && echo "Copilot: ruleset-requested OK" \
  || echo "Copilot: NOT requested -- verify copilot_code_review rule in org ruleset"
```

If verification fails, the `copilot_code_review` rule is missing or
disabled. Re-apply via:

```bash
uv run python scripts/setup_org_rulesets.py --org {ORG} \
  --body docs/reference/org-rulesets/{ORG}-universal.json --enforcement active
```

Do not block the rest of this workflow on the result.

---

## Step 2: Fetch PR Metadata

```bash
gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" \
  --json title,body,state,isDraft,labels,baseRefName,headRefName,author,number,mergeStateStatus
```

**Eligibility check (Haiku agent):**
Abort with a clear message if:

- `state` is `CLOSED`
- `isDraft` is `true` (note it in the report header but continue; drafts can
  be reviewed, user explicitly requested it)

```bash
# Fetch the full diff
gh pr diff "$PR_NUMBER" --repo "$OWNER/$REPO"

# Fetch file list with patch status
gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" --json files
```

Store:

- `PR_TITLE`: PR title
- `PR_BODY`: PR description
- `BASE_BRANCH`: baseRefName
- `HEAD_BRANCH`: headRefName
- `MERGE_STATE`: mergeStateStatus
- `PR_DIFF`: full unified diff text
- `CHANGED_FILES`: list of file paths from the files JSON

### 2c. CI status

> Note: `gh pr checks --json` uses `state` and `link`, NOT `status`, `conclusion`, or `detailsUrl` — those are REST API field names. Passing the wrong names causes "Unknown JSON field" errors.

```bash
gh pr checks "$PR_NUMBER" --repo "$OWNER/$REPO" \
  --json name,state,description,link \
  --jq '.[] | {name, state, description, link}'
```

Store as `CI_CHECKS`. For any check where `state` is not `SUCCESS` and not
`PENDING` (PENDING means in-progress; skip it), classify the finding using the
branch state diagnostic before emitting.

**Branch state diagnostic (applies when `MERGE_STATE == "BEHIND"`):**

When `MERGE_STATE` is `BEHIND`, a CI failure may originate in the diverged base
history rather than in the PR's diff. Fetch the base branch's check results to
distinguish the two cases:

```bash
BASE_SHA=$(gh api repos/"$OWNER"/"$REPO"/branches/"$BASE_BRANCH" \
  --jq '.commit.sha')
BASE_CHECKS=$(gh api repos/"$OWNER"/"$REPO"/commits/"$BASE_SHA"/check-runs \
  --jq '[.check_runs[] | {name: .name, conclusion: .conclusion}]')
```

For each failing check in `CI_CHECKS`, look up the same check name in `BASE_CHECKS`:
- Fails on base too: emit `[Critical - pre-existing, rebase needed]` — the fix is rebase, not code change.
- Passes on base (or absent from base): emit `[Critical - PR-introduced]` — the fix is in the PR's diff.
- `MERGE_STATE` is not `BEHIND`: emit `[Critical]` — divergence attribution does not apply.

Emit each finding:

```text
[Critical] CI: {check name}: {state} ({link})
Confidence: 100 (objective CI result)
```

If any Critical CI finding exists, the report header must include:
**BUILD FAILING: do not merge until CI is green.**

If any finding is tagged `[Critical - pre-existing, rebase needed]`, also add to the header:
**BRANCH BEHIND: some failures may clear after rebasing on {BASE_BRANCH}.**

---

## Step 3: Classify Changes (Haiku agent)

Analyze `CHANGED_FILES` and the first 50 lines of `PR_DIFF` to classify:

| Signal | Agent(s) to Activate |
| ------ | -------------------- |
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
- Large: > 500 lines changed (see large-PR handling strategy at the top of Step 5)

---

## Step 4: Fetch SonarQube Findings (parallel with Step 5)

### 4a. Detect organization

Check for org config in this order:

1. `.sonarlint/connectedMode.json` → `sonarCloudOrganization` field
2. `sonar-project.properties` → `sonar.organization` field
3. Infer from the GitHub owner: `byronwilliamscpa` or `williaby`

Route to the correct MCP server:

| Org | MCP Tool Prefix |
| ----- | ---------------- |
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

```text
search_sonar_issues_in_projects(
  projects: [PROJECT_KEY],
  pullRequest: PR_NUMBER   ← PR-specific analysis only
)
```

If the PR has not been analyzed yet (empty result), fall back to branch issues:

```text
search_sonar_issues_in_projects(
  projects: [PROJECT_KEY],
  branch: HEAD_BRANCH
)
```

Note in the report whether results are PR-specific or branch-level.

### 4f. Fetch PR-specific security hotspots

Security hotspots are a completely separate queue from issues in SonarCloud.
`search_sonar_issues_in_projects` never returns them; this explicit call is
required. Skipping it is the most common reason hotspots go unreviewed.

```text
search_security_hotspots(
  projectKey: PROJECT_KEY,
  pullRequest: PR_NUMBER
)
```

If the result is empty (PR not yet analyzed), fall back to branch-level with
status filter:

```text
search_security_hotspots(
  projectKey: PROJECT_KEY,
  branch: HEAD_BRANCH,
  status: "TO_REVIEW"
)
```

Note in the report whether results are PR-specific or branch-level.
Store as `SONAR_HOTSPOTS`. For each hotspot record: component, line, rule key,
message, securityCategory, vulnerabilityProbability (HIGH/MEDIUM/LOW).

### 4g. Pre-flight SonarCloud configuration check

Before fetching findings, inspect any `sonar-project.properties` or
`sonar-project.properties.template` for placeholder values:

```bash
gh api repos/{OWNER}/{REPO}/contents/sonar-project.properties \
  --jq '.content' | base64 -d 2>/dev/null
```

If any of these patterns appear, emit a **Critical** finding in the report:

- `sonar.organization=your-org` or `sonar.organization=your_org`
- `sonar.projectKey=your-project` or similar placeholder
- `sonar.host.url` pointing at `localhost`

Message: "SonarCloud configuration contains placeholder values; CI quality
gate will fail. Update `sonar-project.properties` with the real organization
and project key before merge."

This prevents the silent "SonarCloud: not configured" skip that delays
findings until a later push.

### 4e. Store SonarQube findings and hotspots for the fix step

SonarQube issues are deterministic -- they have clear, prescribed fixes and
do not require human judgment. Do not include them in the review report.
Store as `SONAR_FINDINGS` and pass to the fix workflow.

For each issue record: file, line, rule key, message, severity. Run a
`show_rule` lookup for any unfamiliar rule key so the fix step has
remediation guidance ready.

Security hotspots require human judgment to decide exploitability, but still
warrant a code change in most cases (pinning an unpinned action, removing a
vulnerable regex, etc.). Store `SONAR_HOTSPOTS` alongside `SONAR_FINDINGS`
and pass both to the fix workflow.

The review report shows only a one-line summary:
"SonarQube: {N} issues and {M} hotspots queued for auto-fix."
Omit the hotspot clause if M = 0. The fix step resolves both without
further review unless a hotspot genuinely requires a human decision.

---

## Step 5: Run Parallel Review Agents

Launch all applicable agents simultaneously using the Agent tool. Each agent
receives its context inline (no local git state; all from `gh` output).

### Large-PR handling

If the total diff exceeds 500 lines, choose a strategy before spawning agents:

**Strategy A: Per-file chunking** (preferred when PR has many small files):
Split `CHANGED_FILES` into batches of 10 files each. Run all agents once per batch.
Merge findings across batches before Step 6. Label each finding with the batch file
that produced it.

**Strategy B: Hard stop** (preferred when PR has one or two very large files):
Emit a Critical finding immediately:

```text
[Critical] Review: Diff exceeds 500 lines ({actual_count} lines). pr-review cannot
guarantee complete coverage of diffs this large. Lines beyond 500 were not analyzed.
```

Then proceed with the first 500 lines and label the report:
`WARNING: Review covers lines 1-500 only. Lines 501 onward were not analyzed.`

Never silently truncate. Always tell the user what was and was not reviewed.

### File context fetch (run before spawning agents)

For each file in `CHANGED_FILES` that has more than 10 lines changed, fetch its full
content at the PR head SHA:

```bash
gh api repos/{OWNER}/{REPO}/contents/{FILE_PATH}?ref={HEAD_SHA} \
  --jq '.content' | base64 -d > /tmp/ctx_{FILE_SLUG}.txt
```

Store as `CONTEXT_FILES` map: `{file_path: full_file_content}`.

Agents B, F, G, and K receive `CONTEXT_FILES` in addition to the diff. Their
instructions include: "When evaluating a changed function, read the surrounding 200
lines from CONTEXT_FILES to understand callers and callees before issuing findings."

**Critical instruction for all agents:**
> Do NOT dismiss any finding as trivial, a nitpick, or "would be caught by
> a linter." Report everything you observe. Categorize it; do not omit it.
> The user reviews all tiers. Confidence scoring happens after you return.

### Agent A: CLAUDE.md Compliance (Sonnet)

```text
You are reviewing a GitHub pull request for project standards compliance.

PR: {PR_TITLE} ({OWNER}/{REPO}#{PR_NUMBER})
Base branch: {BASE_BRANCH}

CLAUDE.md content:
{contents of all CLAUDE.md files in the repo, fetched via gh}

PR diff:
{PR_DIFF}

Review the diff against CLAUDE.md. Find every violation, large and small.
Do NOT filter anything as trivial. Report each issue with: file, approximate
line, description, which CLAUDE.md rule it violates.

Also check: if the commit history contains any `feat:`, `fix:`, `perf:`, or `!`
(breaking) commit (run `gh api repos/{OWNER}/{REPO}/commits?sha={HEAD_SHA}&per_page=20`
and scan the commit messages), verify that `CHANGELOG.md` appears in CHANGED_FILES.
If it is absent, report:
`[Important] CLAUDE.md: CHANGELOG.md not updated for feat/fix/perf/breaking change`
```

### Agent B: Bug Scan (Sonnet)

```text
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

### Agent C: Git History Context (Sonnet)

```text
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

### Agent D: Prior PR Comments (Sonnet)

```text
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

### Agent E: Code Comment Accuracy (Sonnet)

*Run only if comment-analyzer is activated in Step 3.*

```text
You are reviewing whether code comments and docstrings in a PR are accurate.

PR diff:
{PR_DIFF}

For every docstring, inline comment, or TODO added or modified in the diff:
1. Check whether it accurately describes the surrounding code
2. Identify comment rot (comment says X but code does Y)
3. Flag missing docstrings on new public functions/classes
4. Flag outdated parameter descriptions

Report ALL issues; do not skip anything because it seems minor. Include:
file, line, the comment text, the discrepancy.
```

### Agent F: Silent Failure / Error Handling (Sonnet)

*Run only if silent-failure-hunter is activated in Step 3.*

```text
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
- Exception handlers that do not cover the full call surface inside the
  try block: parsing calls (resp.json(), datetime.fromisoformat(), etc.)
  nested inside network try blocks that only catch network exception types
  (HTTPError, RequestException): json.JSONDecodeError and ValueError are
  NOT subclasses of those types, so a 200 response with a non-JSON body
  propagates uncaught and aborts the script rather than being treated as a
  per-item warning. For each try block, enumerate every call inside it and
  verify the except clauses cover all raised types, not just the primary
  network call.

Do NOT dismiss anything as minor. Report every case: file, line, pattern,
what failure scenario it silences, recommended fix.
```

### Agent G: Test Coverage Quality (Sonnet)

*Run only if pr-test-analyzer is activated in Step 3.*

```text
You are reviewing test coverage quality in a pull request.

PR diff:
{PR_DIFF}

For every new or modified function/method/class in the diff:
1. Check whether the PR includes tests for it
2. Identify missing edge cases, boundary conditions, negative tests
3. Flag tests that are too implementation-coupled (test internals, not behavior)
4. Flag missing tests for error conditions introduced in the diff

Rate each gap 1–10 (10 = critical, will cause production failures without it).
Report ALL gaps; do not skip low-rated ones. Include: what's untested,
what failure it could allow, the criticality rating.
```

### Agent H: Type Design (Sonnet)

*Run only if type-design-analyzer is activated in Step 3.*

```text
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

Rate each dimension 1–10. Report ALL issues; do not skip low scores.
Include: type name, dimension, rating, specific concern.
```

### Agent I: Security Pass (Sonnet)

```text
You are performing a dedicated security review of a pull request diff.

PR diff:
{PR_DIFF}

Evaluate every check below explicitly. Do NOT skip a check just because it
seems unlikely; state "No issues found" for each clean check.

Checks:
- SQL injection: string concatenation into queries, f-string queries, execute()
  with user-supplied input
- Command injection: subprocess calls, shell execution APIs (eval, exec) with
  user-supplied input
- Path traversal: file open operations without resolve() combined with a
  base-path check
- SSRF: outbound HTTP calls where the URL contains user-supplied hostname or path
- Authentication bypass: routes missing auth decorator, permission checks skipped
  by early return
- Secrets in code: API keys, tokens, passwords hardcoded or logged
- Insecure deserialization: unsafe deserialization of untrusted binary or text data,
  yaml.load without Loader=SafeLoader

For each check output one of:
  [Critical] Security/{check}: {finding}
  [Info] Security/{check}: No issues found

Confidence: Critical findings score 90 unless attacker-controlled input is
demonstrably impossible, in which case 70.
```

### Agent J: PR Description vs Diff Validation (Sonnet)

```text
You are validating that the PR description accurately reflects the diff.

PR title: {PR_TITLE}
PR body: {PR_BODY}
Changed files: {CHANGED_FILES}
PR diff: {PR_DIFF}

Checks:
1. For each component or change claimed in the "## Changes" section of PR_BODY:
   verify a corresponding file or function change exists in the diff.
   Report [Important] PRDesc: {claim}: not found in diff.

2. For each file in CHANGED_FILES: verify it is mentioned (directly or by
   implication) in PR_BODY.
   Report [Suggested] PRDesc: {file} changed but not mentioned in description.

3. Check whether PR_BODY contains a "## Why" or equivalent motivation section.
   Report [Suggested] PRDesc: Missing motivation section (## Why or equivalent).

4. If the PR title or labels indicate a bug fix, check whether PR_BODY references
   an issue number (Fixes #N, Closes #N, or Relates to #N).
   Report [Suggested] PRDesc: Bug fix PR does not reference an issue number.
```

### Agent K: Performance Review (Sonnet)

```text
You are reviewing a pull request for performance anti-patterns.

PR diff:
{PR_DIFF}

Also available: CONTEXT_FILES (full file content for files with >10 lines changed).
When evaluating a changed function, read the surrounding context from CONTEXT_FILES
to understand callers and data flow before issuing findings.

Checks:
- N+1 queries: ORM calls inside loops (for item in queryset: item.related.all())
- Blocking I/O in async context: synchronous HTTP calls or file reads inside
  async def functions
- Unbounded loops: while True or iteration with a database/network call and no
  break or limit condition
- Quadratic complexity: nested loops where both iterables grow with user input
- Missing pagination: list endpoints returning unbounded result sets
- Large in-memory loads: loading entire files or tables into memory without
  streaming

For each issue found:
  [Important] Perf/{category}: {finding}, estimated impact: {brief statement}

If no issues found:
  [Info] Perf: No performance issues detected in diff
```

### Agent L: Architectural Review (PAL consensus)

*Run when `CHANGED_FILES` includes new modules, new public API surfaces,
new base classes, or structural changes to existing modules (heuristic:
any file where more than 30% of lines changed or a new top-level class
or function was added).*

Call `mcp__pal__consensus` with `PAL_CONSENSUS_MODELS` and the prompt below.
Each model is assigned stance `neutral` so all participate as independent
reviewers rather than debating a position.

```text
Prompt: You are reviewing a pull request for architectural quality.

PR title: {PR_TITLE}
PR diff:
{PR_DIFF}

Review dimensions:
1. Coupling: does the change introduce tight coupling between modules that
   were previously independent? Are dependencies flowing in the right direction?
2. Abstraction: are new abstractions at the right level? Do they generalize
   beyond this immediate use case without being over-engineered?
3. Extensibility: are extension points preserved or introduced where future
   growth is likely?
4. Consistency: does the change follow the patterns established in adjacent
   modules or diverge without clear justification?
5. Boundary clarity: are the responsibilities of each new class, function,
   or module clearly delineated?

For each concern found, report:
  [Important] Arch/{dimension}: {finding}

If no concerns found, report:
  [Info] Arch: No architectural concerns detected in diff
```

Collect the consensus synthesis as Agent L findings. Route through Step 6
confidence scoring and Step 7 deduplication with `agent source: L`.

---

## Step 6: Confidence Scoring (parallel Haiku agents)

For each finding returned by Agents A–H, launch a parallel Haiku agent with:

```text
Score this code review finding on a scale of 0–100.

Finding: {finding description}
File: {file}
Agent source: {A|B|C|D|E|F|G|H|I|J|K|L}
PR diff context: {10 lines of diff around the finding}

Scoring rubric:
- 0:  False positive that doesn't survive basic scrutiny, or pre-existing issue
      unrelated to this PR's changes.
- 25: Might be real, hard to confirm. Speculative.
- 50: Verifiably real, but low impact; affects edge cases rarely hit.
- 75: Real and impactful; will affect users or functionality in normal use.
      Or: directly called out in CLAUDE.md.
- 100: Certain, frequent impact. Direct evidence in the diff confirms it.

Additional constraint: If the agent source is C (Git History) or D (Prior PR
Comments) AND the finding does not point to a specific, fixable line in the
diff (it describes historical context, file churn, or past review patterns
rather than an issue in the changed code): cap the score at 20 regardless of
the rubric above.

Return ONLY a JSON object:
{"score": <number>, "rationale": "<one sentence>"}
```

**Tier assignment from score:**

| Score | Tier |
| ----- | ---- |
| 75–100 | Critical |
| 50–74 | Important |
| 25–49 | Suggested |
| 0–24 | Informational |

**Do not discard any finding.** All four tiers appear in the output.
The old practice of dropping findings below 80 does NOT apply here.

---

## Step 7: Deduplicate (Haiku agent)

Pass all scored findings from all agents to a single Haiku agent:

```text
You are deduplicating a list of code review findings from multiple agents.

Findings:
{all findings as JSON array with agent source, file, line, description, score}

Instructions:
- If two findings describe the same issue at the same location, keep the
  one with the higher score. Add both agent names as sources.
- If two findings describe related but distinct aspects of the same issue,
  keep both but mark them as related.
- Do not merge findings at different files or different lines.
- Preserve all findings; deduplication only removes exact duplicates.

Return a JSON array of deduplicated findings with all original fields preserved.
```

---

## Step 7b: PAL Validation of Critical Findings

After deduplication, use PAL tools to validate the Critical tier before
assembling the final report. This catches false positives before they reach
the user.

**Before calling either tiered_consensus below, extract a 15-line diff context
window for each Critical finding.** For each finding, locate its `file` and
`line` in `PR_DIFF` and capture lines `[line - 7 .. line + 7]` (clamped to
file boundaries). Attach this context to the finding JSON passed to PAL so
models can assess the actual code, not just the description.

### 7b-1. Cross-model false-positive filter (all Critical findings)

If there are any Critical findings (score 75–100), call:

```text
mcp__pal__tiered_consensus(
  level:          PAL_TIERED_LEVEL,
  domain:         "code_review",
  thinking_mode:  PAL_TIERED_THINKING,
  prompt: "You are reviewing Critical-tier findings from a PR code review.
           For each finding, decide: is this a genuine defect that must be
           fixed before merge, or is it a false positive? A false positive
           is a finding that does not survive scrutiny when you read the
           actual code context provided.

           Findings (JSON array):
           {Critical findings as JSON with file, line, description, score,
            rationale, and 15 lines of diff context around the finding}

           For each finding return:
           { 'finding_id': N, 'verdict': 'genuine' | 'false_positive',
             'reason': 'one sentence' }

           Demote false positives to Informational tier; do not discard them."
)
```

Apply the verdicts: move any finding marked `false_positive` from Critical to
Informational, appending "(PAL: false positive: {reason})" to its rationale.

### 7b-2. Security finding validation (Critical security findings only)

If any Critical finding originates from Agent I (Security Pass) or contains
"Security/" in its description, call:

```text
mcp__pal__tiered_consensus(
  level:          2,
  domain:         "security",
  thinking_mode:  PAL_TIERED_THINKING,
  prompt: "You are validating security findings from a PR review.
           For each finding, assess: is the vulnerability real and
           exploitable given the code context, or is it a false positive?

           Findings:
           {Security findings as JSON with file, line, description, score,
            and 20 lines of diff context}

           For each finding return:
           { 'finding_id': N, 'verdict': 'real' | 'false_positive',
             'exploitability': 'high' | 'medium' | 'low' | 'theoretical',
             'reason': 'one sentence' }

           False positives should be downgraded to Important (not removed)
           so reviewers still see them."
)
```

Apply security verdicts: downgrade `false_positive` security findings from
Critical to Important. Retain `exploitability` in the finding rationale:
"(PAL security: {exploitability}, {reason})".

Note: security validation always runs at level 2 regardless of
`PAL_TIERED_LEVEL` because security decisions warrant more model coverage.

---

## Step 8: Wait for Copilot and CodeRabbit Reviews

Before assembling the final report, poll for async reviewer results so that
pr-fix (if selected) can address everything in a single pass.

**Polling target:** Copilot (`copilot-pull-request-reviewer`) and CodeRabbit
(`coderabbitai`) review submissions on the PR.

```bash
# Poll every 30s for up to 5 minutes (10 attempts)
for i in $(seq 1 10); do
  REVIEWS=$(gh api repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/reviews \
    --jq '[.[] | select(.user.login == "copilot-pull-request-reviewer" or .user.login == "coderabbitai[bot]") | .user.login] | unique')
  COPILOT_DONE=$(echo "$REVIEWS" | grep -c "copilot-pull-request-reviewer" || true)
  CODERABBIT_DONE=$(echo "$REVIEWS" | grep -c "coderabbitai" || true)
  if [ "$COPILOT_DONE" -ge 1 ] && [ "$CODERABBIT_DONE" -ge 1 ]; then
    break
  fi
  sleep 30
done
```

**When reviews arrive during the window:**

1. Fetch Copilot review comments:
   `gh api repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/comments`
   and filter by `user.login == "copilot-pull-request-reviewer"`
2. Fetch CodeRabbit review comments:
   `gh api repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/comments`
   and filter by `user.login == "coderabbitai[bot]"`
3. Convert each comment into a finding with:
   - file, line from the comment's `path` and `line` fields
   - description from the comment body
   - agent source: "Copilot" or "CodeRabbit"
4. Run each through the same confidence scoring as Step 6
5. Merge into the existing `FINDINGS` list and deduplicate (Step 7)

**Timeout behavior:**

- If both arrive: proceed with full findings
- If only one arrives: proceed, note the missing reviewer in the report header
  (e.g., "CodeRabbit: review pending, not included in this pass")
- If neither arrives: proceed without them, note both as pending
- If Copilot was not successfully requested in Step 1: do not wait for it
- If the repo has no CodeRabbit app installed (no prior `coderabbitai` reviews
  in the repo): do not wait for it

The goal is to give pr-fix a complete picture on the first pass, eliminating
the push-then-react-to-new-comments cycle.

---

## Step 9: Assemble and Output Report

Present the following report in the terminal. Do NOT post to GitHub
automatically; the user can decide whether to post.

```markdown
# PR Review: {PR_TITLE}
{OWNER}/{REPO}#{PR_NUMBER} | {BASE_BRANCH} ← {HEAD_BRANCH}
{DRAFT WARNING if isDraft}

## Review Status
- **GitHub Copilot**: {Received N comments / Pending (timed out) / Failed}
- **CodeRabbit**: {Received N comments / Pending (timed out) / Not installed}
- **SonarQube Issues**: {N} queued for auto-fix
  *(PR-specific / branch-level / not configured / placeholder config detected)*
  Severity: Blocker: {N} | Critical: {N} | Major: {N} | Minor: {N} | Info: {N}
- **SonarQube Hotspots**: {M} queued for review *(omit line if M = 0)*
  Probability: HIGH: {N} | MEDIUM: {N} | LOW: {N}
- **CI checks**: {N} failing / all passing / BUILD FAILING (if Critical CI findings exist)
- **Agents run**: {list of agents that fired}
- **Agent findings**: {N} ({critical} Critical, {important} Important,
  {suggested} Suggested, {informational} Informational)

---

## Review Agent Findings ({N})

### Critical (must fix before merge)
- **[{agent}]** `{file}:{line}`: {description}
  *(Score: {score}: {rationale})*

### Important (should fix)
- **[{agent}]** `{file}:{line}`: {description}
  *(Score: {score}: {rationale})*

### Suggested (consider addressing)
- **[{agent}]** `{file}:{line}`: {description}
  *(Score: {score}: {rationale})*

### Informational (noted, low priority)
- **[{agent}]** `{file}:{line}`: {description}
  *(Score: {score}: {rationale})*

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

## Step 10: Next Steps Prompt

After the report is output, present exactly these options. Do not add
explanation; keep the prompt concise.

```text
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

## Step 11: Execute Next Steps

### Option 1 or 3: Post to GitHub

Get the HEAD commit SHA:

```bash
gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" --json headRefOid \
  --jq '.headRefOid'
```

Post the condensed review comment:

```bash
gh pr comment "$PR_NUMBER" --repo "$OWNER/$REPO" --body "$(cat <<'EOF'
### PR Review

{condensed report: Critical and Important findings only, with full
SHA-anchored file links:
https://github.com/{OWNER}/{REPO}/blob/{HEAD_SHA}/{file}#L{start}-L{end}}

{SonarQube summary line if findings exist}

{If COPILOT_STATUS=0: "Copilot review requested; see Reviewers section for results." Else: "Copilot review request failed; request manually via GitHub UI."}

🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

Use the full 40-character SHA in every file link. Never use branch names;
they are mutable.

After posting, if `NEXT_ACTION` is 3, continue to the fix workflow below.
If `NEXT_ACTION` is 1, stop here.

### Option 2 or 3: Run /pr-fix

Load `workflows/pr-fix.md` and execute it. Pass forward:

- `OWNER`, `REPO`, `PR_NUMBER`
- `HEAD_BRANCH` (the branch to check out in the worktree)
- `FINDINGS`: the full deduplicated, scored findings list from Step 7
- `SONAR_FINDINGS`: SonarQube findings from Step 4 (if any)
- `SONAR_HOTSPOTS`: security hotspots from Step 4f (if any)

The pr-fix workflow runs its own gather step for CI check failures,
review comments, and Codecov status (data that pr-review did not collect),
supplementing the FINDINGS and SONAR_FINDINGS already in context.

---

## Error Handling

| Situation | Action |
| --------- | ------ |
| `gh` not authenticated | Stop. Print: "Run `gh auth login` first." |
| PR not found | Stop. Verify the URL and repo access. |
| PR is closed | Stop. Note: "PR #{number} is closed. Provide an open PR URL." |
| PR is draft | Continue with a warning banner in the report header. |
| Copilot reviewer add fails | Log "Copilot: request failed; add manually via GitHub UI." Continue. |
| SonarQube MCP unreachable | Log "SonarQube: MCP server offline; run `/sonarcloud check`." Continue. |
| SonarQube project not found | Log "SonarQube: project not configured for this repo." Continue. |
| Large PR (> 500 lines) | See large-PR handling strategy in Step 5; never silently truncate. |
| Agent returns no findings | Include: "{Agent}: No issues found." in the relevant tier section. |
