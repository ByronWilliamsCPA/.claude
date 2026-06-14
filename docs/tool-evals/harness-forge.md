# Tool Eval: Harness Forge

**Date:** 2026-06-14
**Source:** <https://github.com/001TMF/harness-forge> (main, inspected 2026-06-14; v1.0.0, MIT, Tristan Farmer)
**Verdict:** PORT PATTERNS (vendor the single skill into our tree and adapt to conventions). SUBMODULE is a viable alternative if zero-maintenance upstream tracking is preferred over normalization.

## Characterization

Harness Forge is a Claude Code skill (`meta-harness`) packaged as a plugin. It
implements the "Meta-Harness" method: optimize the scaffolding around a frozen
model (memory, retrieval, context construction, prompts, tool selection) via a
native propose -> validate -> score -> Pareto-merge -> repeat loop. Proposer
agents write candidate harness variants, a deterministic local scorer evaluates
each at $0 (no LLM, no network), and a Pareto frontier keeps the quality-vs-cost
best. The stated headline result is "+7.7 accuracy points at ~4x fewer context
tokens" on text classification, a pure harness-side gain. The notable engineering
claim is that native Claude Code orchestration (Agent/Workflow primitives)
replaced roughly 1,260 lines of the original Python implementation with about 75.
Stack: Python (stdlib scorer plus Pareto computation), framework-free Workflow
JS, and markdown skill/reference content.

## Value core vs. peripheral LOC

Unlike a typical app eval, almost the entire repo is value core. There is no UI,
blog, or marketing mass, because the repo is purpose-built loadable content.

| Segment | LOC | Notes |
| --- | --- | --- |
| Value core | ~600-900 | `skills/meta-harness/SKILL.md`; `references/` (method, native-execution, building-blocks, proteus-example); `assets/` (workflow-template.js = 94, scorer-template.py, candidate_base-template.py, proposer-prior-template.md); `scripts/pareto.py` = 108 |
| Peripheral mass | ~100 | `install.sh`, `.claude-plugin/marketplace.json`, `examples/memory-summary/`, `README.md`, `LICENSE` |
| **Total** | ~700-1000 | Exact counts: `pareto.py` 108, `workflow-template.js` 94; remainder estimated from directory inspection without a full clone |

## Candidate element table

| Element | Portable? | Maps to our gap | Fits delivery model? | Value-to-effort |
| --- | --- | --- | --- | --- |
| `meta-harness` SKILL.md + references | PORTABLE (markdown) | `.claude/skills/` (no existing scaffolding-optimization skill) | FITS | High |
| `scripts/pareto.py` | PORTABLE (stdlib only: argparse, json, pathlib) | `.claude/skills/meta-harness/scripts/` | FITS | High |
| `assets/workflow-template.js` | PORTABLE (zero imports; native `parallel`/`agent`/`phase`/`log` primitives only) | `.claude/skills/.../assets/` | FITS (Workflow default mode); degrades to Skill+`/loop` if Workflow JS runtime is unavailable | Medium |
| `assets/*-template.py/.md` | PORTABLE | template scaffolding for the skill | FITS | Medium |
| `install.sh` + `.claude-plugin/marketplace.json` | PORTABLE | None (our skills are committed first-class; install path `~/.claude/skills/` is already our repo) | N/A | Low (drop) |
| `examples/memory-summary/` | PORTABLE | None (illustrative; optional to vendor as a worked example) | FITS | Low |

## Licence

MIT (c) 2026 Tristan Farmer. No non-commercial carve-outs, no bundled-asset or
font exceptions, no sub-dependency restrictions. Clean for direct inclusion;
preserve the copyright notice on any vendored files.

## Relationship classification

HOMOGENEOUS LOADABLE CONTENT. Claude Code loads this skill exactly the way it
loads our own `.claude/skills/`; the upstream install target is literally
`~/.claude/skills/meta-harness`, which is our repo. This is the class where a
submodule is structurally appropriate.

## Convergent-validation notes

- **Native orchestration over Python drivers.** Collapsing ~1,260 Python lines
  to ~75 native lines by using Agent/Workflow primitives validates our Pattern B
  philosophy and the supervisor rule that skills orchestrate natively rather than
  shelling out to headless drivers.
- **Deterministic, $0, no-network scorer with held-out discipline.** Mirrors our
  `evals/` skill-directory convention and our testing discipline (held-out split
  touched exactly once; anti-Goodhart quality floor).
- **Three execution modes (Workflow / Skill+`/loop` / Team).** Maps directly onto
  primitives we already document: `/loop` recipes and agent teams. The skill
  arrived independently at the same lane choices we use.

## Recommended actions

1. **Vendor the skill** into `.claude/skills/meta-harness/` (copy SKILL.md,
   `references/`, `assets/`, `scripts/pareto.py`). Keep the MIT copyright header
   on vendored files and add a one-line provenance note (source URL + commit) at
   the top of SKILL.md.
2. **Normalize to our conventions:** run `pre-commit run --all-files` (no-em-dash
   PC-011, markdownlint MD040, yamllint), keep SKILL.md under 200 lines (move
   overflow into `references/`), and confirm `user-invocable` is set correctly
   (this is a Pattern B tool-invoked workflow, so leave it user-invocable).
3. **Register** the skill in `AGENTS-AND-SKILLS.md`.
4. **Drop the plumbing:** do not vendor `install.sh` or `.claude-plugin/` (our
   skills are committed first-class, not installed via marketplace). Optionally
   keep `examples/memory-summary/` as a worked example under the skill's
   `references/` or `evals/`.
5. **Alternative if low maintenance is preferred over normalization:**
   `git submodule add https://github.com/001TMF/harness-forge` and load via the
   plugin mechanism. This preserves attribution and auto-tracks upstream, but the
   content bypasses our pre-commit normalization and `AGENTS-AND-SKILLS.md`
   registration, and a single small skill carries submodule init/update friction.
   Given upstream is a single-author, low-cadence repo, the update-tracking
   benefit is small, which is why PORT is the primary recommendation.
