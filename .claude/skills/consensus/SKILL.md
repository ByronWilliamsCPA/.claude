---
description: >
  Multi-model consensus via OpenRouter, replacing the zen/pal MCP consensus tools. Two
  modes: tiered-review (structured IT review team, levels 1-3, professional roles per
  domain) and consensus (fully flexible models and stances). Use when the user wants
  second opinions from multiple AI models, a tiered review, multi-model consensus, or to
  consult other models. Triggers on: consensus, tiered consensus, tiered review, second
  opinion, multi-model review, ask other models, review team, model roster.
tools: ["Read", "Bash", "Grep", "Glob", "Edit", "Write"]
---

# Consensus

Fan a question out to multiple AI models via OpenRouter and synthesize their
responses. The engine script handles selection, parallel calls, retries,
failover, and cost caps. You (Claude) do the synthesis; never delegate
synthesis to a model template.

## Prerequisites

- `OPENROUTER_API_KEY` set in the environment. If `run` fails with a key
  error (exit code 1), tell the user and stop.
- All commands run from the repo root with `uv run` (the script carries
  PEP 723 inline dependencies).

## Mode routing

| User intent | Mode | Workflow |
| --- | --- | --- |
| "tiered consensus", "review team", "level 1/2/3", wants structured IT review | Tiered review | `workflows/tiered-review.md` |
| Names specific models, wants stances (for/against), ad-hoc panel | Flexible consensus | `workflows/consensus.md` |
| "refresh the model data", roster references dead models | Data refresh | `workflows/refresh-data.md` |

When the request is ambiguous, default to tiered review at level 1 (it is
nearly free) and say so.

## Engine quick reference

```bash
uv run .claude/skills/consensus/scripts/consensus_cli.py select --level 2 --domain architecture
uv run .claude/skills/consensus/scripts/consensus_cli.py estimate --level 3
uv run .claude/skills/consensus/scripts/consensus_cli.py run --prompt-file /tmp/q.txt --roster-file /tmp/roster.json
uv run .claude/skills/consensus/scripts/consensus_cli.py run --prompt-file /tmp/q.txt --models "openai/gpt-5.1,anthropic/claude-opus-4.6" --roles-file /tmp/roles.json
uv run .claude/skills/consensus/scripts/consensus_cli.py refresh
```

Domains: `code_review` (default), `security`, `architecture`, `general`.

Exit codes: 0 success, 1 missing API key, 2 cost cap breach or unreadable
input file, 3 every model failed.

## Levels and cost caps

| Level | Roster | Cap |
| --- | --- | --- |
| 1 | 3 free models (failover may substitute cheap paid models) | $0.50 |
| 2 | level 1 + 3 economy models (6 total) | $1.00 |
| 3 | level 2 + 2 premium models (8 total) | $10.00 |

The script refuses to run past the cap; pass `--max-cost` only after the
user explicitly approves the higher spend. Models outside the curated
catalog cannot be estimated; the run output carries a `warning` key listing
them, and their cost is NOT capped. Surface that warning to the user.

## Synthesis requirements

After `run` returns, synthesize from the raw JSON yourself:

1. Per-model summary (one line each, name the model and role).
2. Consensus points: claims at least half the models agree on.
3. Disagreements: attribute positions to specific models.
4. Your recommendation, weighing role-specific concerns.
5. Report actual `total_cost_usd`, any `warning`, and any failed models.

Never present template text as analysis. If `failed > 0`, say which models
failed and that the synthesis covers a partial panel.
