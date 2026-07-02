# Skill and Agent Routing

When more than one skill matches, route by the FIRST matching row.

| If the request is about | Use | Not |
| --- | --- | --- |
| A failing test you can name | /debug-tests | testing, tdd |
| Writing new tests for existing code | /testing | test-coverage |
| Coverage numbers or gaps | /test-coverage | testing |
| Writing code for a new feature | test-driven-development first | testing |
| Lint/format/type errors only | /quality | ci-fix |
| Any red CI gate, or several gates | /ci-fix | quality |
| One number: how healthy is this repo | /health | ci-fix, quality |
| Reviewing a diff before commit | code-reviewer agent | /pr-review |
| Reviewing an open PR (URL exists) | /pr-review | code-reviewer, /code-review |
| A second opinion from other vendors | /panel | pr-review |
| "Should we build this at all" | premise-interrogation | brainstorming |
| Requirements are agreed, design is not | brainstorming | writing-plans |
| Design agreed, need ordered steps | writing-plans | executing-plans |
| A plan document exists | executing-plans | writing-plans |

Verification-word disambiguation ("verify", "check", "confirm"):
- a code assumption -> /rad
- a completed task's own output -> verification-before-completion
- a fact against an external source -> external-reference-verification
- a framework API you are about to use -> source-driven-development
- a decision that would be expensive if wrong -> doubt-driven-development
