---
title: "Analysis: Runnable Implementations"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Subagent 2 analysis: external implementation, agents, skills, and commands vs local equivalents."
tags:
  - analysis
  - agents
  - skills
---

> **Slice**: Runnable implementations (agents, commands, skills as working examples)
>
> **Scope**: Compare concrete `.claude/agents/`, `.claude/commands/`, `.claude/skills/`
> files and implementation guides from `shanraisshan/claude-code-best-practice`
> against our local runnable implementations at `/home/byron/dev/.claude/.claude/`.

## Files reviewed

### External implementation guides

| External file | Size | Summary |
| --- | --- | --- |
| `implementation/claude-subagents-implementation.md` | 96 lines | Walks through weather-agent as an example of Command → Agent → Skill; shows minimized YAML example that diverges from the full production file |
| `implementation/claude-commands-implementation.md` | 83 lines | Documents `/weather-orchestrator` as the Command layer of the pipeline and explains Agent/Skill tool routing |
| `implementation/claude-skills-implementation.md` | 120 lines | Introduces the "Skill" vs "Agent Skill" pattern dichotomy via weather-svg-creator (user invoked) and weather-fetcher (preloaded via `skills:` frontmatter) |
| `implementation/claude-agent-teams-implementation.md` | 103 lines | Multi-session tmux/iTerm2 workflow behind `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, with a coordination task-list diagram |
| `implementation/claude-scheduled-tasks-implementation.md` | 60 lines | `/loop` built-in skill demo with `/loop 1m "tell current time"`; cron minimum granularity 1 minute, 3 day auto-expire, session-scoped |

### External concrete runnable files

| External file | Size | Summary |
| --- | --- | --- |
| `.claude/agents/weather-agent.md` | 78 lines | Specialized fetcher using preloaded `weather-fetcher` skill, model sonnet, maxTurns 5, permissionMode acceptEdits, memory project, inline PreToolUse/PostToolUse/PostToolUseFailure voice hooks, broad `allowedTools` list |
| `.claude/agents/time-agent.md` | 45 lines | Minimal imperative agent: only Bash tool, haiku model, maxTurns 3, no hooks, no memory, no skills |
| `.claude/agents/presentation-curator.md` | 133 lines | Complex self-evolving agent with explicit Workflow steps, Learnings section that grows over time, and cross-doc consistency updates |
| `.claude/commands/weather-orchestrator.md` | 46 lines | Coordinator command with `description:` + `model:` frontmatter, numbered Workflow steps, Critical Requirements footer, Output Summary footer |
| `.claude/commands/time-command.md` | 26 lines | Trivial slash command (no agent delegation) |
| `.claude/skills/weather-fetcher/SKILL.md` | 45 lines | "Agent skill" preloaded by weather-agent; `user-invocable: false` |
| `.claude/skills/weather-svg-creator/SKILL.md` | 29 lines | "Skill" invoked via Skill tool; references sibling `reference.md` + `examples.md` |
| `.claude/skills/time-skill/SKILL.md` | 32 lines | User invoked (`user-invocable: true`), single-purpose |
| `agent-teams/.claude/commands/time-orchestrator.md` | 50 lines | Shows explicit `### Data Contract` section between Agent and Skill steps |
| `agent-teams/.claude/agents/time-agent.md` | 23 lines | Uses `tools: Bash` (narrow), not broad `allowedTools` |
| `agent-teams/agent-teams-prompt.md` | 60 lines | Master bootstrap prompt used to spawn the Command Architect / Agent Engineer / Skill Designer team |

### Our local files reviewed

- `/home/byron/dev/.claude/.claude/agents/code-reviewer.md`
- `/home/byron/dev/.claude/.claude/agents/test-engineer.md`
- `/home/byron/dev/.claude/.claude/agents/research-agent.md`
- `/home/byron/dev/.claude/.claude/agents/security-auditor.md`
- `/home/byron/dev/.claude/.claude/agents/documentation-writer.md`
- `/home/byron/dev/.claude/.claude/skills/git/SKILL.md`
- `/home/byron/dev/.claude/.claude/skills/testing/SKILL.md`
- `/home/byron/dev/.claude/.claude/skills/brainstorming/SKILL.md`
- `/home/byron/dev/.claude/.claude/skills/quality/SKILL.md`
- `/home/byron/dev/.claude/.claude/skills/rad/SKILL.md`
- `/home/byron/dev/.claude/.claude/skills/dispatching-parallel-agents/SKILL.md`
- `/home/byron/dev/.claude/.claude/skills/subagent-driven-development/SKILL.md`
- `/home/byron/dev/.claude/.claude/commands/` (entirely symlinks to vendored plugin submodules)

