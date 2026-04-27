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
[Exact next steps with commands — be specific enough to follow without context]

## Gotchas
[Non-obvious context the next session needs: workarounds, known issues, assumptions made]
```

### 4. Report

Output the path to the generated file so it can be referenced or committed.
