---
title: "Session Handoff: Harness Remediation, PR-1 Done, PR-2 Through PR-5 Remaining"
schema_type: planning
status: draft
owner: core-maintainer
component: Strategy
source: "docs/planning/2026-07-02-harness-remediation-plan.md"
purpose: "Handoff from the cloud session that produced the harness review, the remediation plan, and executed PR-1, so a local session can verify the deferred checks and execute PR-2 through PR-5."
tags:
  - planning
  - architecture
  - hooks
  - agents
  - skills
---

# Session Handoff: 2026-07-02

Written by the cloud session on branch `claude/harness-architecture-review-46bhiz`.
The handoff skill's default output path (`~/.claude/logs/handoffs/`) is
ephemeral in a cloud container, so this doc is committed to the repo instead,
following the `docs/audits/*-handoff-*` precedent.

## Goal / Intent

Make this harness let a smaller runtime model perform closer to a stronger
one. The session produced three artifacts toward that goal: a full
architecture review (findings), a 28-task remediation plan (work order), and
an executed first wave (PR-1: failing checks first, then hook fixes and the
zen/pal dead-reference kill list), run subagent-driven with sonnet workers,
sonnet checklist reviewers, and a haiku sweep, per the plan's Dispatch
Protocol.

## Current State

- Branch: `claude/harness-architecture-review-46bhiz`, clean tree, fully
  pushed (0 unpushed commits as of this doc).
- 15 session commits: `a5f8fce` (review doc) through `f214648` (final PAL
  prose fix). All signed; the stop hook's "Unverified" warnings in this
  container are a local-verification gap only (`gpg.ssh.allowedSignersFile`
  unset here; every commit carries a gpgsig header).
- Tests, all green as of `f214648`:
  `uv run --with pytest-cov pytest --no-cov tests/unit/test_reference_integrity.py tests/unit/test_hook_registration.py` (4 passed);
  `npx --yes bats tests/scripts/test_tdd_enforcement_hook.bats` (5 passed).
- No active errors.

## What Was Done

- `docs/audits/harness-architecture-review-2026-07-02.md`: the review; 14
  sections, findings P1-1 through P3-6.
- `docs/planning/2026-07-02-harness-remediation-plan.md`: the plan; Dispatch
  Protocol, Tasks 0-28, five PR waves, cloud vs local task split.
- PR-1 (plan Tasks 1-9), all on this branch:
  - `tests/unit/test_reference_integrity.py`: gate for retired zen/pal tool
    references (consumer: pytest suite; enforces plan Task 9's outcome).
  - `tests/unit/test_hook_registration.py`: duplicate-registration and
    script-existence gates (consumers: pytest suite; guards hooks.json,
    settings.json, .claude/settings.json).
  - `tests/scripts/test_tdd_enforcement_hook.bats`: five-case opt-in
    contract (consumer: bats; guards scripts/tdd-enforcement-hook.sh).
  - `scripts/tdd-enforcement-hook.sh:17-22,84-91`: opt-in marker gate
    (`.claude/tdd-enforce`) and unknown-language warn fallthrough.
  - `hooks.json`: now the single hook-registration source (gained the
    SessionStart set, tdd, track-mcp, snyk-reminder, keyword-trigger
    entries); five plugin entries rewritten to portable
    `$HOME/.claude/plugin-hooks/` paths with if/then/else existence guards
    that propagate plugin exit codes.
  - `settings.json`: `hooks` key emptied to `{}` (single-source decision).
  - `.claude/settings.json`: duplicate bash-pre-hook entry and the inline
    whole-project `datetime.UTC` grep removed.
  - `scripts/stop-pre-commit-hook.sh:8-16`: scoped to touched files via git
    diff plus untracked; non-repo guard; `--all-files` on Stop is gone.
  - `setup.sh`: `ensure_symlink "${CLAUDE_DIR}/plugin-hooks" "${REPO_DIR}/.submodules/anthropics-plugins/plugins"`.
  - Kill list (commits `a419865` + `f214648`): zero `mcp__pal__`/`mcp__zen__`
    references remain in `.claude/agents|skills|rules`; rad,
    project-planning, and pr-review workflows route through `Skill("panel")`;
    supervisor.md and mcp-strategy.md zen bundle rows corrected; rad model
    roster now points at `panel/data/models.csv`.
  - Deleted: seven orphaned `tests/test_*.bats` files plus
    `tests/helpers/test_helper.bash`.

## What Remains

Ordered; goals are required, mechanisms follow the plan unless a deviation is
noted.

1. GOAL: verify PR-1's two cloud-deferred checks locally (details in How to
   Resume, steps 2-3).
2. GOAL: run `pre-commit run --all-files` on the branch and fix anything it
   flags (pre-commit was not installed in the cloud container; the branch has
   NOT been through the full hook suite).
