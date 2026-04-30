# Task Observer Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the rebelytics/one-skill-to-rule-them-all Task Observer meta-skill into the ~/.claude skills library as a thin adaptation that silently logs improvement opportunities during work sessions and applies them on a scheduled review cycle.

**Architecture:** Upstream SKILL.md tracked as a git submodule at `.submodules/one-skill-to-rule-them-all/`; a patch script transforms it into `~/.claude/skills/task-observer/SKILL.md` with exactly three sed/awk transformations. Activation uses two layers: a CLAUDE.md structural trigger (compaction-resilient) plus a SessionStart hook that generates a skills manifest file, replacing Cowork's `<available_skills>` system prompt injection. A CronCreate-based agent runs Monday/Wednesday/Friday to apply non-escalated observations.

**Tech Stack:** Bash (patch script, manifest generator, hooks), git submodules, sed/awk, Claude Code settings.json hooks, CLAUDE.md structural triggers, CronCreate scheduled agents.

---

## Task 1: Add Upstream Git Submodule

**Files:**
- Modify: `.gitmodules` (via git command)
- Create: `.submodules/one-skill-to-rule-them-all/` (via git command)

- [ ] **Step 1: Verify submodule does not yet exist**

```bash
ls .submodules/
```

Expected: `anthropics-plugins  anthropics-skills  image-generation  reference-library  superpowers` (no `one-skill-to-rule-them-all`)

- [ ] **Step 2: Add the submodule**

```bash
git submodule add https://github.com/rebelytics/one-skill-to-rule-them-all.git .submodules/one-skill-to-rule-them-all
```

Expected: Clones the repo and outputs something like:
```
Cloning into '/home/byron/dev/.claude/.submodules/one-skill-to-rule-them-all'...
```

- [ ] **Step 3: Verify .gitmodules was updated correctly**

```bash
grep -A 2 "one-skill-to-rule-them-all" .gitmodules
```

Expected:
```
[submodule ".submodules/one-skill-to-rule-them-all"]
	path = .submodules/one-skill-to-rule-them-all
	url = https://github.com/rebelytics/one-skill-to-rule-them-all.git
```

- [ ] **Step 4: Verify upstream SKILL.md is present**

```bash
ls .submodules/one-skill-to-rule-them-all/
```

Expected: Should include `SKILL.md`.

- [ ] **Step 5: Find the exact title of the section to strip (Patch 3)**

```bash
grep "^## " .submodules/one-skill-to-rule-them-all/SKILL.md
```

Expected: A list of section headings. Note the exact heading for the "Without Persistent Storage" or "handoff doc mode" section. You will use this exact string in Task 3 when writing the awk pattern.

- [ ] **Step 6: Verify CC BY 4.0 attribution block is present**

```bash
grep -n "CC BY\|rebelytics\|Eoghan" .submodules/one-skill-to-rule-them-all/SKILL.md
```

Expected: Lines showing attribution to Eoghan Henn / rebelytics.com. Record these line numbers -- Patch 3 must not touch them.

- [ ] **Step 7: Commit**

```bash
git add .gitmodules .submodules/one-skill-to-rule-them-all
git commit -m "chore: add one-skill-to-rule-them-all as git submodule"
```

Expected: Clean commit. If pre-commit hooks fail on the submodule contents, add `.submodules/` to any per-tool ignore list rather than bypassing the hook.

---

## Task 2: Update .gitignore for Runtime Data Directories

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Verify the directories do not yet exist (nothing to accidentally track)**

```bash
ls skill-observations 2>&1; ls skill-updates 2>&1
```

Expected: `ls: cannot access 'skill-observations': No such file or directory` for both.

- [ ] **Step 2: Add entries to .gitignore**

Append at the end of `.gitignore`:

```
# Task Observer runtime data (gitignored; populated at runtime, never committed)
skill-observations/
skill-updates/
```

- [ ] **Step 3: Verify git will ignore the new directories**

```bash
git check-ignore -v skill-observations skill-updates
```

