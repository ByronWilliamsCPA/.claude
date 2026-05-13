---
title: "Analysis: Tips Harvest (Boris Cherny + Community)"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Subagent 4 analysis: 76 discrete tips from Boris Cherny and Thariq classified against local skills and agents."
tags:
  - analysis
  - research
  - tooling
---

> **Scope:** Seven tip files from `shanraisshan/claude-code-best-practice/tips/`
> covering Boris Cherny posts (Jan 3 through Mar 30, 2026) plus Thariq's March 17
> skill-construction guide. Total of 76 discrete items extracted and mapped
> against our 41 skills / 29 agents / 7 rules / 7 commands at `/home/byron/dev/.claude`.
>
> **Audience:** Solo practitioner. Prioritization reflects that team-specific
> tips (Slack sync, mobile app, Cowork Dispatch) are deprioritized.

## Files reviewed

| External file | Tip count | Authors |
| --- | --- | --- |
| `tips/claude-boris-13-tips-03-jan-26.md` | 13 | Boris Cherny |
| `tips/claude-boris-10-tips-01-feb-26.md` | 10 | Boris + CC team |
| `tips/claude-boris-12-tips-12-feb-26.md` | 12 | Boris Cherny |
| `tips/claude-boris-2-tips-10-mar-26.md` | 2 | Boris Cherny |
| `tips/claude-thariq-tips-17-mar-26.md` | 22 (9 categories + 9 construction + 4 distribution) | Thariq |
| `tips/claude-boris-2-tips-25-mar-26.md` | 2 | Boris Cherny |
| `tips/claude-boris-15-tips-30-mar-26.md` | 15 | Boris Cherny |
| **Total** | **76** | |

Note: Expected list was 6 files; directory actually contains 7. The extra
file `claude-boris-2-tips-10-mar-26.md` (Code Review + test time compute)
was included.

## All tips extracted

### Boris Jan 3 (13 tips)

| # | Tip (short name) | Classification |
| --- | --- | --- |
| 1 | Run 5 Claudes in parallel across numbered terminal tabs | partially covered |
| 2 | Use `claude.ai/code` for web parallelism, teleport between web and local | gap |
| 3 | Use Opus with thinking for everything | already covered |
| 4 | Share a single `CLAUDE.md` checked into git, iterate weekly | already covered |
| 5 | Tag `@claude` on PRs to amend `CLAUDE.md` during review | gap |
| 6 | Start most sessions in Plan mode (shift+tab twice) | partially covered |
| 7 | Use slash commands for inner-loop workflows | already covered |
| 8 | Use subagents to automate common workflows | already covered |
| 9 | PostToolUse hook to auto-format code | already covered |
| 10 | Pre-allow permissions in `/permissions`, not `--dangerously-skip-permissions` | already covered |
| 11 | Let Claude use Slack/BigQuery/Sentry via MCP | gap |
| 12 | Verify long-running tasks with Stop hook or ralph-wiggum plugin | partially covered |
| 13 | Give Claude a way to verify its work (feedback loop primacy) | already covered |

### Boris Feb 1 (10 tips)

| # | Tip (short name) | Classification |
| --- | --- | --- |
| 14 | 3-5 parallel worktrees, shell aliases (2a/2b/2c), analysis worktree | partially covered |
| 15 | Start every complex task in Plan mode; second Claude reviews as staff engineer | partially covered |
| 16 | Invest in `CLAUDE.md`: update after every correction | already covered |
| 17 | Commit skills to git: `/techdebt`, Slack+GDrive+Asana sync skill | partially covered |
| 18 | Claude fixes most bugs alone: paste Slack thread, "fix CI", docker logs | partially covered |
| 19 | Level up prompting: challenge Claude, "scrap and reimplement", detailed specs | already covered |
| 20 | Terminal setup: Ghostty, `/statusline`, tmux, voice dictation | gap |
| 21 | Subagents: "use subagents" suffix, offload for context hygiene, route perms via hook | partially covered |
| 22 | `bq` CLI + BigQuery skill for analytics | gap |
| 23 | Learning: Explanatory/Learning output style, HTML presentations, ASCII diagrams, spaced repetition | gap |

