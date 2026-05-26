---
title: "Dependency Management & Supply-Chain Security Improvement Plan"
schema_type: planning
status: draft
owner: core-maintainer
component: Strategy
source: "Four-agent analysis (fleet audit + tooling overlap + research + infrastructure)"
purpose: "Prioritized improvement plan for Renovate, SBOM scanning, and supply-chain security across the BWCPA + williaby fleet. Pairs with renovate-architecture.md as the action companion to the reference doc."
tags:
  - dependencies
  - security
  - compliance
  - planning
  - planning
---

This is the action plan derived from a four-agent analysis run on 2026-05-24. Read alongside `docs/reference/renovate-architecture.md` (the reference) and `docs/audits/dependabot-renovate-coverage-2026-05-24.md` (the prior coverage audit).

## TL;DR

The Renovate stack is structurally sound but operationally broken in several places that the existing checks did not catch. Three findings reframe the next 90 days:

1. **PC-015 is installed on 0 of 44 non-exempt repos.** The hook that exists specifically to prevent the recurring `"uv"` trap is in the manifest but was never rolled out. The trap recurred three times because the hook never ran anywhere.
2. **Renovate v42 reached EOL on 2026-01-29.** The homelab is running an unsupported version. v43 eliminates the `"uv"` trap, the validator-pin lockstep, and the `prPriority` placement quirk in one upgrade. Upgrading retires the entire motivation for PC-015.
3. **Trivy's release infrastructure was compromised in March 2026** with vuln DB updates suspended. The SBOM workflow depends on it. Switching to Grype is the recommended pivot.

Plus one urgent fleet-state finding: **36 of 44 non-exempt repos run BOTH Renovate and Dependabot Version Updates** (CI-021 violation). Duplicate PR engines have been shipping in parallel.

## Active Problems (fix this week)

### P0-1: Global `config.json` has `"uv"` in enabledManagers

**Where:** `homelab-infra/services/renovate/config/config.json` line 319, plus two `matchManagers` entries in packageRules (lines 47 and 55).

**Why critical:** Renovate v42.x rejects `"uv"` as an unsupported manager identifier and discards the entire config. Because this is the *global* mounted config, the rejection cascades to every repo simultaneously. The likely current state: Renovate is opening zero PRs fleet-wide.

**Why PC-015 did not catch it:** PC-015 validates per-repo `renovate.json` files. The global Docker-mounted config was never in scope.

**Fix:**
1. Replace `"uv"` with `"pep621"` in `enabledManagers` (line 319).
2. Remove the two `"uv"` entries from `matchManagers` arrays in packageRules (lines 47, 55). They silently do nothing in v42 but cause confusion.
3. Validate the updated config locally with `npx renovate-config-validator@42.92.14 config/config.json`.
4. Restart the renovate container; tail the next run logs for `Config validation errors found`.
5. Add a new manifest check (CI-022 or PC-016) that extends PC-015's validation to `homelab-infra/services/renovate/config/config.json`.

### P0-2: `cookiecutter-python-template` ships the `"uv"` trap

**Why critical:** Every new project bootstrapped from the template inherits the broken config. The template is the *source* of the recurring trap, not its victim. `ByronWilliamsCPA/Unify` already exhibits the downstream symptom (`enabledManagers: github-actions,poetry`, missing `pep621`).

**Fix:** Replace `"uv"` → `"pep621"` in the template. Add the PC-015 hook to the template's `.pre-commit-config.yaml`. Bump the template version and tag a release.

### P0-3: `williaby/PromptCraft` has a triple-defect Renovate config

- Empty `enabledManagers: []` (no PRs at all)
- `managerFilePatterns` (v43-only field, fails on v42)
- `prPriority` inside `vulnerabilityAlerts` (v42 rejects)

Almost certain this repo's Renovate scans are erroring on every run. Fix the config to a known-good v42 baseline.

### P0-4: 9 Python repos declare `"poetry"` against uv-managed projects

**Repos:** `Unify`, `audio-processor`, `cookiecutter-template-sample`, `fragrance-rater`, `maester-tests`, `python-libs`, `rag-processor`, `williaby/dna`, `williaby/image-preprocessing-detector`.

**Why critical:** Per the architecture doc forbidden-values table, the `poetry` manager looks for `[tool.poetry]` but uv uses `[project]`. Result: silently zero dependency PRs. Functionally identical to the `"uv"` trap outcome.

**This explains most of the May 2026 BLOCKED_BY_CONFIG audit finding.** 47% of repos were classified as such; 9 repos with this exact pattern is consistent with that fraction.

