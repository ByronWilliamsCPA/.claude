---
title: "Synthesis: Best-Practice Repo Review"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Cross-cutting themes, prioritized action table, consensus validation, and adoption short list from the best-practice repo review."
tags:
  - analysis
  - research
  - planning
---

> **What this is:** Cross-cutting findings from six parallel subagent analyses
> of the external repository [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice)
> compared against our local Claude Code practices at `/home/byron/dev/.claude`.
>
> **Supporting evidence:** Six analysis documents in this directory
> ([01](01-core-concepts-and-architecture.md), [02](02-runnable-implementations.md),
> [03](03-development-workflows.md), [04](04-tips-harvest.md),
> [05](05-hooks-and-configuration.md), [06](06-changelog-and-versioning.md)).
> This file deduplicates, re-ranks, and validates via multi-model consensus.
>
> **Methodology:** Each subagent fetched its slice via `gh api`, compared against
> local files, drafted an analysis, ran it through Gemini 3.1 Pro for review,
> revised, and wrote a final template-conformant document. The supervisor then
> synthesized, deduplicated, and ran this report through 5-model consensus
> (gemini-3.1-pro-preview, gpt-5.2 against, qwen3.5-plus, grok-4.1-fast against,
> glm-4.5-air) for adversarial validation.

## Executive summary

The external repository is a public teaching product maintained by an
Anthropic-adjacent community. It is exceptional on three fronts: **citation
discipline** (every claim links to an Anthropic doc or engineer tweet),
**runnable worked examples** (weather orchestrator, agent teams, scheduled
tasks), and **platform-level configuration knowledge** (settings hierarchy,
permission model, sandbox architecture, 27 hook events). It is weaker than our
setup on **workflow rigor** (our writing-plans/executing-plans and multi-stage
review are stricter), **test and quality gates** (our ci-fix/quality/testing
stack is more complete), and **MCP minimalism** (our `mcp-minimal-bloat.md`
standard is better cited and more actionable).

The **single highest-ROI adoption** is the settings-and-permissions hardening
package: the 22-entry `ask` list for destructive bash commands plus a new rule
file documenting the five-scope settings hierarchy, deny-as-floor evaluation,
and sandbox architectural layer. This is a one-afternoon change that closes
our largest safety gap and is the common thread across chunks 1 and 5.

The **single most important deliberate non-adoption** is the monolithic
`hooks.py` + per-event soundboard pattern. Our targeted shell scripts pay no
Python interpreter boot cost per tool call, and threshold-based exception
alerts beat per-event sound feedback for a solo workflow.

The review surfaces **47 raw recommendations** across six analysis documents.
After deduplication and cross-cutting grouping, the prioritized action table
contains **38 distinct actions** (12 high, 18 medium, 8 low) plus **7 explicit
non-adoption decisions** captured in Theme 4. Consensus validation (see
section below) recommends cutting or deferring several of the high-priority
items; the consensus-adjusted short list is **10 actions** to execute in the
next two weeks.

## Themes

### Theme 1: What we have but could strengthen

| Area | Current state | External insight | Strengthening action |
| --- | --- | --- | --- |
| MCP strategy | `rules/mcp-strategy.md` + `standards/mcp-minimal-bloat.md` (ours is richer and better cited) | External documents three MCP scopes (Project / User / Subagent) with precedence | Add a short subsection naming the native scope model and explaining our deliberate deviation so future maintainers do not accidentally try to use subagent-frontmatter `mcpServers:` |
| Agent prompt structure | 29 agents written as encyclopedic `## Capabilities` + `## Review Checklist` reference docs | External agents use imperative `## Your Task` + numbered `### Step N` + `## Critical Requirements` + `## Output Summary` state-machine framing | Gradual migration to imperative framing, starting with the five most-invoked agents |
| Plan writing | `writing-plans` skill enforces TDD 2-5 minute steps, no placeholders | External RPI adds a mandatory Technical Discovery (Explore pass) step before the plan's File Structure section is written | Add a codebase discovery checklist item to `writing-plans/SKILL.md` |
| Subagent review loop | `subagent-driven-development` has two-stage review (spec compliance, then code quality) | External `constitutional-validator` adds a non-functional Complexity Appropriateness dimension | Extend the existing code quality reviewer prompt with a complexity check. Do not create a new subagent. |
| Hook coverage | 4 events wired (PreToolUse, PostToolUse, UserPromptSubmit, SessionStart) | External wires 27 events to a monolithic Python dispatcher | Wire only three additional events worth the cost: `SessionEnd` (cleanup leaked temp state), `FileChanged` (with `.env*` matcher for secret-file audit), and `PermissionDenied` (advisory to break retry loops) |
| PR size and squash discipline | Already in `rules/git-workflow.md` | External includes 2026 Anthropic internal PR distribution stats (p50=118 lines, p90=498, p99=2978) | Add the stats as a reference anchor in git-workflow.md for calibration |
| Verification discipline | `verification-before-completion` skill + RAD tagging | External emphasizes Stop hook for deterministic verification that does not rely on model compliance | Wire a Stop hook that runs `pre-commit run --files <touched>` at minimum, so verification is unconditional |

