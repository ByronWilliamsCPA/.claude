---
schema_type: common
title: Consensus skill (zen-mcp-server replacement)
status: in-review
owner: engineering
tags: [skills, tooling, automation]
purpose: Design for an umbrella consensus skill that replaces the zen-mcp-server custom consensus suite (consensus, tiered_consensus, dynamic_model_selector) with two workflows (flexible consensus and a tiered IT review team) driving one shared OpenRouter engine script. Band selection, roles, failover, and cost caps are ported from the MCP server; template synthesis is replaced by Claude-native synthesis from raw JSON responses.
---

> **Status**: Approved | **Date**: 2026-06-11
> **Decision context**: The williaby/zen-mcp-server fork (upstream dead since 2025-12-15)
> is being trialed for replacement by a Claude Code skill. Direction chosen by user on
> 2026-06-11: hybrid; build the skill now, run it alongside the MCP server, decide
> archive/keep after the skill proves parity. The fork stays frozen meanwhile.

## Goal

Replace the zen-mcp-server custom consensus suite (`consensus`, `tiered_consensus`,
`dynamic_model_selector`) with a single umbrella skill plus one engine script that
calls OpenRouter directly. Synthesis moves from Python templates (the confirmed-broken
layer) to Claude itself.

## User decisions (recorded)

| Decision | Choice |
| --- | --- |
| Architecture direction | Hybrid: skill first, MCP server kept frozen until parity proven |
| Scope | Full port: levels AND professional roles/domains |
| Tool identities | Both come over: `tiered-consensus` = structured IT review team (levels + roles); `consensus` = full flexibility on models and roles |
| Model data | Curated dataset + live OpenRouter validation (24h cache); refresh workflow flags stale rows |
| Structure | Approach A: one umbrella skill, two workflows, one shared engine script |
| L1 cost cap | $0.50 (target $0 via free models; headroom for paid equivalents when free models are unavailable) |

## Layout

```text
~/dev/.claude/.claude/skills/consensus/
├── SKILL.md                  # Router: flexible vs tiered mode; under 200 lines
├── workflows/
│   ├── consensus.md          # Flexible mode: any models, any roles/stances
│   ├── tiered-review.md      # IT review team: --level 1/2/3, roles by domain
│   └── refresh-data.md       # Dataset staleness check and update procedure
├── scripts/
│   └── consensus_cli.py      # Engine: uv-run script, PEP 723 inline deps (httpx only)
└── data/
    ├── models.csv            # Curated dataset: costs, HumanEval/SWE-bench, specialization, org level
    ├── bands_config.json     # Tier criteria: free/economy/premium bands, org-level criteria
    └── roles.json            # Roles per level and domain, with focus prompts
```

## Salvage map (from zen-mcp-server `tools/custom/`)

| Source | Disposition |
| --- | --- |
| `band_selector.py` | Filtering logic rewritten in pure Python dicts. pandas dropped entirely, which also deletes the three `RangeIndex.take` workaround hacks (Python 3.10 + pandas 2.3 + numpy 2.2 bug) |
| `consensus_models.py` | Availability cache and failover-candidate logic ported into the script |
| `consensus_roles.py` | Role definitions and focus prompts exported to `data/roles.json` |
| `consensus_synthesis.py` | NOT ported. Template synthesis is the confirmed-broken layer (2026-06-10 smoke test: boilerplate output, wrong counts). Claude synthesizes from raw JSON |
| `tiered_consensus.py` | MCP WorkflowTool step machinery discarded; level definitions and cost estimation survive |
| `dynamic_model_selector.py` | Capability folded into the `select` subcommand flags |
| `docs/models/models.csv`, `docs/models/bands_config.json` | Copied into `data/` (hand-rated fields the OpenRouter API does not provide) |

## Script interface

All subcommands emit JSON. `OPENROUTER_API_KEY` read from the environment; fail fast
with a clear message if missing.

- `select --level N [--domain code_review|security|architecture|general] [--limit K]`
  Band-filtered roster with role assignments and cost estimate. Validates picks against
  the live OpenRouter `/models` endpoint (disk cache, 24h TTL) and substitutes failover
  candidates for dead or unavailable models. This structurally fixes the stale-roster
  defect observed 2026-06-10.
- `run --prompt-file F (--roster-file J | --models m1,m2,...) [--roles-file R]`
  Parallel fan-out via OpenRouter chat completions; each model receives its role or
  stance system prompt. Roster files from `select` already carry role assignments;
  for flexible mode, `--roles-file R` is a JSON object mapping model name to a role
  name from `data/roles.json` or a literal system-prompt string. Returns per-model
  `{model, role, response, tokens, cost_usd, error}`.
- `estimate --level N`
  Cost preview without calling any model.
- `refresh`
  Diff `data/models.csv` against the live API. Reports dead and notable new models.
  Never auto-edits: HumanEval/SWE-bench/specialization fields are hand-rated.

## Data flow

**Tiered review:** request, then `select --level N --domain D`, present roster and
estimated cost, write prompt file, `run --roster-file`, Claude synthesizes from the
JSON: agreement matrix, consensus points, disagreements with attribution,
recommendation, actual cost.

**Flexible consensus:** same flow, but models and stances come from the user or
Claude's judgment instead of `select`.

## Error handling and cost guardrails

- Per-model timeout (120s); 429/5xx retry, then failover to the next band candidate.
  A single model failure never kills the run.
- Partial success (at least 1 response) still returns results with failures listed;
  Claude synthesizes with an explicit caveat. Zero successes returns raw errors.
- Cost caps enforced in the script per level: L1 $0.50 (free models first; paid
  equivalents only on failover), L2 $1, L3 $10. `--max-cost` overrides. `run` refuses
  when the estimate exceeds the cap.

## Testing

- pytest unit tests: band selection against shipped data files, roster failover with a
  mocked catalog, cost-cap refusal, JSON output schema. Live calls mocked via httpx
  transport injection. Test location follows the repo's existing pytest layout.
- One documented manual smoke eval: level-1 run (3 free models, ~$0) verifying
  end-to-end fan-out; the same scenario the MCP server failed on.

## Registration and repo integration

- Entry in `AGENTS-AND-SKILLS.md`.
- `pre-commit run --all-files` green; conventional signed commit.
- Skill conventions per `.claude/skills/CLAUDE.md`: stateless, under 200 lines for
  SKILL.md, workflows in `workflows/`.

## Out of scope

- `chat`, `listmodels` equivalents (covered incidentally: `run --models <one>` and
  `select`/`refresh` output).
- `clink` (Claude Code runs CLI agents natively via Bash).
- Any changes to the zen-mcp-server repo (frozen during the trial).
- Retiring the pal MCP server config (decided after parity assessment).

## Parity criteria (for ending the hybrid trial)

1. Level-1 tiered review completes with 3 models at ~$0 with rendered synthesis.
2. Level-2 review across 6 models in two cost bands with role assignments.
3. Flexible consensus with user-named models and stances.
4. Roster never references a model absent from the live OpenRouter catalog.
