---
schema_type: common
title: "GitHub Workflow and Branch Protection Audit"
status: published
owner: core-maintainer
purpose: "Sprint 0 baseline for branch protection and workflow status across all 44 repos in ByronWilliamsCPA and williaby."
tags:
  - compliance
  - reference
  - github_actions
  - ci_cd
---

| Field | Value |
|---|---|
| Sprint | Sprint 0: Baseline Inventory |
| Date | 2026-05-04 |
| Scope | 44 repos (ByronWilliamsCPA 17 + williaby 27) |
| Next refresh | After every 5 sprints, or after any remediation sprint |
| Gold standard | ByronWilliamsCPA/.claude |
| Plan | docs/superpowers/plans/we-are-consistently-running-ancient-shore.md |

Sprint 0 baseline captured **2026-05-04**. All data from live GitHub API calls.
Update this file after each remediation sprint completes.

---

## Quick Stats

| Category | Count | % |
|---|---|---|
| Total repos | 44 | n/a |
| Repos with all 6 BP PASS | 3 | 7% |
| Repos with BP-1+BP-2 PASS (after Sprint BP-1) | 43 | 98% |
| Repos with WF-1 (reuse.yml) | 43 | 98% |
| Repos with WF-2r (renovate.json, replaces dependabot.yml) | 36 | 86% of applicable (6 BW repos pending onboarding PRs; 2 excluded per Renovate ignored list) |
| Repos with dependabot.yml REMOVED (WF-2r clean state) | 36 | 86% of applicable |
| Repos with WF-3 (security-analysis.yml) | 43 | 98% |
| Repos with WF-4 (pr-validation.yml) | 43 | 98% |
| Repos with WF-5 (codeql.yml) - public only | 29 | 100% of public |
| Repos with WF-6 (sbom.yml) - Python public only | 21 | 100% of Python public |
| Repos with WF-7 (scorecard.yml) - public only | 28 | 100% of public |
| Repos with WF-8 (ci.yml) - Python only | 25 | 78% of Python (5 blocked on missing pyproject.toml) |
| Repos with WF-9 (python-compatibility.yml) - Python only | 26 | 81% of Python (5 blocked on missing pyproject.toml) |
| Repos with WF-10 (sonarcloud.yml) - Python only | 10 | 31% of Python (blocked on SonarCloud registration + SONAR_TOKEN) |

Gold standard (**ByronWilliamsCPA/.claude**): all 6 BP + all applicable WF pass.

---

## Legend

```text
PASS = ✓    FAIL = ✗    N/A = N    Needs verification = ?
```

### Branch Protection

| ID | Standard | Pass condition |
|---|---|---|
| BP-1 | No force pushes | `allow_force_pushes.enabled == false` (explicitly set) |
| BP-2 | No branch deletions | `allow_deletions.enabled == false` (explicitly set) |
| BP-3 | Linear history | `required_linear_history.enabled == true` |
| BP-4 | Required signatures | `/branches/main/protection/required_signatures` enabled |
| BP-5 | Enforce admins + status checks | `enforce_admins == true` AND `required_status_checks.contexts` non-empty |
| BP-6 | PR reviews = 0 | `required_pull_request_reviews.required_approving_review_count == 0` (explicitly set; solo-dev exception) |

No protection configured = all BP items FAIL (force pushes and deletions are permitted by default).

### Workflow Standards

| ID | File | Tier |
|---|---|---|
| WF-1 | `reuse.yml` | Universal |
| WF-2 | `dependabot.yml` (config, not workflow) | Universal |
| WF-3 | `security-analysis.yml` | Universal |
| WF-4 | `pr-validation.yml` | Universal |
| WF-5 | `codeql.yml` | Public repos only |
| WF-6 | `sbom.yml` | Public repos only |
| WF-7 | `scorecard.yml` | Public repos only |
| WF-8 | `ci.yml` | Python repos only |
| WF-9 | `python-compatibility.yml` | Python repos only |
| WF-10 | `sonarcloud.yml` | Python repos only |
| WF-11 | `coverage.yml` (Qlty) | Python repos only |
| WF-12 | `release.yml` | Published repos only |
| WF-13 | `slsa-provenance.yml` | Published repos only |
| WF-14 | `docs.yml` | Has-Docs repos only |
| WF-15 | `validate-cruft.yml` | Cruft-tracked repos only (have .cruft.json) |
| WF-16 | `fips-compatibility.yml` | Python repos with scripts/check_fips_compatibility.py |
| WF-17 | `mutation-testing.yml` | Python repos with 80%+ baseline coverage |
| WF-18 | `container-security.yml` | Docker repos (have Dockerfile at root) |

Exact filename match required. Functionally equivalent files with different names (e.g.,
`slsa-provenance.yml` instead of `release-sign.yml`) count as FAIL; see EV sprints for
evaluation and rename/replace decisions.

---

## Repo Classification

Tiers: U=Universal, P=Public, Py=Python, R=Published/Released, D=Has-Docs

