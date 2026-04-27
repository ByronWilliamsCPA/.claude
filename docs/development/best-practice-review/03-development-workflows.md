---
title: "Analysis: Development Workflows and Orchestration"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Subagent 3 analysis: external development-workflows (cross-model, RPI) vs local supervisor and dispatching skills."
tags:
  - analysis
  - development
  - automation
---

> **Scope:** Subagent 3 of 6 in the systematic comparison of
> `shanraisshan/claude-code-best-practice` against `/home/byron/dev/.claude`.
> This slice covers `development-workflows/` (cross-model + RPI) versus our
> supervisor rule and multi-agent orchestration skills.

## Files reviewed

### External

| External file | Size | Summary |
| --- | --- | --- |
| `development-workflows/cross-model-workflow/cross-model-workflow.md` | 4251 B | Four-step Claude Opus + Codex GPT-5.4 workflow across two terminals: Plan (Claude) → QA Review (Codex, additive-only) → Implement (Claude) → Verify (Codex). |
| `development-workflows/rpi/rpi-workflow.md` | 2718 B | RPI methodology overview: Research → Plan → Implement with GO/NO-GO gates, `rpi/{feature-slug}/` folder convention, and slash commands `/rpi:research`, `/rpi:plan`, `/rpi:implement`. |
| `development-workflows/rpi/.claude/commands/rpi/research.md` | 12204 B | Six-phase research command orchestrating requirement-parser, product-manager, Explore, senior-software-engineer, technical-cto-advisor, documentation-analyst-writer agents. Emits GO / CONDITIONAL GO / DEFER / NO-GO. |
| `development-workflows/rpi/.claude/commands/rpi/plan.md` | 11943 B | Five-phase plan command producing four plan files (`pm.md`, `ux.md`, `eng.md`, `PLAN.md`) via product-manager + ux-designer + senior-software-engineer + documentation-analyst-writer. |
| `development-workflows/rpi/.claude/commands/rpi/implement.md` | 16586 B | Six-step per-phase implement command: Explore → senior-software-engineer → Self-validation → code-reviewer → **User Validation Gate** → Documentation Update. Uses phase status markers `[ ] [~] [x] [!] [-]`. |
| `development-workflows/rpi/.claude/agents/constitutional-validator.md` | 9100 B | Opus-model agent validating roadmap items across five dimensions: Mission, Architecture, Knowledge System, Collaboration Model, Complexity. Verdicts APPROVED / APPROVED WITH CONDITIONS / NEEDS REVISION / REJECTED. |
| `development-workflows/rpi/.claude/agents/requirement-parser.md` | 8500 B | Sonnet-model first-in-pipeline agent that converts unstructured feature requests into structured functional + non-functional requirements, complexity estimate, and clarifying questions. |

### Local

| Local file | Role |
| --- | --- |
| `/home/byron/dev/.claude/.claude/rules/supervisor.md` | Supervisor role: TodoWrite-first, task→agent routing table, scope tracing for phased projects, PR preparation pointer. |
| `/home/byron/dev/.claude/.submodules/superpowers/skills/dispatching-parallel-agents/SKILL.md` | Pattern for dispatching one agent per independent problem domain when facing 2+ unrelated failures. |
| `/home/byron/dev/.claude/.submodules/superpowers/skills/subagent-driven-development/SKILL.md` | Execute plans by dispatching fresh subagent per task with two-stage review (spec compliance then code quality). |
| `/home/byron/dev/.claude/.submodules/superpowers/skills/executing-plans/SKILL.md` | Lighter-weight plan execution for separate-session handoff without subagent support. |
| `/home/byron/dev/.claude/.submodules/superpowers/skills/writing-plans/SKILL.md` | Produce bite-sized (2-5 min steps) TDD plan documents with exact file paths and no placeholders. |

## Key patterns observed in external repo

