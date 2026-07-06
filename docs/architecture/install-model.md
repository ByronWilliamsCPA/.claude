---
title: "Install Model"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Narrative description of the two-layer symlink install model."
tags:
  - architecture
  - install
  - symlinks
  - technical
---

The configuration repository does not live where Claude Code expects it. This is intentional.

Claude Code reads from `~/.claude/`. The repository lives at `~/dev/.claude`. `setup.sh` bridges the two by creating a set of symlinks from `~/.claude/` into the repo. From Claude Code's perspective, the agents, skills, rules, and scripts look native. From the developer's perspective, they are version-controlled files in a normal git repository.

For the reasoning behind this design, see [ADR-001](adr/ADR-001-two-layer-symlink-install.md).

## Two Layers

**Layer 1: the repository** (`~/dev/.claude`):

This is where you work. It is a standard git repository with submodules, a Python toolchain (`pyproject.toml`, `uv.lock`), pre-commit hooks, and all the tooling a maintainer needs. You run `git`, `uv run pytest`, `pre-commit`, and `mkdocs` here.

**Layer 2: the runtime config** (`~/.claude/`):

This is where Claude Code reads. It contains a mix of real files and symlinks. The symlinks point into Layer 1. `settings.json` is a genuine machine-local file that is never committed, and it holds more than the merged hooks: tool installers (for example `codebase-memory-mcp install`) write hook entries directly into it, and its `enabledPlugins` key controls which plugin-registered hooks Claude Code loads from `~/.claude/plugins/cache/`. The committed allowlist `hook-inventory.json` plus `scripts/check-hook-sources.sh` track these out-of-repo additions; see [Hook Pipeline → Hook Sources](hook-pipeline.md#hook-sources). Other genuine runtime-managed content in Layer 2 includes `plugins/`, `projects/`, and installer-owned directories such as `~/.claude/hooks/`.

`setup.sh` creates Layer 2 from Layer 1. Running it again is always safe: every operation is idempotent.

## Diagram

![Install layer component diagram](diagrams/install_layer.svg)

## What `setup.sh` Does

`setup.sh` runs five phases in order:

**1. Preflight**: checks that `ln` and `git` are available. Warns (but does not abort) if `jq` is missing: symlinks can still be created; the hooks merge step will be skipped.

**2. Submodule init**: calls `git submodule update --init --recursive` if the submodules have not been initialized. This populates `.submodules/reference-library/`, `.submodules/anthropics-plugins/`, and the others.

**3. Symlink creation**: creates or updates eight symlinks in `~/.claude/`:

| Symlink | Points to |
| --- | --- |
| `~/.claude/CLAUDE.md` | `~/dev/.claude/CLAUDE.md` |
| `~/.claude/agents/` | `~/dev/.claude/.claude/agents/` |
| `~/.claude/skills/` | `~/dev/.claude/.claude/skills/` |
| `~/.claude/commands/` | `~/dev/.claude/.claude/commands/` |
| `~/.claude/rules/` | `~/dev/.claude/.claude/rules/` |
| `~/.claude/standards/` | `~/dev/.claude/.claude/standards/` |
| `~/.claude/reference-library/` | `~/dev/.claude/.submodules/reference-library/` |
| `~/.claude/scripts/` | `~/dev/.claude/scripts/` |

All use `ln -sfn` (force-replace, no-dereference), so re-running after a structural change is safe.

**4. Hook merge**: reads `hooks.json` from the repo root and uses `jq` to write its contents into the `.hooks` key of `~/.claude/settings.json`. If `settings.json` does not exist, it creates one. If it exists, other top-level keys (API keys, model preferences, `enabledPlugins`) are preserved, but the `.hooks` key itself is **replaced wholesale**, not merged: any hook a tool installer added directly to `settings.json` is wiped by the next `setup.sh` run. This is a known defect; the fix is owned by the `fix/setup-merge-hooks-protocol` branch, and until it lands the hook-source drift check reports the wipe as a stale-allowlist warning. A timestamped backup is created before any write.

**5. claudeMdExcludes merge**: adds two path patterns to `settings.json`'s `.claudeMdExcludes` array: one for `~/dev/.claude/CLAUDE.md` and one for `~/dev/.claude/.claude/**`. This prevents Claude Code from double-loading the repo-local CLAUDE.md. Deduplicates before writing.

## Verifying the Install

```bash
./setup.sh --doctor
```

The doctor mode prints every expected symlink, its current target, and whether the target exists. Broken symlinks, dangling targets, and drift from the expected topology are all reported. It also checks whether `settings.json` has the hooks block and `claudeMdExcludes` merged in, runs `scripts/check-hook-sources.sh` to diff every live hook source (settings.json entries and enabled-plugin hooks) against the committed allowlist `hook-inventory.json`, and verifies the expected vendored plugins are installed. An unreviewed hook source fails the doctor run.

## See Also

- [ADR-001 Two-Layer Symlink Install](adr/ADR-001-two-layer-symlink-install.md): why this design
- [ADR-002 Hook Composition and Ordering](adr/ADR-002-hook-composition.md): how `hooks.json` merges into `settings.json`
- [Getting Started → Install](../getting-started/install.md): step-by-step walkthrough for new developers
- [Submodule Strategy](submodule-strategy.md): what the five submodules provide