### Boris Feb 12 (12 customization tips)

| # | Tip (short name) | Classification |
| --- | --- | --- |
| 24 | `/config` terminal theme, notifications, `/terminal-setup`, `/vim` | gap |
| 25 | `/model` effort level (low/medium/high, Boris prefers high) | gap |
| 26 | `/plugin` to install LSPs, MCPs, skills, agents, hooks | partially covered |
| 27 | Custom agents in `.claude/agents/`, `--agent` flag, default via settings.json | already covered |
| 28 | `/permissions` with wildcard syntax `Bash(bun run *)` | already covered |
| 29 | `/sandbox` file and network isolation | gap |
| 30 | `/statusline` for model/directory/context/cost | gap |
| 31 | `/keybindings` with live reload | gap |
| 32 | Hooks to route permissions to Slack, nudge Claude, pre/post-process | partially covered |
| 33 | Customize spinner verbs | gap (trivial) |
| 34 | Output styles: Explanatory, Learning, Custom | gap |
| 35 | Customize everything via `settings.json` checked into git | already covered |

### Boris Mar 10 (2 tips)

| # | Tip (short name) | Classification |
| --- | --- | --- |
| 36 | Code Review product: team of agents runs deep review on every PR | partially covered |
| 37 | Test time compute: multiple uncorrelated context windows catch bugs | already covered |

### Boris Mar 25 (2 tips)

| # | Tip (short name) | Classification |
| --- | --- | --- |
| 38 | Always squash merge (141 PRs/day, clean history, easy revert) | already covered |
| 39 | PR size distribution: p50=118 lines, p90=498, p99=2978 | partially covered |

### Boris Mar 30 (15 tips)

| # | Tip (short name) | Classification |
| --- | --- | --- |
| 40 | Claude Code mobile app (iOS/Android Code tab) | gap (low priority solo) |
| 41 | `/teleport` and `/remote-control` between mobile/web/desktop/terminal | gap (low priority solo) |
| 42 | `/loop` and `/schedule` for recurring automation | gap |
| 43 | Hooks: SessionStart dynamic context, PreToolUse logging, Stop nudging | partially covered |
| 44 | Cowork Dispatch (remote control for Claude Desktop app) | gap (low priority solo) |
| 45 | Chrome extension for frontend iteration feedback loop | gap |
| 46 | Claude Desktop app auto-starts and tests web servers | gap |
| 47 | Fork session via `/branch` or `claude --resume <id> --fork-session` | gap |
| 48 | `/btw` for side queries while agent is working | gap |
| 49 | `claude -w` for worktree-backed sessions | already covered |
| 50 | `/batch` to fan out massive changesets across dozens of worktrees | gap |
| 51 | `--bare` flag: skip auto-loading, 10x faster SDK startup | gap |
| 52 | `--add-dir` / `additionalDirectories` for multi-repo access | gap |
| 53 | `--agent` flag for custom system prompt and restricted tools | already covered |
| 54 | `/voice` for voice input | gap |

### Thariq Mar 17 (22 items)

| # | Tip (short name) | Classification |
| --- | --- | --- |
| T1 | Library & API Reference skill category | partially covered |
| T2 | Product Verification skill category (Playwright/tmux paired) | already covered |
| T3 | Data Fetching & Analysis skill category | gap |
| T4 | Business Process & Team Automation skill category | partially covered |
| T5 | Code Scaffolding & Templates skill category | already covered |
| T6 | Code Quality & Review skill category | already covered |
| T7 | CI/CD & Deployment skill category | already covered |
| T8 | Runbook skill category (symptom to investigation to report) | gap |
| T9 | Infrastructure Operations skill category | gap |
| T10 | Don't state the obvious: push Claude out of default thinking | partially covered |
| T11 | Build a Gotchas section: highest-signal content | partially covered |
| T12 | Use file system as progressive disclosure, not single markdown | partially covered |
| T13 | Avoid railroading: give goals + constraints, not step-by-step | partially covered |
| T14 | Think through setup: `config.json` + AskUserQuestion tool | gap |
| T15 | Description field is a trigger specification, not a summary | already covered |
| T16 | Memory via `${CLAUDE_PLUGIN_DATA}` stable storage path | gap |
| T17 | Store scripts and libraries so Claude composes rather than reconstructs | partially covered |
| T18 | On-demand hooks activated only when skill invoked (`/careful`, `/freeze`) | gap |
| T19 | Distribution: check into repo vs plugin marketplace | already covered |
| T20 | Marketplace management: organic curation, sandbox then promote | not applicable (solo) |
| T21 | Compose skills by reference, model invokes if installed | partially covered |
| T22 | Measure skills with PreToolUse log hook | gap |

