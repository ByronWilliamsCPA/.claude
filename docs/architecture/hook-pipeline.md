---
title: "Hook Pipeline"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Narrative description of the hook lifecycle across a Claude Code conversation turn."
tags:
  - architecture
  - hooks
  - technical
---

Claude Code fires hooks at five points during a session. These hooks enforce quality gates, route behavioral rules, and extend Claude's capabilities without requiring model-level changes. The hook definitions live in `hooks.json` at repo root and are merged into `~/.claude/settings.json` by `setup.sh`.

For the design decisions behind this system, see [ADR-002](adr/ADR-002-hook-composition.md).

## The Five Hook Types

**UserPromptSubmit**: fires immediately after the user sends a message, before Claude processes it. Used for: injecting context, detecting intent signals (PR review reminder), running the hookify user prompt pipeline.

**PreToolUse**: fires before each tool call Claude attempts. Each entry in the `PreToolUse` array can have a matcher regex targeting specific tools. Used for: secrets file guard (Edit/Write), planning bridge gate (Skill), security reminder (Edit/Write/MultiEdit), hookify dispatch (all tools).

**PostToolUse**: fires after each tool call completes. Used for: Python 3.10 compatibility check (Edit/Write), hookify dispatch (all tools).

**Stop**: fires when Claude finishes its turn (before control returns to the user). Used for: hookify stop handler.

**SessionStart**: fires once when a new Claude Code session opens. Six entries are defined in `hooks.json`, running in array order: keyword reset (`keyword-tool-trigger.sh --reset`), superpowers (`run-superpowers-session-start.sh`), session rules (`session-start-rules.sh`), skills manifest (`generate-skills-manifest.sh`), CLI tools (`install-cli-tools.sh`), and harness doctor (`harness-doctor.sh`).

## Diagram

![Hook pipeline sequence diagram](diagrams/hook_pipeline.svg)

## Execution Order Across a Turn

Two files register hooks in this repo. `hooks.json` at repo root is the single authoring source per [ADR-002](adr/ADR-002-hook-composition.md); `setup.sh` merges it into the user-scope `~/.claude/settings.json`. The committed `.claude/settings.json` in this repo registers project-scope hooks that apply only when working inside this repository. Claude Code loads both files and fires every matching hook from each; cross-file ordering between the two is not guaranteed, so each step below names its registering file.

A single user message triggers the following hook sequence:

```text
User sends message
  → UserPromptSubmit (hooks.json, no matcher): hookify userpromptsubmit.py, then pr-review-reminder.py
  → UserPromptSubmit (hooks.json, matcher .*): keyword-tool-trigger.sh

  Model processes, issues tool calls. The no-matcher hookify PreToolUse and
  PostToolUse entries fire on every call; matcher-specific entries fire in
  addition, based on the tool name:

    Bash calls:
      → PreToolUse (hooks.json, matcher Bash): bash-pre-hook.sh
      → PreToolUse (hooks.json, no matcher): hookify pretooluse.py
      → Tool executes
      → PostToolUse (hooks.json, no matcher): hookify posttooluse.py
      → PostToolUse (.claude/settings.json, matcher Bash): bash-notify.sh

    Write / Edit / MultiEdit calls:
      → PreToolUse (hooks.json, matcher Write|Edit|MultiEdit): tdd-enforcement-hook.sh
      → PreToolUse (hooks.json, matcher Edit|Write|MultiEdit): sensitive-file-guard.sh
      → PreToolUse (hooks.json, matcher Edit|Write|MultiEdit, existence-guarded): security_reminder_hook.py
      → PreToolUse (hooks.json, no matcher): hookify pretooluse.py
      → Tool executes
      → PostToolUse (hooks.json, matcher Edit|Write): py310-compat-check.sh
      → PostToolUse (hooks.json, matcher Edit|Write|MultiEdit): snyk-dep-reminder.sh
      → PostToolUse (hooks.json, no matcher, existence-guarded): hookify posttooluse.py
      → PostToolUse (.claude/settings.json, matcher Edit|Write): ruff check --fix (inline), shellcheck on *.sh (inline), validate-frontmatter.sh
      → FileChanged (.claude/settings.json, matcher (^|/)\.env[^/]*$): env-file-audit.sh, fires only when the changed file's name starts with .env

    Skill calls:
      → PreToolUse (hooks.json, matcher Skill): planning-bridge-gate.sh
      → PreToolUse (hooks.json, no matcher): hookify pretooluse.py
      → Tool executes
      → PostToolUse (hooks.json, no matcher, existence-guarded): hookify posttooluse.py

    mcp__* calls:
      → PreToolUse (hooks.json, no matcher): hookify pretooluse.py
      → Tool executes
      → PostToolUse (hooks.json, matcher mcp__*): track-mcp-usage.sh
      → PostToolUse (hooks.json, no matcher, existence-guarded): hookify posttooluse.py

    Any other tool call:
      → PreToolUse (hooks.json, no matcher): hookify pretooluse.py
      → Tool executes
      → PostToolUse (hooks.json, no matcher, existence-guarded): hookify posttooluse.py

  Model turn ends
    → Stop (hooks.json, no matcher, existence-guarded): hookify stop.py
    → Stop (.claude/settings.json, no matcher): stop-pre-commit-hook.sh (runs pre-commit against touched files)
```

