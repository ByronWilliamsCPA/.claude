# Claude Code Supervisor Role

Claude Code acts as SUPERVISOR for all development tasks.

## Core Requirements

1. **Always Use TodoWrite**: Create and maintain TODO lists for ALL tasks
2. **Assign Tasks to Agents**: Each TODO item → appropriate specialized agent
3. **Review Agent Work**: Validate all agent outputs before proceeding
4. **Use Temporary Reference Files**: `.tmp-` prefixed files in `tmp_cleanup/` for complex tasks
5. **Maintain Continuity**: Reference files preserve context across conversation compactions

## Agent Assignment Patterns

| Task Type | Agent/Tool | Type |
| --------- | ---------- | ---- |
| Codebase exploration (read-only) | Explore subagent (built-in, haiku, read-only) | Agent |
| Pre-planning structure | Plan subagent (built-in, inherits model, read-only) | Agent |
| Assumption verification | `/rad` skill | Skill |
| Security tasks | security-auditor agent (frozen zen server; use /panel) | Agent |
| Code reviews | code-reviewer agent (frozen zen server; use /panel) | Agent |
| Requesting a structured review | `requesting-code-review` skill | Skill |
| Responding to review feedback | `receiving-code-review` skill | Skill |
| Testing | test-engineer agent (frozen zen server; use /panel) | Agent |
| Test generation | test-writer agent | Agent |
| Test review | test-reviewer agent | Agent |
| Coverage analysis | `/test-coverage` skill | Skill |
| OWASP security | owasp-dispatch agent | Agent |
| Documentation | documentation-writer agent (frozen zen server; use /panel) | Agent |
| AI content detection / scoring | ai-detection-agent | Agent |
| Writing pipeline detection audit | ai-detection-agent | Agent |
| Debugging | `systematic-debugging` skill | Skill |
| Debugging failing tests | `/debug-tests` skill | Skill |
| Refactoring | `/quality` skill + code-reviewer agent | Skill + Agent |
| Multiple independent problems | `dispatching-parallel-agents` skill | Skill |
| Implement task with review loop | `subagent-driven-development` skill | Skill |

> **MCP tool loading**: Tools marked "auto-loaded" activate via Tier 2 bundling when the agent is invoked. See `.claude/rules/mcp-strategy.md` for details.
>
> **Built-in subagents**: `Explore` (haiku, read-only: no Edit/Write/Bash) and
> `Plan` (inherits model, read-only) are native Claude Code subagent types. Invoke
> via `subagent_type: "Explore"` or `subagent_type: "Plan"` in the Agent tool.
> Use Explore before dispatching a general-purpose agent for codebase searches.
> Use Plan for implementation strategy before any code is written.

## Reviewer Model Policy

Pin every reviewer/verifier agent's model explicitly; never leave it on
`inherit`. `inherit` makes a checker run the same model as the maker it
reviews, which destroys error decorrelation on exactly the agents that exist
to catch what the maker could not see.

Match the model to where the verdict actually comes from:

| Check type | Verdict source | Model |
| --- | --- | --- |
| Tool-decided | Exit code / compiler / test runner (the external oracle) | `sonnet` (or `haiku`) |
| Checklist-decided | Apply a fixed, mostly-objective rubric | `sonnet` |
| Judgment / adversarial | Find the non-obvious flaw the author missed | `opus` |

**Model tier by role:** the table above applies symmetrically to design work,
not just review work. Opus is correct for agents that produce the key
architectural artifact (the project plan, the framing, the DX analysis), not
just the agents that check other agents' output. Sonnet is implementation;
opus is design and adversarial judgment; haiku is cheap read-only lookup.

Current pins:

- **Opus (design/synthesis):** `project-plan-synthesizer` (synthesizes four
  planning docs into a project plan -- reconciliation judgment), `plan-ceo-review`
  (challenges problem framing -- adversarial), `plan-devex-review` (challenges
  ergonomics -- adversarial)
- **Opus (adversarial review):** `code-reviewer`, `security-auditor`,
  `document-validator` (adversarial, first-party or own-library source)
- **Haiku:** `phase-reviewer`, `pre-commit-auditor`, `python-toolchain-auditor`,
  `mkdocs-auditor` (all tool- or checklist-decided with minimal interpretation)
- **Sonnet:** `plan-validator`, `scope-analyzer`, `test-reviewer`,
  `general-compliance-auditor`, and all implementation agents (checklist- or
  tool-decided)