- **Cross-model asymmetric review.** Claude Opus handles creation (plan, implement); Codex GPT-5.4 handles adversarial review (QA plan, verify implementation) in a separate terminal. Both agents share state through a single plan file. Source: `cross-model-workflow.md`.
- **Additive-only plan editing.** The Codex QA reviewer inserts intermediate "Phase 2.5" sections with "Codex Finding" headings and is explicitly instructed to ADD to the plan, never rewrite original phases. Source: `cross-model-workflow.md`.
- **RPI four-step methodology.** Describe → Research → Plan → Implement, each with a dedicated folder under `rpi/{feature-slug}/`: `REQUEST.md`, `research/RESEARCH.md`, `plan/{pm,ux,eng,PLAN}.md`, `implement/IMPLEMENT.md`. Source: `rpi-workflow.md`.
- **Mandatory GO/NO-GO research gate before planning.** Five-phase research pipeline with explicit verdict (GO / CONDITIONAL GO / DEFER / NO-GO) emitted before any planning work begins. Prevents wasted effort on non-viable features. Source: `rpi/.claude/commands/rpi/research.md`.
- **Technical Discovery precedes feasibility assessment ("Phase 2.5").** Explore agent deeply investigates the current codebase before the senior-software-engineer agent renders technical feasibility judgment. Explicitly called "CRITICAL" because it ensures Phase 3 is based on actual code reality rather than assumptions. Source: `research.md` lines referring to Phase 2.5.
- **Multi-artifact plan split.** Plans are decomposed into four separate files by audience: `pm.md` (product), `ux.md` (user experience), `eng.md` (technical), `PLAN.md` (roadmap). Source: `plan.md`.
- **Explicit human validation gate per implementation phase.** The `/rpi:implement` command STOPS at a user validation gate after each phase and requests PASS / CONDITIONAL PASS / FAIL from the human. Phase status tracked with five checkbox states: `[ ]` (not started), `[~]` (in progress), `[x]` (validated pass), `[!]` (conditional pass), `[-]` (failed validation). Source: `implement.md`.
- **Constitutional validation across five dimensions.** The `constitutional-validator` agent checks Mission Alignment, Architectural Alignment, Knowledge System Alignment, Collaboration Model Alignment, and Complexity Appropriateness. This is a non-functional heuristics check, not a functional acceptance-criteria check. Source: `constitutional-validator.md`.
- **Explore-first loop within implementation.** Every implementation phase starts by re-running the Explore agent on the files about to be modified. Source: `implement.md` Step 1.
- **Post-workflow `/compact` reminder.** All three RPI commands end with a mandatory instruction to prompt the user to run `/compact` to reclaim context. Source: `research.md`, `plan.md`, `implement.md`.

## Comparison to our practices

