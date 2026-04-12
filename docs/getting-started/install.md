---
title: "Install"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Step-by-step install guide for Claude Code Configuration."
tags:
  - new_dev
  - install
  - setup
  - installation
---

This page walks through installing Claude Code Configuration from scratch. The install creates symlinks from `~/.claude/` into the repo — Claude Code sees the agents, skills, and rules as native config, while the repo stays version-controlled at `~/dev/.claude`.

For the design rationale behind this two-layer approach, see [Architecture → Install Model](../architecture/install-model.md).

## Prerequisites

- **Git** with SSH or HTTPS access to GitHub
- **Python 3.10+** (`python3 --version`)
- **uv** (`uv --version` — if missing, see [uv install docs](https://docs.astral.sh/uv/getting-started/installation/))
- **jq** (`jq --version` — if missing: `apt install jq` or `brew install jq`)
- A working Claude Code installation

## Clone the Repository

```bash
git clone --recurse-submodules https://github.com/ByronWilliamsCPA/.claude.git ~/dev/.claude
```

The `--recurse-submodules` flag initializes all five submodules in a single step. Without it, you will need to run `git submodule update --init --recursive` afterward (see below).

If you cloned without `--recurse-submodules`:

```bash
cd ~/dev/.claude
git submodule update --init --recursive
```

## Run setup.sh

```bash
cd ~/dev/.claude
./setup.sh
```

`setup.sh` is safe to re-run at any time — every operation is idempotent. It will:

1. Check for required commands (`ln`, `git`) and warn if `jq` is missing.
2. Initialize any uninitialized submodules.
3. Create `~/.claude/` if it does not exist.
4. Create symlinks from `~/.claude/{agents,skills,commands,rules,standards,reference-library,scripts}` and `~/.claude/CLAUDE.md` into the repo.
5. Back up `~/.claude/settings.json` (if it exists) and merge the hooks from `hooks.json` into it via jq.
6. Merge `claudeMdExcludes` entries for this repo into `settings.json`.

The full detail of what each step does is in [Architecture → Install Model](../architecture/install-model.md).

## Verify the Install

Run the doctor check:

```bash
./setup.sh --doctor
```

This prints every expected symlink, its current target, and whether the target exists. You should see `[ok]` next to all entries.

Manual checks:

```bash
# Confirm symlinks are in place
ls -la ~/.claude/agents ~/.claude/skills ~/.claude/rules

# Confirm hooks merged
jq '.hooks | keys' ~/.claude/settings.json
# Expected: ["PostToolUse", "PreToolUse", "Stop", "UserPromptSubmit"]
```

## Install the Python Toolchain (Optional — Required for Contributing)

If you plan to run tests, lint, or pre-commit hooks:

```bash
cd ~/dev/.claude
uv sync --all-extras
uv run pre-commit install
```

Verify:

```bash
uv run pytest -v
```

## Uninstall or Re-run

To reset the symlinks and hooks without touching anything else:

```bash
./setup.sh
```

To fully remove the Claude Code Configuration install (does not delete the repo):

```bash
# Remove symlinks from ~/.claude/
rm ~/.claude/CLAUDE.md
rm ~/.claude/agents ~/.claude/skills ~/.claude/commands
rm ~/.claude/rules ~/.claude/standards
rm ~/.claude/reference-library ~/.claude/scripts
# Optionally: remove the hooks block from ~/.claude/settings.json manually
```

## Next

[Your First Agent](first-agent.md) — invoke a specialist agent in a Claude Code session.