**Fix:** Replace `"poetry"` with `"pep621"` in each repo's `renovate.json`. One PR per repo or one sweep PR with per-repo commits.

### P0-5: 36 of 44 repos run both Renovate and Dependabot Version Updates

CI-021 says `dependabot.yml` must be absent when `renovate.json` is present. Spot-check confirms `Unify`'s `dependabot.yml` is a full `version: 2` config scheduling `pip` and `github-actions` weekly, not an alert-only stub.

**Fix:** Mass-delete `.github/dependabot.yml` from the 36 affected repos. Single sweep PR per repo (or use the `cleanup-backlog-scout` agent to scope a batch). Dependabot **Alerts** continue working independently; they are a separate GitHub feature not controlled by `dependabot.yml`.

## Strategic Pivots (fix next 30 days)

### S-1: Upgrade Renovate v42.92 → v43.x

This is the highest-leverage change in the entire plan because it retires multiple existing pieces of complexity:

- The `"uv"` manager trap **disappears entirely** (v43 accepts it).
- The "validator pin must match server" lockstep **disappears entirely** (v43 validator and server accept the same schema).
- The 15 repos using `managerFilePatterns` / `matchSeverity` / `prPriority`-under-vulnerabilityAlerts that currently fail on v42 will pass.
- PC-015 can be downgraded from "exact patch pin" to a tilde-range pin like `renovate@~43` or removed entirely.

**Coordinated rollout (per the existing upgrade procedure in the architecture doc):**

1. Read v43 release notes; identify any *new* breaking changes since current v42.92.
2. Validate the updated global config and a sample of per-repo configs against `renovate-config-validator@latest`.
3. Bump the Docker image tag in `homelab-infra/services/renovate/docker-compose.yml` to a *digest-pinned* v43 image: `renovate/renovate@sha256:<digest>`, not a floating `:43.x` tag.
4. Update PC-015 to a v43-pinned validator (or relax to `renovate@~43` if confident).
5. Update every repo's `.pre-commit-config.yaml` `additional_dependencies` pin in lockstep.
6. Deploy, watch first-run logs for `Config validation errors found`.

### S-2: Roll out PC-015 to all 44 repos (or defer pending S-1)

**Decision point:** PC-015 exists precisely to catch the `"uv"` trap. v43 makes the trap impossible. If S-1 (v43 upgrade) is going to happen in the next 30 days, the value of PC-015 deployment drops to "catch other invalid syntax" rather than "catch the recurring uv trap."

**Two options:**

- **Option A (do both):** Deploy PC-015 now to catch existing v43-deprecated syntax in 15 repos (`fileMatch`, `matchSeverity`, `managerFilePatterns`, `prPriority` placement). Then on v43 upgrade, downgrade or remove the pin.
- **Option B (skip PC-015, jump to v43):** Accept that the existing v43-syntax repos will be fixed by upgrading the server; the validator never had to catch them.

Recommendation: **Option A**, because PC-015 also catches the *next* class of invalid syntax (e.g., a developer copy-pastes from a Renovate plugin doc that uses v44 syntax). The pre-commit gate is structurally valuable beyond the uv trap.

### S-3: Add semantic-lint check for enabledManagers vs detected ecosystem files

PC-015 catches schema errors. It does NOT catch a uv-managed repo with `enabledManagers: ["github-actions"]` only (silently drops Python deps). This is the **other class of silent failure** beyond the `"uv"` trap.

**Implementation:** 30-line Python script as a `local` pre-commit hook. For each repo: if `pyproject.toml` with `[project]` exists, assert effective `enabledManagers` (after org template inheritance) includes `pep621`. If `.github/workflows/` exists, assert it includes `github-actions`. Etc.

Add as **CI-023** in the standards manifest, severity: important.

### S-4: Pin all third-party GitHub Actions to commit SHAs (tj-actions class defense)

The tj-actions/changed-files compromise (CVE-2025-30066, March 2025) retroactively poisoned 23,000+ repos via tag-pointer manipulation. **Repos that pinned to commit SHAs were unaffected.** This is the single highest-impact defensive control available; the cost is one find-and-replace per workflow file.

**Implementation:** Audit all `.github/workflows/*.yml` for `uses: org/action@v4`-style refs (tag pins). Replace with `uses: org/action@<full-sha>` and add a comment `# v4.1.7` for readability. Renovate's `pinDigests: true` packageRule automates this going forward.

**Add manifest check:** **CI-024** (severity: important): third-party action references must be SHA-pinned.

### S-5: Raise `minimumReleaseAge` from 3 days to 14 days for non-security automerge

