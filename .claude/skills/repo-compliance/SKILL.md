---
description: >
  Repo compliance coordinator. Audits any repository against the standards
  manifest, presents findings by severity, applies approved remediations, and
  runs the retrospective. Interactive mode: full audit-approve-remediate-PR
  flow. Scheduled mode: report-only for org-wide sweeps.
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

## Type-Conditional Evaluation

Before dispatching domain agents, read the target repo's entry in
`docs/reference/github-repos.json`:

1. Look up the entry by matching `org` + `name` fields in the `repos[]` array.
2. Read `repositoryType` from the entry.
3. Load `_meta.typeProfiles[repositoryType]` to get the type profile.

Pass the following to each domain agent in the coordinator prompt:

```yaml
Repository type: <repositoryType>
Exempt workflows (do not raise FINDING for absence): <exemptWorkflows list>
Exempt hooks (do not raise FINDING for absence): <exemptHooks list>
Scorecard floor: <scorecardFloor from type profile, or 7.0 if not overridden>
Scorecard target: <scorecardTarget from type profile, or 8.5 if not overridden>
```

**Exemption rule:** If a workflow filename appears in `exemptWorkflows`, log
`EXEMPT` instead of `FINDING` for its absence. Same for `exemptHooks`.

**Scorecard evaluation:** Use the type profile's `scorecardFloor` and
`scorecardTarget` when they exist; fall back to `idealEntry.scorecard.floor`
(7.0) and `idealEntry.scorecard.target` (8.5) otherwise.

**Example:**
- Repo `homelab-infra` has `repositoryType: "infrastructure"`
- Type profile exempts `release.yml`, `coverage.yml`, `python-compatibility.yml`
- Absent `release.yml` is logged as `EXEMPT (infrastructure type)`, not a FINDING

## Coordinator Prompt Template

When dispatching each domain agent, include in the prompt:

```yaml
Mode: <audit|remediation>
Target repo: <absolute path>
Manifest checks for this domain:
<paste the relevant check entries from standards-manifest.yaml>
Override entries (skip these check IDs):
<paste entries from compliance-overrides.md, or "none">
Repository context:
  type: <repositoryType>
  exempt_workflows: <list from typeProfiles>
  exempt_hooks: <list from typeProfiles>
  scorecard_floor: <floor>
  scorecard_target: <target>
```

For the `ossf-compliance-auditor` specifically, also include:

```html
Repo slug: <owner/repo GitHub slug>
```

The OSSF agent queries live APIs (Scorecard REST API, Best Practices Badge API, GitHub API) using the repo slug. It will produce FINDING blocks both for OSSF-* manifest checks and for Scorecard checks that score below 4, even when those checks have no manifest entry.
