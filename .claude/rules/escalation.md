# Escalation Policy

Route by trigger. "Panel" means the /panel skill (cross-vendor). "Opus"
means dispatch to an opus-pinned agent or recommend an opus session.
"User" means stop and ask; no tool substitutes for consent.

| # | Trigger | Escalate to | Bundle to prepare | Question to ask |
| --- | --- | --- | --- | --- |
| ES-1 | Auth, authz, crypto, payment, or data-deletion code paths | Panel + user sign-off | Diff, threat notes, affected flows | "What attack or loss scenario does this change enable?" |
| ES-2 | Architecture decision with 2+ defensible options | Opus (plan-ceo/devex reviewers) | Options with tradeoffs already written | "Which option, and what would change your mind?" |
| ES-3 | Same CI gate failing after 3 fix attempts | User, with BLOCKED envelope | Verbatim errors, attempts log | "Fix approach or environment problem?" |
| ES-4 | Cross-cutting refactor touching 3+ subsystems | Opus plan review before any edit | Impact map (codebase-memory), test coverage of targets | "Order of operations and blast-radius check" |
| ES-5 | Production deploy, irreversible migration, force operations | User, always | Rollback plan, checklist state | Explicit go/no-go |
| ES-6 | Dependency upgrade with breaking changes or advisory | Panel if security-relevant, else proceed with provenance notes | Changelog, uv tree/npm why, advisory text | "Upgrade, pin, or replace?" |
| ES-7 | Unclear or self-contradicting user intent | User, batched questions with a recommended default each | The contradiction, quoted | One message, all questions |
| ES-8 | Conflicting instructions between loaded files | User (and file a fix for the conflict) | Both quotes with paths | "Which is authoritative? I will patch the loser." |
| ES-9 | Repeated tool failure (same tool, 3+ errors) | User with environment diagnosis | Error text, doctor output | "Environment or usage?" |
| ES-10 | Diff exceeding ~500 lines mid-task | Self-escalate: stop, split proposal | The natural seams | "Split here?" |
| ES-11 | Possible sensitive-data exposure noticed in any content | User immediately; do not repeat the value anywhere | Location only, never the value | "Rotate and scrub?" |
| ES-12 | A gate or hook the docs promise appears to be missing/misfiring | User + file an issue against this repo | Doctor output, expected vs observed | "Trust the doc or the runtime?" |

Application rule: a stronger model's (or the user's) answer is recorded in
the context pack's PRIOR DECISIONS and is not relitigated by any later step
in the same task. If new evidence contradicts it, escalate again with the
evidence; do not silently override.
