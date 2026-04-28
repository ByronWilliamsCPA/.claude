---
title: "Troubleshooting"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Common install and runtime issues with their diagnostic steps."
tags:
  - new_dev
  - install
  - guide
---

Start every troubleshooting session with:

```bash
cd ~/dev/.claude && ./setup.sh --doctor
```

The doctor mode reports every expected symlink and its status. If any entry shows `[miss]`, `[dangle]`, or `[drift]`, re-run `./setup.sh` to repair it.

## Symlinks Missing from `~/.claude/`

**Symptom**: Claude Code cannot find an agent or skill that exists in `~/dev/.claude/.claude/`.

**Diagnose**:

```bash
ls -la ~/.claude/agents
# Should be: ~/.claude/agents -> /home/<you>/dev/.claude/.claude/agents
```

**Fix**: Re-run `./setup.sh`. If the symlink target was a real directory (not a symlink), `setup.sh` will warn and skip it. In that case, back up and remove the real directory first:

```bash
mv ~/.claude/agents ~/.claude/agents.bak
./setup.sh
```

## `hooks.json` Not Merged into `settings.json`

**Symptom**: Hooks do not fire. `jq .hooks ~/.claude/settings.json` returns empty or null.

**Diagnose**:

```bash
jq '.hooks | keys' ~/.claude/settings.json
# Expected: ["PostToolUse", "PreToolUse", "Stop", "UserPromptSubmit"]
```

**Cause 1: jq was not installed when you ran `setup.sh`**: Install jq and re-run:

```bash
apt install jq   # or brew install jq
./setup.sh
```

**Cause 2: `settings.json` has a syntax error or unexpected structure**:

```bash
jq '.' ~/.claude/settings.json
```

If this fails, the file is malformed. Restore from the most recent backup (`~/.claude/settings.json.bak.*`) and re-run `./setup.sh`.

## Submodules Empty

**Symptom**: `.submodules/reference-library/` (or another submodule directory) is empty after clone.

**Cause**: You cloned without `--recurse-submodules`.

**Fix**:

```bash
cd ~/dev/.claude
git submodule update --init --recursive
./setup.sh
```

## MCP Tool Not Loaded

**Symptom**: An expected MCP tool (`postgres.*`, `playwright.*`, `docker.*`) is not available in a session.

**Diagnose**: Determine the tool's tier:

- **Tier 1** tools load at session start. If a Tier 1 tool is missing, check `~/.claude/settings.json` for the MCP server configuration.
- **Tier 2** tools load when their agent is invoked. Invoke the agent explicitly; the tool bundle loads with it.
- **Tier 3** tools load when trigger keywords appear. Include the relevant keyword (e.g., "docker", "database", "playwright") in your prompt.

See [Architecture → MCP Tiered Loading](../architecture/mcp-tiered-loading.md) for the full tier breakdown and keyword list.

## Agent Not Found / `subagent_type` Error

**Symptom**: An `Agent` tool call fails with an unknown agent type.

**Diagnose**:

```bash
ls ~/.claude/agents/
```

If the agent file is missing, the `agents/` symlink may be broken. Run `./setup.sh --doctor`.

If the file exists but the agent type string does not match, check the `name:` field in the agent's frontmatter:

```bash
grep '^name:' ~/.claude/agents/<filename>.md
```

The `subagent_type` must match the `name:` field exactly (not the filename).

## Pre-commit Hook Fails on Commit

**Symptom**: `git commit` fails because a pre-commit hook exits non-zero.

**Fix**: Read the error output carefully: pre-commit failures identify exactly which check failed and what to fix. The most common causes are Ruff lint errors, BasedPyright type errors, or frontmatter validation failures.

Do not use `--no-verify` to bypass hooks. Fix the underlying issue.

## Where to File Issues

If none of the above resolves your problem, open a GitHub issue:

- **Bug reports**: `https://github.com/ByronWilliamsCPA/.claude/issues`
- **General questions**: `https://github.com/ByronWilliamsCPA/.claude/discussions`

Include the output of `./setup.sh --doctor` and any relevant error messages.
