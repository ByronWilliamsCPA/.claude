---
schema_type: common
title: Compliance Retrospective Aggregation Design
status: draft
owner: engineering
tags: [compliance, agents, standards]
purpose: Design for centralizing per-repo compliance retrospectives into a fleet-wide rollup with weekly synthesis, mirroring the task-observer aggregation precedent.
---

**Date**: 2026-05-16
**Status**: Draft
**Author**: Byron Williams

---

## Problem

Compliance retrospectives are scattered across individual repos. The
`compliance-retrospective` agent writes per-session output to
`<repo>/docs/compliance-reports/lessons-learned/YYYY-MM-DD.md` and (when the
3-repo threshold fires) `<repo>/docs/compliance-reports/fleet-actions/YYYY-MM-DD.md`.
These files live in the repo where the audit ran. No central rollup exists,
so cross-session patterns (the same gap recurring across sweeps, weeks
apart) get lost.

The per-session agent already detects fleet patterns within a single
session via its 3-of-N threshold. What is missing is the cross-session
view: trending recurrence, stuck candidates, fleet-action follow-through,
coverage and override hotspots.

The same problem was previously solved for task-observer through a central
log at `~/.claude/skill-observations/log.md` and a separate
`aggregate-observations` skill that performs a weekly review. This design
applies the same pattern to compliance retrospectives.

A secondary problem is naming drift. Today there are three competing
central directories for related content:

- `~/dev/.claude/compliance-retrospectives/` (naked at repo root)
- `~/dev/.claude/docs/compliance-retrospectives/` (under docs/)
- `~/dev/.claude/docs/compliance-reports/lessons-learned/`
  (the agent's documented per-repo output path)

This design consolidates on a single canonical root.

## Goals

- One central, structured master log of every compliance retrospective
  session across every repo in the fleet.
- A weekly synthesis report that surfaces cross-session patterns the
  per-session agent cannot see.
- An on-demand reconciliation path that catches anything written
  out-of-band.
- Idempotent operation: re-running reconciliation never produces duplicate
  entries.
- Zero behavior change for existing per-repo audit output. The new system
  is purely additive.

## Non-Goals

- The system does not modify the standards manifest. It surfaces candidates;
  promotion remains a human decision.
- The system does not open PRs from synthesis recommendations.
- The system does not re-run audits to verify findings; it trusts the
  master log with limited spot-check verification.
- The system does not aggregate at the per-finding level (each finding
  rolled up across repos). Aggregation is at the session level; finding
  detail is preserved by reference (link back to the per-repo file).

## Decisions

- **Approach:** Two-agent split, mirroring task-observer precedent
  (separate write-side and review-side). Push at write time with on-demand
  reconciliation. Scheduled weekly synthesis with on-demand override.
- **Canonical root:** `~/.claude/docs/compliance-reports/` (aligns with
  the per-repo path naming convention).
- **Source of truth:** JSONL file (`master-log.jsonl`), append-only,
  dedupe by `(session_date, repo)`.
- **Human view:** `master-log.md`, deterministically rendered from JSONL
  by a Python script on every append. Pure function.
- **Synthesis cadence:** Weekly via Claude Code scheduler (Mondays 09:37
  local, off-peak minute). Manual override via slash command.
- **Insights covered:** trending recurrence, stuck manifest candidates,
  fleet-action follow-through, coverage gaps + override hotspots.

## Architecture

### Three actors, three concerns

- **Write-side**: `compliance-retrospective` agent (extended). Same per-repo
  output as today, plus appends one JSONL entry to the central log and
  invokes the renderer.
- **Reconcile-side**: `/compliance-rollup` slash command (new). Walks every
  catalog repo's `docs/compliance-reports/lessons-learned/` directory,
  appends anything missing from the master log. Idempotent. Read-only on
  per-repo files.
- **Review-side**: `compliance-synthesis` agent (new). Reads the master log,
  computes four insight sets, writes a synthesis report. Triggered weekly
  by scheduler and on-demand via slash command.

### Central file layout

```text
~/.claude/docs/compliance-reports/
├── master-log.jsonl                       # source of truth, append-only
├── master-log.md                          # rendered view, regenerated on every append
├── synthesis/
│   └── YYYY-MM-DD.md                      # weekly synthesis reports
├── fleet-actions/
│   └── YYYY-MM-DD.md                      # central fleet-action history
├── archive/
│   └── sessions/                          # migrated legacy session files
└── state/
    ├── last-synthesis-date.txt
    ├── scheduler-registered.txt
    └── reconcile-log.txt                  # audit trail of reconcile sweeps

<repo>/docs/compliance-reports/lessons-learned/    # per-repo (unchanged)
<repo>/docs/compliance-reports/fleet-actions/      # per-repo (unchanged)
```

### Data flow

```text
audit session in repo X
     ↓
compliance-retrospective agent
     ├── writes <repo X>/docs/compliance-reports/lessons-learned/YYYY-MM-DD.md   (unchanged)
     ├── writes <repo X>/docs/compliance-reports/fleet-actions/YYYY-MM-DD.md     (if applicable)
     └── appends JSON entry to ~/.claude/docs/compliance-reports/master-log.jsonl
                              ↓
                       renderer regenerates master-log.md

weekly scheduler (Mondays 09:37) or /compliance-synthesis
     ↓
compliance-synthesis agent
     ├── reads master-log.jsonl
     ├── reads recent per-repo retrospectives (verification spot-checks)
     ├── writes ~/.claude/docs/compliance-reports/synthesis/YYYY-MM-DD.md
     └── updates state/last-synthesis-date.txt

/compliance-rollup (on demand)
     ↓
walks every repo in github-repos.json
     ├── reads <repo>/docs/compliance-reports/lessons-learned/*.md
     ├── for each (date, repo) not in master-log.jsonl → append (reconciled=true)
     └── re-renders master-log.md, writes reconcile-log.txt summary
```

## Master log JSONL schema

Each session emits one JSON line. The synthesis agent works almost
entirely from these entries.

```jsonc
{
  "schema_version": 1,
  "session_date": "2026-05-16",
  "session_id": "2026-05-16T19:42:11Z-fdc2",
  "repo": "ByronWilliamsCPA/llc-manager",
  "repo_path": "/home/byron/dev/llc-manager",
  "audit_mode": "interactive",
  "repo_type": "python-app",
  "visibility": "public",
  "reconciled": false,
  "totals": {
    "critical": 0,
    "important": 3,
    "suggested": 7,
    "unclassified_candidates": 2,
    "overrides_applied": 1
  },
  "findings_by_check": [
    {"id": "FOUND-008", "severity": "important", "remediation_status": "open"},
    {"id": "CI-005", "severity": "suggested", "remediation_status": "open"}
  ],
  "unclassified_candidates": [
    {
      "candidate_id": "2026-05-16-llc-manager-01",
      "pattern": ".editorconfig absent from project root",
      "proposed_manifest_id": "FOUND-012",
      "proposed_yaml_path": "docs/compliance-reports/lessons-learned/2026-05-16.md#proposed-manifest-additions"
    }
  ],
  "fleet_action_proposals": [
    {
      "check_id": "FOUND-008",
      "repos_in_session": ["org/r1", "org/r2", "org/r3"],
      "fleet_actions_file": "docs/compliance-reports/fleet-actions/2026-05-16.md"
    }
  ],
  "scope_expansion_flags": [
    {"agent": "python-toolchain-auditor", "note": "..."}
  ],
  "links": {
    "lessons_learned": "docs/compliance-reports/lessons-learned/2026-05-16.md",
    "fleet_actions": "docs/compliance-reports/fleet-actions/2026-05-16.md"
  },
  "superseded_by": null
}
```

### File header

The JSONL file's first line is a header sentinel, written when the file
is first created:

```jsonc
{"type": "header", "schema_version": 1, "created": "2026-05-16"}
```

Readers skip lines where `type == "header"`.

### Dedupe and supersede rules

- Uniqueness key: `(session_date, repo)`.
- If the same key is appended twice, the existing entry's `superseded_by`
  field is set to the new `session_id`. Both entries remain in the file.
- The renderer and the synthesis agent both select the canonical entry
  per `(session_date, repo)` using: filter to non-superseded; if more than
  one remains (rare race: two concurrent writes both missed the supersede
  step), select the one with the latest `session_id` (ISO timestamp prefix
  guarantees lexicographic ordering matches chronological).
- `reconciled=true` on entries appended by `/compliance-rollup`; `false`
  on entries appended by the retrospective agent at write time.

### Atomicity

JSONL append is POSIX-atomic for writes below `PIPE_BUF` (4 KB on Linux).
All entries fit well under that limit (typical entry size: 1-2 KB).
Concurrent audits in different repos can safely append in parallel.

## Components

### compliance-retrospective agent (extension)

**File:** `~/.claude/agents/compliance-retrospective.md` (modified)
**Tools:** `Read, Write, Bash, Grep, Glob` (unchanged)
**Model:** `sonnet` (unchanged)

**Change:** Add a "Step 7: Central log append" after the existing Step 6.

Step 7 actions:

1. Resolve central root `~/.claude/docs/compliance-reports/`. Create the
   directory tree if it does not exist.
2. If `master-log.jsonl` does not exist, create it with a header line:
   `{"type": "header", "schema_version": 1, "created": "<today>"}`.
3. Construct the session's JSONL entry per the schema in this spec.
   `reconciled` is `false`. `superseded_by` is `null`.
4. Check whether `(session_date, repo)` already exists in the file. If
   yes: read the file fully, set the existing entry's `superseded_by`
   field to the new `session_id`, and rewrite the file via temp file +
   `os.rename` (atomic on the same filesystem). This is acceptable
   because supersede is the rare case; the common-path append uses the
   shell redirect in step 5.
5. Append the new entry to the file using `printf '%s\n' "$JSON" >> master-log.jsonl`.
6. Invoke the renderer: `python3 ~/.claude/scripts/compliance-log-render.py`.

What does NOT change in the agent:

- Per-repo Markdown output formats stay identical.
- The 3-repo single-session fleet-action threshold stays identical.
- The output document template stays identical.

### Renderer script

**File:** `~/.claude/scripts/compliance-log-render.py` (new)
**Inputs:** none (paths are hardcoded)
**Outputs:** writes `~/.claude/docs/compliance-reports/master-log.md`

Pure function: JSONL in, Markdown out.

```python
# spec sketch; full implementation in the plan
def render() -> None:
    jsonl_path = Path.home() / ".claude/docs/compliance-reports/master-log.jsonl"
    md_path = jsonl_path.parent / "master-log.md"

    entries = []
    for line in jsonl_path.read_text().splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("type") == "header":
            continue
        entries.append(obj)

    entries = dedupe_by_supersede(entries)  # latest non-superseded per (date, repo)
    by_month = group_by_month(entries)

    md_path.write_text(format_markdown(by_month))
```

The rendered `master-log.md` contains:

- A header summary: total sessions, distinct repos audited, oldest entry
  date, newest entry date, count of open fleet actions.
- Per-month sections in reverse-chronological order.
- Within each month, a summary table (date, repo, severity totals,
  candidates count, reconciled flag) plus a bullet of links per session.

### /compliance-rollup slash command

**File:** `~/.claude/commands/compliance-rollup.md` (new)
**Implementation script:** `~/.claude/scripts/compliance-rollup-reconcile.py`

Flags:

- `--dry-run`: report what would be appended without modifying the JSONL.
- `--since YYYY-MM-DD`: only consider per-repo files newer than this date.

Workflow:

1. Load repo catalog `~/.claude/docs/reference/github-repos.json`.
2. Load existing master log; build set of known `(session_date, repo)`
   keys.
3. For each repo in the catalog with a local clone:
   a. Scan `<local-clone>/docs/compliance-reports/lessons-learned/*.md`.
   b. Parse each file's `YYYY-MM-DD.md` filename for `session_date`.
   c. Parse body sections (fixed headings per the existing agent template)
      for `totals`, `findings_by_check`, `unclassified_candidates`,
      `fleet_action_proposals`, `scope_expansion_flags`.
   d. If `(session_date, repo)` not in known set: construct a JSONL entry
      with `reconciled=true` and append (unless `--dry-run`).
4. Re-render `master-log.md`.
5. Write `state/reconcile-log.txt` summary:
   - Sweep timestamp.
   - Repos walked, repos with local clones, repos skipped (no clone).
   - New entries appended, dupes detected.
   - Any parse failures with file paths.

Parser contract (keyed to existing agent template headings):

| JSONL field | Source |
|---|---|
| `session_date` | Filename `YYYY-MM-DD.md` (canonical) |
| `repo` | Catalog lookup keyed by clone path |
| `totals.*` | Session Summary table rows |
| `findings_by_check[*].id` | "High-Frequency Existing Checks" bullets |
| `unclassified_candidates[*]` | YAML blocks under "Proposed Manifest Additions" |
| `fleet_action_proposals[*]` | `### [CHECK-ID]:` headings under "Fleet-Wide Actions Required" |
| `scope_expansion_flags[*]` | Bullets under "Agent Scope Expansion Candidates" |

Hard rules:

- Never modify per-repo files. Read-only on the repos themselves.
- Never silently drop parse failures. Surface them in `reconcile-log.txt`
  with file paths.
- Repos in the catalog without local clones are skipped, not flagged.

### compliance-synthesis agent

**File:** `~/.claude/agents/compliance-synthesis.md` (new)
**Tools:** `Read, Write, Bash, Grep, Glob`
**Model:** `sonnet`

Inputs:

- `central_root`: `~/.claude/docs/compliance-reports/`
- `synthesis_window_start`: ISO date. Defaults to
  `state/last-synthesis-date.txt`, or 90 days back if absent.
- `synthesis_window_end`: ISO date. Defaults to today.
- `invocation_mode`: `scheduled` or `on-demand`.

Workflow:

1. Read `state/last-synthesis-date.txt`. If absent, set window_start to
   90 days back.
2. Read `master-log.jsonl`. Filter entries to window. Apply supersede
   resolution.
3. Compute four insight sets per the algorithms below.
4. For each insight that has actionable items, spot-check 1-2 supporting
   per-repo files via `Read` to confirm the master log is not stale.
5. Write synthesis report to `synthesis/YYYY-MM-DD.md`.
6. Update `state/last-synthesis-date.txt` to today.
7. If `invocation_mode == scheduled`, re-register the next scheduler run
   (Claude Code scheduled tasks expire after 7 days).

Insight algorithms:

| Insight | Algorithm | Threshold |
|---|---|---|
| Trending recurrence | Group `unclassified_candidates[*].pattern` across sessions by normalized-string fuzzy match. Count distinct sessions and repos. | ≥3 distinct sessions AND ≥2 distinct repos |
| Stuck manifest candidates | For each candidate's `proposed_manifest_id`, check whether that ID exists in `~/.claude/docs/standards/standards-manifest.yaml`. | Proposed ≥30 days ago AND still absent from manifest |
| Fleet-action follow-through | For each past `fleet_action_proposals[*]`, scan later sessions for the affected repos. If the same `check_id` still appears as an open `findings_by_check` entry: action did not land. | Open after ≥14 days |
| Coverage gaps | For every catalog repo, find newest `session_date`. | >60 days stale |
| Override hotspots | Count `overrides_applied` per check ID across sessions in window. | Same check overridden in ≥4 repos |

Output template, written to `synthesis/YYYY-MM-DD.md`:

```markdown
# Compliance Synthesis: <YYYY-MM-DD>

**Window:** <start> → <end>
**Sessions analyzed:** N across M distinct repos
**Mode:** scheduled | on-demand
**Meta-finding (if applicable):** reconciled-rate in window is X%; push
mechanism may be missing entries.

## Trending recurrence
<per pattern: pattern, session count, repo list, proposed manifest ID,
recommendation>

## Stuck manifest candidates
<per candidate: description, first proposed date, sessions it re-appeared
in, suggested next action>

## Fleet-action follow-through
<per past fleet-action: original proposal date, repos affected, current
status table (Resolved / Still open / Not re-audited), recommendation>

## Coverage gaps
<table: repo, last audit date, days stale, sorted descending>

## Override hotspots
<per check ID exceeding threshold: check description, repos overriding,
count, recommendation>

## Recommended actions for next sprint
<top 3-5 prioritized recommendations with supporting data>
```

What this agent does NOT do:

- Does not modify the standards manifest.
- Does not open PRs.
- Does not re-run audits.

## Migration (one-time)

1. Create canonical layout at `~/.claude/docs/compliance-reports/` with
   subdirs `synthesis/`, `fleet-actions/`, `archive/sessions/`, `state/`.
2. Run `/compliance-rollup --since 2026-01-01` to backfill the master log
   from existing per-repo retrospectives. All historical entries land
   as `reconciled=true`.
3. Move legacy session-level files (these are not per-repo retrospectives
   and do not fit the JSONL schema):
   - `~/dev/.claude/compliance-retrospectives/*.md` →
     `~/.claude/docs/compliance-reports/archive/sessions/`
   - `~/dev/.claude/docs/compliance-retrospectives/*.md` →
     `~/.claude/docs/compliance-reports/archive/sessions/`
4. Verify: master-log.md header counts match expected total, synthesis/
   is empty, state/scheduler-registered.txt contains "pending".

## Scheduler

Mirrors the task-observer scheduler pattern:

- Cron expression: `37 9 * * 1` (Mondays 09:37 local, off-peak minute).
- Fires: `/compliance-synthesis --mode scheduled`.
- Claude Code scheduled tasks auto-expire after 7 days; the synthesis
  agent re-registers the next run as its last step. If a run fails, it
  does not re-register, and the scheduler self-heals via expiry.
- `state/scheduler-registered.txt` records registration status.

## Settings.json changes

Add to `~/.claude/settings.json` allow rules:

- `Bash(python3 ~/.claude/scripts/compliance-log-render.py:*)`
- `Bash(python3 ~/.claude/scripts/compliance-rollup-reconcile.py:*)`

No new hooks. The scheduler tool handles invocation.

## What stays in the existing repo-compliance skill

The skill itself does not change. It already invokes
`compliance-retrospective` at the end of every session; that agent now
has the additional side effect of appending to the central log.
Optionally, the skill's wrap-up section may gain a one-line note
referencing the central log path.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Two concurrent audits append simultaneously and corrupt JSONL | All entries are well under `PIPE_BUF` (4 KB). POSIX guarantees atomicity for sub-PIPE_BUF append writes. Risk is effectively zero in practice. |
| Parser drift: agent changes Markdown headings, rollup parser breaks | Parser keys off fixed headings documented in the agent template. Heading changes are a coordinated update. Rollup writes parse failures loudly to reconcile-log.txt. |
| Master log diverges from per-repo files | Synthesis agent spot-checks 1-2 supporting files per insight; high reconciled-rate is surfaced as a meta-finding. |
| Stuck-candidate detection is wrong (false positive: candidate was reviewed and rejected) | Manifest acceptance is the positive signal; rejection is not currently recorded. Future enhancement: add an `out-of-scope` registry. Out of scope for this design. |
| Scheduler stops firing silently | Last-synthesis-date drift visible in any manual synthesis run. Meta-finding section flags it. |
| Coverage-gap threshold (60 days) is arbitrary | Threshold tunable in agent prompt. Refine after first synthesis run shows the actual fleet cadence. |

## Open questions

None. All decisions captured above.

## References

- Precedent: `~/.claude/skill-observations/log.md`,
  `~/.claude/skills/aggregate-observations/`,
  `~/.claude/skills/task-observer/`.
- Current agent: `~/.claude/agents/compliance-retrospective.md`.
- Repo catalog: `~/.claude/docs/reference/github-repos.json`.
- Memory: `feedback_skill_reference_audit.md`,
  `project_phase_gate_lifecycle.md` (task-observer integration pattern).
