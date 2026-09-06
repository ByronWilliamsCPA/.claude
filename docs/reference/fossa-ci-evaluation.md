---
title: "FOSSA CI Integration: License Compliance Evaluation and Decision"
schema_type: common
status: published
owner: core-maintainer
purpose: "Evaluation and DEFER decision on adding the FOSSA license-compliance SaaS to the CI fleet, with the cheaper in-house gate-repair alternative documented."
tags:
  - reference
  - dependencies
  - ci_cd
  - evaluation
---

> **Update (2026-09):** GitHub now bills Advanced Security (Code Security) separately, so
> `actions/dependency-review-action` no longer functions on the free tier for any repo,
> public or private. `dependency-review.yml` was removed fleet-wide, and the manifest
> checks this evaluation drove, **CI-036** (dependency-review.yml presence) and **CI-081**
> (its deny-licenses/allow-licenses input), were retired as deprecated stubs. The DEFER
> conclusion below is unaffected: it never relied on dependency-review-action as a reason
> to skip FOSSA. But the "4 existing layers" in Finding 3 is now 3 layers, action-plan step
> 3 (adding `deny-licenses` to `dependency-review.yml`) is moot, and the decision-matrix
> column for `dependency-review-action` reflects a capability the fleet no longer has.
> **CI-080** (the `sbom.yml` license denylist) is unaffected and remains the fleet's
> PR-diff-adjacent, though not diff-scoped, license-policy control.

This report evaluates whether to add FOSSA (a third-party license-compliance SaaS) to the 44-repo `claude-config` fleet's CI. Six dimension analyses converge on a single conclusion: the fleet is overwhelmingly permissive (253 of 263 distributions in the active `claude-config` venv are permissive; the remaining 10 are 8 MPL-2.0 plus 2 LGPL, none of which create obligations for an MIT app that dynamically imports unmodified source), and zero GPL or AGPL packages exist in any managed `uv.lock` fleet-wide. FOSSA's deep-scan value is real but does not match the actual risk profile: its license-gating feature is paid-tier only, its free tier caps at 5 projects against 34 Python repos, it cannot read the org's REUSE 3.0 own-source layout, and every capability it would add over the current stack is already achievable by repairing the dormant in-house license gate that ships in `python-sbom.yml`. This is the same structural conclusion the companion `dependency-tooling-comparison.md` reached for Snyk: a third-party SaaS is not justified at this fleet size unless license compliance becomes a hard contractual requirement.

## Overall recommendation: DEFER

Do not adopt FOSSA at this time. Instead, repair and arm the existing in-house license gate. Revisit FOSSA only if one of these conditions becomes true:

1. A legal team, audit, or enterprise customer contractually requires a FOSSA-branded SBOM or attestation report.
2. Dependency packages with custom or proprietary license texts require source-level (snippet) scanning, which is a FOSSA Enterprise feature.
3. Automated NOTICE / THIRD-PARTY-LICENSES file generation becomes a release-gate requirement and `pip-licenses` output proves insufficient.

None of these hold today. The DEFER is unanimous across all six analysts at high confidence.

### Resolving the central tension explicitly

The tension is deep-scan value versus adding a third-party SaaS to CI when the fleet is overwhelmingly permissive and already owns a dormant in-house gate. It resolves cleanly because the two halves of FOSSA's value proposition fail independently:

- The detection half (find copyleft in the dependency graph) is matched by the in-house stack once three known defects are fixed, at zero marginal cost and zero new egress.
- The gating half (block a PR on a license-policy violation) is a FOSSA paid-tier feature, so the free tier adds nothing the existing `python-sbom.yml` job cannot already do.

There is no quadrant where FOSSA is both differentiated and free. The only genuinely FOSSA-exclusive capabilities (a license-compatibility graph and automated NOTICE generation) are not required at a 44-repo solo-maintained fleet that redistributes no copyleft library files. Adopting FOSSA now would also reintroduce a recurring SaaS cost (roughly $680/month at $20/project for 34 Python repos, or roughly $399/month Team tier just to cover the 4 private repos), a new external dependency in the PR critical path, and a documented incompatibility with the org's REUSE layout.

## What FOSSA would return for the current dependencies

The local, PEP-639-aware license inventory for the `claude-config` resolved closure (263 distinct distributions in the active venv, roughly 201 in `uv.lock`):

