# Skills Deep Dive: Non-Ignored Repos vs. What We Already Have

**Date:** 2026-06-18
**Companion to:** `skills-repos-survey-2026-06.md`
**Method:** one research agent per repo, each reading our actual native
`SKILL.md`/agent files on disk and comparing against upstream skill *bodies*
content-by-content (not by name). Findings below are corrected by the author for
the integration architecture (next section), which the agents could not see
because the submodules are not checked out in this container.

> External README/skill text treated as untrusted data (OWASP LLM01).

## The integration architecture (verified on disk)

Our config does **not** copy most external skills. It vendors source repos as
git submodules under `.submodules/` and **symlinks** individual skills into
`.claude/skills/<name>`:

```text
.claude/skills/brainstorming -> ../../.submodules/superpowers/skills/brainstorming
.claude/skills/docx          -> ../../.submodules/anthropics-skills/skills/docx
.claude/skills/skill-creator  -> ../../.submodules/anthropics-skills/skills/skill-creator
.claude/skills/writing-rules  -> ../../.submodules/anthropics-plugins/plugins/hookify/skills/writing-rules
```

In this ephemeral container the submodules are not `git submodule update --init`'d,
so those symlinks dangle and several agents reported the targets as "missing."
On a real checkout they resolve. This changes the conclusions: **skills already
symlinked are present, not gaps, and must not be "ported."**

### Already present via symlink (DO NOT port; they are live)

| Source submodule | Skills symlinked in |
| --- | --- |
| superpowers | brainstorming, executing-plans, subagent-driven-development, systematic-debugging, finishing-a-development-branch, requesting-code-review, verification-before-completion, using-superpowers, writing-skills |
| anthropics-skills | docx, pdf, pptx, xlsx (proprietary; symlink is the *only* licit path), skill-creator |
| anthropics-plugins | claude-automation-recommender, claude-md-improver, session-report, writing-rules (hookify) |
| jeffallan-claude-skills | fastapi-expert |

### Deliberate forks (real native copies, intentionally ahead of upstream)

`writing-plans`, `test-driven-development`, `receiving-code-review`,
`dispatching-parallel-agents`, `using-git-worktrees`. Each carries
project-specific additions (RAD tags, our observations, `.worktrees/` policy,
AI-branch review notes) that direct symlinking would regress. Keep maintaining
these as forks.

## Per-repo verdicts (corrected)

### 1. obra/superpowers (already a submodule)

Nothing to port. 9 skills are live via symlink; 5 are forks we keep. The only
actionable items are maintenance, not adoption:

- **`using-git-worktrees` fork is behind upstream.** Upstream added a "Step 0:
  Detect Existing Isolation" pass (`git rev-parse --git-dir/--git-common-dir/
  --show-superproject-working-tree`) that prevents nested-worktree and
  in-submodule false positives. Our fork lacks it and still lists
  `~/.config/superpowers/worktrees/` as a valid path, which contradicts our
  `git-workflow.md` `.worktrees/<slug>`-only rule. **Fix: port Step 0, delete
  the global-path option.**
- **Submodule pin is stale vs upstream v6.** The pin predates the June 2026 v6
  rewrite. Decide whether to `git submodule update --remote` for the symlinked
  skills, balanced against re-validating our 5 forks against v6. Pin to a release
  tag, not `main` HEAD.

### 2. anthropics/skills (already a submodule)

`skill-creator` and the four document skills are already symlinked. The four
document skills are **proprietary/source-available** (no redistribution), so the
symlink-from-submodule is the only permissible access path; never copy them into
native files. Genuine Apache-2.0 gaps not currently symlinked, worth adding (port
or symlink the specific skill dir):

| Skill | License | Status | Action |
| --- | --- | --- | --- |
| `mcp-builder` | Apache-2.0 | No equivalent (we *use* MCP, no build-a-server guide) | ADD (symlink or port) |
| `claude-api` | Apache-2.0 | Partial (`ai-engineer` agent lacks current model IDs/SDK/caching) | PORT into ai-engineer or add skill |
| `algorithmic-art` | Apache-2.0 | No generative-art capability | LOW priority |
| `web-artifacts-builder` | Apache-2.0 | `frontend-design` lacks the single-file bundle pipeline | OPTIONAL |
| `webapp-testing` `with_server.py` pattern | Apache-2.0 | `ui-testing-agent` lacks server-lifecycle manager | ADD to `testing/workflows/e2e.md` |

Skip as duplicates (ours are supersets): `frontend-design`, `doc-coauthoring`
(our 7-agent `writing` pipeline), `skill-creator` (already symlinked).

### 3. mattpocock/skills (not vendored)

TypeScript-centric; our config is Python-centric. After removing overlaps with
our symlinked superpowers skills, the genuine gaps are narrower than the survey
implied:

| Upstream skill | Status vs ours | Action |
| --- | --- | --- |
| `domain-modeling` (live CONTEXT.md glossary, terminology-drift challenge) | GAP | **PORT** |
| `triage` (issue/PR triage state machine) | GAP | PORT (strip TS) |
| `prototype` (throwaway-to-answer-one-question) | GAP | PORT |
| `git-guardrails-claude-code` (PreToolUse hook blocking force-push/hard-reset) | Enforcement gap; but we have hookify + settings.json `ask` | Implement as a **hookify rule**, not a skill |
| `to-issues` / `to-prd` (conversation -> filed GitHub issue) | Complementary; converges with gstack `/spec` | PORT **one** issue-gen skill |
| `diagnosing-bugs` | Largely covered by symlinked `systematic-debugging` | SKIP (borrow hypothesis-first framing only) |
| `grilling`/`grill-me` | Overlaps `brainstorming` (symlinked) | SKIP (see convergence cluster) |
| `tdd`, `handoff`, `writing-great-skills`, `ask-matt` | Ours equal/better | SKIP |
| `setup-pre-commit`, `migrate-to-shoehorn`, `scaffold-exercises`, `teach` | TS-locked / out of scope | SKIP |

### 4. garrytan/gstack (not vendored)

~50 slash-commands; most value is locked behind a Bun browser daemon, GBrain/
Supabase, compiled binaries, or iOS tunneling (all SKIP-infra-locked). The
prompt-only role skills are the value:

| Skill | Status vs ours | Action |
| --- | --- | --- |
| `/retro` (engineering analytics from git history; per-author velocity, cross-project) | No equivalent | **PORT** (unique) |
| `/plan-ceo-review`, `/plan-devex-review` (founder/DX-mode plan challenge) | `plan-validator` checks completeness, not problem-framing | PORT as agents |
| `/office-hours` (premise interrogation before any spec) | Partially covers `brainstorming` | PORT (convergence cluster) |
| `/spec` (utterance -> filed GitHub issue + PII/secret redaction gate) | No equivalent; converges with mattpocock `to-issues` | PORT one issue-gen skill |
| `/health` (weighted dashboard over type/lint/test/dead-code) | We run `quality`+`test-coverage`+`sonarcloud` separately | PORT (aggregator) |
| `/freeze` (dynamic per-session directory scope-lock) | settings.json is static/global | Implement via hook; MEDIUM |
| `/design-review` AI-slop rubric (named blacklist + A-F across 10 categories) | Absent from frontend pipeline | Inject rubric into `frontend-designer` agent (cheap) |
| `/document-generate` Diataxis partitioning | `documentation-writer` lacks it | Add to that agent (cheap) |
| `/investigate` | Largely covered by symlinked `systematic-debugging` (also has 3-strike escalation) | SKIP / borrow scope-lock idea |
| `/review`, `/cso`, `/codex`, `/careful`, `/context-save`, `/ship`, `/setup-deploy` | Duplicate `pr-review`, owasp suite, `consensus`, settings.json, `handoff`, `git`, `devops-deployment-agent` | SKIP |

### 5. nextlevelbuilder/ui-ux-pro-max-skill (not vendored)

Our `frontend-design` skill **already credits this repo as a source** and inlines
its 99 UX guidelines. So the skill itself is a SKIP (already absorbed). The
net-new asset is the curated CSV knowledge our skill does not carry:

- **EXTRACT-DATA** into `.claude/skills/frontend-design/context/`: `styles.csv`
  (67 styles x21 cols), `colors.csv` (161 product-type palettes), `typography.csv`
  (57 font pairings), `products.csv` + `ui-reasoning.csv` (161 product-type
  patterns), `charts.csv` (25 chart types w/ a11y grades). Drop the `search.py`
  BM25 runtime; static files are referenceable directly by the model.
- Optional new design sub-skills (`brand`, `design-system`, `slides`,
  `banner-design`) are genuine gaps but LOW priority for a dev-centric config.

### 6. Egonex-AI/Understand-Anything (not vendored)

No skills to compare; it is a compiled TS/WASM plugin. Unchanged verdict: **RUN
STANDALONE** via the plugin marketplace per-project if codebase-onboarding
knowledge graphs are ever needed. Nothing to port.

## Convergence signals (multiple independent repos arrived at the same gap)

These are the highest-confidence gaps because 2-3 repos built the same thing and
we lack it:

1. **Premise interrogation before spec**: gstack `/office-hours`, mattpocock
   `grilling`/`grill-me`, addyosmani `interview-me`/`idea-refine`. Our symlinked
   `brainstorming` only partially covers (it moves toward a spec; these hold the
   pen back and interrogate demand/scope first). Port **one** interrogation skill
   or strengthen brainstorming with a pre-spec gate.
2. **Conversation -> filed GitHub issue**: gstack `/spec`, mattpocock
   `to-issues`/`to-prd`. We write plan docs to disk, never to the issue tracker.
   Port **one** issue-generation skill (with the PII/secret redaction gate from
   `/spec`).
3. **Anti-rationalization tables**: addyosmani uses excuse/rebuttal tables in 4
   skills; our `test-driven-development` already uses one. Adopt cross-cutting.

## Consolidated recommendation (deduplicated, ranked)

### Tier 1: pure production-ops gaps (highest net-new, addyosmani)

Nothing in superpowers/anthropics/native covers these:

1. `observability-and-instrumentation` (structured logs, RED/USE metrics,
   correlation IDs, cardinality discipline, percentile alerting)
2. `deprecation-and-migration` (strangler/adapter/feature-flag, churn rule)
3. `performance-optimization` (measure-first, N+1, profiling-before-change)
4. `shipping-and-launch` (canary %, rollback triggers, flag lifecycle) +
   gstack `/land-and-deploy` post-deploy verification loop
5. `source-driven-development` (version-detect + cite official docs; note
   context7 MCP already does the retrieval step)

### Tier 2: reasoning/quality enhancements (cheap, high-leverage)

6. `doubt-driven-development` (addyosmani): adversarial fresh-context review
   layer that complements RAD; cross-reference from `rad/SKILL.md`
7. `context-engineering` (addyosmani): five-tier context hierarchy + trust
   levels + confusion-management; upgrades every multi-file session
8. Anti-rationalization tables: add to `rad`, `debug-tests`, `security`
9. gstack `/design-review` AI-slop rubric -> into `frontend-designer` agent
10. gstack Diataxis discipline -> into `documentation-writer` agent

### Tier 3: planning/discovery cluster (convergent; targeted ports)

11. One **premise-interrogation** skill (merge office-hours + grilling +
    interview-me)
12. `plan-ceo-review` + `plan-devex-review` strategic review agents (gstack)
13. `domain-modeling` CONTEXT.md glossary (mattpocock)
14. One **issue-generation** skill (gstack `/spec` ~ mattpocock `to-issues`)

### Tier 4: workflow/analytics (gstack + mattpocock)

15. `/retro` git-history engineering analytics (unique)
16. `/health` quality dashboard aggregator
17. `triage` issue triage (mattpocock); `prototype` (mattpocock); `/freeze`
    directory scope-lock (gstack, via hook)
18. `git-guardrails` PreToolUse hook -> implement as a **hookify rule**

### Tier 5: design data (ui-ux-pro-max)

19. Extract the 6 CSV catalogs into `frontend-design/context/`
20. Optional `brand`/`slides`/`banner`/`design-system` sub-skills (low priority)

### Maintenance items (not adoption)

- Port superpowers `using-git-worktrees` Step 0 into our fork; remove the global
  `~/.config/superpowers/` path option.
- Decide on bumping the superpowers/anthropics submodule pins to current upstream
  (v6), then re-validate our 5 forks against the new upstream.
- For anthropics document skills: confirm they stay symlink-only (license).

### Explicitly do NOT port (already covered)

`/review`, `/cso`, `/codex`, `/careful`, `/context-save`, `/ship`,
`/setup-deploy` (gstack); `tdd`, `handoff`, `setup-pre-commit`, `ask-matt`
(mattpocock); `security-and-hardening`, `code-review-and-quality`,
`ci-cd-and-automation`, `git-workflow-and-versioning`, `frontend-ui-engineering`,
`planning-and-task-breakdown`, `test-driven-development`, `using-agent-skills`
(addyosmani); `frontend-design`, `doc-coauthoring` (anthropics); the entire
gstack browser-daemon / GBrain / iOS / compiled-binary surface.

## Suggested sequencing

Open `feat/skills-gap-port` and land in three small PRs to stay under the p90
size line: (1) Tier 1 production-ops skills, (2) Tier 2 reasoning enhancements +
the two cheap agent-rubric injections, (3) the convergence-cluster ports (one
interrogation skill, one issue-gen skill, domain-modeling, retro). Record source
URL + commit SHA + MIT/Apache attribution in each ported file. Do the
`using-git-worktrees` Step 0 fix and the submodule-pin decision as a separate
maintenance PR.
