---
title: "ADR-009: Snyk Role Consolidation, Always-On Authoring, and Dependency Provenance"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Records Snyk's consolidated role across the fleet, the always-on authoring MCP decision and its quota trade-off, and the two-layer dependency-provenance design (deterministic CI data plus local cross-repo interpretation)."
tags:
  - adr
  - decisions
  - compliance
  - security
  - architecture
---

> **Status**: Proposed
>
> **Decision date**: 2026-06-29
>
> **Deciders**: Byron Williams

## Context

Snyk is deployed across four surfaces in this fleet: the CI/CD reusable
workflows (`ByronWilliamsCPA/.github`), the Claude Code MCP server (authoring),
the VS Code extension (IDE panel), and the Snyk web UI (SCM-integrated
dashboard). The CI layer is mature: ADR-003 in `ByronWilliamsCPA/.github`
establishes Snyk Code as the primary SAST gate, Open Source as advisory, and
IaC plus AIBOM as owned, with a weekly `sbom-nightly` cron pattern. This repo's
[ADR-008](ADR-008-scanner-allowlist-tiers.md) classifies Snyk as
`advisory_by_intent` in the scanner allowlist, consistent with the
Open-Source-stays-advisory stance.

The authoring layer was not mature. Three problems motivated this ADR:

1. **Wrong MCP tool names.** The authoring standards documented `snyk_test`,
   `snyk_code_test`, and `snyk_monitor`. Direct `tools/list` introspection of
   the running Snyk MCP server shows the real names are `snyk_sca_scan`,
   `snyk_code_scan`, and that `monitor` is a CLI-only command with no MCP tool.
   An agent following the old docs called tools that do not exist and silently
   scanned nothing.

2. **Broken setup instructions.** The documented `npx -y snyk@latest mcp
   configure --tool=claude-cli` re-downloads the platform binary (stalls),
   writes the server entry to `~/.claude.json` (not `~/.claude/settings.json` as
   the docs claimed), and injects a malformed always-apply rule block into
   `~/.claude/CLAUDE.md`, which on this workstation is a symlink into the tracked
   standards repo.

3. **No shift-left and no provenance.** The owner wants real shift-left:
   security feedback woven into all Claude Code activities, not just at CI. And
   Open-Source findings are not actionable without transitive provenance: which
   direct dependency drags in the insecure downstream package, so it can be
   removed, replaced, or gated.

A field report from the CYO_Adventure team added a constraint: Snyk Open Source
over-reports filesystem-scope noise (`.venv/`, `.worktrees/`, vendored JS) while
the real lockfile-scoped surface is clean. They asked the template team to ship
a `.snyk` scope baseline and to define Snyk's role versus the existing scanners.

A hard constraint frames every decision below: the owner has hit the Snyk plan's
docker plus open-source **hosted-test quota**, so the design must minimize Snyk
hosted-test calls and source high-frequency and provenance data from local
unlimited tools (`osv-scanner`, `pip-audit`, `uv tree`, `npm why`).

## Decision

### Snyk role table

Snyk's role is explicit and consolidated. The table below is the single source
of truth for which layer owns which signal.

| Capability | Owner | Mode |
| --- | --- | --- |
| SAST (Snyk Code) | Snyk | Primary; CI gate plus always-on authoring |
| IaC | Snyk | Owned (`python-snyk-iac.yml`, per `.github` ADR-003) |
| AIBOM | Snyk | Owned (`snyk-aibom`, per `.github` ADR-003) |
| Pre-add package health | Snyk | `snyk_package_health_check` at authoring time |
| Open Source / SCA | Snyk | **Advisory, NOT disabled** (keeps visibility) |
| Primary SCA gate | Existing local tools (`osv-scanner`, `pip-audit`) | Keyless, unlimited, no Snyk quota |

Snyk Open Source stays advisory rather than disabled: it keeps fleet-wide
visibility in the Snyk web UI without becoming a blocking gate, while the
keyless local tools carry the primary SCA enforcement that does not consume Snyk
quota. This is consistent with `.github` ADR-003 and this repo's ADR-008
(`advisory_by_intent`).

### Always-on authoring MCP

Register the Snyk MCP server **always-on at user scope** in `~/.claude.json` so
`snyk_code_scan` and `snyk_package_health_check` are callable inline in every
session. This is the shift-left decision: authoring-time security feedback
rather than CI-only detection.

The quota and token trade-off is accepted and bounded by design:

- **Token cost:** always-on adds the server's tool descriptions to every
  session. Accepted as the cost of weaving security into authoring.
- **Quota cost:** always-on lets the agent call hosted SAST. The curated
  Secure-at-Inception rule (`.claude/rules/snyk-secure-at-inception.md`) uses a
  **significant-change trigger** (not per-edit) for `snyk_code_scan`, and routes
  all high-frequency and provenance data to local unlimited tools. The
  significant-change path bounds hosted calls to materially-reworked
  security-relevant code; trivial edits do not trigger a scan.

The server entry points at the local binary (machine-specific path), so it stays
out of any committed `.mcp.json`, the same rationale as the localhost-bound
sonarqube entry. The auto-injected CLAUDE.md rule block is removed and replaced
by the curated Secure-at-Inception rule, which carries the correct tool names.

### Dependency-provenance design (two layers)