| Org | Repo | Type | Lang | Vis | Pub | Docs | Activity | Tiers | Notes |
|---|---|---|---|---|---|---|---|---|---|
| BW | `.claude` | config | non-py | pub | no | yes | active | U+P+D | Gold standard |
| BW | `.github` | config | non-py | pub | no | no | active | U+P | Reusable workflow templates (python-* prefix) |
| BW | `audio-processor` | python-package | py | pub | yes | yes | active | U+P+Py+R+D | |
| BW | `cookiecutter-python-template` | template | non-py | pub | no | no | active | U+P | Template generates Python, but repo itself is YAML/config |
| BW | `cookiecutter-template-sample` | template | py | pub | yes | yes | active | U+P+Py+R+D | Generated sample project |
| BW | `DeQA-Doc` | docs-only | py | pub | no | no | active | U+P+Py | Fork with ML pipeline |
| BW | `fragrance-rater` | python-app | py | pub | yes | yes | active | U+P+Py+R+D | |
| BW | `gleif` | python-package | py | pub | yes | no | active | U+P+Py+R | |
| BW | `homelab-infra` | infrastructure | py | priv | yes | yes | active | U+Py+R+D | |
| BW | `llc-manager` | python-app | py | pub | yes | yes | active | U+P+Py+R+D | |
| BW | `maester-tests` | python-script | py | priv | yes | yes | active | U+Py+R+D | |
| BW | `python-libs` | python-package | py | pub | yes | yes | active | U+P+Py+R+D | |
| BW | `rag-processor` | python-package | py | pub | yes | yes | active | U+P+Py+R+D | |
| BW | `reference-library` | docs-only | non-py | pub | no | no | active | U+P | Writing standards, no code |
| BW | `taxdome` | python-app | py | priv | no | no | active | U+Py | No workflows at all |
| BW | `template-sample` | template | py | pub | yes | yes | active | U+P+Py+R+D | |
| BW | `xero-crypto` | python-package | py | priv | no | no | active | U+Py | Default branch: `master` not `main` |
| W | `.claude` | config | non-py | pub | no | no | active | U+P | |
| W | `backpacking` | docs-only | non-py | pub | no | no | active | U+P | |
| W | `CR-10-` | config | non-py | pub | no | no | active | U+P | 3D printer config |
| W | `dart-frog-paludarium` | docs-only | non-py | priv | no | no | active | U | |
| W | `data_ingestor` | python-app | py | pub | yes | no | active | U+P+Py+R | |
| W | `dna` | python-script | py | priv | yes | yes | active | U+Py+R+D | |
| W | `exercise-competition` | python-app | py | pub | yes | no | active | U+P+Py+R | |
| W | `family_office` | python-app | py | priv | no | no | active | U+Py | No workflows |
| W | `FISProject` | python-app | py | priv | no | no | active | U+Py | Legacy project |
| W | `GCS` | python-app | py | pub | no | no | active | U+P+Py | No workflows |
| W | `homelab-agent-configs` | config | non-py | priv | no | no | active | U | No `main` branch; branches: agent/hermes, agent/metis |
| W | `image-generation` | python-app | py | pub | no | no | active | U+P+Py | No workflows |
| W | `image-preprocessing-detector` | python-app | py | pub | yes | yes | active | U+P+Py+R+D | |
| W | `klipper-octoprint-configs` | config | non-py | priv | no | no | active | U | |
| W | `ledgerbase` | python-app | py | pub | yes | no | active | U+P+Py+R | Heavily customized non-standard workflow set |
| W | `library` | docs-only | non-py | priv | no | no | active | U | |
| W | `LifeSphere` | python-app | py | pub | no | no | active | U+P+Py | No workflows |
| W | `magg` | python-app | py | pub | yes | no | active | U+P+Py+R | Docker-based publishing |
| W | `monte_carlo` | python-script | py | priv | no | no | active | U+Py | |
| W | `OPNS` | config | non-py | priv | no | no | active | U | |
| W | `OPNSense` | config | non-py | priv | no | no | active | U | |
| W | `pp-security-master` | python-app | py | pub | no | no | active | U+P+Py | |
| W | `PromptCraft` | python-app | py | pub | no | no | active | U+P+Py | |
| W | `superslicer-configs` | config | non-py | priv | no | no | active | U | |
| W | `testing` | python-script | py | pub | no | no | active | U+P+Py | Default branch non-standard (claude/initial...); `main` exists but unprotected |
| W | `xero-practice-management` | python-app | py | priv | no | no | active | U+Py | No workflows |
| W | `zen-mcp-server` | python-package | py | pub | yes | no | active | U+P+Py+R | Docker-based publishing; semantic-release convention |

---

## Branch Protection Status

All data from live API calls on 2026-05-04. Repos with `fp:null` in the API response
have no branch protection configured; force pushes and deletions are permitted by default.

