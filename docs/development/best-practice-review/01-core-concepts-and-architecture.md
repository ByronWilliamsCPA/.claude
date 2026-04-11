---
title: "Analysis: Core Concepts and Architecture"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Subagent 1 analysis: external best-practice guides and orchestration-workflow vs local CLAUDE.md, rules, and standards."
tags:
  - analysis
  - architecture
  - research
---

> Subagent 1 of 6. Slice: concept-level patterns in the external
> [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice)
> repo vs our local rules and standards. Runnable implementation details
> (hooks, commands, scripts) are owned by Subagent 2.

## Files reviewed

| External file | Size | Summary |
| --- | --- | --- |
| best-practice/claude-subagents.md | ~4 KB | 16 subagent frontmatter fields; 5 official built-ins (general-purpose, Explore, Plan, statusline-setup, claude-code-guide) |
| best-practice/claude-commands.md | ~12 KB | 13 command frontmatter fields; 68 built-in slash commands grouped by category |
| best-practice/claude-skills.md | ~3 KB | 13 skill frontmatter fields; 5 bundled skills; agent-skill vs Skill tool distinction |
| best-practice/claude-settings.md | ~60 KB | 5-level settings hierarchy, permissions model, sandbox architecture, 60+ settings, 170+ env vars |
| best-practice/claude-memory.md | ~4 KB | Ancestor-eager vs descendant-lazy CLAUDE.md loading semantics for monorepos |
| best-practice/claude-mcp.md | ~5 KB | Daily-use server shortlist; Project/User/Subagent scopes and precedence |
| best-practice/claude-cli-startup-flags.md | ~8 KB | Categorized flag reference; teammate-mode; startup-only env vars |
| best-practice/claude-power-ups.md | ~2 KB | 10 interactive lessons as a discovery mechanism |
| orchestration-workflow/orchestration-workflow.md | ~7 KB | Worked Command -> Agent(skill) -> Skill orchestration with single-responsibility roles |
| orchestration-workflow/output.md | ~0.2 KB | Example rendered output file from the orchestration demo |

## Key patterns observed in external repo

