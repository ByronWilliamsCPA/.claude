---
title: "ADR-005: Submodule Extension Model"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Records why external capabilities are git submodules rather than vendored or packaged."
tags:
  - adr
  - decisions
  - submodules
  - architecture
---

> **Status**: Accepted
>
> **Decision date**: 2026-04-11
>
> **Deciders**: Byron Williams

## Context

The repo integrates external capability trees that are maintained upstream and should receive updates independently of this repo's own development. Five such trees are in active use:

| Submodule | Upstream | What it provides |
| --- | --- | --- |
| `reference-library` | `ByronWilliamsCPA/reference-library` | Agent prompt templates with `{{LIBRARY_PATH}}` placeholders |
| `image-generation` | `williaby/image-generation` | Image generation utility agents and skills |
| `superpowers` | `obra/superpowers` | Community skills: brainstorming, writing-plans, TDD, debugging, git-worktrees, review patterns |
| `anthropics-skills` | `anthropics/skills` | Official Anthropic skill collection |
| `anthropics-plugins` | `anthropics/claude-plugins-official` | hookify plugin engine, security-guidance hooks |

The question is how to integrate these trees. The options are: copy the files into this repo (vendor), use git submodules (pinned upstream references), use git subtrees (merged history), or treat them as a separate installation step (external packages).

## Decision

External capability trees are integrated as git submodules under `.submodules/`. `setup.sh` symlinks their contents into `~/.claude/` via the two-layer install model (see [ADR-001](ADR-001-two-layer-symlink-install.md)), making them first-class citizens of the Claude Code runtime without losing their upstream identity.

Submodule paths under `.submodules/` follow the pattern `.submodules/{name}/`. The `reference-library` submodule is additionally symlinked to `~/.claude/reference-library/` so it is accessible at the path agents reference via the `{{LIBRARY_PATH}}` placeholder convention.

`anthropics-plugins` sits at `.submodules/anthropics-plugins/`. The hookify engine inside it is invoked directly by hooks in `hooks.json` via its absolute path (`$HOME/dev/.claude/.submodules/anthropics-plugins/plugins/hookify/...`), not via a symlink into `~/.claude/`. This is intentional: hookify is a runtime dependency of the hook system, not a user-facing capability that needs to appear in `~/.claude/`.

Updating a submodule to track upstream changes:

```bash
git submodule update --remote --merge .submodules/<name>
git add .submodules/<name>
git commit -m "chore(submodules): update <name> to latest upstream"
```

## Alternatives Considered

**Vendor (copy files into main repo)**: The copied files diverge from upstream immediately. Bug fixes and new agents from upstream require manual cherry-picks. The repo size grows to include all submodule content. Upstream attribution is obscured.

**Separate pip/npm packages**: Prompt-and-script bundles (agents, skills, hook scripts) do not map cleanly to Python or Node package semantics. There is no standard distribution channel for Claude Code capability bundles. Installing would require a separate `pip install` step that breaks the single-`./setup.sh` install model.

**Git subtrees**: Subtree merges inline upstream history into this repo's history. Pulling upstream updates requires `git subtree pull`, which is less intuitive than `git submodule update --remote --merge` and produces merge commits that obscure this repo's own history. Subtrees also make it harder to push local changes upstream.

**External installation step (separate clone)**: Requires contributors to clone each upstream repo separately and maintain their paths independently. Breaks the `./setup.sh` single-step install guarantee. The `{{LIBRARY_PATH}}` placeholder convention in `reference-library` agents depends on the submodule being at a predictable, setup-managed path.

## Consequences

### Positive

- Upstream improvements (new agents, bug fixes, new hookify plugins) flow in via a single `git submodule update --remote --merge` command.
- Each submodule is pinned to a specific commit. This repo controls exactly which upstream version is in use — updates are opt-in, not automatic.
- Contributors only run `./setup.sh` once after clone. `setup.sh` calls `git submodule update --init --recursive` as part of its preflight, so submodule initialization is handled automatically.

### Negative

- Contributors must initialize submodules on clone, or `setup.sh` must be run before git operations that assume submodules are present. Cloning without `--recurse-submodules` and skipping `setup.sh` leaves submodule directories empty.
- Some git operations need `--recurse-submodules` to work correctly across the full tree (e.g., `git grep`, `git log` for submodule content).
- Upstream repos can be deleted, renamed, or made private. The `.gitmodules` URLs would then break. For `anthropics/*` submodules, this risk is low; for community repos (`obra/superpowers`), it is non-zero.

### Neutral

- The `{{LIBRARY_PATH}}` placeholder convention in `reference-library` agent templates requires contributors to resolve the placeholder to `~/.claude/reference-library` when using those agents. `setup.sh` documents this in its output: `Note: agents in reference-library use {{LIBRARY_PATH}} as a placeholder. Resolve it to: ~/.claude/reference-library`.

## References

- `.gitmodules` — the five submodule definitions with upstream URLs
- `setup.sh` — `ensure_submodules()` function handles init; symlink targets reference submodule paths
- `.submodules/reference-library/` — agent templates
- `.submodules/superpowers/` — community skills
- `.submodules/anthropics-skills/` — official Anthropic skills
- `.submodules/anthropics-plugins/` — hookify and security-guidance
- `.submodules/image-generation/` — image generation utilities
- `docs/architecture/submodule-strategy.md` — narrative explanation of the five submodules
- [ADR-001](ADR-001-two-layer-symlink-install.md) — the two-layer install model that wires submodules into `~/.claude/`
