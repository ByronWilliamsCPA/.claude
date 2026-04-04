---
name: sonarcloud
description: >
  Review, triage, and fix SonarCloud issues using the SonarQube MCP servers.
  Auto-detects project org and key from workspace config files. Supports
  issue search, quality gate checks, rule lookup, setup diagnostics, and
  automated fixing. Includes health checks for configuration consistency.
version: 2.0.0
---

# SonarCloud Skill

Review and resolve SonarCloud issues for the current project.

## Activation

Trigger on: sonar, sonarcloud, sonarqube, sonarlint, quality gate, sonar issues,
code smells, security hotspots, sonar check, sonar fix

## Product Naming Reference

SonarSource rebranded all products in October 2024. Users may use old or new names
interchangeably. Claude MUST treat these as equivalent:

| Old Name | Current Name | What It Is |
|----------|-------------|------------|
| SonarLint | **SonarQube for IDE** | VS Code extension for local real-time analysis |
| SonarCloud | **SonarQube Cloud** | Cloud-hosted SaaS analysis service |
| SonarQube (self-hosted) | **SonarQube Server** | Self-managed server (not used here) |

When a user says "sonarlint issues", "sonarqube issues", "sonarcloud issues", or
"sonar issues" they are all referring to the same thing — treat them identically.

## How the Ecosystem Fits Together

Understanding the data flow prevents confusion about where issues come from:

```
Developer writes code
       |
       v
[SonarQube for IDE — VS Code Extension]
  - Real-time local analysis (5,000+ rules)
  - Shows findings in PROBLEMS tab (as diagnostics) and SONARQUBE tab
  - Connected Mode syncs quality profile FROM SonarCloud
  - Suppresses cloud issues marked "Accepted" or "False Positive"
  - ONE-WAY: IDE does NOT push findings TO SonarCloud
       |
       v
Developer pushes to GitHub
       |
       v
[SonarCloud — Automatic Analysis or CI Scanner]
  - GitHub App auto-analyzes main branch + PRs (no CI config needed)
  - OR: SonarScanner CLI runs in CI and sends results to SonarCloud
  - Computes quality gate pass/fail
  - Decorates PRs with status checks
       |
       v
[SonarCloud Dashboard — sonarcloud.io]
  - Stores all issues with status tracking
  - This is what the MCP server queries
  - Issues here may differ from VS Code findings because:
    a) Cloud analysis may be stale (not run recently)
    b) Cloud sees full repo; IDE only analyzes open files
    c) Cloud has taint analysis (cross-file vulnerability detection)
       |
       v
[Connected Mode — back to IDE]
  - Syncs issue statuses (accepted, false positive) to suppress in IDE
  - Pushes taint vulnerability findings to IDE
  - Quality gate change notifications
```

**Key implications for Claude:**
- MCP tools return SonarCloud data (the server-side view), not IDE-local findings
- If the user references issues from the VS Code SONARQUBE tab, those are the same
  cloud issues (synced via Connected Mode)
- Fixing code locally does NOT update SonarCloud — a new analysis must run first
- If analysis is stale, MCP data reflects the OLD state of the code

## VS Code Integration Points

The SonarQube for IDE extension provides these UI elements in VS Code:

| UI Element | What It Shows |
|-----------|---------------|
| **PROBLEMS tab** | SonarQube issues as inline diagnostics (squiggly lines) |
| **SONARQUBE tab** (bottom panel) | All findings synced from SonarCloud, grouped by file |
| **SONARQUBE SETUP** (sidebar) | Connected Mode status, org/project bindings |
| **Status bar** | SonarQube connection indicator |

When the user says "I see 22 issues in the SonarQube tab" or "the problems tab shows
sonar warnings", these are the same underlying issues from SonarCloud. Claude can
look them up via MCP using the rule ID shown in the issue (e.g., `python:S3776`).

## Arguments