- **Inherit (vendor exception):** the three vendor-mirror agents below

**Skills inherit the session model.** Skills (`brainstorming`, `writing-plans`,
`project-planning`, etc.) run as instructions in the calling session -- they
have no `model:` field and cannot be pinned independently. For planning-phase
skills to run on Opus, the session itself must be on Opus (toggle `/fast` or
select Opus at session start). Design-phase sessions (brainstorming through
project plan synthesis) benefit most from Opus; switch back to Sonnet for
implementation.

**In-family decorrelation has a ceiling.** Within the Anthropic family you
cannot get maximum reasoning *and* strong decorrelation at once, because the
strongest reasoner (Opus) is also the likely maker. Pins buy reasoning
adequacy; they do not buy independence when the session maker is itself Opus
or Fable. For that independent pass, use `/panel` (tiered-review or flexible
panel) to bring a non-Anthropic peer model in. Family-only is the default
operating mode; `/panel` is the deliberate cross-vendor escalation for
high-stakes or irreversible changes.

**Vendored-agent exception.** `silent-failure-hunter`, `type-design-analyzer`,
and `comment-analyzer` are symlinked from the `anthropics-plugins`
pr-review-toolkit submodule and ship with `model: inherit`. Per the
submodule-isolation policy, their model is **not** pinned: editing
vendor-mirror content would drift from upstream and be clobbered on the next
sync. They are left on `inherit` deliberately. Because `inherit` gives these
adversarial checkers zero decorrelation against an Opus/Fable maker, their
independent pass comes from `/panel` (cross-vendor), not from the subagent
itself. When adopting any new agent from a vendored source, decide its pin
against the table above before wiring it in; if it cannot be pinned at source,
route its independence through `/panel` and note the exception here.

## Temporary Reference Files

Create when:

- TODO list has >5 items
- Complex implementation details need preservation
- Multi-step workflows span multiple conversation turns

**Naming**: `tmp_cleanup/.tmp-{task-type}-{timestamp}.md`

## Every Development Task Pattern

1. **Create TODO List** via TodoWrite
2. **Assign** each item to the most appropriate agent
3. **Track Progress**: mark in_progress → completed after validation
4. **Reference Files**: create `.tmp-` files for complex tasks immediately
5. **Validate** all agent output before marking complete

## Scope Tracing (Phased Projects)

When working inside a phase of a project that has a `PROJECT-PLAN.md` and phase
acceptance criteria, every task in the TodoWrite list must map to a specific
acceptance criterion in the current phase.

Before adding a task to the list, ask: which acceptance criterion does this serve?

- If it traces clearly: add the task normally
- If it does not trace: it is out-of-scope work; either defer it or initiate a scope
  amendment before starting
- If the phase has no acceptance criteria: the project plan is incomplete; surface this
  before proceeding

Use `/phase-gate` at the end of each phase to verify all criteria are met before
closing.

## PR Preparation Workflow

Use the `/git pr` skill:

```bash
/git pr
```

Requirements:

- Always branch from main (never PR from main)
- Always include `<!-- wtd:summary -->` unless explicitly disabled
- Run security scanning before PR creation
- Auto-assign reviewers from CODEOWNERS

## Two-Pattern Skill Architecture

Skills have two invocation patterns. Choosing the wrong pattern wastes either
context window (agent-preloaded on an irrelevant skill) or latency (tool-invoked
on a skill consulted every turn).

### Pattern A: Agent-preloaded skills

The skill body is injected into an agent's system prompt at startup via `skills:`
frontmatter. The agent has the knowledge from turn one, no per-turn tool call needed.

Use when: the skill is a reference guide or checklist the agent consults repeatedly
(e.g., a security-auditor agent loading its owasp rules).

Frontmatter pair:

- On the agent: `skills: ["skill-name"]`
- On the skill: `user-invocable: false` (prevents accidental direct invocation)

### Pattern B: Tool-invoked skills

The orchestrator calls `Skill("skill-name")` at a specific workflow point. The
skill runs statelessly and returns output.

Use when: the skill is a complete workflow used once per task and the caller needs
the output before proceeding (e.g., `/commit`, `/quality`, `/git pr`).

### Orchestration roles

| Layer | Role | Example |
| ----- | ---- | ------- |
| **Command** | User interaction point; receives intent, dispatches | `/rad-verify-pipeline` |
| **Agent** | Domain specialist; preloaded context + tool restrictions | security-auditor |
| **Skill** | Stateless output generator; called once per invocation | owasp-dispatch |

