---
title: "Org Plugin Distribution"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Narrative description of how first-party agents and skills reach the team via the ByronWilliamsCPA/plugin repo, and how to update the manifest that controls what ships."
tags:
  - architecture
  - plugins
  - technical
---

This repo is public and personal. The team needs shared access to the
applicable parts of it, but claude.ai's org-wide distribution features (see
[ADR-011](adr/ADR-011-org-plugin-distribution.md) for the full decision and
alternatives) require a private or internal repo. `ByronWilliamsCPA/plugin`
is that repo; this doc covers the mechanics of keeping it in sync.

## The pipeline

```text
.claude/agents/*.md, .claude/skills/*/  (this repo)
          |
          v
scripts/org-plugins/manifest.yaml            <- the only thing a human edits
          |
          v
scripts/org-plugins/build_org_plugins.py      <- pure function of the manifest
          |
          v
.github/workflows/sync-org-plugins.yml         <- runs the build, opens/auto-merges a PR
          |
          v
ByronWilliamsCPA/plugin (main, via PR)
  .claude-plugin/marketplace.json
  plugins/wff-code/   (agents + all first-party skills)  -> Claude Code
  plugins/wff-chat/   (portable skills only, no agents)  -> claude.ai chat/Cowork
```

The workflow triggers on push to `main` touching `.claude/agents/**`,
`.claude/skills/**`, or the manifest itself, so a normal PR to this repo is
the only step needed to update the team's copy. The generated repo is a pure
build artifact: never edit it by hand, the next sync overwrites it.

## Adding a new agent

Add its name to the `agents:` list in `scripts/org-plugins/manifest.yaml`.
There is no per-agent classification: every entry in that list ships in
`wff-code` only, since claude.ai chat and Cowork have no subagent-dispatch
surface. Vendored/symlinked agents (from `anthropics-plugins`,
`reference-library`, `image-generation`) are deliberately left out; see the
"Vendored content" section below before adding one.

## Adding a new skill

Add `<skill-name>: <classification>` under `skills:` in the manifest.
Classify honestly, this is a trust decision, not a formality:

- **`portable`**: the skill's SKILL.md and any bundled files have no
  reference to the Agent/Task tool, TodoWrite, or an `mcp__*` tool, and don't
  assume a companion skill that lives elsewhere. Ships in both `wff-code` and
  `wff-chat`.
- **`claude-code-only`**: everything else that's first-party and safe to
  ship, it just won't do anything useful outside Claude Code. Ships in
  `wff-code` only.
- **`exclude`**: don't ship anywhere yet. Use this for a skill that's a delta
  on a vendored companion (see below), or that has a known blocker (a
  hardcoded local path, an unreviewed dependency).

An unclassified skill is excluded by default (the build script only copies
what the manifest lists), so forgetting to classify something withholds it
rather than leaking it.

## Vendored content

Several skills and agents in this repo are symlinks into `.submodules/`
(`superpowers`, `anthropics-skills`, `anthropics-plugins`, `reference-library`,
`image-generation`, `jeffallan-claude-skills`). The other two submodules,
`one-skill-to-rule-them-all` and `agents-observe`, are wired by mechanisms of
their own rather than a direct symlink (see the ADR-011 provenance split
below); see [submodule-strategy.md](submodule-strategy.md) for the full
eight-submodule inventory and trust tiers. No vendored or third-party
submodule *content* ships through this
pipeline. Re-distributing it into a second repo is a separate license question
from the one this pipeline answers, don't fold it in silently. If a specific
vendored item needs to reach the team, clear its license for redistribution
first, then add it to the manifest with a comment recording that check,
following the same admission-bar discipline as a new submodule.

The [ADR-011 provenance split](adr/ADR-011-org-plugin-distribution.md) (2026-07-10
update) sorts the submodules by redistribution license and states, per bucket,
where the team gets each: first-party submodules (`reference-library`,
`image-generation`) as their own plugins in a follow-up; Anthropic vendor
content from Anthropic's official channels; third-party marketplaces
(`superpowers`, `agents-observe`, and the rest) added upstream directly. Read
that update before adding any submodule-sourced entry to the manifest.

### The `*-extras` skills

Each `*-extras` skill is first-party content: a delta layered on a companion
skill. Only the companion may be third-party; the delta itself is ours. So the
delta ships as `claude-code-only` regardless of where the companion comes from,
because the team obtains the companion from its own source (bucket B/C of the
provenance split for vendored companions, or first-party alongside for the
rest). The delta references concepts the companion defines but does not
redistribute the companion. This is why every `*-extras` skill is now
`claude-code-only`, including the eleven that were `exclude` before the
2026-07-10 update (`audience-reaction-analyzer-extras`, `brainstorming-extras`,
`code-review-extras`, `executing-plans-extras`, `fastapi-expert-extras`,
`finishing-a-development-branch-extras`, `pdf-extras`, `pptx-extras`,
`subagent-driven-development-extras`, `systematic-debugging-extras`,
`verification-before-completion-extras`), alongside `receiving-code-review-extras`
and `test-driven-development-extras`, which were already `claude-code-only`.

## Running the build locally

```bash
uv run python scripts/org-plugins/build_org_plugins.py --out /tmp/org-plugin-build
```

Inspect `/tmp/org-plugin-build` before trusting a manifest change; the CI
workflow runs the identical script.

## One-time setup this pipeline still needs

1. **`ORG_PLUGIN_PUSH_TOKEN` repo secret** on `ByronWilliamsCPA/.claude`: a
   fine-grained PAT scoped to `ByronWilliamsCPA/plugin` only, with **Contents:
   Read and write** and **Pull requests: Read and write** (the workflow opens
   a PR and calls `gh pr merge --auto`, it needs both). Without it the
   workflow fails fast with an explicit error rather than proceeding with an
   under-scoped token.
2. **"Allow auto-merge" enabled** in `ByronWilliamsCPA/plugin`'s repository
   settings (General > Pull Requests). Without it, `gh pr merge --auto` errors
   immediately and the workflow falls back to leaving the PR open for a manual
   merge (it logs a warning, it doesn't fail the run).
3. **`ByronWilliamsCPA/plugin` excluded from the `default-branch-baseline`
   org ruleset.** That ruleset requires three status checks (Security Gate
   Validation, Dependency & Standards Validation, Check REUSE Compliance) that
   only run in `.claude`'s own CI, never in an artifact-only repo, so they would
   block every sync PR indefinitely. The repo name is listed under the ruleset's
   `conditions.repository_name.exclude`; it still inherits the push-baseline and
   tag-protection rulesets. Re-adding the repo to the baseline reinstates the
   permanent block.
4. **Claude Code side**: team members run
   `claude plugin marketplace add ByronWilliamsCPA/plugin` once, then
   `/plugin install wff-code@wff-plugins`.
5. **claude.ai side**: an org owner connects `ByronWilliamsCPA/plugin` as a
   marketplace source under Organization Settings > Plugins (Libraries),
   installing the `wff-chat` plugin, and enables "Sync automatically" so
   future pushes propagate without a manual re-sync.

## See Also

- [ADR-011: Org-Wide Plugin Distribution](adr/ADR-011-org-plugin-distribution.md)
- [Submodule Strategy](submodule-strategy.md): the inbound analog of this pipeline
- `scripts/org-plugins/manifest.yaml`, `scripts/org-plugins/build_org_plugins.py`
- `.github/workflows/sync-org-plugins.yml`
