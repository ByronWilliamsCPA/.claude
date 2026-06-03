---
schema_type: common
title: "Dependency Tooling Effectiveness: Renovate vs Dependabot vs Snyk vs SBOM"
status: published
owner: core-maintainer
purpose: "Empirical, data-grounded comparison of how the self-hosted Renovate stack is actually keeping packages current and vulnerabilities closed across the 24 Renovate-configured repos, benchmarked against what Dependabot, Snyk, and an SBOM-based scan would add, with a phased tooling recommendation."
tags:
  - reference
  - dependencies
  - security
  - compliance
  - automation
---

This is the empirical companion to [renovate-architecture.md](renovate-architecture.md). That document
is the architecture source of truth (the self-hosted Docker stack, layered config, manifest enforcement).
This document measures the **outcome**: given that architecture, how current are the packages and how many
vulnerabilities are actually closing?

| Field | Value |
|---|---|
| Date | 2026-06-02 |
| Scope | 24 unique GitHub repos carrying `renovate.json` (28 local clones, deduplicated) |
| Data sources | GitHub Dependabot alerts API (paginated), GitHub PR/issue API, `osv-scanner` on lockfiles, PyPI release-date drift (libyear) |
| Excluded | `dataset_dev` (local-only orphan, 404 on GitHub); docs-only/config repos without `pyproject.toml` are PR-only |
| Raw data | `/tmp/dep-analysis/{github_combined,local_combined,merged_rows}.json` |

## The decision this answers

The operative question is not "which tool wins." It is: **is the current Renovate-only structure adequate,
and if not, what changes to it or in parallel get us there?** The fleet is mid-migration to uv (the structure
Renovate needs to operate fully), and the prior state had both Dependabot and Renovate opening PRs. The goal is
Renovate as the sole PR-opener. This document tests whether that is adequate for both remediation and detection.

## TL;DR verdict

1. **You are already Renovate-only for PRs.** Dependabot opens 0 PRs fleet-wide today; only `AMC` and `Unify`
   still carry a `dependabot.yml` (both with 0 open PRs). The dual-PR friction is effectively gone.
2. **Incomplete uv migration is the dominant constraint, confirmed by the data.** Unmigrated (poetry or
   requirements) repos carry **4 to 6x the alerts per repo at roughly a quarter of the merge rate** of migrated
   uv repos. Migration degrades both axes: Renovate detects-and-acts only through a manifest it can parse, so a
   legacy manifest suppresses both detection-driven action and remediation.
3. **Migration is necessary but not sufficient.** Two refinements: dual-manifest debt (a leftover
   `requirements.txt` after adding `uv.lock`) is the single biggest alert source (389 on one repo), and even
   fully-migrated repos keep a transitive backlog that only `lockFileMaintenance` closes.
4. **For remediation, Renovate-only is adequate by design, and proven where it is fully deployed.** The
   ready cohort (uv on main + green CI) averages 3.4 alerts per repo, 4 of 5 at zero. The 786-alert backlog is
   concentrated in not-ready repos. The dominant blocker is red main CI (16 of 24 repos; red-main repos average
   48.1 alerts vs 2.1 for green, a 23x gap): Renovate cannot land a fix onto a broken base. Close the gap by
   finishing the rollout, not by adding tools.
5. **For detection, Renovate as the sole detector is not adequate, but the fix is free: keep Dependabot
   alerts on.** They open no PRs (no dual-PR regression) and give a queryable ledger Renovate lacks. A single
   detector can be blind to a whole ecosystem: a Python-only SBOM scan reported 0 for `rag-processor`
   while its npm frontend carried 17 live vulnerabilities that Dependabot's multi-ecosystem alerts caught.
6. **Adequate end-state = Renovate (sole PR-opener) + Dependabot alerts (free detection ledger).** Both already
   in place. `osv-scanner` in CI is an optional gate or second detector; **Snyk is not justified** at this scale
   unless reachability or license compliance become hard requirements.

## What each tool actually answers

The comparison is muddled if "Renovate vs Dependabot vs Snyk" is read as three interchangeable products.
They answer different questions, and the SBOM scan is the neutral ground truth underneath all three.