- Citation discipline: every external file closes with a "Sources" section linking the authoritative Claude Code doc, Anthropic engineering post, changelog entry, or community thread that backs the claims. (all files)
- Five-level settings hierarchy with deny-as-hard-floor: managed (org) > CLI args > `.claude/settings.local.json` > `.claude/settings.json` > `~/.claude/settings.json`. Deny rules win regardless of which scope defined them; array values are concatenated and deduplicated across scopes. (claude-settings.md)
- Drop-in configuration directory: `managed-settings.d/` pattern follows the systemd convention. `managed-settings.json` is the base, then `*.json` files in the drop-in dir are merged alphabetically on top. Scalars override, arrays concatenate and deduplicate, objects deep-merge. Enables policy fragmentation without monolithic config files. (claude-settings.md)
- Permissions evaluation order: `deny -> ask -> allow`, first matching rule wins. Path prefixes follow gitignore-style semantics (`//` absolute, `~/` home, `/` project root, `./` or none for relative). Bash wildcard supports prefix, suffix, and middle positions with word-boundary semantics. (claude-settings.md)
- Sandbox as architectural layer: `sandbox.filesystem` (`allowWrite`/`denyWrite`/`denyRead`/`allowRead`) and `sandbox.network` (allowed domains, Unix socket paths, macOS Mach lookup) give bash command isolation independent of the permission rules. Paths from `Edit(...)` permission rules merge into sandbox writeable paths automatically. (claude-settings.md)
- Two-pattern skill architecture: "agent skill" is preloaded into an agent via the frontmatter `skills:` list (full SKILL.md content injected as domain knowledge at agent startup). "Skill" is invoked dynamically via the Skill tool from a command or agent context and runs in the caller's context. The same SKILL.md file can serve either role. (claude-skills.md, orchestration-workflow.md)
- Command -> Agent -> Skill orchestration: command owns user interaction and workflow coordination, agent fetches data with preloaded domain knowledge, skill generates independent output. Single-responsibility boundary per component. (orchestration-workflow.md)
- Monorepo-aware CLAUDE.md loading: ancestor files load eagerly at startup (walking up to root), descendants load lazily only when Claude touches a file in that subtree, siblings never load. Shared instructions propagate down, component-specific instructions stay isolated. (claude-memory.md, citing Boris Cherny X post)
- Subagent worktree isolation: `isolation: "worktree"` frontmatter field creates a temporary git worktree for the subagent and auto-cleans if no changes are produced. (claude-subagents.md)
- Subagent memory scoping: `memory: user|project|local` frontmatter field routes where an agent persists notes, giving three distinct lifetime classes per agent. (claude-subagents.md)
- `initialPrompt` as auto-submitted first turn: when a subagent runs as the main session agent (via `--agent` or `agent:` setting), `initialPrompt` is prepended to any user-provided prompt and processed including commands and skills. (claude-subagents.md)
- Read-only primitives: official `Explore` (haiku, read-only) and `Plan` (inherit, read-only) subagents are supplied for discovery and planning. Cheap, safe, write-restricted by design. (claude-subagents.md)
- Path-scoped skills and commands: `paths:` glob field auto-activates a skill or command only when working with matching files. (claude-skills.md, claude-commands.md)
- `context: fork` runs a command or skill in an isolated subagent context; pairs with the `agent:` field to pick the subagent type. (claude-commands.md, claude-skills.md)
- `user-invocable: false`: marks a skill or command as background knowledge only, hidden from the `/` menu but still loadable into agent contexts. (claude-skills.md)
- Teammate mode as orchestration choice: `--teammate-mode auto|in-process|tmux` selects how agent-team subagents display and interact with the orchestrator (backgrounded, inline, or in a tmux split). (claude-cli-startup-flags.md)
- Env-as-configuration: 170+ env vars settable via the `env` key in `settings.json` avoid wrapper scripts. Notable examples: `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (context compaction threshold), `CLAUDE_CODE_SUBAGENT_MODEL` (route subagents to a cheaper model), `MAX_THINKING_TOKENS`, `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` (defense-in-depth credential stripping for subprocess env). (claude-settings.md)
- Three MCP scopes with clear precedence: Project (`.mcp.json`) > User (`~/.claude.json`) > Subagent (frontmatter `mcpServers:` field). Precedence: Subagent > Project > User. (claude-mcp.md)
- Minimalism via community data: Reddit r/mcp citation ("15 MCP servers, used 4 daily") grounds the "keep always-loaded tools small" argument in observed user behavior rather than authority alone. (claude-mcp.md)
- Discovery through interactive lessons: `/powerup` exposes 10 curated lessons with animated demos as a built-in discoverability mechanism for features users miss. (claude-power-ups.md)

## Comparison to our practices

| External pattern | Our equivalent | Verdict |
| --- | --- | --- |
| Citation discipline with "Sources" sections | Rules and standards cite a few inline URLs but have no systematic Sources footer. `standards/mcp-minimal-bloat.md` cites the Anthropic engineering blog; most files cite nothing. | gap |
| Five-level settings hierarchy with deny-as-floor | We use `.claude/settings.json`, `settings.local.json`, `~/.claude/settings.json`, but the precedence chain, array-concatenation rule, and deny-as-floor semantics are not documented anywhere in our rules. | gap |
| `managed-settings.d/` drop-in directory pattern | No equivalent. Our config lives in monolithic JSON files. | no-equivalent |
| Permissions evaluation order (deny -> ask -> allow) and path-prefix syntax | No dedicated documentation. Readers must infer from `settings.local.json.example` and external docs. | gap |
| Sandbox architectural layer (`sandbox.filesystem`, `sandbox.network`) | No mention in rules or standards. | gap |
| Two-pattern skill architecture (agent-preloaded vs tool-invoked) | `rules/supervisor.md` lists "Skill" and "Agent" as mutually exclusive rows in the assignment table; does not explain that a SKILL.md can play either role depending on how it is wired. | gap |
| Command -> Agent -> Skill orchestration pattern | `rules/supervisor.md` defines Claude as supervisor with TodoWrite fan-out but no worked example of a command orchestrating an agent plus a skill with clean role boundaries. | gap |
| Monorepo CLAUDE.md loading semantics | `CLAUDE.md` references `.claude/rules/*.md` path-scoping and project-local CLAUDE.md but never explains the ancestor-eager, descendant-lazy, sibling-never loading rule that makes the pattern safe for monorepos. | gap |
| Subagent isolation via `isolation: "worktree"` frontmatter | `rules/git-workflow.md` references the `using-git-worktrees` superpowers skill for human-driven worktree setup; the lighter-weight subagent frontmatter field is not mentioned. | gap |
| Subagent memory scoping (user/project/local) | No equivalent. We use auto-memory plus CLAUDE.md ancestor loading. | gap |
| `initialPrompt` for persistent first-turn | No equivalent. | gap |
| Read-only built-in subagents (Explore, Plan) | `rules/supervisor.md` agent table lists specialized agents but does not reference the built-in `Explore` (haiku) or `Plan` (inherit) read-only primitives. | gap |
| Path-scoped skills/commands via `paths:` glob | `rules/python.md` and `rules/testing.md` already use `paths:` frontmatter at the rule level. We do not document extending this to skills/commands. | partial overlap |
| `context: fork` + `agent:` pairing | `rules/supervisor.md` uses TaskCreate patterns but does not cover the inline fork mechanism. | gap |
| `user-invocable: false` for background knowledge | No equivalent. | gap |
| Teammate mode (`--teammate-mode auto/in-process/tmux`) | No equivalent. Not mentioned in supervisor rules or git-workflow rules. | gap |
| Env-as-configuration via the `env` key | No rule or standard documents this pattern even though our `settings.json` likely uses it. | gap |
| Three MCP scopes (Project/User/Subagent) with precedence | `rules/mcp-strategy.md` explicitly rejects the Subagent-frontmatter scope. Our architecture routes per-agent MCP bundling through a custom `mcp_config.yaml` + `mcp-tool-loader.sh` pipeline (Tier 2 bundles), centralizing the mapping. | we-do-differently |
| MCP minimalism with community data | `standards/mcp-minimal-bloat.md` makes the same argument citing Anthropic's Advanced Tool Use Guide with token-cost math. Richer and better-cited than the external repo on this topic. | overlap |
| `/powerup` interactive lessons as discovery | `AGENTS-AND-SKILLS.md` catalog plus `/skills` list is our discovery surface. No interactive walkthrough equivalent. | no-equivalent |

## Recommendations

### Recommendation 1: Add a "Sources" citation section to rules and standards files
- **What:** Each file in `.claude/rules/` and `.claude/standards/` ends with a bulleted "Sources" section linking the canonical Claude Code doc, Anthropic engineering post, or changelog entry that backs the rule. Adopt the external repo's citation-first footer pattern.
- **Why:** Rules and standards today reference internal submodules and each other but rarely cite the canonical Claude Code doc they are encoding. A future maintainer cannot audit a rule's fidelity without re-reading Anthropic's docs from scratch. Our `standards/mcp-minimal-bloat.md` already does this well for one file; generalizing it is mechanical.
- **Target files:** `/home/byron/dev/.claude/.claude/rules/*.md` (7 files including testing.md), `/home/byron/dev/.claude/.claude/standards/*.md` (selected files where behavior maps to Claude Code features, not Python packaging)
- **Effort:** M (1-4 hours)
- **Priority:** medium
- **Source citation:** claude-subagents.md, claude-commands.md, claude-skills.md, claude-settings.md, claude-memory.md, claude-mcp.md, claude-cli-startup-flags.md (consistent "Sources" footer across all external files)

### Recommendation 2: Document the settings, permissions, and sandbox model in a new rule file
- **What:** Create `/home/byron/dev/.claude/.claude/rules/settings-and-permissions.md` covering three linked topics: (a) the five-scope settings hierarchy with deny-as-floor and array concatenation, (b) the permissions `deny -> ask -> allow` evaluation order with path-prefix syntax (`//`, `~/`, `/`, `./`), and (c) the `sandbox.filesystem` and `sandbox.network` architectural layer. Note the `--setting-sources user,project,local` flag for per-session scope selection.
- **Why:** Our `CLAUDE.md` references rules/standards but never explains how Claude Code composes settings, how permission rules resolve, or that sandbox is a separate enforcement layer. When a rule conflicts with a personal `settings.local.json`, there is no guidance on which wins. These three topics sit underneath everything else in our rule set and deserve explicit treatment.
- **Target files:** new file `/home/byron/dev/.claude/.claude/rules/settings-and-permissions.md`; two-line cross-reference added to `CLAUDE.md`
- **Effort:** M (1-4 hours)
- **Priority:** high
- **Source citation:** claude-settings.md sections "Settings Hierarchy", "Permissions", "Sandbox"

### Recommendation 3: Document the two-pattern skill architecture (agent-preloaded vs tool-invoked)
- **What:** Add a section to `rules/supervisor.md` (or a new `rules/skill-patterns.md` file) explaining that a SKILL.md can be used two ways: (a) preloaded into an agent frontmatter's `skills:` list as domain knowledge (full content injected at agent startup), or (b) invoked dynamically via the Skill tool from a command or agent context. Include a short decision rule: preload when the skill is reference material used throughout the agent's run; invoke via Skill tool when the skill is a one-shot action producing output that the caller will use.
- **Why:** Our `rules/supervisor.md` treats "Agent" and "Skill" as mutually exclusive rows in its assignment table, which obscures the fact that skills can play either role. This ambiguity likely drives inefficient skill design: SKILL.md files that could preload cheaply instead end up as dynamic tool calls.
- **Target files:** `/home/byron/dev/.claude/.claude/rules/supervisor.md` (new subsection) or new `/home/byron/dev/.claude/.claude/rules/skill-patterns.md`
- **Effort:** S (under 1 hour)
- **Priority:** high
- **Source citation:** claude-skills.md frontmatter fields table, orchestration-workflow.md "Two Skill Patterns" design principle

### Recommendation 4: Add monorepo CLAUDE.md loading semantics to global CLAUDE.md
- **What:** Add 4-6 lines to our global `CLAUDE.md` explaining ancestor-eager vs descendant-lazy vs sibling-never loading. Call out the implication: component-specific CLAUDE.md files and path-scoped rules in `.claude/rules/*.md` compose cleanly in monorepos because subtree context does not bloat root-level loading.
- **Why:** Our CLAUDE.md currently says "Project-specific rules that do not fit here belong in `.claude/rules/*.md` (path-scoped where possible) or a project-local `CLAUDE.md`." This is correct but does not explain WHY path-scoping and project-local files compose safely. Naming the loading mechanism makes the design intent legible.
- **Target files:** `/home/byron/dev/.claude/CLAUDE.md` (global instructions)
- **Effort:** S (under 1 hour)
- **Priority:** medium
- **Source citation:** claude-memory.md, citing Boris Cherny X post (https://x.com/bcherny/status/2016339448863355206) and Humanlayer "Writing a good Claude.md"

### Recommendation 5: Contrast the three MCP scopes against our Tier 1/2/3 strategy in rules/mcp-strategy.md
- **What:** Extend `rules/mcp-strategy.md` with a short "MCP Scopes and our deviation" subsection that (a) names the three Claude Code scopes (Project `.mcp.json`, User `~/.claude.json`, Subagent frontmatter) with their Subagent > Project > User precedence, and (b) explicitly states that we do NOT use the subagent-frontmatter scope. Reaffirm that Tier 2 bundling is handled by `mcp_config.yaml` plus `scripts/mcp-tool-loader.sh` to keep agent MCP routing centralized rather than distributed across frontmatter. Link to the trade-off so future maintainers understand the deliberate deviation.
- **Why:** Our `rules/mcp-strategy.md` currently explains our Tier 1/2/3 model but does not mention the native scope model it replaces. A newcomer reading the file in isolation cannot answer "where should I put a project-specific MCP server" without external context, and may accidentally try to add per-agent servers via frontmatter even though the lines 70-82 of our current rule file forbid it.
- **Target files:** `/home/byron/dev/.claude/.claude/rules/mcp-strategy.md`
- **Effort:** S (under 1 hour)
- **Priority:** medium
- **Source citation:** claude-mcp.md "MCP Scopes" section

### Recommendation 6: Document the Command -> Agent -> Skill orchestration concept in supervisor.md
- **What:** Add an "Orchestration Roles" subsection to `rules/supervisor.md` that names the three-role pattern: Command = user interaction and workflow coordinator, Agent = data fetcher with preloaded domain knowledge, Skill = independent output generator invoked via the Skill tool. State the single-responsibility boundary so a future designer chooses the right component for each slice of a workflow. Do NOT include a runnable worked example here. That runnable example belongs to Subagent 2's slice.
- **Why:** Our supervisor rules list patterns in a table but never articulate what "Claude as supervisor" looks like when it fans out to a command, an agent with preloaded skills, and a skill for output generation. Naming the roles at the concept level is enough to prevent the common error of collapsing "agent" and "skill" into a single choice.
- **Target files:** `/home/byron/dev/.claude/.claude/rules/supervisor.md`
- **Effort:** S (under 1 hour)
- **Priority:** medium
- **Source citation:** orchestration-workflow.md "Key Design Principles" and "Component Details" sections

### Recommendation 7: Adopt built-in Explore and Plan read-only subagents for discovery tasks
- **What:** Update the agent assignment table in `rules/supervisor.md` to mandate `Explore` (haiku, read-only) for codebase search and discovery tasks and `Plan` (inherit, read-only) for pre-planning research before dispatching a write-capable agent. Note their read-only nature as a safety advantage when exploring unfamiliar code.
- **Why:** The built-in `Explore` and `Plan` subagents are cheap, safe, and purpose-built for the kind of read-only research that today consumes Sonnet or Opus budget through general-purpose agents. Our supervisor rules do not reference them, so they are invisible to Claude when choosing an agent. Adding them to the table closes a cost and safety gap at zero implementation effort.
- **Target files:** `/home/byron/dev/.claude/.claude/rules/supervisor.md` (Agent Assignment Patterns table)
- **Effort:** S (under 1 hour)
- **Priority:** high
- **Source citation:** claude-subagents.md official built-ins table (Explore and Plan rows)

### Recommendation 8: Document subagent worktree isolation and teammate-mode as orchestration levers
- **What:** Two small additions: (a) in `rules/git-workflow.md` Git Worktrees section or `standards/git-worktree.md`, note that subagents support `isolation: "worktree"` in frontmatter, which auto-creates a temp worktree and cleans up if no changes are produced; this is a lighter alternative to the `using-git-worktrees` skill for short-lived subagent work. (b) In `rules/supervisor.md`, note that `--teammate-mode auto|in-process|tmux` selects how agent-team subagents display when the orchestrator fans out, relevant for multi-agent workflows.
- **Why:** Our current worktree guidance is optimized for human-driven work. The subagent frontmatter isolation field is a cheaper pattern for autonomous short work that self-cleans on no-change. Similarly, teammate-mode is a concrete orchestration choice the supervisor rules should name, not leave implicit.
- **Target files:** `/home/byron/dev/.claude/.claude/rules/git-workflow.md`, `/home/byron/dev/.claude/.claude/standards/git-worktree.md`, `/home/byron/dev/.claude/.claude/rules/supervisor.md`
- **Effort:** S (under 1 hour)
- **Priority:** low
- **Source citation:** claude-subagents.md (isolation field), claude-cli-startup-flags.md (teammate-mode flag)

### Recommendation 9: Note `CLAUDE_CODE_SUBAGENT_MODEL` as a cost optimization lever
- **What:** Add a one-line note in `rules/supervisor.md` that subagent work can be routed to a cheaper model via `CLAUDE_CODE_SUBAGENT_MODEL` in the `env` block of `settings.json` (for example `CLAUDE_CODE_SUBAGENT_MODEL=haiku`). Pairs well with our Tier 1/2/3 MCP strategy for keeping per-agent operational cost low.
- **Why:** Our supervisor pattern dispatches work to specialized agents without any cost-awareness guidance. Making the env-var visible in the rule file gives Claude and readers an explicit lever.
- **Target files:** `/home/byron/dev/.claude/.claude/rules/supervisor.md`
- **Effort:** S (under 1 hour)
- **Priority:** low
- **Source citation:** claude-settings.md Model Environment Variables section

## Gemini review pass (summary)

- Gemini flagged that Recommendation 5 (as originally drafted) recommended adopting the subagent-frontmatter `mcpServers:` scope, which directly contradicts `rules/mcp-strategy.md` lines 70-82. That file explicitly routes per-agent MCP bundling through `mcp_config.yaml` plus `scripts/mcp-tool-loader.sh` instead. Revised Rec 5 to contrast the external scope model against our Tier 1/2/3 strategy and state the deviation deliberately.
- Gemini flagged that I missed the `managed-settings.d/` drop-in directory pattern, the explicit `deny -> ask -> allow` permissions evaluation order, the `sandbox.filesystem` / `sandbox.network` architectural layer, and `--teammate-mode`. Added the first three to a consolidated Recommendation 2 (settings + permissions + sandbox rule file) and teammate-mode to Recommendation 8.
- Gemini flagged that I noted Explore and Plan in the comparison table but did not create a recommendation for them. Added Recommendation 7 to pull the read-only built-ins into the supervisor agent assignment table.
- Gemini flagged that Recommendation 6 crossed into Subagent 2's territory by proposing a runnable worked example. Revised Rec 6 to keep the concept-level role documentation and explicitly delegate the runnable implementation to Subagent 2.
- Gemini confirmed the monorepo CLAUDE.md loading recommendation (Rec 4) and the two-pattern skill architecture recommendation (Rec 3) as the strongest concept-level insights and left them intact.

## Authoritative citations found

- Claude Code Docs (https://code.claude.com/docs/en/): sub-agents, slash-commands, skills, memory, mcp, cli-reference, permissions, settings, env-vars, interactive-mode, statusline, channels, amazon-bedrock, agent-teams
- Anthropic engineering blog: "Advanced Tool Use Guide" (https://www.anthropic.com/engineering/advanced-tool-use), "Code Execution with MCP"
- Claude Code CHANGELOG: https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
- Claude Code settings JSON schema: https://json.schemastore.org/claude-code-settings.json
- Boris Cherny on X (Anthropic): CLAUDE.md loading clarification (https://x.com/bcherny/status/2016339448863355206)
- Humanlayer: "Writing a good Claude.md" (https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- Reddit r/mcp community threads: "15 MCP servers, used 4 daily" (https://reddit.com/r/mcp/comments/1mj0fxs/), "5 MCPs that have genuinely made me 10x faster" (https://reddit.com/r/mcp/comments/1qarjqm/)
- Model Context Protocol specification: https://modelcontextprotocol.io/
- Claude Code GitHub settings examples: https://github.com/feiskyer/claude-code-settings
- Shipyard Claude Code CLI cheatsheet: https://shipyard.build/blog/claude-code-cheat-sheet/
