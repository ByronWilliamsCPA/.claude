---
title: "Cleanup Backlog System"
schema_type: common
status: published
owner: core-maintainer
purpose: "Authoritative specification for the local-worker cleanup backlog. Defines schema, state machine, worker contract, scout integration, and reviewer integration."
tags:
  - reference
  - automation
  - compliance
  - infrastructure
---

> **Status**: Active | Core Standard | **Version**: 1.0.0 | **Last Updated**: 2026-05-24

## Purpose

A queue of mechanical cleanup tasks across the BWCPA and williaby repo fleet that a
local model can execute autonomously, with Claude reviewing the resulting PRs.
Splits work by judgment cost: rote changes drain to local, judgment-heavy work
stays with Claude.

## Storage

Runtime data lives at `~/dev/homelab-infra/cleanup-backlog/` and is **gitignored**
in that repo. Rationale: every push to homelab-infra triggers CI; backlog churn
should not consume CI capacity. See `gitignore-patch.md` in this directory for
the exact .gitignore entries.

Schema, worker spec, and agent definition live in this repo and are committed.
If the runtime directory is ever lost, it is fully reconstructible from this
spec plus the most recent backup.

### Backup

The runtime directory must be included in your homelab backup target. Suggested:
nightly rsync or restic snapshot of `~/dev/homelab-infra/cleanup-backlog/` to
the homelab NAS. The schema in this repo survives independently in git.

## Directory layout

```text
~/dev/homelab-infra/cleanup-backlog/
├── pending/    # Available; worker claims oldest local-safe entry
├── active/     # Claimed and in progress
├── review/     # PR opened, awaiting reviewer
├── blocked/    # Worker failed gates; needs Claude intervention
└── done/       # Merged or rejected with final reason
```

State transitions are filesystem renames (`git mv`-style, but with plain `mv`
since the directory is gitignored). Renames are atomic on Unix filesystems,
which gives concurrency safety without locking.

## Per-task frontmatter schema

Every task file uses this frontmatter contract. The body below the frontmatter
contains context, procedure, and out-of-scope notes for the worker.

```yaml
---
id: LOCAL-0001                          # Stable, monotonic, sortable. Allocator:
                                        # max existing LOCAL-NNNN across all status dirs + 1
schema_type: cleanup-task               # For validate-frontmatter.sh compatibility
title: "Short imperative title"         # One line, ~60 chars
repo: ByronWilliamsCPA/repo-name        # Full owner/name. Single repo per entry.
difficulty: local-safe                  # local-safe | claude-required
risk: low                               # low | medium | high. high never goes to local.
created: 2026-05-24                     # ISO date
created_by: claude                      # claude | scout-agent | human
source: doc-audit                       # Optional: what surfaced the task
                                        # (doc-audit | repo-compliance | scout-agent | human | memory:<slug>)
claimed_by: null                        # Worker id once claimed (e.g. "worker-01")
attempts: 0                             # Incremented per failed pre-commit/test cycle
max_attempts: 2                         # After this, auto-escalate to blocked/
pr: null                                # URL once opened
expected_paths:                         # Worker aborts if diff touches anything outside
  - "docs/**/*.md"
forbidden_paths:                        # Worker aborts immediately if it tries to edit
  - ".github/workflows/**"
  - "**/secrets*"
  - "**/.env*"
  - "**/CHANGELOG.md"                   # Convention: only humans/release tooling write here
acceptance:                             # All must be machine-verifiable
  - "no-em-dash pre-commit hook passes"
  - "all other pre-commit hooks pass"
  - "diff touches only files matching expected_paths"
estimated_diff_lines: "5-30"            # Range. Worker aborts if outside upper bound.
history:                                # Replaces git log for this gitignored file
  - "2026-05-24T09:12 created by scout-agent (source: doc-audit finding)"
---
```

### Field validation rules

- `id` must be unique across all status directories. Allocator scans all five dirs.
- `difficulty: local-safe` is only valid if **all** of: risk is low or medium, all
  acceptance items are machine-verifiable, `expected_paths` is non-empty,
  `forbidden_paths` excludes everything in `.github/workflows/`, secrets, env files,
  and CHANGELOG.md, `estimated_diff_lines` upper bound is <=200.
- `difficulty: claude-required` skips all the above checks. These entries are
  reserved for Claude in interactive sessions and are not claimable by the worker.
- `history` is append-only. Workers and the scout agent only add entries; never
  rewrite or delete past entries.

## The five worker gates

A task entry is only valid as `local-safe` if a worker can verify all five gates
mechanically with no model judgment:

1. **Pre-commit gate**: `pre-commit run --all-files` must pass after the change.
   This is the primary correctness contract. Includes the no-em-dash hook, ruff,
   bandit, frontmatter validators, and everything else wired into pre-commit.
