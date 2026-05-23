---
description: >
  Repo compliance coordinator. Audits any repository against the standards
  manifest, presents findings by severity, applies approved remediations, and
  runs the retrospective. Interactive mode: full audit-approve-remediate-PR
  flow. Scheduled mode: report-only for org-wide sweeps.
  Covers the API domain (API-001..005) for repos where api.servesApi is true;
  API checks are skipped silently for non-API repos.
  Triggers on: /repo-audit, repo audit, compliance check, standards audit.
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Agent", "TodoWrite"]
---

Orchestrates a full compliance audit and optional remediation run against any repository.

## Invocation

```text
/repo-audit                          # interactive mode, current directory
/repo-audit /path/to/repo            # interactive mode, specified path
/repo-audit --scheduled              # report-only mode for cron trigger
```

## Mode Selection

- Default (no flag): interactive mode, see `workflows/interactive-mode.md`
- `--scheduled`: scheduled mode, see `workflows/scheduled-mode.md`

## Workflow

Follow the appropriate workflow file for the selected mode. Both modes share these steps:

1. Load `~/.claude/docs/standards-manifest.yaml`
2. Load target repo's `.claude/compliance-overrides.md` (if present)
3. Dispatch domain agents in parallel (see workflow file for agent list and prompts)
4. Merge findings, filter overrides, sort by severity
5. Run `compliance-retrospective` after all repos are processed

The retrospective also appends a structured entry to
`docs/compliance-reports/master-log.jsonl` and regenerates the
Markdown view. Fleet-wide synthesis runs weekly via the
`compliance-synthesis` agent; trigger an ad-hoc synthesis with
`/compliance-synthesis`.

## Local Repo Inventory

A pre-built catalog of all 44 repos across both orgs lives at:

- `~/.claude/docs/reference/github-repos.json`: structured compliance data (local only, gitignored)
- `~/.claude/docs/reference/github-repos.md`: human-readable index with refresh commands

The JSON contains a `review` object per repo with pre-fetched values for:
`branchProtection`, `codeql`, `scorecard`, `sonarcloud`, `codecov`, `reuse`, `dependabot`,
`ossfBadge`, `workflows`, `foundations`, `preCommit`, `toolchain`.

**When to consult it:** At the start of any compliance audit:

1. Load `_meta.idealEntry` as the compliance target. Every key in `idealEntry` is the
   expected value for a fully-compliant repo. Pass it to domain agents so they can diff
   the actual repo against the ideal rather than evaluating each field in isolation.
2. Look up the target repo slug (`org/name`) in `repos[]`. If found, extract the `review`
   object and pass it to each domain agent as pre-fetched context to skip redundant GitHub
   API calls and focus on local file verification.

In scheduled mode, use the catalog to pre-populate known state before cloning and
dispatching agents.

**Limitations:** The catalog is local-only (gitignored) and must be refreshed manually using
the commands in `github-repos.md`. Treat cached data as a starting hint, not a definitive
answer. Agents should still verify anything time-sensitive (CI runs, live Scorecard scores).
The `_meta.lastUpdated` field shows the refresh date; flag data older than 30 days as
potentially stale.

## Domain Agents

| Domain | Agent | Checks |
|--------|-------|--------|
| foundations | `repo-foundations-auditor` | FOUND-* |
| toolchain | `python-toolchain-auditor` | TOOL-* |
| pre_commit | `pre-commit-auditor` | PC-* |
| ci | `devops-deployment-agent` (CI audit mode) | CI-* |
| claude_docs | `claude-docs-auditor` | CLAUDE-* |
| ossf | `ossf-compliance-auditor` | OSSF-* + live Scorecard/Badge API results |
| general | `general-compliance-auditor` | unclassified |
| mkdocs | `mkdocs-auditor` | MKDOCS-* (skipped when mkdocs.yml absent) |
| api | `openapi-compliance-agent` (via check-repo-compliance.py) | API-001..005 (applies_to: api_repos; skip when api.servesApi is false) |

### CI Domain Agent: Triage Notes

**CI-001: org delegation gap, elevated injection risk when local reusable workflows present**

When CI-001 fires because the repo maintains a local `reusable-*.yml` workflow layer (pattern: 7+ files matching `.github/workflows/reusable-*.yml`), annotate the finding with an elevated CI-028 risk note. Local workflow files introduce additional script injection surface that the shared org library handles centrally in org-delegating repos. Explicitly check all local `reusable-*.yml` files for `${{ github.event.* }}` inputs used directly in `run:` steps (S7630 pattern) as part of CI-001 triage; do not wait for the CI-012/SonarCloud gate to surface them.