Expected:
```
.gitignore:NNN:skill-observations/	skill-observations
.gitignore:NNN:skill-updates/	skill-updates
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore skill-observations and skill-updates runtime dirs"
```

---

## Task 3: Create the Patch Script

**Files:**
- Create: `scripts/apply-task-observer-patches.sh`

- [ ] **Step 1: Verify the script does not yet exist**

```bash
ls scripts/apply-task-observer-patches.sh 2>&1
```

Expected: `ls: cannot access 'scripts/apply-task-observer-patches.sh': No such file or directory`

- [ ] **Step 2: Confirm the section title to strip (from Task 1 Step 5)**

Substitute `WITHOUT_PERSISTENT_STORAGE_HEADING` in the script below with the exact `## ` heading text you found in Task 1 Step 5. It should be something like `## Without Persistent Storage` or `## Handoff Document Mode`. Do not guess; use the exact string from the upstream SKILL.md.

- [ ] **Step 3: Write the script**

Create `scripts/apply-task-observer-patches.sh`:

```bash
#!/usr/bin/env bash
# Applies three targeted patches to the upstream one-skill-to-rule-them-all SKILL.md
# and writes the result to ~/.claude/skills/task-observer/SKILL.md.
#
# Patch 1: Replace [your shared folder] with the local repo path (path substitution
#          for all log, archive, and staging paths referenced in the skill).
# Patch 2: Replace <available_skills> with the manifest file path (replaces
#          Cowork's system prompt injection with our SessionStart-generated file).
# Patch 3: Strip the "Without Persistent Storage" section (handoff doc mode).
#          Claude Code always has filesystem access; that section is dead weight here.
#
# The CC BY 4.0 attribution block is not touched by any patch.
# Run again after: git submodule update --remote .submodules/one-skill-to-rule-them-all
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

UPSTREAM="${REPO_ROOT}/.submodules/one-skill-to-rule-them-all/SKILL.md"
OUTPUT="${HOME}/.claude/skills/task-observer/SKILL.md"
REPO_PATH="/home/byron/dev/.claude"
MANIFEST_PATH="${REPO_PATH}/skill-observations/available-skills.md"

# SUBSTITUTE the actual section heading found in Task 1 Step 5 below:
STRIP_SECTION="WITHOUT_PERSISTENT_STORAGE_HEADING"

if [[ ! -f "${UPSTREAM}" ]]; then
    echo "ERROR: upstream SKILL.md not found at ${UPSTREAM}" >&2
    echo "Run: git submodule update --init .submodules/one-skill-to-rule-them-all" >&2
    exit 1
fi

mkdir -p "$(dirname "${OUTPUT}")"

# Apply patches in a single pipeline:
# Patch 1 + Patch 2: sed replacements (both pass-through on lines they don't match)
# Patch 3: awk section strip (skips lines from the target heading to the next ## heading)
sed \
    -e "s|\[your shared folder\]|${REPO_PATH}|g" \
    -e "s|<available_skills>|${MANIFEST_PATH}|g" \
    "${UPSTREAM}" | \
awk -v section="${STRIP_SECTION}" '
    $0 == section { skip=1; next }
    /^## / && skip  { skip=0 }
    !skip           { print }
' > "${OUTPUT}"

echo "Installed: ${OUTPUT}"
```

- [ ] **Step 4: Make executable**

```bash
chmod +x scripts/apply-task-observer-patches.sh
```

- [ ] **Step 5: Verify the shebang and permissions**

```bash
head -1 scripts/apply-task-observer-patches.sh && ls -la scripts/apply-task-observer-patches.sh
```

Expected: First line is `#!/usr/bin/env bash` and permissions show `-rwxr-xr-x`.

- [ ] **Step 6: Commit**

```bash
git add scripts/apply-task-observer-patches.sh
git commit -m "feat: add task-observer patch script for upstream SKILL.md adaptation"
```

---

## Task 4: Run the Patch Script and Install the Skill

**Files:**
- Create: `~/.claude/skills/task-observer/SKILL.md` (output artifact, outside git)