## Gap analysis (ranked high to low for a solo practitioner)

### HIGH priority

#### Gap 1: SessionStart hook for dynamic context injection
- **Tip:** Use a `SessionStart` hook to evaluate the active branch or modified
  files and load only the relevant rule file from `.claude/rules/` into context.
- **Why it matters:** We have `git-workflow.md`, `mcp-strategy.md`,
  `pre-commit.md`, `python.md`, `supervisor.md`, `testing.md`, `writing.md` but
  rely on the model fetching the right one. A SessionStart hook can detect
  modified paths and inject exactly the needed rules, trimming context waste.
- **Where it would land:** New hook entry in `.claude/settings.json` +
  `scripts/session-start-context.sh`.
- **Effort:** M
- **Priority:** high

#### Gap 2: Fork session via `/branch` and `--fork-session`
- **Tip:** `/branch` or `claude --resume <id> --fork-session` branches the
  current conversation. You can explore a destructive refactor in the fork and
  discard it, returning to the parent session unchanged.
- **Why it matters:** Solo developers are the bottleneck for context switching.
  Forking is cheaper than worktrees for speculative exploration and preserves
  the parent's cache.
- **Where it would land:** New entry in `.claude/rules/git-workflow.md` or a
  new `fork-session` playbook note.
- **Effort:** S (documentation only)
- **Priority:** high

#### Gap 3: `/loop` and `/schedule` for babysit-style automation
- **Tip:** `/loop 5m /ci-fix` or `/loop 30m /doc-audit` runs a skill on interval
  for up to a week. Boris uses it for auto-rebase, PR pruning, and
  post-merge sweeping.
- **Why it matters:** Our `ci-fix`, `doc-audit`, `sonarcloud` skills are
  perfect loop candidates. Running `doc-audit` overnight surfaces drift
  without manual invocation.
- **Where it would land:** New section in `CLAUDE.md` or
  `.claude/rules/loop-recipes.md`; no code changes needed.
- **Effort:** S
- **Priority:** high
- **Note on Gemini pushback:** Gemini argued `/loop` is lower value for solo
  work. I disagree for our specific case: our doc and CI skills drift
  continuously and the loop runs as background watcher, not polling. Worth a
  trial, not a full commitment.

#### Gap 4: On-demand hooks inside skills (T18: `/careful`, `/freeze` pattern)
- **Tip:** Skills can register hooks that are active only for the session in
  which the skill is invoked. Example: `/freeze` blocks edits outside the
  current branch directory; `/careful` blocks `rm -rf`, `DROP TABLE`,
  force-push via PreToolUse Bash matcher.
- **Why it matters:** Different from global hooks. Lets a skill temporarily
  tighten guardrails without bloating `settings.json`. Pairs well with our RAD
  framework: a `/rad-strict` on-demand hook could inject verification
  requirements only when RAD tagging is active.
- **Where it would land:** New skill convention documented in
  `.claude/skills/writing-skills/` or `.claude/rules/hook-patterns.md`.
- **Effort:** M
- **Priority:** high

#### Gap 5: `--bare` flag for SDK / non-interactive startup
- **Tip:** `claude -p "..." --bare` skips the auto-scan for local `CLAUDE.md`,
  settings, and MCPs. Up to 10x faster startup.
