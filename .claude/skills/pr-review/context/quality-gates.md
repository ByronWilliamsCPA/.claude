# SonarQube and Qlty quality-gate detail

This covers the detailed procedure for Step 4 (Fetch SonarQube Findings) of
`workflows/pr-review.md`: organization and project-key detection, PR-specific
issue and hotspot fetches with branch-level fallbacks, the SonarCloud
pre-flight placeholder-config check, storage of findings for the fix
workflow, and the Qlty commit-status detection for the other configured
quality gate. The spine keeps the `## Step 4` heading with a short
orchestration stub; the full procedure lives here.

For the shared "unreachable MCP server is not an empty result set" idiom
this content depends on, see
[context/github-api-idioms.md](../context/github-api-idioms.md); this file
keeps its own SonarQube-specific REST fallback text and only points at the
shared file where the general idiom applies.

---

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

**REST fallback when the MCP server is not loaded.** The sonarqube MCP server is not
connected in every session. When the MCP prefix is unavailable, query the SonarCloud Web
API directly with `SONARQUBE_TOKEN` (a local shell env var) rather than skipping Sonar
entirely:

```bash
curl -s -u "${SONARQUBE_TOKEN}:" \
  "https://sonarcloud.io/api/issues/search?projects={KEY}&organization={ORG}&pullRequest={N}"
curl -s -u "${SONARQUBE_TOKEN}:" \
  "https://sonarcloud.io/api/hotspots/search?projectKey={KEY}&pullRequest={N}"
```

Both endpoints require authentication: an anonymous request returns "Project doesn't
exist" even for a valid key, so the `-u "${SONARQUBE_TOKEN}:"` form is mandatory and the
curl path covers BOTH issues and hotspots. Only if both MCP and REST fail should the
workflow skip Sonar.

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

### 4h. Qlty findings (other configured quality gate)

Account for every configured quality gate that produces findings, not just the ones with
convenient APIs. Qlty posts a blocking-issue count as a GitHub commit STATUS (not a
check_run), so the check-runs/annotations API returns nothing for it. Detect it:

```bash
gh api "repos/$OWNER/$REPO/commits/$HEAD_SHA/statuses" \
  --jq '.[] | select(.context | test("qlty"; "i")) | {state, description, target_url}'
```

If a `qlty check` status is present, extract the issue count and `target_url` and note
them in the report header. If the `qlty` CLI is available locally, enumerate findings with
`qlty check --upstream origin/{BASE_BRANCH} --format json` against the PR head. Otherwise
state explicitly in the report that qlty's N issues were counted but NOT enumerated (the
qlty.sh issues page is auth-walled, so WebFetch returns a login page), so the user knows
there is an un-itemized queue rather than assuming full coverage. Pass the count to the fix
workflow. Never let an un-enumerable queue silently imply full coverage.