- (none) — Show quality gate status + top issues summary
- `check` — Validate full SonarCloud setup and diagnose configuration problems
- `issues` — List all open issues, grouped by severity
- `issues <severity>` — Filter: BLOCKER, HIGH, MEDIUM, LOW, INFO
- `fix` — Review and fix issues, starting with highest severity
- `fix <file>` — Fix SonarCloud issues in a specific file
- `gate` — Show quality gate status with condition details
- `rule <key>` — Show details for a specific rule (e.g., `python:S3776`)
- `analyze` — Guidance on triggering a fresh SonarCloud analysis

## Workflow

### Step 1: Detect Project Configuration

Resolve the project key and organization by checking these files in order:

1. `.sonarlint/connectedMode.json` — `projectKey` and `sonarCloudOrganization` fields
2. `sonar-project.properties` — `sonar.projectKey` and `sonar.organization` fields
3. `.vscode/settings.json` — `sonarlint.connectedMode.project.projectKey` and `connectionId`

If none found, use `search_my_sonarqube_projects` on both MCP servers to list
available projects and help the user bind this workspace.

**Quick validation** (runs for ALL modes, not just `check`): If multiple config sources
are found, verify the project key and org are consistent across them. If they conflict,
stop and report the mismatch before proceeding — don't silently use the wrong key.
Also verify the MCP server for the detected org is reachable
(`curl -sf http://localhost:{port}/mcp`). If not, report the infrastructure issue
and suggest running `/sonarcloud check` for full diagnostics.

### Step 2: Select MCP Server

Route to the correct MCP server based on the detected organization:

| Organization | MCP Server Name | Port | MCP Tool Prefix |
|-------------|----------------|------|-----------------|
| `byronwilliamscpa` | `sonarqube` | 8090 | `mcp__sonarqube__` |
| `williaby` | `sonarqube-williaby` | 8091 | `mcp__sonarqube-williaby__` |

Both servers are Docker containers running in HTTP transport mode. They are registered
globally in `~/.claude/settings.json` and available to all projects.

### Step 3: Execute Requested Mode

#### Mode: Summary (default, no arguments)

1. Call `get_project_quality_gate_status` with the detected project key
2. Call `search_sonar_issues_in_projects` with `ps: 10` for a quick overview
3. Present a summary:

```markdown
## SonarCloud: {project_name}

**Quality Gate**: PASSED / FAILED ({N} conditions failed)

| Condition | Status | Actual | Threshold |
|-----------|--------|--------|-----------|
| ... | ... | ... | ... |

**Open Issues**: {total}
| Severity | Count |
|----------|-------|
| BLOCKER  | X     |
| HIGH     | X     |
| MEDIUM   | X     |
| LOW      | X     |

**Top Issues**:
- [{severity}] {file}:{line} - {message} ({rule})
- ...
```

#### Mode: Issues (`issues [severity]`)

1. Call `search_sonar_issues_in_projects` with the project key
2. If severity argument provided, pass it in `severities` filter
3. Page through results if total > 100 (use `p` and `ps` parameters)
4. Group by file, then by severity within each file
5. Present as actionable list with file paths and line numbers
6. Include the `cleanCodeAttribute` and `cleanCodeAttributeCategory` for context

#### Mode: Fix (`fix [file]`)

1. Fetch issues (filtered to specific file if provided, otherwise start with BLOCKER/HIGH)
2. For each file with issues:
   a. Read the local file
   b. For each issue, call `show_rule` to understand the rule's expectation and remediation
   c. Apply the fix following the rule guidance
   d. Track which issues were addressed
3. After fixing, run the project's linter (ruff, basedpyright, etc.) to verify no regressions
4. Present a summary of changes made and issues resolved
5. Do NOT mark issues as resolved in SonarCloud — that happens automatically on next analysis
6. Do NOT use `change_sonar_issue_status` unless the user explicitly asks to suppress/accept

**Important fix considerations:**
- SonarCloud issues reference the code state at last analysis, which may be stale.
  Always read the CURRENT local file — the issue may already be fixed or the line
  numbers may have shifted.