3. GOAL: execute plan PR-2, Tasks 10-13 (instruction-layer contradictions:
   `git add .` examples, worktree standard, ADR index, superseded MCP
   standard, DRAFT spec relocation, context/ deletion, model roster pointers).
4. GOAL: execute plan PR-3, Tasks 14-16 (routing.md, escalation.md,
   core-directive extension with steering parity across CLAUDE.md, AGENTS.md,
   GEMINI.md; Task 16 takes an opus review).
5. GOAL: execute plan PR-4, Tasks 17-22 (agent frontmatter linter, tool-grant
   fixes, consolidations with opus review on Task 19, skill preconditions and
   caps, catalog registration test, extras fold-in).
6. GOAL: execute plan PR-5, Tasks 23-28 (harness doctor, remaining bats,
   bash-pre-hook gap closure, task-observer split with opus review on Task
   26, architecture doc corrections, staleness sweep).
7. GOAL: file the follow-up issues listed under Gotchas item 6.

## Key Decisions

- All work landed on this one branch instead of the plan's five PR branches,
  because the cloud session may push only to its designated branch. Splitting
  locally is optional; the commits are ordered by wave, so
  `git rebase -i` or cherry-picks onto `fix/hooks-and-references` etc. would
  reconstruct the intended PRs cleanly.
- hooks.json is the single hook-registration source (ADR-002); the committed
  `settings.json` keeps an empty `hooks: {}` rather than dropping the key,
  because the registration test's fallback (`config.get("hooks", config)`)
  crashes on a hooks-less settings file. Intent preserved, gate green.
- TDD enforcement became opt-in per project (marker file
  `.claude/tdd-enforce`) rather than warn-globally, because the review showed
  global enforcement blocked every Go/Rust/PHP edit and every repo without
  test conventions, including this one.
- Plugin existence guards use if/then/else, not `[ -f F ] && run F || echo`,
  because the and/or chain relabels a plugin's legitimate exit-2 block as
  "skipped" with exit 0. Found empirically by a sonnet reviewer; the
  defective form originated in the plan and the review doc and was corrected
  in both.
- Hook-command identity in the registration test keys on the first script
  path in the command, not the last token, because guarded bash -c wrappers
  share trailing shell syntax.

## Dead Ends / Rejected Approaches

- `[ -f F ] && run F || echo skipped` guard form: rejected, swallows
  blocking exit codes (see Key Decisions).
- `cmd.split()[-1]` as hook-command identity: rejected, collides on guarded
  wrappers.
- Removing the `hooks` key from settings.json entirely: rejected, crashes the
  test's fallback path.
- Piping stdin into bats `run` directly: does not work in bats-core; the
  working pattern is `run bash -c 'printf ... | bash "$SCRIPT"' _ <args>`
  (see tests/scripts/test_tdd_enforcement_hook.bats).

## User Corrections / Constraints

- This was a cloud session; the user confirmed elements built for local
  Claude Code (submodules, `~/dev` neighbors, localhost MCP servers) do not
  load here. The plan's Task 0 carries the cloud vs local task split.
- Push only to `claude/harness-architecture-review-46bhiz` from cloud
  sessions on this work.
- Standing repo rules that bound every worker and must keep binding local
  ones: signed conventional commits, stage only listed files (never
  `git add -A` or `.`), no em-dashes, banned-term list in
  `.claude/rules/writing.md`, never weaken a test or gate to make it pass.

## Files Touched

Full list: `git diff --name-only 2ac4524..f214648`. The load-bearing ones and
who consumes them:

- `hooks.json`: read by setup.sh's merge into the live user settings; also
  asserted by tests/unit/test_hook_registration.py.
- `settings.json`, `.claude/settings.json`: read by Claude Code at user and
  project scope respectively; asserted by the same test.
- `scripts/tdd-enforcement-hook.sh`: invoked per Write/Edit via hooks.json;
  contract asserted by tests/scripts/test_tdd_enforcement_hook.bats.
- `scripts/stop-pre-commit-hook.sh`: invoked on Stop via
  `.claude/settings.json`.
- `setup.sh`: run at install time; creates the plugin-hooks symlink the five
  guarded hooks.json commands resolve.
- `.claude/skills/rad/*`, `.claude/skills/project-planning/SKILL.md`,
  `.claude/skills/pr-review/workflows/*`, `.claude/agents/mkdocs-*.md`,
  `.claude/agents/project-plan-synthesizer.md`, `.claude/rules/supervisor.md`,
  `.claude/rules/mcp-strategy.md`: loaded as capabilities/rules by sessions;
  asserted by tests/unit/test_reference_integrity.py.
- `docs/planning/2026-07-02-harness-remediation-plan.md`: the work order for
  everything in What Remains; read by the next session.

## How to Resume

