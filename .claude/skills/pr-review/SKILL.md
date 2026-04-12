---
name: pr-review
description: >
  Comprehensive PR review from a GitHub PR URL. Immediately triggers GitHub
  Copilot review, fetches SonarQube PR-specific findings, and runs up to 8
  parallel Sonnet review agents with content-aware routing. Outputs a tiered
  report (Critical / Important / Suggested / Informational) — nothing is
  filtered, everything is categorized. Auto-activates on: review PR, review
  this PR, review pull request, /pr-review, pr review, review the PR
---

# PR Review Skill

Comprehensive pull request review orchestrator. Provide a GitHub PR URL and
this skill coordinates the full review pipeline: Copilot trigger, SonarQube
fetch, parallel agent review, confidence scoring, and consolidated output.

## Usage

```
/pr-review https://github.com/owner/repo/pull/123
```

## Design Principles

- **Nothing is filtered.** All findings are reported at the appropriate
  priority tier. The old 80-confidence hard cut is replaced by
  Critical / Important / Suggested / Informational tiers.
- **SonarQube findings are authoritative.** They bypass AI confidence scoring
  and are always included regardless of perceived severity.
- **Copilot fires first.** The review request is sent to GitHub Copilot
  immediately so its async review runs in parallel with ours.
- **No local checkout.** All context is fetched via `gh` CLI. The user's
  working tree is never touched.

## Routing

Load `workflows/pr-review.md` for the complete orchestration workflow.