- If an issue references a file that no longer exists locally, skip it and note this.
- For cognitive complexity issues (S3776), refactor the function rather than suppressing.
- For security hotspots (githubactions:S7637, etc.), apply the specific remediation
  (e.g., pin GitHub Actions to full SHA hashes).

#### Mode: Gate (`gate`)

1. Call `get_project_quality_gate_status`
2. Call `get_component_measures` with metrics: `ncloc`, `bugs`, `vulnerabilities`,
   `code_smells`, `coverage`, `duplicated_lines_density`, `security_hotspots`,
   `reliability_rating`, `security_rating`, `sqale_rating`
3. Present detailed quality gate breakdown with measures

#### Mode: Rule (`rule <key>`)

1. Call `show_rule` with the provided rule key
2. Present the rule name, description, severity, impacts, and remediation guidance
3. If the rule has `descriptionSections`, show the "how to fix" section

#### Mode: Analyze (`analyze`)

Guide the user on triggering a fresh SonarCloud analysis. Claude cannot trigger
analysis directly — it happens via:

1. **GitHub App automatic analysis** (if configured): Push to main branch or open a PR.
   SonarCloud's GitHub App will pick it up automatically.
2. **CI-based analysis**: If the project has a GitHub Actions workflow with
   `SonarSource/sonarqube-scan-action`, pushing will trigger it.
3. **Local scanner** (manual): The `sonar-scanner` CLI is installed at
   `~/.local/sonar-scanner/bin/sonar-scanner`. Run it with:
   ```bash
   sonar-scanner -Dsonar.token=$SONARQUBE_TOKEN
   ```
   This reads `sonar-project.properties` from the project root.

Check which method the project uses:
- Look for SonarCloud in `.github/workflows/*.yml` (CI-based)
- If no CI integration, it's likely using GitHub App automatic analysis
- Check analysis freshness via `get_component_measures` with `last_analysis_date`

If analysis is stale (>30 days), suggest the user push changes or run the scanner.

#### Mode: Check (`check`)

Run a full diagnostic of the SonarCloud setup for the current workspace. This mode
does NOT use MCP tools initially — it reads local files and tests connectivity first,
then validates against the remote server. Report all findings as a checklist.

**1. Infrastructure checks:**

- [ ] Docker is running (`docker ps` succeeds)
- [ ] `sonarqube-mcp` container is running on port 8090
- [ ] `sonarqube-mcp-williaby` container is running on port 8091
- [ ] MCP servers respond (`curl -sf http://localhost:{port}/mcp` for both)
- [ ] `SONARQUBE_TOKEN` environment variable is set (check `$SONARQUBE_TOKEN`)

If Docker or containers are down, provide restart commands:
```bash
# Start Docker Desktop from Windows (WSL2 environment)
# Then containers auto-restart. If containers were removed:
docker run --init -d --name sonarqube-mcp --restart unless-stopped \
  -v ~/.sonarqube-mcp-storage:/app/storage \
  -e SONARQUBE_TOKEN -e SONARQUBE_ORG=byronwilliamscpa \
  -e SONARQUBE_TRANSPORT=http -e SONARQUBE_HTTP_PORT=8090 \
  -e SONARQUBE_HTTP_HOST=0.0.0.0 -p 8090:8090 mcp/sonarqube

docker run --init -d --name sonarqube-mcp-williaby --restart unless-stopped \
  -v ~/.sonarqube-mcp-storage-williaby:/app/storage \
  -e SONARQUBE_TOKEN -e SONARQUBE_ORG=williaby \
  -e SONARQUBE_TRANSPORT=http -e SONARQUBE_HTTP_PORT=8091 \
  -e SONARQUBE_HTTP_HOST=0.0.0.0 -p 8091:8091 mcp/sonarqube
```

**2. Project configuration checks:**

Read each config source and cross-validate. Flag any of these problems:

- [ ] **Missing config**: No `.sonarlint/connectedMode.json`, no `sonar-project.properties`,
      no VS Code connected mode settings — project has no SonarCloud binding
