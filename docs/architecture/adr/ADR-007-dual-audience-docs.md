---
title: "ADR-007: Dual-Audience Documentation Structure"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Records the persona-first mkdocs nav and the frontmatter schema decision for docs."
tags:
  - adr
  - decisions
  - documentation
  - architecture
---

> **Status**: Accepted
>
> **Decision date**: 2026-04-11
>
> **Deciders**: Byron Williams (with four-model consensus review)

## Context

Before this ADR, the documentation site had a single undifferentiated "User Guide" section with no audience segmentation, no published ADRs, and no architecture diagrams. The nav exposed a flat list of guides that mixed onboarding content (how to clone, how to run agents) with operational reference (how to write tests, how to lint Python) without distinguishing what a new contributor needed from what a returning maintainer needed.

The practical consequence: a new developer cloning the repo for the first time had no clear path through the docs. A maintainer returning after months away had no way to recover the reasoning behind load-bearing decisions (two-layer install, hook composition, tiered MCP loading) without re-deriving it from the source code.

Two distinct audiences need to be served:

1. **New developer**: someone who has just cloned the repo and needs to install it, invoke their first agent, trigger their first skill, and verify the hook pipeline is working. Five-to-fifteen-minute onboarding path. Cares about steps, not rationale.
2. **Technical maintainer (usually future-Byron)**: someone who needs to understand *why* load-bearing decisions were made, so that future modifications do not silently regress architectural intent. Cares about rationale, not steps.

The reference pattern was `/home/byron/dev/monte_carlo`, which uses a persona-first nav (tabs for business readers vs. technical readers), a role-based landing page with a "Quick Reference by Role" table, published ADRs with YAML frontmatter, and PUML source files rendered offline with committed SVG siblings.

This plan was reviewed by four external models (Gemini 3.1 Pro, GPT-5.2, Qwen 3.5, GLM-4.5-air) in a consensus session. Key changes from v1 to v2 that the review surfaced are documented at the end of this ADR.

## Decision

The following changes were made to serve both audiences:

1. **Persona-first navigation**: `mkdocs.yml` `nav:` block restructured into six top-level tabs: Home, Getting Started, Architecture, Reference, Contributing, Project. `navigation.tabs` was already enabled; the change is purely in the nav tree structure.

2. **Role-selector landing page**: `docs/index.md` rewritten as a "Pick Your Path" table, directing each reader persona to their relevant section. Modeled on the monte_carlo pattern.

3. **ADR directory**: `docs/architecture/adr/` added, with a numbered ADR log (ADR-001 through ADR-007) covering load-bearing decisions only. Slim template at `docs/architecture/adr/_template.md` (excluded from build).

4. **Diagram directory**: `docs/architecture/diagrams/` added, with four PUML sources and committed SVG siblings: `install_layer`, `hook_pipeline`, `agent_skill_dispatch`, `mcp_tier_loading`. SVGs are rendered offline via `scripts/render_diagrams.sh` and committed with the source, so MkDocs can embed them directly without a rendering plugin.

5. **Frontmatter schema unchanged**: The existing `CommonFM` Pydantic model (`tools/frontmatter_contract/models.py`) was not modified. It uses `model_config = ConfigDict(extra="forbid")`, meaning any unknown field causes a validation failure across all existing docs. Audience is represented via the existing `tags` field using new tags `new_dev` and `technical`. Nav structure, not tags, drives reader routing.

6. **Legacy directories preserved**: `docs/guides/` and `docs/development/` are physically left in place, remain buildable, but are not referenced from the new nav. They are buildable (not in `exclude_docs:`) to avoid 404s from any hardcoded external links. A follow-up docs reconciliation sprint is planned to resolve or migrate their content.

## Alternatives Considered

**Add `audience`, `category`, `last_updated` fields to `CommonFM`**: Breaks validation of every existing doc. `extra="forbid"` means any field not in the schema model causes a hard failure. Changing the schema would require updating all 99 existing docs or risk broken CI. The tag-based approach achieves the same discoverability without a schema migration.

