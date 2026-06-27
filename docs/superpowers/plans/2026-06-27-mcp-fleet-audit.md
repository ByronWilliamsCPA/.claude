---
schema_type: planning
title: "MCP Fleet-Wide Audit Implementation Plan"
status: draft
owner: core-maintainer
purpose: "Ensure all MCP servers connect reliably across all active dev repos, resolving the GITHUB_PERSONAL_ACCESS_TOKEN gap and the User vs Project count discrepancy."
component: Development-Tools
source: "docs/superpowers/plans/2026-06-27-mcp-fleet-audit.md"
tags:
  - mcp_strategy
  - tooling
  - infrastructure
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure all MCP servers connect reliably in every active dev repo, starting with the confirmed GITHUB_PERSONAL_ACCESS_TOKEN gap and the unexplained "User (1) vs Project (3)" discrepancy seen in CYO_Adventure vs this repo.

**Architecture:** Fix the confirmed environment gap first, then diagnose why global MCP servers appear differently across projects, then write a validation script that can be re-run any time a new repo is cloned or a server is added to the fleet.

**Tech Stack:** Bash, Claude Code settings.json, Docker (github/sonarqube MCP servers), npx (context7), Python (zen/pal server)

---

## Background / Context

Two screenshots surfaced this issue:

| Repo | MCP Panel Shows |
|------|----------------|
| `~/.claude` (this repo) | Project (3): context7, pal, sonarqube |
| `CYO_Adventure` | User (1): pal only |

Global `~/.claude/settings.json` defines 5 MCP servers: zen (shows as pal), context7, github, sonarqube, sonarqube-williaby.

**Confirmed root cause:** `GITHUB_PERSONAL_ACCESS_TOKEN` is not set in `.bashrc`: the github MCP server silently fails to start.

**Suspected root cause for the "User (1)" count:** Servers that fail to start never appear in the panel at all (no "Failed" indicator). With github failing and sonarqube/context7 possibly slow to connect, only pal (the fastest-starting server) appears under "User" in CYO_Adventure.

**Key settings in `~/.claude/settings.json`:**
- `enableAllProjectMcpServers: false`: project-level mcpServers blocks do NOT auto-enable; servers must be in global settings or explicitly listed.
- `enabledMcpjsonServers: [zen, context7, github, sonarqube, sonarqube-williaby, playwright, sentry, mermaid, docker, uml-mcp-server]`: the 5 additional Tier 2/3 servers (playwright, sentry, mermaid, docker, uml-mcp-server) are defined in `mcp/*.json` files, not in `mcpServers` directly.

---

## File Structure

```
~/.claude/
  settings.json                          # MODIFY: nothing yet; after audit may add env vars
~/.bashrc                                # MODIFY: add GITHUB_PERSONAL_ACCESS_TOKEN
~/dev/.claude/
  scripts/
    validate-mcp-connections.sh          # CREATE: per-repo validation script
  docs/
    reference/
      mcp-fleet-status.md               # CREATE: living audit record of server health
```

---

## Task 1: Add GITHUB_PERSONAL_ACCESS_TOKEN

**Files:**
- Modify: `~/.bashrc` (near line 128, after SONARQUBE_TOKEN)

**Prerequisite:** Create a GitHub Classic PAT at https://github.com/settings/tokens with scopes: `repo`, `read:org`, `read:user`. The token will look like `ghp_...`.

- [ ] **Step 1: Add the token to .bashrc**

