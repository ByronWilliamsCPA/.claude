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

> **williaby deployment note:** `--org williaby` returns HTTP 404 because williaby is a personal
> account, not a GitHub organization. The `/orgs/{account}/rulesets` API endpoint only exists
> for organization accounts. For williaby repos, use the per-repo deployment path via
> `scripts/apply_williaby_repo_rulesets.sh` with templates from `docs/reference/repo-rulesets/`.
> Tag-protection deployment templates for williaby are not yet present in `repo-rulesets/`; that
> path is deferred until the per-repo ruleset infrastructure is extended.

## Ruleset Architecture

Each org has a four-tier ruleset stack. The branch-target rulesets apply to the
default branch on push and PR events; the push-target ruleset applies to every
push regardless of branch:

| Tier | File | Target | Applies to | Adds |
| ---- | ---- | ------ | ---------- | ---- |
| Universal baseline | `*-universal.json` | branch | All repos | Lifecycle rules, PR policy, status checks |
| Push baseline | `*-push-baseline.json` | push | All repos | Trust-boundary file protection, file size cap |
| Python CI gate | `*-python.json` | branch | Python repos only | CI Gate required check |
| Tag protection | `*-tag-protection.json` | tag | All repos with releases | SemVer name enforcement, tag immutability (creation/deletion/update/non_fast_forward) |

A repo's effective protection is the union of every ruleset whose target and
conditions match the operation. Per-repo rulesets in `../repo-rulesets/` layer
on top of these org-level rules.

> **Why push baseline is a separate ruleset:** `file_path_restriction` and
> `max_file_size` are push-rule types in the GitHub Rulesets API. The API
> rejects them inside a `target: branch` body with a 422 Validation Failed.
> Push rules do not accept branch targeting because they apply to every push,
> not to a specific ref. Splitting the push baseline into its own ruleset is
> the structurally required fix, not a stylistic choice.

## File Inventory

### ByronWilliamsCPA

**`ByronWilliamsCPA-universal.json`**: `ByronWilliamsCPA-default-branch-baseline`

Applied to all repositories at `target: branch`. Enforces:
- Force push and branch deletion prohibition
- Required linear history (squash or rebase merges only; no merge commits)
- Required commit signatures (GPG/SSH)
- Pull request policy: 0 required reviewers, CODEOWNERS review required, stale review
  dismissal on push, squash/rebase merge methods only
- Copilot code review on PR open/ready events
- Required status checks: Security Analysis / Security Gate Validation, Dependency & Standards Validation,
  Check REUSE Compliance (all pinned to integration_id 15368)

**`ByronWilliamsCPA-push-baseline.json`**: `ByronWilliamsCPA-push-baseline`

Applied to all repositories at `target: push`. Enforces:
- File path restriction: trust-boundary path set protected from modification by non-bypass
  actors: `.github/workflows/`, `.github/CODEOWNERS`, `.pre-commit-config.yaml`,
  `pyproject.toml`, `renovate.json`, `sonar-project.properties`, `.gitleaks.toml`
- File size cap: 100 MB per file (prevents large-binary commits by bypass actors that
  bypass pre-commit hooks)

**`ByronWilliamsCPA-python.json`**: `ByronWilliamsCPA-python-tier-ci-gate`

Applied to Python repositories only (via generated repository pattern). Adds:
- Required status check: CI Gate (pinned to integration_id 15368)
- `do_not_enforce_on_create: true` so the first push to a new repo default branch is
  not blocked before CI Gate workflow exists

**`ByronWilliamsCPA-tag-protection.json`**: `ByronWilliamsCPA-semver-tag-protection`

Applied to all repositories, targeting `refs/tags/v*` refs. Enforces:
- Tag creation restricted to bypass actors
- Tag deletion restricted to bypass actors
- No tag movement (non_fast_forward)
- No annotated-tag reassignment via the API (update)
- Required signatures on tagged commits
- Tag name must match SemVer regex `^v\d+\.\d+\.\d+(-[\w.]+)?$` (tag_name_pattern)

### williaby

**`williaby-universal.json`**: `williaby-default-branch-baseline`

Identical to ByronWilliamsCPA-universal except excludes `homelab-agent-configs`.
Applied as a user-level ruleset (williaby is a personal account, not an org).

**`williaby-push-baseline.json`**: `williaby-push-baseline`

Identical to ByronWilliamsCPA-push-baseline except excludes `homelab-agent-configs`.
Williaby application is deferred (per the rulesets-migration roadmap); the JSON is
maintained in lockstep with the BW counterpart so the structural fix lands together
across both orgs.

**`williaby-python.json`**: `williaby-python-tier-ci-gate`

Identical to ByronWilliamsCPA-python: CI Gate required check, `do_not_enforce_on_create: true`.

**`williaby-tag-protection.json`**: `williaby-semver-tag-protection`

