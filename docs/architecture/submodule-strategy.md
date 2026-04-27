---
title: "Submodule Strategy"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Narrative description of how git submodules integrate external capabilities into the repo."
tags:
  - architecture
  - submodules
  - technical
---

The repo extends Claude's capabilities by incorporating five external trees as git submodules. Each submodule is a separately maintained upstream repository, pinned to a specific commit. `setup.sh` wires them into the runtime config (`~/.claude/`) via symlinks, making them first-class citizens of the Claude Code install without vendor-copying their contents.

For the reasoning behind this design, see [ADR-005](adr/ADR-005-submodule-extension-model.md).

## The Five Submodules

| Submodule path | Upstream | What it provides |
| --- | --- | --- |
| `.submodules/reference-library/` | `ByronWilliamsCPA/reference-library` | Agent prompt templates using `{{LIBRARY_PATH}}` placeholders for parameterized agent paths |
| `.submodules/image-generation/` | `williaby/image-generation` | Agents and utilities for image generation workflows |
| `.submodules/superpowers/` | `obra/superpowers` | Community-maintained skills: brainstorming, writing-plans, TDD, systematic debugging, git-worktrees, review patterns |
| `.submodules/anthropics-skills/` | `anthropics/skills` | Official Anthropic skill collection |
| `.submodules/anthropics-plugins/` | `anthropics/claude-plugins-official` | hookify plugin engine and security-guidance hooks used by the hook pipeline |

## How `setup.sh` Wires Them

Each submodule under `.submodules/` is populated by:

```bash
git submodule update --init --recursive
```

`setup.sh` runs this automatically if the submodules have not been initialized (checked by looking for a sentinel file in `reference-library`).

After initialization, `setup.sh` creates one additional symlink beyond the standard set:

```bash
~/.claude/reference-library/ → ~/dev/.claude/.submodules/reference-library/
```

This makes the reference library accessible at `~/.claude/reference-library/`, which is the path the `{{LIBRARY_PATH}}` placeholder resolves to. Agents in the reference library reference each other using that placeholder; resolving it to `~/.claude/reference-library` lets them work without hardcoded paths.

The other submodules (`superpowers`, `anthropics-skills`, `image-generation`) are accessed by Claude Code via the `.claude/skills/` symlink, which points to `.claude/skills/` in this repo. Skills from those submodules should be added to `.claude/skills/` if they need to be reachable at runtime: the submodule content itself is not automatically in the skill load path.

`anthropics-plugins` is not symlinked into `~/.claude/`. The hook scripts in `hooks.json` reference it directly by absolute path:

```bash
$HOME/dev/.claude/.submodules/anthropics-plugins/plugins/hookify/...
```

This keeps the plugin engine out of the user-visible `~/.claude/` namespace while making it accessible to the hook pipeline.

## Upstream Update Flow

To pull upstream changes from any submodule:

```bash
cd ~/dev/.claude
git submodule update --remote --merge .submodules/<name>
git add .submodules/<name>
git commit -m "chore(submodules): update <name> to latest upstream"
```

Run `./setup.sh` afterward if the submodule added new content that needs to be symlinked (e.g., new skills that reference a different path).

To update all submodules at once:

```bash
git submodule update --remote --merge
```

Review diffs carefully before committing. Upstream changes can include breaking changes to hook scripts (in `anthropics-plugins`) or new skill triggers (in `superpowers`) that conflict with existing configuration.

To verify nothing broke after an update:

```bash
./setup.sh --doctor
uv run pytest
uv run mkdocs build
```

## The `{{LIBRARY_PATH}}` Convention

Agent templates in `reference-library` use `{{LIBRARY_PATH}}` as a placeholder for the path where the library is installed. When using these templates, substitute `~/.claude/reference-library`:

```text
{{LIBRARY_PATH}} → ~/.claude/reference-library
```

`setup.sh` prints a reminder about this at the end of every run. Automated substitution tooling is a candidate for a future improvement.

## See Also

- [ADR-005 Submodule Extension Model](adr/ADR-005-submodule-extension-model.md): why submodules over vendoring or packaging
- [Install Model](install-model.md): how `setup.sh` creates the symlink topology
- [Hook Pipeline](hook-pipeline.md): how `anthropics-plugins/hookify` is used by the hook system
- `.gitmodules`: the five submodule definitions with upstream URLs
