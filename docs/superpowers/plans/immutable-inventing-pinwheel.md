---
title: "Renovate v42.92 to v43.x Upgrade Plan"
schema_type: planning
status: draft
owner: core-maintainer
component: Strategy
source: "Synthesized from the 2026-05-24 dependency-management fleet audit. Pairs with docs/audits/v43-readiness-2026-05-24.md."
purpose: "Hybrid Phase 0 hotfix plus Phase 1-3 coordinated cutover from Renovate v42.92 to v43.x for the self-hosted Renovate stack in homelab-infra; retires PC-015 and the uv-manager trap."
tags:
  - planning
  - dependencies
  - automation
  - infrastructure
---

## Context

The self-hosted Renovate Docker stack in `homelab-infra/services/renovate/` runs v42.92, which reached end-of-life on **2026-01-29**. The fleet audit on 2026-05-24 (see `docs/audits/dependency-management-improvement-plan-2026-05-24.md`) identified the v43 upgrade (item S-1) as the highest-leverage architectural change because it simultaneously retires three documented sources of complexity:

1. The recurring `"uv"` manager trap (`feedback_renovate_uv_manager_trap.md`, recurred four times); v43 accepts `"uv"` natively.
2. The validator-server schema lockstep that motivates PC-015; v43 unifies the schemas.
3. The `prPriority` placement quirk under `vulnerabilityAlerts`; v43 accepts the new placement.

The upgrade also addresses an **active production issue**: the global `config/config.json` currently contains `"uv"` in `enabledManagers`, which v42 rejects, causing fleet-wide silent failure of Renovate PR generation. That issue is fixed in Phase 0 independent of the v43 upgrade.

**Intended outcome:** v43.195.1 (current latest as of 2026-05-24 per endoflife.date) deployed via SHA-digest pin, PC-015 retired, semantic-lint (CI-059) and image-pin (CI-061) checks active, all 46 repos receiving Renovate PRs again with the correct manager coverage.

## Recommended approach: Hybrid (Phase 0 hotfix + Phase 1-3 coordinated cutover)

Approach was selected after pressure-testing against strict-lockstep and leapfrog alternatives. Strict-lockstep is obsolete the moment v43 retires the validator pin. Leapfrog ignores three v43 breaking changes (postUpgradeTasks shell mode, lockFileMaintenance grouping, Node 24 baseline) that must be audited before cutover. Hybrid splits the urgent fleet-restoration work from the structural upgrade.

### Phase 0: Day 0 emergency hotfix (~2 hours)

Goal: stop the silent fleet-wide breakage without touching v43 yet.

**Files to modify:**

- `homelab-infra/services/renovate/config/config.json`
  - Line 318-333 `enabledManagers`: remove `"uv"`, keep `"pep621"`.
  - Lines 47, 55, 63 `packageRules[].matchManagers`: remove `"uv"` entries (silently no-op on v42, cause confusion on v43).
- `ByronWilliamsCPA/cookiecutter-python-template`: `renovate.json`: replace `"uv"` with `"pep621"` in `enabledManagers`. Same change in any committed template fixtures.
- `williaby/PromptCraft/renovate.json`: replace empty `enabledManagers: []` with `["pep621", "github-actions", "dockerfile", "docker-compose", "npm"]`. Remove `managerFilePatterns` (v43-only). Move `prPriority` out of `vulnerabilityAlerts` into the appropriate `packageRules` entry (v42 placement).

**Validation:** locally run `npx renovate-config-validator@42.92.14 config/config.json` against each modified file. Exit code must be 0.

**Deploy:** ship the homelab-infra change via PR, merge, `systemctl restart renovate.service`. Tail `/var/log/renovate-last-run.log` after the next 3-hour timer fire; confirm absence of `Config validation errors found`.

### Phase 1: Day 1-7 pre-upgrade audit (~6 hours, no production changes)

Goal: surface every v43 incompatibility before cutover. Read-only work.

**Resolve target versions:**

- Target: **renovate/renovate:43.195.1** (current latest as of 2026-05-24 per endoflife.date; well past the 43.20.1 floor that mattered for the lockFileMaintenance grouping revert). At cutover time, re-check `https://endoflife.date/renovate` for any newer patch; Renovate's release cadence is daily, so 43.195.1 will likely be superseded by cutover Day 8. Pin via `docker pull renovate/renovate:43.195.1` (or the current latest) and capture the resulting `sha256:` digest with `docker inspect renovate/renovate:43.195.1 --format '{{index .RepoDigests 0}}'`.
- Skip the `renovatebot/pre-commit-hooks` SHA resolution: PC-015 is being retired entirely in Phase 3, not re-pinned.

**Audit current global config for v43 breaking changes:**