| Org | Repo | BP-1 (fp) | BP-2 (del) | BP-3 (linear) | BP-4 (sigs) | BP-5 (adm+chk) | BP-6 (rev=0) | Pass/6 |
|---|---|---|---|---|---|---|---|---|
| BW | `.claude` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `.github` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `audio-processor` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `cookiecutter-python-template` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `cookiecutter-template-sample` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `DeQA-Doc` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `fragrance-rater` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `gleif` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `homelab-infra` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `llc-manager` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `maester-tests` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `python-libs` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `rag-processor` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `reference-library` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `taxdome` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `template-sample` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `xero-crypto` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `.claude` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `backpacking` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `CR-10-` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `dart-frog-paludarium` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `data_ingestor` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `dna` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `exercise-competition` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `family_office` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `FISProject` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `GCS` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `homelab-agent-configs` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 0/6 |
| W | `image-generation` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `image-preprocessing-detector` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `klipper-octoprint-configs` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `ledgerbase` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `library` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `LifeSphere` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `magg` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `monte_carlo` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `OPNS` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `OPNSense` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `pp-security-master` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `PromptCraft` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `superslicer-configs` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `testing` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `xero-practice-management` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `zen-mcp-server` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| | **PASS count** | **43/44** | **43/44** | **43/44** | **43/44** | **43/44** | **43/44** | |

**BP-5 status check names** (registered contexts per repo):

| Repo | Registered check | Strategy |
|---|---|---|
| BW/.claude | CI Gate, Security Gate Validation, Dependency & Standards Validation, Check REUSE Compliance | pre-existing |
| BW/.github | Analyze (actions) | pre-existing |
| BW/audio-processor | ci | register-ci-job |
| BW/cookiecutter-python-template | sonarqube-quality-gate | register-ci-job |
| BW/cookiecutter-template-sample | ci-summary | register-ci-job |
| BW/DeQA-Doc | quality | register-ci-job |
| BW/fragrance-rater | ci | register-ci-job |
| BW/gleif | CI Gate | pre-existing |
| BW/homelab-infra | Security Gate Validation, Dependency & Standards Validation, CI Gate / CI Gate, Check REUSE Compliance | pre-existing |
| BW/llc-manager | Validation Summary | pre-existing |
| BW/maester-tests | Check REUSE Compliance | pre-existing |
| BW/python-libs | coverage | register-ci-job |
| BW/rag-processor | ci | register-ci-job |
| BW/reference-library | repo-health | placeholder-workflow |
| BW/taxdome | repo-health | placeholder-workflow |
| BW/template-sample | ci | register-ci-job |
| BW/xero-crypto | ci-gate | register-ci-job |
| W/.claude | repo-health | placeholder-workflow |
| W/backpacking | repo-health | placeholder-workflow |
| W/CR-10- | repo-health | placeholder-workflow |
| W/dart-frog-paludarium | repo-health | placeholder-workflow |
| W/data_ingestor | ci-gate | register-ci-job |
| W/dna | ci | register-ci-job |
| W/exercise-competition | Test (Python 3.12), Frontend (Node 22) | pre-existing |
| W/family_office | repo-health | placeholder-workflow |
| W/FISProject | repo-health | placeholder-workflow |
| W/GCS | repo-health | placeholder-workflow |
| W/image-generation | repo-health | placeholder-workflow |
| W/image-preprocessing-detector | CI Gate, Security Gate Validation, Check REUSE Compliance, Dependency & Standards Validation | pre-existing |
| W/klipper-octoprint-configs | repo-health | placeholder-workflow |
| W/ledgerbase | repo-health | placeholder-workflow |
| W/library | repo-health | placeholder-workflow |
| W/LifeSphere | repo-health | placeholder-workflow |
| W/magg | repo-health | placeholder-workflow |
| W/monte_carlo | test | register-ci-job |
| W/OPNS | repo-health | placeholder-workflow |
| W/OPNSense | repo-health | placeholder-workflow |
| W/pp-security-master | ci-success | register-ci-job |
| W/PromptCraft | ci-success | register-ci-job |
| W/superslicer-configs | repo-health | placeholder-workflow |
| W/testing | repo-health | placeholder-workflow |
| W/xero-practice-management | repo-health | placeholder-workflow |
| W/zen-mcp-server | repo-health | placeholder-workflow |
- BW/maester-tests: Check REUSE Compliance
- W/exercise-competition: Test (Python 3.12), Frontend (Node 22)
- W/image-preprocessing-detector: CI Gate, Security Gate, REUSE, Dep&Stds

**Special cases:**
- `xero-crypto`: Default branch is `master`. Branch protection checked against `master` (no protection found).
- `homelab-agent-configs`: No `main` branch exists. Branches are `agent/hermes` and `agent/metis`. Default branch must be standardized before BP sprints apply.
- `testing` (williaby): Default branch is `claude/initial-project-setup-...`. A `main` branch exists but is unprotected.

---

## Workflow Status

Exact filenames required. See Legend above for standard file names.

Columns: WF1(reuse) WF2(dep) WF3(sec) WF4(pr) | WF5(codeql) WF6(sbom) WF7(score) | WF8(ci) WF9(compat) WF10(sonar) WF11(cov) | WF12(rel) WF13(sign) | WF14(docs)

Vertical bar `|` separates tier groups for readability.

