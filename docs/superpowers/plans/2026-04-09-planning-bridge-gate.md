---
schema_type: planning
title: "Planning Bridge Gate Implementation Plan"
status: draft
owner: core-maintainer
purpose: "Implementation plan for the PreToolUse hook that gates writing-plans until the project-planning bridge mode has generated ADR and Roadmap documents."
component: Development-Tools
source: "docs/superpowers/specs/"
tags:
  - automation
  - planning
  - tooling
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Intercept brainstorming's automatic `writing-plans` invocation with a PreToolUse hook that redirects Claude to run `project-planning` in bridge mode first, ensuring ADR and Roadmap are generated from the approved spec before implementation planning begins.

**Architecture:** A bash hook script checks three conditions on every Skill tool call targeting `writing-plans` — spec exists, no ADR yet, no Roadmap yet — and exits 2 (blocking) with a redirect message when all three are true. The `project-planning` skill gains two modes: `entry` (PVS generation before brainstorming) and `bridge` (ADR + Roadmap generation after spec approval). Bridge mode is idempotent, skipping documents that already exist.

**Tech Stack:** Bash (hook script), JSON/jq (hook input parsing), Markdown (skill update)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `~/.claude/scripts/planning-bridge-gate.sh` | Create | Hook that intercepts writing-plans and enforces bridge mode |
| `~/.claude/settings.json` | Modify | Wire hook to PreToolUse on Skill tool matcher |
| `.claude/skills/project-planning/SKILL.md` | Modify | Add entry and bridge mode definitions |

---

### Task 1: Write the planning-bridge-gate hook script

**Files:**
- Create: `/home/byron/.claude/scripts/planning-bridge-gate.sh`

- [ ] **Step 1: Write the failing test**

```bash
# Test: hook passes through non-writing-plans skill calls
echo '{"tool_name":"Skill","tool_input":{"skill":"brainstorming"}}' \
  | bash /home/byron/.claude/scripts/planning-bridge-gate.sh
echo "Exit: $?"
# Expected: Exit: 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bash /home/byron/.claude/scripts/planning-bridge-gate.sh <<< '{"tool_name":"Skill","tool_input":{"skill":"brainstorming"}}'
echo "Exit: $?"
```

Expected: FAIL — script does not exist yet.

- [ ] **Step 3: Write the script**

```bash
cat > /home/byron/.claude/scripts/planning-bridge-gate.sh << 'SCRIPT'
#!/usr/bin/env bash
# =============================================================================
# Planning Bridge Gate — PreToolUse Hook
# =============================================================================
# Intercepts Skill tool calls targeting "writing-plans". When brainstorming
# has produced a spec but bridge mode has not yet run (no ADR, no Roadmap),
# blocks the call with exit 2 and directs Claude to run project-planning
# in bridge mode first.
#
# Exit codes:
#   0 — allow tool call to proceed
#   2 — block tool call; stdout message fed back to Claude
# =============================================================================

set -euo pipefail

LOG_FILE="${HOME}/.claude/logs/planning-bridge-gate.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# Read JSON context from stdin
CONTEXT=$(cat)

if [[ -z "$CONTEXT" ]]; then
    exit 0
fi

# Extract skill name from tool input
SKILL=$(echo "$CONTEXT" | jq -r '.tool_input.skill // empty' 2>/dev/null)

# Only act on writing-plans invocations
if [[ "$SKILL" != "writing-plans" ]]; then
    exit 0
fi

# Resolve project working directory
# Claude Code sets PWD to the project root when running hooks
PROJECT_DIR="${PWD}"

# Condition 1: a brainstorming spec exists
SPEC_FILE=$(find "${PROJECT_DIR}/docs/superpowers/specs" -name "*.md" 2>/dev/null | sort | tail -1)

if [[ -z "$SPEC_FILE" ]]; then
    # No spec — brainstorming hasn't run; let writing-plans proceed normally
    log "No spec found, passing through writing-plans"
    exit 0
fi

# Condition 2: no ADR has been generated yet
ADR_FILE=$(find "${PROJECT_DIR}/docs/planning/adr" -name "*.md" 2>/dev/null | head -1)

# Condition 3: roadmap does not exist yet
ROADMAP="${PROJECT_DIR}/docs/planning/roadmap.md"

if [[ -z "$ADR_FILE" ]] && [[ ! -f "$ROADMAP" ]]; then
    log "Bridge mode required: spec=${SPEC_FILE}, no ADR, no roadmap"
    echo "Bridge mode required: a brainstorming spec exists at '${SPEC_FILE}' but no ADR or Roadmap have been generated yet. Invoke the project-planning skill in bridge mode first (run: /project-planning bridge), then retry writing-plans."
    exit 2
fi

# ADR or Roadmap already exists — bridge has run, allow writing-plans
log "Bridge already complete, passing through writing-plans"
exit 0
SCRIPT
chmod +x /home/byron/.claude/scripts/planning-bridge-gate.sh
```