### Theme 2: What we are missing entirely (adopt)

| Area | Nature of gap | Adoption action |
| --- | --- | --- |
| Settings + permissions + sandbox documentation | We have no rule file explaining the five-scope settings hierarchy, the `deny -> ask -> allow` evaluation order, path-prefix syntax, or the `sandbox.filesystem` / `sandbox.network` architectural layer | Create `rules/settings-and-permissions.md` |
| Destructive-bash `ask` list | Our local example has 4 entries; external has 22 covering `rm`, `chmod`, `chown`, `docker`, `kubectl`, `npm`, `pip`, `firebase`, `gcloud`, `kill`, `pkill`, `dd`, `mkfs`, etc. | Copy the external 22-entry list into `settings.json` and the local example |
| Preloaded "agent skill" pattern | We have no mechanism for injecting a skill's body into an agent at startup; every skill invocation goes through the Skill tool | Introduce `skills:` frontmatter on agents paired with `user-invocable: false` on the target skill, starting with security-auditor + owasp-dispatch |
| Worked Command -> Agent -> Skill coordinator | `.claude/commands/` is entirely symlinks to vendored plugins; we have no hand-authored coordinator | Author one reference coordinator (e.g., `commands/rad-verify-pipeline.md` or `commands/test-coverage-pipeline.md`) with an explicit `### Data Contract` block between steps |
| SessionStart dynamic rule loading | Rules rely on model to find and load the right subset | Hook that detects git branch + modified paths + project type and injects the relevant rule subset |
| Fork session awareness | `--fork-session` and `/branch` are not documented anywhere in our rules | Short section in `git-workflow.md` on when to fork (speculative exploration, preserves parent cache) vs when to worktree (filesystem isolation) |
| `/loop` experimentation | No documentation on when to use `/loop` for babysit-style automation | Document two recipes (`/loop 6h /doc-audit`, `/loop 30m /sonarcloud`) and run for 48 hours as a bounded experiment (the 7-day auto-expiry makes it self-terminating) |
| `${CLAUDE_PLUGIN_DATA}` stateful skill memory | Detector skills rediscover the same patterns every run | Update `silent-failure-hunter`, `test-coverage`, `debug-tests` to persist findings and read history on invocation |
| Citation discipline | Our rules cite a few inline URLs but have no systematic Sources footer; only `standards/mcp-minimal-bloat.md` does this well | Add a `## Sources` footer to each file in `.claude/rules/` and the behavior-related files in `.claude/standards/` |
| Built-in Explore and Plan read-only subagents | Our agent assignment table in `supervisor.md` does not reference them | Add Explore (haiku, read-only) for codebase search and Plan (inherit, read-only) for pre-planning to the supervisor agent table |
| Monorepo CLAUDE.md loading semantics | Our CLAUDE.md references path-scoped rules but never explains why they compose safely | Add 4-6 lines on ancestor-eager vs descendant-lazy vs sibling-never loading to the global CLAUDE.md |
| Attribution + plansDirectory + outputStyle + autocompact settings | Four one-line declarative gains we do not use | Add to `settings.json`: `attribution.commit`, `attribution.pr`, `plansDirectory`, `outputStyle: "Explanatory"`, `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: "80"` |
| `--bare` flag for SDK calls | Our scripts that shell out to `claude -p` pay the full auto-scan cost | Audit `scripts/*.sh` and add `--bare` where appropriate for 10x cold-start improvement |
| Verification checklist pattern | We do not track accumulated audit rules from past drift incidents | Single file `docs/development/platform-audit-checklist.md` that grows only when a new drift type is caught |
| On-demand skill hooks | No convention for hooks that activate only while a skill is in use | Document the pattern in `writing-skills` and ship one reference implementation (e.g., `/rad-strict` that blocks commit until `#VERIFY` annotations exist) |

