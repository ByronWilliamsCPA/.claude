---
title: "Renovate Architecture & Dependency Management"
schema_type: common
status: published
owner: core-maintainer
purpose: "Authoritative reference for how Renovate is configured across the ByronWilliamsCPA and williaby fleet, including the Docker stack, global and per-repo configs, manifest enforcement, and relationships to Dependabot, SBOM generation, and (historically) dependency-review."
tags:
  - reference
  - dependencies
  - security
  - infrastructure
  - automation
---

This document is the canonical source of truth for how dependency updates and vulnerability remediation are wired across the fleet. It covers the self-hosted Renovate stack, the layered config inheritance model, manifest enforcement, and how Renovate interacts with adjacent processes (Dependabot Alerts, SBOM generation, pip-audit). It also documents the retired dependency-review workflow for historical context (see "Relationship to dependency-review" below).

## Quick Reference

| Element | Path |
| --- | --- |
| Docker stack | `homelab-infra/services/renovate/docker-compose.yml` |
| Global config (applied to all repos) | `homelab-infra/services/renovate/config/config.json` |
| Org template (BWCPA, redirects from williaby) | `ByronWilliamsCPA/.github/renovate.json` |
| Per-repo override | `{repo}/renovate.json` |
| Pre-commit validator hook (PC-016, homelab-infra only) | `homelab-infra/.pre-commit-config.yaml` |
| Manifest checks | PC-016, CI-020, CI-021, CI-058, CI-059, CI-060, CI-061, CI-063, CI-064, REPO-001, REPO-002 in `docs/standards-manifest.yaml` |
| Reusable SBOM workflow | `ByronWilliamsCPA/.github/.github/workflows/python-sbom.yml` |
| Reusable dependency-review workflow (RETIRED 2026-09, paid GHAS required) | `ByronWilliamsCPA/.github/.github/workflows/dependency-review.yml` |

## Architecture Overview

Renovate runs as a self-hosted Docker stack that processes every repo in the ByronWilliamsCPA and williaby orgs on a schedule. Configuration is layered: a global config sets fleet-wide policy, an org-level template defines per-repo defaults, and each repo can override specific keys in its own `renovate.json`. The standards manifest enforces minimum requirements at each layer.

```text
┌────────────────────────────────────────────────────────────────┐
│ LAYER 1: Docker stack (homelab-infra/services/renovate)        │
│ - renovate/renovate:43.150.0@sha256:... (digest-pinned bot)    │
│ - Loki + Promtail (log aggregation)                            │
│ - RENOVATE_BINARY_SOURCE=install (uv/poetry binary fetching)   │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 2: Global config (config/config.json)                    │
│ - enabledManagers fleet-wide (v43 includes "uv" natively)      │
│ - platformAutomerge: true (defensive explicit set, CI-064)     │
│ - vulnerabilityAlerts, osvVulnerabilityAlerts                  │
│ - lockFileMaintenance, transitiveRemediation                   │
│ - packageRules (security severity gating, automerge policy)    │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 3: Org template (ByronWilliamsCPA/.github/renovate.json) │
│ - Default per-repo enabledManagers                             │
│ - Default packageRules                                         │
│ - Auto-applied to repos that have NO renovate.json             │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 4: Per-repo config ({repo}/renovate.json)                │
│ - REPLACES (not merges) array keys from upstream layers        │
│ - Thin overlay; do NOT duplicate global packageRules (CI-063)  │
│ - May use either "uv" or "pep621" on uv-managed projects (v43) │
└────────────────────────────────────────────────────────────────┘
```

**Critical inheritance rule:** Renovate's `enabledManagers`, `packageRules`, `customManagers`, and most other array fields are **replace-not-merge**. A per-repo `enabledManagers: ["pep621"]` does not inherit additional managers from the global config; it replaces the list entirely. This is the root cause of most fleet-wide Renovate drift.

## Layer 1: Docker Stack

The Renovate bot runs in Portainer/Docker on the homelab as a non-continuous container (`restart: "no"`), triggered on a schedule via cron or systemd. Three services:

| Service | Image | Purpose |
| --- | --- | --- |
| renovate | `renovate/renovate:43.150.0@sha256:...` (digest-pinned, CI-061) | The bot itself, runs scans and opens PRs |
| loki | `grafana/loki:2.9.3` | Log aggregation for diagnostics |
| promtail | `grafana/promtail:2.9.3` | Ships container logs to Loki |

The Renovate image MUST be pinned to a 64-char sha256 digest alongside the human-readable tag (CI-061, critical). A bare tag is rejected; the canonical form is `renovate/renovate:<tag>@sha256:<digest>`. This closes the silent-upgrade vector where a re-pushed floating tag would change the running bot on the next systemd timer fire with no audit signal.

**Critical environment variables:**

| Variable | Value | Why |
| --- | --- | --- |
| `RENOVATE_TOKEN` | GitHub PAT or App token | Required for repo access AND `security_events: read` (vulnerability alerts feed) |
| `RENOVATE_BINARY_SOURCE` | `install` | Lets containerbase download the `uv` binary at runtime so `uv lock` can regenerate `uv.lock` inside a PR. Without this, every uv-project PR fails with `renovate/artifacts: FAILURE`. |
| `RENOVATE_AUTODISCOVER` | `true` | Auto-discovers BWCPA + williaby repos. |
| `RENOVATE_IGNORED_REPOS` | `["williaby/dart-frog-paludarium","williaby/homelab-agent-configs"]` | Per-repo opt-out list. These repos retain `dependabot.yml` instead. |
| `RENOVATE_ALLOWED_POST_UPGRADE_COMMANDS` | `["^echo","^uv lock","^poetry lock","^npm ci"]` | Security allowlist for postUpgradeTasks. |
| `NODE_OPTIONS` | `--max-old-space-size=3500` | V8 default heap (~1 GB) crashes on 40+ repo runs; explicit limit prevents OOM. |

**Security posture:**
- Runs as uid 1000:1000 (non-root)
- `cap_drop: ALL` + `no-new-privileges:true`
- GNUPGHOME pinned to `/tmp/renovate-gnupg` because the container image's `/home/ubuntu` is owned by a different uid (12021)
- Network isolated on dedicated bridge (`renovate-network`)
- Resource caps: 2 CPUs, 4 GB RAM, 500 MB reservation