- **postUpgradeTasks shell mode:** Grep `homelab-infra/services/renovate/config/config.json` for `postUpgradeTasks`. If any command contains `&&`, `|`, redirects, globs, or other shell metacharacters, either set `allowShellExecutorForPostUpgradeCommands: true` in the new config OR rewrite each command as a single executable plus args array. The existing `RENOVATE_ALLOWED_POST_UPGRADE_COMMANDS` env var allowlist is orthogonal and continues to work.
- **lockFileMaintenance grouping:** Confirm no `packageRules` group `lockFileMaintenance` with other update types. 43.20.1 reverted the breakage but verify.
- **replacements grouping:** Same check for any `packageRules` that group `replacements`.

**Audit all 44 per-repo configs against v43 validator:**

- For each repo, fetch `renovate.json` via `gh api repos/{org}/{repo}/contents/renovate.json` (per `feedback_gh_search_code_staleness.md`, never `gh search code`).
- Run `npx renovate-config-validator@43.195.1` (or whichever 43.x is the target at cutover) against each in a scratch directory.
- Expected zero failures for the 15 repos already using v43-syntax (`managerFilePatterns`, `prPriority`-under-vulnerabilityAlerts); they currently fail v42 and pass v43.
- Collect any unexpected failures into a remediation list.

**Output:** an audit report at `docs/audits/v43-readiness-2026-MM-DD.md` listing every config that needs touching and what change is required. Do not touch any files yet.

### Phase 2: Day 8 cutover (~1 hour active + 24-hour watch)

Goal: deploy v43 with rollback capability intact.

**Phase 1 revised this section's scope.** The full Phase 1 audit (`docs/audits/v43-readiness-2026-05-24.md`) returned 0 hard failures across 34 per-repo configs + the global config + the org template. No config field edits are required beyond the customManager addition. The cutover is the three changes below.

**Resolved target reference (2026-05-24):** `renovate/renovate:43.150.0@sha256:f2d4c467a8eb4b885630a8ca7d068173db69a5a1156ba41480c0a3a2e011d759`. Re-resolve at cutover time if more than a few days have passed (Renovate ships daily). Resolve via:

```bash
TOKEN=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:renovate/renovate:pull" | jq -r .token)
curl -sI -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json" \
  "https://registry-1.docker.io/v2/renovate/renovate/manifests/<version>" \
  | grep -i docker-content-digest
```

**Single PR to homelab-infra:**

1. `services/renovate/docker-compose.yml` line 14: change `image: renovate/renovate:42.92` → `image: renovate/renovate:43.150.0@sha256:f2d4c467a8eb4b885630a8ca7d068173db69a5a1156ba41480c0a3a2e011d759` (tag + digest both present so the version is human-readable AND cryptographically verified).
2. `services/renovate/config/config.json`: add a `customManagers` regex entry that matches the `image: renovate/renovate:<tag>@sha256:<digest>` line in `docker-compose.yml`, with `datasourceTemplate: docker`, `depNameTemplate: renovate/renovate`. Pair with a packageRule targeting `matchPackageNames: ["renovate/renovate"]` setting `minimumReleaseAge: "14 days"` and `automerge: false`. Self-bumps deserve human review and community burn-in time. NO other config.json field edits are needed; the Phase 1 audit confirmed v43 accepts the existing config as-is.
3. `services/renovate/systemd/renovate.service` line 11: remove `ExecStartPre=/usr/bin/docker compose pull --quiet renovate`. The image is now SHA-pinned, so no need to pull-then-up on every fire; `docker compose up` alone will use the cached image matching the digest. This kills the silent-pull vector.

**Deploy:** merge the PR, `systemctl daemon-reload && systemctl restart renovate.service`.

**Watch (24 hours):**

- Tail `/var/log/renovate-last-run.log` across the next 8 timer fires (24 hours).
- Watch for `Config validation errors found` (none expected after Phase 1 audit).
- Watch for `postUpgradeTask` failures with the specific signature of `command not found` or `permission denied` (the shell-mode regression).
- Watch for "artifacts: FAILURE" on uv.lock PRs (the most likely v43 regression surface).
- Check the GitHub PR dashboard for any new Renovate PRs; confirm normal cadence resumes within one timer cycle.