Open-Source findings become actionable through transitive provenance, split into
a deterministic data layer and an interpretation layer:

- **Data layer (deterministic, no Claude):** a weekly GitHub workflow runs
  `osv-scanner` for the vuln list and `uv tree --invert --package <pkg>`
  (Python) plus `npm why <pkg>` (where a `frontend/package.json` exists) to map
  each vulnerable transitive package to its introducing direct dependency. It
  posts a sticky issue and uploads an artifact. No `claude-code-action` step, so
  it incurs no Anthropic API spend.

- **Interpretation layer (local cross-repo agent):** the
  `dependency-provenance` agent (`.claude/agents/dependency-provenance.md`) reads
  across all local repo clones under `~/dev`, pulls each repo's latest provenance
  issue or artifact, runs `uv tree --invert` / `npm why` live, and produces a
  consolidated fleet plan mapping each vulnerable transitive package to the
  introducing direct dep(s) and a recommended action (remove unused / upgrade /
  replace / accept via control gate). It runs on the owner's subscription via
  `claude -p` (no Anthropic API cost) on the task-observer `>7-day` cadence. It
  cannot run from GitHub by design: cross-repo reasoning over local clones is the
  whole point, which a cloud or managed agent cannot do.

### Scope baseline

Code repositories ship a `.snyk` scope baseline so filesystem-scope noise is
excluded by default. This repo's own `.snyk` adds `.worktrees/**`,
`**/.worktrees/**`, `htmlcov/**`, `out/**`, and `**/site-packages/**` to the
existing `exclude: global:` list. A `suggested`-severity manifest check
(FOUND-019) records the baseline expectation fleet-wide.

## Consequences

### Positive

- Snyk's role is unambiguous: one table states which layer owns each signal, so
  future contributors do not duplicate SCA enforcement or accidentally disable
  Open-Source visibility.
- Shift-left authoring works honestly: correct tool names everywhere, always-on
  MCP, and a curated rule with a bounded trigger.
- Open-Source findings become actionable via transitive provenance without
  paying Anthropic API cost: the deterministic CI layer gathers data keylessly,
  the local agent interprets it on the subscription.
- Scope noise is fixed at the template level, so every new repo is clean by
  default; the existing local SCA tools keep primary enforcement at no Snyk
  quota cost.

### Negative

- Always-on MCP adds per-session token cost and admits hosted-test quota usage.
  Mitigation: the significant-change trigger and the local-tool high-frequency
  path bound the spend; the owner accepted the residual cost.
- The provenance split adds two moving parts (a CI workflow and a local agent)
  that must agree on report shape. Mitigation: the agent reads the workflow's
  issue/artifact as its input contract.
- `snyk mcp configure` will re-inject its CLAUDE.md block on every re-run; the
  setup standard documents removing it each time. This is a manual step that can
  regress if skipped.

### Neutral

- The change spans multiple repos (`.claude` authoring layer, `.github` CI
  workflow, the cookiecutter template, and CYO_Adventure as first consumer). This
  ADR records only the `.claude` decisions; the CI workflow is governed by
  `.github` ADR-003 and its addendum.
- The implementation PR is classified `fix(snyk):` for the correctness bug (wrong
  tool names) plus `feat` for the always-on rule, ADR, manifest check, and agent.

## Security Considerations

- The always-on server runs the local Snyk binary with the user's `SNYK_TOKEN`.
  Keep the token out of committed config; it lives in the runtime-managed
  `~/.claude.json` and the shell environment only.
- The Secure-at-Inception rule must never become a silent blocker: it surfaces
  HIGH/CRITICAL findings to the user and lets the user decide, consistent with
  the report-do-not-block stance the rest of the authoring layer uses.
- The provenance agent reads across all local clones. It must treat issue and
  artifact contents as untrusted data (OWASP LLM01), not as instructions, since
  issue bodies are externally writable.
- Open-Source staying advisory rather than disabled is a deliberate
  visibility-over-gating choice; the keyless local tools, not Snyk, carry the
  enforcing SCA gate, so demoting Snyk OSS to advisory does not weaken the gate.

## References

- [ADR-003 (ByronWilliamsCPA/.github)](https://github.com/ByronWilliamsCPA/.github/blob/main/docs/architecture/adr/ADR-003-snyk-ci-role.md):
  the CI layer this ADR's authoring layer complements (Snyk Code primary, OSS
  advisory, IaC and AIBOM owned, `sbom-nightly` cron).
- [ADR-008](ADR-008-scanner-allowlist-tiers.md): classifies Snyk as
  `advisory_by_intent` in the scanner allowlist; consistent with the
  Open-Source-stays-advisory decision here.
- `.claude/standards/snyk-mcp-setup.md`: corrected setup, tool table, and the
  CLAUDE.md cleanup step.
- `.claude/rules/snyk-secure-at-inception.md`: the curated always-on authoring
  rule with the significant-change trigger.
- `.claude/rules/mcp-strategy.md`: records Snyk as an always-on authoring server.
- `.claude/agents/dependency-provenance.md`: the local cross-repo interpretation
  agent.
- `docs/standards-manifest.yaml` check FOUND-019: the `.snyk` scope-baseline
  expectation.
- [Conventional Commits 1.0](https://www.conventionalcommits.org/)
