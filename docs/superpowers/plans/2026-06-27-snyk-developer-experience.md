---
schema_type: planning
title: "Snyk Developer Experience Implementation Plan"
status: draft
owner: core-maintainer
purpose: "Wire Snyk into the global Claude Code config so every repo gets dependency scanning and SAST secrets detection during authoring, before any commit exists."
component: Development-Tools
source: "docs/superpowers/plans/2026-06-27-snyk-developer-experience.md"
tags:
  - security
  - tooling
  - compliance
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Snyk into the global Claude Code config so every repo gets dependency scanning (SCA) and SAST secrets detection during authoring, before any commit exists.

**Architecture:** Three complementary layers -- a setup standard documenting the one-time workstation config, a path-scoped rule that reminds the agent to invoke Snyk when dependency files change, and a PostToolUse hook that fires the same reminder as a second enforcement point. A pre-commit entry closes the bypass window left by `--no-verify`. The Snyk MCP Server is Tier 2 (on-demand) in the MCP loading strategy, not always-loaded.

**Tech Stack:** Snyk CLI, Snyk MCP Server (`npx snyk@latest mcp configure`), Claude Code hooks (PostToolUse), pre-commit, bash, Python 3 (stdlib only for hook script)

---

## File Structure

| Action | Path | Purpose |
|--------|------|---------|
| Create | `standards/snyk-mcp-setup.md` | One-time workstation setup, which tools to expose, when to invoke each |
| Create | `rules/snyk-mcp.md` | Path-scoped rule; fires when editing pyproject.toml / requirements / uv.lock |
| Modify | `rules/pre-commit.md` | Add Snyk secrets gate checkbox to Security section |
| Modify | `rules/mcp-strategy.md` | Add Snyk to Tier 2 agent bundle table |
| Create | `scripts/snyk-dep-reminder.sh` | PostToolUse hook script; reads stdin JSON, checks file_path |
| Modify | `~/.claude/settings.json` | Add PostToolUse hook entry wiring the reminder script |
| Modify | `projects/-home-byron-dev--claude/memory/MEMORY.md` | Add pointer to snyk-mcp-setup.md |
| Modify | `CLAUDE.md` (global) | Add Snyk standard reference in Core development standards (LOW) |

---

## Task 1: Create feature branch

**Files:** none (git only)

- [ ] **Step 1: Confirm current branch and working tree is clean**

```bash
git -C /home/byron/dev/.claude status
git -C /home/byron/dev/.claude branch --show-current
```

Expected: working tree clean, current branch shown (not `main`; if on `main` proceed to next step).

- [ ] **Step 2: Create and switch to the feature branch**

```bash
git -C /home/byron/dev/.claude checkout -b claude/snyk-developer-experience-0 main
```

Expected output: `Switched to a new branch 'claude/snyk-developer-experience-0'`

- [ ] **Step 3: Confirm branch**

```bash
git -C /home/byron/dev/.claude branch --show-current
```

Expected: `claude/snyk-developer-experience-0`

---

## Task 2: Create standards/snyk-mcp-setup.md

**Files:**
- Create: `~/.claude/standards/snyk-mcp-setup.md`

This is the primary reference document. All other files point back to it.

- [ ] **Step 1: Write the file**

Create `/home/byron/dev/.claude/standards/snyk-mcp-setup.md` with this exact content:

````markdown
# Snyk MCP Server Setup

> **Status**: Active | Standard
> **Version**: 1.0.0
> **Last Updated**: 2026-06-27
> **References**: `rules/snyk-mcp.md`, `rules/mcp-strategy.md`, `standards/mcp-minimal-bloat.md`

Snyk MCP Server enables Claude Code to invoke `snyk test` and `snyk code test`
inline during authoring, before any commit exists. This closes the vulnerability
detection gap between writing code and pushing it to GitHub.

## One-time setup (per workstation)

```bash
# Install Snyk CLI globally
npm install -g snyk
# Alternative on macOS: brew install snyk

# Authenticate (browser opens; use GitHub SSO or personal token)
snyk auth

# Configure MCP Server for Claude Code
npx -y snyk@latest mcp configure --tool=claude-cli
```

The configure command writes a `snyk-mcp` entry to `~/.claude/settings.json`
automatically.

## Verify the MCP entry

