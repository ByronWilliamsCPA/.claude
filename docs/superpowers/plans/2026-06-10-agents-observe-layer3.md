---
schema_type: planning
title: "agents-observe Layer 3 Adoption"
status: draft
owner: core-maintainer
purpose: "Adopt the agents-observe plugin, pinned at a release tag, to provide per-subagent token attribution (usage-monitoring Layer 3) with hook-composition review, security pass, and a decision on a /usage-report agents mode."
component: Development-Tools
source: "GitHub issue #197 (Layer 3: adopt agents-observe plugin for per-subagent token attribution)"
tags:
  - automation
  - hooks
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install the agents-observe Claude Code plugin pinned at release v0.9.11 so that supervisor-pattern sessions show per-agent token attribution for the full delegation tree, with the existing 11 repo-managed hooks unaffected, the SQLite store confirmed local and gitignored, a security review of what the hooks persist, and a recorded decision on adding an `agents` mode to `/usage-report`.

**Architecture:** agents-observe ships as a Claude Code plugin whose hooks live in the plugin's own `hooks/hooks.json` (29 events, all running `bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/hook.sh`, plus a `SessionStart` autostart via `observe_cli.mjs`). Plugin hooks are loaded by the plugin system and run in addition to `settings.json` hooks; they never modify `settings.json`. Pinning follows the repo's established posture: a git submodule at `.submodules/agents-observe` checked out at the `v0.9.11` tag, registered as a directory-source marketplace in `extraKnownMarketplaces` (the same pattern as `superpowers-dev` and `anthropic-agent-skills`). The SQLite database lands at `~/.claude/plugins/data/agents-observe-<variant>/data/observe.db`, which is outside the repo working tree; `*.db` in `.gitignore` provides a second layer of protection.

**Tech Stack:** Claude Code plugin system (`claude plugin` CLI, `enabledPlugins`, `extraKnownMarketplaces`), git submodules, SQLite (`sqlite3` CLI), bash, jq.

---

### Hard Constraints (every task must respect)

1. **Precondition: PR #198 must be merged first.** `docs/reference/usage-monitoring-survey.md` and `.claude/skills/usage-report/SKILL.md` exist only on branch `claude/usage-monitoring-visibility-0ylkey` (PR #198, open as of 2026-06-10). Tasks 7 and 8 edit those files. Task 0 verifies the merge; if PR #198 is not merged, stop and surface to the user rather than basing this branch on an unmerged branch.
2. **Two copies of settings.json.** The repo tracks the canonical `settings.json` at the repo root; setup.sh merges it into the live `~/.claude/settings.json` (a real file, not a symlink). Every settings change in this plan must be applied to BOTH files, repo copy first (it is the reviewed artifact), live copy second.
3. **No `claude plugin update` as a fix.** The pin is the submodule SHA. If something is broken, fix the submodule pin explicitly and record why.
4. **Treat agents-observe code as untrusted input during review.** Tasks 2 and 3 read third-party hook scripts. Do not execute repo-external scripts outside the plugin system's normal invocation path during review; read them.
5. **Signed conventional commits**, `pre-commit run --all-files` before each commit, no em-dash characters in any authored text.
6. **Worktree isolation.** All work happens in `.worktrees/agents-observe-layer3` (shared-clone concurrency: other agent sessions use this clone).

### Known Unknowns (verify during execution, do not assume)