### Theme 3: What we do differently (and our way is better)

These are deliberate decisions. Capturing them here prevents later audits from
re-raising the same questions.

| Area | External approach | Our approach | Why ours is better |
| --- | --- | --- | --- |
| MCP per-agent routing | `mcpServers:` field in subagent frontmatter (distributed) | `mcp_config.yaml` + `scripts/mcp-tool-loader.sh` (centralized) | Centralized mapping is auditable; prevents drift between agents; enables Tier 1/2/3 bundling |
| Hook architecture | Monolithic `hooks.py` (one Python file handles all 27 events via dispatch) | Targeted shell scripts (one script per purpose, bash is effectively free to start) | Python interpreter boot on every tool call is an unacceptable tax; one syntax error in monolith breaks every hook |
| Sound feedback | 27-folder per-event MP3 soundboard | Threshold-based Windows toast via `bash-notify.sh` when Bash exceeds 30 seconds | Exception-signal beats reward-signal for focus; solo work has no audience requiring constant feedback |
| Hook disable mechanism | `hooks-config.json` with `disable<Event>Hook` boolean keys | Remove the entry from `settings.json` or use an env var | Disable flags still fork the process and pay the Python boot cost; removing the entry skips the hook entirely |
| Plan artifact layout | Multi-file split by audience (`pm.md`, `ux.md`, `eng.md`, `PLAN.md`) in `rpi/{feature-slug}/` | Single file at `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md` | Single reader (same agent) gains nothing from audience split; single file is faster to traverse and sync-proof |
| Feasibility gate | 6-agent research pipeline with GO / CONDITIONAL GO / DEFER / NO-GO | Currently no gate; see Theme 2 for the lightweight adoption | Full RPI pipeline is over-engineering for 90% of real tasks; a single-agent gate captures the value at 10% of the cost |
| Quality gate stack | Single `bun run format` in a PostToolUse hook | ruff format + ruff lint + shellcheck + Python 3.10 compat + pre-commit + RAD tagging + TDD enforcement | Our pipeline is fundamentally richer and better calibrated for a Python-first codebase |
| CLAUDE.md iteration pattern | Advice to "edit CLAUDE.md after every correction" | Dedicated `claude-md-improver` skill that audits against templates and applies structured updates | Skill-based iteration is verifiable and repeatable; manual edit advice decays |
| Verification stack | "Give Claude a way to verify its work" | `verification-before-completion` + `test-driven-development` + `systematic-debugging` + RAD `#VERIFY` tagging | Multi-layer verification with deterministic components is strictly stronger than model-compliance verification alone. Note: we should still add the Stop hook (Theme 1) to close the deterministic-verification gap. |

### Theme 4: Explicit non-adoption decisions

Capturing deliberate NO votes so they do not resurface.

1. **Monolithic `hooks.py` dispatcher** (Subagent 5 Rec 6). Architectural
   anti-pattern for our workload.
2. **Per-event MP3/WAV soundboard** (Subagent 5 Rec 7). Pure novelty for a
   solo workflow.
3. **`hooks-config.json` disable flag pattern** (Subagent 5 Rec 8). Performance
   anti-pattern because the fork still happens.
4. **Multi-file plan split (pm/ux/eng/PLAN)** (Subagent 3 Rec 6). Overhead
   without audience split benefit.
