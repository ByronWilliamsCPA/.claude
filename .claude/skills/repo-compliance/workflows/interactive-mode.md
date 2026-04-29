# Interactive Mode Workflow

Full audit-approve-remediate-PR flow for a single target repo.

## Steps

### 1. Setup

```bash
# Resolve target repo path
TARGET_REPO="${1:-$(pwd)}"
cd "$TARGET_REPO"
git status  # confirm it is a git repo
```

Read `~/.claude/docs/standards-manifest.yaml`.
Read `$TARGET_REPO/.claude/compliance-overrides.md` if it exists; extract the Check ID column.

**Load pre-fetched catalog data (if available):**
Read `~/.claude/docs/reference/github-repos.json` if it exists. Derive the repo slug from the target repo's `git remote get-url origin` output (format: `org/repo-name`). Find the matching entry in `repos[]` by `org` + `name`. If found, extract the `review` object. Attach it to each domain agent's prompt under the key `cachedReview` so the agent can skip redundant GitHub API calls. Include the catalog `_meta.lastUpdated` date; if it is older than 30 days, note that cached data may be stale.

### 2. Parallel Audit Dispatch

Use TodoWrite to track agent dispatch. Dispatch all domain agents in parallel using the Agent tool. Pass each agent the coordinator prompt template from SKILL.md populated with:
- Mode: audit
- Target repo: resolved absolute path
- Manifest checks: the subset for that domain
- Override entries: IDs from compliance-overrides.md

Agents to dispatch simultaneously:
- `repo-foundations-auditor` (FOUND-* checks)
- `python-toolchain-auditor` (TOOL-* checks)
- `pre-commit-auditor` (PC-* checks)
- `devops-deployment-agent` in CI audit mode (CI-* checks)
- `claude-docs-auditor` (CLAUDE-* checks)
- `ossf-compliance-auditor` (OSSF-* and SCORECARD:* checks)
- `general-compliance-auditor` (all checks as negative filter, freeform review)
- `mkdocs-auditor` in audit mode (MKDOCS-* checks; skipped automatically when no mkdocs.yml is present in the project root)

### 3. Merge and Present Findings

Collect all FINDING blocks. Filter out any finding whose ID is in the override list. Sort by severity: Critical first, then Important, then Suggested. Present unclassified candidates in a separate section.

Present findings in this format:

```html
COMPLIANCE AUDIT: <repo-name>
Standards version: <manifest last_updated>
Overrides applied: N

CRITICAL (N findings)
  [FOUND-001] SECURITY.md absent from project root
  [CI-005] 6 action refs use mutable tags instead of SHA pins

IMPORTANT (N findings)
  [FOUND-005] .worktrees/ absent from .gitignore
  ...

SUGGESTED (N findings)
  ...

UNCLASSIFIED CANDIDATES (N items, for retrospective review)
  [candidate] .editorconfig absent; proposed domain: foundations, severity: suggested
  ...
```

### 4. Approval Loop

Ask: "Which findings would you like to remediate? Options:
  A) All critical and important
  B) All critical, important, and suggested
  C) Select specific check IDs (comma-separated)
  D) Skip remediation (report only)"

Wait for user response. Parse the selection into an approved findings list.

### 5. Remediation Dispatch

For each approved finding, route to the owning domain agent in remediation mode. Use the same coordinator prompt template with Mode: remediation and only the approved findings list.

Dispatch agents by domain in dependency order:

1. `repo-foundations-auditor` (foundations: no dependencies)
2. `python-toolchain-auditor` (toolchain: no dependencies)
3. `pre-commit-auditor` (pre_commit: depends on toolchain being correct)
4. `devops-deployment-agent` CI audit mode (ci: no dependencies)
5. `claude-docs-auditor` (claude_docs: no dependencies)
6. `ossf-compliance-auditor` (ossf: no dependencies)
7. `mkdocs-auditor` in remediate mode (mkdocs: no dependencies; skipped automatically when no mkdocs.yml is present)

Collect ACTION lines from each agent and present a summary of all changes made.

### 6. Open PR

```bash
cd "$TARGET_REPO"
git add -A
git commit -m "chore(compliance): apply standards alignment from repo-compliance audit

Remediations applied:
<list check IDs that were remediated>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push -u origin HEAD

gh pr create \
  --title "chore(compliance): standards alignment $(date +%Y-%m-%d)" \
  --body "$(cat <<'EOF'
## Compliance Remediations

Applied by the repo-compliance system against standards manifest v<version>.

### Changes Made
<list of ACTION lines>

### Checks Resolved
<list of check IDs>

### Remaining (not approved for this run)
<list of skipped findings>
EOF
)"
```

### 7. Retrospective

Dispatch `compliance-retrospective` with: session date, target repo path, all domain findings, all unclassified candidates.

After it writes the lessons-learned doc, print:
"Retrospective written to docs/compliance-reports/lessons-learned/<date>.md; review before the next scheduled run."
