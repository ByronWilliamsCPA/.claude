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
| Repos with WF-1 (reuse.yml) | 11 | 25% |
| Repos with WF-2 (dependabot.yml) | 13 | 30% |
| Repos with WF-3 (security-analysis.yml) | 15 | 34% |
| Repos with WF-4 (pr-validation.yml) | 15 | 34% |

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
| WF-13 | `release-sign.yml` | Published repos only |
| WF-14 | `docs.yml` | Has-Docs repos only |

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
| BW | `.github` | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | 3/6 |
| BW | `audio-processor` | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | 5/6 |
| BW | `cookiecutter-python-template` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| BW | `cookiecutter-template-sample` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| BW | `DeQA-Doc` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| BW | `fragrance-rater` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| BW | `gleif` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| BW | `homelab-infra` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| BW | `llc-manager` | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | 3/6 |
| BW | `maester-tests` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 5/6 |
| BW | `python-libs` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| BW | `rag-processor` | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | 5/6 |
| BW | `reference-library` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| BW | `taxdome` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| BW | `template-sample` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| BW | `xero-crypto` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `.claude` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `backpacking` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `CR-10-` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `dart-frog-paludarium` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `data_ingestor` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `dna` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `exercise-competition` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `family_office` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `FISProject` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `GCS` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `homelab-agent-configs` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 0/6 |
| W | `image-generation` | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | 4/6 |
| W | `image-preprocessing-detector` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **6/6** |
| W | `klipper-octoprint-configs` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `ledgerbase` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `library` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `LifeSphere` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `magg` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `monte_carlo` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `OPNS` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `OPNSense` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `pp-security-master` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `PromptCraft` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `superslicer-configs` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `testing` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `xero-practice-management` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| W | `zen-mcp-server` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| | **PASS count** | **43/44** | **43/44** | **6/44** | **8/44** | **4/44** | **7/44** | |

**BP-5 status check names** (for repos with at least one check):
- BW/.claude: CI Gate, Security Gate Validation, Dependency & Standards Validation, Check REUSE Compliance
- BW/.github: Analyze (GitHub Actions reusable)
- BW/gleif: CI Gate
- BW/homelab-infra: Security Gate, Dep&Stds, CI Gate, REUSE (4 checks)
- BW/llc-manager: Validation Summary
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

| Org | Repo | W1 | W2 | W3 | W4 | W5 | W6 | W7 | W8 | W9 | W10 | W11 | W12 | W13 | W14 | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BW | `.claude` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | N | N | N | N | N | N | ✓ | **8/8** |
| BW | `.github` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | 0/7 |
| BW | `audio-processor` | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | 11/14 |
| BW | `cookiecutter-python-template` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | 0/7 |
| BW | `cookiecutter-template-sample` | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | 7/14 |
| BW | `DeQA-Doc` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | N | N | N | 1/11 |
| BW | `fragrance-rater` | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | 11/14 |
| BW | `gleif` | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | N | 6/13 |
| BW | `homelab-infra` | ✓ | ✓ | ✓ | ✓ | N | N | N | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | 8/11 |
| BW | `llc-manager` | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | 11/14 |
| BW | `maester-tests` | ✓ | ✓ | ✓ | ✓ | N | N | N | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | 8/11 |
| BW | `python-libs` | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | 11/14 |
| BW | `rag-processor` | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | 11/14 |
| BW | `reference-library` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | 0/7 |
| BW | `taxdome` | ✗ | ✗ | ✗ | ✗ | N | N | N | ✗ | ✗ | ✗ | ✗ | N | N | N | 0/8 |
| BW | `template-sample` | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ | ✓ | 10/14 |
| BW | `xero-crypto` | ✗ | ✗ | ✓ | ✓ | N | N | N | ✓ | ✗ | ✗ | ✗ | N | N | N | 3/8 |
| W | `.claude` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | 0/7 |
| W | `backpacking` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | 0/7 |
| W | `CR-10-` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | 0/7 |
| W | `dart-frog-paludarium` | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | N | N | N | 0/4 |
| W | `data_ingestor` | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | N | 5/13 |
| W | `dna` | ✓ | ✓ | ✓ | ✓ | N | N | N | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | 9/11 |
| W | `exercise-competition` | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | N | 7/13 |
| W | `family_office` | ✗ | ✗ | ✗ | ✗ | N | N | N | ✗ | ✗ | ✗ | ✗ | N | N | N | 0/8 |
| W | `FISProject` | ✗ | ✗ | ✗ | ✗ | N | N | N | ✗ | ✗ | ✗ | ✗ | N | N | N | 0/8 |
| W | `GCS` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N | N | N | 0/11 |
| W | `homelab-agent-configs` | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | N | N | N | 0/4 |
| W | `image-generation` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N | N | N | 0/11 |
| W | `image-preprocessing-detector` | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ | ✓ | 9/14 |
| W | `klipper-octoprint-configs` | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | N | N | N | 0/4 |
| W | `ledgerbase` | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | N | 3/13 |
| W | `library` | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | N | N | N | 0/4 |
| W | `LifeSphere` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N | N | N | 0/11 |
| W | `magg` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N | 0/13 |
| W | `monte_carlo` | ✗ | ✗ | ✗ | ✗ | N | N | N | ✓ | ✗ | ✗ | ✗ | N | N | N | 1/8 |
| W | `OPNS` | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | N | N | N | 0/4 |
| W | `OPNSense` | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | N | N | N | 0/4 |
| W | `pp-security-master` | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | N | N | N | 3/11 |
| W | `PromptCraft` | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | N | N | N | 3/11 |
| W | `superslicer-configs` | ✗ | ✗ | ✗ | ✗ | N | N | N | N | N | N | N | N | N | N | 0/4 |
| W | `testing` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N | N | N | 0/11 |
| W | `xero-practice-management` | ✗ | ✗ | ✗ | ✗ | N | N | N | ✗ | ✗ | ✗ | ✗ | N | N | N | 0/8 |
| W | `zen-mcp-server` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N | 0/13 |
| | **PASS count** | **11** | **13** | **15** | **15** | **4** | **12** | **16** | **19** | **10** | **9** | **0** | **17** | **0** | **10** | |
| | **of applicable** | **44** | **44** | **44** | **44** | **27** | **27** | **27** | **32** | **32** | **32** | **32** | **24** | **24** | **16** | |
| | **% pass** | **25%** | **30%** | **34%** | **34%** | **15%** | **44%** | **59%** | **59%** | **31%** | **28%** | **0%** | **71%** | **0%** | **63%** | |