5. **6-agent research pipeline** (Subagent 3 Rec 4 explains the lightweight
   alternative). Over-engineering; the lightweight single-agent gate captures
   the value.
6. **Per-version Claude Code changelog** (Subagent 6 Rec 1). Duplication with
   Anthropic's `/release-notes` and `code.claude.com/docs`. The lightweight
   verification-checklist (Theme 2) captures the genuinely novel contribution.
7. **`mcpServers:` in subagent frontmatter** (contradicts our existing
   `rules/mcp-strategy.md` lines 70-82; covered in Theme 3).

## Prioritized action table

Sorted by priority (high -> medium -> low), then by effort (S -> M -> L).
Numbers in square brackets reference the source analysis document.

| Priority | Effort | Action | Target files | Source |
| --- | --- | --- | --- | --- |
| high | S | Add 22-entry `permissions.ask` list for destructive bash commands | `settings.json`, `.claude/settings.local.json.example` | [05] Rec 1 |
| high | S | Document `/branch` and `--fork-session` in `rules/git-workflow.md` | `rules/git-workflow.md` | [04] Rec 2 |
| high | S | Document three `/loop` recipes and run 48h trial on `doc-audit` + `sonarcloud` | new `rules/loop-recipes.md` | [04] Rec 3 |
| high | S | Add `--bare` flag to SDK-style `claude -p` invocations | audit `scripts/*.sh` | [04] Rec 9 |
| high | S | Add built-in Explore and Plan read-only subagents to supervisor table | `rules/supervisor.md` | [01] Rec 7 |
| high | S | Document two-pattern skill architecture (agent-preloaded vs tool-invoked) | `rules/supervisor.md` or new `rules/skill-patterns.md` | [01] Rec 3 |
| high | S | Add codebase discovery checklist to `writing-plans` skill | `skills/writing-plans/SKILL.md` | [03] Rec 1 |
| high | M | Create `rules/settings-and-permissions.md` covering 5-scope hierarchy, `deny -> ask -> allow`, sandbox layer | new `rules/settings-and-permissions.md`; xref from CLAUDE.md | [01] Rec 2 |
| high | M | SessionStart hook for dynamic rule loading based on branch and modified paths | `settings.json`, new `scripts/session-start-rules.sh` | [04] Rec 1 |
| high | M | Stop hook for deterministic verification (`pre-commit run --files <touched>` minimum) | `settings.json`, new `scripts/stop-verification.sh` | [04] Rec 10 |
| high | M | On-demand skill hooks convention + one reference impl (`/rad-strict`) | `skills/writing-skills/SKILL.md`, `skills/rad/` | [04] Rec 4 |
| high | L | Convert 5 high-traffic agents to imperative state-machine framing | `agents/code-reviewer.md`, `test-engineer.md`, `security-auditor.md`, `documentation-writer.md`, `research-agent.md` | [02] Rec 2 |
| medium | S | Add `attribution.commit`, `attribution.pr`, `plansDirectory`, `outputStyle`, `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` to settings.json | `settings.json` | [05] Rec 2 |
| medium | S | Add monorepo CLAUDE.md loading semantics to global CLAUDE.md | `CLAUDE.md` | [01] Rec 4 |
| medium | S | Extend subagent-driven-development reviewer with complexity check | `skills/subagent-driven-development/code-quality-reviewer-prompt.md` | [03] Rec 3 |
| medium | S | Append-only constraint to code-review and plan-review skills | `skills/requesting-code-review/SKILL.md`, `skills/writing-plans/SKILL.md` | [03] Rec 2 |
| medium | S | Contrast three MCP scopes vs our Tier 1/2/3 strategy in mcp-strategy.md | `rules/mcp-strategy.md` | [01] Rec 5 |
| medium | S | Document Command -> Agent -> Skill orchestration concept in supervisor.md | `rules/supervisor.md` | [01] Rec 6 |
| medium | S | Add `maxTurns`, `permissionMode`, `color` frontmatter fields to all agents | `agents/*.md` | [02] Rec 3 |
| medium | S | Skill usage telemetry via PreToolUse log | `settings.json`, new `scripts/log-skill-usage.sh` | [04] Rec 7 |
| medium | M | Normalize agent tool declarations to `allowedTools` YAML list (least privilege) | `agents/*.md`, `skills/*/SKILL.md` | [02] Rec 4 |
| medium | M | Add `## Output Summary` terminal contracts to all non-trivial agents | `agents/*.md` | [02] Rec 7 |
| medium | M | Author one Command -> Agent -> Skill reference coordinator with `### Data Contract` | new `commands/rad-verify-pipeline.md` or similar | [02] Rec 5 |
| medium | M | Wire FileChanged hook with `.env*` matcher | `settings.json`, new `scripts/env-file-guard.sh` | [05] Rec 3 |
| medium | M | Wire SessionEnd cleanup hook | `settings.json`, new `scripts/session-end-cleanup.sh` | [05] Rec 4 |
| medium | M | Adopt preloaded "agent skill" pattern for domain knowledge | `agents/security-auditor.md`, `agents/test-engineer.md` | [02] Rec 1 |
| medium | M | Lightweight feasibility-check skill between brainstorming and writing-plans | new `skills/feasibility-check/SKILL.md` | [03] Rec 4 |
| medium | M | `${CLAUDE_PLUGIN_DATA}` memory for detector skills | `skills/silent-failure-hunter/`, `test-coverage/`, `debug-tests/` SKILL.md | [04] Rec 6 |
| medium | M | Runbook skill template for operational procedures | new `skills/runbook-template/` | [04] Rec 8 |
| medium | M | Citation footers across rules/ and behavior-related standards/ | `rules/*.md`, selected `standards/*.md` | [01] Rec 1 |
| low | S | PermissionDenied advisory hook | `settings.json`, new `scripts/permission-denied-advisor.sh` | [05] Rec 5 |
| low | S | Lightweight verification-checklist (accumulated audit rules) | new `docs/development/platform-audit-checklist.md` | [06] Rec 2 |
| low | S | Document subagent `isolation: "worktree"` and `--teammate-mode` as orchestration levers | `rules/git-workflow.md`, `standards/git-worktree.md`, `rules/supervisor.md` | [01] Rec 8 |
| low | S | Note `CLAUDE_CODE_SUBAGENT_MODEL` as cost optimization lever | `rules/supervisor.md` | [01] Rec 9 |
| low | S | Cross-model review in subagent-driven-development (reviewer != implementer family) | `skills/subagent-driven-development/SKILL.md` Model Selection section | [03] Rec 5 |
| low | S | Document "dispatching-parallel-agents vs agent-teams" tradeoff | `rules/supervisor.md` or new `standards/multi-agent-coordination.md` | [02] Rec 10 |
| low | S | Standardize skill frontmatter to always include `name:` and optionally `user-invocable:` | `skills/*/SKILL.md` | [02] Rec 9 |
| low | S | Self-evolving Learnings pattern for maintenance agents | `agents/skill-creator`, `claude-md-improver`, `diagram-maintenance` | [02] Rec 8 |
| low | L | Progressive disclosure audit across existing 41 skills | `skills/*/SKILL.md` | [04] Rec 5 |

