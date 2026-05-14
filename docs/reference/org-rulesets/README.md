---
schema_type: common
title: "Org-level and user-level ruleset bodies"
status: published
owner: core-maintainer
purpose: "JSON bodies for GitHub org/user rulesets, applied via setup_org_rulesets.py."
tags:
  - automation
  - security
---

JSON files in this directory define GitHub rulesets applied at the organization (ByronWilliamsCPA)
or user-account (williaby) level. Apply via:

```bash
uv run python scripts/setup_org_rulesets.py \
  --org <org> \
  --body docs/reference/org-rulesets/<file>.json \
  --enforcement active
```

## Ruleset Architecture

Each org has a two-tier ruleset stack that applies to every non-exempt default branch:

| Tier | File | Applies to | Adds |
| ---- | ---- | ---------- | ---- |
| Universal baseline | `*-universal.json` | All repos | Lifecycle rules, PR policy, status checks |
| Python CI gate | `*-python.json` | Python repos only | CI Gate required check |
| Tag protection | `*-tag-protection.json` | All repos with releases | SemVer tag creation/deletion controls |

A repo's effective protection is the union of every ruleset targeting its default branch.
Per-repo rulesets in `../repo-rulesets/` layer on top of these org-level rules.

## File Inventory

### ByronWilliamsCPA

**`ByronWilliamsCPA-universal.json`** -- `ByronWilliamsCPA-default-branch-baseline`

Applied to all repositories. Enforces:
- Force push and branch deletion prohibition
- Required linear history (squash or rebase merges only; no merge commits)
- Required commit signatures (GPG/SSH)
- Pull request policy: 0 required reviewers, CODEOWNERS review required, stale review
  dismissal on push, squash/rebase merge methods only
- Copilot code review on PR open/ready events
- Required status checks: Security Gate Validation, Dependency & Standards Validation,
  Check REUSE Compliance (all pinned to integration_id 15368)
- File path restriction: `.github/workflows/` protected from modification by non-bypass actors

**`ByronWilliamsCPA-python.json`** -- `ByronWilliamsCPA-python-tier-ci-gate`

Applied to Python repositories only (via generated repository pattern). Adds:
- Required status check: CI Gate (pinned to integration_id 15368)

**`ByronWilliamsCPA-tag-protection.json`** -- `ByronWilliamsCPA-semver-tag-protection`

Applied to all repositories, targeting `refs/tags/v*` refs. Enforces:
- Tag creation restricted to bypass actors
- Tag deletion restricted to bypass actors
- No tag movement (non_fast_forward)
- Required signatures on tagged commits

### williaby

**`williaby-universal.json`** -- `williaby-default-branch-baseline`

Identical to ByronWilliamsCPA-universal except excludes `homelab-agent-configs`.
Applied as a user-level ruleset (williaby is a personal account, not an org).

**`williaby-python.json`** -- `williaby-python-tier-ci-gate`

Identical to ByronWilliamsCPA-python. Adds CI Gate required check.

**`williaby-tag-protection.json`** -- `williaby-semver-tag-protection`

Identical to ByronWilliamsCPA-tag-protection except excludes `homelab-agent-configs`.

## Key Design Decisions

**`integration_id: 15368`** on all required status checks: pins each check to the GitHub
Actions app. Without this, any actor with write access can post a passing check with the
same name and satisfy the requirement. 15368 is the stable GitHub Actions app ID; verify
with `gh api /apps/github-actions --jq .id`.

**`strict_required_status_checks_policy: true`**: requires the PR branch to be current
with the base branch before checks count. This prevents a class of race conditions
(two passing PRs that touch overlapping code) at the cost of requiring rebase before merge.

**`file_path_restriction` on `.github/workflows/`**: prevents workflow definition edits
by contributors without bypass access. This closes the most direct supply chain attack
surface (editing the CI definition to bypass the CI gate).

**`enforce: "evaluate"` across all rulesets**: rulesets are in audit mode pending the
CI-022/CI-023 remediation sweep across all repos. Flip to `active` after the sweep confirms
required check names are consistent. See CI-025a/CI-025b in standards-manifest.yaml.

**`bypass_mode: "always"` on Maintainer role**: a solo developer context. The intention
is to migrate bypass to a dedicated GitHub App (Integration actor type) once one is
configured, and change the mode to `pull_request` to disallow direct push bypasses.
See CI-028 notes in standards-manifest.yaml for the migration path.

## Enforcement Migration Checklist

Before flipping any ruleset from `evaluate` to `active`:

1. Resolve all CI-022 true positives (workflow job naming drift) in every repo targeted
   by the ruleset. Run: `uv run python scripts/check-required-checks.py --all-repos`
2. Verify CI-028: all required_status_checks entries have integration_id: 15368
3. Verify CI-029: file_path_restriction is present in universal rulesets
4. Confirm CI-023 passes (effective required checks match required_checks in manifest)
5. Flip `"enforcement": "evaluate"` to `"enforcement": "active"` and re-apply

Apply in order: universal baseline first, then python tier, then tag protection.