| Tool | Primary job | What it delivers | Blind spot in this fleet |
|---|---|---|---|
| **Renovate** (self-hosted) | Update delivery | PRs that move direct deps (and lockfiles) forward on a schedule | Transitive vulns by default; effectiveness gated by whether PRs merge |
| **Dependabot alerts** | Vulnerability detection | Per-(advisory x manifest) alerts against the GitHub Advisory DB; covers transitive | Inflated, non-deduplicated counts; no fix unless security updates are enabled |
| **Dependabot security updates** | Targeted security fixes | PRs that rewrite the lockfile to patch a vulnerable dep, including transitive | A per-repo setting (on at least `llc-manager`), mostly off; security-only, not general currency |
| **Snyk** | Detection + reachability + fix | Proprietary DB (often earlier than GHSA), reachability to cut false positives, license checks, fix PRs | Commercial; free tier caps tests/month; cost scales with 44-repo fleet |
| **SBOM scan** (`osv-scanner`/Trivy) | Neutral enumeration + gate | Deduplicated per-package vuln view across all components, CI gate, free | Reports, does not remediate |

## Fleet totals

| Metric | Value |
|---|---|
| Open Dependabot alerts | **786** (21 critical, 343 high, 310 medium, 112 low) |
| Alerts with a fix available | 757 (**96%**) |
| Renovate PRs opened (all time) | 476 |
| Renovate PRs merged | 204 (**43%**) |
| Renovate PRs closed unmerged | 213 (**45%**) |
| Renovate PRs open now | 59 |
| Repos with `renovate.json` but 0 Renovate PRs ever | 3 (`AMC`, `MTG_AI`, `Unify`) |
| Repos with `dependabot.yml` (version/security updates) | **2/24** |
| Vulnerable packages: direct vs transitive (osv) | 51 direct / **153 transitive (75%)** |

Two numbers carry the whole argument: **45% of Renovate PRs are closed without merging**, and **75% of
vulnerable packages are transitive**. The first is a delivery failure; the second is a coverage gap in
Renovate's default behaviour. Neither is fixed by replacing Renovate.

## Per-repo scorecard

Sorted by open Dependabot alerts. `ren e/m/o/c` = Renovate PRs ever / merged / open / closed-unmerged.
`osv d/t` = vulnerable packages direct / transitive. `libyr` = summed libyears of direct-dep release-date lag
(uv.lock repos only; poetry/requirements repos show 0.0 because those lockfiles carry no upload timestamps).

| Repo | DB alerts | C/H/M/L | ren e/m/o/c | osv d/t | libyr | last ren |
|---|--:|---|---|---|--:|---|
| williaby/image-preprocessing-detector | 389 | 6/157/155/71 | 6/1/3/2 | 17/19 | 38.3 | 2026-06-01 |
| williaby/data_ingestor | 99 | 3/38/40/18 | 29/4/10/15 | 12/28 | n/a | 2026-05-30 |
| ByronWilliamsCPA/maester-tests | 58 | 2/31/22/3 | 6/2/2/2 | 2/21 | 14.8 | 2026-05-28 |
| williaby/PromptCraft | 56 | 0/20/23/13 | 164/25/8/131 | 10/20 | n/a | 2026-05-28 |
| ByronWilliamsCPA/python-libs | 54 | 2/31/18/3 | 7/2/2/3 | 5/20 | 19.8 | 2026-05-28 |
| ByronWilliamsCPA/xero-crypto | 46 | 1/20/24/1 | 41/12/11/18 | 0/1* | n/a | 2026-06-01 |
| williaby/dna | 29 | 0/17/12/0 | 3/0/2/1 | 0/11 | 8.0 | 2026-05-28 |
| ByronWilliamsCPA/cookiecutter-python-template | 18 | 1/9/7/1 | 14/10/1/3 | 0/9 | 6.5 | 2026-06-01 |
| ByronWilliamsCPA/rag-processor | 17 | 3/9/4/1 | 17/12/2/3 | 2/0 | 21.6 | 2026-06-01 |
| ByronWilliamsCPA/AMC | 14 | 2/9/2/1 | 0/0/0/0 | 0/0 | 0.1 | never |
| ByronWilliamsCPA/Unify | 4 | 0/2/2/0 | 0/0/0/0 | 0/0 | 5.7 | never |
| ByronWilliamsCPA/fragrance-rater | 1 | 1/0/0/0 | 11/7/1/3 | 0/0 | 0.9 | 2026-06-02 |
| ByronWilliamsCPA/reference-library | 1 | 0/0/1/0 | 20/13/3/4 | 1/0 | 1.1 | 2026-06-02 |
| ByronWilliamsCPA/MTG_AI | 0 | - | 0/0/0/0 | 0/0 | 0.1 | never |
| ByronWilliamsCPA/audio-processor | 0 | - | 9/3/2/4 | 0/0 | 25.5 | 2026-06-01 |
| williaby/backpacking | 0 | - | 3/0/1/2 | docs | - | 2026-05-28 |
| ByronWilliamsCPA/.github | 0 | - | 15/11/0/4 | config | - | 2026-05-28 |
| ByronWilliamsCPA/cookiecutter-template-sample** | n/a | - | n/a | 2/21 | 17.7 | n/a |
| ByronWilliamsCPA/family-office-portal | 0 | - | 9/8/0/1 | 0/1 | 0.0 | 2026-06-01 |
| ByronWilliamsCPA/gleif | 0 | - | 13/7/2/4 | 0/1 | 0.9 | 2026-06-01 |
| ByronWilliamsCPA/homelab-infra | 0 | - | 83/73/5/5 | 0/1 | 13.1 | 2026-06-02 |
| williaby/image-generation | 0 | - | 12/8/1/3 | 0/0 | 0.0 | 2026-06-02 |
| ByronWilliamsCPA/llc-manager | 0 | - | 10/5/2/3 | 0/0 | 0.9 | 2026-06-01 |
| williaby/.claude | 0 | - | 4/1/1/2 | docs | - | 2026-05-08 |

