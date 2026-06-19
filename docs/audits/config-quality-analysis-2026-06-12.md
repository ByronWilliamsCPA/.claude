---
title: "Config Quality Analysis: Capabilities Gap and Improvement Plan"
schema_type: planning
status: draft
owner: core-maintainer
component: Strategy
source: "Three-agent analysis (structural inventory + drift audit + best-practices research) with supervisor verification"
purpose: "Full quality analysis of this config repo against current Claude Code capabilities and Anthropic plus community best practices, with a prioritized improvement plan."
tags:
  - configuration
  - quality
  - planning
  - compliance
---

**Date:** 2026-06-12
**Method:** Three parallel analysis tracks: (1) structural inventory of agents, skills, commands, settings, hooks, and MCP config with byte-level measurements; (2) drift and contradiction audit across CLAUDE.md, rules, standards, catalogs, and docs; (3) research against official Claude Code documentation (code.claude.com/docs) and community sources current to June 2026. Subagent claims were spot-verified before inclusion; two inventory claims were corrected during verification (see Appendix C).

## Summary

The repo is in good operational health: 50 commits in 60 days, every pre-commit invariant in `.claude/rules/pre-commit.md` verified against the actual `.pre-commit-config.yaml` with zero mismatches, all CLAUDE.md cross-references resolving, and 45 of 46 working agents carrying `tools:` restrictions (the lone exception is the frontmatter-less `ossf-criteria-reference` reference file, relocated to `.claude/standards/` in this change). The improvement opportunities fall into two classes:

1. **Architecture lag.** Several homegrown mechanisms predate native Claude Code features that now do the same job better: the MCP tier-loading design (never wired to a hook) is superseded by per-subagent `mcpServers` frontmatter; the commands directory is a legacy mechanism; the symlink-plus-submodule install is what plugin marketplaces now solve; and prose "always/never" rules sit in always-loaded context where hooks would give deterministic enforcement at zero context cost.
2. **Context budget.** Roughly 33,000 tokens load before any work begins in a typical task session (15,200 from CLAUDE.md plus unscoped rules, about 18,000 from the task-observer skill). Official guidance targets under 200 lines per CLAUDE.md file and warns that bloat reduces instruction adherence. This is the single largest lever on output quality across all repos this config governs.

Findings are ordered by priority. Each item names the file, the problem, and the recommended action.

## What is working well

- The pre-commit invariant system (PC-YAMLLINT-FILE-REF, PC-MARKDOWNLINT-MD040, PC-HOOK-STAGED-SCOPE, no-em-dash PC-011, interrogate, pydoclint, commitizen, detect-secrets) is fully consistent between the rule doc and the live config. This audit found zero gaps.
- `.claude/rules/python.md` and `.claude/rules/testing.md` use `paths:` frontmatter correctly and load only when matching files are touched.
- The standards manifest (174 checks across 9 domains) plus the domain-auditor agent family is a coherent, testable compliance architecture with regression fixtures under `data/test_fixtures/`.
- Agent hygiene is above community norms: 45 of 46 working agents restrict `tools:` (the one exception, `ossf-criteria-reference`, carries no frontmatter and is a reference file, not an executable agent), and the supervisor output-envelope contract (verdict plus mandatory evidence field) is a pattern Anthropic's own docs now recommend.
- The cost-lane documentation in `mcp-strategy.md` (subscription vs Agent SDK credit vs metered API) is accurate and ahead of most community guidance.

## Priority 1: Broken or misfiring machinery

These are defects in the current setup, independent of any best-practice judgment.

### 1.1 `bash-pre-hook.sh` registered twice

Both `/settings.json` (user scope, repo root) and `.claude/settings.json` (project scope) register `bash-pre-hook.sh` on `PreToolUse/Bash`. When working inside this repo, the hook fires twice per Bash call: doubled latency and double-block risk. Remove the project-scope duplicate.

### 1.2 zen/pal MCP server registered under two names