Tag the finding: `[BLOCKER/HIGH] CI-001 + elevated CI-028 risk: local reusable workflow layer found; script injection audit required.`

**CI-003c: Scorecard workflow trigger absence (distinct from absent or misconfigured)**

When the Scorecard API returns 0 scores or shows 74+ consecutive failures, check for CI-003c before assuming a configuration error: open `.github/workflows/scorecard.yml` (or equivalent) and verify it contains an `on.schedule.cron` entry. A `workflow_dispatch`-only workflow is syntactically valid and passes file-presence checks (CI-003) but never runs automatically, producing a sustained 0-score result that is indistinguishable from a broken workflow at the API level.

If `on.schedule.cron` is absent: emit `[BLOCKER] CI-003c: Scorecard workflow has no schedule trigger; add a weekly cron (e.g., \`0 1 * * 1\`) to enable automatic scoring.`

Run CI-003c first when Scorecard shows 0 scores; the one-line fix (adding a cron trigger) is far cheaper than diagnosing a configuration error that does not exist.

### Bash file-existence checks: handle 404 responses correctly

When a domain agent uses `gh api repos/<org>/<repo>/contents/<path> --jq '.<field>'`
to test for file presence, the 404 case is a trap: the GitHub API returns
`{"message":"Not Found","status":"404"}` and `--jq '.name'` on that response
returns the literal string `null`, not an empty string. Bash tests like
`[ -n "$result" ]` then evaluate `null` as truthy and report the file as
PRESENT when it is actually absent. Symptom: a foundation file check reports
all required files present even on a freshly initialized repo with only
`README.md`.

Robust patterns:

- Use `--jq '.<field> // "NOT_FOUND"'` and test against the sentinel:
  `if [ "$status" != "NOT_FOUND" ] && [ "$status" != "null" ]; then ...`
- Or check the HTTP status directly with `--silent`:
  `gh api "..." --silent 2>/dev/null && echo PRESENT || echo ABSENT`

Apply to any new bash check in this skill or in domain agent prompts that
calls `gh api ... --jq` and tests for non-empty output.

### API Domain: applies_to Conditional

Before dispatching API-domain checks, read `api.servesApi` from the target
repo's catalog entry. The canonical catalog path is
`${CLAUDE_HOME:-$HOME/.claude}/docs/reference/github-repos.json`; inside this
repo it is also reachable at the relative path `docs/reference/github-repos.json`.
Both refer to the same file (the `~/.claude` location is a symlink installed
by `setup.sh`). If `api.servesApi` is absent or `false`, skip all API-*
checks without raising FINDINGs; log `SKIP (api.servesApi: false)` in the
audit summary. API-* checks run only for repos where `api.servesApi: true`.

API-001 through API-003 are evaluated by `scripts/check-repo-compliance.py` via
the GitHub Contents API. API-004 and API-005 read from the catalog directly
(fields set by the openapi-compliance-agent after a successful run).

## Type and Visibility Evaluation

Before dispatching domain agents, read the target repo's entry in
`docs/reference/github-repos.json`:

1. Look up the entry by matching `org` + `name` fields in the `repos[]` array.
2. Read `repositoryType` from the entry.
3. Load `_meta.typeProfiles[repositoryType]` to get the type profile.
4. Read `isPrivate` from the entry. If absent, default to `false` (treat as public): skip
   loading the visibility profile, set `Scorecard API skip: false`, and leave `exemptChecks`
   and visibility `exemptWorkflows` empty.
5. If `isPrivate` is `true`, load `_meta.visibilityProfiles.private` to get the visibility
   profile. If `_meta.visibilityProfiles.private` is absent or null, treat it as an empty
   profile: no additional exemptions, no `scopedNotes`, no `Scorecard API skip`.
6. Merge visibility exemptions with type exemptions (union of both sets): combine
   `exemptWorkflows` from both profiles, combine `exemptChecks` from the visibility profile
   with the per-repo override entries from `.claude/compliance-overrides.md`. Pass
   `exemptChecks` (from the visibility profile) and override check IDs (from
   `compliance-overrides.md`) as separate coordinator prompt fields; do not collapse them
   so domain agents can log `EXEMPT (private repo)` vs `OVERRIDE` with distinct audit trails.
   #ASSUME both sources use identical check ID formats (e.g., `OSSF-001`); verify if adding
   a new profile type.