\* `xero-crypto` is partly a Node project; its `requirements.txt` is not `==`-pinned, so the Python osv scan
under-counts it. Dependabot's 46 alerts (mostly npm) are the authoritative figure there.
\** Correction (2026-06-02, post independent review): `cookiecutter-template-sample` returns 404 on GitHub.
It is a local-only orphan (like `dataset_dev`), not a live fleet repo; its earlier "0 Dependabot alerts" was a
404 artifact, not a coverage gap. Its GitHub-side columns are invalid and excluded; the local osv result is
shown only to note the orphan clone itself carries vulnerable components. It must not be counted in fleet
GitHub-side conclusions.

## Detection-to-remediation wiring: can Renovate fix what Dependabot detects?

Yes, and it already does. The global config (`homelab-infra/services/renovate/config/config.json`) has the full
remediation stack enabled fleet-wide: `vulnerabilityAlerts.enabled: true`, `osvVulnerabilityAlerts: true`,
`transitiveRemediation: true`, and `lockFileMaintenance.enabled: true`, with no `enabledManagers` restriction
(so npm and other ecosystems are in scope by default). `vulnerabilityAlerts` is the feature that reads GitHub's
vulnerability-alert graph, the same data source Dependabot surfaces as alerts, and raises `fix(deps):` PRs at any
time, bypassing the normal schedule and grouping.

This is not theoretical. Renovate is actively opening vulnerability-remediation PRs across ecosystems:
`renovate/pypi-gradio-vulnerability`, `renovate/pypi-pyjwt-vulnerability` (PromptCraft),
`renovate/npm-vitest-vulnerability` (xero-crypto), `renovate/pypi-pymupdf-vulnerability` (data_ingestor). Where
CI is healthy these merge (xero-crypto's `renovate/pypi-pytest-vulnerability` and `renovate/pypi-black-vulnerability`
merged 2026-05-05). Where main is red or the repo is unmigrated, they sit OPEN (PromptCraft and data_ingestor each
carry 4 open vulnerability PRs) and the corresponding Dependabot alerts persist. The fix engine works; the merge
step is the bottleneck, exactly as the readiness analysis shows.

### The dominant root cause: `enabledManagers` does not match the migrated manifests

The biggest reason Renovate is not fixing detected vulnerabilities is not the engine, the token, or the
database. It is that on most of the high-alert repos, Renovate's per-repo `enabledManagers` allow-list points at
a package manager the repo no longer uses, so Renovate never looks at the vulnerable manifests at all. A
fleet-wide audit of `enabledManagers` against the manifests actually present on the default branch:

| Repo | enabledManagers | Manifests present | Gap | Alerts |
|---|---|---|---:|---:|
| image-preprocessing-detector | pep621, github-actions | uv.lock + 8 requirements*.txt | **pip_requirements excluded** (289 of 389 alerts) | 389 |
| maester-tests | poetry, github-actions | uv.lock (no poetry) | **stale poetry; pep621 missing** (manages nothing) | 58 |
| python-libs | poetry, github-actions | uv.lock (no poetry) | **stale poetry; pep621 missing** | 54 |
| dna | poetry, github-actions | uv.lock (no poetry) | **stale poetry; pep621 missing** | 29 |
| cookiecutter-python-template | pep621, github-actions | + package-lock.json | **npm excluded** | 18 |
| rag-processor | pep621, github-actions | + frontend/package-lock.json | **npm excluded** (the 17 npm vulns) | 17 |
| Unify | poetry, github-actions | uv.lock (no poetry) | **stale poetry; pep621 missing** | 4 |
| fragrance-rater | pep621, github-actions | + package.json, requirements | npm + pip_requirements excluded | 1 |
| MTG_AI | pep621, github-actions | + package.json | npm excluded | 0 |

