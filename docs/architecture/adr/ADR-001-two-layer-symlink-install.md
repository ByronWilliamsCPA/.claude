---
title: "ADR-001: Two-Layer Symlink Install"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Records why the repo lives at ~/dev/.claude and ~/.claude is a symlink tree."
tags:
  - adr
  - decisions
  - install
  - symlinks
  - architecture
---

> **Status**: Accepted
>
> **Decision date**: 2026-04-11
>
> **Deciders**: Byron Williams

## Context

Claude Code reads configuration from `~/.claude/`. That directory must contain `CLAUDE.md`, `agents/`, `skills/`, `commands/`, `rules/`, `standards/`, and a `settings.json` with merged hook definitions. The natural instinct is to clone the configuration repository directly into `~/.claude/` — one directory, one location, done.

But the configuration repository is not a simple dotfiles collection. It has:

- **Git submodules** (`reference-library`, `anthropics-plugins`, `anthropics-skills`, `superpowers`, `image-generation`) that must be initialized and updated independently.
- **A Python toolchain** (`uv`, `pytest`, `pre-commit`, BasedPyright) that expects to live in a conventional project directory with `pyproject.toml` at the root.
- **A `hooks.json`** file that must be jq-merged into `~/.claude/settings.json` by `setup.sh` — a merge that requires the script to be outside the merge target.
- **Repository-local scripts** (`scripts/`, `tools/`) that need to reference each other by relative path without being exposed inside `~/.claude/` at runtime.

Cloning directly into `~/.claude/` breaks all four of these. The git working tree becomes the Claude Code config directory, which means `git status`, `git log`, and `pre-commit` all run against the user's live Claude config. Submodule paths that should be private to the repo (`.submodules/`) sit directly inside `~/.claude/`. The `settings.json` that `setup.sh` is supposed to write already exists as a committed file. The jq merge step has no stable file to write to.

## Decision

The repository lives at `~/dev/.claude`. After cloning, the contributor runs `setup.sh` once. `setup.sh` creates a set of symlinks from `~/.claude/` into the repository, making the agents, skills, commands, rules, standards, and reference-library appear to Claude Code exactly as if they lived natively in `~/.claude/`.

Symlinks created by `setup.sh`:

| `~/.claude/` path | Points to |
| --- | --- |
| `CLAUDE.md` | `~/dev/.claude/CLAUDE.md` |
| `agents/` | `~/dev/.claude/.claude/agents/` |
| `skills/` | `~/dev/.claude/.claude/skills/` |
| `commands/` | `~/dev/.claude/.claude/commands/` |
| `rules/` | `~/dev/.claude/.claude/rules/` |
| `standards/` | `~/dev/.claude/.claude/standards/` |
| `reference-library/` | `~/dev/.claude/.submodules/reference-library/` |
| `scripts/` | `~/dev/.claude/scripts/` |

`~/.claude/settings.json` is **not** a symlink. It is a machine-local file written by `setup.sh` during each run. The hooks block is jq-merged from `hooks.json` at repo root into this file. `claudeMdExcludes` entries for this repo are also merged in. Everything else in `settings.json` (API keys, model preferences) is left untouched.

`setup.sh` is idempotent. Re-running it after adding a new submodule or changing `hooks.json` is safe.

## Alternatives Considered

**Clone directly into `~/.claude/`**: Breaks git workflow (working tree is the live config dir), prevents jq-merge of hooks (the target file is committed), and puts private repo tooling (`.submodules/`, `tools/`, `pyproject.toml`) directly inside Claude Code's config directory.

**Install via a package manager (pip, brew, etc.)**: No suitable distribution channel exists for prompt-and-script bundles. Packaging agents and skills as a Python package would require a significant wrapper layer with no benefit.

**Copy files on each `setup.sh` run rather than symlinking**: Copies fall out of sync as soon as any file in the repo changes. Requires re-running `setup.sh` after every edit rather than just after structural changes (new directories, new hook entries). Symlinks stay in sync automatically.

**Put the repo inside `~/.claude/` as a subdirectory**: Claude Code would scan the subdirectory, potentially double-loading agents and rules. The git root would be inside the Claude config root, making `pre-commit` behavior unpredictable.

## Consequences

### Positive

- Git workflow is fully isolated from the Claude Code runtime. `git status`, `git log`, `pre-commit`, and `uv run pytest` all work as expected from `~/dev/.claude`.
- Submodule initialization (`git submodule update --init --recursive`) happens in the repo, not in `~/.claude/`, so submodule paths never bleed into the user config.
- `setup.sh --doctor` provides a live topology report showing every symlink, its target, and whether the target exists. Drift is immediately visible.
- The `hooks.json` → `settings.json` merge pattern means hook definitions are version-controlled and reproducible on any machine.

### Negative

- Two paths to keep in mind: `~/dev/.claude` for development work, `~/.claude` for Claude Code's runtime view. Contributors who forget and edit files in `~/.claude/` directly will lose their changes on the next `setup.sh` run (hooks block) or silently edit a symlinked file (agents, rules).
- `setup.sh` must be re-run when: adding a new submodule, changing `hooks.json`, or when a new symlink target is added to the install topology.

### Neutral

- `~/.claude/settings.json` is never committed to the repository. Each machine has its own copy produced by `setup.sh`. This is intentional: machine-local state (API keys, any user-specific overrides) must not be committed.

## References

- `setup.sh` — the installer; `--doctor` flag shows current symlink topology
- `hooks.json` — source of truth for the hooks block merged into `settings.json`
- `.gitmodules` — the five submodule definitions
- `docs/architecture/install-model.md` — narrative explanation with embedded diagram
- `docs/architecture/diagrams/install_layer.svg` — component diagram of this topology
- [ADR-002](ADR-002-hook-composition.md) — explains the `hooks.json` merge in detail