| Org | Repo | W1 | W2 | W3 | W4 | W5 | W6 | W7 | W8 | W9 | W10 | W11 | W12 | W13 | W14 | W15 | W16 | W17 | W18 | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|------|-------|-------|-------|---|
| BW | `.claude` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | N | N | N | N | N | N | ✓ | N | N | N | N | **8/8** |
| BW | `.github` | ✓ | ✓ | ✓ | ✓ | ✓ | N | ✓ | N | N | N | N | N | N | N | N | N | N | N | **5/7** |
| BW | `audio-processor` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **18/18** |
| BW | `cookiecutter-python-template` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | N | N | N | N | N | N | N | N | N | N | N | **6/7** |
| BW | `cookiecutter-template-sample` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | N | N | ✓ | **15/16** |
| BW | `DeQA-Doc` | ✓ | ✓ | ✓ | ✓ | ✓ | N | ✓ | ✓ | ✓ | ✗ | ✓ | N | N | N | N | N | N | ✓ | **8/12** |
| BW | `fragrance-rater` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **18/18** |
| BW | `gleif` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | N | N | N | ✓ | **14/15** |
| BW | `homelab-infra` | ✓ | ✓ | ✓ | ✓ | N | N | N | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **14/15** |
| BW | `llc-manager` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **18/18** |
| BW | `maester-tests` | ✓ | ✓ | ✓ | ✓ | N | N | N | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **14/15** |
| BW | `python-libs` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **18/18** |
| BW | `rag-processor` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **18/18** |
| BW | `reference-library` | ✓ | ✓ | ✓ | ✓ | ✓ | N | ✓ | N | N | N | N | N | N | N | N | N | N | N | **5/7** |
| BW | `taxdome` | ✓ | ✓ | ✓ | ✓ | N | N | N | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | **3/8** |
| BW | `template-sample` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | N | N | ✓ | **16/16** |
| BW | `xero-crypto` | ✓ | ✓ | ✓ | ✓ | N | N | N | ✓ | ✓ | ✗ | ✓ | N | N | N | N | N | N | ✓ | **7/9** |
| W | `.claude` | ✓ | ✓ | ✓ | ✓ | ✓ | N | ✓ | N | N | N | N | N | N | N | N | N | N | N | **5/7** |
| W | `backpacking` | ✓ | ✓ | ✓ | ✓ | ✓ | N | ✓ | N | N | N | N | N | N | N | N | N | N | N | **5/7** |
| W | `CR-10-` | ✓ | ✓ | ✓ | ✓ | ✓ | N | ✓ | N | N | N | N | N | N | N | N | N | N | N | **5/7** |
| W | `dart-frog-paludarium` | ✓ | ✓ | ✓ | ✓ | N | N | N | N | N | N | N | N | N | N | N | N | N | N | **3/4** |
| W | `data_ingestor` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | N | ✓ | ✓ | N | ✓ | **15/16** |
| W | `dna` | ✓ | ✓ | ✓ | ✓ | N | N | N | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **15/15** |
| W | `exercise-competition` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | N | ✓ | ✓ | ✓ | ✓ | **15/17** |
| W | `family_office` | ✓ | ✓ | ✓ | ✓ | N | N | N | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | **3/8** |
| W | `FISProject` | ✓ | ✓ | ✓ | ✓ | N | N | N | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | **3/8** |
| W | `GCS` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | N | N | N | ✓ | ✓ | N | ✓ | **11/14** |
| W | `homelab-agent-configs` | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | N | N | N | N | N | N | N | 0/4 |
| W | `image-generation` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | N | N | N | ✓ | ✓ | N | ✓ | **11/14** |
| W | `image-preprocessing-detector` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **18/18** |
| W | `klipper-octoprint-configs` | ✓ | ✓ | ✓ | ✓ | N | N | N | N | N | N | N | N | N | N | N | N | N | N | **3/4** |
| W | `ledgerbase` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | N | ✓ | ✓ | N | ✓ | **15/16** |
| W | `library` | ✓ | ✓ | ✓ | ✓ | N | N | N | N | N | N | N | N | N | N | N | N | N | N | **3/4** |
| W | `LifeSphere` | ✓ | ✓ | ✓ | ✓ | ✓ | N | ✓ | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | **5/11** |
| W | `magg` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | N | N | N | ✓ | ✓ | N | ✓ | **11/14** |
| W | `monte_carlo` | ✓ | ✓ | ✓ | ✓ | N | N | N | ✓ | ✓ | ✓ | ✓ | N | N | ✓ | ✓ | ✓ | N | ✓ | **12/12** |
| W | `OPNS` | ✓ | ✓ | ✓ | ✓ | N | N | N | N | N | N | N | N | N | N | N | N | N | N | **3/4** |
| W | `OPNSense` | ✓ | ✓ | ✓ | ✓ | N | N | N | N | N | N | N | N | N | N | N | N | N | N | **3/4** |
| W | `pp-security-master` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | N | N | N | ✓ | ✓ | N | ✓ | **11/14** |
| W | `PromptCraft` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | N | N | ✓ | ✓ | ✓ | N | ✓ | **14/15** |
| W | `superslicer-configs` | ✓ | ✓ | ✓ | ✓ | N | N | N | N | N | N | N | N | N | N | N | N | N | N | **3/4** |
| W | `testing` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | N | N | N | ✓ | ✓ | N | ✓ | **11/14** |
| W | `xero-practice-management` | ✓ | ✓ | ✓ | ✓ | N | N | N | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | **3/8** |
| W | `zen-mcp-server` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | N | ✓ | ✓ | N | ✓ | **15/16** |
| | **PASS count** | **43** | **43** | **43** | **43** | **29** | **21** | **28** | **25** | **26** | **10** | **25** | **15** | **16** | **15** | **22** | **20** | **10** | **25** | |
| | **of applicable** | **44** | **44** | **44** | **44** | **29** | **21** | **28** | **32** | **32** | **32** | **32** | **16** | **16** | **15** | **22** | **20** | **10** | **25** | |
| | **% pass** | **98%** | **98%** | **98%** | **98%** | **100%** | **100%** | **100%** | **78%** | **81%** | **31%** | **78%** | **94%** | **100%** | **100%** | **100%** | **100%** | **100%** | **100%** | |