**9 of 24 repos have a manager gap, and they hold 570 of 786 alerts (73% of the fleet).** The pattern is a
single migration-completeness bug repeated nine times: the manifests were migrated to uv (or an npm frontend was
added) but the per-repo `renovate.json` `enabledManagers` was never updated. The clearest cases are the
stale-poetry repos (`python-libs`, `maester-tests`, `dna`, `Unify`): their only open Renovate PRs are "Update
GitHub Actions," and every Dependabot alert sits in the `uv.lock` that the `poetry` manager cannot see.
`image-preprocessing-detector` compounds this with 8 redundant `requirements*.txt` files left behind by the
migration, 289 of its 389 alerts living in manifests the `pip_requirements` manager (excluded) would own.

This is the literal answer to "can Renovate fix what Dependabot detects": yes, but first stop telling it to
ignore the manifests. Fixing `enabledManagers` to match each repo's reality (or removing the restriction so
Renovate autodiscovers all managers, as the global config already does) puts 570 alerts back into Renovate's
remediation scope.

Two further items to verify so the loop closes on GitHub-detected (not just OSV-detected) vulnerabilities:

1. **Token scope.** Renovate's `vulnerabilityAlerts` only fires if its GitHub token can read the repo's
   vulnerability alerts. The deployed token is injected at runtime (`RENOVATE_ORG_GITHUB_TOKEN`, not in the
   readable env files) and PRs author as a user, so it is a PAT; a `repo`-scoped classic PAT can read
   vulnerability alerts (confirmed: the GraphQL `vulnerabilityAlerts` query returns 389 for
   image-preprocessing-detector under `repo` scope). Because `osvVulnerabilityAlerts` is independently enabled
   and OSV mirrors the GitHub Advisory DB, detection does not critically depend on this read, but verify the
   token carries `repo` (or fine-grained "Dependabot alerts: read") and check the Renovate run logs for a
   vulnerability-alert count to be certain.
2. **Redundant manifests.** `image-preprocessing-detector` carries 8 `requirements*.txt` files (including a
   duplicated `requirements/` subdirectory). Once uv is authoritative, delete them; this removes the manifests
   Dependabot is alerting on rather than trying to keep eight stale exports patched.

### Leveraging the existing SBOM step

The standards manifest already mandates an SBOM workflow (`sbom.yml`, manifest check; reusable
`ByronWilliamsCPA/.github/.github/workflows/python-sbom.yml`, plus `sbom-nightly.yml`). It is more than
generation: it produces a CycloneDX SBOM and scans it with Trivy (gating), Grype (advisory), and OSV-Scanner
(keyless gate, transitive-aware), uploading SARIF to the Security tab. That is a strong detection-and-gate layer.

Two limits shape how it fits the fix loop:

- **It is uv/Python-only by org policy.** The reusable workflow errors out on poetry repos and skips repos
  without a root `pyproject.toml`; it does not scan npm, container, or other ecosystems. So it has the same
  coverage gap that hid `rag-processor`'s 17 npm vulnerabilities, and the same uv-migration precondition. It
  cannot be the sole detector for polyglot repos.
- **It gates and verifies; it does not trigger Renovate.** Renovate detects independently via GitHub alerts and
  OSV; it does not read the SBOM or the SARIF. The SBOM step's role in the loop is to (a) gate merges so a
  Renovate fix PR is verified to actually clear the CVE, (b) provide the audit artifact, and (c) push a deep
  Python transitive ledger to the Security tab. It complements Renovate; it does not feed it.

**Target wiring (most of it already in place):** detection = Dependabot alerts (multi-ecosystem, free) plus the
SBOM SARIF gate (deep Python); remediation = Renovate (`vulnerabilityAlerts` + `osvVulnerabilityAlerts` +
`transitiveRemediation` + `lockFileMaintenance`); verification = the SBOM gate confirming the fix and blocking
regressions. Going "Renovate-only for PRs" does not mean dropping Dependabot alerts; it means Dependabot opens no
PRs (already true) while its alert feed remains the multi-ecosystem detection ledger Renovate acts on. To cover
npm in CI as well, either extend the SBOM workflow to the npm ecosystem or rely on Dependabot alerts for it.

## Readiness segmentation (the fair test)

A fleet average over a half-finished rollout measures the rollout, not the tool. Renovate operates through a
manifest it can parse, on a branch its config is merged into, against a base its PRs can pass CI on. Scoring its
effectiveness requires filtering on three readiness gates, measured against the **default branch** (not a local
feature-branch checkout): (1) migrated to uv on main, (2) structural/enable PRs merged so main carries the
working config, (3) main CI green so PRs rebase onto a clean base.