Open `~/.bashrc` and add after the `SONARQUBE_TOKEN` line (currently line 128):

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_YOUR_TOKEN_HERE"
```

- [ ] **Step 2: Source and verify the variable is set**

```bash
source ~/.bashrc
echo "Token set: ${GITHUB_PERSONAL_ACCESS_TOKEN:0:4}..."
```

Expected output: `Token set: ghp_...`

If output is blank, the export did not take effect: verify the line was added to the correct `.bashrc` (not `.bash_profile`).

- [ ] **Step 3: Verify the token authenticates with GitHub**

```bash
curl -s -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  https://api.github.com/user | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Authenticated as: {d[\"login\"]}')"
```

Expected: `Authenticated as: ByronWilliamsCPA` (or your GitHub username).

If you get `{"message":"Bad credentials"}`, regenerate the token.

- [ ] **Step 4: Commit nothing: this is an env var change only, no code changed**

Restart your Claude Code session (close and reopen VSCode or the terminal) to pick up the new env var.

---

## Task 2: Diagnose the "User (1)" Panel Discrepancy

**Files:**
- Read: `~/.claude/settings.json` (already read: no changes)
- Read: `~/dev/CYO_Adventure/.claude/settings.json` (no changes)

**Goal:** Confirm whether the missing servers in CYO_Adventure are a PAT issue, timing issue, or a settings scoping bug.

- [ ] **Step 1: Open a Claude Code session in CYO_Adventure with the new PAT set**

In a terminal:

```bash
cd ~/dev/CYO_Adventure
source ~/.bashrc
echo $GITHUB_PERSONAL_ACCESS_TOKEN | head -c 8  # confirm var is set in this shell
code .  # or relaunch VSCode from this shell
```

- [ ] **Step 2: After the session opens, wait 30 seconds then open MCP Servers panel**

Expected: "User (4 or 5)" showing pal, context7, github, sonarqube, sonarqube-williaby.

If still "User (1)":
  - This is NOT just a PAT issue.
  - Proceed to Step 3.

If "User (4+)": **Task complete**: PAT was the root cause. Skip to Task 3.

- [ ] **Step 3: If servers still missing, check Claude Code logs**

```bash
# Claude Code logs location on WSL2
ls ~/.claude/logs/ 2>/dev/null || ls /tmp/claude-*/logs/ 2>/dev/null
```

Look for lines like `MCP server "context7" failed to start` or `ENOENT npx`.

- [ ] **Step 4: If npx not found, make it explicit in settings.json**

If logs show `ENOENT npx`, the VSCode extension's PATH doesn't include `~/.npm-global/bin`. Fix by making the npx path absolute in `~/.claude/settings.json`:

```json
"context7": {
  "command": "/home/byron/.npm-global/bin/npx",
  "args": ["-y", "@upstash/context7-mcp"],
  "env": {}
}
```

Run: `which npx` to confirm the path before editing.

- [ ] **Step 5: Commit if settings.json was changed**

```bash
cd ~/dev/.claude
git add .claude/settings.json  # note: ~/.claude symlinks here
git commit -S -m "fix(mcp): use absolute npx path for context7 server"
```

---

## Task 3: Create MCP Connection Validation Script

**Files:**
- Create: `~/dev/.claude/scripts/validate-mcp-connections.sh`

This script can be run from any project directory to check which MCP servers would connect.

- [ ] **Step 1: Create the script**

```bash
cat > ~/dev/.claude/scripts/validate-mcp-connections.sh << 'EOF'
#!/usr/bin/env bash
# Validates MCP server connectivity from any project directory.
# Usage: bash ~/.claude/scripts/validate-mcp-connections.sh

set -euo pipefail

PASS=0
FAIL=0
WARN=0

check() {
  local name="$1"
  local result="$2"
  local detail="$3"
  if [[ "$result" == "ok" ]]; then
    echo "  [OK]   $name: $detail"
    ((PASS++))
  elif [[ "$result" == "warn" ]]; then
    echo "  [WARN] $name: $detail"
    ((WARN++))
  else
    echo "  [FAIL] $name: $detail"
    ((FAIL++))
  fi
}

echo "=== MCP Connection Validation ==="
echo ""