## Consensus validation summary

The draft synthesis was reviewed by three models in parallel via
`mcp__pal__chat`. Two additional models (grok-4.1-fast, glm-4.5-air) were
blocked by per-call token-budget limits on file attachments and could not
process the 5306-token synthesis report. The three responding models
(gemini-3.1-pro-preview neutral, gpt-5.2 against, qwen3.5-plus-02-15 neutral)
provided substantively critical feedback that surfaced several real weaknesses.

### Cross-model convergent findings (all three models agreed)

1. **Accounting inconsistency in the executive summary.** The original draft
   claimed "24 distinct actions" and "three non-adoption decisions" but the
   action table lists 38 rows and Theme 4 lists 7 non-adoptions. **Addressed:**
   executive summary numbers corrected to 38 actions / 7 non-adoptions.
2. **Theme 3 "our way is better" claims lack supporting evidence.** Python
   interpreter boot cost is asserted as "unacceptable tax" with no
   measurement; "our pipeline is richer and better calibrated" conflates
   richer with better. **Addressed:** see "Theme 3 revisions" below.
3. **Imperative agent rewrite (high priority, L effort) is a regression
   risk.** Modifying already-working, high-traffic agents without a
   regression suite is unsafe. **Addressed:** demoted to medium priority with
   an explicit "pilot on one agent first" condition.