| Cohort | Repos | Alerts/repo | Renovate merge rate |
|---|--:|--:|--:|
| **Ready: uv-only on main + green CI** | 5 | **3.4** | 57% |
| Migrated (uv-only) but main CI red | 10 | 17.9 | 60% |
| Dual-manifest (uv + leftover legacy) | 2 | 194.5* | 83% |
| Unmigrated (poetry / requirements) | 3 | 67.0 | 18% |
| Docs/config (no Python lockfile) | 4 | 0.0 | n/a |

The single strongest signal is main CI health, independent of migration:

| Main CI | Repos | Alerts/repo | Merge rate |
|---|--:|--:|--:|
| green | 8 | **2.1** | 58% |
| red | 16 | **48.1** | 40% |

Red main is a 23x alert multiplier. The mechanism is direct: Renovate PRs inherit a red base, fail CI, and
cannot merge. Across the not-ready repos, open Renovate PRs are almost uniformly red (PromptCraft 8 of 8,
data_ingestor 10 of 10, xero-crypto 11 of 11). Merge rate alone is a poor discriminator (it is ~57% even in the
ready cohort, because Renovate routinely supersedes and closes its own PRs); what tracks the alert backlog is
whether the *security* PRs can land, which is gated by CI health and migration, not by Renovate.

**Conclusion:** Where Renovate is fully deployed, it holds repos at near-zero alerts. The backlog is a rollout
artifact, not a tooling inadequacy. The lone ready-cohort outlier is `rag-processor` (uv, green, but 17 alerts),
which needs its open Renovate PRs merged and `lockFileMaintenance` for transitive residue.

\* dual-manifest average is skewed by `image-preprocessing-detector` (389); `homelab-infra` is 0.

## Multi-scanner validation on the ready cohort

To test whether "ready" repos are genuinely clean or whether Dependabot's count hides or inflates issues, all
five ready repos were scanned against their **main-branch** lockfiles with four independent sources: Dependabot
(live), osv-scanner, pip-audit, and Trivy (via a generated CycloneDX SBOM). Snyk was not run (no account token);
its delta is characterized below rather than measured.

| Repo | Dependabot | osv (py) | pip-audit | Trivy | osv (npm) | Verdict |
|---|--:|--:|--:|--:|--:|---|
| williaby/image-generation | 0 | 0 | 0 | 0 | n/a | Truly clean (unanimous, single ecosystem) |
| ByronWilliamsCPA/audio-processor | 0 | 0 | 0 | 0 | n/a | Clean app deps; carries Dockerfiles (image surface unscanned) |
| ByronWilliamsCPA/llc-manager | 0 | 0 | 0 | 0 | n/a | Clean app deps; carries a Dockerfile |
| ByronWilliamsCPA/gleif | 0 | 0 | **1** | 0 | n/a | 1 unfixable PYSEC ReDoS in `py` (no patch exists) |
| ByronWilliamsCPA/rag-processor | 17 | 0 | 0 | 0 | **18** | 17-18 real npm vulns in `frontend/`, missed by the Python-only scan |

Three findings, each load-bearing for the tooling decision:

1. **For the Python surface, the scanners agree with Dependabot.** Three repos are unanimously 0; the others'
   Python lockfiles are 0. An SBOM-plus-osv pipeline reproduces Dependabot's verdict on Python deps. Renovate
   plus Dependabot alerts is not under-detecting fixable Python vulnerabilities on ready repos.
2. **The only "extra" finding beyond Dependabot is unfixable.** pip-audit alone flags `py==1.11.0`
   (PYSEC-2022-42969, a ReDoS) in `gleif`, sourced from PyPI's advisory feed that GHSA/OSV/Trivy do not carry.
   It has `fix_versions=[]`: no patch exists, so no tool, including Snyk, could remediate it via a bump. It is a
   database-curation difference, not a coverage gap, and not actionable.
3. **The real gap is ecosystem coverage, and it is the most important result.** `rag-processor` is uv-migrated
   and Python-clean, but has an unmanaged React frontend whose `frontend/package-lock.json` carries 17 to 18
   live npm vulnerabilities (handlebars, tar, esbuild, vite, vitest, ws). The Python-only SBOM reported 0;
   Dependabot caught them because it scans every manifest; osv-scanner reproduces them when pointed at the npm
   lockfile. A naive "osv-scanner on uv.lock in CI" gate would have given false comfort here.