| External pattern | Our equivalent | Verdict |
| --- | --- | --- |
| `dispatching-parallel-agents` pattern (one agent per independent problem domain, parallel dispatch) | `dispatching-parallel-agents` SKILL at `/home/byron/dev/.claude/.submodules/superpowers/skills/dispatching-parallel-agents/SKILL.md` | overlap (effectively identical concept). Ours is more prescriptive with explicit "When NOT to use" guidance and a real-world case study. |
| Fresh subagent per task with two-stage review | `subagent-driven-development` SKILL | overlap (ours is more rigorous: spec compliance review BEFORE code quality review, explicit implementer status codes `DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED`, and cost-aware model selection). |
| Bite-sized tasks with exact file paths, TDD structure, no placeholders | `writing-plans` SKILL | overlap. Ours enforces 2-5 minute steps and a hard no-placeholder rule with specific red-flag phrases listed. |
| Cross-model Claude + Codex adversarial pairing (creator model vs reviewer model from different families) | No direct equivalent. `subagent-driven-development` notes that reviewers can use different models but does not mandate cross-family review. `mcp__pal__consensus` runs cross-family but only for point-in-time consensus, not as a workflow gate. | gap |
| Additive-only plan editing constraint ("never rewrite original phases, only append findings") | No equivalent. Our `requesting-code-review` and `writing-plans` patterns do not forbid rewriting. | gap |
| Mandatory GO/NO-GO research gate BEFORE planning | Partial. `brainstorming` skill explores intent but does not emit a formal feasibility verdict. `project-planning` skill generates PVS/ADR/Tech-Spec/Roadmap but assumes the project is already a GO. | gap |
| Phase 2.5 Technical Discovery: mandatory Explore pass before technical feasibility assessment | No equivalent. Our `writing-plans` skill assumes the planner either already has the codebase in context or will look things up ad hoc. It has no mandatory discovery step. | gap |
| Explore-first loop inside every implementation phase | No equivalent. Our `subagent-driven-development` explicitly prefers providing full task text upfront so the implementer does NOT need to read files first. This is a philosophical difference, not an oversight: ours optimizes for token efficiency when the plan is complete; RPI optimizes for correctness when the plan may be stale. | we-do-differently |
| Multi-artifact plan split (`pm.md`, `ux.md`, `eng.md`, `PLAN.md`) | We-do-differently. Our plans live at `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md` as a single file. `project-planning` skill does produce PVS / ADR / Tech Spec / Roadmap but at the project level, not the feature level. | we-do-differently |
| RPI feature folder convention (`rpi/{slug}/{request,research,plan,implement}/`) | Flat plan location only | we-do-differently |
| Explicit human validation gate per phase with five checkbox states | Partial. `executing-plans` has per-task checkpoints but no explicit STOP-and-request-user-approval gate per phase. `subagent-driven-development` uses two-stage subagent review instead of human validation. `/phase-gate` skill evaluates phase readiness but is invoked manually, not as a mandatory step. | overlap (we cover the same territory differently). |
| `constitutional-validator` agent with five alignment dimensions (Mission, Architecture, Knowledge, Collaboration, Complexity) | Partial. Our `supervisor.md` scope tracing asks "which acceptance criterion does this serve?" which is a FUNCTIONAL check only. Our `/phase-gate` skill also operates on functional completeness. We have no automated non-functional check for architectural hygiene or complexity-appropriateness. | gap (non-functional validation). |
| Post-workflow `/compact` reminder baked into commands | Partial. Our `handoff` skill generates session continuity docs. We do not have a convention of reminding the user to compact after long workflows. | gap (minor). |
| "Platform vs Products" complexity distinction in `constitutional-validator` (rejects applying platform-level complexity to product-level problems) | No equivalent | no-equivalent |
| Filesystem-level isolation of agent roles (each role writes to its own file: `pm.md`, `ux.md`, `eng.md`) | We rely on subagent prompt boundaries and single-file outputs | we-do-differently (ours is faster and less sync-prone; theirs is more auditable) |

## Recommendations

### Recommendation 1: Add mandatory "Technical Discovery" step to writing-plans

- **What:** Update `writing-plans` SKILL to require a codebase discovery pass BEFORE the File Structure section is written. This mirrors RPI's Phase 2.5 but without requiring a dedicated subagent pipeline. A single checklist item forces the planner to traverse the real codebase state.
- **Why:** Gemini's review called this out as a genuine gap. Our current `writing-plans` assumes the planner already has the codebase in context, which leads to hallucinated file paths when the planner has been working in an adjacent subsystem. RPI solves this with Phase 2.5 Explore; we can solve it with a single explicit step in the skill.
- **Target files:**
  - `/home/byron/dev/.claude/.submodules/superpowers/skills/writing-plans/SKILL.md` (add "Codebase Discovery" section before "File Structure")
- **Effort:** S
- **Priority:** high
- **Source citation:** `development-workflows/rpi/.claude/commands/rpi/research.md` Phase 2.5 "Technical Discovery (Code Exploration)"

### Recommendation 2: Add "append-only" constraint to code-review and plan-review skills

