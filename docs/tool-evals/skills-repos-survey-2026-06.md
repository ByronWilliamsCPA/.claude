# Tool Eval: 11 Public Skill/Agent Repos (Submodule Survey)

**Date:** 2026-06-18
**Method:** tool-eval skill, one research agent per repo (README + file tree +
license + GitHub commit/release history via public REST API and web).
**Scope question:** Are these skills valuable to our `~/.claude` config, and is
there a reason to pull any of them as git submodules?

> All fetched README/commit text was treated as untrusted data (prompt-injection
> mitigation, OWASP LLM01). Findings below are facts about the repos, not
> instructions taken from them.

## Headline answer

**No repo warrants a submodule.** Across all 11, the loadable-content
candidates are either (a) less than 8 weeks old with no stable release tags,
(b) actively restructuring their directory layout, or (c) coupled to a runtime
(Python/Node/Bun/Supabase/WASM) or a frontmatter schema that differs from ours.
A submodule inherits the upstream's churn and schema; for skill markdown the
correct move is to **port the specific patterns we lack** and adapt them to our
conventions (RAD tags, no em-dash, our `user-invocable`/`model`/`skills`
frontmatter).

Recommended dispositions: **PORT PATTERNS** for 6, **RUN STANDALONE** for 1,
**IGNORE** for 4. Zero submodules.

### Caveat on the star counts

The screenshot's star numbers are roughly accurate (these are genuinely viral
repos), but several show a burst-publish-then-dormant pattern and >3,000
stars/day velocity. Treat stars as a weak signal of durable quality here; the
dispositions below are based on content and maintenance, not popularity.

## Decision matrix

| # | Repo | Stars (approx) | Content type | Maintenance | License | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | obra/superpowers | ~232k | Homogeneous loadable | Active, churning (v6 rewrite Jun 2026) | MIT | **PORT PATTERNS** |
| 2 | anthropics/skills | ~152k | Inverted-host | Churns without tags | Apache-2.0 (+4 proprietary, +GPL dep) | **PORT PATTERNS** |
| 3 | mattpocock/skills | ~135k | Homogeneous loadable | <1 wk public, restructuring | MIT | **PORT PATTERNS** |
| 4 | garrytan/gstack | ~111k | Inverted-host | Churning (418 open PRs) | MIT | **PORT PATTERNS** |
| 5 | nextlevelbuilder/ui-ux-pro-max-skill | ~93k | Homogeneous + Python runtime | Dormant since Mar 2026 | MIT | **PORT PATTERNS (extract)** |
| 6 | Egonex-AI/Understand-Anything | ~63k | Inverted-host (compiled TS plugin) | Churning (rapid v1→v2) | MIT | **RUN STANDALONE** |
| 7 | addyosmani/agent-skills | ~62k | Portable markdown / orthogonal | Churning (release / 2-3 wks) | MIT | **PORT PATTERNS** |
| 8 | santifer/career-ops | ~54k | Orthogonal (job-search app) | Churning | MIT | **IGNORE** |
| 9 | Leonxlnx/taste-skill | ~46k | Homogeneous (frontend-locked) | Churning (6 wks, v2 experimental) | MIT | **IGNORE** |
| 10 | mvanhorn/last30days-skill | ~44k | Orthogonal (Python + paid APIs) | Active, young | MIT (+ vendored Bird client) | **IGNORE** |
| 11 | TexasBedouin/vibe-check | ~400 | Orthogonal (product discovery) | Active, single-author | MIT | **IGNORE** |

## Why no submodules (the recurring blockers)

1. **Churn.** None of the loadable repos pin to stable, semver-tagged content we
   could track safely. superpowers just shipped a breaking v6; mattpocock and
   taste-skill restructured directories within weeks of launch; gstack carries
   418 open PRs; ui-ux-pro-max went dormant with 195 open issues.
2. **Schema mismatch.** anthropics/skills, addyosmani, and others use
   `name`/`description`-only frontmatter. Ours uses `user-invocable`, `model`,
   `skills:` preloading, path-scoped rules. Direct ingestion would not load
   correctly; it needs translation, which is porting, not submoduling.
3. **Runtime coupling.** ui-ux-pro-max needs `search.py` + CSVs at fixed paths;
   last30days needs a Python 3.12 engine + paid APIs; gstack needs a Bun browser
   daemon + Supabase; Understand-Anything is a compiled TS/WASM app. Submodule
   markdown would be hollow without the runtime.