Array position determines execution order within a single hook type inside one file. Matcher-specific entries run only when their regex matches the tool being called; entries without a matcher run on every call for that hook type.

## Per-Hook Responsibilities

### UserPromptSubmit

| Script | What it does |
| --- | --- |
| `hookify/hooks/userpromptsubmit.py` | Dispatches to registered hookify plugins for the UserPromptSubmit event |
| `scripts/pr-review-reminder.py` | Detects when the user's message looks like a PR review request and injects a reminder about the review workflow |

### PreToolUse

| Matcher | Script | What it does |
| --- | --- | --- |
| `Edit\|Write\|MultiEdit` | `scripts/sensitive-file-guard.sh` | Blocks writes to secret- and credential-bearing paths, exit code 2 on match (see pattern list below) |
| `Skill` | `scripts/planning-bridge-gate.sh` | Enforces plan-approval workflow before any Skill invocation |
| `Edit\|Write\|MultiEdit` | `security_reminder_hook.py` | Surfaces OWASP-style security reminders when editing files |
| (all tools) | `hookify/hooks/pretooluse.py` | Dispatches to hookify plugin engine |

`scripts/sensitive-file-guard.sh` blocks these path patterns:

- `.env` files (any suffix, e.g. `.env.local`) and `settings.local.json`
- SSH private keys: `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519` (the matching `.pub` public keys are allowed)
- AWS credentials: `.aws/credentials`, `.aws/config`
- Package and registry tokens: `.netrc`, `.npmrc`, `.pypirc`, `.docker/config.json`
- gcloud credentials: `application_default_credentials.json`, `gcloud/credentials.db`
- TLS and GPG private material: `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.kdbx`, and GPG keyring paths (`.gnupg/*`, `secring.gpg`, `private-keys-v1.d/*`)
- Secrets baselines: `*secrets.baseline` (overwriting it would suppress detect-secrets findings)

### PostToolUse

| Matcher | Script | What it does |
| --- | --- | --- |
| `Edit\|Write` | `scripts/py310-compat-check.sh` | Checks modified Python files for syntax that breaks on Python 3.10 |
| (all tools) | `hookify/hooks/posttooluse.py` | Dispatches to hookify plugin engine |

### Stop

| Script | What it does |
| --- | --- |
| `hookify/hooks/stop.py` | Dispatches to hookify plugin engine's stop handlers |

## hookify Dispatch

hookify is a plugin engine from the `anthropics-plugins` submodule (`claude-plugins-official`). It provides a shared rule engine that multiple plugins can hook into without each needing its own top-level hook entry. When hookify's `pretooluse.py` fires, it reads the list of registered plugins from `CLAUDE_PLUGIN_ROOT` and dispatches to each one's handler.

`setup.sh` creates `~/.claude/plugin-hooks` as a symlink to `<repo>/.submodules/anthropics-plugins/plugins`, so the path is stable regardless of where the repo is cloned. Each hookify entry in `hooks.json` sets `CLAUDE_PLUGIN_ROOT` from that symlinked path:

```bash
CLAUDE_PLUGIN_ROOT="$HOME/.claude/plugin-hooks/hookify"
```

Every hookify (and security-guidance) command line is also guarded by an existence check on the handler file before running it, for example:

```bash
if [ -f "$HOME/.claude/plugin-hooks/hookify/hooks/pretooluse.py" ]; then
  CLAUDE_PLUGIN_ROOT="$HOME/.claude/plugin-hooks/hookify" python3 "$HOME/.claude/plugin-hooks/hookify/hooks/pretooluse.py"
else
  echo "[hookify] skipped: plugin hooks not installed" >&2
fi
```

If the symlink target is absent (submodules not initialized, or `setup.sh` has not run yet), the command no-ops cleanly: it prints a skipped notice to stderr and exits 0 instead of failing the tool call. This means hookify plugins are loaded from `~/.claude/plugin-hooks/`, a symlink into the submodule, rather than a hardcoded absolute repo path. Adding a new hookify plugin still requires a submodule change, not just a `hooks.json` edit.

## Adding a New Hook

1. Write your script and place it in `scripts/`.
2. Add an entry to `hooks.json` under the appropriate hook type with the correct matcher.
3. Run `./setup.sh` to merge the updated `hooks.json` into `~/.claude/settings.json`.
4. Test with a Claude Code session.

For the full workflow, see [Contributing → Adding a Hook](../contributing/adding-hooks.md).

## See Also

- [ADR-002 Hook Composition and Ordering](adr/ADR-002-hook-composition.md): why hooks.json is the source of truth
- [Install Model](install-model.md): how hooks.json gets merged into settings.json
- [Contributing → Adding a Hook](../contributing/adding-hooks.md): step-by-step hook authoring guide