- **Why it matters:** Our `ci-fix` and doc audit hooks already invoke
  `claude -p` style calls. If we move toward cron-backed automation
  (see Gap 3), `--bare` reduces cold-start cost.
- **Where it would land:** `.claude/scripts/*.sh` that shell out to `claude -p`.
- **Effort:** S
- **Priority:** high

### MEDIUM priority

#### Gap 6: `${CLAUDE_PLUGIN_DATA}` stable storage for skill memory
- **Tip:** Skills can persist state across sessions via
  `${CLAUDE_PLUGIN_DATA}`. Anthropic uses it for append-only logs, JSON
  caches, SQLite.
- **Why it matters:** Our `silent-failure-hunter`, `test-coverage`, and
  `debug-tests` skills rediscover the same patterns every run. Stateful
  memory would let them track flaky tests, coverage trends, and repeated
  bug sites.
- **Where it would land:** Update three to five existing skills to write to
  `${CLAUDE_PLUGIN_DATA}/<skill>/history.jsonl`.
- **Effort:** M
- **Priority:** medium

#### Gap 7: Data Fetching / Runbook / Infra Ops skill categories (T3, T8, T9)
- **Tip:** Thariq's taxonomy shows three categories we have zero coverage in.
  Runbooks take a symptom (Slack thread, alert, error signature), walk a
  multi-tool investigation, and produce a structured report.
- **Why it matters:** Our `debug-tests` and `systematic-debugging` skills
  operate locally on code. We have no skill that ingests external
  operational state (logs, metrics, alerts) and triages. For a solo dev
  running services, this is a real gap.
- **Where it would land:** New skill directory
  `.claude/skills/runbook-template/` with a config-driven starter. Optional
  Data Fetching skill once we identify a target system.
- **Effort:** M
- **Priority:** medium (depends on whether we operate services)

#### Gap 8: Progressive disclosure audit across existing 41 skills (T12)
- **Tip:** A skill is a folder, not just a markdown file. Claude should read
  `references/` and `examples/` on demand, not eagerly.
- **Why it matters:** Gemini flagged this as "implicit but not verified." We
  need a pass across our 41 skills to ensure SKILL.md files are thin and
  heavy content lives in sibling files the model loads when needed. Context
  budget is real.
- **Where it would land:** Audit script + updates to any skill found
  dumping large reference blocks.
- **Effort:** L
- **Priority:** medium

#### Gap 9: Gotchas sections across existing skills (T11)
- **Tip:** Build up a Gotchas section in every skill from common failure
  points. Highest-signal content.
- **Why it matters:** We likely have partial coverage. Systematic audit
  would surface which skills lack this.
- **Where it would land:** Pair with Gap 8 audit.
- **Effort:** M
- **Priority:** medium

#### Gap 10: Second Claude as staff-engineer plan reviewer (tip 15)
- **Tip:** One Claude writes the plan, a second Claude reviews it as a staff
  engineer before switching to auto-accept mode.
- **Why it matters:** Our `plan-validator` agent is close but the pattern of
  "spin up a fresh session specifically to review the plan" is a workflow
  primitive we should document, not a new tool.
- **Where it would land:** `.claude/skills/writing-plans/` or
  `.claude/skills/executing-plans/`: add a two-session review pattern.
- **Effort:** S
- **Priority:** medium

#### Gap 11: Skill usage measurement via PreToolUse log (T22)
- **Tip:** PreToolUse hook logs every skill invocation so you can see
  which are popular and which are undertriggered.
- **Why it matters:** With 41 skills, we don't know which are unused. A
  simple append-only log of skill names and timestamps would surface
  dead weight for pruning.
- **Where it would land:** New PreToolUse hook + `scripts/log-skill.sh`
  writing to `$HOME/.claude/logs/skill-usage.jsonl`.
- **Effort:** S
- **Priority:** medium

#### Gap 12: `--add-dir` / `additionalDirectories` for multi-repo work
- **Tip:** When working across repos, start Claude in one and use `--add-dir`
  to give it visibility plus permissions on siblings.