- [ ] **Step 1: Verify the skill directory does not yet exist**

```bash
ls ~/.claude/skills/task-observer 2>&1
```

Expected: `ls: cannot access '/home/byron/.claude/skills/task-observer': No such file or directory`

- [ ] **Step 2: Run the patch script**

```bash
./scripts/apply-task-observer-patches.sh
```

Expected: `Installed: /home/byron/.claude/skills/task-observer/SKILL.md`

- [ ] **Step 3: Verify the output file exists and is non-empty**

```bash
wc -l ~/.claude/skills/task-observer/SKILL.md
```

Expected: A line count significantly less than the upstream (the stripped section is gone), but still substantial (should be more than 50 lines).

- [ ] **Step 4: Verify Patch 1 applied -- no `[your shared folder]` remains**

```bash
grep "\[your shared folder\]" ~/.claude/skills/task-observer/SKILL.md
```

Expected: No output (zero matches).

- [ ] **Step 5: Verify Patch 1 substituted the correct path**

```bash
grep "/home/byron/dev/.claude" ~/.claude/skills/task-observer/SKILL.md | head -3
```

Expected: At least one line showing the repo path substituted in.

- [ ] **Step 6: Verify Patch 2 applied -- `<available_skills>` is replaced**

```bash
grep "<available_skills>" ~/.claude/skills/task-observer/SKILL.md
```

Expected: No output (zero matches).

- [ ] **Step 7: Verify Patch 2 substituted the manifest path**

```bash
grep "skill-observations/available-skills.md" ~/.claude/skills/task-observer/SKILL.md
```

Expected: At least one matching line.

- [ ] **Step 8: Verify Patch 3 stripped the handoff section**

```bash
grep "WITHOUT_PERSISTENT_STORAGE_HEADING" ~/.claude/skills/task-observer/SKILL.md
```

(Replace `WITHOUT_PERSISTENT_STORAGE_HEADING` with the exact heading text from Task 1.)

Expected: No output (section is gone).

- [ ] **Step 9: Verify CC BY 4.0 attribution block is intact**

```bash
grep "CC BY\|rebelytics\|Eoghan" ~/.claude/skills/task-observer/SKILL.md
```

Expected: Same lines as found in Task 1 Step 6 -- attribution is unchanged.

No commit needed: the installed skill lives outside the git repo and is a build artifact.

---

## Task 5: Create the Skills Manifest Generator

**Files:**
- Create: `scripts/generate-skills-manifest.sh`

- [ ] **Step 1: Verify the script does not yet exist**

```bash
ls scripts/generate-skills-manifest.sh 2>&1
```

Expected: `ls: cannot access 'scripts/generate-skills-manifest.sh': No such file or directory`

- [ ] **Step 2: Write the script**

Create `scripts/generate-skills-manifest.sh`:

```bash
#!/usr/bin/env bash
# SessionStart hook: generates skill-observations/available-skills.md by enumerating
# ~/.claude/skills/ and extracting frontmatter descriptions.
# Replaces Cowork's <available_skills> system prompt injection for Claude Code environments.
# Silent on success.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SKILLS_DIR="${HOME}/.claude/skills"
OBS_DIR="${REPO_ROOT}/skill-observations"
OUTPUT="${OBS_DIR}/available-skills.md"

mkdir -p "${OBS_DIR}/archive"

{
    echo "# Available Skills"
    echo "# Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo ""

    if [[ -d "${SKILLS_DIR}" ]]; then
        # Directory-based skills: each has a SKILL.md inside a named subdirectory
        for entry in "${SKILLS_DIR}"/*/; do
            [[ -d "${entry}" ]] || continue
            skill_name="$(basename "${entry}")"
            skill_file="${entry}SKILL.md"
            [[ -f "${skill_file}" ]] || continue

            description="$(awk '
                /^---/ { n++; next }
                n == 1 && /^description:/ {
                    sub(/^description:[[:space:]]*/, "")
                    print
                    exit
                }
            ' "${skill_file}")"

            echo "## ${skill_name}"
            [[ -n "${description}" ]] && echo "${description}"
            echo ""
        done

        # Flat .md skill files directly in skills/
        for skill_file in "${SKILLS_DIR}"/*.md; do
            [[ -f "${skill_file}" ]] || continue
            skill_name="$(basename "${skill_file}" .md)"

            description="$(awk '
                /^---/ { n++; next }
                n == 1 && /^description:/ {
                    sub(/^description:[[:space:]]*/, "")
                    print
                    exit
                }
            ' "${skill_file}")"

            echo "## ${skill_name}"
            [[ -n "${description}" ]] && echo "${description}"
            echo ""
        done
    fi
} > "${OUTPUT}"
```

