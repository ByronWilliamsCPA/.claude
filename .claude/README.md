# Claude Configuration Directory

This directory (`.claude/`) is the **deployable Claude config artifact** — the content Claude Code
actually reads. It is symlinked into `~/.claude/` on each developer's machine via `setup.sh`.

---

## How the Two-Layer Structure Works

```text
repo root  (/home/<user>/dev/.claude/)
│
├── .claude/                   ← THIS directory — Claude's deployable config
│   ├── agents/                ← ~/.claude/agents  (via symlink from setup.sh)
│   ├── skills/                ← ~/.claude/skills  (via symlink from setup.sh)
│   ├── commands/              ← ~/.claude/commands (via symlink from setup.sh)
│   └── settings.json
│
├── .submodules/               ← standalone repos, mounted as git submodules
│   ├── reference-library/    ← github.com/ByronWilliamsCPA/reference-library
│   └── image-generation/     ← github.com/williaby/image-generation
│
├── standards/                 ← standards docs (not read by Claude directly)
├── scripts/                   ← maintenance scripts
├── mcp/                       ← MCP server configs
└── setup.sh                   ← run once after cloning to create ~/.claude/ symlinks
```

### The Symlink Chain (Local Setup)

```text
~/.claude/agents                        (dir symlink, machine-specific, created by setup.sh)
    └── document-drafter.md             (relative file symlink, committed to git, portable)
            ↓
        ../../.submodules/reference-library/agents/document-drafter.md
            ↓
        .submodules/reference-library/agents/document-drafter.md  (real file in submodule)
```

The outer dir symlink (`~/.claude/agents`) is created by `setup.sh` — it is machine-specific
and never committed. The inner file symlinks (inside `agents/`) use relative paths and ARE
committed to git, so they work on any machine without modification.

---

## Invariants — Do Not Break

These constraints keep the local and repo approaches working simultaneously.
Violating any of these breaks either `~/.claude/` resolution or cross-machine portability.

1. **`.claude/agents/`, `.claude/skills/`, `.claude/commands/` must stay at these exact paths.**
   `~/.claude/` symlinks point here. Renaming or moving these directories breaks every project
   on every machine that has run `setup.sh`.

2. **Symlinks inside `.claude/agents/` must use relative paths only.**
   Form: `../../.submodules/<repo-name>/path/to/file.md`
   Never use absolute paths — they are machine-specific and break on clone.

3. **All submodules live under `.submodules/` at the repo root.**
   This keeps the relative depth from `.claude/agents/` consistent (`../../.submodules/`).
   Adding a submodule anywhere else breaks the relative symlink pattern.

4. **Agents native to this repo are regular files in `.claude/agents/`.**
   Only content owned by a standalone repo uses a submodule symlink.

5. **`setup.sh` is the only place machine-specific paths appear.**
   Everything inside `.claude/` must be portable across machines.

6. **Never substitute `{{LIBRARY_PATH}}` into source files.**
   Agents in `.submodules/reference-library/agents/` use `{{LIBRARY_PATH}}` as a placeholder.
   `setup.sh` resolves this by symlinking the submodule to `~/.claude/reference-library` — a
   stable, predictable path on every machine. Substituting absolute paths into source files
   breaks portability and will corrupt the submodule on the next `git restore`.

---

## Adding a New Agent

### Native agent (owned by this repo)

```bash
# Just add the file — immediately available globally after setup.sh has run
touch .claude/agents/my-new-agent.md
```

### Agent from an existing submodule

```bash
cd .claude/agents
ln -s ../../.submodules/reference-library/agents/new-agent.md new-agent.md
```

### Agent from a new standalone repo

```bash
# 1. Add the submodule
git submodule add https://github.com/org/repo.git .submodules/repo-name

# 2. Create the relative symlink
cd .claude/agents
ln -s ../../.submodules/repo-name/agents/agent-name.md agent-name.md

# 3. Verify it resolves before committing
ls -la .claude/agents/agent-name.md
```

---

## Adding a New Skill

Skills are always native to this repo — no submodule pattern applies:

```bash
mkdir .claude/skills/my-skill
touch .claude/skills/my-skill/SKILL.md
```

---

## Updating Submodule Content

```bash
# Pull latest from all submodules
git submodule update --remote

# Pull latest from one submodule
git submodule update --remote .submodules/reference-library

# Commit the updated submodule reference
git add .submodules/reference-library
git commit -m "chore: update reference-library submodule"
```

## Editing Content in a Submodule

Edits can be made directly inside the submodule directory and pushed back to the standalone repo:

```bash
cd .submodules/reference-library
# edit files
git add .
git commit -m "feat: update agent"
git push origin main

# Record the new commit reference in the parent repo
cd ../..
git add .submodules/reference-library
git commit -m "chore: update reference-library submodule"
```

---

## New Developer Setup

```bash
git clone --recurse-submodules https://github.com/ByronWilliamsCPA/.claude.git ~/dev/.claude
cd ~/dev/.claude
./setup.sh
```

`setup.sh` creates three symlinks:

- `~/.claude/agents`   → `~/dev/.claude/.claude/agents`
- `~/.claude/skills`   → `~/dev/.claude/.claude/skills`
- `~/.claude/commands` → `~/dev/.claude/.claude/commands`

After that, every project on the machine has access to all agents and skills automatically —
no project-level configuration required.

---

## Current Submodule Registry

| Submodule         | Path                            | Standalone Repo                                                                             | Content                                             |
| ----------------- | ------------------------------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| reference-library | `.submodules/reference-library` | [ByronWilliamsCPA/reference-library](https://github.com/ByronWilliamsCPA/reference-library) | 7 writing pipeline agents                           |
| image-generation  | `.submodules/image-generation`  | [williaby/image-generation](https://github.com/williaby/image-generation)                   | diagram-specialist agent, IMAGE_GENERATION_GUIDE.md |