1. Pull and verify base state:
   `git fetch origin && git checkout claude/harness-architecture-review-46bhiz && git pull`
   then `git submodule update --init --recursive` and re-run the wave gates:
   `uv run pytest tests/unit/test_reference_integrity.py tests/unit/test_hook_registration.py --no-cov -q`
   and `bats tests/scripts/test_tdd_enforcement_hook.bats` (local bats; no
   npx needed if bats-core is installed).
2. Verify the plugin-guard happy path (cloud could only test the skip
   branch): run `./setup.sh` (or just the symlink line from it), confirm
   `~/.claude/plugin-hooks/hookify/hooks/pretooluse.py` resolves, then run
   the hookify PreToolUse command from hooks.json with a benign stdin payload
   and confirm the plugin executes rather than printing the skip message, and
   that a nonzero plugin exit propagates.
3. `pre-commit run --all-files`; fix findings (expect markdownlint or
   prose-lint noise on the three new docs at worst; the code changes went
   through review but never through the full hook suite).
4. Decide packaging: either open one PR from this branch, or split into the
   plan's five wave branches (commit ranges are contiguous per wave; see What
   Was Done).
5. Execute PR-2 (plan Tasks 10-13). Every task in the plan is
   self-contained: dispatch per the plan's Dispatch Protocol
   (sonnet workers, controller re-runs gates, checklist review, opus only
   where marked). `docs/planning/2026-07-02-harness-remediation-plan.md`.
6. Continue PR-3 through PR-5 the same way; file the follow-up issues
   (Gotchas item 6) at PR-5 close per the plan's self-review section.

## Gotchas

1. Subset pytest runs trip the repo's 80% coverage gate; use `--no-cov`
   (cov args live in pyproject's addopts). Full-suite CI behavior unchanged.
2. `settings.json` now intentionally has `hooks: {}`. setup.sh's merge is
   what populates live user settings from hooks.json; do not "fix" the empty
   object back to a hook list.
3. Editing `.claude/settings.json` changes live project hooks for the next
   session in this repo; the removed inline datetime.UTC grep is covered by
   `scripts/py310-compat-check.sh` (registered in hooks.json).
4. `docs/superpowers/plans/` is gitignored (line 363); the remediation plan
   deliberately lives at `docs/planning/2026-07-02-harness-remediation-plan.md`.
   The writing-plans skill's default save path will silently produce
   untracked plans; this is finding-adjacent but unfixed.
5. The stop hook nags about unverified signatures in containers without an
   allowedSignersFile; check `git cat-file -p <sha> | grep -c gpgsig` before
   believing it.
6. Follow-up issues to file (deferred by explicit plan decision):
   OSSF agent-pair merge; catalog auto-generation (a registration-coverage
   test lands in plan Task 21 instead); LLM-judged evals (review 10.2
   E-GOLD/E-ADV/E-CTX/E-HAND); skill frontmatter normalization; stale
   `/home/byron` example paths; `ai-detection-landscape.md` quarterly
   refresh; stale `consensus/scripts/consensus_cli.py` path at
   pr-review.md:44 and :1528 (real script:
   `.claude/skills/panel/scripts/consensus_cli.py`); hook-pipeline.md's stale
   `CLAUDE_PLUGIN_ROOT` narrative `[VERIFY]` (reviewer-reported at line ~106,
   not independently confirmed; plan Task 27 covers it).
7. rad's verify.md now uses capability-band phrasing (premium reasoning
   model, strong free reasoning model) with the roster in
   `panel/data/models.csv`; if a local session finds the phrasing awkward in
   practice, that is a meaning-preservation judgment call flagged during
   review, not an accident.
8. The plan's Task 8 command text was corrected in place (if/then/else); if
   you diff the plan against an older recollection of it, the guard form
   changed deliberately.

## Next-Session Kickoff Prompt

Resuming work on ByronWilliamsCPA/.claude
(branch `claude/harness-architecture-review-46bhiz`). Goal: finish the
harness remediation plan locally; PR-1 (plan Tasks 1-9) is done and pushed
from a cloud session.

First, refresh state before acting (the handoff is a snapshot; treat What
Remains as a hypothesis):
`git fetch origin && git checkout claude/harness-architecture-review-46bhiz && git pull && git submodule update --init --recursive && git status --short && git log --oneline -16`

Immediate next actions, in order: (1) re-run the wave gates
(`uv run pytest tests/unit/test_reference_integrity.py tests/unit/test_hook_registration.py --no-cov -q`
and `bats tests/scripts/test_tdd_enforcement_hook.bats`); (2) verify the
plugin-guard happy path with submodules present; (3) `pre-commit run
--all-files`; (4) execute plan PR-2 (Tasks 10-13) per the Dispatch Protocol
in `docs/planning/2026-07-02-harness-remediation-plan.md`.

Hard constraints: signed conventional commits; stage only listed files; no
em-dashes; never weaken a gate; opus review on plan Tasks 16, 19, 26.

Full handoff (read on demand):
`docs/audits/harness-remediation-handoff-2026-07-02.md`.
