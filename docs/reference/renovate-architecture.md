---
title: "Renovate Architecture & Dependency Management"
schema_type: common
status: published
owner: core-maintainer
purpose: "Authoritative reference for how Renovate is configured across the ByronWilliamsCPA and williaby fleet, including the Docker stack, global and per-repo configs, manifest enforcement, and relationships to Dependabot, SBOM generation, and dependency-review."
tags:
  - reference
  - dependencies
  - security
  - infrastructure
  - automation
---

This document is the canonical source of truth for how dependency updates and vulnerability remediation are wired across the fleet. It covers the self-hosted Renovate stack, the layered config inheritance model, manifest enforcement, and how Renovate interacts with adjacent processes (Dependabot Alerts, SBOM generation, dependency-review, pip-audit).

## Quick Reference

| Element | Path |
| --- | --- |
| Docker stack | `homelab-infra/services/renovate/docker-compose.yml` |
| Global config (applied to all repos) | `homelab-infra/services/renovate/config/config.json` |
| Org template (BWCPA, redirects from williaby) | `ByronWilliamsCPA/.github/renovate.json` |
| Per-repo override | `{repo}/renovate.json` |
| Pre-commit validator hook (PC-016) | `homelab-infra/.pre-commit-config.yaml` |
| Manifest checks | TOOL-013, PC-016, CI-020, CI-021, CI-059, CI-061 in `docs/standards-manifest.yaml` |
| Reusable SBOM workflow | `ByronWilliamsCPA/.github/.github/workflows/python-sbom.yml` |
| Reusable dependency-review workflow | `ByronWilliamsCPA/.github/.github/workflows/dependency-review.yml` |

## Architecture Overview

Renovate runs as a self-hosted Docker stack that processes every repo in the ByronWilliamsCPA and williaby orgs on a schedule. Configuration is layered: a global config sets fleet-wide policy, an org-level template defines per-repo defaults, and each repo can override specific keys in its own `renovate.json`. The standards manifest enforces minimum requirements at each layer.

```text
┌────────────────────────────────────────────────────────────────┐
│ LAYER 1: Docker stack (homelab-infra/services/renovate)        │
│ - renovate/renovate:42.92 (the actual bot)                     │
│ - Loki + Promtail (log aggregation)                            │
│ - RENOVATE_BINARY_SOURCE=install (uv/poetry binary fetching)   │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 2: Global config (config/config.json)                    │
│ - enabledManagers fleet-wide                                   │
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
│ - Must include pep621 if the repo is uv-managed                │
│ - Effective enabledManagers audited by CI-059 (semantic lint)  │
└────────────────────────────────────────────────────────────────┘
```

**Critical inheritance rule:** Renovate's `enabledManagers`, `packageRules`, `customManagers`, and most other array fields are **replace-not-merge**. A per-repo `enabledManagers: ["pep621"]` does not inherit additional managers from the global config; it replaces the list entirely. This is the root cause of most fleet-wide Renovate drift.

## Layer 1: Docker Stack

The Renovate bot runs in Portainer/Docker on the homelab as a non-continuous container (`restart: "no"`), triggered on a schedule via cron or systemd. Three services:

| Service | Image | Purpose |
| --- | --- | --- |
| renovate | `renovate/renovate:42.92` | The bot itself, runs scans and opens PRs |
| loki | `grafana/loki:2.9.3` | Log aggregation for diagnostics |
| promtail | `grafana/promtail:2.9.3` | Ships container logs to Loki |

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