The Renovate upstream documentation now uses 14 days in its examples. Industry rationale: the axios npm compromise (March 2026) was live for ~4 hours; 3-day windows do not defeat that attack class, but 14-day windows do, because ecosystem monitoring catches malicious uploads within 24-48 hours.

**Critical exception preserved:** vulnerability-triggered PRs continue to use `minimumReleaseAge: 0` for CRITICAL/HIGH CVEs. The 14-day floor applies only to routine version updates.

### S-6: Switch Trivy → Grype (or add Grype as primary)

Trivy's release infrastructure was compromised in March 2026 with vulnerability database updates suspended. Anchore's Grype is the recommended alternative: 30-40% faster for pure CVE scanning, SBOM-first workflow (works with the existing CycloneDX output), unaffected by the Trivy incident.

**Implementation:** Update `python-sbom.yml` to call `grype sbom:./sbom.cdx.json --fail-on high` instead of `trivy sbom`. Keep both tools temporarily for a 30-day comparison window; remove Trivy when parity is confirmed.

**Status (2026-05-25):** Parallel-run phase IN PROGRESS. Grype added as non-gating sibling job in
`python-sbom.yml` via ByronWilliamsCPA/.github PR #169. Trivy remains gating. Day-30 parity checkpoint
scheduled for **2026-06-24**. Cutover (Trivy removal) is a separate spec authored at the checkpoint.

### S-7: Pin Renovate Docker image to `@sha256:<digest>`

Currently the systemd timer runs `docker compose pull --quiet renovate` every 3 hours against tag `renovate/renovate:42.92`. If this is a floating minor tag and a breaking patch ships, the next 3-hour run silently upgrades.

**Fix:** Pin to `renovate/renovate@sha256:<digest>`. Renovate itself can manage the digest bump via the docker-compose manager.

### S-8: Wire Loki alert rules to ntfy

Loki + Promtail are deployed but nothing consumes their output. The OBSERVABILITY.md doc has example alert rules but they were never installed.

**Fix:** Install the two example rules (high error rate, CRITICAL CVE detected). Configure the Loki ruler to push alerts to `scripts/notify.sh` (ntfy). The integration is already scaffolded in OBSERVABILITY.md; wire it up.

**Why this matters:** without alerting, the next time the global config breaks (like the current `"uv"` trap), nobody will know until they notice PRs stopped arriving. The infrastructure exists; the alerting glue does not.

### S-9: Close the SBOM workflow gaps

**Missing SBOM workflow (4 Python repos):** `cookiecutter-template-sample`, `family-office-portal`, `PromptCraft`, `monte_carlo`.
**Missing dependency-review (7 repos):** `cookiecutter-template-sample`, `family-office-portal`, `xero-crypto`, `GCS`, `PromptCraft`, `data_ingestor`, `monte_carlo`.
**Pinned to `@main` (6 repos):** `dataset_dev`, `exercise_competition`, `foundry_unify`, `maester_tests`, `python-libs`, `python_libs`. `@main` is a floating ref, same class of risk as the tj-actions attack.

**Fix:** Add the missing callers; replace `@main` with SHA pins. Add **CI-022** (severity: important): python-sbom.yml caller present and SHA-pinned.

## Coverage Blind Spots (fix this quarter)

### B-1: Docker base image OS packages are scanned by NOTHING

`cyclonedx-bom` builds the SBOM from the Python venv only. A CVE in `libexpat`, `openssl`, or `glibc` in the base image passes every current gate.

**Fix:** Add a `trivy image <image>` (or `grype <image>`) step in `python-sbom.yml` for PRs that touch `Dockerfile` or `docker-compose.yml`. Cost: 3-5 CI minutes per affected PR. No infrastructure required.

### B-2: Terraform CVE coverage is ZERO

Renovate updates version pins. No tool reads a Terraform-specific CVE database.

**Fix:** Add Checkov or tfsec to repos containing `*.tf`. Both have pre-built GitHub Actions; both catch misconfigurations *and* known-vulnerable provider versions.

### B-3: npm has no dev-time CVE scanning equivalent to pip-audit

Even free `npm audit` would provide parity with pip-audit. Recommended for the small number of npm-touching repos.

### B-4: GitHub Actions supply chain (compromised actions before GHSA publishes)

Solution path: pin to SHAs (S-4 above) eliminates retroactive tag-poisoning. For real-time compromised-Action detection, the options are paid (Aikido, Socket) and likely overkill at this scale.

## Provenance & Attestation (fix this quarter)

### A-1: PyPI attestations via `pypa/gh-action-pypi-publish`

Free attestations attach automatically when `id-token: write` is granted. PEP 740 GA November 2024; 132K+ packages already attesting. For any Python package published from this fleet to PyPI, the cost is one line in a workflow.