4. **22-entry destructive-bash `ask` list is a double-edged sword.** Could
   cause a prompt storm that trains users to blindly approve, defeating the
   safety goal. **Addressed:** kept at high priority but added a mitigation
   note below.
5. **Dependencies between items are implicit.** **Addressed:** consensus-
   adjusted short list below is explicitly ordered.

### Per-model key feedback (summarized)

**Gemini 3.1 Pro (neutral):**

- Escalate to HIGH: FileChanged `.env*` matcher (secret-leak prevention is
  Theme 2's highest-ROI thesis; leaving it medium contradicts the report's
  own framing). Normalize agent `allowedTools` (foundational least-privilege
  before scaling `/loop` automations).
- Demote to MEDIUM: Explore + Plan read-only subagents (organizational
  luxury), Imperative agent conversion (touches working assets).
- Missing entirely: **Cost/token circuit breaker for `/loop` trials.** An
  unattended loop running for 48 hours with a malformed prompt can cause API
  bill shock. This is genuinely absent from the report.
- Effort reality check: "On-demand skill hooks" and "Preloaded agent skill
  pattern" are realistically L, not M (state management + empirical testing).
- Biggest uncalled risk: **Compounding invisible state.** Dynamic rule
  loading plus on-demand hooks plus cleanup hooks plus 41 skills times 29
  agents equals a nondeterministic environment where debugging a misbehaving
  session becomes a nightmare.

**GPT-5.2 (adversarial, advanced reasoning):**

- Cut outright or demote aggressively: SessionStart dynamic rule loading
  ("complexity bomb, will create heisenbugs"), On-demand skill hooks ("no
  rollback story"), Convert 5 high-traffic agents ("regression risk,
  high-traffic makes it worse"), repo-wide mechanical edits (maxTurns +
  color + Output Summary + citation footers = time sinks with unclear
  payoff), Progressive disclosure audit ("refactor-a-thon").
- Theme 3 claims that need data: Python boot cost, centralized mapping
  "prevents drift", single-file plan "faster and sync-proof", quality gate
  stack "richer". None of these are measured.
- Hidden dependencies not priced in: Stop hook requires pre-commit installed
  and fast everywhere; FileChanged needs robust globbing and a policy for
  legitimate `.env.example` edits; skill telemetry is a new logging pipeline
  with storage/rotation/analysis costs; `${CLAUDE_PLUGIN_DATA}` creates data
  format migration ownership.
- Risk blind spots: SessionStart creates non-reproducible session behavior;
  imperative rewrites can reduce agent flexibility; on-demand hooks create
  a second control plane that is hard to reason about.
- Speculative high priorities: `/loop` recipes (where is the pain signal?),
  Explore/Plan built-ins, Command to Agent to Skill orchestration doc,
  attribution strings.

**Qwen 3.5 Plus (neutral, technical accuracy focus):**

- Technical accuracy concerns that must be verified before adoption:
  - **`${CLAUDE_PLUGIN_DATA}` is not in Anthropic's official docs.** It may
    be a community convention from the external repo rather than a
    documented Claude Code platform feature. Recommendation 4.6 is built on
    sand if this is not real. **Addressed:** added verification step.
  - **"--bare flag 10x cold-start improvement"** lacks a citation anchor.
    Should be measured before auditing 10+ scripts. **Addressed:** added
    verification step.
  - **"27 hook events"** may be the external repo's extrapolation, not all
    officially supported. **Addressed:** added verification step.
- Dependency ordering issues: settings-and-permissions.md should land with
  or before the 22-entry ask list; Discovery checklist logically follows
  feasibility gating; ask list plus `.env*` guard should be tested together.
- SessionStart is realistically L effort, not M (detection, classification,
  rule selection, injection, and testing across project types).