- [ ] **Step 3: Make executable**

```bash
chmod +x scripts/generate-skills-manifest.sh
```

- [ ] **Step 4: Run the script manually to test it**

```bash
./scripts/generate-skills-manifest.sh
```

Expected: No output (silent on success). The `skill-observations/` directory is created if it did not exist.

- [ ] **Step 5: Verify the manifest was generated**

```bash
head -20 skill-observations/available-skills.md
```

Expected: A header like:
```
# Available Skills
# Generated: 2026-04-28T...

## brainstorming
...

## task-observer
...
```

At minimum `task-observer` should appear since we installed it in Task 4.

- [ ] **Step 6: Verify task-observer appears in the manifest**

```bash
grep "task-observer" skill-observations/available-skills.md
```

Expected: `## task-observer`

- [ ] **Step 7: Verify git ignores the generated file**

```bash
git status skill-observations/
```

Expected: `skill-observations/` does not appear in the output (it is ignored).

- [ ] **Step 8: Commit**

```bash
git add scripts/generate-skills-manifest.sh
git commit -m "feat: add skills manifest generator for SessionStart hook"
```

---

## Task 6: Initialize the Skill-Observations Directory Structure

**Files:**
- Create: `skill-observations/log.md` (gitignored)
- Create: `skill-observations/cross-cutting-principles.md` (gitignored)
- Create: `skill-observations/last-review-date.txt` (gitignored)
- Create: `skill-observations/archive/` (gitignored)

The `skill-observations/` directory may already exist from Task 5 Step 4. These seed files provide the structure the task-observer skill expects to find on its first run.

- [ ] **Step 1: Create the observation log with an empty header**

Create `skill-observations/log.md`:

```markdown
# Skill Observation Log

<!-- Format per observation:
**Observation N** | Skill: <skill-name or "All skills"> | Status: OPEN
- **Issue:** <what was observed>
- **Suggested improvement:** <what should change>
- **Principle:** <which cross-cutting principle this relates to, if any>
-->
```

- [ ] **Step 2: Create the cross-cutting principles file**

Create `skill-observations/cross-cutting-principles.md`:

```markdown
# Cross-Cutting Principles

<!-- This file is populated by the task-observer skill as patterns emerge across
multiple skills. The scheduled review agent consults this as a mandatory checklist
when creating or regenerating any skill. It starts empty and grows over time. -->
```

- [ ] **Step 3: Create the last-review-date file**

```bash
echo "never" > skill-observations/last-review-date.txt
```

- [ ] **Step 4: Verify archive directory exists (created by manifest generator in Task 5)**

```bash
ls skill-observations/archive/
```

Expected: Empty directory listing (or directory already exists from Task 5).

If it does not exist:

```bash
mkdir -p skill-observations/archive
```

- [ ] **Step 5: Verify git still ignores the directory**

```bash
git status skill-observations/
```

Expected: No output -- the entire directory is ignored.

No commit: these are runtime files, not tracked in git.

---

## Task 7: Add the SessionStart Hook to settings.json

**Files:**
- Modify: `settings.json` (lines 71-98 approximately -- the `SessionStart` array)

- [ ] **Step 1: Verify the current hook count**

```bash
grep -c '"type": "command"' settings.json
```

Note the count. After the change, the count should be one higher.