After running the configure command, open `~/.claude/settings.json` and confirm
a `snyk-mcp` block appears under `mcpServers`. If the entry is missing, re-run
the configure command.

## Snyk MCP tools

Snyk MCP Server exposes multiple tools. Per `standards/mcp-minimal-bloat.md`,
only tools that earn their token cost are documented here.

| Tool | Purpose | When to invoke |
|------|---------|----------------|
| `snyk_test` | SCA: checks the project against the Snyk advisory database | After adding or upgrading a dependency in pyproject.toml, requirements*.txt, or uv.lock |
| `snyk_code_test` | SAST: scans specified file paths for code vulnerabilities | Before committing a new authentication module, secrets handler, or user-input processor |
| `snyk_monitor` | Pushes a snapshot to the Snyk org dashboard | **Manual only; do not invoke automatically** (see below) |

## When to invoke snyk_test

Invoke `snyk_test` on the project root when:

- A new package is added via `uv add`, `pip install`, or direct requirements edit.
- A dependency is upgraded in pyproject.toml, requirements*.txt, or uv.lock.
- Reviewing a PR that adds new MCP tool dependencies.

If `snyk_test` returns HIGH or CRITICAL findings on the newly added package,
surface the finding to the user before proceeding. Do not block the edit
unilaterally; report and let the user decide.

If `SNYK_TOKEN` is not set or the MCP server is not configured, note the gap
and continue without blocking.

## When to invoke snyk_code_test

Invoke `snyk_code_test` on the changed files before committing:

- A new authentication or session-handling module.
- A module that processes user-supplied input.
- A module that handles secrets, tokens, or credentials.

## snyk_monitor: manual only

`snyk_monitor` creates a persistent project entry in the Snyk organisation
dashboard. Automatic calls accumulate entries that require manual cleanup.
Rules and hooks in this config do NOT call `snyk_monitor`. Use it only when
deliberately registering a project for ongoing Snyk monitoring.

## Snyk MCP Scan (pre-GA as of 2026-06)

Snyk MCP Scan scans MCP configuration files for prompt-injection risks. It is
not generally available yet. When it reaches GA, add a pre-push hook that runs
`snyk mcp-scan` on `.claude/settings.json` and any project-local MCP
configuration files. Track the GA announcement at
https://docs.snyk.io/snyk-cli/mcp.

## Tier placement

Snyk MCP Server is Tier 2 (on-demand) per `rules/mcp-strategy.md`. It is
NOT in the always-loaded `mcpServers` block. The path-scoped rule
`rules/snyk-mcp.md` and the PostToolUse hook in `settings.json` serve as
reminder enforcement points during authoring.
````

- [ ] **Step 2: Verify no em-dashes were introduced**

```bash
grep -n -- "--" /home/byron/dev/.claude/standards/snyk-mcp-setup.md | grep -v "bash\|npm\|brew\|npx\|snyk\|uv\|pip\|pre-" || echo "clean"
```

Look at any hits and confirm they are CLI flags (`--tool`, `--frozen`) not prose em-dashes. The `no-em-dash` pre-commit hook will catch actual em-dashes.

- [ ] **Step 3: Stage and commit**

```bash
git -C /home/byron/dev/.claude add standards/snyk-mcp-setup.md
git -C /home/byron/dev/.claude commit -S -m "docs(standards): add Snyk MCP Server setup standard"
```

---

## Task 3: Create rules/snyk-mcp.md (path-scoped rule)

**Files:**
- Create: `~/.claude/rules/snyk-mcp.md`

This rule activates only when the agent edits dependency files, matching the
same pattern used by `rules/python.md` (`paths:` plural list format).

- [ ] **Step 1: Confirm existing rules frontmatter format**

```bash
head -5 /home/byron/dev/.claude/rules/python.md
```

Expected: `paths:` key with a list (not `path:` singular). Proceed only after confirming.

- [ ] **Step 2: Write the file**

Create `/home/byron/dev/.claude/rules/snyk-mcp.md` with this content:

```markdown
---
paths:
  - "**/pyproject.toml"
  - "**/requirements*.txt"
  - "**/uv.lock"
---

# Snyk MCP: Dependency Review Rule

When a dependency is added or upgraded in a file this rule matches:

1. After the change is written, invoke the `snyk_test` MCP tool on the project root.
2. If `snyk_test` returns HIGH or CRITICAL findings on the newly added package,
   surface the finding to the user before proceeding.
3. Do NOT invoke `snyk_monitor` automatically.
4. Do NOT block the edit based solely on `snyk_test` output; report findings and
   let the user decide.

When `snyk_test` is not available (SNYK_TOKEN not set or MCP server not configured),
note the gap and continue without blocking.

**Full setup instructions:** `~/.claude/standards/snyk-mcp-setup.md`
```

