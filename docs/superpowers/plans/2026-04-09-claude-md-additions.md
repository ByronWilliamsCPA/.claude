---
schema_type: planning
title: "CLAUDE.md Global Standards Additions"
status: draft
owner: core-maintainer
purpose: "Implementation plan for three inline text additions to CLAUDE.md encoding environment debugging order, no-workaround generalization, and project docs over memory."
component: Development-Tools
source: "docs/superpowers/specs/2026-04-09-claude-md-additions-design.md"
tags:
  - automation
  - tooling
  - documentation
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three inline sentences to the global CLAUDE.md that encode recurring session corrections as permanent behavioral rules.

**Architecture:** Three text edits to a single file. No new files. No scripts. No hooks. The source file is `/home/byron/dev/.claude/CLAUDE.md`, symlinked to `~/.claude/CLAUDE.md` - editing the source is sufficient.

**Tech Stack:** Markdown (text edit only)

---

### Task 1: Add three behavioral rules to CLAUDE.md and commit

**Files:**
- Modify: `/home/byron/dev/.claude/CLAUDE.md`

- [ ] **Step 1: Verify the exact anchor text for the Project Context addition**

Read lines 7-12 of `/home/byron/dev/.claude/CLAUDE.md`.

Expected content:

```markdown
## Project Context

For project context, always search project docs and markdown files first (especially files in
docs/, initiatives/, or project root). Do not search memory or make assumptions about
organizational priorities.
```

- [ ] **Step 2: Add the project docs rule to the Project Context section**

In `/home/byron/dev/.claude/CLAUDE.md`, replace:

```text
Do not search memory or make assumptions about
organizational priorities.
```

With:

```text
Do not search memory or make assumptions about
organizational priorities.

When asked about business priorities, organizational strategy, or project decisions, read the
relevant project files before answering. If no file covers the topic, state what was searched
and answer from general knowledge with an explicit flag that the answer may not reflect current
project priorities.
```

- [ ] **Step 3: Verify the Project Context section now reads correctly**

Read lines 7-16 of `/home/byron/dev/.claude/CLAUDE.md`.

Expected: both paragraphs present, blank line between them, no truncation.

- [ ] **Step 4: Verify the exact anchor text for the Code Quality addition**

Read lines 13-20 of `/home/byron/dev/.claude/CLAUDE.md` (line numbers will have shifted by the lines added in Step 2 - read by content, not line number).

Expected content:

```markdown
## Code Quality

When SonarCloud or linting tools flag issues, fix the actual issues rather than proposing
exclusions. Only exclude files if explicitly approved by the user.
```

- [ ] **Step 5: Add the no-workaround rule to the Code Quality section**

In `/home/byron/dev/.claude/CLAUDE.md`, replace:

```text
exclusions. Only exclude files if explicitly approved by the user.
```

With:

```text
exclusions. Only exclude files if explicitly approved by the user.

This applies to all quality gates: never propose `# noqa` comments, `# type: ignore`,
`pytest.mark.skip`, `--no-verify`, or CI bypass flags as solutions. Fix the root cause.
Exceptions: vendored or third-party code that cannot be changed, or suppression paired with a
tracking reference (ticket number, GitHub issue, or TODO with link).
```

- [ ] **Step 6: Verify the Code Quality section now reads correctly**

Read the `## Code Quality` section (expected: both paragraphs present, blank line between them).

- [ ] **Step 7: Verify the exact anchor text for the System / Shell addition**

Find the `## System / Shell` section in `/home/byron/dev/.claude/CLAUDE.md`.

Expected content:

```markdown
## System / Shell

When commands fail due to permissions (e.g., mkdir, mount), try with sudo immediately.
```

- [ ] **Step 8: Add the environment debugging rule to the System / Shell section**

In `/home/byron/dev/.claude/CLAUDE.md`, replace:

```text
When commands fail due to permissions (e.g., mkdir, mount), try with sudo immediately.
```

With:

```text
When commands fail due to permissions (e.g., mkdir, mount), try with sudo immediately.

When a connection error, socket failure, or service-unreachable symptom appears, check
platform-level causes first: WSL2 port forwarding rules, Docker bridge networking, Unix socket
paths, and container health. Do not exhaust code-level fixes before ruling out the environment.
```

- [ ] **Step 9: Verify the System / Shell section now reads correctly**

Read the `## System / Shell` section (expected: both paragraphs present, blank line between them).

- [ ] **Step 10: Run pre-commit on CLAUDE.md**

```bash
cd /home/byron/dev/.claude && pre-commit run --files CLAUDE.md
```

Expected: all hooks pass.

- [ ] **Step 11: Confirm all three additions are present**

```bash
grep -n "quality gates\|platform-level causes\|explicit flag" /home/byron/dev/.claude/CLAUDE.md
```

Expected: three matches, one for each addition.

- [ ] **Step 12: Commit**

```bash
git -C /home/byron/dev/.claude add CLAUDE.md
git -C /home/byron/dev/.claude commit -m "feat: add environment debugging, no-workaround, and project-docs-over-memory rules to CLAUDE.md"
```