- **What:** Update `requesting-code-review` and add a note to `writing-plans` that reviewers should INSERT review findings (e.g., "Phase N.5: Review Finding") rather than rewrite existing content. Phrase it as a hard constraint, not a preference.
- **Why:** The external repo's Codex reviewer is explicitly forbidden from rewriting original phases. This solves the classic problem where an LLM asked to "fix one paragraph" rewrites the whole file and silently drops constraints. This is a concrete pattern we do not currently enforce.
- **Target files:**
  - `/home/byron/dev/.claude/.submodules/superpowers/skills/requesting-code-review/SKILL.md`
  - `/home/byron/dev/.claude/.submodules/superpowers/skills/writing-plans/SKILL.md`
- **Effort:** S
- **Priority:** medium
- **Source citation:** `cross-model-workflow.md` STEP 2 QA REVIEW ("Adds to the plan: never rewrites original phases.")

### Recommendation 3: Add architectural complexity check to subagent-driven-development review loop

- **What:** Extend the two-stage review in `subagent-driven-development` (spec compliance, then code quality) with a third lightweight check: architectural complexity appropriateness. A single pass looking for over-abstraction, unnecessary indirection, and complexity inflation relative to problem size. Do NOT create a separate `constitutional-validator` subagent; bundle the check into the existing code quality reviewer's prompt.
- **Why:** Our `supervisor.md` scope tracing and `/phase-gate` skill only cover FUNCTIONAL compliance (did the work match the acceptance criterion?). The external `constitutional-validator` adds a non-functional "Complexity Appropriateness" dimension that catches the classic LLM failure mode of applying platform-level patterns to simple problems. Adding a dedicated validator subagent would be heavy; augmenting the existing quality reviewer's prompt is cheap and closes the gap.
- **Target files:**
  - `/home/byron/dev/.claude/.submodules/superpowers/skills/subagent-driven-development/code-quality-reviewer-prompt.md` (primary)
  - `/home/byron/dev/.claude/.submodules/superpowers/skills/subagent-driven-development/SKILL.md` (reference the new check)
- **Effort:** S
- **Priority:** medium
- **Source citation:** `development-workflows/rpi/.claude/agents/constitutional-validator.md` Section 5 "Platform vs. Products"

### Recommendation 4: Add a GO/NO-GO research gate skill, but keep it lightweight

- **What:** Create a single new skill (call it `feasibility-check` or `rad-gate`) that runs between `brainstorming` and `writing-plans`. One agent, 5-10 minutes, produces a one-page GO / CONDITIONAL GO / DEFER / NO-GO verdict. Do NOT mirror RPI's 6-agent pipeline; that is over-engineering for most features.
- **Why:** Gemini's review confirmed the 5-agent research pipeline is overkill for 90% of real-world tasks, but the concept of a formal feasibility gate before planning is genuinely missing from our flow. A single-agent version preserves the value (filter non-viable features before writing a full plan) without the token overhead.
- **Target files:**
  - New: `/home/byron/dev/.claude/skills/feasibility-check/SKILL.md`
  - Update: `/home/byron/dev/.claude/.submodules/superpowers/skills/brainstorming/SKILL.md` (reference the new gate)
  - Update: `/home/byron/dev/.claude/.submodules/superpowers/skills/writing-plans/SKILL.md` (reference the new gate as optional prerequisite)
- **Effort:** M
- **Priority:** medium
- **Source citation:** `development-workflows/rpi/rpi-workflow.md` Step 2 Research (GO/NO-GO decision gate)

### Recommendation 5: Enable cross-model review in subagent-driven-development

- **What:** Update `subagent-driven-development` SKILL's "Model Selection" section to explicitly call out that spec compliance and code quality reviewers SHOULD use a different model family than the implementer when possible (e.g., Claude implementer + Gemini or GPT reviewer via `mcp__pal__chat` or MCP). Frame it as confirmation-bias elimination.
- **Why:** Gemini's review confirmed that running the reviewer on a different model family eliminates confirmation bias in a way that same-model review cannot. The external repo achieves this via two terminals; we can achieve it via MCP within a single session. This is a cheap upgrade that captures the substantive benefit of the cross-model workflow without the two-terminal theater.
- **Target files:**
  - `/home/byron/dev/.claude/.submodules/superpowers/skills/subagent-driven-development/SKILL.md` (Model Selection section)