- **Why it matters:** We often touch `.claude/` globals while in a project
  repo. `additionalDirectories` in project `settings.json` would make this
  work without manual steps.
- **Where it would land:** Template update for project-level
  `settings.json` examples.
- **Effort:** S
- **Priority:** medium

### LOW priority

#### Gap 13: Output styles (Explanatory / Learning)
- **Tip:** `/config` sets an output style. Explanatory explains the why.
  Learning coaches you through changes.
- **Why it matters:** Nice for onboarding unfamiliar codebases. Not
  critical for daily work.
- **Effort:** S
- **Priority:** low

#### Gap 14: `/sandbox` file and network isolation
- **Tip:** Claude Code ships a sandbox runtime with file and network
  isolation.
- **Why it matters:** Would reduce permission prompts and offer defense in
  depth. But adds complexity to a working setup.
- **Effort:** M
- **Priority:** low

#### Gap 15: `/btw` for side queries
- **Tip:** Ask a quick side question without interrupting the agent.
- **Why it matters:** Minor quality-of-life improvement.
- **Effort:** S (no setup required, just habit)
- **Priority:** low

#### Gap 16: `/statusline`, spinner verbs, keybindings, terminal theme
- **Tip:** Purely cosmetic customization (tips 24, 30, 31, 33).
- **Why it matters:** Zero effect on code quality.
- **Effort:** S
- **Priority:** low (skip unless craving)

#### Gap 17: Chrome extension for frontend feedback loop
- **Tip:** Give Claude a browser so it can iterate on frontend code with
  visual feedback.
- **Why it matters:** Our `frontend-design` skill has no visual feedback
  loop. For rare frontend work this matters; for us it's situational.
- **Effort:** M
- **Priority:** low (unless frontend work picks up)

### Tips classified as NOT APPLICABLE or NOT WORTH IT for solo

- Slack + GDrive + Asana + GitHub 7-day context sync (tip 17 sub): no team
  systems to sync.
- Tag `@claude` on PRs for Compounding Engineering (tip 5): our PRs are
  solo; we'd be tagging ourselves.
- Mobile app, teleport, Cowork Dispatch (tips 40, 41, 44): solo laptop
  workflow doesn't need remote delegation.
- `/batch` for dozens of worktree agents (tip 50): scale mismatch.
- Voice dictation (tips 20, 54): personal preference, not a process gap.
- Marketplace curation (T20): we share skills via the single `.claude`
  repo, not via a marketplace.

## Tips we cover better

- **CLAUDE.md iteration (tip 4, 16):** We have a `claude-md-improver` skill
  that audits CLAUDE.md files against templates and updates them. Boris's
  advice is "edit it after every correction"; we have a dedicated skill.
- **Slash commands for inner loop (tip 7):** Our `ci-fix`, `quality`,
  `testing`, `security`, `sonarcloud`, `git` skills are exactly
  inner-loop workflows plus CI safety nets.
- **Subagent workflow automation (tip 8):** 29 agents with role separation
  including `code-simplifier`, `plan-validator`, `silent-failure-hunter`,
  `test-writer`, `test-engineer`, `security-auditor` exceeds what Boris
  describes in the tips.
- **Feedback loop / test verification (tips 12, 13):** We pair
  `verification-before-completion` + `test-driven-development` +
  `systematic-debugging` + RAD tagging, which is stricter than Boris's
  "give Claude a way to verify."
- **PostToolUse formatting (tip 9):** Our hooks run ruff auto-fix,
  shellcheck, Python 3.10 compatibility check, and pre-commit. Boris's
  example was a single `bun run format` call.
- **Squash merge policy (tip 38):** Already in `.claude/rules/git-workflow.md`.
- **Pre-allow permissions (tip 10, 28):** `.claude/settings.json` already
  maintains allowlists.
- **Plan mode primitives (tips 6, 15):** `brainstorming`, `writing-plans`,
  `executing-plans`, `project-planning`, `plan-validator` cover this more
  explicitly than shift+tab twice.
