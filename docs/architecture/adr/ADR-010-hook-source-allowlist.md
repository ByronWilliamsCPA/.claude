---
title: "ADR-010: Hook-Source Allowlist and Trust Tiers"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Records the decision to enumerate every live hook-injection source against a committed allowlist, and the trust-tier policy for hook-injected session content."
tags:
  - adr
  - decisions
  - hooks
  - security
  - architecture
---

> **Status**: Proposed
>
> **Decision date**: 2026-07-06
>
> **Deciders**: Byron Williams

## Context

The 2026-07-06 senior architecture review found that Claude Code executes
hooks from at least three independent, uncoordinated registration mechanisms,
of which only one was documented or checked:

1. This repo's `hooks.json`, merged into `~/.claude/settings.json` by
   `setup.sh` (documented in ADR-002 and `hook-pipeline.md`).
2. Direct writes to `~/.claude/settings.json` by tool installers
   (`codebase-memory-mcp install` wrote a `SessionStart` reminder and a
   `PreToolUse` gate) and by manual wiring (the Snyk dependency reminder).
3. Each enabled plugin's own `hooks/hooks.json` under
   `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/hooks/`
   (the `superpowers` plugin injects directive-toned session-start content
   this way; `agents-observe` registers a hook on every event Claude Code
   exposes; `hookify` registers four).

Session-start injections carry real behavioral authority over the agent, yet
this repo applied more suspicion to fetched web content (the OWASP LLM01
untrusted-content rule in `CLAUDE.md`) than to its own session-start pipeline.
A new or changed injection source, whether from a plugin update, a tool
installer, or an attacker with write access to `~/.claude/`, was invisible:
nothing enumerated the live hook surface or compared it to a reviewed state.

Independent verification during this work confirmed the "three mechanisms"
framing was a floor, not a ceiling: 34 plugin `hooks.json` files exist across
the cache and marketplace directories, one enabled plugin double-registers
hooks already wired via the submodule path, and the live `settings.json`
diverged from the repo baseline in seven hook registrations.

## Decision

We will commit an allowlist of every authorized hook source
(`hook-inventory.json` at repo root) and enumerate the live hook surface
against it at doctor time (`scripts/check-hook-sources.sh`, run by
`setup.sh --doctor`), keying each hook on its plugin or source name, hook
event, matcher, and command string rather than on filesystem paths.

Alongside the mechanism, we adopt a trust-tier policy for injected content:

- **Tier 1 (binding)**: `CLAUDE.md`, `.claude/rules/`, and hooks defined in
  the repo baseline `hooks.json`. Committed, reviewed in PRs, authoritative.
- **Tier 2 (accepted tooling, advisory on conflict)**: hooks listed in
  `hook-inventory.json`: installer additions and enabled-plugin hooks that
  were reviewed once when allowlisted. Their injected content guides
  workflow, but where it conflicts with Tier 1 the Tier 1 rule wins, and the
  agent should name the conflict rather than silently picking a side. This
  holds regardless of the injected content's tone; the `superpowers`
  injection styles itself "not negotiable" yet its own instruction hierarchy
  concedes that user instructions take precedence.
- **Tier 3 (unreviewed)**: any live hook absent from both the baseline and
  the allowlist. The checker fails, and until the source is reviewed its
  injected content is treated as untrusted data under the same OWASP LLM01
  posture as fetched web content.

## Alternatives Considered

- **Documentation only** (rewrite `hook-pipeline.md`, no checker): rejected.
  Drift had already happened silently at least three times (codebase-memory
  installer writes, Snyk manual wiring, plugin-registered session hooks);
  prose does not detect the fourth.
- **Hard enforcement** (`setup.sh` prunes any live hook not allowlisted):
  rejected for now. Pruning is destructive, would break tool installers
  mid-cycle, and interacts with the known replace-semantics defect in
  `merge_hooks()` (a repo `hooks.json` merge currently wipes installer
  additions; fix owned by the `fix/setup-merge-hooks-protocol` branch).
  Detection with a failing doctor is sufficient until merge semantics are
  fixed; revisit pruning afterward.
- **Path-keyed allowlist**: rejected. Plugin cache paths embed the plugin
  version (`.../superpowers/5.0.7/...`), so every plugin update would break
  the allowlist without any behavioral change. Plugin hook commands are
  written against `${CLAUDE_PLUGIN_ROOT}` and are version-independent, so
  keying on (plugin, event, matcher, command) survives version bumps and
  still catches real command changes.
- **Treat plugin-injected content as fully binding (single tier)**:
  rejected. It would let any plugin update rewrite agent behavior with the
  same authority as reviewed repo rules, inverting the repo's own
  prompt-injection posture.

## Consequences

- **Positive**: a new hook from any source (installer, plugin update, manual
  edit, or malicious write) becomes a visible doctor failure instead of a
  silent behavioral change. Plugin version bumps that do not change hook
  commands need no allowlist edit. A changed hook command fails the check
  until re-reviewed, which is the desired review gate.
- **Negative**: the allowlist is one more artifact to maintain; intentional
  hook changes now require touching `hook-inventory.json` in the same PR.
  The check is machine-local (it reads `~/.claude/`), so CI cannot run it;
  it only fires when someone runs `setup.sh --doctor`.
- **Neutral**: the checker trusts `enabledPlugins` in
  `~/.claude/settings.json` as the definition of "live" for plugins, and
  reports cached-but-disabled plugins with hooks as informational only.
  Project-level `.claude/settings.json` hooks in other repos are out of
  scope; they are reviewable in each repo's own tree.

## References

- `hook-inventory.json` (the allowlist), `scripts/check-hook-sources.sh`
  (the enumerator), `setup.sh` `doctor()` (the integration point).
- [Hook Pipeline](../hook-pipeline.md): hook-source taxonomy and trust tiers.
- [ADR-002 Hook Composition and Ordering](ADR-002-hook-composition.md):
  the repo-baseline merge this decision extends.
- [ADR-008 Two-Tier Scanner Allowlist](ADR-008-scanner-allowlist-tiers.md):
  prior art for allowlist-with-tiers in this repo.
- `docs/reviews/senior-review-repo-2026-07-01.md`: the originating finding
  ("Three distinct hook-registration mechanisms exist...").