## Key patterns observed in external repo

### Pattern 1: Command → Agent → Skill pipeline as the canonical architecture

Every runnable example is structured as a three-layer orchestration. The
**Command** is the user facing entry point that gathers input and controls
flow; the **Agent** is invoked via the Task/Agent tool with a preloaded "agent
skill" that contains domain instructions; and the standalone **Skill** is
invoked via the Skill tool for stateless side effect work (file writes, SVG
rendering). Evidence: the Files column at the bottom of every implementation
doc spells out this triple, and `.claude/commands/weather-orchestrator.md`
executes all three steps in numbered order.

### Pattern 2: YAML list form for `allowedTools` with permission patterns

External agents declare tools as a YAML list of quoted strings that match
Claude Code's permission pattern grammar, not a flat tool name array. Example
from `.claude/agents/weather-agent.md` lines 4 to 15:

```yaml
allowedTools:
  - "Bash(*)"
  - "Read"
  - "Write"
  - "WebFetch(*)"
  - "mcp__*"
```

This format is accepted directly by the Claude Code config loader and enables
fine grained Bash/MCP pattern restrictions.

### Pattern 3: "Agent skill" (preloaded) vs "Skill" (invoked) dichotomy

External repo intentionally uses `skills:` frontmatter on agents to inject a
skill's body into the agent context at startup, treated as a system prompt
extension. These preloaded skills set `user-invocable: false` to hide them
from the `/` menu. Standalone skills are explicitly invoked via the Skill
tool and set `user-invocable: true`. Evidence:

- `weather-fetcher/SKILL.md` line 4: `user-invocable: false` (preloaded)
- `time-skill/SKILL.md` line 4: `user-invocable: true` (user invokable)
- `weather-agent.md` lines 21-22: `skills: - weather-fetcher`

This makes the skill content available to the agent without a Skill tool call
and without incurring an extra turn.

### Pattern 4: Imperative workflow framing with numbered Steps

External agents and commands do not use "Capabilities" or "Checklist"
sections. They use `### Step 1`, `### Step 2`, `### Step N` under a
`## Workflow` header, followed by `## Critical Requirements` and
`## Output Summary`. This reads as a state machine script rather than a
reference manual. Evidence: `weather-orchestrator.md` lines 10-31,
`presentation-curator.md` lines 32-106.

### Pattern 5: Explicit "Data Contract" section for inter-step handoffs

The `agent-teams/.claude/commands/time-orchestrator.md` file introduces an
explicit `### Data Contract` block (lines 22-26) that enumerates the fields
the upstream agent must return for the downstream skill to consume:

```markdown
The time-agent MUST return these three fields:
- time: The time portion (e.g., "14:30:45")
- timezone: "GST (UTC+4)"
- formatted: Full formatted string (e.g., "2026-03-12 14:30:45 +04")
```

This transforms the text-based LLM interface into a reliable inter-step API
and prevents drift when an orchestrator passes data between sibling steps.

### Pattern 6: Output Summary as a terminal state contract

Every external command and complex agent ends with an `## Output Summary`
section that specifies exactly what the final user facing output should
include. Evidence: `weather-orchestrator.md` lines 41-46,
`presentation-curator.md` lines 127-133,
`agent-teams/.claude/commands/time-orchestrator.md` lines 43-50. This prevents
chatty over-explanation and gives the model a termination signal.

### Pattern 7: Self-evolving agents with inline Learnings

`presentation-curator.md` demonstrates a self-modification pattern where the
agent updates both its dependent skills and its own Learnings section after
every execution (lines 74-118). The agent literally writes new bullets to
its own markdown file to prevent knowledge drift between the live artifact
and its domain instructions.