**Notable workflow gaps:**
- **WF-5 (codeql.yml)**: Only 4/27 public repos have it. The `ByronWilliamsCPA/.github` reusable library has `python-codeql.yml` but repos call it by a different name; EV sprint needed.
- **WF-11 (coverage.yml)**: 0% pass rate. Repos use `codecov.yml` or `qlty.yml` instead of `coverage.yml`. The standard `coverage.yml` template uses Qlty; EV sprint will evaluate migration path.
- **WF-13 (release-sign.yml)**: 0% pass rate. Repos use `slsa-provenance.yml` instead. The standard `release-sign.yml` uses Cosign; EV sprint will determine if `slsa-provenance.yml` is equivalent or needs replacement.
- **WF-12 (release.yml)**: 71% pass rate on applicable repos. High pass rate but file must use the standard name; some repos use `semantic-release.yml` (zen-mcp-server) or `publish.yml` (magg) instead.

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
| BP-3 (linear) | All except BW/.claude, audio-proc, homelab-infra, maester, rag-proc, W/image-preproc | 38/44 |
| BP-4 (signatures) | All except BW/.claude, .github, audio-proc, homelab-infra, maester, rag-proc, W/image-gen, image-preproc | 36/44 |
| BP-5 (admin+checks) | All except BW/.claude, homelab-infra, maester, W/image-preproc | 40/44 |
| BP-6 (reviews=0) | All except BW/.claude, audio-proc, homelab-infra, llc-mgr, rag-proc, W/image-gen, image-preproc | 37/44 |
| WF-1 (reuse.yml) | 33/44 universal failing | 33/44 |
| WF-2 (dependabot) | 31/44 universal failing | 31/44 |
| WF-3 (security-analysis) | 29/44 universal failing | 29/44 |
| WF-4 (pr-validation) | 29/44 universal failing | 29/44 |
| WF-5 (codeql) | 23/27 public repos failing | 23/27 |
| WF-8 (ci.yml) | 13/32 python repos failing | 13/32 |

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
| Sprint BP-3 | pending | - | - |
| Sprint BP-4 | pending | - | - |
| Sprint BP-5 | pending | - | - |
| Sprint BP-6 | pending | - | - |
| Sprint WF-1 | pending | - | - |
| Sprint WF-2 | pending | - | - |
| Sprint WF-3 | pending | - | - |
| Sprint WF-4 | pending | - | - |
| Sprint WF-5 | pending | - | - |
| Sprint WF-6 | pending | - | - |
| Sprint WF-7 | pending | - | - |
| Sprint WF-8 | pending | - | - |
| Sprint WF-9 | pending | - | - |
| Sprint WF-10 | pending | - | - |
| Sprint WF-11 | pending | - | - |
| Sprint WF-12 | pending | - | - |
| Sprint WF-13 | pending | - | - |
| Sprint WF-14 | pending | - | - |
| Sprint EV-1 | pending | - | ByronWilliamsCPA non-standard workflow evaluation |
| Sprint EV-2 | pending | - | williaby non-standard workflow evaluation |
