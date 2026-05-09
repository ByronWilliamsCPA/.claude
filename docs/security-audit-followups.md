---
title: "Security Audit Follow-Ups (deferred from 2026-05-01 audit)"
schema_type: common
status: published
owner: core-maintainer
purpose: "Tracking record for security-audit findings that are not closed in PR #76. Each item lists the audit ID, current status, and what is needed to resolve."
tags:
  - security
  - compliance
---

> Companion document to `docs/security-analysis-2026-05-01.md`. PR #76
> closed 18 of the audit's 35 findings (Tier 1 + most of Tier 2). The
> remaining items are tracked here so the deferral is visible without
> embedding `_comment_*` placeholder keys inside JSON config files.

## Open audit follow-ups

### M-04: SonarQube bearer token over cleartext loopback HTTP

**Where:** `.mcp.json` `sonarqube` server block (`url: http://localhost:8090/mcp`).

**Why deferred:** Requires a server-side reconfiguration of the local
SonarQube container (HTTPS or Unix-socket transport, bind to 127.0.0.1
only). The MCP client config can only point at whatever the server
exposes, so the fix lives in the SonarQube container manifest, not in
this repo.

**To close:** Reconfigure the SonarQube docker container with TLS
termination (or socket transport), update `.mcp.json` URL to the new
endpoint, and remove this entry.

### M-05 (clarifying note): bash-pre-hook registration retains a `_comment` requirement risk

**Where:** Previously had `_comment_M05` inline in `settings.json`. The
PR removed it after PR #76 review flagged the field as schema-strict
risk.

**Why deferred:** The registration itself is in place. The only follow-up
is to confirm at runtime that Claude Code does not validate the
PreToolUse entry against a strict schema (which would silently drop the
hook). Verification step: open a session, run `/status hooks` (or
equivalent), confirm the bash-pre-hook.sh entry shows up as registered.

### L-04: SHA-verification script for pre-commit hooks

**Where:** `.pre-commit-config.yaml` (all 12 hook `rev:` entries).

**Why deferred:** Design task. Need a script that queries the GitHub API
to confirm each pinned SHA still maps to its stated tag, runs in CI on
any change to `.pre-commit-config.yaml`, and tolerates rate limits.
Roughly a half-day of work; no immediate exposure since SHA pins
themselves are immutable.

**To close:** Build `scripts/verify-pre-commit-shas.sh`, add a CI step
that runs it on PRs touching `.pre-commit-config.yaml`.

### L-05: narrow the `.claude/` exclusion on the no-em-dash hook

**Where:** `.pre-commit-config.yaml` no-em-dash hook `exclude:` field.

**Why deferred:** Properly narrowing the exclusion requires first
cleaning ~2400 existing em-dashes across legacy standards, agent
prompts, and skill workflows. Bounded but tedious. The
`.claude/skills/writing-workspace/` subtree must remain excluded
permanently because it contains adversarial test fixtures for the
writing pipeline.

**To close:** Run a pass over `.claude/standards/`, `.claude/skills/*/SKILL.md`,
`.claude/agents/`, `.claude/rules/`, and `.claude/context/` replacing
em-dashes with appropriate punctuation per the writing-quality rules,
then narrow the exclude pattern to keep only the writing-workspace
exemption.

### I-01: deduplicate context7 MCP server definition

**Where:** `context7` is defined in both `settings.json` (`mcpServers`)
and `.mcp.json` (`mcpServers`). Both are now pinned to `2.2.4`.

**Why deferred:** Refactor risk. Removing one of the two could break
session bootstrap depending on how Claude Code resolves overlapping MCP
definitions. The duplication is consistent (same version, same npx
invocation) and the supply-chain pin is in both places, so the
duplicated entries are not a security exposure.

**To close:** Verify Claude Code's precedence rule for MCP server
definitions, then remove the lower-precedence entry.

## Phase 2 (workflow refactors) deferred

These were never in scope for PR #76 and remain tracked in
`docs/security-analysis-2026-05-01.md`. Each is significant and warrants
a dedicated PR:

- **P-01:** repo-compliance interactive mode auto-commits without per-action confirmation
- **P-02:** scheduled mode clones unattended with no audit trail for secrets encountered
- **P-03:** remediation agents hold full Write+Bash with no path restriction
- **P-04:** reviewed repo's compliance-overrides.md injected verbatim into agent context
- **P-06:** `github-repos.json` catalog has no integrity protection
- **P-07:** shell commands built from unvalidated `uses:` and hook URLs
- **P-08:** reviewed repo's CI build script (`bash scripts/ci.sh`) executed without confirmation
- **P-09:** upstream skill sources (frontend-design) have no SHA pin
- **P-10:** `/loop` recipes lack max-iteration count and concurrent-run lock
- **P-12:** `general-compliance-auditor` loads overseer config and untrusted target content into the same context window

## Items resolved in PR #76 review (2026-05-08 ... 2026-05-09)

The PR's own automated review surfaced 5 additional defects that the
remediation introduced or missed. All five were corrected in the
remediation pass:

- bash-pre-hook.sh:188 happy path still wrote to /tmp (timing
  notification regression)
- task-observer-review.sh SAFETY preamble referenced a nonexistent
  inline UNTRUSTED CONTENT block
- .github/hooks/pre-push retained two `--no-verify` references
- hooks.json sensitive-file-guard matcher omitted MultiEdit
- sensitive-file-guard.sh patterns required `/` prefix, allowing bare
  relative paths to bypass

These are recorded for the lessons-learned retrospective: an audit
remediation needs its own review pass because remediation code is itself
new code.