### Pattern 8: Inline per-agent hooks

External agents can declare their own `hooks:` block in frontmatter.
`weather-agent.md` lines 23-43 attach PreToolUse, PostToolUse, and
PostToolUseFailure voice hooks to every tool call (`matcher: ".*"`). This
keeps hook wiring co located with the agent it applies to rather than in a
central `.claude/settings.json`.

### Pattern 9: Agent Teams as multi-session coordination via shared task list

External `agent-teams/` uses `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` with
tmux and iTerm2 to spawn multiple independent full Claude sessions (each with
its own CLAUDE.md, MCP servers, and skills loaded). They coordinate via a
shared task list rather than subagent forks. The bootstrap prompt
(`agent-teams-prompt.md`) assigns role based teammates (Command Architect,
Agent Engineer, Skill Designer) and explicitly instructs them to post the
agreed data contract to the shared task list.

### Pattern 10: Skill directory with reference and example siblings

External skills keep SKILL.md short (often under 50 lines) and place templates
in sibling files `reference.md` (templates, specs) and `examples.md` (input
output pairs). Evidence: `weather-svg-creator/` directory contains all three.
SKILL.md simply references them.

## Comparison to our practices

| External pattern | Our equivalent | Verdict |
| --- | --- | --- |
| `allowedTools` as YAML list of permission patterns | `tools: ["Read", "Write", ...]` flat array in most agents; `allowed-tools` kebab case in `rad/SKILL.md` as comma string | we-do-differently |
| `maxTurns`, `permissionMode`, `memory`, `color` frontmatter on agents | None of these used in our 5 sampled agents | gap |
| `skills:` frontmatter preloading (agent skills) | We have no preloaded skill mechanism; all skill invocation is via Skill tool | no-equivalent |
| `user-invocable: false` flag to hide agent only skills | Not used in any local skill | gap |
| Imperative `## Workflow` with numbered `### Step N` | Our agents use descriptive `## Capabilities`, `## Review Checklist`, `## Commands` encyclopedic sections | we-do-differently |
| `## Critical Requirements` + `## Output Summary` terminal contracts | Not present in our agent prompts | gap |
| Explicit `### Data Contract` in orchestrator commands | Not applicable; we have no Command → Agent → Skill coordinators | no-equivalent |
| Self evolving Learnings section | Not present; our agents are static | gap |
| Inline `hooks:` block per agent | Hooks live only in `settings.json` | we-do-differently |
| Command → Agent → Skill pipeline as canonical architecture | No coordinator commands; our `commands/` is entirely symlinks to vendored plugins | gap |
| Multi session agent teams via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | Our `dispatching-parallel-agents` and `subagent-driven-development` skills; isolated subagent forks in one session | we-do-differently |
| Short skills with `reference.md`/`examples.md` siblings | Our skills embed routing tables and workflows/ subfiles; tend to be longer | we-do-differently |
| Scheduled tasks via `/loop` built-in skill | We have a local `loop` skill loaded; equivalent | overlap |
| `name:` in skill frontmatter | Mixed; some skills have it (`rad`, `testing`, `git`, `brainstorming`) and some do not (`quality` uses only `description:`) | we-do-differently |
| "Use PROACTIVELY" trigger phrasing in descriptions | Mostly absent from our agent descriptions | gap |

## Recommendations

### Recommendation 1: Adopt the "agent skill" preloading pattern for domain knowledge

- **What:** Introduce the `skills:` frontmatter field on our agents so that
  agent specific domain instructions can be preloaded into the context at
  startup rather than being invoked as separate Skill tool calls. Pair with
  `user-invocable: false` on the preloaded skills to hide them from the `/`
  menu.
- **Why:** It removes an extra turn per agent execution, keeps domain
  instructions versioned with the agent they serve, and documents clearly
  which skills are system prompt extensions versus stateless utilities.
- **Target files:** Start with agents that already have a narrow domain:
  `.claude/agents/security-auditor.md` could preload an `owasp-dispatch`
  skill, `.claude/agents/test-engineer.md` could preload a `testing-standards`
  skill.