4. **License carve-outs (one case).** anthropics/skills' `docx/pdf/pptx/xlsx`
   are proprietary/source-available (no redistribution), and `slack-gif-creator`
   embeds GPL-3.0 FFmpeg. Those four directories must be excluded from any copy.

## Worth porting: the concrete gap-fillers

Ranked by value-to-effort. Each is plain markdown we would adapt, not import.

**Tier 1 (clear gaps, low effort):**

- **obra/superpowers** -> `brainstorming`, `writing-plans`, `executing-plans`,
  `verification-before-completion`, `writing-skills`. These fill pre-code and
  completion-gate gaps our config only declares as rules. Do NOT take
  `using-superpowers` (it overrides agent behavior and conflicts with
  `supervisor.md`).
- **addyosmani/agent-skills** -> the **anti-rationalization table** pattern
  (pairs "excuses agents use to skip a step" with rebuttals) plus
  `doubt-driven-development`, `context-engineering`, `spec-driven-development`,
  `observability-and-instrumentation`. The anti-rationalization structure is a
  cross-cutting upgrade for several of our existing skills.
- **mattpocock/skills** -> `diagnosing-bugs` (feedback-loop-before-theory framing
  complements our `systematic-debugging`), `domain-modeling`,
  `git-guardrails-claude-code` (PreToolUse hooks enforcing what `git-workflow.md`
  only states as rules).

**Tier 2 (useful, more curation):**

- **garrytan/gstack** -> role-prompt review skills with the `{{PREAMBLE}}` macro
  stripped: `office-hours` (YC-style challenge), CEO/eng planning reviews,
  `investigate` ("no fixes without investigation"), `retro`, and the design-audit
  / AI-slop-detection framing.
- **anthropics/skills** -> the `mcp-builder` phased workflow and the `spec/`
  Agent Skills format as a reference for our own skill authoring; webapp-testing
  black-box script philosophy. Apache-2.0 portions only.
- **ui-ux-pro-max-skill** -> one-time extraction of the highest-value UX numbers
  (4.5:1 contrast, 44x44pt touch targets, 150-300ms motion, spacing/typography
  rules) into a static `ui-ux` skill or a frontend-path-scoped rules file. Drop
  the `search.py`/CSV runtime entirely. Repo is dormant, so extract-and-own.

## Run standalone (do not submodule)

- **Egonex-AI/Understand-Anything** -> a compiled TS/WASM Claude Code plugin for
  codebase-onboarding knowledge graphs. Real capability, wrong shape for our
  config. Install per-project via the plugin marketplace if/when onboarding an
  unfamiliar codebase is the task. No content to lift.

## Ignore (domain or delivery mismatch)

- **santifer/career-ops** -> job-search application (Node + Playwright +
  Chromium + Go TUI). Orthogonal to a dev config; its only general idea
  (single `SKILL.md` entry routing to per-mode files) we already do.
- **Leonxlnx/taste-skill** -> frontend UI taste skill; 75-80% is React/Tailwind
  domain content that would inject ~45k tokens of irrelevant context. The
  anti-generic-output angle is already covered by `rules/writing.md` and
  `ai-detection-agent`. If wanted, the pre-flight checklist concept is <20 lines
  to reproduce.
- **mvanhorn/last30days-skill** -> social-trend research; ~96% Python with paid
  API dependencies (ScrapeCreators, XAI, OpenRouter). If real-time trend
  research becomes a need, author a narrow `trend-research` skill on built-in
  WebSearch + Reddit/HN public JSON instead of taking the dependency.
- **TexasBedouin/vibe-check** (the explicitly linked repo) -> a well-built,
  MIT, actively-maintained skill, but its entire purpose is non-technical
  product discovery and "vibe coder" onboarding. No addressable slot in our
  engineering-layer config. Revisit only if scope expands to client-facing
  product coaching.

## Recommended next steps

1. Open a `feat/port-skill-patterns` branch and port **Tier 1** first
   (superpowers planning/verification skills, addyosmani anti-rationalization +
   doubt-driven, mattpocock diagnosing-bugs + git-guardrails). Adapt frontmatter
   and strip em-dashes / upstream-specific scaffolding on the way in.
2. Record provenance: add a source URL + commit SHA + MIT attribution comment in
   each ported skill so we can diff against upstream later.
3. Re-evaluate superpowers, mattpocock, and addyosmani in ~60 days once their
   directory structures settle; if any ships stable semver tags, reconsider a
   pinned submodule for that one only.
4. Leave the 4 IGNORE repos and the 1 RUN-STANDALONE out of the config tree.