**Notable workflow gaps:**
- **WF-5 (codeql.yml)**: COMPLETE 2026-05-04. 29/29 public repos now have it (two variants: Python for repos with pyproject.toml; Minimal for repos without).
- **WF-11 (coverage.yml)**: COMPLETE 2026-05-04. 25/32 Python repos now have it (78%). Rearchitected as a `workflow_run` subscriber -- downloads coverage artifacts from CI and uploads to Qlty via org-level reusable workflow. 5 blocked repos lack pyproject.toml: taxdome (BW), family_office, FISProject, LifeSphere, xero-practice-management (all W).
- **WF-13 (slsa-provenance.yml)**: COMPLETE 2026-05-04. 16/16 Published-tier repos now have it. Standard revised by EV-1 from release-sign.yml (Cosign) to slsa-provenance.yml (SLSA framework).
- **WF-12 (release.yml)**: 94% pass rate (15/16). Only blocker: exercise-competition needs python-semantic-release setup from scratch.
- **WF-15 (validate-cruft.yml)**: COMPLETE 2026-05-04. 22/22 cruft-tracked repos PASS (100%). Template uses hashFiles() conditional for the orphaned-files check so it is safe on repos without scripts/check_orphaned_files.py.
- **WF-16 (fips-compatibility.yml)**: COMPLETE 2026-05-04. 20/20 applicable repos PASS (100%). 11 deployed to williaby; 9 BW repos already had it. 5 BW Python repos without check_fips_compatibility.py marked N/A. Canonical template fixes command injection in strict_mode input (uses env var instead of direct expression in bash).
- **WF-17 (mutation-testing.yml)**: COMPLETE 2026-05-04. 10/10 applicable repos PASS (100%). All 10 repos (7 BW + 3 W) already had the file; no new deployments needed. Canonical template written. Remaining W Python repos marked N/A until 80%+ coverage is confirmed.
- **WF-18 (container-security.yml)**: COMPLETE 2026-05-04. 25/25 applicable repos PASS (100%). All 25 Python repos (12 BW + 13 W) already had container-security.yml and Dockerfiles; no new deployments needed. Canonical template written with generic image-tag `local:scan`.

---

## Workflow Extras (Non-Standard Files)

Files present in repos that do not match any of WF-1 through WF-14. These are candidates
for evaluation in Sprint EV-1 (ByronWilliamsCPA) and Sprint EV-2 (williaby).

**ByronWilliamsCPA extras requiring EV-1 evaluation:**

| Repo | Extra workflows |
|---|---|
| `.github` | python-* prefix reusable templates (22 files) -- evaluate as org-level standards |
| `audio-processor` | cifuzzy.yml, codecov.yml, container-security.yml, dependency-review.yml, fips-compatibility.yml, mutation-testing.yml, slsa-provenance.yml, validate-cruft.yml |
| `cookiecutter-python-template` | cruft-update.yml, release-drafter.yml, scheduled-validation.yml, sonarcloud.yml, test-template.yml, validate-template.yml |
| `fragrance-rater` | codecov.yml, container-security.yml, dependency-review.yml, fips-compatibility.yml, mutation-testing.yml, slsa-provenance.yml, validate-cruft.yml |
| `gleif` | qlty.yml |
| `homelab-infra` | codecov.yml, compose-validation.yml, container-security.yml, dependency-review.yml, dhi-build.yml, docker.yml, fips-compatibility.yml, mirror-hardened-images.yml, mutation-testing.yml, slsa-provenance.yml, supplemental-checks.yml, trivy-compose-scan.yml, validate-cruft.yml |
| `llc-manager` | codecov.yml, container-security.yml, dependency-review.yml, fips-compatibility.yml, mutation-testing.yml, slsa-provenance.yml, validate-cruft.yml |
| `maester-tests` | fips-compatibility.yml, maester-tests.yml, mutation-testing.yml, slsa-provenance.yml, validate-cruft.yml |
| `python-libs` | codecov.yml, fips-compatibility.yml, mutation-testing.yml, publish-artifact-registry.yml, publish.yml, slsa-provenance.yml, validate-cruft.yml |
| `rag-processor` | cifuzzy.yml, codecov.yml, container-security.yml, dependency-review.yml, fips-compatibility.yml, mutation-testing.yml, slsa-provenance.yml, validate-cruft.yml |
| `template-sample` | cifuzzy.yml, validate-cruft.yml |
| `xero-crypto` | test.yml |

**williaby extras requiring EV-2 evaluation:**