**Operational note:** the running Renovate version is the gatekeeper for which schema features are valid. The fleet runs `v43.150.0` as of the 2026-05-25 cutover (homelab-infra PR #425). v43 accepts the `"uv"` manager identifier natively, unified the validator and server schemas, and changed the `platformAutomerge` default to `true`. The historical v42 schema-mismatch trap that motivated the never-landed PC-015 check is retired; the structural successors are CI-059 (semantic enabledManagers lint), PC-016 (global config validator, suggested), and CI-064 (explicit `platformAutomerge` setting).

## Layer 2: Global Config

`homelab-infra/services/renovate/config/config.json` is mounted into the container at `/config/config.json` and read on every run. It defines fleet-wide policy that every repo inherits (subject to per-repo overrides).

**Key fields:**

| Field | Value | Purpose |
| --- | --- | --- |
| `enabledManagers` | `pep621, uv, poetry, pip_requirements, pip-compile, github-actions, docker-compose, dockerfile, pre-commit, terraform, ansible, ansible-galaxy, npm, regex` | The complete fleet-wide allowlist of managers. Since the 2026-05-25 v43 cutover, `"uv"` is a first-class manager identifier; `pep621` continues to handle the generic PEP 621 path for repos that have not added `"uv"` explicitly. |
| `platformAutomerge` | `true` | Causes Renovate to enable GitHub native auto-merge on every PR it opens. Set explicitly (CI-064, suggested) rather than relying on the v40+ default; defensive against another silent default flip. Pairs with REPO-001 (`allow_auto_merge=true` at the repo level), which GitHub requires before any PR in the repo can have auto-merge enabled. |
| `vulnerabilityAlerts.enabled` | `true` | Subscribes Renovate to GitHub's Dependabot Alerts feed for security PRs. Requires `security_events: read` on the PAT. |
| `osvVulnerabilityAlerts` | `true` | Adds Open Source Vulnerabilities (OSV) database as a second source. Catches CVEs not yet in GHSA. |
| `transitiveRemediation` | `true` | Deep-patches lockfiles to address CVEs in indirect dependencies. |
| `lockFileMaintenance.enabled` | `true` | Weekly Monday job to regenerate lockfiles even without dependency changes. Critical for catching newly-disclosed CVEs in pinned transitive deps. |
| `minimumReleaseAge` | `3 days` | Default stability gate. Vulnerability PRs override this via packageRules. |
| `autodiscoverFilter` | `["ByronWilliamsCPA/*", "williaby/*"]` | Scope guard. |

**Vulnerability handling (priority order):**

1. **CRITICAL/HIGH CVEs:** `minimumReleaseAge: 0 days`, `prPriority: 20`, automerge if CI passes
2. **MEDIUM CVEs:** `minimumReleaseAge: 2 days`, `prPriority: 10`
3. **LOW/UNKNOWN CVEs:** `minimumReleaseAge: 7 days`, `prPriority: 1`
4. **All vulnerability alerts:** bypass grouping and schedule, fire immediately

All of these are configured via `matchJsonata` expressions in packageRules, e.g.:
```json
"matchJsonata": ["isVulnerabilityAlert = true and (vulnerabilitySeverity = 'CRITICAL' or vulnerabilitySeverity = 'HIGH')"]
```

## Layer 3: Org Template

`ByronWilliamsCPA/.github/renovate.json` defines the default per-repo config inherited by any BWCPA or williaby repo that has no `renovate.json` of its own. (The `williaby/.github` URL is an HTTP 301 redirect to `ByronWilliamsCPA/.github`; same underlying repo ID 975216077, so both orgs share the same defaults.)

This template is intentionally narrower than the global config. It declares the most common managers that downstream repos need (`pep621`, `pip_requirements`, `github-actions`) without dragging in container, terraform, or ansible managers that are only relevant to homelab-infra.

**Canonical content:**
```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:recommended",
    ":dependencyDashboard",
    ":semanticCommits",
    ":preserveSemverRanges"
  ],
  "enabledManagers": ["pep621", "pip_requirements", "github-actions"],
  ...
}
```

When changing this file, remember: the org template is consumed by every BWCPA + williaby repo without its own `renovate.json`. A broken template silently breaks every downstream Renovate run.

## Layer 4: Per-Repo Config

Only override the org template when the repo has manager needs the template doesn't cover. Common reasons:

| Reason | What to add |
| --- | --- |
| Repo uses npm | `"npm"` to `enabledManagers` |
| Repo has Dockerfile | `"dockerfile"` to `enabledManagers` |
| Repo uses docker-compose | `"docker-compose"` to `enabledManagers` |
| Repo uses Terraform | `"terraform"` to `enabledManagers` |
| Repo uses custom version markers in workflow YAML | `customManagers` block with regex |
| Repo's lockfile maintenance schedule differs from default | `lockFileMaintenance` override |

**Forbidden values:**

| Value | Why |
| --- | --- |
| `"poetry"` in `enabledManagers` for a uv-managed repo | `poetry` manager looks for `[tool.poetry]`, not `[project]`; silently produces zero PRs. |
| Removing `pep621` from `enabledManagers` on a repo that has not explicitly added `"uv"` | Under v43 `pep621` still handles the generic PEP 621 path for repos that have not migrated their config to `"uv"`. Dropping `pep621` without adding `"uv"` leaves the repo with no manager for `pyproject.toml` and silently produces zero PRs. |
| `matchSeverity` in packageRules | Use `matchJsonata` on `vulnerabilitySeverity` instead. |
| `fileMatch` in customManagers | Renamed to `managerFilePatterns` in v43. Old key is silently ignored. |
| Duplicating global `packageRules` in per-repo `renovate.json` | Renovate uses replace-not-merge semantics on arrays; the per-repo array shadows the global one. If the global rules later change, the per-repo override continues applying the stale set. (CI-063, suggested.) |

**Historical pitfalls retired by the v43 cutover** (preserved here so audits do not re-flag them as regressions in old PRs or commits):

| Value | Why it mattered under v42 | Status under v43 |
| --- | --- | --- |
| `"uv"` in `enabledManagers` | v42 had no `uv` manager identifier; the entire config was rejected and Renovate produced zero PRs. | `"uv"` is a first-class manager. |
| `prPriority` under `vulnerabilityAlerts` | Only valid under `packageRules` in v42. | v43 relaxed the placement constraint. |

**Per-repo config template (minimal, uv project):**
```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "enabledManagers": ["pep621", "github-actions"]
}
```

That's it. Inheritance from the global config handles vulnerabilityAlerts, lockFileMaintenance, packageRules, etc.

## Standards Manifest Enforcement

The repo-compliance system enforces Renovate hygiene via the following manifest checks. PC-015 was a historical placeholder for a v42-era validator pin lockstep and was never landed; the manifest header explicitly retires it.

| Check | Severity | Purpose |
| --- | --- | --- |
| **PC-016** | suggested | Global Renovate config at `homelab-infra/services/renovate/config/config.json` validates clean against renovate-config-validator pinned to the same major version as the running Docker image. Defensive against forward-compat issues with a future v44 schema. Applies only to homelab-infra. |
| **CI-020** | important | `renovate.json` present at repo root |
| **CI-021** | important | `dependabot.yml` absent when `renovate.json` is present (no duplicate PR engines) |
| **CI-058** | suggested | python-sbom.yml reusable workflow called via SHA-pinned ref (not @main, not @vN) |
| **CI-059** | suggested | renovate.json effective enabledManagers includes every manager required by the detected ecosystem files (catches the uv-trap class of silent-failure) |
| **CI-060** | suggested | Third-party Action `uses:` references in workflows are full 40-char SHA pins |
| **CI-061** | critical | Renovate Docker image is digest-pinned (`renovate/renovate:<tag>@sha256:<64-hex>`), not a bare tag |
| **CI-063** | suggested | Per-repo `renovate.json` is a thin overlay; does not duplicate global `packageRules` or `groupName` entries |
| **CI-064** | suggested | Global config explicitly sets `platformAutomerge: true` rather than relying on the v40+ default |
| **REPO-001** | critical | Repository setting `allow_auto_merge=true` at the GitHub API level (without this, GitHub silently refuses every bot auto-merge request) |
| **REPO-002** | important | Repository setting `delete_branch_on_merge=true` (prevents stale Renovate branches from accumulating after merge) |

**Why REPO-001 is critical for Renovate:** Renovate's `platformAutomerge: true` triggers a GraphQL `enablePullRequestAutoMerge` call on every PR it opens. If the target repo has `allow_auto_merge=false`, that call fails silently and the PR opens without auto-merge attached. The 2026-05-26 audit found 11 of 42 repos in this state, blocking the entire Renovate auto-merge pipeline despite an otherwise-correct global config.

**Renovate version bumps no longer require validator lockstep.** v43 unified the validator and server schemas, so a single PC-016 pin (homelab-infra only) is sufficient. Per-repo `.pre-commit-config.yaml` files no longer need a `renovate-config-validator` hook.

## Relationship to Dependabot

Dependabot has three independent features. Only one is used; the other two are explicitly disabled in favor of Renovate.

| Feature | Status | Rationale |
| --- | --- | --- |
| **Dependabot Alerts** | ENABLED on every active repo | Feeds GitHub's Advisory Database (GHSA) into both the Security tab AND Renovate's `vulnerabilityAlerts` config. Free, GitHub-native, no PR duplication risk. |
| **Dependabot Security Updates** | DISABLED (long-term target) | Currently kept on as a safety net for repos where Renovate is misconfigured. Will be disabled fleet-wide after the broken-config remediation completes and verification shows Renovate is opening security PRs for everything Dependabot was. |
| **Dependabot Version Updates** | DISABLED | `dependabot.yml` is forbidden when `renovate.json` is present (CI-021). Running both creates duplicate PRs and conflicting automerge rules. |

**Why this layering works:**
- GHSA (Dependabot's data source) → flows to GitHub Alerts feed → consumed by Renovate's `vulnerabilityAlerts.enabled: true`
- OSV (Renovate's second data source) → consumed by `osvVulnerabilityAlerts: true`
- Net: Renovate's coverage is a **strict superset** of Dependabot Security Updates when configured correctly.

**Audit reference:** `docs/audits/dependabot-renovate-coverage-2026-05-24.md` mapped 350 open Dependabot alerts to their corresponding Renovate config state. 0 alerts were classified as `ECOSYSTEM_NOT_COVERED`, confirming Renovate's reach is complete; 47% were `BLOCKED_BY_CONFIG` due to invalid `enabledManagers`, which is the gap the May 2026 + this-session remediation closes.

**Two specific exceptions retain Dependabot Version Updates:**
- `williaby/dart-frog-paludarium`
- `williaby/homelab-agent-configs`

Both are in `RENOVATE_IGNORED_REPOS` in the docker-compose env and may keep `dependabot.yml` as their sole update manager. CI-020/CI-021 mark them as N/A.

## Relationship to SBOM Generation

The reusable `python-sbom.yml` workflow in `ByronWilliamsCPA/.github` generates a CycloneDX SBOM and scans it for vulnerabilities on every PR and push. It is **independent of Renovate** but addresses an adjacent concern.

| Tool | Role | Trigger |
| --- | --- | --- |
| `cyclonedx-bom==7.3.0` | Generate SBOM from installed environment | Workflow `Generate SBOMs` job |
| `grype` (gating) | Scan SBOM for known CVEs (CRITICAL/HIGH by default) | Workflow `Scan Runtime Dependencies` job |
| `osv-scanner` (gating, keyless) | Scan SBOM for known CVEs across OSV/GHSA/NVD/PyPI | Workflow `Scan Runtime Dependencies (OSV-Scanner)` job |
| License compliance check | Block forbidden SPDX licenses (default: GPL/AGPL family) | Workflow `License Compliance Check` job |

**Trivy-to-Grype cutover complete (issue ByronWilliamsCPA/.github#152):** Grype
(Anchore) replaced Trivy as the gating runtime-dependency CVE scanner. Trivy's release
infrastructure was compromised in March 2026 with vulnerability-database updates
suspended, making the scanner itself a supply-chain risk. A parallel-run window
confirmed package-level and severity-level detection parity (Grype missed nothing
Trivy caught, at identical CVSS scores including HIGH findings) before the cutover
landed. The promoted Grype job keeps the `Scan Runtime Dependencies` status-check name
the former Trivy job used, so consumer rulesets are unaffected. OSV-Scanner remains a
second keyless gate.

**Workflow inputs:**
- `python-version`: which interpreter to scan against
- `fail-on-vulnerabilities`: true by default; blocks merge on CRITICAL/HIGH
- `severity-threshold`: defaults to `CRITICAL,HIGH`
- `forbidden-licenses`: JSON array of SPDX IDs
- `grype-config-path`: `.grype.yaml` to suppress known CVEs in Grype
  (default `.grype.yaml`). The former `trivyignore-path` input was removed at the
  issue ByronWilliamsCPA/.github#152 cutover.

**How SBOM and Renovate interact:**
1. Renovate proposes a dependency PR (routine or vulnerability-triggered).
2. The PR triggers CI, which runs `python-sbom.yml`.
3. Grype scans the post-update SBOM. If a CRITICAL/HIGH CVE remains, CI fails and the PR
   cannot merge. OSV-Scanner scans the same SBOM as a second keyless gate.
4. If Grype finds a CVE Renovate doesn't know about (e.g., not yet surfaced as a Renovate
   update), the SBOM scan blocks the PR even though Renovate would have allowed it.
   Grype's and OSV's independent databases provide cross-checks against each other.

**Net effect:** SBOM scanning is the *last line of defense* against vulnerable dependencies sneaking into main. It does not generate PRs; it gates them. The 90-day artifact retention preserves SBOMs for audit.

## Relationship to dependency-review (RETIRED 2026-09)

> **Retired.** `actions/dependency-review-action` now requires paid GitHub Advanced Security
> (Code Security) on every repo, public or private; the free-tier capability this section
> describes no longer exists. `dependency-review.yml` callers were removed fleet-wide. This
> section is kept for historical context and to explain what the SBOM workflow now covers
> alone. The manifest checks that enforced this workflow, CI-036 and CI-081, were retired as
> deprecated stubs in `docs/standards-manifest.yaml`.

The `dependency-review.yml` reusable workflow ran on every pull request to main and used GitHub's `dependency-review-action`. It checked the *diff* of dependencies in a PR against GHSA and a license allowlist.

| Setting | Value |
| --- | --- |
| Trigger | `pull_request: branches: [main]` |
| Failure threshold | `fail-on-severity: high` |
| Allowed licenses | `MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, CC0-1.0, CC-BY-4.0` |

**How it differs from SBOM:**
- SBOM scans the **entire installed environment** for vulnerabilities; dependency-review scans **only the diff**.
- SBOM uses Grype plus OSV-Scanner (see ByronWilliamsCPA/.github#152); dependency-review
  uses GitHub's GHSA directly.
- SBOM persists artifacts (90 days); dependency-review is ephemeral check-run output.

**How it differs from Renovate:**
- Renovate **proposes** updates; dependency-review **gates** them.
- Renovate operates on a schedule (or webhook); dependency-review operates on PR events.

## Relationship to pip-audit

`pip-audit` is required as a dev dependency on every Python repo (TOOL-006, severity: critical). Unlike the workflow-based tools above, it runs **locally** during development.

| Aspect | pip-audit | Renovate | SBOM workflow |
| --- | --- | --- | --- |
| Where it runs | Developer machine + CI | Self-hosted Docker | GitHub Actions |
| What it scans | Installed environment | Lockfile + manifest | Generated SBOM |
| Data source | PyPI Advisory DB | OSV + GHSA | Anchore Grype DB + OSV-Scanner |
| Output | CLI report | PR | SARIF + artifact |
| Cadence | On-demand | Scheduled + on PR | On every PR |

**The three layers compose:**
1. **pip-audit** catches CVEs at development time (fastest feedback).
2. **Renovate** proposes upgrades to fix CVEs at scheduled cadence.
3. **SBOM workflow** scans the final post-PR state and blocks merges with remaining CRITICAL/HIGH issues.

**Unfixed CVEs:** When pip-audit finds a vulnerability that cannot be immediately resolved, it must be documented in `docs/known-vulnerabilities.md` using the template at `docs/known-vulnerabilities-template.md`. Review quarterly. No entry ages past 60 days without reassessment. The OpenSSF release gate blocks releases for any vulnerability older than 60 days regardless of reassessment status. See `CLAUDE.md` § "Unfixed CVEs" for the full process.

## End-to-End Flow Examples

### Routine dependency update
1. Renovate (homelab Docker) wakes on schedule, scans BWCPA and williaby orgs.
2. Reads each repo's effective config: docker-compose env → global config → org template → per-repo override.
3. Detects a new `pydantic` minor version via pep621 manager.
4. Opens PR, signed by `Renovate Bot <renovate@byronwilliams.dev>`.
5. CI runs: tests, `python-sbom.yml` (SBOM + Grype/OSV scan), pip-audit (if in dev deps).
6. All checks pass; Renovate's automerge rule fires after the 3-day stability window.
7. PR auto-merges via squash.

### Critical CVE in transitive dep
1. New GHSA published for a transitive dep in `uv.lock`.
2. GitHub Dependabot Alerts surfaces the CVE in the Security tab.
3. Next Renovate run picks up the alert via `vulnerabilityAlerts.enabled: true`.
4. `transitiveRemediation` instructs Renovate to bump the lockfile entry, not the top-level dep.
5. Renovate runs `uv lock` via `RENOVATE_BINARY_SOURCE=install` to regenerate `uv.lock`.
6. PR opens with `prPriority: 20`, `minimumReleaseAge: 0 days`, labels `["security"]`.
7. CI passes; PR auto-merges immediately (no stability gate for CRITICAL/HIGH CVEs).
8. Dependabot Alert closes automatically when the merge lands.

### Renovate config drift (semantic mismatch, post-v43)

1. Someone declares `enabledManagers: ["poetry"]` on a uv-managed repo (the project has `[project]` in pyproject.toml, not `[tool.poetry]`).
2. The config validator passes (the manager identifier is valid), so PC-016 does not fire.
3. The next Renovate run completes with zero PRs because the `poetry` manager finds nothing to manage on this repo. No error is logged; the repo silently stops getting dependency updates.
4. **CI-059** (semantic enabledManagers lint) is the structural guard: it reads the repo's file inventory and verifies that every detected ecosystem has a matching manager in the effective config. CI-059 flags this case as a finding even though the validator passed.

This is the post-v43 equivalent of the v42-era "uv-trap" pattern. v43 made the validator stricter on identifier names, but the semantic-coverage class of failure (right name, wrong manager for this repo's actual ecosystem) is structurally distinct and required its own check.

### Stuck pre-cutover PRs (the 2026-05-25 incident class)

1. Renovate v42 opened PRs on dozens of repos without enabling GitHub native auto-merge (v42 default behavior).
2. The homelab Docker image was bumped to v43 (cutover PR #425, 2026-05-25). v43's new default attaches `platformAutomerge` to newly created PRs.
3. **Pre-cutover PRs do not get retroactively patched.** Renovate does not click the auto-merge button on existing PRs when its defaults change.
4. Fleet symptom: every PR created before 2026-05-25 sits open without auto-merge; every PR created after 2026-05-25 auto-merges normally.
5. Diagnosis: correlate stuck-PR creation timestamps with the cutover date, not config-file state. See the Cutover Playbook section below.

## Common Pitfalls

| Pitfall | Symptom | Fix |
| --- | --- | --- |
| Declaring `enabledManagers: ["poetry"]` on a uv-managed repo | Renovate runs cleanly but produces zero PRs (poetry manager finds nothing) | Use `["pep621"]` or `["uv"]`; CI-059 catches this |
| Using `dependabot.yml` alongside `renovate.json` | Duplicate PRs, conflicting automerge | Delete `dependabot.yml` (CI-021) |
| Forgetting `RENOVATE_BINARY_SOURCE=install` | uv.lock PRs fail with `artifacts: FAILURE` | Set env var in docker-compose |
| Pinning the Docker image to a bare tag | Re-pushed upstream tag silently changes the running bot at the next timer fire | Pin to `renovate/renovate:<tag>@sha256:<digest>` (CI-061) |
| Repo has `allow_auto_merge=false` at the GitHub settings layer | Renovate's `platformAutomerge: true` is silently ignored on this repo; PRs open without auto-merge | Run `gh api repos/<org>/<repo> -X PATCH -f allow_auto_merge=true` (REPO-001) |
| Per-repo `renovate.json` redeclaring global `packageRules` | Global rule changes silently shadowed by stale per-repo overlay | Audit per-repo files for redundancy (CI-063); keep overlays thin |
| Per-repo `enabledManagers` with one entry, expecting merge | Other managers silently disabled | Renovate replaces, does not merge; list every manager you need |

## Cutover Playbook: Bumping the Renovate Major Version

When the homelab Renovate Docker image is upgraded to a new major version (e.g. v42 → v43), do all of these in a single coordinated PR set, then run the post-cutover cleanup. The playbook is derived from the 2026-05-26 Renovate auto-merge fleet rollout, which surfaced two recurring lessons: required-check verification methodology and the post-cutover PR cleanup phase.

### Phase 1: Schema audit and config fixes

1. **Read the upstream changelog** for the new major. Identify breaking schema changes (e.g., the v42→v43 `fileMatch` → `managerFilePatterns` rename, `matchSeverity` placement changes, `prPriority` placement under `vulnerabilityAlerts`, default behavior flips like `platformAutomerge`).
2. **Audit existing configs** for any uses of deprecated syntax. The renovate-config-validator pinned to the *new* version is the easiest way: run it against every `renovate.json` in the fleet and collect failures.
3. **Open per-repo fix PRs** for each failing config, using the new syntax.
4. **Identify default-behavior changes** that the validator does NOT flag (e.g., the v43 `platformAutomerge` default flip). For each, add an explicit setting to the global config so that future default flips do not silently change behavior again. (CI-064 is the manifest record of one such defensive setting.)

### Phase 2: Image deploy

5. **Update the Docker image tag AND sha256 digest** in `homelab-infra/services/renovate/docker-compose.yml`. The canonical form is `renovate/renovate:<tag>@sha256:<digest>` (CI-061).
6. **Update PC-016 in the standards manifest** if the validator version pin needs to track a new major.
7. **Deploy the new image** and watch the first run logs for `Config validation errors found`.
8. **If any repo's config rejects on the new server,** roll back the Docker image immediately and fix the per-repo config before re-attempting.

### Phase 3: Post-cutover PR cleanup (do not skip)

Bot upgrades do not retroactively change behavior on PRs that already exist. The 2026-05-26 audit found 54 PRs stuck open across both orgs because pre-cutover Renovate (v42) had opened them without `platformAutomerge` attached and v43 does not retroactively click the auto-merge button. The cleanup is mechanical but invisible if you do not know to look for it.

9. **List all open Renovate PRs** that pre-date the cutover commit timestamp:
   ```bash
   gh search prs --state open --author "@me" --created "<YYYY-MM-DD" \
     --json repository,number,title,headRefName \
     --jq '.[] | select(.headRefName | startswith("renovate/"))'
   ```
   (Filter by `headRefName`, not author: self-hosted Renovate authenticates as a PAT and shows the human user as PR author, per L-004.)
10. **Close each pre-cutover PR with an explanatory comment** referencing the cutover commit SHA. Renovate will recreate them on the next scheduled run with the new defaults attached.
11. **Exclude from cleanup:** major-version bumps (intentional manual review per the global config's `automerge: false` for majors), in-progress human-authored config PRs, and any PR explicitly marked "abandoned" in the title (closing it would erase the abandonment signal).
12. **Verify auto-merge attachment on recreated PRs:**
    ```bash
    gh pr list -R <org>/<repo> --json number,autoMergeRequest \
      --jq '.[] | select(.autoMergeRequest == null) | .number'
    ```
    Any number returned is a PR that still lacks auto-merge after recreation; investigate before closing more PRs.

### Diagnostic pattern: cutover date as fleet-failure signal

When investigating "why is X intermittently broken across the fleet," check whether the failure correlates with a single bot or runtime upgrade date before inspecting per-repo configs. In the 2026-05-26 audit every stuck PR predated the v43 cutover and every auto-merging PR postdated it. This was a far cleaner diagnostic than reading 42 `renovate.json` files. The signal generalizes: any fleet-wide bot, runner, or reusable workflow upgrade can present as "config drift" when it is actually a cutover artifact.

### Verification methodology (do not use commit check-runs)

Verifying required-check coverage after a cutover: query `gh pr view <PR> --json statusCheckRollup` on a recent merged PR. Do NOT use `gh api repos/<owner>/<repo>/commits/<sha>/check-runs` on main HEAD; workflows triggered by `pull_request` events do not re-run on the merge commit and are absent from commit-level check-runs. See `docs/reference/repo-compliance.md` § "Audit methodology gotchas".

## References

- **Memory entry:** `feedback_renovate_uv_manager_trap.md`: full incident history for the v42-era uv manager mistake (retired by the v43 cutover; preserved for context)
- **Memory entry:** `project_renovate_selfhost_architecture.md`: notes on the PAT auth model and `headRefName` filter pattern
- **Audit report:** `docs/audits/dependabot-renovate-coverage-2026-05-24.md`: fleet-wide coverage analysis (BLOCKED_BY_CONFIG breakdown)
- **Standards manifest:** `docs/standards-manifest.yaml`: PC-016, CI-020/CI-021, CI-058 through CI-064, REPO-001, REPO-002
- **Renovate upstream docs:** https://docs.renovatebot.com/ (current v43 schema)
- **CycloneDX:** https://cyclonedx.org/specification/ (SBOM format)
- **GHSA vs OSV:** https://github.com/github/advisory-database vs https://osv.dev/
- **CLAUDE.md** § "Unfixed CVEs": pip-audit suppression policy