`settings.json` registers the server as `zen`; `.mcp.json` registers the same binary as `pal`. Both load, creating two instances. Tool references are split across the codebase: the `rad` skill and `project-planning` skill reference `mcp__pal__*`, while `project-plan-synthesizer` references `mcp__zen__consensus`. Whichever single name is kept (CLAUDE.md's own guidance in `mcp-strategy.md` says keep `zen`), one registration must be deleted and all `mcp__pal__*` references renamed.

### 1.3 Machine-specific absolute paths in tracked files

`/home/byron/...` paths appear in files consumed at runtime on other machines:

- `settings.json`: `extraKnownMarketplaces` and `enabledPlugins` point at `/home/byron/dev/.claude/.submodules/agents-observe`, so the agents-observe plugin fails everywhere except the original machine.
- `docs/standards-manifest.yaml`: three `source_template:` entries use `/home/byron/dev/...`; the repo-foundations-auditor emits these paths in its remediation output (`.claude/agents/repo-foundations-auditor.md:94`).

Replace with `~`-relative or repo-relative paths resolved at runtime.

### 1.4 `enabledMcpjsonServers` lists six undefined servers

`settings.json` enables `playwright`, `postgres`, `sentry`, `mermaid`, `docker`, and `uml-mcp-server`, but no loaded config defines them (they exist only in the design file `mcp/mcp_config.yaml`). Either define them in `.mcp.json` or remove the entries; see also finding 3.1.

### 1.5 `ossf-criteria-reference.md` is not an agent

A 266-line reference table sits in `.claude/agents/` with no frontmatter at all. It is the one file failing the repo's own `validate-frontmatter.sh` contract, and per ADR-004 it belongs in `.claude/standards/`. Move it and update the two OSSF agents that reference it.

### 1.6 Cloud and fresh-clone sessions silently lose a third of the catalog

14 agent, 19 skill, and 7 command symlinks resolve into submodules that are empty in any clone where `install-vendored-plugins.sh` has not run, which includes every Claude Code on the web session (this one included). The writing pipeline (all seven reference-library agents), the entire superpowers skill set, the pr-review-toolkit agents, and the hookify commands are all unavailable here, while AGENTS-AND-SKILLS.md and CLAUDE.md present them as live. Actions:

- Add a repo SessionStart hook (the `session-start-hook` skill exists for exactly this) that runs `git submodule update --init` plus `install-vendored-plugins.sh`, or document the limitation.
- Mark submodule-backed entries in AGENTS-AND-SKILLS.md so a session can tell local from vendored.
- Longer term, finding 3.4 (marketplace packaging) removes the symlink fragility entirely.

### 1.7 `sonarqube` MCP server has undocumented prerequisites

`.mcp.json` defines `sonarqube` against `http://localhost:8090/mcp` with `SONARQUBE_TOKEN`, but neither appears in `.env.mcp.example`. Add both, or the sonarcloud skill fails opaquely on new machines.

## Priority 2: Context budget and enforcement architecture

This is where the config most directly affects the quality of code produced everywhere else. Official guidance: target under 200 lines per CLAUDE.md file; "bloated CLAUDE.md files cause Claude to ignore your actual instructions" (code.claude.com/docs/en/memory, /best-practices). Community measurements put the effective high-adherence budget at 80 to 120 lines of high-signal content.

### 2.1 Always-on context is about 15,200 tokens; target is roughly half that

Measured bytes loaded into every session regardless of task:

| File | Bytes | Path-scoped? |
| --- | --- | --- |
| `CLAUDE.md` | 12,977 | no (by design) |
| `.claude/rules/git-workflow.md` | 14,449 | no |
| `.claude/rules/supervisor.md` | 9,998 | no |
| `.claude/rules/mcp-strategy.md` | 7,506 | no |
| `.claude/rules/pre-commit.md` | 7,447 | no |
| `.claude/rules/writing.md` | 4,087 | no |
| `.claude/rules/settings-and-permissions.md` | 2,640 | no |
| `.claude/rules/loop-recipes.md` | 1,683 | no |
| Total | 60,787 (~15,200 tokens) | |

(`python.md` at 10.2 KB and `testing.md` at 3.6 KB are correctly path-scoped and excluded.)

Recommended dispositions, in descending size order:

- **git-workflow.md (14.4 KB):** keep the branch strategy table, force-push prohibition, and remote verification (about 3 KB). Move merge-queue guidance, PR-size calibration, session forking, gate-system catalog, and worktree detail into the `/git` skill's context files, which already exist (`.claude/skills/git/context/`). These are needed at git-operation time, and the `/git` skill fires then.
- **supervisor.md (10.0 KB):** the agent-assignment table duplicates information Claude already receives from agent descriptions in its listing; the output-envelope spec is needed only when composing agent prompts. Keep the core requirements and scope-tracing rule (about 2 KB); move the envelope spec and two-pattern architecture to `.claude/standards/`.
- **mcp-strategy.md (7.5 KB):** the cost-lane table is the load-bearing part. Keep it (about 2 KB); move tier tables and fork-history narrative to `.claude/standards/mcp-minimal-bloat.md`, which already covers adjacent ground.
- **pre-commit.md (7.4 KB):** a checklist consulted at commit time is the textbook case for skill-time loading. Move into the `/git` skill (commit-prep workflow) and keep a three-line pointer. The three PC-* invariants belong in `.claude/standards/` next to `manifest-changes.md`.
- **settings-and-permissions.md (2.6 KB) and loop-recipes.md (1.7 KB):** pure reference; move to `.claude/standards/`. The `/loop` skill can cite the recipes file.
- **CLAUDE.md (13.0 KB, ~340 lines):** apply the official pruning test ("would removing this line cause mistakes?"). Candidates for relocation: the repository-structure tree (Claude can read the tree), the compact-instructions section (keep, it is load-bearing), the project-context grep ritual (fold into a doc-writing skill), and the model-selection table (move detail to supervisor standard, keep the four-row summary).

Net effect: always-on context drops from about 15,200 to roughly 6,000 to 7,000 tokens, with no rule deleted, only relocated to load at the moment it applies. Use the `InstructionsLoaded` hook (new; reports `file_path`, `memory_type`, `load_reason`) to verify post-change what actually loads per session.

### 2.2 task-observer adds about 18,000 tokens to every task session

`task-observer/SKILL.md` is 72,230 bytes (1,496 lines), the largest file in the config, and CLAUDE.md mandates invoking it at the start of every task-oriented session. The official skill guidance caps SKILL.md at 500 lines and says to move detail to reference files loaded on demand. Restructure:

- Keep in SKILL.md: the observation format, logging protocol with collision checks, and surfacing rules (roughly 300 lines).
- Move to reference files read only when triggered: the comprehensive-review procedure, the five confidentiality layers, delivery and archival mechanics, environment-compatibility notes, and the licensing catalog (roughly 1,200 lines).
- The upstream skill is vendored from `one-skill-to-rule-them-all`; carry the restructure as a local overlay or upstream PR rather than a fork drift.

This one change recovers about 14,000 tokens per session. Combined with 2.1, a typical session starts near 10,000 tokens of config instead of 33,000.

### 2.3 Convert deterministic "always/never" prose to hooks

Official position: prose rules are probabilistic; hooks execute regardless of what the model decides. Every rule moved to a hook can then be shortened or cut from always-on context. The repo already does this well in places (stop-pre-commit-hook, tdd-enforcement, py310-compat, security-guidance). Remaining candidates:

| Prose rule (location) | Hook replacement |
| --- | --- |
| Never commit to main/master/develop (git-workflow.md) | `PreToolUse` on `Bash(git commit*)`: exit 2 if `git branch --show-current` is protected |
| Never force-push protected branches (git-workflow.md) | `PreToolUse` on `Bash(git push*)`: exit 2 on `--force*` to protected refs (currently only an `ask` permission) |
| Sign every commit (CLAUDE.md) | `PreToolUse` on `Bash(git commit*)`: exit 2 if `commit.gpgsign` unset |
| Worktrees only at `.worktrees/` (CLAUDE.md) | `PreToolUse` on `Bash(git worktree add*)`: exit 2 on paths outside project |
| No em-dash in any output (writing.md) | Already enforced at commit (PC-011); add `PostToolUse` on Write/Edit to catch non-committed artifacts |

Use the hook `if` field for surgical matching so the catch-all cost stays near zero.

### 2.4 Skill and agent listing budget

Skill descriptions share a listing budget (default 1 percent of context; per-skill cap 1,536 characters combined with `when_to_use`; least-used descriptions truncate first). With 30 skill directories and 46 agents:

- The `task-observer` and `writing` descriptions are far past the point of diminishing returns; tighten to trigger conditions only.
- Ten agent descriptions exceed 320 characters (worst: `cleanup-backlog-scout` at 728). Long descriptions crowd the routing budget and dilute auto-delegation for everything else.
- Mark side-effect workflow skills (`close`, `close-clean`, `compliance-rollup`, `compliance-synthesis` once migrated per 3.2) with `disable-model-invocation: true` so they cannot auto-fire and stop consuming description budget.
- Run `/doctor` to check current overflow status; consider `skillListingBudgetFraction` only if trimming is insufficient.

## Priority 3: Adopt current platform features

### 3.1 Retire the homegrown MCP tier-loading design

The Tier 2/3 architecture in `mcp/mcp_config.yaml` and ADR-003 was never wired up: `mcp-tool-loader.sh` is called by no hook, and `keyword-tool-trigger.sh` only logs suggestions because servers cannot be hot-loaded mid-session. The platform now provides the real mechanism:

- **Per-subagent `mcpServers` frontmatter**: each agent declares exactly the servers it needs (inline or by reference). This implements "Tier 2 agent bundles" natively. Apply to security-auditor (sentry, github), database-operations-agent (postgres), devops-deployment-agent (docker, sentry), test-engineer (playwright), documentation-writer (mermaid).
- **Skill `allowed-tools`**: already used by four skills; extend to the skill bundles described in mcp-strategy.md.

Then delete the dead loader scripts, mark ADR-003 superseded, and resolve finding 1.4 by defining servers where agents actually reference them.

### 3.2 Migrate `.claude/commands/` to skills

Commands are a legacy mechanism ("custom commands have been merged into skills", code.claude.com/docs/en/skills). The five local commands (`close`, `close-clean`, `aggregate-observations`, `compliance-rollup`, `compliance-synthesis`) should become skills to gain `context: fork` (run wind-down work in an isolated context), `disable-model-invocation`, and skill-scoped hooks. The command-invokes-agent pattern (compliance-synthesis) maps cleanly to a skill with `context: fork` and `agent: compliance-synthesis`.

### 3.3 Execute or drop the Pattern A pilot

supervisor.md approved preloading skills into security-auditor and owasp-dispatch via `skills:` frontmatter on 2026-04-11; two months later nothing uses it. The field is now stable and also accepts agent `memory:`. Either run the pilot (the owasp rule sets are the ideal preload payload) or remove the section from supervisor.md.

### 3.4 Package the repo as a plugin marketplace

The symlink install (`setup.sh`) plus eight submodules is the pre-plugin-era solution to distribution. A `.claude-plugin/marketplace.json` in this repo would give: versioned installs pinned to SHAs, one-command machine setup (`/plugin marketplace add`), namespaced skills, native bundling of hooks and MCP config, and elimination of the machine-specific paths in finding 1.3. Suggested split: a `core` plugin (rules-as-skills, hooks, key agents), a `compliance` plugin (auditor family plus manifest), and a `writing` plugin (pipeline agents, replacing the reference-library symlinks). The submodules that are pure upstream consumption (anthropics-skills, superpowers) can be installed from their own marketplaces instead of vendored. This is the largest structural change recommended here; stage it after Priorities 1 and 2.

### 3.5 Use current subagent frontmatter in the agent fleet

45 of 46 agents are `model: sonnet`, 1 is opus, 0 are haiku, despite CLAUDE.md's own table routing read-only exploration to Haiku. Fleet-wide pass:

- `model: haiku` for read-only scanners and reference-heavy auditors where reasoning depth is low (cleanup-backlog-scout, ossf-criteria lookups, parts of the compliance family). Measure with `/usage-report agents` before and after.
- `maxTurns` caps on auditors that occasionally wander.
- `isolation: worktree` in frontmatter for remediation agents (openapi-code-enricher already gets a worktree from its orchestrator; the frontmatter form is self-serve).
- `memory: project` for compliance agents that currently re-derive fleet state each run (compliance-synthesis reads the master log every time; persistent agent memory is the native fit).
- `background: true` for long-running audit agents dispatched from interactive sessions.

### 3.6 Settings modernization

- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: "80"` is the old percentage knob. The current recommendation is an absolute window (`CLAUDE_CODE_AUTO_COMPACT_WINDOW`, commonly 400000) because context rot is a function of absolute tokens, not percentage. Verify the variable name against the current settings schema before switching.
- Consider `effortLevel` defaults: `xhigh` for architecture and security review agents via per-agent `effort:` frontmatter, low effort for Explore-pattern work.
- `sandbox.enabled: false` is documented as deliberate for trusted local work, but unattended `/loop` runs are exactly where sandbox plus auto-allow is the right posture. Add a sandbox-on requirement to loop-recipes safeguards.
- Evaluate `/schedule` (cloud-persistent recurring jobs) as a replacement for the `/loop 6h /doc-audit` recipe; unverified against official docs as of this audit, so confirm it exists before documenting.
- Add LSP plugins (official marketplace) for Python and TypeScript to the setup path; diagnostics-aware editing measurably reduces lint round-trips.

## Priority 4: Drift and contradictions

Doc-only fixes, cheap and mechanical:

1. **zen/pal consensus replacement not propagated.** The `/consensus` skill (merged 2026-06-11, PR #204) replaces the zen consensus tools, but `mcp-strategy.md` (Tier 1 table, line ~37 guidance, `/git` and `/project-planning` bundles), `supervisor.md` (auto-loaded tool annotations), and `docs/development/agent-teams-pilot.md` (decision table) still route to `zen.tiered_consensus` and friends. One sweep, about six files.
2. **Copilot review: advisory or blocking?** `pre-commit.md` production checklist says "address comments before merging"; `git-workflow.md` says "advisory comments only; not yet a merge blocker (see Phase 3.5)". Phase 3.5 was a two-week evaluation that ended in May. Decide, then make both files say the same thing.
3. **Model version drift.** `claude-docs-auditor.md:44` says Opus 4.7; CLAUDE.md says Opus 4.8. The auditor checks CLAUDE.md for a living, so this one is self-undermining. Consider making the CLAUDE.md table the single source and having the auditor reference it by path.
4. **Catalog gaps.** Six pr-review-toolkit agents used by `/pr-review` are absent from AGENTS-AND-SKILLS.md; ADR-004 says "43 agents" twice (actual: 46); submodule-backed entries are not distinguishable from local ones. The `catalog-refresh.yml` workflow exists; extend it to count agents and diff the catalog so this class of drift fails CI instead of accumulating.
5. **README points to `docs/ADRs/` (templates only) as the ADR home** while real ADRs live in `docs/architecture/adr/`; `docs/planning/adr/` is a third, empty location. Collapse to one.
6. **X/Twitter posts as canonical sources** for active rules (PR-size thresholds, forking guidance, skills adoption). Archive the content of each cited post into `docs/reference/` and cite the archive; keep the URL as provenance.
7. **Stale plans.** The Renovate v43 plan remains `status: draft` four months past the v42 EOL it cites; agent-teams-pilot.md cites a billing change dated 2026-06-15 as future, which is now three days out. Sweep `docs/superpowers/plans/` for plans that completed or expired.

## Priority 5: Consolidation

Lower urgency; bundle with adjacent work.

- **OSSF pair:** `ossf-compliance-auditor.md` (838 lines) and `ossf-badge-evaluator.md` (406 lines) overlap heavily. Extract the shared criterion logic into one standard (alongside the relocated `ossf-criteria-reference`) and slim both agents to their distinct verbs (audit-and-remediate vs evaluate-and-prefill).
- **Testing triad routing:** supervisor.md lists both test-engineer and test-writer for generation with no dispatch rule. Add one line: test-writer for coverage-driven generation loops, test-engineer for strategy and infrastructure, test-reviewer for validation.
- **`owasp-agent` naming:** it covers Agentic-Applications AG01-AG10 but reads as the family generic; rename to `owasp-agentic` to prevent misdispatch against `owasp-dispatch`.
- **Parallel filenames in rules/ and standards/:** `git-workflow.md`, `python.md`, `testing.md` exist in both directories at different detail levels. The split is intentional (rule vs specification) but unlabeled; add a one-line header to each rules file naming its standards counterpart, and vice versa.
- **Six agents over 300 lines** (worst: ossf-compliance-auditor at 838, visual-content-generator at 435, diagram-maintenance-agent at 407): move procedural reference into standards files the agent reads on demand. Long agent bodies pay their cost on every invocation.
- **`pipeline-coordinator-reference`** (442 lines, `user-invocable: false`, no executable workflow) belongs in `.claude/standards/` per ADR-004's own rubric.

## Suggested sequencing

| Phase | Scope | Items | Effort |
| --- | --- | --- | --- |
| 1 | Defect fixes | 1.1 to 1.7, 4.3 | Hours; no design decisions |
| 2 | Drift sweep | 4.1, 4.2, 4.4 to 4.7 | Hours; one decision (Copilot blocking) |
| 3 | Context diet | 2.1, 2.2, 2.4, plus 2.3 hooks | One focused session; measure with InstructionsLoaded before and after |
| 4 | Platform adoption | 3.1, 3.2, 3.3, 3.5, 3.6, Priority 5 | Incremental over weeks |
| 5 | Marketplace packaging | 3.4 | Separate project; design doc first |

Phases 1 to 3 are where code-quality impact concentrates: deterministic enforcement replaces probabilistic prose, and the instruction set shrinks to a size the model reliably follows.

## Appendix A: Measured footprint

- Always-on rule load: 60,787 bytes (~15,200 tokens) across CLAUDE.md plus 7 unscoped rules.
- task-observer skill: 72,230 bytes (~18,000 tokens), invoked per task session by CLAUDE.md mandate.
- Largest files under `.claude/`: task-observer SKILL.md (72.2 KB), pr-fix workflow (59.6 KB), standards/testing.md (52.5 KB), pr-review workflow (51.1 KB), ossf-compliance-auditor (44.7 KB).
- Agent fleet: 46 working agents (45 sonnet, 1 opus, 0 haiku, 1 missing frontmatter), 14 broken symlinks in fresh clones.
- Skills: 11 working local skills with SKILL.md, 19 submodule symlinks; frontmatter conventions vary (three different tool-field spellings; 5 of 30 use `user-invocable`; 4 use `version`).
- Hook scripts: roughly 30 scripts in `scripts/` are not referenced by any hook (most are manual utilities; `mcp-tool-loader.sh` is the one that was designed as a hook and never wired).

## Appendix B: Sources

- code.claude.com/docs/en/memory, /skills, /sub-agents, /hooks, /plugins, /plugin-marketplaces, /settings, /sandboxing, /agent-teams, /best-practices (fetched 2026-06-12)
- howborisusesclaudecode.com (Boris Cherny patterns; dynamic workflows, context minimalism, auto-compact window)
- HumanLayer "Writing a good CLAUDE.md"; claudelint.com size-rule analysis
- Repo-internal: ADR-003, ADR-004, standards-manifest.yaml v1.0 (2026-06-04), supervisor.md adoption status (2026-04-11)

## Appendix C: Corrections made during verification

Two subagent findings were corrected before inclusion, recorded here so future audits weigh single-agent negative claims appropriately:

1. The structural inventory reported all nine rules files as loading into every session; direct inspection showed `python.md` and `testing.md` carry `paths:` frontmatter and are correctly scoped. Totals above reflect the corrected set.
2. The inventory flagged `FileChanged` as a nonexistent hook event; the documentation research confirmed it is a current (observe-only) event, so the `env-file-audit.sh` registration was removed from the defect list. Whether an observe-only event suits that script's intent is worth a follow-up check.
