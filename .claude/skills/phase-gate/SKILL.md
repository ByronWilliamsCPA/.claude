---
name: phase-gate
description: >
  Evaluate phase readiness by analyzing scope completion and running quality gates.
  Use when transitioning between implementation phases, checking phase status,
  or validating that a phase is ready for completion.
version: 1.0.0
---

# Phase Gate Skill

Evaluate whether an implementation phase is complete and ready for transition to the next phase. Orchestrates scope analysis and quality gate review, then presents results for user approval.

## When to Use This Skill

- User says "is phase X done?", "check phase X", "phase gate", "ready for next phase"
- User invokes `/phase-gate` with a phase number
- Before creating a PR that represents phase completion
- When starting a new phase (to confirm the previous one is complete)

## Arguments

- `phase <N>` — Evaluate phase N (0-6). Required.
- `scope-only` — Run only scope analysis, skip quality gates
- `review-only` — Run only quality gates, skip scope analysis
- `plan` — Validate a proposed action plan against phase scope (for pre-implementation)

## Workflow

### Mode: Full Evaluation (default)

This is the primary workflow. It runs both scope analysis and quality review in parallel, then synthesizes results.

#### Step 1: Parse Phase Number

Extract the phase number from `$ARGUMENTS`. Valid values: 0-6. If missing, check the current git branch name for a phase indicator (e.g., `feat/phase-1-*`). If still unclear, ask the user.

#### Step 2: Dispatch Agents in Parallel

Launch both agents simultaneously using the Agent tool:

1. **scope-analyzer** agent:
   - Task: "Analyze phase {N} scope against docs/IMPLEMENTATION_PLAN.md. Check which deliverables are DONE, PARTIAL, NOT STARTED, or UNCLEAR. Detect any scope creep on the current branch."
   - This agent reads the implementation plan and scans the source tree
   - Returns: Deliverable status table, scope boundaries, scope creep detection

2. **phase-reviewer** agent:
   - Task: "Run quality gates for phase {N}. Execute: ruff check, ruff format --check, basedpyright, pytest with coverage, bandit. Check the per-phase smoke test from docs/IMPLEMENTATION_PLAN.md."
   - This agent runs the actual checks
   - Returns: Quality gate pass/fail table, coverage detail, smoke test results, verdict

#### Step 3: Synthesize Results

Combine both agent reports into a single summary for the user:

```markdown
## Phase {N} Gate Review: {Phase Name}

### Scope Status
- **Deliverables**: X/Y complete, Z partial, W not started
- **Scope creep**: {none detected / items listed}

### Quality Gates
- **Lint**: PASS/FAIL
- **Types**: PASS/FAIL
- **Tests**: PASS/FAIL (XX% coverage)
- **Security**: PASS/FAIL
- **Smoke test**: PASS/FAIL/MANUAL

### Verdict: {READY / NOT READY}

{If NOT READY: specific blockers}
{If READY: "Phase {N} is complete. Approve to proceed to Phase {N+1}?"}
```

#### Step 4: Wait for User Approval

**CRITICAL**: Do not begin any work on the next phase until the user explicitly approves. If the verdict is NOT READY, offer to help address the blockers.

### Mode: Scope Only (`scope-only`)

Run only the scope-analyzer agent. Useful for checking progress mid-phase without running the full quality gate suite.

### Mode: Review Only (`review-only`)

Run only the phase-reviewer agent. Useful when scope is already confirmed and you just need to verify quality gates pass.

### Mode: Plan Validation (`plan`)

For pre-implementation validation. Instead of checking what's done, validate a proposed plan:

1. Launch the **plan-validator** agent with the phase number and the current TodoWrite items (or ask the user for the plan)
2. Present the traceability matrix showing which plan items map to acceptance criteria
3. Flag scope creep candidates and coverage gaps
4. Get user approval of the plan before implementation begins

## Examples

```bash
# Full phase gate evaluation
/phase-gate phase 0

# Check scope progress mid-phase
/phase-gate phase 1 scope-only

# Verify quality gates before PR
/phase-gate phase 0 review-only

# Validate implementation plan before coding
/phase-gate phase 1 plan
```

## Integration

This skill works with:

- **scope-analyzer** agent (`/.claude/agents/scope-analyzer.md`)
- **phase-reviewer** agent (`/.claude/agents/phase-reviewer.md`)
- **plan-validator** agent (`/.claude/agents/plan-validator.md`)
- Phase-gate behavioral rules in `CLAUDE.md`
- Implementation plan at `docs/IMPLEMENTATION_PLAN.md`