- [ ] **Project key mismatch**: `sonar-project.properties` `sonar.projectKey` differs from
      `.sonarlint/connectedMode.json` `projectKey` or `.vscode/settings.json` `projectKey`.
      All three MUST agree. Show the values found in each file.
- [ ] **Organization mismatch**: `sonar-project.properties` `sonar.organization` differs from
      `.sonarlint/connectedMode.json` `sonarCloudOrganization` or `.vscode/settings.json`
      `connectionId`
- [ ] **Missing organization**: `sonar-project.properties` exists but has no
      `sonar.organization` field. This field is REQUIRED for SonarCloud (not needed for
      self-hosted SonarQube Server, but we use SonarCloud).
- [ ] **Unknown organization**: Organization is not `byronwilliamscpa` or `williaby` —
      no MCP server is configured for it
- [ ] **connectionId vs org**: `.vscode/settings.json` `connectionId` should match the
      org name used in `.sonarlint/connectedMode.json` `sonarCloudOrganization`

**3. sonar-project.properties validation:**

If the file exists, check for common problems:

- [ ] **sonar.sources path exists**: Verify the path(s) in `sonar.sources` actually exist
      on disk. Glob for the directories. Comma-separated values are multiple paths.
- [ ] **sonar.tests path exists**: If `sonar.tests` is set (not commented out), verify
      the path exists on disk
- [ ] **sonar.python.version**: If set, check it matches the project's actual Python version
      (from `pyproject.toml` `requires-python`, `.python-version`, or `setup.cfg`)
- [ ] **sonar.python.coverage.reportPaths**: If set, check the file exists. If it doesn't
      exist, note as INFO (not ERROR) — it's generated by test runs.
- [ ] **Exclusion sanity**: Check that `sonar.exclusions` doesn't accidentally exclude
      source code directories (e.g., matching `src/` or the entire project root)
- [ ] **sonar.projectKey format**: For SonarCloud, keys follow `{org}_{repo}` pattern.
      Flag if the key doesn't match this pattern, contains spaces, or uses a completely
      different format (like the old `claude-config` mistake).
- [ ] **Commented-out settings**: Flag important settings that are commented out
      (like `#sonar.tests=tests`, `#sonar.python.coverage.reportPaths=coverage.xml`)
      as suggestions to enable

**4. .sonarlint/connectedMode.json validation:**

- [ ] **File exists**: If missing, the VS Code extension won't use Connected Mode
- [ ] **Valid JSON**: File parses without errors
- [ ] **Required fields**: Has `projectKey` and either `sonarCloudOrganization`
- [ ] **Region field**: Has `region` field (should be `EU` for our setup)
- [ ] **Git tracking**: Check if `.sonarlint/` is in `.gitignore`. The `connectedMode.json`
      SHOULD be committed for team sharing (it contains no secrets). Warn if gitignored.
      Note: other files in `.sonarlint/` (like caches) can be gitignored.

**5. VS Code settings validation:**

- [ ] `.vscode/settings.json` exists and contains `sonarlint.connectedMode.project`
- [ ] `connectionId` matches an org that has a configured MCP server
- [ ] `projectKey` matches the other config files

**6. Remote validation (uses MCP):**

After local checks pass, validate against the actual SonarCloud server:

- [ ] **Project exists**: Call `search_my_sonarqube_projects` on the appropriate MCP server
      and verify the detected project key is in the results
- [ ] **Quality gate accessible**: Call `get_project_quality_gate_status` — if it returns
      an error, the project key may be wrong or the token lacks access
- [ ] **Analysis freshness**: Call `get_component_measures` for the project. Flag if
      analysis is older than 30 days (WARNING) or older than 90 days (ERROR).

**7. CI integration check:**

- [ ] Look for SonarCloud/SonarQube references in `.github/workflows/*.yml`
- [ ] If no CI integration found, note that the project relies on GitHub App automatic
      analysis (which is fine, but means analysis only runs on push/PR)
- [ ] If `scripts/check_quality_gate.py` exists, verify its `--project-key` default
      matches the detected project key

**8. Presentation:**

Present results as a diagnostic report:

```markdown
## SonarCloud Setup Check: {project_name}

### Infrastructure
- [x] Docker running
- [x] sonarqube-mcp container (port 8090) — UP
- [x] sonarqube-mcp-williaby container (port 8091) — UP
- [x] SONARQUBE_TOKEN set

### Configuration
- [x] Project key: `williaby_monte_carlo` (consistent across 3 files)
- [x] Organization: `williaby` (consistent)
- [ ] **ERROR**: `sonar.tests=tests/` but `tests/` directory not found
- [ ] **WARNING**: `sonar.organization` missing from sonar-project.properties

### Remote Validation
- [x] Project found in SonarCloud
- [x] Quality gate accessible (status: ERROR)
- [ ] **WARNING**: Last analysis was 92 days ago — push changes to trigger fresh analysis

### Summary: 1 error, 2 warnings

**Auto-fixable issues:**
- Add `sonar.organization=williaby` to sonar-project.properties
- Remove `sonar.tests=tests/` (directory doesn't exist)

Apply fixes? (y/n)
```

If errors are found, offer to fix them automatically where possible:
- Correcting project key mismatches (align to the SonarCloud-verified key)
- Adding missing `sonar.organization` field
- Removing references to non-existent paths
- Uncommenting useful settings like `sonar.tests` if the path exists

## Available MCP Tools Reference

Both MCP servers expose these tools (use the appropriate prefix):

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `search_sonar_issues_in_projects` | Search issues | `projects[]`, `severities[]`, `ps`, `p`, `pullRequestId` |
| `get_project_quality_gate_status` | Quality gate status | `projectKey`, `branch`, `pullRequest` |
| `get_component_measures` | Project metrics | `projectKey`, `metricKeys[]`, `branch` |
| `show_rule` | Rule details | `key` (e.g., `python:S3776`) |
| `search_my_sonarqube_projects` | List projects | `page` |
| `change_sonar_issue_status` | Accept/FP/reopen | `key`, `status[]` |
| `list_quality_gates` | List quality gates | (none) |
| `get_raw_source` | Source code from SonarCloud | `key` (file key), `branch` |
| `get_scm_info` | Git blame from SonarCloud | `key`, `from`, `to` |
| `list_rule_repositories` | Rule repos | `language`, `q` |
| `search_metrics` | Available metrics | `ps`, `p` |
| `create_webhook` | Create webhook | `name`, `url`, `projectKey` |
| `list_webhooks` | List webhooks | `projectKey` |

## Important Notes

- **Docker required**: MCP servers run as Docker containers. If Docker Desktop isn't
  running, all MCP tools will fail. Run `/sonarcloud check` to diagnose.
- **HTTP transport**: Servers use HTTP mode (not stdio) on ports 8090/8091 due to
  Docker stdio buffering issues with Java-based MCP servers.
- **Analyzer cache**: Plugins are cached in `~/.sonarqube-mcp-storage/` and
  `~/.sonarqube-mcp-storage-williaby/`. First start after clearing cache takes ~60s.
- **Token location**: `SONARQUBE_TOKEN` is exported in `~/.bashrc` and referenced
  by `~/.claude/settings.json`. Same token works for both orgs.
- **Read-only by default**: Only use `change_sonar_issue_status` when the user
  explicitly asks to accept or mark an issue as false positive.
- **Analysis lag**: Fixing code locally does NOT update SonarCloud. The next push
  or PR triggers re-analysis. If the user asks "why is the issue still showing",
  explain this lag.
- **sonar-scanner CLI**: Available at `~/.local/sonar-scanner/bin/sonar-scanner`
  for manual local scans. Reads `sonar-project.properties` from project root.
- **check_quality_gate.py**: Some projects have `scripts/check_quality_gate.py`
  that queries the SonarCloud API directly with LLM governance tag mapping.

## Known Project Configurations

| Org | Project | Key | Region |
|-----|---------|-----|--------|
| byronwilliamscpa | .claude | `ByronWilliamsCPA_.claude` | EU |
| williaby | monte_carlo | `williaby_monte_carlo` | EU |