echo "-- Environment --"
if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
  GH_USER=$(curl -sf -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
    https://api.github.com/user 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('login','unknown'))" 2>/dev/null || echo "error")
  if [[ "$GH_USER" == "error" ]]; then
    check "GITHUB_PERSONAL_ACCESS_TOKEN" "fail" "set but GitHub auth failed: token may be expired"
  else
    check "GITHUB_PERSONAL_ACCESS_TOKEN" "ok" "authenticates as $GH_USER"
  fi
else
  check "GITHUB_PERSONAL_ACCESS_TOKEN" "fail" "NOT SET: add to ~/.bashrc"
fi

if [[ -n "${SONARQUBE_TOKEN:-}" ]]; then
  check "SONARQUBE_TOKEN" "ok" "set (${#SONARQUBE_TOKEN} chars)"
else
  check "SONARQUBE_TOKEN" "fail" "NOT SET: add to ~/.bashrc"
fi

echo ""
echo "-- Servers --"

# zen/pal: check if python and server.py exist
ZEN_PY="/home/byron/dev/zen-mcp-server/.pal_venv/bin/python"
ZEN_SRV="/home/byron/dev/zen-mcp-server/server.py"
if [[ -x "$ZEN_PY" && -f "$ZEN_SRV" ]]; then
  check "zen (pal)" "ok" "venv and server.py present"
else
  check "zen (pal)" "fail" "missing venv or server.py at $ZEN_PY / $ZEN_SRV"
fi

# context7: check npx reachable
NPX_PATH=$(which npx 2>/dev/null || echo "")
if [[ -n "$NPX_PATH" ]]; then
  check "context7" "ok" "npx found at $NPX_PATH"
else
  check "context7" "fail" "npx not in PATH: VSCode extension may need absolute path"
fi

# github: check docker running
if docker info &>/dev/null; then
  if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
    check "github" "ok" "docker running and PAT set"
  else
    check "github" "fail" "docker running but GITHUB_PERSONAL_ACCESS_TOKEN not set"
  fi
else
  check "github" "fail" "docker not running"
fi

# sonarqube: check HTTP endpoints
for port in 8090 8091; do
  name="sonarqube"
  [[ "$port" == "8091" ]] && name="sonarqube-williaby"
  HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${SONARQUBE_TOKEN:-}" \
    "http://localhost:$port/mcp" 2>/dev/null || echo "000")
  if [[ "$HTTP_CODE" == "405" || "$HTTP_CODE" == "200" ]]; then
    check "$name" "ok" "port $port responding (HTTP $HTTP_CODE)"
  elif [[ "$HTTP_CODE" == "000" ]]; then
    check "$name" "fail" "port $port unreachable: is the Docker container running?"
  else
    check "$name" "warn" "port $port returned HTTP $HTTP_CODE"
  fi
done

echo ""
echo "=== Summary: $PASS ok, $WARN warn, $FAIL fail ==="
[[ $FAIL -gt 0 ]] && exit 1 || exit 0
EOF
chmod +x ~/dev/.claude/scripts/validate-mcp-connections.sh
```

- [ ] **Step 2: Run the script to confirm it works**

```bash
bash ~/dev/.claude/scripts/validate-mcp-connections.sh
```

Expected (after Task 1 complete):
```
=== MCP Connection Validation ===

-- Environment --
  [OK]   GITHUB_PERSONAL_ACCESS_TOKEN: authenticates as ByronWilliamsCPA
  [OK]   SONARQUBE_TOKEN: set (40 chars)

-- Servers --
  [OK]   zen (pal): venv and server.py present
  [OK]   context7: npx found at /home/byron/.npm-global/bin/npx
  [OK]   github: docker running and PAT set
  [OK]   sonarqube: port 8090 responding (HTTP 405)
  [OK]   sonarqube-williaby: port 8091 responding (HTTP 405)

=== Summary: 7 ok, 0 warn, 0 fail ===
```

- [ ] **Step 3: Commit the script**

```bash
cd ~/dev/.claude
git add scripts/validate-mcp-connections.sh
git commit -S -m "feat(scripts): add MCP connection validation script"
```

---

## Task 4: Audit All Local Dev Repos for Conflicting MCP Config

**Files:**
- Create: `~/dev/.claude/docs/reference/mcp-fleet-status.md`

**Goal:** Check all repos under `~/dev/` for any project-level settings that might conflict with or override global MCP config.

- [ ] **Step 1: Find all project settings.json files**

```bash
find ~/dev -maxdepth 3 -name "settings.json" -path "*/.claude/*" \
  ! -path "*/dev/.claude/.claude/*" \
  | sort
```

- [ ] **Step 2: Check which have mcpServers blocks**

```bash
find ~/dev -maxdepth 3 -name "settings.json" -path "*/.claude/*" \
  ! -path "*/dev/.claude/.claude/*" \
  | xargs grep -l "mcpServers" 2>/dev/null \
  || echo "No project-level mcpServers found"
```

Expected: `No project-level mcpServers found` (discovery confirmed zero project-level overrides).

- [ ] **Step 3: Check for any settings.json that has `enableAllProjectMcpServers: true`**

```bash
find ~/dev -maxdepth 3 -name "settings.json" -path "*/.claude/*" \
  | xargs grep -l "enableAllProjectMcpServers" 2>/dev/null \
  || echo "No project overrides for enableAllProjectMcpServers"
```

- [ ] **Step 4: Write the fleet status doc**

```bash
cat > ~/dev/.claude/docs/reference/mcp-fleet-status.md << 'EOF'
# MCP Fleet Status

> Last audited: 2026-06-27

## Global Config (`~/.claude/settings.json`)

| Server | Type | Status |
|--------|------|--------|
| zen (pal) | command (Python) | Tier 1: always loaded |
| context7 | command (npx) | Tier 1: always loaded |
| github | command (docker) | Tier 1: requires GITHUB_PERSONAL_ACCESS_TOKEN |
| sonarqube | url (localhost:8090) | Tier 1: requires SONARQUBE_TOKEN + container running |
| sonarqube-williaby | url (localhost:8091) | Tier 1: requires SONARQUBE_TOKEN + container running |

Additional Tier 2/3 servers (defined in `mcp/*.json`, listed in `enabledMcpjsonServers`):
playwright, sentry, mermaid, docker, uml-mcp-server

## Required Environment Variables

| Variable | Where Set | Purpose |
|----------|-----------|---------|
| SONARQUBE_TOKEN | `~/.bashrc` line 128 | sonarqube + sonarqube-williaby auth |
| GITHUB_PERSONAL_ACCESS_TOKEN | `~/.bashrc` (added 2026-06-27) | github MCP server auth |

## Fleet Project Override Status

As of 2026-06-27: **0 of 45 repos** have project-level `mcpServers` blocks.
All projects inherit from global config. This is intentional: avoid duplication.

## Key Setting

`enableAllProjectMcpServers: false`: prevents project-level mcpServers from
auto-enabling without explicit listing. Since no project defines mcpServers, this
has no current effect but is the correct posture.

## Validation

Run any time a server seems missing:
```bash
bash ~/.claude/scripts/validate-mcp-connections.sh
```

## When to Add Project-Level mcpServers

Only add a project-level mcpServers block when:
1. A project needs a server the global config doesn't have (e.g. a project-specific postgres instance)
2. A server needs project-specific env vars (e.g. different SENTRY_ORG per project)

Do NOT duplicate the global Tier 1 servers in project settings: that creates drift.
EOF
```

- [ ] **Step 5: Commit the status doc**

```bash
cd ~/dev/.claude
git add docs/reference/mcp-fleet-status.md
git commit -S -m "docs(mcp): add fleet MCP status reference doc"
```

---

## Task 5: Add `validate-mcp-connections` to Bash Permissions

The validation script needs Bash permission to run without prompts in Claude Code sessions.

- [ ] **Step 1: Check current Bash allow rules in `~/.claude/settings.json`**

```bash
python3 -c "
import json
with open('/home/byron/.claude/settings.json') as f:
    d = json.load(f)
allows = d.get('permissions', {}).get('allow', [])
[print(a) for a in allows if 'validate' in a.lower() or 'scripts' in a.lower()]
"
```

- [ ] **Step 2: If not present, add the allow rule**

Open `~/.claude/settings.json` and add to the `permissions.allow` array:

```json
"Bash(bash ~/.claude/scripts/validate-mcp-connections.sh*)"
```

- [ ] **Step 3: Commit if changed**

```bash
cd ~/dev/.claude
git add .  # settings.json changes
git commit -S -m "chore(settings): allow validate-mcp-connections script"
```

---

## Self-Review

**1. Spec coverage:**
- Fix GITHUB_PERSONAL_ACCESS_TOKEN: Task 1 ✓
- Diagnose User(1) vs Project(3): Task 2 ✓
- Validation script: Task 3 ✓
- Fleet audit for conflicting config: Task 4 ✓
- Permission wiring: Task 5 ✓

**2. Placeholder scan:** No TBDs or "add appropriate X" patterns found.

**3. Type consistency:** All bash scripts use consistent variable names throughout.

**4. Shell command environment:** All commands are self-contained. The validation script uses `source ~/.bashrc`-independent env vars (they must be set before the script runs, which is tested explicitly).

**5. Capability probe:** Task 1 Step 3 probes the GitHub token before any downstream work depends on it. Task 4 Step 2 probes for any conflicting project config before writing the status doc.

---

## Notes

- The `sonarqube-williaby` server sometimes fails to register tools even when healthy (see memory: `reference_sonarcloud_mcp.md`). The validation script checks HTTP reachability only, not tool registration. If tools are absent after the container shows healthy, fall back to the SonarCloud REST API directly.
- The github MCP server runs a Docker container on every session start: this is slow (~5-10s). If it shows as missing in the panel, wait 15 seconds before diagnosing further.
- Do not add `mcpServers` blocks to individual project settings.json files for the global Tier 1 servers. The global config is the single source of truth; duplication causes drift when server paths or args change.
