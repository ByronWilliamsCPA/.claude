---
name: subagent-driven-development-extras
description: Local delta on top of the vendored subagent-driven-development skill. Adds a two-transport rule for reviewer feedback: blocking findings get the fix/re-review loop, accepted-minor findings ride forward as a preamble commit in the next dispatch. Use alongside subagent-driven-development when a quality reviewer returns "approve with non-blocking follow-ups" during a multi-task controller run. Triggers on: subagent controller, reviewer follow-ups, approve with minor, non-blocking review, batch review feedback, preamble commit.
---

# subagent-driven-development-extras

Extends the vendored `subagent-driven-development` skill (read-only, in `.submodules`). Contains only the delta: how the controller routes the two severity classes of reviewer feedback.

## Two severity classes deserve two transport mechanisms

Quality reviewers frequently return "approve with minor follow-ups": non-blocking test gaps, docstring additions, constant placement. Dispatching a dedicated fix-and-re-review cycle for each such batch doubles the subagent count for trivial changes. Instead:

- Blocking findings (request-changes verdicts) keep the closed loop the skill mandates: same-implementer fix plus re-review.
- Accepted, non-blocking suggestions ride forward as an explicit "COMMIT 1: review follow-ups" preamble in the NEXT task's implementer prompt.

This keeps commits separated and the follow-ups traceable to their originating review, while reserving the fix/re-review loop for findings that actually block. Blocking findings need the closed loop; accepted-minor findings only need a guaranteed landing slot, and batching them into the next dispatch preserves quality at roughly half the subagent overhead.