- **Effort:** S
- **Priority:** low
- **Source citation:** `cross-model-workflow.md` STEP 2 and STEP 4 (Codex review of Claude output)

### Recommendation 6: Do NOT adopt RPI's multi-artifact plan split or feature folder convention

- **What:** Keep our single-file plan convention at `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`. Do not split plans into `pm.md`, `ux.md`, `eng.md`, `PLAN.md`. Do not adopt the `rpi/{feature-slug}/` folder layout.
- **Why:** The multi-file split is useful for auditability when product, UX, and engineering are separate humans; it is overhead when all four files are being read by the same agent. Our flat file layout is faster to traverse and less prone to sync issues. Document this as a deliberate decision so it does not resurface in later audits.
- **Target files:**
  - Note this decision in `/home/byron/dev/.claude/docs/development/best-practice-review/03-development-workflows.md` (this file)
- **Effort:** none (documentation of deliberate non-adoption)
- **Priority:** low
- **Source citation:** `development-workflows/rpi/.claude/commands/rpi/plan.md` Phase 5 "Generate Documentation"

## Gemini review pass (summary)

- **Most external patterns are heavy repackagings of concepts we already cover**, with one substantive exception: the external framework enforces separation of concerns at the filesystem/terminal level while we rely on LLM prompt adherence. Both approaches work; ours is faster and theirs is more auditable.
- **The 5-agent research pipeline is over-engineering for 90% of real tasks**, but the underlying concept of a formal feasibility gate is a real gap. Recommend a single-agent version (Recommendation 4).
- **Technical Discovery (Explore before planning) is a genuine critical gap.** Without it, planners hallucinate file paths when working outside their recent context. Recommend a single checklist step in `writing-plans` rather than a dedicated agent pipeline (Recommendation 1).
- **Cross-model review via separate terminals is substantive, not theater.** Running a different model family eliminates confirmation bias that same-model review cannot catch. We can achieve the same benefit via MCP within a single session (Recommendation 5).
- **Our `/phase-gate` covers functional compliance; it does NOT cover architectural hygiene or complexity-appropriateness.** The `constitutional-validator` concept is a genuine non-functional check missing from our stack. Bundle it into the existing code quality reviewer prompt rather than creating a new subagent (Recommendation 3).

## Authoritative citations found

- Cross-model workflow: <https://github.com/shanraisshan/claude-code-best-practice/blob/main/development-workflows/cross-model-workflow/cross-model-workflow.md>
- RPI workflow overview: <https://github.com/shanraisshan/claude-code-best-practice/blob/main/development-workflows/rpi/rpi-workflow.md>
- RPI research command: <https://github.com/shanraisshan/claude-code-best-practice/blob/main/development-workflows/rpi/.claude/commands/rpi/research.md>
- RPI plan command: <https://github.com/shanraisshan/claude-code-best-practice/blob/main/development-workflows/rpi/.claude/commands/rpi/plan.md>
- RPI implement command: <https://github.com/shanraisshan/claude-code-best-practice/blob/main/development-workflows/rpi/.claude/commands/rpi/implement.md>
- Constitutional validator agent: <https://github.com/shanraisshan/claude-code-best-practice/blob/main/development-workflows/rpi/.claude/agents/constitutional-validator.md>
- Requirement parser agent: <https://github.com/shanraisshan/claude-code-best-practice/blob/main/development-workflows/rpi/.claude/agents/requirement-parser.md>
- Companion Codex CLI best-practice repo referenced by cross-model workflow: <https://github.com/shanraisshan/codex-cli-best-practice>