**Answer to "would they still come up with 0":** Not uniformly. One repo is genuinely 0 everywhere; two are 0 on
app deps but carry an unscanned container base-image surface; one has a single unfixable PYSEC finding; and one
has 17 to 18 real npm vulnerabilities that a Python-centric view misses entirely. The deviations are not caused
by Renovate being weak or by needing Snyk. They are caused by **ecosystem coverage**: "ready" was defined on the
uv/Python axis, but a polyglot repo has npm and container surfaces that uv migration and a uv-only SBOM never
touch. This is the strongest argument in the entire analysis for keeping Dependabot alerts (multi-ecosystem by
default) and, if an SBOM CI gate is added, for making it enumerate every ecosystem rather than just Python.

**What Snyk would add here:** it would catch the npm vulnerabilities (multi-ecosystem, like Dependabot) and, via
reachability, could tell you which of the 17 npm alerts are actually reachable in the shipped frontend bundle
(several, like `vitest` and `esbuild`, are build-time dev dependencies that may never ship). That triage value is
real but narrow, and it does not change the conclusion that the ready repos' Python surface is adequately
covered by the free stack.

## Three failure modes

The repos cluster into three patterns. The cluster a repo falls into dictates the fix.

### Cluster A: Renovate merges, repo stays clean (the target state)

`homelab-infra`, `family-office-portal`, `image-generation`, `llc-manager`, `gleif`, `fragrance-rater`,
`reference-library`, `rag-processor`, `.github`, `MTG_AI`. High merge ratios, 0 to 2 alerts. This proves the
architecture works when PRs land. Note these still carry non-security currency lag (`audio-processor` 25.5
libyears, `rag-processor` 21.6) because closed-unmerged minor/patch PRs leave packages behind even when no CVE
is open. Renovate keeps them *safe*, not necessarily *current*.

### Cluster B: Renovate proposes, PRs do not merge, alerts pile up

`PromptCraft` (164 opened, 131 closed unmerged, 56 alerts), `data_ingestor` (29 opened, 4 merged, 99 alerts),
`xero-crypto` (41 opened, 18 closed, 46 alerts). The bottleneck is the merge step. PromptCraft's
`renovate-auto-merge.yml` workflow shows its last several runs as `failure`, which is the literal mechanism by
which proposed fixes fail to land. **This is where the largest, most fixable alert backlog lives.**

### Cluster C: Renovate barely runs, transitive debt dominates

`image-preprocessing-detector` (6 PRs ever, 389 alerts, 38 libyears, 19 transitive vulns), `maester-tests`
(6 PRs, 58 alerts, 21 of 23 vulns transitive), `python-libs` (7 PRs, 54 alerts, 20 transitive), plus the 4
config-only repos that have never produced a Renovate PR. Here the direct-dependency PR model is structurally
insufficient: 21 of 23 vulnerabilities in `maester-tests` are transitive and will never be addressed by a
direct-dep bump. These repos need lockfile-rewriting remediation (Renovate `lockFileMaintenance` plus
vulnerability-driven lockfile updates, or Dependabot security updates).

## The transitive-dependency crux

This is the finding that most directly answers "what would Dependabot or a deeper SBOM analysis add."

- Renovate's default config opens PRs for **direct** dependencies declared in `pyproject.toml`. It will not
  open a PR to patch a vulnerable package that only appears transitively unless `lockFileMaintenance` is
  enabled and merging, or a vulnerability alert specifically triggers a lockfile rewrite.
- **75% of the fleet's vulnerable packages are transitive.** That is the structural reason 786 alerts coexist
  with active Renovate: the tool is doing its declared job (direct-dep currency) while the majority of the
  vulnerability surface sits outside that job.
- **Dependabot security updates** specifically rewrite the lockfile to patch the vulnerable dependency,
  transitive included. That capability is the precise complement to Renovate's gap, and it is free and native.
  It is currently enabled on 2 of 24 repos.
- An **SBOM scan** (`osv-scanner`) enumerates every component and attributes each vuln to a package once,
  giving a deduplicated, transitive-aware count. For `image-preprocessing-detector`, osv reports 36 vulnerable
  packages where Dependabot reports 389 alerts: the same reality, counted differently (Dependabot multiplies by
  advisory and by manifest path; this repo carries both `uv.lock` and `requirements.txt`). For triage, the
  deduplicated SBOM count is the actionable one; for completeness, Dependabot's manifest-aware count flags that
  the second manifest is also exposed.

## Recommendation

The current Renovate-only structure is adequate as an architecture; it is not yet adequate in outcome because
the rollout is unfinished. The fix is to complete the rollout in dependency order, not to add or swap tools.
Sequence matters: each step is a precondition for the next being measurable.

**Finish the rollout (closes the backlog, no new tooling):**