- **Challenging Claude / review prompting (tip 19):** Our
  `receiving-code-review` and `requesting-code-review` skills codify
  this as a process, not ad-hoc advice.
- **Skill description = trigger (T15):** Our `writing-skills` skill
  enforces this for new skill creation.
- **Squash + PR size discipline (tips 38, 39):** `git-workflow.md`
  handles squash. We don't enforce a 118-line median but our general
  small-PR preference is compatible.
- **Custom agents pattern (tip 27):** 29 agents already in
  `.claude/agents/` plus SKILL.md infrastructure.

## Recommendations

### Recommendation 1: SessionStart hook for dynamic rule loading
- **What:** Add a `SessionStart` hook to `.claude/settings.json` that
  detects git branch, modified paths, and project type, then injects the
  relevant subset of `.claude/rules/*.md` into the session.
- **Why:** We have seven rule files but rely on the model to find them.
  Deterministic injection cuts context waste and ensures the right
  constraint is always active.
- **Target files:** `.claude/settings.json`,
  `.claude/scripts/session-start-rules.sh` (new),
  `.claude/rules/session-start-strategy.md` (new).
- **Effort:** M
- **Priority:** high
- **Source citation:** Boris Mar 30 2026 tip 4 (hooks for SessionStart),
  [x.com/bcherny/status/2038454343519932844](https://x.com/bcherny/status/2038454343519932844)

### Recommendation 2: Document `/branch` and `--fork-session` in git-workflow rules
- **What:** Add a section to `.claude/rules/git-workflow.md` documenting
  when to fork a session versus creating a worktree. Forks preserve parent
  cache; worktrees isolate filesystem.
- **Why:** Zero-implementation-cost capability already in Claude Code.
  Solo practitioners benefit most from cheap speculation.
- **Target files:** `.claude/rules/git-workflow.md`.
- **Effort:** S
- **Priority:** high
- **Source citation:** Boris Mar 30 2026 tip 8,
  [x.com/bcherny/status/2038454350214041740](https://x.com/bcherny/status/2038454350214041740)

### Recommendation 3: Trial `/loop` on doc-audit and sonarcloud
- **What:** Document two loop recipes: `/loop 6h /doc-audit` for weekly
  drift tracking, `/loop 30m /sonarcloud` for PR review watchdog. Run
  each for 48 hours and measure signal-to-noise.
- **Why:** Our `doc-audit` and `sonarcloud` skills are idempotent and
  produce useful state on every run. The 7-day auto-expiry on loops
  means the experiment is self-terminating.
- **Target files:** `.claude/rules/loop-recipes.md` (new).
- **Effort:** S
- **Priority:** high
- **Source citation:** Boris Mar 30 2026 tip 3,
  [x.com/bcherny/status/2038454341884154269](https://x.com/bcherny/status/2038454341884154269)

### Recommendation 4: On-demand hooks convention for skills
- **What:** Document a convention for skill-scoped PreToolUse hooks.
  Concrete first example: `/rad-strict` that blocks any `Bash` command
  matching `git commit` until `#VERIFY` annotations are present.
- **Why:** Lets us tighten guardrails for specific workflows without
  bloating global settings.
- **Target files:** `.claude/skills/writing-skills/SKILL.md` (update),
  `.claude/skills/rad/` (reference implementation).
- **Effort:** M
- **Priority:** high
- **Source citation:** Thariq Mar 17 2026 tip 9,
  [x.com/trq212/status/2033949937936085378](https://x.com/trq212/status/2033949937936085378)

### Recommendation 5: Audit existing skills for progressive disclosure + Gotchas
- **What:** Run `skill-creator` or a one-off audit against each of the 41
  skills. Verify SKILL.md is under ~200 lines, heavy reference material
  lives in sibling files, and every skill has a Gotchas section with at
  least three entries. Update skills that fail.
- **Why:** Context budget is real. Thariq is explicit that the file system
  is the vehicle for progressive disclosure. We should not assume this is
  fine without measurement.
- **Target files:** Audit across `.claude/skills/*/SKILL.md`.
- **Effort:** L
- **Priority:** medium
- **Source citation:** Thariq Mar 17 2026 tips 11 and 12,
  [x.com/trq212/status/2033949937936085378](https://x.com/trq212/status/2033949937936085378)

### Recommendation 6: `${CLAUDE_PLUGIN_DATA}` memory for detector skills
- **What:** Update `silent-failure-hunter`, `test-coverage`, and
  `debug-tests` to persist findings to
  `${CLAUDE_PLUGIN_DATA}/<skill>/history.jsonl`. On next invocation,
  read history to prioritize known flaky tests or repeat failure sites.
- **Why:** Current state: each run rediscovers the same patterns. With
  stable memory they become smarter over time.
- **Target files:** `.claude/skills/silent-failure-hunter/SKILL.md`,
  `.claude/skills/test-coverage/SKILL.md`,
  `.claude/skills/debug-tests/SKILL.md`.
- **Effort:** M
- **Priority:** medium
- **Source citation:** Thariq Mar 17 2026 tip 7,
  [x.com/trq212/status/2033949937936085378](https://x.com/trq212/status/2033949937936085378)

### Recommendation 7: Skill usage telemetry via PreToolUse log
- **What:** Add a PreToolUse hook that logs skill invocations to
  `$HOME/.claude/logs/skill-usage.jsonl`. Review monthly and prune skills
  with zero use after 90 days.
- **Why:** With 41 skills we don't know which are dead weight. Telemetry
  is cheap and data-driven pruning reduces context dump and cognitive load.
- **Target files:** `.claude/settings.json`,
  `.claude/scripts/log-skill-usage.sh` (new).
- **Effort:** S
- **Priority:** medium
- **Source citation:** Thariq Mar 17 2026, measurement section,
  [x.com/trq212/status/2033949937936085378](https://x.com/trq212/status/2033949937936085378)

### Recommendation 8: Runbook skill template for operational procedures
- **What:** Create `.claude/skills/runbook-template/` that scaffolds a
  symptom-to-investigation-to-report flow. Concrete first instance:
  `runbook-preflight` that validates GPG, SSH, pip-audit, uv lock state
  before release.
- **Why:** Thariq's taxonomy surfaces Runbook as a distinct category.
  Our `systematic-debugging` is closest but is code-focused. Runbooks
  should codify checklists that currently live in our heads.
- **Target files:** `.claude/skills/runbook-template/` (new directory).
- **Effort:** M
- **Priority:** medium
- **Source citation:** Thariq Mar 17 2026 category 8,
  [x.com/trq212/status/2033949937936085378](https://x.com/trq212/status/2033949937936085378)

### Recommendation 9: Add `--bare` to any SDK-style invocations
- **What:** Audit our `.claude/scripts/` for any `claude -p` shell-outs
  and add `--bare` flag plus explicit `--system-prompt`, `--settings`,
  `--mcp-config` where needed. Document as the default for new scripts.
- **Why:** 10x cold-start improvement. Free win.
- **Target files:** `.claude/scripts/*.sh` (audit), rules documentation.
- **Effort:** S
- **Priority:** high
- **Source citation:** Boris Mar 30 2026 tip 12,
  [x.com/bcherny/status/2038454357088457168](https://x.com/bcherny/status/2038454357088457168)

### Recommendation 10: Stop hook for deterministic verification
- **What:** Add a `Stop` hook that runs `ci-fix` or at minimum a
  `pre-commit run --files <touched>` pass before exit. Prevents
  "forgot to run tests" failures that rely on the model remembering.
- **Why:** Gemini's pushback on classifying our `verification-before-completion`
  skill as covering tip 12 is correct: skills require model compliance,
  hooks run unconditionally. The Stop hook closes that gap.
- **Target files:** `.claude/settings.json`,
  `.claude/scripts/stop-verification.sh` (new).
- **Effort:** M
- **Priority:** high
- **Source citation:** Boris Jan 3 2026 tip 12 and Mar 30 tip 4,
  [x.com/bcherny/status/2007179858435281082](https://x.com/bcherny/status/2007179858435281082)

## Gemini review pass (summary)

- Gemini corrected me on three "already covered" classifications: the
  Stop hook tip (we rely on skill-based verification, which is non-deterministic),
  progressive disclosure (we assumed coverage without verifying), and
  parallel worktree usage (we have the skill but probably don't actually
  run concurrent sessions in practice).
- Gemini pushed back on ranking `/loop` and `/schedule` as high impact
  for a solo dev, arguing they introduce background state complexity.
  I partially accepted (moved to medium) but kept a narrow experiment
  in Recommendation 3 since our `doc-audit` and `sonarcloud` skills
  are specifically idempotent.
- Gemini surfaced three skill-taxonomy gaps (Data Fetching, Runbook,
  Infra Ops) that I had marked as covered by `debug-tests` and
  `systematic-debugging`. Gemini's distinction: runbook skills codify
  operational procedures (deploy, rollback, rotate credentials),
  not debugging sessions. Accepted into Recommendation 8.
- Gemini reinforced `--fork-session` (Recommendation 2),
  `${CLAUDE_PLUGIN_DATA}` (Recommendation 6), and on-demand hooks
  (Recommendation 4) as highest value for solo work. Accepted.
- Gemini recommended avoiding new procedural agents and focusing on
  context branching plus stateful data sharing between existing agents.
  This shaped the final ordering: recommendations lean on extending
  existing skills rather than creating new ones.

## Authoritative citations found

- Boris Cherny, Jan 3 2026 (13 tips thread):
  [x.com/bcherny/status/2007179832300581177](https://x.com/bcherny/status/2007179832300581177)
- Boris Cherny, Feb 1 2026 (10 team tips thread):
  [x.com/bcherny/status/2017742741636321619](https://x.com/bcherny/status/2017742741636321619)
- Boris Cherny, Feb 12 2026 (12 customization tips thread):
  [x.com/bcherny/status/2021699851499798911](https://x.com/bcherny/status/2021699851499798911)
- Boris Cherny, Mar 10 2026 (Code Review + test time compute):
  [x.com/bcherny/status/2031089411820228645](https://x.com/bcherny/status/2031089411820228645),
  [x.com/bcherny/status/2031151689219321886](https://x.com/bcherny/status/2031151689219321886)
- Boris Cherny, Mar 25 2026 (squash merge + PR size):
  [x.com/bcherny/status/2038552880018538749](https://x.com/bcherny/status/2038552880018538749)
- Boris Cherny, Mar 30 2026 (15 hidden features):
  [x.com/bcherny/status/2038454336355999749](https://x.com/bcherny/status/2038454336355999749)
- Thariq, Mar 17 2026 (How we use skills at Anthropic):
  [x.com/trq212/status/2033949937936085378](https://x.com/trq212/status/2033949937936085378)
- Claude Code terminal setup docs:
  [code.claude.com/docs/en/terminal](https://code.claude.com/docs/en/terminal)
- Claude Code plugins docs:
  [code.claude.com/docs/en/discover-plugins](https://code.claude.com/docs/en/discover-plugins)
- Claude Code sub-agents docs:
  [code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents)
- Claude Code permissions docs:
  [code.claude.com/docs/en/permissions](https://code.claude.com/docs/en/permissions)
- Claude Code sandbox docs:
  [code.claude.com/docs/en/sandbox](https://code.claude.com/docs/en/sandbox)
- Claude Code statusline docs:
  [code.claude.com/docs/en/statusline](https://code.claude.com/docs/en/statusline)
- Claude Code keybindings docs:
  [code.claude.com/docs/en/keybindings](https://code.claude.com/docs/en/keybindings)
- Claude Code hooks reference:
  [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks)
- Claude Code output styles docs:
  [code.claude.com/docs/en/output-styles](https://code.claude.com/docs/en/output-styles)
- Claude Code settings docs:
  [code.claude.com/docs/en/settings](https://code.claude.com/docs/en/settings)
- Claude Code skills docs:
  [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)
- Claude GitHub App (install @claude action):
  [github.com/apps/claude](https://github.com/apps/claude)