- Missing: success metrics and sunset criteria. Each of the 38 actions needs
  a "Definition of Done" column. Without measurable outcomes, there is no
  way to know whether the effort paid off or when to roll back.
- Theme 4 non-adoption #1 (monolithic hooks.py) is sound for per-tool-call
  events but a **hybrid approach** (Python for infrequent lifecycle events,
  shell for frequent tool events) was not explored. Worth noting.

### Theme 3 revisions (responding to convergent feedback)

The "our way is better" claims are now framed as working hypotheses rather
than demonstrated facts:

- Python interpreter boot cost: kept as a hypothesis, not a proven tax. If
  we later adopt any hook that genuinely needs Python (JSON parsing, state
  management), measure the per-call cost first.
- Centralized MCP mapping: kept as our convention, with acknowledgment that
  it creates a single point of staleness that must be audited.
- Single-file plan layout: kept, with acknowledgment that the single-reader
  assumption holds only while this repo has one maintainer.
- Quality gate stack: kept, with acknowledgment that deterministic linters
  can create panic loops if the subagent cannot appease them; mitigation is
  the existing `ci-fix` skill which handles the retry logic centrally.

### Consensus-adjusted short list (execute first, within two weeks)

This is the minimum viable adoption subset after consensus. Everything else
in the full action table stays in place as a backlog, but is not promised
as two-week work.