Pass the following to each domain agent in the coordinator prompt:

```yaml
Repository type: <repositoryType>
Repository visibility: <public|private>
Exempt workflows (do not raise FINDING for absence): <merged exemptWorkflows from type + visibility profiles>
Exempt hooks (do not raise FINDING for absence): <exemptHooks list from type profile>
Exempt check IDs (log EXEMPT, not FINDING): <exemptChecks from visibility profile, if private>
Scorecard floor: <scorecardFloor from type profile, or 7.0 if not overridden>
Scorecard target: <scorecardTarget from type profile, or 8.5 if not overridden>
Scorecard API skip: <true if private repo, false otherwise>
```

**Exemption rule:** If a workflow filename appears in the merged `exemptWorkflows`, log
`EXEMPT (infrastructure type)` or `EXEMPT (private repo)` for its absence; use the
source that triggered the exemption in the label. Same for `exemptHooks`. For check IDs in
`exemptChecks`, log `EXEMPT (private repo)` instead of FINDING.

**Exemption label tiebreaker:** When a workflow filename appears in both the type profile
and the visibility profile `exemptWorkflows`, label the exemption with the type source
(e.g., `EXEMPT (infrastructure type)`) and omit the visibility label; type takes precedence
for labeling.

**Scorecard evaluation:** Use the type profile's `scorecardFloor` and
`scorecardTarget` when they exist; fall back to `idealEntry.scorecard.floor`
(7.0) and `idealEntry.scorecard.target` (8.5) otherwise. When `Scorecard API skip: true`,
skip the live `api.securityscorecards.dev` lookup entirely; the public API does not
index private repos and will return no data. Do not raise a FINDING for a missing score.

**Private repo scoped notes** (from `visibilityProfiles.private.scopedNotes`): Include
these as informational context in the audit report, not as FINDINGs. They explain
limitations (e.g., GitHub PVR unavailable) rather than compliance gaps.

**Examples:**
- Repo `homelab-infra` has `repositoryType: "infrastructure"` and `isPrivate: true`
  - Type profile exempts `release.yml`, `release-sign.yml`, `sbom.yml`, `coverage.yml`, `python-compatibility.yml`, `reuse.yml`
  - Visibility profile additionally exempts `codeql.yml` (GHAS required) and check IDs `OSSF-001`, `OSSF-006`
  - Absent `release.yml` is logged as `EXEMPT (infrastructure type)`, absent `codeql.yml` as `EXEMPT (private repo)`
  - OSSF-001 finding is suppressed with `EXEMPT (private repo: badge API is public OSS only)`

## Coordinator Prompt Template

When dispatching each domain agent, include in the prompt:

```yaml
Mode: <audit|remediation>
Target repo: <absolute path>
Manifest checks for this domain:
<paste ONLY the check entries whose ID prefix matches this agent's domain,
 not the full manifest. E.g., CI-* only for devops-deployment-agent.>
Override entries (skip these check IDs):
<paste entries from compliance-overrides.md, or "none">
Repository context:
  type: <repositoryType>
  visibility: <public|private>
  exempt_workflows: <merged list from type + visibility profiles>
  exempt_hooks: <list from type profile>
  exempt_check_ids: <list from visibility profile exemptChecks, or empty>
  scorecard_floor: <floor>
  scorecard_target: <target>
  scorecard_api_skip: <true|false>
Cached review data (domain-scoped):
<paste only the cachedReview keys relevant to this agent's domain:
  repo-foundations-auditor: foundations, codeowners, license
  python-toolchain-auditor: toolchain, dependabot
  pre-commit-auditor: preCommit
  devops-deployment-agent: workflows, ci
  claude-docs-auditor: claudeDocs
  ossf-compliance-auditor: scorecard, ossfBadge, codeql
  mkdocs-auditor: mkdocs
  general-compliance-auditor: full cachedReview>
```

For the `ossf-compliance-auditor` specifically, also include:

```html
Repo slug: <owner/repo GitHub slug>
Scorecard API skip: <true if private, false if public>
```

The OSSF agent queries live APIs (Scorecard REST API, Best Practices Badge API, GitHub API) using the repo slug. It will produce FINDING blocks both for OSSF-* manifest checks and for Scorecard checks that score below 4, even when those checks have no manifest entry. When `Scorecard API skip: true`, the agent must skip the Scorecard REST API call and suppress score-based FINDINGs; it should still evaluate local file checks (SECURITY.md content, workflow presence) that do not require the API.