- **Effort:** M
- **Priority:** medium
- **Source citation:**
  [weather-agent.md lines 21-22](https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/agents/weather-agent.md),
  [weather-fetcher/SKILL.md line 4](https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/skills/weather-fetcher/SKILL.md)

### Recommendation 2: Convert agent prompts from encyclopedic to imperative state machine form

- **What:** Rewrite our agent bodies to drop the `## Capabilities` and
  `## Review Checklist` sections and replace them with `## Your Task`,
  `## Workflow` with `### Step N` numbered steps, `## Critical Requirements`,
  and `## Output Summary`. Keep reference material in sibling files or
  linked standards docs.
- **Why:** LLMs interpret step-by-step imperative prompts as a state machine
  script with higher execution reliability. Encyclopedic prompts are treated
  as background context and lead to drift. The external `presentation-curator.md`
  is the clearest example of this contrast; it reads 2x as actionable as our
  `test-engineer.md` despite being shorter.
- **Target files:** `code-reviewer.md`, `test-engineer.md`, `security-auditor.md`,
  `documentation-writer.md`, `research-agent.md`.
- **Effort:** L (touches all agents)
- **Priority:** high
- **Source citation:**
  [presentation-curator.md lines 32-133](https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/agents/presentation-curator.md),
  [weather-orchestrator.md lines 10-46](https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/commands/weather-orchestrator.md)

### Recommendation 3: Add `maxTurns`, `permissionMode`, and `color` to agent frontmatter

- **What:** Standardize our agent frontmatter to always include `maxTurns`
  (bounds runaway loops), `permissionMode` (explicit decision about edit
  autonomy), and `color` (UI differentiation when multiple agents run in
  parallel).
- **Why:** `maxTurns` is a cheap safety belt; `permissionMode` moves what is
  currently implicit into explicit; `color` is low cost and aids visual
  disambiguation when using `dispatching-parallel-agents`.
- **Target files:** All files in `.claude/agents/`.
- **Effort:** S
- **Priority:** medium
- **Source citation:**
  [weather-agent.md lines 18-20](https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/agents/weather-agent.md),
  [time-agent.md lines 16-17](https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/agents/time-agent.md)

### Recommendation 4: Normalize tool declarations to `allowedTools` YAML list with permission patterns

- **What:** Replace our mixed `tools: ["Read", ...]`, `allowed-tools: Read, Bash(...)`,
  `tools: Read, Write` formats with a consistent `allowedTools:` YAML list.
  Use permission patterns (`"Bash(git:*)"`, `"WebFetch(*)"`, `"mcp__*"`) for
  fine grained control. Follow the principle of least privilege: default to
  the narrow set a la `ext-team-time-agent.md` (line 4: `tools: Bash`), not
  the broad set a la the production `weather-agent.md`.
- **Why:** Consistent frontmatter makes agents easier to audit; YAML lists
  are correctly parsed by Claude Code's config loader; permission patterns
  close the gap between declaring a tool and declaring what that tool can do.
- **Target files:** All `.claude/agents/*.md` and `.claude/skills/*/SKILL.md`
  that declare tools. Note the over permissioning discrepancy in the external
  `weather-agent.md` versus `team-time-agent.md`; we should not copy the
  over permissioned form.
