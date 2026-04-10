---
schema_type: common
title: "CLAUDE.md Global Standards Additions — Three Behavioral Rules"
status: draft
owner: core-maintainer
purpose: "Design spec for three targeted additions to the global CLAUDE.md that encode recurring session corrections into permanent behavioral rules: environment debugging order, no-workaround generalization, and project docs over memory."
tags:
  - tooling
  - specifications
  - documentation
---

> **Date**: 2026-04-09
> **Status**: Approved
> **Scope**: Global `~/.claude/CLAUDE.md` (source at `~/dev/.claude/CLAUDE.md`)

## Problem

Three patterns appeared repeatedly across 110 sessions in the March–April 2026 usage report:

1. **Environment debugging last**: Connection and service-unreachable errors triggered extensive code-level debugging before WSL2 port forwarding, Docker networking, or IPC pipe issues were checked. The environment was the root cause in 20+ sessions.

2. **Workaround instinct**: The existing SonarCloud rule ("fix issues, don't exclude") did not transfer to `# noqa`, `# type: ignore`, `pytest.mark.skip`, `--no-verify`, and CI bypass flags. Each suppression mechanism required a fresh correction.

3. **Memory over docs**: When asked about business priorities or project decisions, the assistant answered from general knowledge or memory instead of reading project files. The existing "search docs first" instruction lacked a fallback protocol.

## Goals

- Encode all three corrections into CLAUDE.md so they apply automatically in every session
- Keep additions minimal — one to three sentences each, inline in the relevant section
- Preserve the document's scan-friendly structure (short sections, no new headings)

## Non-Goals

- No new CLAUDE.md sections — all additions are inline in existing sections
- No changes to project-level CLAUDE.md files — this is global scope only
- No changes to rule files (git-workflow.md, pre-commit.md, etc.)

## Design

### Approach: Minimal Inline Additions (Option A)

Append one to three sentences to each of three existing sections. No structural changes.

---

### Addition 1 — `## Project Context`

**Location**: Append after "Do not search memory or make assumptions about organizational priorities."

**Text to add**:

> When asked about business priorities, organizational strategy, or project decisions, read the relevant project files before answering. If no file covers the topic, state what was searched and answer from general knowledge with an explicit flag that the answer may not reflect current project priorities.

**Behavior change**: The assistant must now (a) read project files before answering context questions, and (b) explicitly flag when falling back to general knowledge, naming what was searched.

---

### Addition 2 — `## Code Quality`

**Location**: Append after "Only exclude files if explicitly approved by the user."

**Text to add**:

> This applies to all quality gates: never propose `# noqa` comments, `# type: ignore`, `pytest.mark.skip`, `--no-verify`, or CI bypass flags as solutions. Fix the root cause. Exceptions: vendored or third-party code that cannot be changed, or suppression paired with a tracking reference (ticket number, GitHub issue, or TODO with link).

**Behavior change**: Generalizes the existing SonarCloud rule to cover all suppression and bypass mechanisms. Adds an explicit escape hatch for third-party code and tracked suppressions to avoid over-blocking legitimate use cases.

---

### Addition 3 — `## System / Shell`

**Location**: Append after "When commands fail due to permissions (e.g., mkdir, mount), try with sudo immediately."

**Text to add**:

> When a connection error, socket failure, or service-unreachable symptom appears, check platform-level causes first: WSL2 port forwarding rules, Docker bridge networking, Unix socket paths, and container health. Do not exhaust code-level fixes before ruling out the environment.

**Trigger**: Narrow — applies only to connection errors, socket/IPC failures, and service-unreachable symptoms. Does not apply to pure logic bugs, test failures, or import errors.

---

## Implementation

Three text edits to a single file: `CLAUDE.md` (source at `/home/byron/dev/.claude/CLAUDE.md`, symlinked to `~/.claude/CLAUDE.md`).

No new files. No script changes. No hook changes.

## Testing

Manual verification: after editing, read each affected section and confirm the new sentences are present and grammatically correct. No automated test required.

## File Locations

| File | Action |
| ---- | ------ |
| `CLAUDE.md` (repo root) | Three inline text additions |
