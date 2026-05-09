# Compliance Retrospective: 2026-05-07

## Session Summary

| Metric | Value |
|--------|-------|
| Repos reviewed | 1 (ByronWilliamsCPA/family-office-portal) |
| Total findings (net of overrides) | 26 |
| Critical | 7 |
| Important | 17 |
| Suggested | 2 |
| Passes | 3 (FOUND-001, FOUND-005, OSSF-003) |
| Unclassified general candidates | 6 |
| Overrides applied | 0 |

**Critical findings breakdown:**

- FOUND-002: CONTRIBUTING.md absent
- CI-014 through CI-016: Gate jobs absent (root cause: no .github/workflows/ at all)
- CI-017: Branch protection not configured on main
- OSSF-002: SECURITY.md uses public email; GitHub PVR not enabled

**Root cause note:** CI-001 through CI-016 all stem from a single gap -- the
.github/workflows/ directory is entirely absent. Auditors should treat the
entire CI domain as one remediation unit for Phase 0 repos rather than
reporting 14+ individual CI findings. See scope expansion candidates below.

---

## Patterns Observed

This is the first retrospective in this session log. No cross-repo pattern
threshold (3+ repos) can be reached in a single-repo session. All six
unclassified general candidates are recorded below for future cross-session
tracking. A pattern is promoted to manifest candidate when it appears in 3 or
more distinct repos across retrospectives.

| Unclassified candidate | Repos (this session) | Running total |
|------------------------|---------------------|---------------|
| pyproject.toml missing authors/maintainers fields | 1 (family-office-portal) | 1 |
| LICENSE lacks SPDX identifier line | 1 (family-office-portal) | 1 |
| .editorconfig absent from project root | 1 (family-office-portal) | 1 |
| docs/ structure misaligned (ADRs in docs/planning/adr/ not docs/architecture/) | 1 (family-office-portal) | 1 |
| docs/known-vulnerabilities.md absent (SECURITY.md references path) | 1 (family-office-portal) | 1 |
| No source code or tests/ directory (Phase 0 -- expected) | 1 (family-office-portal) | 1 |

Note: docs/known-vulnerabilities.md is already covered by FOUND-009 in the
manifest. The general auditor surfaced it as an unclassified candidate because
the domain agent filed it correctly as FOUND-009. No duplication action needed.

---

## Proposed Manifest Additions

No patterns have reached the 3-repo threshold in this session. The candidates
below are pre-staged for promotion in future sessions. YAML snippets are
provided so they are ready to paste once the threshold is met.

### Pre-staged: pyproject.toml authors/maintainers fields

Appears in 1 of 1 repos. Promote when count reaches 3.

```yaml
- id: FOUND-015
  domain: foundations
  severity: suggested
  description: "pyproject.toml [project] table includes authors and maintainers fields"
  verify: "content_present: pyproject.toml, authors"
  override_eligible: true
```

### Pre-staged: LICENSE SPDX identifier line

Appears in 1 of 1 repos. Promote when count reaches 3.

```yaml
- id: FOUND-016
  domain: foundations
  severity: suggested
  description: "LICENSE file contains an SPDX-License-Identifier line"
  verify: "content_present: LICENSE, SPDX-License-Identifier"
  override_eligible: true
```

### Pre-staged: .editorconfig present

Appears in 1 of 1 repos. Promote when count reaches 3.

```yaml
- id: FOUND-017
  domain: foundations
  severity: suggested
  description: ".editorconfig present at project root"
  verify: "file_exists: .editorconfig"
  override_eligible: true
```

---

## Agent Scope Expansion Candidates

### ci-auditor: Phase 0 short-circuit mode

