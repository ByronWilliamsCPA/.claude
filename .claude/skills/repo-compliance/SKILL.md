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

## Local Repo Inventory

A pre-built catalog of all 44 repos across both orgs lives at:

- `~/.claude/docs/reference/github-repos.json` — structured compliance data (local only, gitignored)
- `~/.claude/docs/reference/github-repos.md` — human-readable index with refresh commands

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

## Coordinator Prompt Template

When dispatching each domain agent, include in the prompt:

```yaml
Mode: <audit|remediation>
Target repo: <absolute path>
Manifest checks for this domain:
<paste the relevant check entries from standards-manifest.yaml>
Override entries (skip these check IDs):
<paste entries from compliance-overrides.md, or "none">
```

For the `ossf-compliance-auditor` specifically, also include:

```html
Repo slug: <owner/repo GitHub slug>
```

The OSSF agent queries live APIs (Scorecard REST API, Best Practices Badge API, GitHub API) using the repo slug. It will produce FINDING blocks both for OSSF-* manifest checks and for Scorecard checks that score below 4, even when those checks have no manifest entry.
