---
title: "Getting Started"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Landing page for new developers onboarding to Claude Code Configuration."
tags:
  - new_dev
  - onboarding
  - getting_started
  - overview
---

This section is for someone who has just cloned the repo and wants Claude Code running with the full agent and skill library in under 15 minutes.

If you are a technical maintainer who needs to understand the architectural decisions behind what you are installing, start with the [Architecture](../architecture/index.md) section after completing install.

## Prerequisites

Before you start, make sure you have:

- **Git** — for cloning and submodule management
- **Python 3.10 or higher** — required by the repo's toolchain (`uv`, `pre-commit`, `pytest`)
- **uv** — Python package and project manager ([install instructions](https://docs.astral.sh/uv/getting-started/installation/))
- **jq** — command-line JSON processor used by `setup.sh` to merge hooks (`apt install jq` / `brew install jq`)
- **Claude Code** — a working Claude Code installation (CLI, IDE extension, or web app)

## The Five Steps

1. [Install](install.md) — clone the repo, initialize submodules, run `setup.sh`.
2. [Your First Agent](first-agent.md) — delegate a task to a specialist agent.
3. [Your First Skill](first-skill.md) — trigger a one-shot skill automation.
4. [Picking Agents vs Skills](picking.md) — learn when to use which.
5. [Troubleshooting](troubleshooting.md) — common symlink, hook, and submodule issues.

## How Long It Takes

About 15 minutes if everything goes well. The install itself (clone + `setup.sh`) is under 5 minutes; the rest is orientation. If you hit an issue, check [Troubleshooting](troubleshooting.md) before filing a bug — the most common issues have known fixes.

## Next

After you have the repo installed and have triggered your first agent and skill, the [Architecture](../architecture/index.md) section explains why things are set up the way they are — the reasoning behind the two-layer install model, the hook pipeline, MCP tiered loading, and more.
