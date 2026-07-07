---
title: "Tool Eval: fable5-methodology"
schema_type: common
status: published
owner: core-maintainer
purpose: "Evaluation of the fable5-methodology skill/agent/hook collection against this configuration, with a port-versus-ignore recommendation."
tags:
  - tooling
  - evaluation
  - skills
  - agents
  - hooks
---

**Date:** 2026-07-07
**Source:** <https://github.com/UnpaidAttention/fable5-methodology> (main, commit `bcc2eaca7046c400f22c0c5234e5cca07441939c`, inspected 2026-07-07)
**Verdict:** PORT PATTERNS (a small set of specific elements) | IGNORE (the bulk of the collection, which overlaps what we already have)

## Characterization

A prose-plus-machinery methodology collection presented as "Claude Fable 5
documenting its own working process so a weaker model can execute it cold."
Four layers: prose (`PLAYBOOK.md`, `AUDIT.md`, `INTEGRITY.md`, `MEMORY.md`,
`README.md`), 26 on-demand skills, 4 subagents (builder, code-reviewer,
qa-verifier, research-scout), 6 lifecycle hooks (destructive-command guard,
a Stop-time verification gate, an evidence logger, a post-edit verifier, a
pre-compact handoff writer, a session loader), and 4 stack standards
(PostgreSQL, Python, Rust, TypeScript/Node). Explicitly candid that it has
not been benchmarked head-to-head against baseline yet (an A/B harness exists
in `evals/ab-harness/` but has not been run). Stated scale target: any Claude
Code session doing hands-on engineering work, not a specific language or app
type.

## Value core vs. peripheral LOC

The whole repo is loadable content; there is no peripheral UI or build
tooling to strip.

| Segment | LOC | Notes |
| --- | --- | --- |
| Skills (26) | 2,403 | `skills/*/SKILL.md` |
| Top-level prose | 2,375 | `PLAYBOOK.md`, `README.md`, `AUDIT.md`, `INTEGRITY.md`, `MEMORY.md`, `GRADING_RUBRIC.md`, `TASK_BRIEFING_TEMPLATE.md` |
| Evals | 794 | `evals/eval-01..05/`, `evals/ab-harness/` |
| Hooks | 481 | `hooks/*.sh`, `hooks/pre-tool-guard.py` |
| Stacks | 378 | `stacks/*.md` |
| Agents (4) | 292 | `agents/*.md` |
| **Total** | ~6,723 | `install.sh` and `.gitignore` excluded (peripheral) |

## Candidate element table

| Element | Portable? | Maps to our gap | Fits delivery model? | Value-to-effort |
| --- | --- | --- | --- | --- |
| `skills/self-consistency-check` | PORTABLE (pure prose) | `.claude/skills/` -- no equivalent pre-code pairwise-conflict + cold-read + N-version-divergence check exists | FITS | High |
| `skills/predictive-execution` | PORTABLE (pure prose) | `.claude/skills/` -- no explicit predict-then-compare discipline; adjacent to but distinct from `systematic-debugging` | FITS | Medium-High |
| `skills/course-correction` | PORTABLE (pure prose) | `.claude/skills/` -- partial overlap with `doubt-driven-development` and `systematic-debugging-extras`, but the named alarm list (patch-on-patch, "too far to restart") is not written down anywhere in our tree | FITS | Medium |
| `hooks/pre-tool-guard.py` chmod/chown/SQL-DROP/curl-pipe-shell/workspace-scoped-rm patterns | PORTABLE (Python stdlib only: `json`, `os`, `re`, `subprocess`, `sys`) | `scripts/bash-pre-hook.sh` covers git force-push/reset --hard only; these five pattern classes are a real gap in our PreToolUse guard | FITS | Medium-High |
| `hooks/delivery-gate.sh` (evidence-log Stop gate) | PORTABLE (bash + python3, no framework) | Overlaps `scripts/stop-pre-commit-hook.sh`, which already force-runs pre-commit at Stop -- our mechanism is stronger (executes verification) vs. theirs (checks a log for whether verification happened) | FITS | Low (redundant) |
| `hooks/pre-tool-guard.py` secret-in-staged-diff check | PORTABLE | Overlaps `detect-secrets`/TruffleHog pre-commit hooks already required by `PC-HOOK-STAGED-SCOPE` | FITS | Low (redundant) |
| `skills/integrity-guardrails` | PORTABLE (pure prose) | Overlaps CLAUDE.md core directives, `doubt-driven-development`, `receiving-code-review-extras` | FITS | Low (convergent, not a gap) |
| `skills/context-economy` | PORTABLE (pure prose) | Overlaps CLAUDE.md's "Delegation and subagent usage" and "Session length" sections almost line for line | FITS | Low (convergent, not a gap) |
| `skills/uncertainty-management` | PORTABLE (pure prose) | Adjacent to RAD (`#CRITICAL`/`#ASSUME`/`#EDGE`/`#VERIFY`) but tags conversational claims rather than code; marginal | FITS | Low-Medium |
| `skills/session-state-management` | PORTABLE (pure prose) | Overlaps `/handoff` and the CLAUDE.md "Compact Instructions" section; theirs is continuous (`WORKING_NOTES.md` updated every milestone) vs. ours is endpoint-triggered | FITS | Low-Medium |
| Remaining 20 skills, 4 agents, 4 stack docs, evals harness | PORTABLE | No confirmed gap after sampling; substantial content overlap with our existing skill/rule set (see Convergent-validation notes) | FITS | Low |

