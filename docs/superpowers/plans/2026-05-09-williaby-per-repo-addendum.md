---
schema_type: planning
title: "williaby per-repo rulesets addendum"
status: draft
owner: core-maintainer
purpose: "Amends 2026-05-08-rulesets-migration.md to handle the discovery that williaby is a User account, not an Organization. Applies the same ruleset shape via per-repo POSTs instead of an org-level POST."
component: Development-Tools
source: "discovered during Track 5 prep on 2026-05-09 when gh api /orgs/williaby/rulesets returned 404"
tags:
  - automation
---

> **Reads:** `2026-05-08-rulesets-migration.md` (parent plan). This addendum replaces that plan's williaby-org-ruleset references with williaby-per-repo-ruleset workflows. The ByronWilliamsCPA org-level path is unchanged.

## Why this addendum exists

`williaby` is a GitHub **User account**, not an Organization. There is no `/orgs/williaby/rulesets` endpoint. User accounts can only host **per-repo rulesets** at `/repos/williaby/<repo>/rulesets`. The parent plan assumed two organizations; that assumption holds for `ByronWilliamsCPA` (27 repos) but breaks for `williaby` (19 repos in catalog).

`setup_repo_rulesets.py` (shipped in PR #78) already handles per-repo POSTs and reuses the same `validate_solo_dev_safe` guard. The fix is operational, not architectural.

## What changes vs. the parent plan

| Topic | Parent plan | This addendum |
| --- | --- | --- |
| williaby ruleset application | Two `/orgs/williaby/rulesets` POSTs (universal + python-tier) | One `/repos/williaby/<repo>/rulesets` POST per non-exempt repo, picking the right template |
| Number of williaby ruleset configurations to maintain | 2 JSON files | 2 template JSON files (same number, different shape) |
| Number of API mutations per phase | 2 per orgmovement | ~25 per phase (dry-runable in seconds) |
| ByronWilliamsCPA path | unchanged | unchanged |
| `setup_org_rulesets.py` against williaby | broken (404) | not used; williaby handled by `setup_repo_rulesets.py` instead |
| Solo-dev guard | yes (in `setup_org_rulesets.py`) | yes (same guard, reused via import in `setup_repo_rulesets.py`) |

## File deliverables (new)

1. `docs/reference/repo-rulesets/_williaby-template-universal.json` , per-repo universal ruleset body for non-Python williaby repos
2. `docs/reference/repo-rulesets/_williaby-template-python.json` , per-repo body for Python williaby repos (universal rules plus `CI Gate`)
3. `scripts/apply_williaby_repo_rulesets.sh` , loop script reading the catalog and applying the right template per repo

The leading underscore in template filenames marks them as templates, not per-repo overrides. The existing per-repo file convention `<org>__<repo>.json` is reserved for hand-authored overrides.

## Tasks

### Task A1: Author the per-repo template bodies

**Files:**
- Create: `docs/reference/repo-rulesets/_williaby-template-universal.json`
- Create: `docs/reference/repo-rulesets/_williaby-template-python.json`

The repo-level body shape is the same as the org-level body, except:
- `conditions.repository_name` is omitted (irrelevant at repo scope)
- `conditions.ref_name.include` stays as `["~DEFAULT_BRANCH"]` (still resolved per-repo)
- `name` becomes per-repo at apply-time; the template uses a placeholder

`_williaby-template-universal.json`:

```json
{
  "name": "williaby-default-branch-baseline",
  "target": "branch",
  "enforcement": "evaluate",
  "bypass_actors": [
    {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
  ],
  "conditions": {
    "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}
  },
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "required_linear_history"},
    {"type": "required_signatures"},
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["squash", "rebase"]
      }
    },
    {
      "type": "copilot_code_review",
      "parameters": {
        "review_draft_pull_requests": false,
        "review_on_push": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          {"context": "Security Gate Validation"},
          {"context": "Dependency & Standards Validation"},
          {"context": "Check REUSE Compliance"}
        ]
      }
    }
  ]
}
```

`_williaby-template-python.json`: identical to the universal template above, except the `required_status_checks.required_status_checks` array also includes `{"context": "CI Gate"}`. (Single ruleset per Python repo combining universal + python-tier rules, since per-repo rulesets compose differently than org-level.)

### Task A2: Author the loop script

**File:** `scripts/apply_williaby_repo_rulesets.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

CATALOG="${CATALOG:-docs/reference/github-repos.json}"
ENFORCEMENT="${ENFORCEMENT:-evaluate}"
DRY_RUN="${DRY_RUN:-false}"
LOG="${LOG:-backups/williaby-rulesets-$(date +%Y-%m-%d).log}"

mkdir -p "$(dirname "$LOG")"
: > "$LOG"

PYTHON_TYPES='"python-package","python-app","python-script"'

while IFS= read -r repo; do
  type=$(jq -r --arg r "$repo" \
    '.repos[] | select(.org=="williaby" and .name==$r) | .repositoryType' "$CATALOG")
  if [[ "$type" == "python-package" || "$type" == "python-app" || "$type" == "python-script" ]]; then
    body="docs/reference/repo-rulesets/_williaby-template-python.json"
    tier="python"
  else
    body="docs/reference/repo-rulesets/_williaby-template-universal.json"
    tier="universal"
  fi

  echo "Applying $tier ruleset to williaby/$repo (enforcement=$ENFORCEMENT)" | tee -a "$LOG"
  args=(--repo "williaby/$repo" --body "$body" --enforcement "$ENFORCEMENT")
  if [[ "$DRY_RUN" == "true" ]]; then
    args+=(--dry-run)
  fi

  if uv run python scripts/setup_repo_rulesets.py "${args[@]}" >>"$LOG" 2>&1; then
    echo "OK williaby/$repo" | tee -a "$LOG"
  else
    echo "FAIL williaby/$repo (exit $?)" | tee -a "$LOG"
    exit 1
  fi
done < <(jq -r '.repos[] | select(.org == "williaby" and (.branchProtectionExempt != true)) | .name' "$CATALOG")

echo "DONE: applied $(grep -c "^OK williaby/" "$LOG") williaby per-repo rulesets" | tee -a "$LOG"
```

Usage:
- Dry-run sweep: `DRY_RUN=true bash scripts/apply_williaby_repo_rulesets.sh`
- Evaluate-mode sweep: `bash scripts/apply_williaby_repo_rulesets.sh`
- Active-mode sweep: `ENFORCEMENT=active bash scripts/apply_williaby_repo_rulesets.sh`

The script fails fast on first repo failure (per `set -euo pipefail`) so a transient error stops the sweep instead of silently corrupting state across repos. Re-run after fixing; the script is idempotent because `setup_repo_rulesets.py` finds and PUTs existing rulesets by name.

### Task A3: Manifest amendment

`docs/standards-manifest.yaml` CI-025 currently reads:

```yaml
verify: "org_ruleset_present: orgs=[ByronWilliamsCPA,williaby], enforcement=active"
```

Replace with two checks:

```yaml
  - id: CI-025a
    domain: ci
    severity: critical
    description: >-
      ByronWilliamsCPA org has at least one active ruleset targeting the default
      branch of every non-exempt repo.
    verify: "org_ruleset_present: orgs=[ByronWilliamsCPA], enforcement=active"
    override_eligible: false
    not_applicable_when: "repo.org != 'ByronWilliamsCPA' OR repo.branchProtectionExempt == true"

  - id: CI-025b
    domain: ci
    severity: critical
    description: >-
      Every non-exempt williaby repo has at least one active repo-level ruleset
      targeting its default branch (williaby is a User account, not an Org).
    verify: "repo_ruleset_present: owner=williaby, enforcement=active"
    override_eligible: false
    not_applicable_when: "repo.org != 'williaby' OR repo.branchProtectionExempt == true"
```

Delete the original CI-025. Renumber CI-026 and CI-027 only if a downstream tool sorts or hashes the manifest by ID; otherwise leave them as-is.

CI-026 (`copilot_code_review` rule present) and CI-027 (classic protection absent post-migration) verify directives need analogous adjustment: the predicate "in the org ruleset" must broaden to "in the org ruleset (BW) or in the repo ruleset (williaby)". Suggested:

- CI-026 verify: `ruleset_contains_rule: targets=[org:ByronWilliamsCPA, repo:williaby/*], rule_type=copilot_code_review`
- CI-027 verify: unchanged (operates per-repo against the classic protection endpoint regardless of owner type)

### Task A4: Auditor doc amendment

In `.claude/agents/ossf-compliance-auditor.md`, the CI-025 FINDING template currently emits:

```text
remediation: |
  uv run python scripts/setup_org_rulesets.py --org <ORG> \
    --body docs/reference/org-rulesets/<ORG>-universal.json --enforcement active
```

Add a sibling block for the williaby case:

```text
**For CI-025b findings (williaby per-repo ruleset missing):**

\`\`\`text
FINDING:
id: CI-025b
severity: critical
description: williaby/<repo> has no active repo-level ruleset on default branch
status: configuration_gap
current_value: gh api repos/williaby/<repo>/rulesets returned [] or all entries have enforcement != active
remediation: |
  uv run python scripts/setup_repo_rulesets.py \\
    --repo williaby/<repo> \\
    --body docs/reference/repo-rulesets/_williaby-template-<tier>.json \\
    --enforcement active
  # tier is "python" if repositoryType in {python-package, python-app, python-script}
  # else "universal"
\`\`\`
```

The CI-026 FINDING similarly needs an alternate remediation path for williaby repos (re-apply the relevant template).

### Task A5: Backup script amendment

The Track 5 backup loop in the parent plan (Task 15) iterates all 45 non-exempt repos and dumps each repo's classic protection. That logic is owner-agnostic and needs no change. The same backup covers both BW and williaby repos.

## Track 5 sequence after this addendum lands

1. **Pre-flight (BW org)**: POST `ByronWilliamsCPA-universal.json` and `ByronWilliamsCPA-python.json` in evaluate mode via `setup_org_rulesets.py` (unchanged from parent plan)
2. **Pre-flight (williaby user)**: `DRY_RUN=true bash scripts/apply_williaby_repo_rulesets.sh` to verify; then `bash scripts/apply_williaby_repo_rulesets.sh` (evaluate mode default)
3. **Verify both**: `gh api /orgs/ByronWilliamsCPA/rulesets` shows two rulesets; spot-check `gh api /repos/williaby/<repo>/rulesets` on a few williaby repos shows one ruleset each
4. **Continue per parent plan** Tracks 6 through 9, with the canary step (Task 17) flipping the BW org ruleset to active AND running `ENFORCEMENT=active bash scripts/apply_williaby_repo_rulesets.sh` for the williaby canary

## Compatibility with existing tooling

- `scripts/check-required-checks.py --source rulesets` already reads `gh api /repos/:r/rules/branches/:b`, which evaluates BOTH org and repo rulesets. No validator code changes required
- `scripts/check-repo-compliance.py` BP-4/BP-5 helpers already query the same `rules/branches` endpoint and walk back to per-ruleset bodies. No code changes required
- The `migrationPhase` field on each repo continues to drive `--source` selection. williaby repos move through `pending -> dual -> complete` exactly like BW repos
- The `BRANCH_PROTECTION_EXEMPT` constant continues to short-circuit `williaby/homelab-agent-configs` from any audit

## Out of scope

- Renaming `setup_org_rulesets.py` to reflect that it only handles BW now. The current name remains accurate; williaby is handled by the existing `setup_repo_rulesets.py`
- Folding the williaby template bodies under `docs/reference/org-rulesets/`. They are NOT org rulesets; they belong under `repo-rulesets/`
- Auto-detection of owner type in `setup_org_rulesets.py`. The script could check whether `--org` resolves to a User vs Organization and route to repo-mode automatically, but this introduces failure mode complexity for a one-time migration. Defer
