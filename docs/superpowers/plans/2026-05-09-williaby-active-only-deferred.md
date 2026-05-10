---
schema_type: planning
title: "Williaby active-only deferred sub-migration"
status: draft
owner: core-maintainer
purpose: "Defines the deferred sub-migration that posts williaby per-repo rulesets directly in active mode (skipping evaluate) because GitHub repo-level rulesets require Enterprise plan for evaluate enforcement."
component: Development-Tools
source: "Discovered 2026-05-09 during Track 5 Phase 5C of the parent rulesets migration; HTTP 422 on every per-repo POST in evaluate mode."
tags:
  - automation
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Predecessor:** PR #82 (`6f86a93`) shipped the addendum implementation.
**Triggered by:** Track 5 Phase 5C blocker discovered 2026-05-09.

## Why this plan exists

During Track 5 Phase 5C (`bash scripts/apply_williaby_repo_rulesets.sh`),
all 26 POST attempts returned HTTP 422 with this error body:

```json
{
  "message": "Validation Failed",
  "errors": [
    "Enforcement evaluate option is not supported on this plan. Please upgrade to Enterprise to enable it."
  ]
}
```

The parent plan and the per-repo addendum both assumed `enforcement: evaluate`
would work uniformly across owners. It does not:

- Org rulesets support `evaluate` mode on all GitHub plans (Free, Team, Enterprise)
- Repo rulesets support `evaluate` mode only on GitHub Enterprise

The `williaby` account is a User on a non-Enterprise plan, so per-repo
rulesets cannot use `evaluate`. The sub-migration must skip the evaluation
period that the original plan baked into Track 5 and proceed directly to
`active` enforcement, mitigating risk via a canary-first deployment.

## What already exists on williaby

Four williaby repos carry pre-existing rulesets unrelated to this migration:

| Repo | Ruleset id | Name | Enforcement |
| --- | --- | --- | --- |
| image-preprocessing-detector | 9575480 | Copilot review for default branch | active |
| image-preprocessing-detector | 9694992 | main | active |
| ledgerbase | 4698329 | Protect Main Branch | active |
| pp-security-master | 15815381 | Main Branch Protection | active |
| PromptCraft | 5939198 | Main Branch Protection | active |

These do not match the migration template's name (`williaby-default-branch-baseline`),
so the sweep script's PUT-by-name idempotency will not touch them. They will
coexist with the migration rulesets as additional layers. **Leaving them in
place per session decision 2026-05-09.** Track 9 cleanup may revisit.

## Scope

This plan defines what runs when the user authorizes williaby live-state work.
It does not run automatically; it must be triggered explicitly.

### Phase W1: Canary (williaby/.claude only)

**Goal:** Prove that an active-mode ruleset on a single williaby repo allows
solo-dev self-merge before sweeping the rest.

- [ ] **Step 1: Apply canary ruleset**

```bash
cd /home/byron/dev/.claude
PYTHONPATH=. uv run --active python scripts/setup_repo_rulesets.py \
  --repo williaby/.claude \
  --body docs/reference/repo-rulesets/_williaby-template-universal.json \
  --enforcement active
```

Expected: ruleset created (POST returns 201), no 422 error.

- [ ] **Step 2: Verify**

```bash
gh api /repos/williaby/.claude/rulesets --jq '.[] | {id, name, enforcement}'
```

Expected: 1 ruleset named `williaby-default-branch-baseline` in `enforcement: active`.

### Phase W2: Open canary test PR and confirm self-merge

- [ ] **Step 1: Open test PR**

In a clone of williaby/.claude:

```bash
git checkout -b canary/ruleset-test
echo "<!-- canary -->" >> README.md
git commit -am "chore: canary test for ruleset enforcement"
git push -u origin canary/ruleset-test
gh pr create --title "Canary: williaby ruleset" --body "Verifies merge under active ruleset."
```

- [ ] **Step 2: Confirm mergeable state**

Wait for CI. Confirm:

```bash
gh pr checks <PR_NUMBER>
gh pr view <PR_NUMBER> --json mergeable,mergeStateStatus
```

Expected: `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN`.

If `BLOCKED`: rollback canary ruleset (`gh api -X DELETE /repos/williaby/.claude/rulesets/{id}`)
and investigate. Classic protection on williaby/.claude is preserved in
`backups/branch-protection-2026-05-09/williaby__.claude.json` for restore.

- [ ] **Step 3: Self-merge**

```bash
gh pr merge <PR_NUMBER> --squash --delete-branch
```

Expected: success.

### Phase W3: Sweep remaining 25 repos in active mode

- [ ] **Step 1: Run the sweep**

After canary validates:

```bash
cd /home/byron/dev/.claude
ENFORCEMENT=active bash scripts/apply_williaby_repo_rulesets.sh
```

The sweep PUTs the canary's ruleset by name (idempotent on williaby/.claude)
and POSTs the other 25. Expected log line: `DONE: applied=26 failed=0`.

### Phase W4: Strip classic protection on williaby canary

- [ ] **Step 1: Delete classic protection**

```bash
gh api -X DELETE /repos/williaby/.claude/branches/main/protection
```

- [ ] **Step 2: Update catalog**

Update `migrationPhase` for `williaby/.claude` from `dual` (or `pending` if
still unset) to `complete`.

### Phase W5: Strip classic protection on remaining 25

- [ ] **Step 1: Run sweep-strip**

Run the sweep-strip script (authored as part of parent plan Task 19) on
the 25 non-canary williaby repos. Bulk-update catalog `migrationPhase` to
`complete`.

### Phase W6: Final validation

- [ ] **Step 1: Run rulesets-only validator**

```bash
PYTHONPATH=. uv run --active python scripts/check-required-checks.py \
  --repo-path . \
  --manifest docs/standards-manifest.yaml \
  --registry docs/reusable-workflow-jobs.yaml \
  --repo-slug williaby/.claude --branch main --check-bp --source rulesets
```

Expected: exit 0, empty findings array.

## Risk assessment

Compared to the original evaluate-then-active plan, the active-only path
is moderately higher risk because:

1. No observation period: a misconfigured ruleset blocks merges immediately
2. The canary mitigates by exercising one repo first, but a canary failure
   on williaby/.claude still affects an in-use repo
3. CI Gate context is in the python template; if any williaby python repo
   has a broken CI workflow, its merges block until CI is fixed
4. Solo-dev guard prevents the worst class of failure (bypass-blocking
   reviewer requirements), but cannot prevent CI-context drift

Mitigations:

- Backup of every classic protection state captured 2026-05-09
- Canary-first: prove the body shape before wide rollout
- Per-repo, sequential sweep, with fail-fast logging in the sweep script
  isolating the first failing repo for diagnosis without affecting others
- Idempotent script so re-running converges cleanly after a partial failure
- `family-office-portal` (empty contexts) flagged in the parent plan
  Gotchas as an expected verification edge case

## When to run this plan

The user will trigger this plan in a future session by saying something like:
"run the williaby active-mode migration." Until then, williaby repos remain
in `migrationPhase: pending` and continue to operate under classic
protection only.

The parent migration (BW Tracks 6-9) can proceed without this plan completing
first. The two migrations are independent.