When .github/workflows/ is entirely absent, the CI auditor currently files
CI-001 through CI-016 as 14+ individual findings, all with the same root cause.
Consider adding a guard at the top of the CI audit: if the workflows directory
is absent, emit one consolidated finding ("CI-000: .github/workflows/ directory
absent -- all CI checks skipped") and skip the remaining CI-domain checks.
This prevents the findings list from being dominated by a single structural gap
and makes triage faster.

### ci-auditor: OSSF-007 is org-level, not repo-level

OSSF-007 (org requires 2FA) is the same result for every repo in the
ByronWilliamsCPA org. The CI/OSSF auditor currently re-queries the GitHub API
for this on every repo audit. Consider caching the result at session level and
re-using it without an API call on subsequent repos in the same org.

### foundations-auditor: Positive-assertion inversion risk (haiku model)

In this session the foundations agent (running on haiku) inverted FOUND-005 and
FOUND-006: it reported FOUND-005 (.worktrees/ in .gitignore) as a FINDING when
it was a PASS, and FOUND-006 (docs/compliance-reports/ in .gitignore) as a PASS
when it was a FINDING. The underlying manifest descriptions for both checks are
phrased as positive assertions ("X present in .gitignore"). Haiku models
sometimes negate the assertion direction when summarizing boolean results.

Recommended mitigations (pick one or both):

1. Rephrase verify field to an imperative form: `content_present:
   .gitignore, .worktrees/` becomes `verify: grep_returns_match: .gitignore,
   ^\\.worktrees/` so the agent is checking a literal match rather than
   interpreting a description.
2. Add an explicit `pass_if: match_found` / `fail_if: match_absent` field to
   content_present checks so the pass/fail direction is unambiguous regardless
   of how the description is phrased.

---

## High-Frequency Existing Checks

Only one repo was audited this session, so no check can meet the 50% threshold
across multiple repos. The following checks failed and are candidates for
high-frequency status as more repos are audited.

Checks that failed in this session (all 100% of repos audited):

| Check | Severity | Description |
|-------|----------|-------------|
| FOUND-002 | critical | CONTRIBUTING.md absent |
| FOUND-003 | important | CHANGELOG.md absent |
| FOUND-004 | important | CODEOWNERS at root not .github/ |
| FOUND-006 | important | docs/compliance-reports/ absent from .gitignore |
| FOUND-009 | important | docs/known-vulnerabilities.md absent |
| FOUND-010 | important | AGENTS.md absent |
| FOUND-014 | suggested | docs/architecture/ absent |
| TOOL-007 | important | darglint absent from dev dependencies |
| PC-006 | important | darglint hook absent |
| CI-001 to CI-016 | critical/important | All CI checks (no workflows dir) |
| CI-017 | critical | Branch protection not configured |
| CI-020 | important | renovate.json absent |
| OSSF-001 | important | No OpenSSF Best Practices Badge filed |
| OSSF-002 | critical | No private vulnerability reporting channel |
| OSSF-004 | important | CHANGELOG absent (CVE check unverifiable) |
| OSSF-007 | important | ByronWilliamsCPA org does not require 2FA |

**Priority remediation order for family-office-portal (Phase 0 to Phase 1 gate):**

1. Add .github/workflows/ using org reusable workflows (resolves 14 CI findings at once)
2. Configure branch protection on main (CI-017)
3. Add CONTRIBUTING.md (FOUND-002, critical)
4. Enable GitHub Private Vulnerability Reporting; remove public email from SECURITY.md (OSSF-002, critical)
5. Enable 2FA requirement at org level (OSSF-007)
6. Add CHANGELOG.md, AGENTS.md, CODE_OF_CONDUCT.md, GOVERNANCE.md (FOUND-003, FOUND-010, FOUND-012, FOUND-013)
7. Move CODEOWNERS to .github/CODEOWNERS (FOUND-004)
8. Add docs/compliance-reports/ to .gitignore (FOUND-006)
9. Add docs/known-vulnerabilities.md from template (FOUND-009)
10. Add darglint to dev deps and pre-commit config (TOOL-007, PC-006)
11. Add renovate.json (CI-020)
12. File OpenSSF Best Practices Badge (OSSF-001)