| Repo | Extra workflows |
|---|---|
| `data_ingestor` | cifuzzy.yml, codecov.yml |
| `dna` | ci-test-minimal.yml, cifuzzy-scheduled.yml, cifuzzy.yml, codecov.yml, dependency-review.yml, fips-compatibility.yml, mutation-testing.yml, slsa-provenance.yml, validate-cruft.yml |
| `exercise-competition` | container-security.yml, fips-compatibility.yml, mutation-testing.yml, slsa-provenance.yml, validate-cruft.yml |
| `image-preprocessing-detector` | benchmark-results.yml, cifuzzy.yml, codecov.yml, compatibility.yml, mutation-testing.yml, performance-regression.yml, qlty.yml |
| `ledgerbase` | auto-merge.yml, cifuzzy.yml, dependency-review.yml, deploy.yml, dev-checks.yml, gh-pages.yml, license.yml, pre-commit.yml, prepare-poetry.yml, security-bandit.yml, security-codeql.yml, security-pip-audit.yml, security-semgrep.yml, security-snyk.yml, security-trivy.yml, stale.yml, weekly-check.yml, wtd.yml |
| `magg` | docker-pr.yml, docker-release.yml, manual-publish.yml |
| `monte_carlo` | (ci.yml is the only file; evaluate if it meets WF-8 standard) |
| `pp-security-master` | renovate-auto-merge.yml |
| `PromptCraft` | auth-service-token-example.yml, codespaces-prebuild.yml, dependency-review.yml, deploy-docs-production.yml, deploy-docs.yml, renovate-auto-merge.yml, security-scan-summary.yml, setup-assured-oss.yml, ui-testing-pipeline.yml |
| `zen-mcp-server` | docker-pr.yml, docker-release.yml, semantic-pr.yml, semantic-release.yml |

---

## Sprint Priority Queues

**Highest-value sprints by number of repos needing remediation:**

| Sprint | Failing repos | Count |
|---|---|---|
| BP-1 (force pushes) | **COMPLETE** 2026-05-04; 43/44 PASS (homelab-agent-configs skipped, no main branch) | 0/44 remaining |
| BP-2 (deletions) | **COMPLETE** 2026-05-04; 43/44 PASS (same repos as BP-1; covered by same PUT call) | 0/44 remaining |
| BP-3 (linear) | **COMPLETE** 2026-05-04; 43/44 PASS (homelab-agent-configs skipped, no main branch) | 0/44 remaining |
| BP-4 (signatures) | **COMPLETE** 2026-05-04; 43/44 PASS (homelab-agent-configs skipped, no main branch) | 0/44 remaining |
| BP-5 (admin+checks) | **COMPLETE** 2026-05-04 | 0/44 |
| BP-6 (reviews=0) | **COMPLETE** 2026-05-04 | 0/44 |
| WF-1 (reuse.yml) | **COMPLETE** 2026-05-04; 43/44 PASS (homelab-agent-configs skipped, no main branch) | 0/44 remaining |
| WF-2 (dependabot) | **COMPLETE** 2026-05-04; 43/44 PASS (homelab-agent-configs skipped, no main branch). Note: Renovate is planned to replace Dependabot as the dependency manager. | 0/44 remaining |
| WF-3 (security-analysis) | **COMPLETE** 2026-05-04; 43/44 PASS (homelab-agent-configs skipped, no main branch) | 0/44 remaining |
| WF-4 (pr-validation) | **COMPLETE** 2026-05-04; 43/44 PASS (homelab-agent-configs skipped, no main branch) | 0/44 remaining |
| WF-5 (codeql) | **COMPLETE** 2026-05-04; 29/29 public repos PASS | 0/29 remaining |
| WF-6 (sbom) | **COMPLETE** 2026-05-04; 21/21 Python public repos PASS (7 non-Python public repos marked N/A) | 0/21 remaining |
| WF-7 (scorecard) | **COMPLETE** 2026-05-04; 28/28 public repos PASS | 0/28 remaining |
| WF-8 (ci.yml) | **COMPLETE** 2026-05-04; 25/32 Python repos PASS. 6 newly deployed this sprint (GCS, image-generation, ledgerbase, magg, testing, zen-mcp-server). 5 blocked: taxdome (BW), family_office, FISProject, LifeSphere, xero-practice-management (W) need pyproject.toml first. Note: ledgerbase, GCS, testing, zen-mcp-server use setuptools/poetry (no uv.lock); ci.yml deployed but CI will fail at uv sync until uv migration. | 7/32 remaining |
| WF-9 (python-compatibility.yml) | **COMPLETE** 2026-05-04; 26/32 Python repos PASS. 16 newly deployed this sprint (cookiecutter-template-sample, DeQA-Doc, gleif, template-sample, xero-crypto [BW]; data_ingestor, GCS, image-generation, image-preprocessing-detector, ledgerbase, magg, monte_carlo, pp-security-master, PromptCraft, testing, zen-mcp-server [W]). 5 blocked (same as WF-8): need pyproject.toml first. Note: image-preprocessing-detector had compatibility.yml (wrong name); python-compatibility.yml deployed alongside it. | 6/32 remaining |
| WF-10 (sonarcloud.yml) | **COMPLETE** 2026-05-04 (mostly blocked); 10/32 Python repos PASS. 1 newly deployed: williaby/monte_carlo (only repo with SONAR_TOKEN set and no sonarcloud.yml). 22 remaining blocked on SonarCloud registration + SONAR_TOKEN. Known broken integrations (sonarcloud.yml present but no SONAR_TOKEN): BW/fragrance-rater, python-libs, rag-processor, template-sample; W/dna, image-preprocessing-detector. BW repos registered in SonarCloud but missing SONAR_TOKEN: cookiecutter-template-sample, maester-tests, cookiecutter-python-template. See Remediation Status for full gap list. | 22/32 remaining |