### A-2: cosign keyless signing for Docker images

`cosign sign --yes $IMAGE_DIGEST` in a workflow with `id-token: write`. No key management; signatures stored in registry as `.sig` OCI artifacts. Verification at deploy time via Kyverno or Sigstore Policy Controller.

### A-3: Enforce `uv run --frozen` (not `uv sync`) in CI

Without `--frozen`, `uv sync` is permitted to mutate the lockfile to accommodate dependency drift. This silently weakens lockfile integrity. The fix is one flag in every CI workflow.

## Process Changes

### Pr-1: `lockFileMaintenance: { automerge: true }` (currently false)

Weekly lockfile PRs sit unmerged → superseded by next week's PR → continuous treadmill with no net effect. Lockfile-only PRs contain no logic changes; CI is sufficient gate. If a repo has flaky CI, override per-repo.

### Pr-2: Add a middle automerge tier for dev/tooling minors

Current policy: CRITICAL/HIGH auto immediately, patches auto after 14 days (per S-5), everything else manual. Add: minor updates on dev dependencies (test frameworks, linters, type checkers) auto-merge after 3 days with passing CI. These have near-zero production risk and currently sit in the manual review queue indefinitely.

### Pr-3: Weekly Dependency Dashboard triage cadence

Aligns with `lockFileMaintenance` (Monday). Any open Renovate PR where CI passes and `minimumReleaseAge` has elapsed should be merged or labeled `stop-updating`. PRs open > 14 days with passing CI are blocked by process, not by content.

### Pr-4: Defer retiring Dependabot Security Updates

The doc proposes retiring this once Renovate config is verified clean. The fleet audit shows that "clean" is fragile: replace-not-merge semantics on `enabledManagers` means a single per-repo edit can silently narrow coverage below Dependabot. **Recommendation:** keep Dependabot Security Updates enabled until (a) S-3 (semantic enabledManagers lint) is deployed AND (b) two consecutive monthly Renovate audits show zero `BLOCKED_BY_CONFIG` repos.

## Deferred / Scale-Only

- **Socket.dev / Aikido** for malicious package detection (PyPI/npm). Behavior-based detection beyond CVEs. Paid; appropriate at higher scale.
- **PEP 770** (SBOM in wheel METADATA). Watch but do not implement; spec still in draft as of mid-2026.
- **Renovate App** (managed) instead of self-hosted. Eliminates lockstep entirely but introduces a different validator-pin tracking problem. Self-hosted + v43 is the right call at this scale.
- **Sigstore Policy Controller / Kyverno** for image signature verification at deploy time. Requires Kubernetes; not applicable to current homelab posture.

## Priority Summary

| Priority | Item | Effort | Risk if not done |
|---|---|---|---|
| P0-1 | Fix global config.json `"uv"` | 30 min | Fleet-wide Renovate failure |
| P0-2 | Fix cookiecutter-python-template | 1 hr | New projects inherit trap |
| P0-3 | Fix PromptCraft triple-defect | 30 min | Renovate erroring per-run |
| P0-4 | Fix 9 `poetry`→`pep621` repos | 2 hr | Silent zero PRs continue |
| P0-5 | Delete 36 dependabot.yml files | 4 hr | Duplicate PR engines |
| S-1 | Upgrade Renovate v42→v43 | 1 day | Running on EOL'd version |
| S-2 | Roll out PC-015 to 44 repos | 4 hr | Next trap also goes unblocked |
| S-3 | Add semantic enabledManagers lint | 1 day | Silent coverage gaps recur |
| S-4 | SHA-pin third-party Actions | 1 day | tj-actions class exposure |
| S-5 | minimumReleaseAge 3d → 14d | 30 min | axios-class exposure |
| S-6 | Trivy → Grype migration | 1 day | Trivy compromise propagates |
| S-7 | Pin Renovate image to SHA digest | 30 min | Silent breaking upgrades |
| S-8 | Wire Loki alerts to ntfy | 2 hr | Future failures stay silent |
| S-9 | Close SBOM caller gaps | 4 hr | 4-7 repos missing gates |
| B-1 | Trivy/Grype direct image scanning | 4 hr | Docker base CVE blind spot |
| B-2 | Checkov for Terraform | 2 hr | Terraform CVE blind spot |
| A-1 | PyPI attestations | 1 hr per repo | Missing free provenance |
| A-2 | cosign image signing | 1 day | No signature verification |
| Pr-1 | lockFileMaintenance automerge | 15 min | PR treadmill |

**Total P0 work: ~8 hours.** Should be done this week; P0-1 is the most urgent.
**Total S-tier work: ~5 days spread across 30 days.**