| License class | Count | Packages of note |
|---|--:|---|
| Permissive (MIT 123, BSD 73, Apache-2.0 45, ISC 9, Python 2, PSF 1) | 253 | The overwhelming majority; no obligations |
| MPL-2.0 (file-level copyleft) | 8 | certifi, fqdn, hypothesis, pathspec, pytest-html, pytest-metadata, pytest-rerunfailures, tqdm |
| LGPL (weak copyleft) | 2 | psycopg2-binary, python-gitlab |
| GPL / AGPL | 0 | none in `claude-config` |
| Undetermined | 0 | none |

For an MIT application that imports (does not modify or statically link) these packages, none of the 10 non-permissive packages create an obligation. MPL-2.0 file-copyleft triggers only on modifying and redistributing the covered source files; LGPL explicitly permits dynamic import. FOSSA would flag all 10 for review, requiring 10 per-package ignores with justification, while delivering no new actionable finding versus a correctly configured in-house denylist.

Three caveats sharpen this picture and are the reason the in-house gate must be repaired rather than merely armed:

- `tqdm`, `psycopg2-binary`, and `python-gitlab` are NOT in any managed `uv.lock` or `pyproject.toml`; they are spurious manual pip installs polluting the `claude-config` venv. They should be removed from the venv, not gated. FOSSA scanning the full venv SBOM would flag them as managed risk when they are not.
- `hypothesis` declares MPL-2.0 via the PEP-639 `License-Expression` field. The pinned `cyclonedx-bom==7.3.0` emits NO license entry for it without the `--PEP-639` flag, and that flag crashes on `structlog`. So `hypothesis` is invisible to the current SBOM regardless of denylist content.
- The single unavoidable runtime MPL-2.0 package fleet-wide is `certifi` (pulled transitively via `requests`), present in every Python app lock file. Any future hard-fail gate must allowlist it or every Python repo's CI breaks.

## Findings by dimension

### 1. Fleet-wide license exposure

True exposure concentrates almost entirely in one repo. Four of five sampled repos with lockfiles carry only MPL-2.0 and occasional LGPL, already covered by the `claude-config` baseline. The sole outlier is `image_detection` (its `pyproject.toml`): `PyMuPDF>=1.27.1` is AGPL-3.0 in the base graph; the `[ml]`/`[ood]` extras add `ultralytics`, `doclayout-yolo`, and `internetarchive` (all AGPL-3.0); `[dev]` pulls `dvc` which drags in GPL-2.0 transitives (grandalf, asyncssh, pygit2). The repo's own declared license is CC-BY-SA-4.0, inconsistent with the MIT fleet standard. Critically, PyMuPDF's CycloneDX entry uses a free-text `name` ("Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License"), not the SPDX `id`, so the existing AGPL denylist's exact-`id` match silently misses it. The fleet gate is `fail-on-forbidden-licenses: false` everywhere, so nothing fails regardless.

- Risks: AGPL-3.0 in `image_detection` base graph is HIGH if that repo is ever exposed as a network service; the gate is universally advisory-only and blind to the free-text `name` field; `ledgerbase` carries `semgrep` (LGPL-2.1) in its main (non-dev) dependency group, inflating its production closure unnecessarily.
- Recommendation: this is a real, repo-specific finding that does NOT require FOSSA. Replace PyMuPDF with `pypdfium2` (BSD/Apache, already in the venv) or document an Artifex commercial-license decision; move `semgrep` to `ledgerbase`'s dev group; arm the in-house gate with LGPL/MPL plus free-text `name` matching.

### 2. CI integration mechanics and cost