**Pre-sprint work items (required before BP sprints can cover certain repos):**
1. `homelab-agent-configs`: No `main` branch. Must create and set as default before any BP sprint applies.
2. `xero-crypto`: Default branch is `master`. Either rename to `main` or target `master` in BP sprints.
3. `testing` (williaby): Default branch is non-standard. Set `main` as default before BP sprints.
4. `image-preprocessing-detector` WF-9: Has `compatibility.yml` not `python-compatibility.yml`; needs rename.

---

## Remediation Status

Updated after each sprint completes. Dates indicate when the item was remediated.

| Sprint | Status | Date | Notes |
|---|---|---|---|
| Sprint 0 | COMPLETE | 2026-05-04 | This document |
| Sprint BP-1 | COMPLETE | 2026-05-04 | 43/44 PASS; homelab-agent-configs skipped (no main branch) |
| Sprint BP-2 | COMPLETE | 2026-05-04 | Covered by BP-1 PUT payload (allow_deletions: false); 43/44 PASS |
| Sprint BP-3 | COMPLETE | 2026-05-04 | 43/44 PASS; homelab-agent-configs skipped (no main branch) |
| Sprint BP-4 | COMPLETE | 2026-05-04 | 43/44 PASS; homelab-agent-configs skipped (no main branch) |
| Sprint BP-5 | COMPLETE | 2026-05-04 | 43/44 PASS; homelab-agent-configs skipped (no main branch) |
| Sprint BP-6 | COMPLETE | 2026-05-04 | 43/44 PASS; homelab-agent-configs skipped (no main branch) |
| Sprint WF-1 | COMPLETE | 2026-05-04 | 43/44 PASS; save-relax-write-restore cycle required (BP-4+BP-5 block unsigned Contents API commits); pp-security-master and PromptCraft also required GitHub Ruleset enforcement=disabled |
| Sprint WF-2 | COMPLETE | 2026-05-04 | 43/44 PASS; same save-relax-write-restore cycle as WF-1; image-preprocessing-detector required full ruleset body PUT to disable. Renovate planned to replace Dependabot in a future migration sprint. |
| Sprint WF-3 | COMPLETE | 2026-05-04 | 43/44 PASS; save-relax-write-restore cycle; pp-security-master (ruleset 15815381) and PromptCraft (ruleset 5939198) required ruleset enforcement=disabled. ByronWilliamsCPA/.github failed on first attempt (transient network) and was retried successfully. |
| Sprint WF-4 | COMPLETE | 2026-05-04 | 43/44 PASS; same save-relax-write-restore cycle; lightweight universal template (no Python deps); pp-security-master (ruleset 15815381) required ruleset enforcement=disabled. |
| Sprint WF-5 | COMPLETE | 2026-05-04 | 29/29 public repos PASS; two variants: Python (18 repos with pyproject.toml -- full uv+deps install) and Minimal (7 repos -- no uv, CodeQL with build-mode: none); image-preprocessing-detector required rulesets 9575480+9694992 disabled; PromptCraft required ruleset 5939198 disabled. |
| Sprint WF-6 | COMPLETE | 2026-05-04 | 21/21 Python public repos PASS; 7 non-Python public repos marked N/A (sbom.yml targets pyproject.toml+uv.lock path triggers; would fail on non-Python repos); PromptCraft (ruleset 5939198) and pp-security-master (ruleset 15815381) required ruleset enforcement=disabled. |
| Sprint WF-7 | COMPLETE | 2026-05-04 | 28/28 public repos PASS; deployed to all public repos (Scorecard is language-agnostic -- analyzes repo security posture, not code); no ruleset handling required for this sprint. |
| Sprint WF-8 | COMPLETE (partial) | 2026-05-04 | 25/32 Python repos PASS; 6 newly deployed (GCS, image-generation, ledgerbase, magg, testing, zen-mcp-server in williaby); 5 blocked on missing pyproject.toml (need Python packaging setup). ledgerbase/GCS/testing/zen-mcp-server have ci.yml but will fail uv sync until uv migration. |
| Sprint WF-9 | COMPLETE (partial) | 2026-05-04 | 26/32 Python repos PASS; 16 newly deployed; 5 blocked on missing pyproject.toml (same as WF-8); image-preprocessing-detector had compatibility.yml (wrong name) -- python-compatibility.yml deployed alongside it; xero-crypto targets master branch. pp-security-master (ruleset 15815381), PromptCraft (ruleset 5939198), image-preprocessing-detector (rulesets 9575480+9694992) required ruleset enforcement=disabled. |
| Sprint WF-10 | COMPLETE (mostly blocked) | 2026-05-04 | 10/32 Python repos PASS; 1 deployed (williaby/monte_carlo -- only repo with SONAR_TOKEN set). 22 repos blocked on SonarCloud project registration and/or SONAR_TOKEN secret. BW org projects confirmed via SonarCloud MCP: 13 projects registered; only audio-processor, llc-manager, homelab-infra have SONAR_TOKEN set and sonarcloud.yml. BW broken integrations (sonarcloud.yml present, no SONAR_TOKEN): fragrance-rater, python-libs, rag-processor, template-sample. Action needed: add SONAR_TOKEN to all registered repos; register remaining Python repos in SonarCloud. |
| Sprint WF-11 | COMPLETE (partial) | 2026-05-04 | 25/32 Python repos PASS (78%). Template rearchitected as workflow_run subscriber (no hardcoded paths). Downloads coverage-reports artifact from CI and delegates to org-level python-qlty-coverage.yml. 5 blocked repos lack pyproject.toml. Deployed to: audio-processor, cookiecutter-template-sample, DeQA-Doc, fragrance-rater, gleif, homelab-infra, llc-manager, maester-tests, python-libs, rag-processor, template-sample, xero-crypto (BW); data_ingestor, dna, exercise-competition, GCS, image-generation, image-preprocessing-detector, ledgerbase, magg, monte_carlo, pp-security-master, PromptCraft, testing, zen-mcp-server (W). |
| Sprint WF-12 | DEFERRED (partial) | 2026-05-04 | 15/16 applicable repos PASS. Remaining blocker: exercise-competition needs python-semantic-release setup from scratch. magg set to N/A (Docker-only). zen-mcp-server resolved by EV-2 rename. |
| Sprint WF-13 | COMPLETE | 2026-05-04 | 16/16 Published-tier repos PASS (100%). Standard revised by EV-1 from release-sign.yml (Cosign) to slsa-provenance.yml (SLSA framework). 9 repos already had slsa-provenance.yml; 7 deployed this sprint: cookiecutter-template-sample, gleif, template-sample (BW), data_ingestor, image-preprocessing-detector, ledgerbase, zen-mcp-server (W). Canonical template created at .github/workflows/slsa-provenance.yml. |
| Sprint WF-14 | COMPLETE | 2026-05-04 | 15/15 Has-Docs repos PASS (100%); 3 deployed this sprint (gleif, monte_carlo, PromptCraft); 12 already had docs.yml from prior state; applicable count corrected to 15 (16 in Sprint 0 was wrong by 1) |
| Sprint EV-1 | COMPLETE | 2026-05-04 | Evaluated all BW extras. 4 new WF sprints (WF-15 through WF-18). WF-13 standard revised: release-sign.yml (Cosign) replaced by slsa-provenance.yml (SLSA framework) as standard. WF-11 unblocked: template needs parameterized source-dir input. No removals. See sprint plan EV-1 section for full findings table. |
| Sprint EV-2 | COMPLETE | 2026-05-04 | Evaluated all W extras. 2 concrete actions: (1) removed compatibility.yml from image-preprocessing-detector (replaced by python-compatibility.yml); (2) renamed semantic-release.yml to release.yml in zen-mcp-server (unblocks WF-12). magg W12/W13 set to N/A (Docker-only release). 9 repos now PASS WF-13 under revised standard. See sprint plan EV-2 section for full findings table. |
| Sprint WF-15 | COMPLETE | 2026-05-04 | 22/22 cruft-tracked repos PASS (100%); 12 deployed; 10 already had validate-cruft.yml. Template uses hashFiles() conditional on scripts/check_orphaned_files.py so it is safe on repos without that script. EVENT_NAME env var used for security. image-preprocessing-detector (9575480+9694992), pp-security-master (15815381), PromptCraft (5939198) required ruleset enforcement=disabled. |
| Sprint WF-16 | COMPLETE | 2026-05-04 | 20/20 applicable repos PASS (100%); 11 deployed (all williaby); 9 BW repos already had it. 5 BW Python repos (cookiecutter-template-sample, DeQA-Doc, gleif, template-sample, xero-crypto) marked N/A -- no check_fips_compatibility.py. Canonical template fixes command injection: STRICT_MODE passed via env var, not direct expression interpolation in bash. Also adds uv sync --frozen (resolves S8544), concurrency group, and JSON report artifact upload. image-preprocessing-detector (9575480+9694992), pp-security-master (15815381), PromptCraft (5939198) required ruleset enforcement=disabled. |
| Sprint WF-17 | COMPLETE | 2026-05-04 | 10/10 applicable repos PASS (100%). All 10 repos (7 BW + 3 W: dna, exercise-competition, image-preprocessing-detector) already had mutation-testing.yml; no new deployments. Canonical template written to .github/workflows/mutation-testing.yml. Remaining W Python repos marked N/A (coverage data needed before WF-17 can be applied). |
| Sprint WF-18 | COMPLETE | 2026-05-04 | 25/25 applicable repos PASS (100%). All 25 Python repos (12 BW + 13 W) already had container-security.yml AND Dockerfiles; no new deployments needed. Canonical template created at .github/workflows/container-security.yml with generic image-tag 'local:scan'. Delegates to org-level python-container-security.yml reusable workflow; fails on CRITICAL/HIGH; generates SBOM; uploads SARIF. |