1. **Fix `enabledManagers` to match the migrated manifests (73% of all alerts).** This is the highest-leverage
   action and a prerequisite for everything else: until Renovate is scoped to the right managers, it does not
   even propose the fixes, so making main green has nothing to merge. Update the nine gapped repos (or simply
   remove the `enabledManagers` restriction so Renovate autodiscovers all managers, matching the global config).
   Priority order by impact: `image-preprocessing-detector` (add `pip_requirements` or delete the 8 legacy
   files), the stale-poetry repos `maester-tests`/`python-libs`/`dna`/`Unify` (change `poetry` to `pep621`), and
   the npm-excluded repos `cookiecutter-python-template`/`rag-processor` (add `npm`).
2. **Make main green.** Red main on 16 of 24 repos is the next blocker (23x alert multiplier); once Renovate is
   proposing the right fixes, they still cannot merge onto a broken base. Prioritise the high-alert red-main
   repos.
3. **Finish uv migration on the 3 unmigrated repos** (`data_ingestor`, `PromptCraft`, `xero-crypto`: 201 alerts
   at an 18% merge rate). On poetry/requirements manifests Renovate cannot run proper lockfile maintenance, so
   both its detection-driven action and its remediation are degraded.
4. **Remove orphan legacy manifests.** Delete the 8 leftover `requirements*.txt` files from
   `image-preprocessing-detector` once uv is authoritative; verify `homelab-infra`'s `requirements.txt` is a
   synced export, not an unmaintained second manifest.
5. **Merge the structural backlog.** Repos with large piles of unmerged non-Renovate PRs (`PromptCraft` 22,
   `Unify` 22, `data_ingestor` 16) are mid-restructure; the enabling config is not on main. Land it.

**Tune Renovate (closes the residual transitive gap on ready repos):**

6. **Enable `lockFileMaintenance` fleet-wide** with automerge-on-green. This is the in-Renovate mechanism that
   refreshes transitive dependencies (the 75% of vulnerable packages direct-dep PRs never touch), which is the
   residue left even on fully-migrated repos like `rag-processor`, `maester-tests`, and `python-libs`. Keep
   `vulnerabilityAlerts` and `osvVulnerabilityAlerts` on for vulnerability-triggered PRs. This removes the need
   for Dependabot to open PRs at all.

**Keep a detection ledger (do not regress to blind):**

7. **Keep Dependabot alerts on (effectively all live repos already have them on).** The only two that read
   "disabled" in the raw scan were a 404 orphan and an archived repo, so live coverage is ~100%, not a gap.
   Alerts open no PRs, so they do not reintroduce the
   dual-PR friction, and they are the queryable, SLA-trackable ledger Renovate has no equivalent for. Renovate
   surfaces only what it can patch; the Python-only scan that reported 0 for `rag-processor` while its npm
   frontend held 17 live vulnerabilities shows a single-ecosystem detector can be blind. Remove the two remaining `dependabot.yml` files (`AMC`, `Unify`) to make
   Renovate the sole PR-opener while leaving Dependabot alerts as detection-only.

**Optional, by need (not required for adequacy):**

8. **`osv-scanner` SBOM gate in CI** (the reusable `python-sbom.yml` already exists). Add it for a hard release
   gate, a deduplicated count, and a second independent detector that would have caught the template-sample
   blind spot. This is the path if you later want to drop Dependabot alerts entirely and stay single-vendor.
9. **Snyk only if** reachability analysis (to triage the backlog down to exploitable-and-reachable) or license
   compliance becomes a hard requirement. At a 44-repo solo-maintained fleet the free stack covers the
   detection and transitive-remediation value; price Snyk against its per-project commercial tier before adopting.

## Answering the decision directly

> Is the current Renovate-only structure adequate? If not, what changes to it or in parallel get us there?

**Adequate as architecture, not yet in outcome, and the gap is rollout completion rather than tooling.** Proof:
the ready cohort (uv on main + green CI) runs at 3.4 alerts per repo with most at zero. The path to fleet-wide
adequacy is steps 1 to 5 above (green main, finish migration, remove legacy manifests, merge structural PRs,
enable `lockFileMaintenance`), all within Renovate and CI. The only thing that should run in parallel is a
**detection ledger**, and you already have the free one (Dependabot alerts); keep it. Snyk and an osv CI gate
are optional enhancements, not prerequisites for "Renovate-only is enough."

## Limitations

- **libyear** is computed only for `uv.lock` repos (poetry.lock and requirements.txt carry no upload
  timestamps); poetry/requirements repos show drift class counts but 0.0 libyears.