- [ ] **Step 3: Stage and commit**

```bash
git -C /home/byron/dev/.claude add rules/snyk-mcp.md
git -C /home/byron/dev/.claude commit -S -m "feat(rules): add path-scoped Snyk MCP dependency review rule"
```

---

## Task 4: Update rules/pre-commit.md (Security section)

**Files:**
- Modify: `~/.claude/rules/pre-commit.md:26-31` (Security section)

Add two items to the existing Security checklist: the Snyk secrets gate and a
pre-GA placeholder for Snyk MCP Scan.

- [ ] **Step 1: Read the current Security section**

```bash
grep -n "Security" /home/byron/dev/.claude/rules/pre-commit.md | head -10
```

Confirm the section starts around line 26 and the first item is the pip-audit entry.

- [ ] **Step 2: Add the two new checkboxes after the pip-audit item**

In `/home/byron/dev/.claude/rules/pre-commit.md`, after this existing line:

```markdown
- [ ] **Security Scanning**: pip-audit runs automatically on pre-push when dependency files change (pyproject.toml, requirements*.txt, uv.lock). Exit code 64 = advisory found; medium+ severity blocks push. For manual audit: `uv run pip-audit`
```

Insert these two lines immediately after:

```markdown
- [ ] **Snyk Secrets Gate**: If `SNYK_TOKEN` is set, run `snyk code test --detection-type=secrets <changed-dirs>` on staged Python files before push. This closes the `--no-verify` bypass vector for the local trufflehog hook. Reference: `standards/snyk-mcp-setup.md`.
- [ ] **Snyk MCP Scan (pre-GA)**: When `snyk mcp-scan` reaches GA, add a pre-push hook scanning `.claude/settings.json` and project-local MCP configs for prompt-injection risks. Track at https://docs.snyk.io/snyk-cli/mcp.
```

- [ ] **Step 3: Verify the Security section looks correct**

```bash
grep -A 10 "^## Security" /home/byron/dev/.claude/rules/pre-commit.md
```

Confirm all three security items appear in order: pip-audit, Snyk Secrets Gate, Snyk MCP Scan.

- [ ] **Step 4: Stage and commit**

```bash
git -C /home/byron/dev/.claude add rules/pre-commit.md
git -C /home/byron/dev/.claude commit -S -m "feat(rules): add Snyk secrets gate and MCP Scan placeholder to pre-commit checklist"
```

---

## Task 5: Update rules/mcp-strategy.md (Tier 2)

**Files:**
- Modify: `~/.claude/rules/mcp-strategy.md` (Tier 2 agent bundles table + note)

Add Snyk MCP tools to the `security-auditor` bundle row in the Tier 2 table,
and add a note that Snyk MCP Server requires separate one-time configuration.

- [ ] **Step 1: Find the security-auditor row**

```bash
grep -n "security-auditor" /home/byron/dev/.claude/rules/mcp-strategy.md
```

Note the line number. The current row reads:
`| security-auditor | \`zen.secaudit\`, \`sentry.*\`, \`github.code_security\`, \`postgres.analyze_db_health\` |`

- [ ] **Step 2: Replace the security-auditor row**

In `/home/byron/dev/.claude/rules/mcp-strategy.md`, replace the line:

```markdown
| security-auditor | `zen.secaudit`, `sentry.*`, `github.code_security`, `postgres.analyze_db_health` |
```

with:

```markdown
| security-auditor | `zen.secaudit`, `sentry.*`, `github.code_security`, `postgres.analyze_db_health`, `snyk_test`, `snyk_code_test` |
```

- [ ] **Step 3: Add a note after the Tier 2 tables**

In `/home/byron/dev/.claude/rules/mcp-strategy.md`, after the Skill Bundles table
(the table that ends with the `/project-planning` row), add:

````markdown
### Snyk MCP Server (Tier 2)

`snyk_test` and `snyk_code_test` are surfaced to the `security-auditor` agent
bundle. The Snyk MCP Server requires one-time workstation setup before these
tools are available:

```bash
npx -y snyk@latest mcp configure --tool=claude-cli
```

Full setup instructions and tool invocation guidance: `standards/snyk-mcp-setup.md`.

Do NOT add Snyk MCP Server to the always-loaded `mcpServers` block. It is
on-demand only, per `standards/mcp-minimal-bloat.md`.

`snyk_monitor` must not be called from any agent bundle or hook. See
`standards/snyk-mcp-setup.md` for the reason.
````

- [ ] **Step 4: Verify changes**

```bash
grep -n "snyk" /home/byron/dev/.claude/rules/mcp-strategy.md
```

Expected: hits on the security-auditor row and the new Snyk MCP Server section.

- [ ] **Step 5: Stage and commit**

```bash
git -C /home/byron/dev/.claude add rules/mcp-strategy.md
git -C /home/byron/dev/.claude commit -S -m "feat(rules): add Snyk MCP Server as Tier 2 on-demand server to MCP strategy"
```

---

## Task 6: Create scripts/snyk-dep-reminder.sh

**Files:**
- Create: `~/.claude/scripts/snyk-dep-reminder.sh`

This is the PostToolUse hook script. Claude Code passes a JSON payload to stdin
containing `tool_name` and `tool_input`. For Edit and Write, `tool_input.file_path`
is the modified file. The script checks if that path is a dependency file and
prints a reminder if so.

The script must always exit 0. A non-zero exit would surface as a hook error and
interrupt the session.

- [ ] **Step 1: Write the script**

Create `/home/byron/dev/.claude/scripts/snyk-dep-reminder.sh` with this content:

```bash
#!/usr/bin/env bash
# PostToolUse hook: prints a Snyk reminder when a dependency file is modified.
# Reads Claude Code PostToolUse JSON payload from stdin.
# Always exits 0 to avoid interrupting the session.

python3 - <<'PYEOF'
import sys
import json
import re

try:
    payload = json.load(sys.stdin)
    file_path = payload.get("tool_input", {}).get("file_path", "")
    if re.search(r"(pyproject\.toml|requirements[^/]*\.txt|uv\.lock)$", file_path):
        print("")
        print("Snyk reminder: dependency file modified.")
        print("If SNYK_TOKEN is set, invoke snyk_test via the Snyk MCP Server before committing.")
        print("Setup instructions: ~/.claude/standards/snyk-mcp-setup.md")
except Exception:
    pass
sys.exit(0)
PYEOF
```

- [ ] **Step 2: Make the script executable**

```bash
chmod +x /home/byron/dev/.claude/scripts/snyk-dep-reminder.sh
```

- [ ] **Step 3: Smoke-test the script with a matching payload**

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"/home/user/project/pyproject.toml","content":"..."}}' \
  | bash /home/byron/dev/.claude/scripts/snyk-dep-reminder.sh
```

Expected output:
```text
Snyk reminder: dependency file modified.
If SNYK_TOKEN is set, invoke snyk_test via the Snyk MCP Server before committing.
Setup instructions: ~/.claude/standards/snyk-mcp-setup.md
```

- [ ] **Step 4: Smoke-test with a non-matching payload (should produce no output)**

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"/home/user/project/src/main.py","content":"..."}}' \
  | bash /home/byron/dev/.claude/scripts/snyk-dep-reminder.sh
echo "exit code: $?"
```

Expected: no reminder output, exit code 0.

- [ ] **Step 5: Smoke-test with empty stdin (should not crash)**

```bash
echo '{}' | bash /home/byron/dev/.claude/scripts/snyk-dep-reminder.sh
echo "exit code: $?"
```

Expected: no output, exit code 0.

- [ ] **Step 6: Stage and commit**

```bash
git -C /home/byron/dev/.claude add scripts/snyk-dep-reminder.sh
git -C /home/byron/dev/.claude commit -S -m "feat(scripts): add PostToolUse hook script for Snyk dependency reminder"
```

---

## Task 7: Wire PostToolUse hook in settings.json

**Files:**
- Modify: `~/.claude/settings.json` (PostToolUse array)

Add a new entry to the `PostToolUse` array. The existing array has two entries
(py310-compat-check and the hookify posttooluse handler). Add a third entry for
the Snyk reminder. The entry must use the same `matcher` + `hooks` structure as
the existing py310 entry.