- [ ] **Step 4: Run the pass-through test**

```bash
echo '{"tool_name":"Skill","tool_input":{"skill":"brainstorming"}}' \
  | bash /home/byron/.claude/scripts/planning-bridge-gate.sh
echo "Exit: $?"
```

Expected: Exit: 0 (passes through non-writing-plans calls)

- [ ] **Step 5: Run the no-spec pass-through test**

```bash
# writing-plans with no spec → should pass through
cd /tmp && echo '{"tool_name":"Skill","tool_input":{"skill":"writing-plans"}}' \
  | bash /home/byron/.claude/scripts/planning-bridge-gate.sh
echo "Exit: $?"
```

Expected: Exit: 0 (no spec in /tmp/docs/superpowers/specs/)

- [ ] **Step 6: Run the bridge-required block test**

```bash
# Set up fixture: spec exists, no ADR, no roadmap
FIXTURE=$(mktemp -d)
mkdir -p "$FIXTURE/docs/superpowers/specs"
mkdir -p "$FIXTURE/docs/planning/adr"
echo "# Test Spec" > "$FIXTURE/docs/superpowers/specs/2026-04-09-test-design.md"

cd "$FIXTURE" && echo '{"tool_name":"Skill","tool_input":{"skill":"writing-plans"}}' \
  | bash /home/byron/.claude/scripts/planning-bridge-gate.sh
echo "Exit: $?"

rm -rf "$FIXTURE"
```

Expected: message printed to stdout + Exit: 2

- [ ] **Step 7: Run the already-bridged pass-through test**

```bash
# Set up fixture: spec + ADR exists
FIXTURE=$(mktemp -d)
mkdir -p "$FIXTURE/docs/superpowers/specs"
mkdir -p "$FIXTURE/docs/planning/adr"
echo "# Test Spec" > "$FIXTURE/docs/superpowers/specs/2026-04-09-test-design.md"
echo "# ADR-001" > "$FIXTURE/docs/planning/adr/adr-001-database.md"

cd "$FIXTURE" && echo '{"tool_name":"Skill","tool_input":{"skill":"writing-plans"}}' \
  | bash /home/byron/.claude/scripts/planning-bridge-gate.sh
echo "Exit: $?"

rm -rf "$FIXTURE"
```

Expected: Exit: 0 (ADR exists, bridge already ran)

- [ ] **Step 8: Commit**

```bash
git -C /home/byron/dev/.claude add /home/byron/.claude/scripts/planning-bridge-gate.sh
git -C /home/byron/dev/.claude commit -m "feat: add planning-bridge-gate PreToolUse hook script"
```

---

### Task 2: Wire hook into settings.json

**Files:**
- Modify: `/home/byron/.claude/settings.json`

- [ ] **Step 1: Write a test to verify the hook section is absent**

```bash
jq '.hooks.PreToolUse // empty' /home/byron/.claude/settings.json
```

Expected: empty output (no hooks section yet)

- [ ] **Step 2: Run test to verify current state**

```bash
jq '.hooks // "NO_HOOKS"' /home/byron/.claude/settings.json
```

Expected: `"NO_HOOKS"` — confirms no hooks key exists.

- [ ] **Step 3: Add the hooks section to settings.json**