2. **Test gate**: project tests must pass with the change applied. If the repo
   has no test suite, this gate is skipped (note in the task body if so).
3. **Expected-paths gate**: the worker's diff must touch only paths matching
   `expected_paths` globs. Touching anything else aborts the work and moves the
   entry to `blocked/`.
4. **Forbidden-paths gate**: the worker must refuse to read or write anything
   matching `forbidden_paths` even if the patch logically requires it. Refusal
   means abort, not workaround.
5. **Diff-size gate**: the diff must be within `estimated_diff_lines` range.
   Exploding diffs indicate scope drift; abort.

Failure of any gate moves the entry from `active/` to `blocked/`, increments
`attempts`, and appends a history line describing the failure. After
`max_attempts`, the entry stays in `blocked/` and is surfaced to Claude in the
next interactive session.

## Status transitions

```text
pending/  -> active/      worker claims oldest local-safe entry (mv)
active/   -> review/      worker pushes branch, opens PR, sets pr field, mv
active/   -> blocked/     any gate fails; attempts++; mv
blocked/  -> pending/     Claude fixes the entry (narrows paths, splits, etc.); mv
review/   -> done/        PR merged; final history line added; mv
review/   -> blocked/     reviewer requests changes worker cannot satisfy; mv
*         -> done/        rejected by Claude with reason in history; mv
```

The worker never moves entries to `done/` directly. Only the reviewer (Claude,
or an automated post-merge hook) does that.

## Scout agent integration

The `cleanup-backlog-scout` agent (defined at
`~/dev/.claude/.claude/agents/cleanup-backlog-scout.md`) writes new entries to
`pending/`. It is the primary author of backlog entries.

Three invocation patterns:

1. **Targeted scout**: "scout repo X for cleanup work" -- agent surveys one repo
   and writes 0-N entries.
2. **Fleet scout**: "scout the fleet" -- agent iterates the repo catalog in
   `docs/reference/github-repos.md` and writes entries per repo.
3. **Post-audit scout**: when another skill (repo-compliance, doc-audit,
   general-compliance-auditor) produces findings, the scout agent converts the
   findings whose severity matches its difficulty bar into backlog entries.

The scout is conservative: when in doubt about classification, it marks
`claude-required`, not `local-safe`. Claude can always rewrite later; a wrong
`local-safe` classification gets executed by the worker before review.

## Reviewer integration

For now, review happens in interactive sessions. When a `local-dev`-labeled PR
opens in any repo, Claude triggers `/pr-review` against it in the next session
where you ask for fleet status, or directly when you invoke review.

The reviewer's responsibilities:
- Verify the diff actually matches the task description in `pr.body` (which
  links back to the LOCAL-NNNN id).
- Confirm `expected_paths` and `forbidden_paths` were honored.
- Merge if clean; request changes if recoverable; close and move entry to
  `blocked/` with reason if not.

When a PR merges, Claude moves the task file from `review/` to `done/`,
appending a final history line with the merge SHA and date.

## Worker contract (summary)

The worker is implemented separately (see future
`~/dev/.claude/docs/standards/cleanup-backlog/worker-spec.md` when written).
For now, the contract is:

- Reads only from `pending/`.
- Claims by `mv pending/X.md active/X.md`.
- Operates in a fresh git clone per task at `/tmp/cleanup-work/<task-id>/`.
- Uses signed commits (the worker must have access to the GPG key configured
  on the host).
- Pushes to a branch named `chore/local-<task-id>`.
- Opens PR with label `local-dev` and body linking back to the task id.
- Never bypasses pre-commit (`--no-verify`) or signing (`--no-gpg-sign`).
  These are already blocked by `bash-pre-hook.sh` if the worker runs through
  Claude Code; if it runs standalone, the worker code must encode the same
  refusals.

## Integration with existing systems

| System | Relationship |
| --- | --- |
| `bash-pre-hook.sh` | Blocks --no-verify, --no-gpg-sign, force-push to main. Worker inherits these protections if it routes through Claude Code. |
| `validate-frontmatter.sh` | Validates the `schema_type: cleanup-task` frontmatter. Add `cleanup-task` to its known types. |
| `repo-compliance` skill | Findings can be piped to scout for backlog conversion. |
| `doc-audit` skill | Same. |
| `/pr-review` skill | Reviewer for `local-dev` labeled PRs. |
| Branch protection rulesets | PRs from worker are subject to all required checks unchanged. No special bypass. |

## Versioning

This document is the source of truth for the schema. When the schema changes,
bump the version line at the top and add a `## Migration` section describing
how existing entries should be updated. Workers and the scout agent must check
the version on startup and refuse to operate against a schema they do not know.