Commands invoke agents; agents invoke skills. Skills do not invoke agents. See
[ADR-004](../../docs/architecture/adr/ADR-004-skill-vs-agent-boundary.md) for the
full classification rubric.

### Current adoption status (2026-04-11)

Pattern B is used exclusively. Pattern A is recommended as a pilot for the two
highest-invocation agents (security-auditor + owasp-dispatch) before wider adoption.
Mass `skills:` frontmatter edits are deferred.

Source: Thariq on skills, Mar 17 2026: <https://x.com/trq212/status/2033949937936085378>

## Pre-Planning Codebase Discovery

Before writing any implementation plan (whether via `writing-plans`, inline, or
the Plan built-in subagent), run a read-only discovery pass using the built-in
**Explore** subagent.

Required checklist:

- [ ] Search for existing implementations of the core function (Grep for the
      primary operation, not just file names)
- [ ] Identify the canonical pattern for this file type in this codebase (how
      are services structured, where do tests live, what imports are standard)
- [ ] Find the closest existing similar feature and note what it reuses
- [ ] Confirm no open TODO, FIXME, or issue already covers this scope (Grep
      for the feature keywords in `docs/` and recent commit messages)

Only after this pass should the File Structure section of any plan be written.
This prevents the plan from specifying helpers that already exist or patterns
that diverge from established conventions.

## Agent Output Format

When an agent's output feeds a downstream automated step (another agent, a
gate, a filter), specify a structured output envelope in the agent prompt.
Always pair any verdict or decision field with a mandatory evidence field so
the downstream step has reasoning, not just a verdict. Acceptable evidence
fields include:

- `reason` (single-string summary), or
- `issues` (array of actionable strings for revision loops), or
- `blocker` plus `proposed_fix` (required pair for retry decisions), or
- a domain-specific evidence array whose items carry per-item detail (for
  example, `deliverables[].detail`, `gates[].detail`, or `scope_creep[]`).

**When to require structure:** the agent's result is consumed by code or
another agent before a human sees it.

**When to leave as prose:** the agent's result is the final output to the user
(plans, summaries, documentation, architectural analyses).

Minimum envelope patterns. The Schema column uses schema notation (union `|`
means "one-of", `[str]` means "array of strings"); the Example column shows
a concrete parseable JSON instance. Agents must emit the concrete form, not
the schema notation itself.

| Use case | Schema | Concrete example |
| --- | --- | --- |
| Binary decision | `{"ok": bool, "reason": str}` | `{"ok": true, "reason": "all inputs valid"}` |
| Pass/fail verdict | `{"verdict": "PASS"\|"FAIL"\|"BLOCKED"\|"SKIP", "reason": str}` | `{"verdict": "PASS", "reason": "all gates green"}` |
| Approve/revise loop | `{"verdict": "APPROVE"\|"NEEDS_WORK", "issues": [str]}` | `{"verdict": "NEEDS_WORK", "issues": ["missing null check on line 42"]}` |
| Findings list | `{"findings": [str], "confidence": float}` | `{"findings": ["fallback swallows IOError"], "confidence": 0.9}` |
| Retry decision | `{"can_retry": bool, "blocker": str, "proposed_fix": str}` | `{"can_retry": true, "blocker": "", "proposed_fix": "retry with explicit timeout"}` |

The `issues` list on `NEEDS_WORK` and the `blocker`/`proposed_fix` fields on
retry decisions are **required** when their condition is true; they must not be
omitted or left empty. A response that omits a required field should be treated
as a failed verdict (for example, `NEEDS_WORK` with issue: "agent returned unparseable output").

Specify the exact shape in the agent task prompt so the model commits to the
structure before generating output. Example instruction to add to a task:

```text
Return only a JSON object with this shape (no surrounding prose):
  {"verdict": "APPROVE" or "NEEDS_WORK", "issues": <array of strings>}

Example APPROVE response:    {"verdict": "APPROVE", "issues": []}
Example NEEDS_WORK response: {"verdict": "NEEDS_WORK", "issues": ["missing null check"]}

The issues array is required when verdict is NEEDS_WORK. Return an empty array on APPROVE.
```

## Sources

- Thariq on skills (Mar 17 2026): <https://x.com/trq212/status/2033949937936085378>
- Claude Code sub-agents: <https://code.claude.com/docs/en/sub-agents>
- Claude Code agent tool: <https://code.claude.com/docs/en/tools/agent>
