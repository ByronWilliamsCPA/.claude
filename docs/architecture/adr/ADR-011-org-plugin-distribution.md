---
title: "ADR-011: Org-Wide Plugin Distribution"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Records why applicable agents and skills are exported to a separate private plugin repo instead of shared in place."
tags:
  - adr
  - decisions
  - plugins
  - architecture
---

> **Status**: Proposed
>
> **Decision date**: 2026-07-09
>
> **Deciders**: Byron Williams

## Context

This repo (`ByronWilliamsCPA/.claude`) is public, and holds one person's personal
Claude Code configuration: agents, skills, rules, and standards. The account
this repo serves switched from a personal to a team (Team/Enterprise) Claude
plan, and the team needs shared access to the applicable parts of this
configuration.

Two distribution surfaces exist for that, and neither can point at this repo
directly:

- **Organization settings > Skills** (claude.ai admin panel): zip-upload only,
  skills only, no agents, no git-backed update path.
- **Organization settings > Plugins** (claude.ai admin panel, and Claude
  Code's own `/plugin marketplace add`): can bundle agents, skills, hooks, and
  MCP servers, and supports GitHub-repo-backed marketplaces with automatic
  sync on push, but **the repo must be private or internal**. This repo is
  public.

Content also isn't uniformly portable across the two consumer surfaces even
once packaged: Claude Code supports the Agent/Task tool, TodoWrite, and MCP
servers; claude.ai chat, Desktop, and Cowork do not. Of the 62 first-party
skills, roughly a third are pure instructional/Bash content with no such
dependency; the rest either dispatch subagents, call MCP tools, or are deltas
layered on a vendored companion skill from a third-party submodule.

## Decision

We will maintain a classification manifest (`scripts/org-plugins/manifest.yaml`)
in this repo that tags every first-party agent and skill, build two plugins
from it with `scripts/org-plugins/build_org_plugins.py`, and land the result in
a separate private repo (`ByronWilliamsCPA/plugin`) via a GitHub Action
(`.github/workflows/sync-org-plugins.yml`) that runs on every push to `main`
touching `.claude/agents/`, `.claude/skills/`, or the manifest. The workflow
opens a PR against the target repo's main and enables auto-merge on it, rather
than pushing directly: `ByronWilliamsCPA/plugin` inherited the org's
default-branch-baseline ruleset on transfer, which blocks non-PR pushes to
main outright. Auto-merge only completes once whatever the ruleset requires
(checks, reviews) is satisfied; otherwise the PR waits for a manual merge,
same fallback `sync-org-pins.yml` already uses elsewhere in this repo.

- **`wff-code`**: all first-party agents plus all first-party skills not
  explicitly excluded. Distributed via Claude Code's plugin marketplace
  (`claude plugin marketplace add ByronWilliamsCPA/plugin`), where every
  dependency (Agent/Task, MCP, TodoWrite) is available.
- **`wff-chat`**: only skills classified `portable` in the manifest (no
  agents). Distributed via claude.ai's Organization Settings > Plugins panel
  with GitHub sync, for chat, Desktop, and Cowork.

Vendored and third-party-submodule-sourced content (the `anthropics-plugins`,
`reference-library`, `image-generation`, `superpowers`, and similar submodules)
is excluded from both plugins in v1: redistributing it into a second repo
needs its own license check, tracked separately from this decision.

## Alternatives Considered

- **Zip-upload to Organization Settings > Skills**: rejected as the primary
  mechanism. No agent support, no git-backed update path; every change would
  need a manual re-zip and re-upload.
- **Make this repo private**: rejected. This repo predates the team-account
  switch and has independent reasons to stay public (OpenSSF badge, community
  contribution). Splitting the org-facing subset into a dedicated repo is less
  disruptive than changing this repo's visibility.
- **Ship everything (including Agent/MCP-dependent skills and all agents) to
  both plugins**: rejected for `wff-chat` specifically. Agent definitions are
  inert in claude.ai chat (no subagent-dispatch surface exists there), and
  Anthropic's own guidance on Skill recall warns that too many simultaneously
  loaded skills degrade Claude's ability to pick the right one; shipping
  non-functional entries there has a real cost, not just a theoretical one.
- **Per-skill frontmatter tag instead of a central manifest**: rejected for
  v1. A single manifest file is easier to review in one diff and keeps the
  classification decision out of ~110 individual files; revisit if the
  manifest becomes unwieldy.

## Consequences

- **Positive**: updating the org-wide plugins is a normal PR to this repo
  (edit `manifest.yaml`, or add/edit an agent or skill); the Action opens and
  auto-merges a PR with the rebuilt output on the target repo. No manual
  zip/upload step for `wff-code`; only `wff-chat`'s claude.ai-side sync
  additionally requires the org owner to connect the marketplace once in
  Organization Settings > Plugins.
- **Negative**: two repos now need to be kept consistent (this one and
  `ByronWilliamsCPA/plugin`); the Action is a new automated push path that
  needs a scoped `ORG_PLUGIN_PUSH_TOKEN` secret with write access to exactly
  one repo. New skills/agents default to unshipped until someone classifies
  them in the manifest, which is intentional but means a forgotten
  classification silently withholds new content from the team rather than
  silently leaking it.
- **Neutral**: the manifest's classification is a point-in-time judgment call
  (see the `-extras` exclusions); it should be revisited whenever a vendored
  submodule pin bumps or a new skill is added.

## References

- `scripts/org-plugins/manifest.yaml`, `scripts/org-plugins/build_org_plugins.py`
- `.github/workflows/sync-org-plugins.yml`
- `docs/architecture/org-plugin-distribution.md` (narrative walkthrough)
- `docs/architecture/submodule-strategy.md` (the inbound-distribution analog: how third-party content reaches this repo)
- [ADR-005](ADR-005-submodule-extension-model.md): the submodule model this decision deliberately mirrors on the outbound side
- Anthropic Help Center: "Provision and manage skills for your organization", "Manage plugins for your organization"
- Claude Code docs: `/en/plugins`, `/en/plugin-marketplaces`