Edit `/home/byron/.claude/settings.json`. Add after the `"model": "sonnet"` line:

```json
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "bash $HOME/.claude/scripts/planning-bridge-gate.sh"
          }
        ]
      }
    ]
  }
```

The full updated file (only the closing section changes):
```json
  "effortLevel": "high",
  "model": "sonnet",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "bash $HOME/.claude/scripts/planning-bridge-gate.sh"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 4: Verify JSON is valid and hook key is present**

```bash
jq '.hooks.PreToolUse[0].hooks[0].command' /home/byron/.claude/settings.json
```

Expected: `"bash $HOME/.claude/scripts/planning-bridge-gate.sh"`

- [ ] **Step 5: Verify full file parses without error**

```bash
jq empty /home/byron/.claude/settings.json && echo "Valid JSON"
```

Expected: `Valid JSON`

- [ ] **Step 6: Commit**

```bash
git -C /home/byron/dev/.claude add /home/byron/.claude/settings.json
git -C /home/byron/dev/.claude commit -m "feat: wire planning-bridge-gate hook to PreToolUse on Skill tool"
```

---

### Task 3: Add entry and bridge modes to project-planning SKILL.md

**Files:**
- Modify: `/home/byron/dev/.claude/.claude/skills/project-planning/SKILL.md`

- [ ] **Step 1: Verify the current SKILL.md opens with its frontmatter**

```bash
head -10 /home/byron/dev/.claude/.claude/skills/project-planning/SKILL.md
```

Expected: frontmatter block with `name: project-planning`

- [ ] **Step 2: Add a Modes section after the Overview block**

Add the following after the `## When to Use This Skill` section and before `## Output Documents`:

```markdown
## Modes

This skill operates in two modes depending on where you are in the planning flow.

### Entry Mode (`/project-planning entry`)

**When to use:** At the very start of a new project, before brainstorming.

**What it does:**
1. Collect the project description from the user
2. Read `pyproject.toml` and existing project structure for constraints
3. Generate `docs/planning/project-vision.md` (PVS only — no ADR, Tech Spec, or Roadmap yet)
4. Run `mcp__pal__consensus` review on the PVS (see review prompt below); revise until READY
5. Commit the PVS to version control
6. Tell Claude: "PVS saved to `docs/planning/project-vision.md`. Invoke the brainstorming skill now — it will read the PVS as existing project context in step 1 and skip re-discovering scope."

**Output:** `docs/planning/project-vision.md` only.

---

### Bridge Mode (`/project-planning bridge`)

**When to use:** After brainstorming has completed and the user has approved the spec, before writing-plans. The planning-bridge-gate hook will redirect Claude here automatically.

**What it does (idempotent — safe to run twice):**

1. **Find the approved spec:** Locate the most recent file in `docs/superpowers/specs/*.md`
2. **Generate ADR** (skip if `docs/planning/adr/adr-001-*.md` already exists):
   - Read the "Proposed 2-3 approaches" section from the spec
   - Formalize the chosen approach as `docs/planning/adr/adr-001-<decision-slug>.md`
   - Use template at `templates/adr-template.md`
   - Run `mcp__pal__consensus` review; revise until READY
3. **Generate Roadmap** (skip if `docs/planning/roadmap.md` already exists):
   - Read the approved spec's architecture and component sections
   - Build a phased roadmap aligned to spec deliverables
   - Save to `docs/planning/roadmap.md`
   - Use template at `templates/roadmap-template.md`
   - Run `mcp__pal__consensus` review; revise until READY
4. **Commit** both documents
5. Tell Claude: "Bridge complete. ADR and Roadmap are in `docs/planning/`. Proceed to writing-plans."

**Skipping already-complete documents:**
- If `docs/planning/adr/adr-001-*.md` exists: log "ADR already exists, skipping" and move to Roadmap step
- If `docs/planning/roadmap.md` exists: log "Roadmap already exists, skipping" and move to commit step
- If both exist: log "Bridge already complete" and immediately tell Claude to proceed to writing-plans

**Output:** `docs/planning/adr/adr-001-*.md` and `docs/planning/roadmap.md`

---

### Default Mode (no argument)

Generates all four documents sequentially as documented in the Generation Process section below. Use for projects that are not using the brainstorming → bridge → writing-plans flow.
```

- [ ] **Step 3: Verify the edit compiles (no YAML frontmatter broken)**

```bash
head -20 /home/byron/dev/.claude/.claude/skills/project-planning/SKILL.md
```

Expected: frontmatter intact, `## Modes` section visible below `## When to Use This Skill`

- [ ] **Step 4: Update the `## When to Use This Skill` section to reference the modes**

Replace the existing `## When to Use This Skill` content with:

```markdown
## When to Use This Skill

| Invocation | When |
|---|---|
| `/project-planning entry` | Starting a new project — generates PVS and hands off to brainstorming |
| `/project-planning bridge` | After brainstorming spec is approved — generates ADR + Roadmap before writing-plans |
| `/project-planning` | Default: generates all four documents for projects not using the brainstorming flow |
```

- [ ] **Step 5: Verify the full skill file reads cleanly**

```bash
wc -l /home/byron/dev/.claude/.claude/skills/project-planning/SKILL.md
grep -n "## " /home/byron/dev/.claude/.claude/skills/project-planning/SKILL.md
```

Expected: all section headings visible, no duplicates

- [ ] **Step 6: Commit**

```bash
git -C /home/byron/dev/.claude add .claude/skills/project-planning/SKILL.md
git -C /home/byron/dev/.claude commit -m "feat: add entry and bridge modes to project-planning skill"
```

---

### Task 4: Smoke test the full integration

**Files:** No changes — read-only verification.

- [ ] **Step 1: Confirm hook script is executable and parseable**

```bash
bash -n /home/byron/.claude/scripts/planning-bridge-gate.sh && echo "Syntax OK"
```

Expected: `Syntax OK`

- [ ] **Step 2: Confirm settings.json hook is wired correctly**

```bash
jq '.hooks.PreToolUse[] | select(.matcher == "Skill") | .hooks[].command' \
  /home/byron/.claude/settings.json
```

Expected: `"bash $HOME/.claude/scripts/planning-bridge-gate.sh"`

- [ ] **Step 3: Run the full fixture test sequence**

```bash
FIXTURE=$(mktemp -d)
mkdir -p "$FIXTURE/docs/superpowers/specs" "$FIXTURE/docs/planning/adr"
echo "# Approved Spec" > "$FIXTURE/docs/superpowers/specs/2026-04-09-myapp-design.md"

# Should block (no ADR, no roadmap)
RESULT=$(cd "$FIXTURE" && echo '{"tool_name":"Skill","tool_input":{"skill":"writing-plans"}}' \
  | bash /home/byron/.claude/scripts/planning-bridge-gate.sh; echo "exit:$?")
echo "$RESULT" | grep -q "Bridge mode required" && echo "BLOCK: pass" || echo "BLOCK: FAIL"
echo "$RESULT" | grep -q "exit:2" && echo "EXIT2: pass" || echo "EXIT2: FAIL"

# Add ADR — should now pass through
echo "# ADR" > "$FIXTURE/docs/planning/adr/adr-001-db.md"
cd "$FIXTURE" && echo '{"tool_name":"Skill","tool_input":{"skill":"writing-plans"}}' \
  | bash /home/byron/.claude/scripts/planning-bridge-gate.sh
echo "Passthrough exit: $?"

rm -rf "$FIXTURE"
```

Expected:
```
BLOCK: pass
EXIT2: pass
Passthrough exit: 0
```

- [ ] **Step 4: Confirm SKILL.md has all three modes documented**

```bash
grep -A2 "## Modes" /home/byron/dev/.claude/.claude/skills/project-planning/SKILL.md
```

Expected: Entry Mode, Bridge Mode, and Default Mode all present

- [ ] **Step 5: Final commit for plan document itself**

```bash
git -C /home/byron/dev/.claude add docs/superpowers/plans/2026-04-09-planning-bridge-gate.md
git -C /home/byron/dev/.claude commit -m "docs: add planning bridge gate implementation plan"
```
