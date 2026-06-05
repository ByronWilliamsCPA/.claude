---
name: handoff
description: >
  Generate a structured handoff document for session continuity. Auto-activates on:
  handoff, session end, context handoff, end of session, switch context, next session,
  wrap up session
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
---

# Handoff Skill

Create a structured handoff document capturing current session state so the next
session can resume without context loss.

## Invocation

```text
/handoff
```

## Workflow

### 1. Gather State

```bash
git branch --show-current
git status
git log --oneline -10
git diff --stat
```

### 2. Check In-Progress Work

Review any active TODO items or in-progress tasks noted in the conversation.

### 3. Write Handoff Document

Output to: `tmp_cleanup/.tmp-handoff-$(date +%Y%m%d-%H%M).md`

The document must contain all six sections:

```markdown
# Session Handoff — {date}

## What Was Done
[Completed items with file paths changed]

## What Remains
[Incomplete items, ordered by priority]

## Key Decisions
[Architecture/design decisions made, with rationale]

## Files Modified
[From git diff --stat]

## How to Resume
[Exact next steps with commands -- be specific enough to follow without context]

## Gotchas
[Non-obvious context the next session needs: workarounds, known issues, assumptions made]
```

### 4. Report

Output the path to the generated file so it can be referenced or committed.

---

## Handoff Quality Standards

A handoff is a snapshot of a past moment, not ground truth. The consuming session must
treat it as a starting hypothesis, not a task list to execute blindly. The following
standards apply when authoring a handoff and when consuming one.

### For handoff authors

**Separate GOAL from MECHANISM.** For every prescribed action, state:
- The GOAL: what outcome the change must achieve (required)
- The MECHANISM: the specific edit or command assumed to achieve it (optional, clearly flagged as an assumption)

When the mechanism rests on an unverified structural assumption (CI runs tests inline,
a field exists in the data, a tool is on PATH, a function accepts a certain parameter),
the consuming session needs the goal to recover gracefully when the assumption fails.

Bad: "Add a step inside the CI Gate job, which already has Python set up"
Good: "Ensure CI validates the manifest self-consistency check. The current ci.yml may
      delegate to a reusable workflow; confirm where Python tests actually run before
      deciding which file to edit."

**Distinguish verified from speculative.** Tag any field names, API endpoints, CLI
flags, assertion patterns, or identifier names that were NOT directly verified against
the live source as `[VERIFY before implementing]`. This tells the consuming session
which parts need a probe check:

```markdown
## Implementation notes
- The manifest uses `applies_to` (verified at manifest:line 42)
- The check accepts `--check-id` flag [VERIFY: grep check-repo-compliance.py --help]
- Severity should be `suggested` on introduction [VERIFY: confirm current policy]
```

**Pre-written artifacts must be paste-correct for the introduction state.** When a
handoff includes literal YAML, JSON, or code blocks to be pasted, the literal value
must be correct for the moment of introduction, not the eventual target state. When
introduction state and end state differ on a field (e.g., `severity: suggested`
introducing a check that will later be promoted to `severity: critical`), annotate
the divergent field inline:

```yaml
severity: suggested  # target: critical after 100% fleet reach
```

Do not rely on a separate "Rollout note" prose section to communicate the introduction
state; an implementer copying a block trusts the block, not a paragraph three sections away.

**Include coupled-invariant checklists.** For known artifact types, list the secondary
edits that must accompany the primary change:

- **Standards manifest check addition:** also update `last_updated` in the manifest header,
  add a `### Added` CHANGELOG entry, classify the commit per `manifest-changes.md` (feat vs fix)
- **Pre-commit hook addition:** also verify `rev:` is pinned to a SHA, add to `additional_dependencies`
  if needed, run `pre-commit autoupdate` or pin manually

### For handoff consumers (mandatory pre-flight before acting on any handoff)

**Re-verify current state before executing.** A handoff's "What Remains" section
describes work as of the moment it was written. Branches and PRs advance after a
handoff is created. The cheapest, highest-leverage first action when resuming is:

```bash
git fetch --all
gh pr list --state all
gh pr view {PR_NUMBER} --json state,mergeable,checks  # if PR referenced
```

Treat "What Remains" as a hypothesis. Diagnose the CURRENT state of the work
before executing the handoff's plan. A 2-minute check may reveal that the
"remaining work" is already complete, or that the actual blocker is different
from what the handoff described.

**Verify external identifiers before building.** Before using any identifier named
in the handoff (check IDs, file paths, CLI flags, API endpoints, function names,
schema field names), confirm it exists in the current live source:

- Check IDs: grep the manifest (`grep "id: CI-NNN" docs/standards-manifest.yaml`)
- File paths: `test -f {path}` or `ls {path}`
- Function names: `grep "def {name}" {file}`
- CLI flags: `{tool} --help | grep {flag}`

A handoff mixes verified observations with speculative scaffolding, and the reader
cannot tell them apart by tone. The fix is to verify before building.

**Probe data schemas before writing assertions.** If the handoff prescribes tests
or assertions against a data structure, run a schema probe of the actual data first:

```python
import yaml; data = yaml.safe_load(open("manifest.yaml")); print(list(data['checks'][0].keys()))
```

Assertions against fields that do not exist will raise `KeyError` (dict key access) or fail for the wrong reason (if `dict.get()` returns `None` and the assertion happens to pass on that).