**`docs_site/` symlink layer** (as used in monte_carlo): monte_carlo uses a symlink layer to serve docs from a different directory than the source tree. This repo has a single source tree (`docs/`) and a single `docs_dir: docs` in `mkdocs.yml`. The additional layer adds complexity without benefit.

**Full `git mv` sweep of legacy directories**: Moving `docs/guides/*` and `docs/development/*` into the new tree would break hardcoded relative links in `README.md`, `CLAUDE.md`, `AGENTS-AND-SKILLS.md`, and potentially in submodule content. Four-model consensus (3 of 4 models) recommended the hybrid approach: leave legacy directories in place, write new content from scratch, defer cleanup to a follow-up sprint.

**`exclude_docs:` for legacy directories**: Excluding `docs/guides/*` from the build removes them from the MkDocs output. Any remaining internal link to those files produces a 404. This is the v1 plan's contradiction (it both linked to those files from new pages and excluded them). v2 does not add them to `exclude_docs:`.

## Consequences

- **Positive**: Two clear reader paths from the landing page. The "why" behind every load-bearing decision is now documented and findable. Zero changes to the install layer, hook system, agents, skills, or rules.
- **Negative**: Some legacy files under `docs/guides/` and `docs/development/` are now orphaned: present in the build but not reachable from the nav. This creates "zombie" pages until the follow-up reconciliation sprint resolves them.
- **Neutral**: The `audience` concept is a tag, not a schema field. Future tooling that needs to filter by audience (e.g., a CI step that generates audience-specific PDF exports) must query the `tags` field rather than a dedicated `audience` field.

## Consensus review changes (v1 → v2)

The four-model review surfaced ten substantive changes from the original v1 plan:

1. **Fixed `exclude_docs` contradiction** (GPT-5.2): v1 claimed to link from new pages to files it was simultaneously excluding. v2 leaves those files buildable-but-unlinked.
2. **Stub-first, nav-first sequencing** (Gemini): v1 authored content then flipped the nav last, creating a blind authoring environment. v2 creates stubs, flips the nav, then authors against a live `mkdocs serve`.
3. **Dropped ADR-008** (three-model consensus): offline PUML rendering is operational policy, not architecture. Content moved to `contributing/writing-diagrams.md`.
4. **Merged flat-directory ADR into ADR-004** (Gemini, GPT-5.2, Qwen): the flat agent directory convention is an implementation detail of the skill-vs-agent decision, not a standalone ADR.
5. **Added ADR-006 Rules vs Standards** (Gemini strongly, GPT-5.2 conditionally): the rules/standards split has different context-injection semantics and is load-bearing.
6. **Expanded ADR-002 to cover hook composition** (GPT-5.2): hookify dispatch and planning-bridge-gate are sub-decisions of the hook source-of-truth decision, not separate ADRs.
7. **Added Validation and Tooling section**: `scripts/render_diagrams.sh`, `tools/check_docs.sh` concepts formalized.
8. **Added rollback plan**: explicit revert commands documented.
9. **Fixed "frontmatter drives routing" overclaim** (GPT-5.2): `audience:` is metadata; `nav:` drives routing.
10. **Timeline revised from 7 to 10–14 days**: four-model consensus.

## References

- `/home/byron/.claude/plans/polished-singing-crab.md`: the approved v2 plan this ADR records
- `mkdocs.yml`: the nav block and `exclude_docs:` changes
- `docs/index.md`: the role-selector landing page
- `tools/frontmatter_contract/models.py`: the `CommonFM` schema that was not modified
- `scripts/render_diagrams.sh`: SVG rendering wrapper
- `docs/architecture/diagrams/`: PUML sources and SVG siblings
- [ADR-001](ADR-001-two-layer-symlink-install.md) through [ADR-006](ADR-006-rules-vs-standards.md): the decisions this docs structure makes findable