**Operational note:** the running Renovate version is the gatekeeper for which schema features are valid. The homelab-infra v43 cutover (PR #425) unified the validator and server schemas, so the historical v42-era "validator pinned in lockstep with the server" risk no longer applies. CI-061 (critical) enforces that the Docker image stays digest-pinned so the running server cannot silently drift. See the Standards Manifest Enforcement section below.

## Layer 2: Global Config

`homelab-infra/services/renovate/config/config.json` is mounted into the container at `/config/config.json` and read on every run. It defines fleet-wide policy that every repo inherits (subject to per-repo overrides).

**Key fields:**

| Field | Value | Purpose |
| --- | --- | --- |
| `enabledManagers` | `pep621, poetry, pip_requirements, pip-compile, github-actions, docker-compose, dockerfile, pre-commit, terraform, ansible, ansible-galaxy, npm, regex` | The complete fleet-wide allowlist of managers. **Does NOT include `uv`** because v42.x has no `uv` manager identifier; `pep621` handles uv-managed `pyproject.toml`. |
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
| `"uv"` in `enabledManagers` | Renovate v42.x rejects this; silently breaks the entire config. Use `"pep621"` instead. |
| `"poetry"` in `enabledManagers` for a uv-managed repo | `poetry` manager looks for `[tool.poetry]`, not `[project]`; silently produces zero PRs. |
| `matchSeverity` in packageRules | Not a valid v42 field; use `matchJsonata` on `vulnerabilitySeverity`. |
| `fileMatch` in customManagers | Renamed to `managerFilePatterns` in newer Renovate. |
| `prPriority` under `vulnerabilityAlerts` | Only valid under `packageRules` in v42; v43 relaxed this. |

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

The repo-compliance system enforces Renovate hygiene via six manifest checks:

| Check | Severity | Purpose |
| --- | --- | --- |
| **TOOL-013** | critical | uv is the primary Python package manager; `[tool.poetry]` is forbidden, `uv.lock` is required alongside `[project]` table |
| **PC-016** | suggested | `.pre-commit-config.yaml` includes `renovate-config-validator`; no version pin lockstep with the running server |
| **CI-020** | important | `renovate.json` present at repo root |
| **CI-021** | important | `dependabot.yml` absent when `renovate.json` is present (no duplicate PR engines) |
| **CI-059** | suggested | `renovate.json` effective `enabledManagers` (after org template inheritance) covers every detected ecosystem in the repo |
| **CI-061** | critical | Renovate Docker image in `homelab-infra` is `sha256:` digest-pinned |

**PC-016 is a syntactic validator, not a version-pinned tripwire.** The v43 cutover unified the validator and server schemas, so the v42-era pre-commit pin (the retired "PC-015" placeholder hook) is no longer load-bearing. PC-016 keeps a config-validator hook in place at the homelab-infra layer to catch outright schema-invalid configs at commit time, without the lockstep maintenance burden the retired check required.

**CI-059 is the structural successor to the retired schema-pin check.** It runs at CI time and lints effective `enabledManagers` (after org template inheritance, with Renovate's replace-not-merge array semantics applied) against the ecosystem files actually present in each repo. This catches a strictly larger class of bug than the v42-era validator-pin approach ever could: cases like `"poetry"` declared for a uv-managed project, or a per-repo override silently dropping `pep621`, which are syntactically valid but semantically broken. See `feedback_renovate_uv_manager_trap.md` in the memory store.

**CI-061 closes the silent-upgrade vector at the Docker layer.** The Renovate self-hosted image in `homelab-infra/services/renovate/docker-compose.yml` must match `renovate/renovate:<tag>@sha256:<digest>` (both tag AND 64-hex digest present). A bare floating tag would let an upstream re-push silently change which image runs on the next timer fire, with no audit trail. The digest pin landed in homelab-infra PR #425; CI-061 ensures it stays in place.

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
| `trivy` | Scan SBOM for known CVEs (CRITICAL/HIGH by default) | Workflow `Scan Runtime Dependencies` job |
| License compliance check | Block forbidden SPDX licenses (default: GPL/AGPL family) | Workflow `License Compliance Check` job |

**Workflow inputs:**
- `python-version`: which interpreter to scan against
- `fail-on-vulnerabilities`: true by default; blocks merge on CRITICAL/HIGH
- `severity-threshold`: defaults to `CRITICAL,HIGH`
- `forbidden-licenses`: JSON array of SPDX IDs
- `trivyignore-path`: `.trivyignore` to suppress known CVEs (must have tracked references)

**How SBOM and Renovate interact:**
1. Renovate proposes a dependency PR (routine or vulnerability-triggered).
2. The PR triggers CI, which runs `python-sbom.yml`.
3. Trivy scans the post-update SBOM. If a CRITICAL/HIGH CVE remains, CI fails and the PR cannot merge.
4. If Trivy finds a CVE Renovate doesn't know about (e.g., not yet in OSV or GHSA), the SBOM scan blocks the PR even though Renovate would have allowed it.

**Net effect:** SBOM scanning is the *last line of defense* against vulnerable dependencies sneaking into main. It does not generate PRs; it gates them. The 90-day artifact retention preserves SBOMs for audit.

## Relationship to dependency-review

The `dependency-review.yml` reusable workflow runs on every pull request to main and uses GitHub's `dependency-review-action`. It checks the *diff* of dependencies in a PR against GHSA and a license allowlist.

| Setting | Value |
| --- | --- |
| Trigger | `pull_request: branches: [main]` |
| Failure threshold | `fail-on-severity: high` |
| Allowed licenses | `MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, CC0-1.0, CC-BY-4.0` |

**How it differs from SBOM:**
- SBOM scans the **entire installed environment** for vulnerabilities; dependency-review scans **only the diff**.
- SBOM uses Trivy (broader CVE coverage); dependency-review uses GitHub's GHSA directly.
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
| Data source | PyPI Advisory DB | OSV + GHSA | Trivy DB |
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
5. CI runs: tests, `python-sbom.yml` (SBOM + Trivy scan), `dependency-review.yml`, pip-audit (if in dev deps).
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

### Broken Renovate config (the May 2026 incident class, post v43 cutover)
1. Someone edits `renovate.json` and either writes an outright schema-invalid key, or declares a manager (e.g., `"poetry"`) that does not match the ecosystem files actually in the repo.
2. **PC-016 (syntactic gate):** if the change is schema-invalid, the renovate-config-validator pre-commit hook exits non-zero on the homelab-infra config layer and blocks the commit at author time. Catches the outright-malformed class at the cheapest possible point.
3. **CI-059 (semantic gate):** for changes that pass schema validation but break ecosystem coverage (e.g., `"poetry"` declared for a uv-managed repo, or a per-repo override silently dropping `pep621` via replace-not-merge), the CI lint reads the effective `enabledManagers` after org-template inheritance and compares it to the detected ecosystem files. It surfaces the gap on the PR rather than letting Renovate go silent for months. This is the structurally larger class of bug that the retired v42-era schema-pin check never caught even in principle.

## Common Pitfalls

| Pitfall | Symptom | Fix |
| --- | --- | --- |
| Adding `"uv"` to enabledManagers | Renovate rejects entire config; zero PRs | Use `"pep621"` |
| Removing `pep621` thinking `"uv"` will work | Same as above | Restore `pep621` |
| Using `dependabot.yml` alongside `renovate.json` | Duplicate PRs, conflicting automerge | Delete `dependabot.yml` (CI-021) |
| Forgetting `RENOVATE_BINARY_SOURCE=install` | uv.lock PRs fail with `artifacts: FAILURE` | Set env var in docker-compose |
| Homelab Renovate image left as a bare floating tag | Upstream re-push silently changes which image runs on the next timer fire; no audit trail in PR diff | Pin `renovate/renovate:<tag>@sha256:<digest>` (CI-061 enforces); use `pinDigests: true` packageRule for ongoing bumps |
| Per-repo manager list does not cover actual ecosystem (e.g., `"poetry"` only on a uv repo) | Schema-valid but Renovate produces zero PRs | List every manager the ecosystem files require; CI-059 audits the effective list |
| Per-repo `enabledManagers` with one entry, expecting merge | Other managers silently disabled | Renovate replaces, does not merge; list every manager you need |

## Upgrade Procedure: Bumping the Renovate Major Version

When the homelab Renovate Docker image is upgraded to a new major version (e.g. v42 → v43), do all of these in a single coordinated PR set:

1. **Read the upstream changelog** for the new major. Identify breaking schema changes (e.g., the v42→v43 fileMatch→managerFilePatterns rename, matchSeverity placement changes, prPriority placement under vulnerabilityAlerts).
2. **Audit existing configs** for any uses of the deprecated syntax. The renovate-config-validator pinned to the *new* version is the easiest way: run it against every `renovate.json` in the fleet and collect failures.
3. **Open per-repo fix PRs** for each failing config, using the new syntax.
4. **Update the homelab-infra PC-016 pre-commit hook** `additional_dependencies` pin to the new Renovate major. Per-repo `.pre-commit-config.yaml` files do not need lockstep updates anymore; the v43-era validator and server share a unified schema.
5. **Update the Docker image tag AND digest** in `homelab-infra/services/renovate/docker-compose.yml`. The image reference must remain in the `renovate/renovate:<tag>@sha256:<digest>` form that CI-061 enforces.
6. **Deploy the new image** and watch the first run logs for `Config validation errors found`.
7. **If any repo's config rejects on the new server,** roll back the Docker image immediately and fix the per-repo config before re-attempting.
8. **Re-run the CI-059 lint** against every repo with a `renovate.json` once the new server is live, to confirm no per-repo override silently dropped a required manager during the migration.

**Atomic image bumps.** The Docker image tag and `sha256:` digest must change together (CI-061); a tag-only bump leaves the silent-upgrade vector open and breaks the audit trail in the docker-compose diff.

## References

- **Memory entry:** `feedback_renovate_uv_manager_trap.md`: full incident history for the uv manager mistake
- **Audit report:** `docs/audits/dependabot-renovate-coverage-2026-05-24.md`: fleet-wide coverage analysis
- **Standards manifest:** `docs/standards-manifest.yaml`: TOOL-013, PC-016, CI-020, CI-021, CI-059, CI-061
- **Renovate upstream docs:** https://docs.renovatebot.com/ (use only when cross-checking against the v42 schema)
- **CycloneDX:** https://cyclonedx.org/specification/ (SBOM format)
- **GHSA vs OSV:** https://github.com/github/advisory-database vs https://osv.dev/
- **CLAUDE.md** § "Unfixed CVEs": pip-audit suppression policy