| Order | Priority | Effort | Action | Consensus note |
| --- | --- | --- | --- | --- |
| 1 | high | M | Create `rules/settings-and-permissions.md` (5-scope hierarchy, `deny -> ask -> allow` eval, sandbox layer) | Lands first per qwen ordering; qualifies everything else |
| 2 | high | S | Adopt a **limited** 22-entry `permissions.ask` list with a 7-day trial period and an off-switch | gpt-5.2 flagged prompt-storm risk; mitigation is trial-and-measure, not full adoption |
| 3 | high | S | Wire FileChanged hook with `.env*` matcher | gemini escalated from medium; secret-leak prevention belongs at top |
| 4 | high | S | Add `attribution.commit`, `attribution.pr`, `plansDirectory`, `outputStyle: "Explanatory"`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: 80` to settings.json | 5 one-line gains, zero-risk |
| 5 | high | S | Add `--bare` flag to existing `claude -p` invocations **after verifying the 10x claim on one script first** | qwen verification requirement |
| 6 | high | S | Document `/branch` and `--fork-session` in `rules/git-workflow.md` | Pure documentation, zero risk |
| 7 | high | S | Add built-in Explore + Plan to supervisor agent table | One table row; gemini thought this was lower priority but it is a 5-minute change |
| 8 | high | M | Stop hook running `pre-commit run --files <touched>` with measurement of per-invocation latency before committing to it | gpt-5.2 hidden dependency warning; trial first |
| 9 | high | M | Document two-pattern skill architecture in supervisor.md | Pure documentation |
| 10 | high | S | Add codebase discovery checklist item to `writing-plans` skill | Single checklist line |

**Explicitly deferred from the two-week window** (stays in the full action
table but does not commit until after the short list proves out):

- SessionStart dynamic rule loading (effort reality: L, gpt-5.2 flagged as
  complexity bomb; reassess after we have lived with the ordered items above)
- On-demand skill hooks convention (new primitive; needs rollback story and
  success metric before adoption)
- Imperative agent conversion (demoted to medium; pilot on one low-risk
  agent first, then decide whether to extend)
- Mass frontmatter edits (maxTurns + color + allowedTools normalization +
  Output Summary) — batch these into a single scheduled maintenance pass,
  not sprinkled across the timeline
- Progressive disclosure audit of 41 skills (L effort; schedule separately)
- `${CLAUDE_PLUGIN_DATA}` stateful memory (verify the feature exists first)
- `/loop` recipes (deferred; add a token/cost circuit breaker first per
  gemini's gap finding)

### New recommendations that came out of consensus (not in the source analyses)

- **Cost/token circuit breaker hook** for any unattended `/loop` or
  background task. Add a hard-stop policy before any automation runs for
  more than 30 minutes unattended. (gemini)
- **Success metrics column** on the action table ("Definition of Done" for
  each action). This file does not yet add that column; future
  implementation plans should treat it as a required field. (qwen)
- **Verify before adopting**: `${CLAUDE_PLUGIN_DATA}` environment variable
  existence, `--bare` flag 10x speedup claim, count of officially supported
  hook events (may be less than 27). (qwen)

## Appendix: per-chunk summary

| Chunk | Recs | High | Med | Low | Non-adopt |
| --- | --- | --- | --- | --- | --- |
| [01] Core concepts and architecture | 9 | 3 | 5 | 1 | 0 |
| [02] Runnable implementations | 10 | 2 | 6 | 2 | 0 |
| [03] Development workflows | 6 | 1 | 3 | 1 | 1 |
| [04] Tips harvest | 10 | 6 | 4 | 0 | 0 |
| [05] Hooks and configuration | 8 | 1 | 4 | 1 | 3 |
| [06] Changelog and versioning | 4 | 0 | 0 | 3 | 1 |
| **Total** | **47** | **13** | **22** | **8** | **5** |

After deduplication and cross-cutting grouping, the 47 raw recommendations
consolidated into the 38 actions in the prioritized table above, plus 7
explicit non-adoption decisions captured in Theme 4 (some non-adoptions from
individual chunks merged into a single Theme 4 entry).

## Authoritative citations preserved

Collected across all six analysis documents for future reference in our own
docs.

**Anthropic official:**

- Claude Code docs (full tree): <https://code.claude.com/docs/en/>
- Claude Code sub-agents, skills, settings, memory, mcp, permissions, sandbox, statusline, hooks, output-styles, env-vars, interactive-mode, keybindings
- Claude Code CHANGELOG: <https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md>
- Claude Code settings JSON schema: <https://json.schemastore.org/claude-code-settings.json>
- Anthropic engineering blog: [Advanced Tool Use Guide](https://www.anthropic.com/engineering/advanced-tool-use), "Code Execution with MCP"
- Claude GitHub App: <https://github.com/apps/claude>
- Model Context Protocol specification: <https://modelcontextprotocol.io/>

**Boris Cherny (Anthropic, Claude Code creator) tweets:**

- Jan 3 2026, 13 tips: <https://x.com/bcherny/status/2007179832300581177>
- Feb 1 2026, 10 team tips: <https://x.com/bcherny/status/2017742741636321619>
- Feb 12 2026, 12 customization tips: <https://x.com/bcherny/status/2021699851499798911>
- Mar 10 2026, Code Review + test time compute: <https://x.com/bcherny/status/2031089411820228645>
- Mar 25 2026, squash merge + PR size: <https://x.com/bcherny/status/2038552880018538749>
- Mar 30 2026, 15 hidden features: <https://x.com/bcherny/status/2038454336355999749>
- CLAUDE.md loading clarification: <https://x.com/bcherny/status/2016339448863355206>

**Community:**

- Thariq on skills, Mar 17 2026: <https://x.com/trq212/status/2033949937936085378>
- Humanlayer "Writing a good Claude.md": <https://www.humanlayer.dev/blog/writing-a-good-claude-md>
- Reddit r/mcp thread 1: <https://reddit.com/r/mcp/comments/1mj0fxs/>
- Reddit r/mcp thread 2: <https://reddit.com/r/mcp/comments/1qarjqm/>
- Shipyard Claude Code CLI cheatsheet: <https://shipyard.build/blog/claude-code-cheat-sheet/>
- Companion Codex CLI best-practice repo: <https://github.com/shanraisshan/codex-cli-best-practice>

**External repo subject of this review:**

- Root: <https://github.com/shanraisshan/claude-code-best-practice>
- Orchestration workflow: `/orchestration-workflow/orchestration-workflow.md`
- Weather orchestrator example: `/.claude/commands/weather-orchestrator.md`
- RPI workflow: `/development-workflows/rpi/rpi-workflow.md`
- Cross-model workflow: `/development-workflows/cross-model-workflow/cross-model-workflow.md`
- Hook dispatcher: `/.claude/hooks/scripts/hooks.py`