Integration is mechanically feasible but has four hard blockers: the free tier caps at 5 projects (34 Python repos need a paid plan, roughly $680/month at $20/project); the license-gating feature (`fossa test` non-zero exit) is paid-tier only, making FOSSA free-tier functionally equal to the existing job; the `FOSSA_API_KEY` must be a push-only org secret, and the `williaby` user account (26 repos) has no org so each repo needs the secret set individually or via a machine user; and `fossa test` adds a network call to FOSSA SaaS in the PR critical path that Trivy/OSV/Grype (which run fully on-runner) do not have. The correct integration slot, if ever adopted, is a new reusable `python-license.yml` in `ByronWilliamsCPA/.github` mirroring the `python-sbom.yml` caller pattern, NOT a job inside `python-ci.yml` (which would hit GitHub's 4-level nesting ceiling via the `python-standard-stack.yml` chain).

- Risks: partial 5-repo rollout violates the policy-execution-gap lesson; `fossa-cli` binary is downloaded at runtime (not cached, no pinned SHA) which is below the reliability bar of the SHA-pinned Trivy action; a FOSSA SaaS outage blocks or times out the gate.
- Recommendation: do not adopt now; if revisited post-paid-decision, use a separate `python-license.yml`, push-only org secret, `continue-on-error: true` with `--timeout 120` for the first 60 days, and pre-declare the three egress endpoints for future harden-runner block-mode.

### 3. Overlap and redundancy versus the 3 existing layers

At the time of this evaluation the fleet had four overlapping layers: (1) the `python-sbom.yml` `license-compliance` job (non-gating, GPL/AGPL `id`-only); (2) `dependency-review-action` (PR-diff only, inconsistently configured, 6 repos have no license gate at all); (3) REUSE/fsfe-action (own-source SPDX headers only, orthogonal to dependency licenses, irreplaceable by FOSSA); (4) Trivy + Grype + OSV-Scanner (vulnerability-only, zero license capability). Layer (2) was retired fleet-wide in 2026-09 when `dependency-review-action` began requiring paid GitHub Advanced Security; three layers remain. The current in-house script evaluates only 43% of license entries (126 of 295) because it reads only the SPDX `id` field; the 56% name-only and 3 expression entries are silently skipped, and it catches zero of the 8 copyleft packages. The three-step in-house fix (expand denylist to LGPL/MPL, also match `name` and `expression` fields, add a `pip-licenses` step for PEP-639 packages) closes the entire gap in one PR.

- Risks: enabling `fail-on-forbidden-licenses: true` without also fixing the `id`-only matching produces the same false-clean result; policy drift is accelerating across 17 config variations; the `cyclonedx-bom==7.3.0` PEP-639 bug is unresolved and hides `hypothesis` regardless of denylist quality.
- Recommendation: pursue the in-house upgrade now; FOSSA's only no-in-house-equivalent capabilities are license-compatibility-graph reasoning and automated NOTICE generation. Add FOSSA only when those are required, not merely convenient.

### 4. FOSSA policy design (if ever adopted)

If FOSSA is adopted, the policy must target the runtime shipping surface, not the full venv. `certifi` is the ONLY MPL-2.0 package in the runtime graph; all other copyleft packages are dev-group or unmanaged venv pollution. The design is five layers: (1) scope isolation via `uv export --no-dev` so dev deps never reach the scan (eliminates roughly 90% of false positives); (2) a three-tier ALLOW / FLAG-FOR-REVIEW / DENY decision table (DENY = GPL-2.0/3.0, AGPL-3.0, SSPL-1.0, Proprietary); (3) per-package ignores with justification for the known 10; (4) attribution/NOTICE generation for `certifi` only; (5) integration with the existing gates rather than replacement.

- Risks: full-venv SBOM scope inflation creates false positives; spurious venv installs flagged as managed; dual-license `tqdm` (MPL-2.0 AND MIT) requires a documented per-package ignore noting the MIT grant covers usage.
- Recommendation: this is the blueprint to apply IF condition 1, 2, or 3 above is ever met. It is not a reason to adopt now.

### 5. Standards-manifest integration

Two new checks should be added to `docs/standards-manifest.yaml` to drive the in-house repair. They were originally drafted as CI-078 and CI-079, but PR #188 landed CI-078 (the qlty-gate check) and reserved CI-079 for its ruleset companion first, so the checks were renumbered to CI-080 and CI-081. CI-080 gates the `sbom.yml` caller's denylist content to include LGPL/MPL; CI-081 gates `dependency-review.yml` presence of a `deny-licenses` or `allow-licenses` input. Both started at `severity: suggested` per the policy-execution-gap lesson, promoting to `important` only after their prerequisite sweeps (CI-058 for `sbom.yml` callers, CI-036 for `dependency-review.yml`) reached 100% of applicable repos. **CI-081 and its CI-036 prerequisite were retired in 2026-09** when `dependency-review-action` began requiring paid GitHub Advanced Security; CI-080 promotion is unaffected and still tracks the CI-058 `sbom.yml` sweep.

- Risks: promoting CI-080 before CI-058 reaches 100% generates correct-but-unactionable findings; the free-text `name` blind spot is a workflow-code fix, not just a manifest entry; Wave 3 `fail-on-forbidden-licenses: true` requires a `certifi` allowlist mechanism first or every Python repo breaks.
- Recommendation: paste the CI-080 entry (see the ready-to-paste YAML below; CI-081 was retired before fleet rollout, do not recreate it) and do not enable hard-fail until the allowlist mechanism and 100% CI-058 reach are confirmed.

### 6. Supply-chain and secret-management risk

FOSSA's OSS mode transmits dependency-graph metadata (package names, versions, resolved closure, git remote, branch, commit SHA) to FOSSA's US cloud, but not source code in standard mode. For the finance repos `llc-manager` and `family-office-portal`, their `uv.lock` files are already public on GitHub, so FOSSA adds no new exposure there; but the 4 private BWCPA repos (`xero-crypto`, `maester-tests`, `homelab-infra`, `taxdome`) would see net-new egress and require the paid Team tier. The `FOSSA_API_KEY` blast radius is bounded because no workflow uses `pull_request_target` (fork PRs do not receive secrets). The decisive finding: the reusable workflows use `egress-policy: audit`, so FOSSA's egress is unblocked today but becomes a migration blocker if the fleet moves to block mode. A further finding, not currently documented in the standards manifest: FOSSA does not natively recognize the org's REUSE 3.0 layout (LICENSES/ + REUSE.toml), so it would misreport every repo as having no detected own-source license. Record this as a blocker in any future FOSSA evaluation.

- Risks: private-repo egress (medium); REUSE layout incompatibility makes FOSSA's own-source reporting inaccurate (high for self-compliance); org-wide secret scope wider than needed; egress block-mode migration blocker; recurring paid-plan dependency for a free-tier-equivalent capability; policy logic stored in FOSSA UI contradicts the org's policy-as-code pattern.
- Recommendation: do not add FOSSA SaaS. Close the three blind spots in-house using `pip-licenses` plus `Trivy --scanners license` (both already in the Anchore/Trivy stack), zero new secrets, zero new egress. If a policy-as-code engine is later needed, adopt Syft plus grant before FOSSA. Record the REUSE incompatibility as a blocker in any future evaluation.

## Decision matrix: FOSSA versus the 3 existing layers

| Capability | FOSSA (free) | FOSSA (paid) | python-sbom license job (current) | python-sbom license job (repaired) | dependency-review-action (retired 2026-09, paid GHAS required) | REUSE / fsfe-action | Trivy+Grype+OSV |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Dependency license detection | Yes | Yes | Partial (id-only, 43%) | Yes (id+name+expr) | PR-diff only | No | No |
| Copyleft denylist (GPL/AGPL) | Yes | Yes | Yes (advisory) | Yes (gating) | Configurable, unused | No | No |
| LGPL/MPL coverage | Yes | Yes | No | Yes | Configurable, unused | No | No |
| PEP-639 / free-text license fields | Yes | Yes | No | Yes (+pip-licenses) | Partial | No | No |
| PR-time gating | No | Yes | Advisory (false everywhere) | Yes | Yes | Yes | Yes |
| Full-closure scan (not just PR diff) | Yes | Yes | Yes | Yes | No | No | Yes (vuln) |
| License-compatibility graph reasoning | No | Yes | No | No | No | No | No |
| Automated NOTICE/attribution file | No | Yes | No | Partial (pip-licenses) | No | No | No |
| Own-source SPDX header compliance | No (REUSE-blind) | No (REUSE-blind) | No | No | No | Yes (irreplaceable) | No |
| Vulnerability scanning | Single DB | Single DB | No | No | Severity gate | No | Yes (3 DBs) |
| Policy as version-controlled code | No (UI) | No (UI) | Yes (YAML) | Yes (YAML) | Yes (YAML) | Yes (TOML) | Yes (YAML) |
| New external SaaS in PR critical path | Yes | Yes | No | No | No (GitHub-native) | No | No |
| Marginal cost | Free (5-repo cap) | ~$680/mo | $0 | $0 | $0 | $0 | $0 |

The repaired in-house column matches or beats FOSSA-free on every row that matters to this fleet, and matches FOSSA-paid on everything except the two capabilities (compatibility graph, automated NOTICE) that the fleet does not currently need.

## The cheaper in-house alternative (the DEFER path)

Execute these in order. The whole detection-and-gating gap closes in approximately one PR to `python-sbom.yml` plus one manifest entry (CI-080; the second candidate, CI-081, was retired before rollout, see below), with zero new secrets, zero new egress, and zero recurring cost.

1. Repair the `license-compliance` script in `ByronWilliamsCPA/.github` at `.github/workflows/python-sbom.yml`: (a) expand the default `forbidden-licenses` to add `LGPL-2.0-only`, `LGPL-2.0-or-later`, `LGPL-2.1-only`, `LGPL-2.1-or-later`, `LGPL-3.0-only`, `LGPL-3.0-or-later`, `MPL-2.0`; (b) match the CycloneDX `name` and `expression` fields by substring, not only the SPDX `id`; (c) add a `pip-licenses --format=json` step (or `Trivy --scanners license`) to catch PEP-639 packages like `hypothesis` that `cyclonedx-bom==7.3.0` misses entirely.
2. Add a per-package allowlist mechanism (YAML in the caller or in the reusable workflow) seeded with `certifi` (MPL-2.0, transitive via `requests`, present in every Python repo). This is the precondition for any hard-fail gate.
3. ~~Add `deny-licenses` (GPL-2.0/3.0, AGPL-3.0 minimum) to `dependency-review.yml` for an early PR-time signal complementing the SBOM gate.~~ Moot as of 2026-09: `dependency-review.yml` was removed fleet-wide (`actions/dependency-review-action` now requires paid GitHub Advanced Security). The SBOM gate (step 1, `sbom.yml`, running on relevant PRs and pushes) is the fleet's sole license-policy scan; it is not currently an enforcement gate, since its caller sets `fail-on-forbidden-licenses: false`. Step 6 below tracks when that gate is armed.
4. Repo-specific remediation independent of tooling: in `image_detection`, replace PyMuPDF with `pypdfium2` or document the Artifex commercial-license decision; in `ledgerbase`, move `semgrep` from the main to the dev dependency group.
5. Clean the `claude-config` venv: remove the spurious unmanaged installs `tqdm`, `psycopg2-binary`, `python-gitlab` so they stop appearing in the SBOM.
6. Roll out via the staged plan: Wave 1 (now) suggested/advisory, no CI failures; Wave 2 promote to `important` after CI-058 reaches 100% of the 30 Python repos; Wave 3 enable `fail-on-forbidden-licenses: true` only after the `certifi` allowlist is confirmed deployed.

Defer FOSSA, Syft+grant, and any SaaS until a hard attribution or custom-license-scanning requirement actually emerges. If a policy-as-code engine is later needed, prefer Syft plus grant (already in the Anchore OSS stack) over FOSSA.

## Standards-manifest entries (applied)

**CI-080** (the `sbom.yml` caller's `forbidden-licenses` denylist must include
LGPL and MPL, not GPL/AGPL only) is the sole live manifest entry from this
evaluation; a second candidate, **CI-081** (the `dependency-review.yml` caller
must declare `deny-licenses` or `allow-licenses`), was drafted alongside it but
retired before fleet rollout, see below. Both were renumbered from the
originally proposed CI-078/CI-079 after PR #188 took CI-078 (the qlty-gate
check) and reserved CI-079 for its ruleset companion. See the live definitions
in `docs/standards-manifest.yaml` for the authoritative `verify` logic; the
canonical entries are the single source of truth and supersede any earlier
draft. CI-080 starts at `severity: suggested` and promotes to `important` only
after its prerequisite sweep (CI-058) reaches 100% of applicable repos.
CI-080's required LGPL/MPL set covers the LGPL-2.1 variants so that `semgrep`
(the one concrete LGPL-2.1 package observed in the fleet) is not missed.

**CI-081 was retired in 2026-09** (deprecated stub, ID not reused) alongside
its CI-036 prerequisite: `actions/dependency-review-action` now requires paid
GitHub Advanced Security, `dependency-review.yml` was removed fleet-wide, and
a check gating a workflow that no longer exists would fail every repo.
CI-080 is unaffected and remains the fleet's license-policy control.