- **Node coverage is partial.** The local SBOM scan is Python-focused; `xero-crypto`'s npm surface is
  represented by Dependabot's count, not osv.
- **Counts are a 2026-06-02 snapshot.** Renovate runs on a schedule and Dependabot alerts move; re-run the
  collectors in `/tmp/dep-analysis/` to refresh.
- **osv vs Dependabot vs Snyk use different advisory databases.** Absolute vulnerability counts are not
  directly comparable across tools; the direction and the direct/transitive split are the durable signals.

## External validation and concrete config changes (sourced)

A review of primary documentation (Renovate, GitHub, Trivy, OSV-Scanner) confirms the diagnosis above and
corrects one assumption. Each item below is tagged and sourced.

### Correction: `transitiveRemediation` does not help Python

`transitiveRemediation: true` works **only for npm** (via `overrides`) and Yarn (`resolutions`). For Python
(uv/poetry) it is confirmed unsupported: Renovate's Python managers only see direct dependencies in
`pyproject.toml`, not locked transitives. Since roughly 75% of this fleet's vulnerabilities are transitive and
the fleet is mostly Python, **`lockFileMaintenance` is the only mechanism that remediates Python transitive
vulnerabilities**, by regenerating the lockfile to the latest versions the direct constraints allow. The global
config enables it but with `automerge: false` on a weekly schedule, so those PRs are generated and then sit. To
actually close Python transitive vulns, `lockFileMaintenance` PRs must automerge on green.
Source: https://github.com/renovatebot/renovate/discussions/28776

### Validated config changes

1. **[permission] Confirm the Renovate token has vulnerability-alert read.** Classic PAT needs the
   `security_events` scope; fine-grained PAT or App needs "Dependabot alerts: read". Documented failure mode: a
   token lacking it makes GitHub return 403 and Renovate logs "Cannot access vulnerability alerts" and silently
   skips all vulnerability PRs (falling back to OSV only). Note a known false-positive of that same warning
   caused by a schema error on `actions`-ecosystem alerts, relevant since these repos carry many Actions alerts;
   confirm via logs, not the warning alone. Source: https://docs.renovatebot.com/security-and-permissions/

2. **[config] Make vulnerability and lockfile PRs automerge so fixes land.** Add packageRules:
   `matchManagers`/`isVulnerabilityAlert: true` with `automerge: true`, `platformAutomerge: true`,
   `minimumReleaseAge: null`; and a `lockFileMaintenance` rule with `automerge: true`. `platformAutomerge` lets
   GitHub merge after required checks pass (safer than Renovate self-merge) but requires at least one required
   status check in branch protection, or it can merge on a pending check. Vulnerability PRs already bypass
   `minimumReleaseAge`; setting it null is explicit and future-proof.
   Source: https://docs.renovatebot.com/key-concepts/automerge/

3. **[config] Make Dependabot detection-only the canonical way.** Keep "Dependabot alerts" on; disable
   "Dependabot security updates" in repo settings; set `open-pull-requests-limit: 0` per ecosystem in any
   `dependabot.yml` (the two remaining: `AMC`, `Unify`). This keeps the multi-ecosystem alert ledger while
   guaranteeing Renovate is the sole PR-opener.
   Source: https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file

4. **[config] Drop the per-repo `enabledManagers` restrictions** (the 73%-of-alerts root cause) so Renovate
   autodiscovers all managers as the global config intends, or correct each to match the actual manifests.
   Renovate's own `config:best-practices` base preset plus `osvVulnerabilityAlerts: true` and
   `dependencyDashboardOSVVulnerabilitySummary: "all"` is the recommended baseline.
   Source: https://docs.renovatebot.com/presets-config/

5. **[CI] Close the ecosystem-coverage gaps in the SBOM step.** Add `aquasecurity/trivy-action` with
   `scan-type: image` for the Dockerfile repos (`audio-processor`, `llc-manager`, `image-preprocessing-detector`,
   `rag-processor`) and the OSV-Scanner PR-diff reusable workflow for npm-frontend repos (`rag-processor`,
   `cookiecutter-python-template`), both uploading SARIF. This is what makes the in-CI detector multi-ecosystem
   rather than Python-only. Sources: https://github.com/aquasecurity/trivy-action ,
   https://google.github.io/osv-scanner/github-action/

6. **[process] Harden autodiscovery and verify prerequisites.** Consider scoping Renovate autodiscovery to an
   explicit repository list, and confirm "Dependency graph" and "Dependabot alerts" are enabled on all 24 repos
   (`gh api /repos/{owner}/{repo}/vulnerability-alerts` returns 204 when enabled; this audit found every live
   repo enabled, the only two non-204 results being a 404 orphan and an archived repo).