Identical to ByronWilliamsCPA-tag-protection except excludes `homelab-agent-configs`.

## Key Design Decisions

**`integration_id: 15368`** on all required status checks: pins each check to the GitHub
Actions app. Without this, any actor with write access can post a passing check with the
same name and satisfy the requirement. 15368 is the stable GitHub Actions app ID; verify
with `gh api /apps/github-actions --jq .id`.

**`strict_required_status_checks_policy: true`**: requires the PR branch to be current
with the base branch before checks count. This prevents a class of race conditions
(two passing PRs that touch overlapping code) at the cost of requiring rebase before merge.

**`file_path_restriction` expanded to seven trust-boundary paths**: the restriction
covers `.github/workflows/`, `.github/CODEOWNERS`, `.pre-commit-config.yaml`,
`pyproject.toml`, `renovate.json`, `sonar-project.properties`, and `.gitleaks.toml`.
These seven files collectively define the local gate stack: CI workflow definitions,
who owns review gates, pre-commit hooks, Python tool and linting config, dependency
update policy, SonarCloud project config, and secret detection rules. Any one of them
can be modified to disable or circumvent compliance checks. Restricting the full set
closes the gap where a contributor could weaken the hook or scanner config while
leaving `workflows/` intact and passing audit.

**`max_file_size: 100` (MB) in push-baseline rulesets**: GitHub's pre-receive layer rejects
any file exceeding 100 MB, regardless of bypass actor status. Pre-commit hooks that
catch large binaries do not run when a bypass actor pushes directly; this server-side
cap is the backstop. The limit matches GitHub's internal large-file warning threshold
and is consistent with CI-032 in standards-manifest.yaml.

**`update` rule in tag-protection rulesets**: `non_fast_forward` prevents tag movement
(re-pointing an existing tag to a different commit via force-push), but it does not
prevent the GitHub API from reassigning an annotated tag object to a different commit.
Adding `update` closes this gap. Both rules are required for complete tag immutability.

**`tag_name_pattern` with SemVer regex**: enforces `^v\d+\.\d+\.\d+(-[\w.]+)?$` at
the server layer before the tag is created. Without this, a release workflow can push
a tag like `release-20240101` or `v2` that satisfies creation-restricted access but
does not align with semantic-release conventions. The pattern gate runs before any
signature check, so a malformed tag name is rejected immediately without consuming
a signing operation.

**`do_not_enforce_on_create: true` in python-tier rulesets**: the CI Gate required
check cannot exist before the CI Gate workflow file is committed. When a new Python
repo is created, the first push to the default branch would fail the ruleset before
any workflow is in place. Setting `do_not_enforce_on_create: true` allows the initial
branch creation to proceed, after which CI Gate enforcement activates on subsequent
pushes. This flag only skips the check on the branch-create event; it does not waive
the check for any PR or subsequent push.

**`enforcement: "evaluate"` across all rulesets**: rulesets are in audit mode pending the
CI-022/CI-023 remediation sweep across all repos. Flip to `active` after the sweep confirms
required check names are consistent. See CI-025a/CI-025b in standards-manifest.yaml.

**`bypass_mode: "pull_request"` on Admin role** (actor_id: 5, actor_type: RepositoryRole):
a solo developer context. RepositoryAdmin bypass is restricted to merged PRs only;
direct pushes are NOT subject to bypass and the push-baseline rules apply uniformly.
The push-baseline JSON files (`*-push-baseline.json`) were tightened from `always` to
`pull_request` in PR #103 to close the direct-push attack surface ahead of flipping
enforcement from `evaluate` to `active`. Long-term, bypass should migrate to a
dedicated GitHub App (Integration actor type) once one is configured; see CI-028
notes in standards-manifest.yaml for the migration path.

## Enforcement Migration Checklist

Before flipping any ruleset from `evaluate` to `active`:

1. Resolve all CI-022 true positives (workflow job naming drift) in every repo targeted
   by the ruleset. Run: `uv run python scripts/check-required-checks.py --all-repos`
2. Verify CI-028: all required_status_checks entries have integration_id: 15368
3. Verify CI-029: file_path_restriction is present in the push-baseline ruleset and
   covers all seven trust-boundary paths
4. Verify CI-030: tag-protection rulesets are present per org with creation, deletion,
   non_fast_forward, update, required_signatures, and tag_name_pattern rules
5. Verify CI-031: harden-runner egress-policy is `block` (not `audit`) in ci.yml,
   pr-validation.yml, and reuse.yml for each targeted repo, or a dated deferral comment
   is present
6. Verify CI-032: push-baseline rulesets include max_file_size with a value not exceeding 100 MB
7. Confirm CI-023 passes (effective required checks match required_checks in manifest)
8. Flip `"enforcement": "evaluate"` to `"enforcement": "active"` and re-apply

Apply in order: universal baseline first, then push baseline, then python tier, then tag protection.