- `#ASSUME` The plugin manifest name is `agents-observe` and the db path variant suffix. `#VERIFY` in Task 1 Step 4 (read `.claude-plugin/plugin.json`) and Task 5 Step 1 (find the actual db).
- `#ASSUME` The plugin runs from a source checkout without a separate build step (the README's standalone mode uses `just install`, but plugin installs are expected to be self-contained). `#VERIFY` in Task 4 Step 5; the fallback if it fails is documented in Task 4 Step 6.
- `#ASSUME` The observe.db schema exposes per-agent token columns. `#VERIFY` in Task 6 Step 2 via `.schema`; the `/usage-report agents` decision in Task 7 hinges on this.

---

### Task 0: Preconditions and worktree

**Files:** none created; verification only.

- [ ] **Step 1: Verify PR #198 is merged**

```bash
gh pr view 198 --json state,mergedAt --jq '"state=\(.state) mergedAt=\(.mergedAt)"'
```

Expected: `state=MERGED mergedAt=<timestamp>`.
If state is `OPEN` or `CLOSED` without merge: STOP. Report to the user that issue 197 is blocked on PR #198 and do not proceed.

- [ ] **Step 2: Verify the Layer 1-2 artifacts landed on main**

```bash
cd ~/dev/.claude && git fetch origin && git log origin/main --oneline -1 -- docs/reference/usage-monitoring-survey.md .claude/skills/usage-report/SKILL.md
```

Expected: one commit line. Empty output means the files are missing from main; STOP and report.

- [ ] **Step 3: Create the worktree**

```bash
cd ~/dev/.claude && git worktree add .worktrees/agents-observe-layer3 -b feat/agents-observe-layer3 origin/main && cd .worktrees/agents-observe-layer3
```

Expected: `Preparing worktree (new branch 'feat/agents-observe-layer3')`. All subsequent tasks run from this worktree directory.

---

### Task 1: Pin agents-observe as a submodule at v0.9.11

**Files:**
- Create: `.submodules/agents-observe` (submodule)
- Modify: `.gitmodules`

- [ ] **Step 1: Confirm the release tag exists upstream**

```bash
git ls-remote --tags https://github.com/simple10/agents-observe v0.9.11
```

Expected: one line ending in `refs/tags/v0.9.11`. If empty, list available tags with `git ls-remote --tags https://github.com/simple10/agents-observe | tail -5` and use the newest stable tag instead, noting the substitution in the commit message.

- [ ] **Step 2: Add the submodule and pin it**

```bash
git submodule add https://github.com/simple10/agents-observe .submodules/agents-observe
cd .submodules/agents-observe && git checkout v0.9.11 && cd ../..
git add .gitmodules .submodules/agents-observe
```

Expected: `git status` shows `.gitmodules` and the submodule as staged, and `git diff --cached --submodule` shows the submodule at the v0.9.11 commit.

- [ ] **Step 3: Confirm submodule isolation holds**

The repo policy makes `.submodules/` inert to quality gates (pre-commit global exclude plus per-tool excludes). Verify the new path is covered:

```bash
grep -n "submodules" .pre-commit-config.yaml | head -5
pre-commit run --all-files 2>&1 | tail -15
```

Expected: the global `exclude:` pattern covers `.submodules/` (it matches the directory, not individual submodule names), and pre-commit passes without scanning agents-observe files. If any hook flags files under `.submodules/agents-observe/`, fix the exclude pattern, not the plugin files.

- [ ] **Step 4: Read the plugin manifest and record identity facts**

```bash
cat .submodules/agents-observe/.claude-plugin/plugin.json 2>/dev/null || find .submodules/agents-observe -maxdepth 2 -name "*.json" | head
cat .submodules/agents-observe/.claude-plugin/marketplace.json 2>/dev/null
```

Record (in scratch notes for Tasks 4 and 8): the plugin `name`, the marketplace `name`, and whether the manifest declares a `userConfig` schema. These determine the exact `enabledPlugins` key in Task 4.

- [ ] **Step 5: Commit**

```bash
git add .gitmodules .submodules/agents-observe
git commit -S -m "feat(plugins): pin agents-observe submodule at v0.9.11

Layer 3 of the usage-monitoring adoption plan (issue #197).
Submodule serves as a directory-source plugin marketplace, matching
the superpowers and anthropics-skills pinning posture."
```

---

### Task 2: Hook conflict review and composition documentation

depends-on: Task1 [output]

**Files:**
- Read: `.submodules/agents-observe/hooks/hooks.json`, `.submodules/agents-observe/hooks/scripts/hook.sh`
- Modify: `docs/reference/hooks.md` (add a composition section)

- [ ] **Step 1: Inventory the plugin's hook registrations**

```bash
jq -r 'to_entries[] | "\(.key): \(.value | length) registration(s)"' .submodules/agents-observe/hooks/hooks.json
```

Expected (from upstream main as of June 2026): 29 events including PreToolUse, PostToolUse, Stop, UserPromptSubmit, SessionStart, SubagentStart, SubagentStop. Confirm against the pinned checkout; record any difference.

- [ ] **Step 2: Verify the hook script cannot block tool calls**

A PreToolUse hook that exits non-zero or emits a deny decision blocks the tool. Read `hook.sh` and confirm it is fire-and-forget:

```bash
grep -nE "exit [^0]|\"decision\"|permissionDecision" .submodules/agents-observe/hooks/scripts/hook.sh
tail -5 .submodules/agents-observe/hooks/scripts/hook.sh
```

Expected: no non-zero exits on the normal path and no decision JSON on stdout. If the script can exit non-zero on the PreToolUse path (for example when its event spool is unwritable), record that as a caveat for the survey doc in Task 8 and as a finding in this task's doc section.

- [ ] **Step 3: Map overlap against repo-managed hooks**

The 11 repo-managed registrations in `settings.json` (canonical copy at repo root) cover PreToolUse (5), PostToolUse (2), Stop (2), UserPromptSubmit (2). Build a short table: for each event where both sources register, note that both run independently and that plugin hooks cannot replace or reorder `settings.json` hooks. The only shared failure mode is cumulative latency, two extra process spawns per tool call.

- [ ] **Step 4: Write the composition section**

Append to `docs/reference/hooks.md` (keep heading level consistent with the file's existing structure):

```markdown
## Plugin hooks vs repo-managed hooks

Plugins registered through `enabledPlugins` contribute hooks from their own
`hooks/hooks.json`; the plugin system loads them alongside the hooks defined
in `settings.json`. The two sources compose additively:

- A plugin cannot modify, remove, or reorder `settings.json` hooks. Disabling
  the plugin removes its hooks without touching repo-managed ones.
- Both sources fire on the same event. For `PreToolUse` on `Bash`, the order
  observed is settings.json hooks first, then plugin hooks; do not write
  hooks that depend on this ordering, it is not contractual.
- Blocking semantics apply per hook: any PreToolUse hook (either source)
  that exits 2 or returns a deny decision blocks the tool call. Observability
  hooks must therefore be fire-and-forget (exit 0 on every path).
- Latency budget: each registration is one process spawn per event. As of
  2026-06, repo-managed hooks add up to 5 spawns per Bash call and
  agents-observe adds 1 more per Pre/PostToolUse event.

Current plugin hook contributors: hookify (via settings.json command
entries, a legacy wiring), security-guidance (settings.json), and
agents-observe (true plugin-system hooks from
`.submodules/agents-observe/hooks/hooks.json`, pinned at v0.9.11).
```

Adjust the ordering claim in the second bullet to match what Step 5 of Task 6 actually observes; if unverified, state "ordering between sources is unspecified".

- [ ] **Step 5: Commit**

```bash
pre-commit run --files docs/reference/hooks.md
git add docs/reference/hooks.md
git commit -S -m "docs(hooks): document plugin hook composition with repo-managed hooks"
```

---

### Task 3: Security review of captured data

depends-on: Task1 [output]; can run in parallel with Task 2.

**Files:**
- Read: `.submodules/agents-observe/hooks/scripts/hook.sh`, `.submodules/agents-observe/hooks/scripts/observe_cli.mjs`, any ingest/server source under `.submodules/agents-observe/`
- Create: scratch findings list (feeds Task 8's survey-doc caveats; no standalone committed artifact)

- [ ] **Step 1: Determine what the hook persists**

```bash
grep -rnE "tool_input|tool_response|prompt|transcript|INSERT INTO" .submodules/agents-observe/hooks/scripts/ | head -30
grep -rn "CREATE TABLE" .submodules/agents-observe --include="*.mjs" --include="*.js" --include="*.sql" -l
```

Answer these questions explicitly, with file:line citations:
1. Does it store full tool inputs (Bash command text, Write file contents)? Upstream README says yes for tool call payloads.
2. Does it store user prompt content (UserPromptSubmit payload includes the prompt text)?
3. Does it store transcript or model output text, or metadata only?
4. Does it transmit anything off-host (search for `fetch(`, `http`, `POST` to non-localhost)?

- [ ] **Step 2: Classify the result**

Expected outcome (verify, do not assume): data stays in a local SQLite db; payloads include tool commands and results, which can contain secrets that appear in shell commands or written files. The mitigations to record: db is outside the repo tree, `*.db` is gitignored, nothing leaves the host, and the existing `bash-pre-hook.sh` and `sensitive-file-guard.sh` reduce secret-bearing tool calls in the first place. If Step 1 finds off-host transmission, STOP and surface to the user before enabling the plugin (Task 4 must not proceed).

- [ ] **Step 3: Record findings**

Write the findings as a bullet list in the worktree at `docs/superpowers/plans/notes-197-security.md` marked clearly as a working note (it gets folded into the survey doc in Task 8 and deleted there; do not commit it separately).

---

### Task 4: Register the marketplace and install the plugin

depends-on: Task2 [completion], Task3 [completion] (Task 3 Step 2 is a go/no-go gate)

**Files:**
- Modify: `settings.json` (repo root, canonical)
- Modify: `~/.claude/settings.json` (live copy, not in this repo's tree)

- [ ] **Step 1: Add the directory marketplace to the repo settings.json**

In the repo-root `settings.json`, add to `extraKnownMarketplaces` (sibling of the existing `superpowers-dev` entry), using the marketplace name recorded in Task 1 Step 4 (shown here as `agents-observe`; substitute if the manifest differs):

```json
"agents-observe": {
  "source": {
    "source": "directory",
    "path": "/home/byron/dev/.claude/.submodules/agents-observe"
  }
}
```

And to `enabledPlugins`:

```json
"agents-observe@agents-observe": true
```

- [ ] **Step 2: Mirror both edits into the live `~/.claude/settings.json`**

Apply the identical two edits to `/home/byron/.claude/settings.json`. Then verify the copies agree:

```bash
jq '.extraKnownMarketplaces["agents-observe"], .enabledPlugins["agents-observe@agents-observe"]' ~/dev/.claude/.worktrees/agents-observe-layer3/settings.json ~/.claude/settings.json
```

Expected: the marketplace object and `true` printed twice, identically.

- [ ] **Step 3: Install via the plugin CLI**

```bash
claude plugin install agents-observe@agents-observe --scope user
```

Expected: success message. Note: `claude plugin install` has no version flag; the version is pinned by the submodule checkout the marketplace points at.

- [ ] **Step 4: Verify the install record captures the pin**

```bash
jq '.plugins["agents-observe@agents-observe"]' ~/.claude/plugins/installed_plugins.json
```

Expected: an entry with `version` and `gitCommitSha`. Record the SHA and confirm it matches the submodule pin:

```bash
git -C ~/dev/.claude/.worktrees/agents-observe-layer3/.submodules/agents-observe rev-parse HEAD
```

- [ ] **Step 5: Smoke-test in a fresh session**

Start a new Claude Code session (plugin hooks load at session start), run one trivial Bash tool call (`echo ok`), exit, and check for hook errors:

```bash
find ~/.claude/plugins/data -maxdepth 3 -name "observe.db" -newer ~/.claude/plugins/installed_plugins.json 2>/dev/null
```

Expected: one `observe.db` path with a fresh mtime, and no hook error/timeout warnings in the session. If the hooks error because the source checkout lacks built artifacts (missing `node_modules` or similar), proceed to Step 6; otherwise skip Step 6.

- [ ] **Step 6 (fallback only): GitHub-marketplace install**

If and only if the directory-marketplace install cannot run from the raw source checkout: remove the Step 1-2 settings entries, then install from the upstream marketplace and treat the lockfile record as the pin:

```bash
claude plugin marketplace add simple10/agents-observe
claude plugin install agents-observe --scope user
jq '.plugins | to_entries[] | select(.key | startswith("agents-observe")) | .value[0] | {version, gitCommitSha}' ~/.claude/plugins/installed_plugins.json
```

Record version and SHA; keep the submodule from Task 1 as the audited source reference. Document in Task 8 that pinning is via the `installed_plugins.json` record and that `claude plugin update` must not be run for this plugin without re-running the Task 3 security review.

- [ ] **Step 7: Commit the settings change**

```bash
pre-commit run --files settings.json
git add settings.json
git commit -S -m "feat(plugins): enable agents-observe via directory marketplace

Plugin hooks load from the v0.9.11 submodule pin. Live
~/.claude/settings.json updated to match."
```

(If Step 6 fired, the commit instead documents the GitHub-marketplace approach; adjust the message accordingly.)

---

### Task 5: Verify data storage location and gitignore coverage

depends-on: Task4 [output]

**Files:** none modified unless a gap is found (then: `.gitignore`).

- [ ] **Step 1: Locate the database and confirm it is outside the repo tree**

```bash
DB=$(find ~/.claude/plugins/data -maxdepth 3 -name "observe.db" | head -1); echo "$DB"
readlink -f "$DB"
git -C ~/dev/.claude ls-files --error-unmatch "$DB" 2>&1
```

Expected: the resolved path is under `/home/byron/.claude/plugins/data/` (a real directory, not a symlink into the repo), and the `ls-files` call errors with "did not match any file(s)", proving git does not track it.

- [ ] **Step 2: Confirm defense-in-depth gitignore coverage**

```bash
cd ~/dev/.claude && git check-ignore -v plugins/data/x/observe.db plugins/data/x/observe.db-wal plugins/data/x/observe.db-shm
```

Expected: `*.db` matches the first. If the `-wal`/`-shm` sidecar files do not match any rule, append to `.gitignore` under the existing "Database files" block (lines 186-189):

```text
*.db-wal
*.db-shm
```

- [ ] **Step 3: Commit (only if .gitignore changed)**

```bash
git add .gitignore && git commit -S -m "chore(gitignore): cover SQLite WAL sidecar files"
```

---

### Task 6: Representative supervisor-pattern validation sessions

depends-on: Task4 [output]

**Files:** none modified; produces evidence for Tasks 7 and 8.

- [ ] **Step 1: Run a supervisor-pattern session**

In a fresh Claude Code session in this repo, run a task that dispatches at least two named subagents in parallel plus one nested delegation, for example: "Use the Agent tool to run two Explore agents in parallel (one mapping docs/, one mapping scripts/) and then a code-reviewer agent on scripts/bash-pre-hook.sh." Let it complete, then exit the session.

- [ ] **Step 2: Discover the schema**

```bash
DB=$(find ~/.claude/plugins/data -maxdepth 3 -name "observe.db" | head -1)
sqlite3 "$DB" ".tables"
sqlite3 "$DB" ".schema" | grep -iE "agent|token" | head -30
```

Record the actual table and column names. The queries in Step 3 use placeholder names; substitute the real ones.

- [ ] **Step 3: Verify per-agent attribution**

```bash
sqlite3 -header -column "$DB" "SELECT agent_name, parent_agent, SUM(total_tokens) FROM <agents/events table> GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10;"
```

Acceptance evidence (maps to the issue's second checkbox): the output names the dispatched subagents (the two Explore agents and code-reviewer), shows a parent linkage forming the delegation tree, and shows nonzero token counts per agent. Also open the plugin's dashboard once (per its README, `SessionStart` autostarts it; otherwise use its documented start command) and confirm the same tree renders.

- [ ] **Step 4: Hook regression check**

Confirm the repo-managed hooks still behave with the plugin active:

```bash
# bash-pre-hook still blocks a guarded command (expect a block message, not execution):
# in the live session attempt: git push --force origin main   (it must be refused)
echo "test" > /tmp/hook-regression-probe.txt
```

In the session: one Bash call (bash-pre-hook fires), one Write to a repo file then undo (sensitive-file-guard and py310-compat fire), one normal stop (session-length-warning fires). Expected: identical behavior to pre-plugin sessions, no new latency warnings or hook timeouts. Record the observed source ordering for Task 2's doc adjustment.

- [ ] **Step 5: Record results**

Append the evidence (queries used, row counts, dashboard confirmation, regression notes) to `docs/superpowers/plans/notes-197-security.md` working note for folding into Task 8.

---

### Task 7: Decide and (if go) implement `/usage-report agents` mode

depends-on: Task6 [output]

**Files:**
- Modify: `.claude/skills/usage-report/SKILL.md` (exists on main after PR #198)

- [ ] **Step 1: Apply the decision rule**

GO (implement the mode) if all three hold from Task 6: (a) per-agent token columns exist and are queryable with plain `sqlite3`, (b) agent names match the repo's catalog names (so the Model Selection policy can be checked against frontmatter), (c) the db path is discoverable deterministically (stable glob under `~/.claude/plugins/data/`). Otherwise DEFER: skip Steps 2-3 and record the failing condition as the deferral reason in Task 8's survey-doc update.

- [ ] **Step 2 (GO path): Add the agents mode to the skill**

In `.claude/skills/usage-report/SKILL.md`: add `agents` to the mode list in the invocation line (`/usage-report [daily|weekly|monthly|session|blocks|agents]`), add `agents` to the trigger list in the frontmatter description, and add a mode section (substitute the real table/column names discovered in Task 6 Step 2):

```markdown
### agents mode

Per-subagent token attribution from the agents-observe plugin database.
Requires the agents-observe plugin (Layer 3); if the database is missing,
say so and point to docs/reference/usage-monitoring-survey.md section 4.

1. Locate the database:
   `DB=$(find ~/.claude/plugins/data -maxdepth 3 -name "observe.db" | head -1)`
2. Query the delegation tree with token totals:
   `sqlite3 -header -column "$DB" "SELECT <agent>, <parent>, <model>, SUM(<tokens>) AS tokens FROM <table> WHERE <session scope filter> GROUP BY 1,2,3 ORDER BY tokens DESC LIMIT 20;"`
3. Summarize: top 5 agents by tokens, any agent whose recorded model
   contradicts its frontmatter model (flag against the CLAUDE.md Model
   Selection policy), and the deepest delegation chain observed.
4. Keep output under 30 lines, terminal only, same as other modes.
```

- [ ] **Step 3 (GO path): Verify the skill text against reality**

Run the two commands from the new section verbatim in a shell and confirm they return rows. A skill that documents a query that does not run is worse than no mode (memory: skill workflows are executed literally).

- [ ] **Step 4: Commit**

```bash
pre-commit run --files .claude/skills/usage-report/SKILL.md
git add .claude/skills/usage-report/SKILL.md
git commit -S -m "feat(skills): add agents mode to /usage-report via agents-observe db"
```

(DEFER path: no commit in this task; the decision is recorded in Task 8.)

---

### Task 8: Documentation updates

depends-on: Task6 [output], Task7 [completion]

**Files:**
- Modify: `docs/reference/usage-monitoring-survey.md` (section 4, Layer 3 row/paragraph)
- Modify: `AGENTS-AND-SKILLS.md` (skill entry, only if Task 7 went GO)
- Delete: `docs/superpowers/plans/notes-197-security.md` (content folded in)

- [ ] **Step 1: Update the survey doc**

In section 4, mark Layer 3 implemented with: the pinned version and pin mechanism (submodule at v0.9.11, or the Task 4 Step 6 fallback record), the db location, the hook composition summary (one sentence, link to `docs/reference/hooks.md`), the Task 3 security findings as explicit caveats (what is persisted: tool payloads and, if confirmed, prompt text; all local; gitignored), and the `/usage-report agents` decision (implemented, or deferred with the failing condition from Task 7 Step 1). Keep Layer 4 explicitly deferred, unchanged.

- [ ] **Step 2: Update AGENTS-AND-SKILLS.md (GO path only)**

In the Skills section where `/usage-report` is registered, extend its mode list with `agents` and one clause: "per-subagent token attribution via agents-observe (Layer 3)".

- [ ] **Step 3: Remove the working note and commit**

```bash
git rm docs/superpowers/plans/notes-197-security.md 2>/dev/null || rm -f docs/superpowers/plans/notes-197-security.md
pre-commit run --all-files
git add docs/reference/usage-monitoring-survey.md AGENTS-AND-SKILLS.md
git commit -S -m "docs(reference): mark usage-monitoring Layer 3 implemented

Records agents-observe pin, hook composition, data-storage location,
security review findings, and the /usage-report agents decision
(issue #197)."
```

---

### Task 9: Final verification and PR

depends-on: Task8 [completion]

- [ ] **Step 1: Acceptance criteria sweep**

Walk the issue's five checkboxes against evidence: pin recorded (Task 4 Step 4), per-agent attribution shown (Task 6 Step 3 output), storage local and gitignored (Task 5), survey doc updated (Task 8), `/usage-report agents` decision recorded (Task 7/8). Each must have a concrete artifact, not an assertion.

- [ ] **Step 2: Full gate run and staged-diff check**

```bash
pre-commit run --all-files
git diff origin/main --stat
```

Expected: gates pass; the diff touches only the files this plan names (shared-clone safety: nothing from concurrent sessions bundled in).

- [ ] **Step 3: Push and open the PR**

```bash
git push -u origin feat/agents-observe-layer3
gh pr create --title "feat(plugins): adopt agents-observe for per-subagent token attribution (Layer 3)" --body "Closes #197.

Implements Layer 3 of the usage-monitoring adoption plan: agents-observe pinned at v0.9.11 as a directory-source marketplace submodule, hook composition documented in docs/reference/hooks.md, security review recorded in the survey doc, storage verified local and gitignored, and the /usage-report agents decision recorded.

Generated with [Claude Code](https://claude.com/claude-code)"
```

If `gh pr create` is permission-denied by the harness, use the equivalent `gh api repos/{owner}/{repo}/pulls -X POST` fallback.

- [ ] **Step 4: Cleanup**

After merge (separate session or after CI): `git worktree remove .worktrees/agents-observe-layer3`.