- [ ] **Step 2: Add the new hook entry to the SessionStart array**

In `settings.json`, the `SessionStart` array currently ends at the closing `]` before `"mcpServers"`. Add the new entry after the existing `session-start-rules.sh` block.

Locate this block (around line 88-97):

```json
      {
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.claude/scripts/session-start-rules.sh",
            "timeout": 10,
            "statusMessage": "Detecting session context..."
          }
        ]
      }
    ]
```

Replace it with:

```json
      {
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.claude/scripts/session-start-rules.sh",
            "timeout": 10,
            "statusMessage": "Detecting session context..."
          }
        ]
      },
      {
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.claude/scripts/generate-skills-manifest.sh"
          }
        ]
      }
    ]
```

- [ ] **Step 3: Validate the JSON is well-formed**

```bash
python3 -c "import json, sys; json.load(open('settings.json')); print('valid')"
```

Expected: `valid`

- [ ] **Step 4: Verify the new hook appears**

```bash
grep "generate-skills-manifest" settings.json
```

Expected: `"command": "$HOME/.claude/scripts/generate-skills-manifest.sh"`

- [ ] **Step 5: Commit**

```bash
git add settings.json
git commit -m "feat: add skills manifest generator to SessionStart hooks"
```

---

## Task 8: Update CLAUDE.md with Task Observation Section

**Files:**
- Modify: `CLAUDE.md` (currently 223 lines, ends after `## Global resources`)

- [ ] **Step 1: Verify the section does not yet exist**

```bash
grep "Task observation" CLAUDE.md
```

Expected: No output.

- [ ] **Step 2: Append the Task observation section**

The file currently ends at line 223 with:
```
see `AGENTS-AND-SKILLS.md` and `README.md` at the repo root.
```

Append after line 223:

```markdown

## Task observation

At the start of any task-oriented session -- any interaction where you will
use tools and produce deliverables -- invoke the task-observer skill before
beginning work.

When loading any skill, check the observation log for OPEN observations
tagged to that skill at /home/byron/dev/.claude/skill-observations/log.md.
Apply their insights to the current work before beginning.

Available skills are listed in
/home/byron/dev/.claude/skill-observations/available-skills.md
(regenerated each session start). Use this file when the task-observer
skill references <available_skills>.
```

- [ ] **Step 3: Verify the section was added**

```bash
tail -15 CLAUDE.md
```

Expected: The Task observation section content.

- [ ] **Step 4: Run pre-commit hooks**

```bash
pre-commit run --all-files
```

Expected: All hooks pass. If `no-em-dash` or `validate-front-matter` fail, fix before committing -- CLAUDE.md has no frontmatter so front-matter hooks should skip it.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: add Task observation section to CLAUDE.md for observer activation"
```

---

## Task 9: Set Up Scheduled Autonomous Review

This task sets up the Mon/Wed/Fri CronCreate agent using the `schedule` skill. The agent reads the observation log, applies non-escalated observations, and stages updates.

- [ ] **Step 1: Invoke the schedule skill**

```
/schedule
```

Or use the `Skill` tool to invoke `schedule`.

- [ ] **Step 2: Configure the scheduled agent with these parameters**

When prompted by the schedule skill, provide:

**Schedule:** Monday, Wednesday, Friday at 08:00 (local time)

**Agent prompt** (provide this verbatim):

```
You are the Task Observer scheduled review agent for /home/byron/dev/.claude.

Your job each run:

1. Read skill-observations/log.md. Extract all observations with Status: OPEN.
2. Read skill-observations/cross-cutting-principles.md.
3. For each OPEN observation that is NOT escalated (see escalation policy below),
   find the affected skill at ~/.claude/skills/<skill-name>/SKILL.md and prepare
   an updated version that integrates the observation.
