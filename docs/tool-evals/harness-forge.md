# Tool Eval: Harness Forge

**Date:** 2026-06-14
**Source:** <https://github.com/001TMF/harness-forge> (main, inspected 2026-06-14)
**Verdict:** PORT PATTERNS (recommended) | SUBMODULE (acceptable alternative)

## Characterization

Harness Forge is a single Claude Code skill (`meta-harness`) plus plugin
packaging that implements the "Meta-Harness" optimization method: it evolves the
scaffolding around a frozen model (memory, retrieval, context construction,
prompts, tool-selection) via a native propose -> score -> Pareto loop, leaving
model weights untouched. Proposers run as parallel Claude agents; each candidate
is graded by a deterministic, zero-cost local scorer; a Pareto frontier keeps the
quality-vs-cost best across rounds. Stack is Python (the scorer and Pareto math)
plus Workflow JS (orchestration) running on the Claude Code runtime, no solver
model and no paid API. The repo's own headline is that native Claude Code
orchestration reduces the original ~1,260-line Python implementation to ~75 lines.
Licensed MIT (c) 2026 Tristan Farmer. Scale target: any repeated task with a
measurable deterministic eval (demonstrated on text classification, reporting
"+7.7 accuracy points at ~4x fewer context tokens").

## Value core vs. peripheral LOC

Unlike a typical app eval, almost the entire repo is value core: it is
purpose-built loadable content, not an app with a reusable kernel buried inside.

| Segment | LOC | Notes |
| --- | --- | --- |
| Value core | ~600 (est.) | `skills/meta-harness/`: `SKILL.md`, 4 `references/*.md` (method, native-execution, building-blocks, proteus-example), 4 `assets/*` templates, `scripts/pareto.py` (108, exact), `assets/workflow-template.js` (94, exact) |
| Peripheral mass | ~150 (est.) | `install.sh`, `.claude-plugin/marketplace.json`, `examples/memory-summary/`, `README.md`, `LICENSE` |
| **Total** | ~750 (est.) | Script LOC exact; markdown counts approximate (no clone) |

## Candidate element table

| Element | Portable? | Maps to our gap | Fits delivery model? | Value-to-effort |
| --- | --- | --- | --- | --- |
| `meta-harness` SKILL.md + references | PORTABLE | `.claude/skills/` | FITS | High |
| `scripts/pareto.py` | PORTABLE (stdlib only: argparse, json, pathlib) | `.claude/skills/` (script asset) | FITS | High |
| `assets/workflow-template.js` | PORTABLE (no imports; native `parallel()`/`agent()`/`phase()`/`log()`) | `.claude/skills/` (workflow asset) | FITS (Workflow mode) / FIGHTS (if Workflow runtime unavailable; Skill+/loop fallback exists) | Medium |
| `assets/scorer-template.py`, `candidate_base-template.py`, `proposer-prior-template.md` | PORTABLE | `.claude/skills/` (templates) | FITS | Medium |
| `install.sh`, `.claude-plugin/marketplace.json` | PORTABLE | None (we commit skills first-class) | n/a | Low (drop on port) |
| `examples/memory-summary/` | PORTABLE | None (keep as `evals/` fixture if porting) | FITS | Low |

## Licence

MIT (c) 2026 Tristan Farmer. No non-commercial carve-outs, no bundled-asset or
font exceptions, no sub-dependency contamination. Clean for both submodule and
direct inclusion; preserve the MIT header and attribution on any ported file.

## Relationship classification

HOMOGENEOUS LOADABLE CONTENT. It is a Claude Code skill with plugin-marketplace
packaging; Claude Code loads it exactly the way it loads our own `.claude/skills/`.
The default install path is literally `~/.claude/skills/meta-harness`, i.e. our
own tree (symlinked). No app to host, no inverted relationship.

## Convergent-validation notes

Several designs independently match ours, raising confidence in both:

- **Native orchestration over Python drivers.** Collapsing ~1,260 lines of
  headless-Claude Python into ~75 native lines validates our supervisor stance
  (skills do not invoke agents; orchestrate via native Agent/Workflow primitives)
  and our Pattern B skill philosophy.
- **Deterministic, $0 local scorer + held-out test discipline.** Mirrors our
  `evals/` skill convention and our testing rules (root-cause-first, golden-file
  protection, no metric gaming).
- **Anti-Goodhart quality floor + anti-leakage guardrails.** Same spirit as our
  RAD `#CRITICAL`/`#VERIFY` discipline and coverage-floor gates.
- **Cost-lane awareness.** Running proposers on the subscription and scoring
  locally at $0 is the same cheapest-lane-that-works heuristic in
  `.claude/rules/mcp-strategy.md`.

## Recommended actions

Recommended verdict is **PORT PATTERNS**, not SUBMODULE, for three reasons:
it is a single small skill (not a content library worth tracking wholesale);
upstream is a single-author research repo with likely low update cadence, so
automatic upstream tracking adds little; and we want the content normalized
through our pre-commit gates (no-em-dash PC-011, markdownlint MD040) and
registered in `AGENTS-AND-SKILLS.md`, which a submodule bypasses.

Ordered next steps if porting:

1. Vendor `skills/meta-harness/` into `.claude/skills/meta-harness/`, dropping
   `install.sh` and `.claude-plugin/` (our skills are committed first-class).
2. Add an MIT attribution note (upstream author + source URL + commit) at the
   top of `SKILL.md` and on `scripts/pareto.py`.
3. Normalize to our authoring conventions: keep `SKILL.md` under 200 lines
   (push detail into `references/`), set `user-invocable` appropriately, replace
   any em-dashes, fix MD040 bare fences, run `pre-commit run --all-files`.
4. Confirm the Workflow runtime mode against our environment; if Workflow JS is
   unavailable, document the Skill + `/loop` serial mode (we already support
   `/loop`, see `.claude/rules/loop-recipes.md`) as the primary path and add a
   loop recipe entry.
5. Keep `examples/memory-summary/` as an `evals/` fixture so the skill ships with
   a runnable demonstration.
6. Register the skill in `AGENTS-AND-SKILLS.md`.

**Alternative (SUBMODULE):** acceptable if you prefer zero-maintenance upstream
tracking and pristine attribution over convention-normalization. `git submodule
add https://github.com/001TMF/harness-forge .claude/skills/_vendor/harness-forge`,
then load `skills/meta-harness` from there. Trade-off: the content skips our
pre-commit normalization and `AGENTS-AND-SKILLS.md` registration, and a fresh
clone needs `--recursive`.