- [ ] **Step 1: Read the current PostToolUse array**

```bash
python3 -c "
import json
with open('/home/byron/.claude/settings.json') as f:
    s = json.load(f)
print(json.dumps(s['hooks']['PostToolUse'], indent=2))
"
```

Confirm there are currently 2 entries and neither references `snyk-dep-reminder.sh`.

- [ ] **Step 2: Add the Snyk hook entry to settings.json**

Edit `/home/byron/.claude/settings.json`. In the `hooks.PostToolUse` array,
insert this new object as the SECOND item (after the py310 entry, before the
hookify entry):

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "bash $HOME/.claude/scripts/snyk-dep-reminder.sh",
      "timeout": 5
    }
  ]
}
```

The full `PostToolUse` array after the edit should look like:

```json
"PostToolUse": [
  {
    "matcher": "(Edit|Write)",
    "hooks": [
      {
        "type": "command",
        "command": "bash $HOME/.claude/scripts/py310-compat-check.sh"
      }
    ]
  },
  {
    "matcher": "Write|Edit",
    "hooks": [
      {
        "type": "command",
        "command": "bash $HOME/.claude/scripts/snyk-dep-reminder.sh",
        "timeout": 5
      }
    ]
  },
  {
    "hooks": [
      {
        "type": "command",
        "command": "CLAUDE_PLUGIN_ROOT=$HOME/dev/.claude/.submodules/anthropics-plugins/plugins/hookify python3 $HOME/dev/.claude/.submodules/anthropics-plugins/plugins/hookify/hooks/posttooluse.py",
        "timeout": 10
      }
    ]
  }
]
```

- [ ] **Step 3: Validate settings.json is valid JSON**

```bash
python3 -c "
import json
with open('/home/byron/.claude/settings.json') as f:
    json.load(f)
print('valid JSON')
"
```

Expected: `valid JSON`

- [ ] **Step 4: Confirm the new hook entry exists**

```bash
python3 -c "
import json
with open('/home/byron/.claude/settings.json') as f:
    s = json.load(f)
entries = s['hooks']['PostToolUse']
print(f'{len(entries)} PostToolUse entries')
for i, e in enumerate(entries):
    cmd = e.get('hooks', [{}])[0].get('command', '')
    print(f'  [{i}] {cmd[:80]}')
"
```

Expected: 3 entries, second one references `snyk-dep-reminder.sh`.

- [ ] **Step 5: Stage and commit**

`settings.json` is tracked at the root of `/home/byron/dev/.claude/`:

```bash
git -C /home/byron/dev/.claude add settings.json
git -C /home/byron/dev/.claude commit -S -m "feat(hooks): add PostToolUse hook for Snyk dependency file reminder"
```

---

## Task 8: Update MEMORY.md

**Files:**
- Modify: `~/.claude/projects/-home-byron-dev--claude/memory/MEMORY.md`

Add one line to the Memory Index pointing to the new setup standard.

- [ ] **Step 1: Confirm the file exists and check the last entry**

```bash
tail -5 /home/byron/.claude/projects/-home-byron-dev--claude/memory/MEMORY.md
```

- [ ] **Step 2: Append the new pointer line**

In `/home/byron/.claude/projects/-home-byron-dev--claude/memory/MEMORY.md`,
add this line at the end of the index (before any trailing newline):

```markdown
- [Snyk MCP setup](standards/snyk-mcp-setup.md): workstation setup for Snyk MCP Server; which tools to call and when; snyk_monitor must not be called automatically
```

- [ ] **Step 3: Verify the line was added**

```bash
grep "snyk" /home/byron/.claude/projects/-home-byron-dev--claude/memory/MEMORY.md
```

Expected: one hit with the new pointer.

- [ ] **Step 4: Stage and commit**

```bash
git -C /home/byron/dev/.claude add projects/-home-byron-dev--claude/memory/MEMORY.md
git -C /home/byron/dev/.claude commit -S -m "docs(memory): add Snyk MCP setup pointer to memory index"
```

---

## Task 9: Update global CLAUDE.md (LOW priority)

**Files:**
- Modify: `CLAUDE.md` (global, at `/home/byron/dev/.claude/CLAUDE.md`)

Add a single reference line in the "Core development standards" section that
points to the new Snyk standard. This is LOW priority and can be skipped if
the previous tasks are already merged.

- [ ] **Step 1: Find the Core development standards section**

```bash
grep -n "Core development standards\|standards/packages\|standards/container" \
  /home/byron/dev/.claude/CLAUDE.md | head -10