4. Write each updated skill to:
   skill-updates/YYYY-MM-DD/<skill-name>/SKILL.md
   (use today's date in YYYY-MM-DD format)
5. In skill-observations/log.md, change Status: OPEN to Status: ACTIONED for each
   applied observation, adding a note: "Applied YYYY-MM-DD".
6. Write today's date (YYYY-MM-DD) to skill-observations/last-review-date.txt.
7. Delete all date directories in skill-updates/ EXCEPT the two most recent.
8. Write a brief summary: what was applied, what was escalated and why.

ESCALATION POLICY -- flag in the log but do NOT apply autonomously:
- New skill candidates (require user input on naming and scope)
- Observations that remove or restructure existing skill content
- Observations containing uncertainty phrases: "not sure if", "might be",
  "possibly", "unclear whether"
- Two or more observations on the same skill pointing in opposite directions

Model: claude-sonnet-4-6
Repo root: /home/byron/dev/.claude
```

- [ ] **Step 3: Verify the cron entry was created**

After the schedule skill confirms setup, verify:

```bash
# The schedule skill will confirm the CronCreate call succeeded.
# Note the cron ID returned so you can reference it later if needed.
```

Expected: Schedule skill reports success with Mon/Wed/Fri at 08:00.

---

## Task 10: End-to-End Verification

Verify all components work together from a fresh session start.

- [ ] **Step 1: Confirm all committed files are present**

```bash
git log --oneline -8
```

Expected: Should show commits from Tasks 1, 2, 3, 5, 7, 8 in sequence.

- [ ] **Step 2: Check the installed skill**

```bash
ls -la ~/.claude/skills/task-observer/SKILL.md
```

Expected: File exists with a recent modification timestamp.

- [ ] **Step 3: Check the manifest reflects the installed skill**

```bash
grep -A 2 "^## task-observer" skill-observations/available-skills.md
```

Expected: The task-observer skill appears with its description extracted from frontmatter.

- [ ] **Step 4: Verify the upstream update workflow works**

This simulates what you would do after `git submodule update --remote`:

```bash
./scripts/apply-task-observer-patches.sh
```

Expected: `Installed: /home/byron/.claude/skills/task-observer/SKILL.md` with no errors.

- [ ] **Step 5: Verify the manifest generator is wired into settings.json**

```bash
python3 -c "
import json
s = json.load(open('settings.json'))
hooks = s['hooks']['SessionStart']
cmds = [h['hooks'][0]['command'] for h in hooks]
print('generate-skills-manifest found:', any('generate-skills-manifest' in c for c in cmds))
"
```

Expected: `generate-skills-manifest found: True`

- [ ] **Step 6: Verify CLAUDE.md has the activation section**

```bash
grep -c "Task observation" CLAUDE.md
```

Expected: `1`

- [ ] **Step 7: Document the upstream update procedure**

No code change needed -- the spec already documents this. But confirm you can describe the workflow from memory:

1. `git submodule update --remote .submodules/one-skill-to-rule-them-all`
2. `./scripts/apply-task-observer-patches.sh`

That is the complete upstream update workflow. No other steps.

- [ ] **Step 8: Manual smoke test -- invoke task-observer in a new Claude Code session**

Start a new Claude Code session (so CLAUDE.md fires fresh) and observe:

- The `generate-skills-manifest.sh` hook runs silently at session start
- `skill-observations/available-skills.md` is updated (check modification timestamp)
- When you begin a task-oriented interaction, CLAUDE.md instructs the observer to be invoked
- The task-observer skill can be found and loaded via the Skill tool

---

## Appendix: Ongoing Maintenance

**After each upstream SKILL.md release:**

```bash
git submodule update --remote .submodules/one-skill-to-rule-them-all
./scripts/apply-task-observer-patches.sh
# Verify the three verification steps from Task 4 still pass
```

**Accepting a staged skill update:**

```bash
# After a scheduled review run stages an update:
cp skill-updates/YYYY-MM-DD/<skill-name>/SKILL.md ~/.claude/skills/<skill-name>/SKILL.md
```

**Reviewing scheduled agent output:**

Check `skill-observations/log.md` for `Status: ACTIONED` entries with dates, and
`skill-updates/YYYY-MM-DD/` for any staged files awaiting acceptance.