## Licence

**No licence file.** The README states this explicitly: "No license is
included yet, which means all rights reserved by default." This blocks
wholesale inclusion (submodule or verbatim file copy) outright, regardless of
technical quality. Any adoption must be a from-scratch reimplementation of the
*idea* in our own words, not a copy of their prose, until the upstream author
adds a licence. This gate alone rules out SUBMODULE for the whole repo.

## Relationship classification

HOMOGENEOUS LOADABLE CONTENT. Skills, agents, and hooks are loaded by Claude
Code exactly the way ours are (`.claude/skills/`, `.claude/agents/`,
`hooks.json`-registered scripts). No inverted-host relationship.

## Convergent-validation notes

The collection independently arrived at several things we already do, which
raises confidence in both designs rather than surfacing action items:

- **PreToolUse destructive-command guard + Stop-time verification gate** as a
  two-hook pattern, matching `scripts/bash-pre-hook.sh` (git-scoped) and
  `scripts/stop-pre-commit-hook.sh` (pre-commit-scoped).
- **Fail-safe-open hook design** (`sys.exit(0)` on any internal error so a bug
  in the guard never bricks the session), matching our own hooks' explicit
  fail-safe comments.
- **Context-as-scarce-resource discipline**: delegate bulk reads to subagents,
  externalize durable facts to disk, read at the right altitude. This is our
  CLAUDE.md "Delegation and subagent usage" section restated independently.
- **No-success-claim-without-a-run** and **failures-lead** reporting norms,
  matching our doubt-driven-development / receiving-code-review-extras posture.
- **Load-on-demand skills, always-on prose floor** (their `CLAUDE.md` master
  plus on-demand skills) mirrors our Pattern A/B skill architecture split.
- **Tiered ceremony to task size** ("a one-line fix skips the chain a schema
  change runs in full") matches our own scope-tracing and gate-calibration
  instincts, though we do not have it written down as explicitly as their
  PLAYBOOK.md §17.3.

## Recommended actions

Do not submodule or bulk-adopt; the licence gate blocks it and most of the
content duplicates what this repo already has. Reimplement (not copy) three
specific skill ideas and one hook pattern, in our own words:

1. Write a new `.claude/skills/self-consistency-check/SKILL.md` (or fold into
   an existing design/planning skill) capturing the pairwise-constraint-sweep
   + fresh-context-cold-read + N-version-divergence technique for catching
   cross-requirement conflicts before code exists. This is the strongest single
   find in the collection and has no equivalent in our tree.
2. Consider a `predictive-execution` addition to `systematic-debugging-extras`
   or as its own skill: predict the outcome of a consequential command before
   running it, and treat "passed when I expected failure" as equally
   suspicious as an outright failure.
3. Fold the named alarm list from `course-correction` (two patches each fixing
   the prior patch's symptom, fighting the framework, "I've come too far to
   restart") into `systematic-debugging-extras` or `doubt-driven-development`
   as an explicit trigger list, rather than adding a whole new skill.
4. Extend `scripts/bash-pre-hook.sh` (or add a sibling PreToolUse hook) with
   the chmod/chown-recursive-on-root, SQL DROP/TRUNCATE, curl-pipe-to-shell,
   and workspace-scoped `rm -rf` pattern checks from `pre-tool-guard.py`.
   Reimplement the regexes; do not copy the file verbatim given the licence
   gate.
5. Skip the delivery-gate.sh evidence-log mechanism, the secret-in-diff check,
   `integrity-guardrails`, `context-economy`, and the remaining skills/agents:
   confirmed overlap with existing mechanisms that are equal or stronger.
6. Run the collection's own `evals/ab-harness/` (conceptually, not by copying
   it) if we want empirical evidence any of this actually beats baseline
   before investing further; the upstream repo itself has not done this yet.