- **Effort:** M
- **Priority:** medium
- **Source citation:**
  [weather-agent.md lines 4-15 (over permissioned example)](https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/agents/weather-agent.md),
  [agent-teams/.claude/agents/time-agent.md line 4 (narrow example)](https://github.com/shanraisshan/claude-code-best-practice/blob/main/agent-teams/.claude/agents/time-agent.md)

### Recommendation 5: Author at least one Command → Agent → Skill coordinator as a reference example

- **What:** Pick one realistic workflow in our setup (e.g. code review, RAD
  verification, test coverage) and build a hand-authored coordinator command
  in `.claude/commands/` that uses the Agent tool to invoke a specialist
  subagent and the Skill tool to invoke a stateless utility. Include a
  `### Data Contract` block between steps.
- **Why:** Our `.claude/commands/` directory is currently 100% symlinks to
  vendored plugin submodules. We have no local worked example of the
  Command → Agent → Skill pattern. A single reference coordinator teaches
  the pattern to future authors and proves our own plumbing works.
- **Target files:** New file, e.g. `.claude/commands/rad-verify-pipeline.md`
  or `.claude/commands/test-coverage-pipeline.md`.
- **Effort:** M
- **Priority:** high
- **Source citation:**
  [weather-orchestrator.md](https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/commands/weather-orchestrator.md),
  [agent-teams/.claude/commands/time-orchestrator.md](https://github.com/shanraisshan/claude-code-best-practice/blob/main/agent-teams/.claude/commands/time-orchestrator.md)

### Recommendation 6: Add Data Contract sections to any multi step pipeline

- **What:** When an orchestrator passes data between an upstream agent and a
  downstream skill, add an explicit `### Data Contract` block listing the
  required fields with types/examples. Instruct the upstream step to return
  exactly those fields.
- **Why:** LLMs drift in how they summarize text outputs between steps. An
  explicit contract converts an ad hoc text handoff into a pseudo-API, which
  dramatically improves reliability.
- **Target files:** Any future coordinator commands (see Recommendation 5),
  plus our `writing-plans` and `executing-plans` skill workflows that today
  implicitly assume structured output.
- **Effort:** S (per pipeline)
- **Priority:** medium
- **Source citation:**
  [agent-teams time-orchestrator.md lines 22-26](https://github.com/shanraisshan/claude-code-best-practice/blob/main/agent-teams/.claude/commands/time-orchestrator.md)

### Recommendation 7: Add `## Output Summary` terminal contracts to agents

- **What:** Every non trivial agent should end its body with a
  `## Output Summary` section that spells out the exact fields the final
  message must include (e.g. "Temperature, Unit, File written, Comparison
  with previous reading").
- **Why:** It gives the model an unambiguous termination signal and prevents
  chatty over-explanation that bloats the caller's context window.
- **Target files:** All `.claude/agents/*.md` except the most trivial.
- **Effort:** S
- **Priority:** medium
- **Source citation:**
  [presentation-curator.md lines 127-133](https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/agents/presentation-curator.md),
  [weather-orchestrator.md lines 41-46](https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/commands/weather-orchestrator.md)

### Recommendation 8: Consider a self-evolving Learnings pattern for agents that touch long-lived docs

- **What:** For agents that maintain complex documents (e.g. a hypothetical
  `claude-md-improver` agent or our `doc-audit` skill), add a
  `## Learnings` section with explicit instructions that the agent should
  append bullets after every execution describing new edge cases it
  encountered.
- **Why:** Prevents knowledge drift between the agent and the files it
  maintains. The external `presentation-curator.md` uses this to keep its
  own Part 6 descriptions in sync with the actual presentation slides.
  For single purpose agents this is overkill, but for
  maintenance/curation agents it is a meaningful improvement.
- **Target files:** Any agent whose output feeds back into files the agent
  itself reads (specifically `skill-creator`, `claude-md-improver`,
  `diagram-maintenance`).
- **Effort:** S
- **Priority:** low
- **Source citation:**
  [presentation-curator.md lines 74-118 (Self Evolution), lines 107-118 (Learnings)](https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/agents/presentation-curator.md)

### Recommendation 9: Standardize skill frontmatter to always include `name:` and optionally `user-invocable:`

- **What:** Audit all SKILL.md files and ensure every one has a `name:`
  field. Add `user-invocable: true` for the default case and
  `user-invocable: false` for skills only invoked via the agent `skills:`
  field.
- **Why:** Consistent frontmatter; the hidden flag prevents agent specific
  domain knowledge from cluttering the `/` menu for users.
- **Target files:** `.claude/skills/quality/SKILL.md` (missing `name:`),
  and any others we find via `grep -L '^name:' .claude/skills/*/SKILL.md`.
- **Effort:** S
- **Priority:** low
- **Source citation:**
  [weather-fetcher SKILL.md lines 1-5](https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/skills/weather-fetcher/SKILL.md)

### Recommendation 10: Document the "dispatching-parallel-agents vs agent-teams" tradeoff

- **What:** Add a short section to our `.claude/rules/supervisor.md` (or a
  new `.claude/standards/multi-agent-coordination.md`) explaining:
  single-session subagent forks (our `dispatching-parallel-agents`,
  `subagent-driven-development`) versus multi-session agent teams (their
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` with tmux + shared task list).
  Explain when each is appropriate.
- **Why:** Both mechanisms exist and neither is strictly better. Subagent
  forks are cheaper (one session, ephemeral contexts) but share the parent
  session's state. Agent teams are heavier (multiple sessions, full CLAUDE.md
  loaded in each, shared task list) but better for genuinely independent
  long running work.
- **Target files:** New section in `.claude/rules/supervisor.md` or
  `.claude/standards/multi-agent-coordination.md`.
- **Effort:** S
- **Priority:** low
- **Source citation:**
  [agent-teams implementation guide](https://github.com/shanraisshan/claude-code-best-practice/blob/main/implementation/claude-agent-teams-implementation.md),
  our `/home/byron/dev/.claude/.claude/skills/dispatching-parallel-agents/SKILL.md`

## Gemini review pass (summary)

- Confirmed that the imperative vs encyclopedic framing is the biggest
  structural difference; Gemini characterized our local agents as "HR job
  descriptions" processed as background context, versus the external
  imperative style which the LLM treats as a state machine script with
  higher execution reliability. This reinforces Recommendation 2.
- Flagged that the production `weather-agent.md` uses an over permissioned
  `allowedTools` list (virtually superuser) while the newer
  `agent-teams/.claude/agents/time-agent.md` uses a tightly scoped
  `tools: Bash`. We should follow the narrow form per principle of least
  privilege, not copy the over permissioned example. Incorporated into
  Recommendation 4.
- Validated the "agent skill vs skill" distinction as a genuinely useful
  architectural pattern, not just naming. Agent skills are effectively
  system prompt extensions at initialization time; standalone skills are
  stateless utilities invoked via Skill tool. Incorporated into
  Recommendation 1.
- Highlighted that Data Contracts are the pattern that turns a text based
  LLM interface into a reliable inter-step API. Incorporated into
  Recommendation 6.
- Noted a Task vs Agent tool naming inconsistency in the external docs
  themselves (the implementation guide uses "Agent tool" but
  `weather-orchestrator.md` uses `Task` tool in its instructions). We should
  standardize to whichever Anthropic currently documents when we author our
  first coordinator command.
- Called out the `.claude/` directory as a "read/write database" in the
  external repo via the `presentation-curator.md` self-evolving Learnings
  pattern, versus our static authoring model. Incorporated into
  Recommendation 8.

## Authoritative citations found

- External repo root: https://github.com/shanraisshan/claude-code-best-practice
- `.claude/agents/weather-agent.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/agents/weather-agent.md
- `.claude/agents/time-agent.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/agents/time-agent.md
- `.claude/agents/presentation-curator.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/agents/presentation-curator.md
- `.claude/commands/weather-orchestrator.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/commands/weather-orchestrator.md
- `.claude/commands/time-command.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/commands/time-command.md
- `.claude/skills/weather-fetcher/SKILL.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/skills/weather-fetcher/SKILL.md
- `.claude/skills/weather-svg-creator/SKILL.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/skills/weather-svg-creator/SKILL.md
- `.claude/skills/time-skill/SKILL.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/skills/time-skill/SKILL.md
- `implementation/claude-subagents-implementation.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/implementation/claude-subagents-implementation.md
- `implementation/claude-commands-implementation.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/implementation/claude-commands-implementation.md
- `implementation/claude-skills-implementation.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/implementation/claude-skills-implementation.md
- `implementation/claude-agent-teams-implementation.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/implementation/claude-agent-teams-implementation.md
- `implementation/claude-scheduled-tasks-implementation.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/implementation/claude-scheduled-tasks-implementation.md
- `agent-teams/.claude/commands/time-orchestrator.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/agent-teams/.claude/commands/time-orchestrator.md
- `agent-teams/.claude/agents/time-agent.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/agent-teams/.claude/agents/time-agent.md
- `agent-teams/agent-teams-prompt.md`: https://github.com/shanraisshan/claude-code-best-practice/blob/main/agent-teams/agent-teams-prompt.md