```

Note the line numbers. The existing cross-references block ends with a line like:
`> Approved package choices: see \`.claude/standards/packages.md\``

- [ ] **Step 2: Add the Snyk reference line**

After the existing cross-reference lines in the "Core development standards"
section (after the container-images line and before the closing of that block),
add:

```markdown
>
> Snyk MCP Server setup and tool invocation rules:
> see `.claude/standards/snyk-mcp-setup.md`
```

- [ ] **Step 3: Verify the addition**

```bash
grep -A 2 "snyk-mcp-setup" /home/byron/dev/.claude/CLAUDE.md
```

Expected: the new reference line appears.

- [ ] **Step 4: Stage and commit**

```bash
git -C /home/byron/dev/.claude add CLAUDE.md
git -C /home/byron/dev/.claude commit -S -m "docs(claude-md): reference Snyk MCP setup standard in core development standards"
```

---

## Task 10: Run pre-commit and final verification

**Files:** none created (verification only)

- [ ] **Step 1: Run pre-commit across all changed files**

```bash
cd /home/byron/dev/.claude && pre-commit run --all-files
```

If the `no-em-dash` hook fails, search the failing file for `--` patterns and
confirm they are all CLI flags, not prose em-dashes. Fix any actual em-dashes
before proceeding.

If markdownlint fails on the new files, check for:
- Missing blank lines around code blocks (MD031)
- Fenced code blocks without a language tag (MD040)
- Trailing spaces (MD009)

- [ ] **Step 2: Verify all five created/modified files exist**

```bash
ls -la \
  /home/byron/dev/.claude/standards/snyk-mcp-setup.md \
  /home/byron/dev/.claude/rules/snyk-mcp.md \
  /home/byron/dev/.claude/rules/pre-commit.md \
  /home/byron/dev/.claude/rules/mcp-strategy.md \
  /home/byron/dev/.claude/scripts/snyk-dep-reminder.sh
```

All five should appear.

- [ ] **Step 3: Verify settings.json is still valid JSON**

```bash
python3 -m json.tool /home/byron/.claude/settings.json > /dev/null && echo "valid"
```

- [ ] **Step 4: Verify no em-dashes crept in**

```bash
grep -rn $'\xe2\x80\x94' \
  /home/byron/dev/.claude/standards/snyk-mcp-setup.md \
  /home/byron/dev/.claude/rules/snyk-mcp.md \
  /home/byron/dev/.claude/rules/pre-commit.md \
  /home/byron/dev/.claude/rules/mcp-strategy.md \
  && echo "FAIL: em-dashes found" || echo "clean"
```

Expected: `clean`

- [ ] **Step 5: Check git log shows all expected commits on this branch**

```bash
git -C /home/byron/dev/.claude log --oneline main..HEAD
```

Expected: 6-8 commits (one per task above), all signed, all with conventional
commit prefixes.

- [ ] **Step 6: If pre-commit made auto-fixes in step 1, stage and commit them**

```bash
git -C /home/byron/dev/.claude diff --name-only
# If any files appear, stage and commit them:
git -C /home/byron/dev/.claude add -p
git -C /home/byron/dev/.claude commit -S -m "style: apply pre-commit auto-fixes to Snyk developer experience files"
```

---

## Key constraints (summary for the implementing agent)

- **No em-dashes** in any file. Use commas, colons, or restructure the sentence.
- **Signed commits**: every `git commit` must use `-S`.
- **Conventional commit prefixes**: `feat:`, `docs:`, `style:` etc.
- **snyk_monitor is never called automatically**: enforce this in every file that
  mentions Snyk tools.
- **Frontmatter format**: use `paths:` (plural, YAML list), NOT `path:` (singular string).
- **Hook script always exits 0**: a non-zero exit surfaces as an error in the session.
- **settings.json hook has no `condition:` field**: file matching happens inside
  the bash script via Python stdin parsing.
- **Snyk MCP Scan is pre-GA**: document the gap and a TODO; do not implement hooks.
- **Tier 2, not Tier 1**: Snyk MCP Server must not be added to the always-loaded
  `mcpServers` block.