**Rollback plan:** if any failure mode appears, revert the single homelab-infra PR. Image returns to v42.92 (still tagged in registry, still pullable). systemd service restarts cleanly with the old config. Total rollback time ~5 minutes. PC-015 was never re-pinned (it doesn't exist yet on the fleet), so no per-repo rollback is needed.

### Phase 3: Day 9-10 sweep batch (~4 hours)

Goal: bundle the deferred fleet hygiene work that v43 makes safe to ship together.

Open a sweep PR series via `cleanup-backlog-scout` (one PR per repo, batched in a single ride):

1. **9 poetry to pep621 fixes** (`Unify`, `audio-processor`, `cookiecutter-template-sample`, `fragrance-rater`, `maester-tests`, `python-libs`, `rag-processor`, `williaby/dna`, `williaby/image-preprocessing-detector`); same one-line change in each `renovate.json`.
2. **36 `dependabot.yml` deletes**; list per `docs/audits/dependency-management-improvement-plan-2026-05-24.md` P0-5.

**Update the standards manifest in the same window:**

- `docs/standards-manifest.yaml`: delete the PC-015 entry (lines 469-510). Add a `notes:` field to PC-016 explaining it was promoted from suggested to important.
- Promote CI-058 (python-sbom caller SHA-pinned) from `severity: suggested` to `important`.
- Promote CI-059 (semantic enabledManagers lint) from `suggested` to `important`; this becomes the structural successor to PC-015.
- Promote CI-060 (third-party Action SHA pins) from `suggested` to `important`.
- Promote PC-016 (global Renovate config validator) from `suggested` to `critical`.
- Add new check **CI-061 (severity: critical)**: Renovate Docker image in `homelab-infra/services/renovate/docker-compose.yml` must be pinned to a `@sha256:` digest, not a tag. Cross-reference this plan.

### Phase 4: Day 11+ ongoing settle

- Monitor first full v43 PR cycle across the fleet (typically 7-14 days for one complete cycle including lockfile maintenance).
- Build the CI-059 semantic-lint script (per S-3 in the improvement plan) and deploy as a local pre-commit hook to all 44 repos. This is the v43-era structural successor to PC-015.

## Items explicitly NOT in this plan

The following improvement-plan items are deferred to separate PRs after Phase 3 stabilizes; each is bisectable on its own and bundling would obscure causation:

- **S-5** minimumReleaseAge 3d → 14d (Day 22+ separate PR)
- **S-6** Trivy → Grype migration (separate workstream)
- **Pr-1** lockFileMaintenance automerge: true (Day 22+, after one full v43 lockFileMaintenance cycle observed)
- **S-4** Third-party Action SHA pinning (separate fleet sweep, governed by new CI-060)
- **S-8** Loki alert rule wiring (separate observability workstream)

## Critical files reference

- `/home/byron/dev/homelab-infra/services/renovate/docker-compose.yml`: image pin (line 14), systemd interaction
- `/home/byron/dev/homelab-infra/services/renovate/config/config.json`: enabledManagers (lines 318-333), matchManagers (lines 47, 55, 63), postUpgradeTasks audit, customManager addition
- `/home/byron/dev/homelab-infra/services/renovate/systemd/renovate.service`: ExecStartPre removal (line 11)
- `/home/byron/dev/.claude/docs/standards-manifest.yaml`: PC-015 deletion, severity promotions, CI-061 addition
- `/home/byron/dev/.claude/docs/reference/renovate-architecture.md`: update version references from v42.92 to v43.x, document new customManager pattern, remove the "lockstep is essential" warning (no longer applies)

## Verification

End-to-end success criteria:

1. **Phase 0:** `gh api repos/ByronWilliamsCPA/homelab-infra/contents/services/renovate/config/config.json` returns content with `"pep621"` in `enabledManagers`, no `"uv"`. The next 3-hour Renovate run log shows zero `Config validation errors found`. At least one new Renovate PR appears in any BWCPA or williaby repo within 6 hours of the restart.

2. **Phase 1:** Audit report exists at `docs/audits/v43-readiness-YYYY-MM-DD.md` enumerating zero blocking failures (or, if failures exist, each has a Phase 2 remediation plan).

3. **Phase 2:** `docker inspect $(docker compose ps -q renovate) | jq -r '.[0].Image'` shows a v43.x SHA digest. 24 hours after deploy, the GitHub PR dashboard shows new Renovate PRs across the fleet at normal cadence, with zero `artifacts: FAILURE` checks on uv.lock PRs.

4. **Phase 3:** `grep -c "id: PC-015" docs/standards-manifest.yaml` returns 0. `grep "id: CI-061" docs/standards-manifest.yaml` returns 1. All 9 poetry→pep621 PRs and all 36 dependabot.yml-delete PRs are merged. The next fleet audit shows zero `"poetry"` declarations in uv-managed repos and zero `dependabot.yml` files alongside `renovate.json`.

5. **Phase 4:** CI-059 semantic-lint script is in `/home/byron/dev/.claude/scripts/` and runs as a local pre-commit hook in all 44 repos (verified via fleet-wide hook presence audit). Next v43 patch publishes → Renovate's customManager opens a PR to bump the SHA digest within 14 days.
