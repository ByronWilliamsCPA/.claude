# 03 - Code Quality and Maintainability

The repo holds against its own house standard. `ruff check` passes fully, including C901 complexity (<=10), PLR0912 branches (<=12), PLR0915 statements (<=50), and PLR0913 args (<=5). Zero real TODO/FIXME/HACK/XXX markers (the lone grep hit is a regex literal). All 11 `# type: ignore`, 9 `# noqa`, and 29 `cast` occurrences carry inline justifications. Two test skips exist, both legitimate platform `skipif` guards; no xfail, no `assert True` anti-patterns. The one High finding is a coverage-measurement gap, not a code defect. Git history is shallow (50 commits since 2026-05-24), so blame-age is uninformative, and immaterial given near-zero debt markers.

## CQ-01 - Coverage gate measures only `src/`, leaving ~7,700 LOC of script logic ungated

- Severity: High
- Effort: M (add `scripts/` to coverage source, then close whatever gaps the real number exposes; basis: config change plus likely test backfill)
- Evidence: `pyproject.toml:484` sets `source = ["src"]` and `:494` omits `scripts/*`. `src/` is 132 LOC, but `scripts/` holds 6,490 LOC including the three largest, most-branching modules (`check-required-checks.py` 872, `doc-audit.py` 794, `check-repo-compliance.py` 745). `--cov-fail-under=80` therefore certifies 132 lines while the bulk of production logic is unmeasured. Tests for scripts do exist (283 test functions loaded via importlib), so the gap is measurement, not absence. Live coverage number was unobtainable (pytest/pytest-cov not installed in this environment).
- Recommendation: Add `scripts` (and `tools`) to `[tool.coverage.run] source`, re-baseline, and raise gaps to the 80% gate. This converts an existing-but-unmeasured test suite into an enforced one.

## CQ-02 - Near-duplicate `gh` subprocess wrappers across compliance scripts

- Severity: Low
- Effort: M (extract a shared module and rewire call sites; basis: cross-file refactor with test updates)
- Evidence: `check-repo-compliance.py:141` (`gh`) and `:159` (`gh_paginated_array`) reimplement the same run-plus-JSON-plus-error-tuple logic as `check-required-checks.py:629` (`_run_gh`). The repo already models a shared-lib pattern in `compliance_log_common.py`.
- Recommendation: Extract a `gh_api_common.py` helper and route both scripts through it.

## CQ-03 - 61 production `Any` annotations at decode boundaries

- Severity: Low
- Effort: M (introduce TypedDicts where shapes are fixed; basis: incremental typing across three modules)
- Evidence: 61 production `Any` annotations (105 total), concentrated on dynamic-decode boundaries (Actions matrix YAML, `gh` JSON, frontmatter): `check-required-checks.py` (18), `populate-github-repos.py` (14), `compliance_log_common.py` (7). Defensible at the boundary, but they erode the strict-typing guarantee elsewhere.
- Recommendation: Replace `Any` with `TypedDict` where the parsed shape is fixed; keep `Any` only at genuinely dynamic edges.

## CQ-04 - Five tests assert only by absence of a raised exception

- Severity: Low
- Effort: S (add explicit assertions; basis: five one-line edits)
- Evidence: `tests/unit/test_setup_org_rulesets.py` lines 34, 46, 51, 211, 227 use the pattern `validate_solo_dev_safe(body)  # no exception`. Valid idiom, but the success condition is implicit.
- Recommendation: Add an explicit assertion or `pytest.raises`-style negative to make the intended behavior visible.

## Clean areas

- `ruff check` passes fully (C901, PLR0912, PLR0915, PLR0913 all within thresholds).
- Zero real deferred-work markers; all 11 `# type: ignore`, 9 `# noqa`, and 29 `cast` carry justifications.
- Two skips, both legitimate platform `skipif`; no xfail, no `assert True`/`or True` anti-patterns.

## Machine-readable findings

```json
[
  {"id": "CQ-01", "title": "Coverage gate measures only src/, leaving ~7700 LOC of scripts ungated", "domain": "code-quality", "severity": "High", "effort": "M", "files": ["pyproject.toml"], "evidence": "pyproject.toml:484 source=[\"src\"], :494 omits scripts/*; src/ is 132 LOC vs scripts/ 6490 LOC; --cov-fail-under=80 certifies only 132 lines", "recommendation": "Add scripts/ and tools/ to coverage source, re-baseline, and enforce the 80% gate on the existing script tests.", "cve": ""},
  {"id": "CQ-02", "title": "Near-duplicate gh subprocess wrappers across compliance scripts", "domain": "code-quality", "severity": "Low", "effort": "M", "files": ["scripts/check-repo-compliance.py", "scripts/check-required-checks.py"], "evidence": "check-repo-compliance.py:141/159 vs check-required-checks.py:629 reimplement the same gh run+JSON+error-tuple logic", "recommendation": "Extract a gh_api_common.py helper and route both scripts through it.", "cve": ""},
  {"id": "CQ-03", "title": "61 production Any annotations at decode boundaries", "domain": "code-quality", "severity": "Low", "effort": "M", "files": ["scripts/check-required-checks.py", "scripts/populate-github-repos.py", "scripts/compliance_log_common.py"], "evidence": "61 production Any (105 total): check-required-checks.py 18, populate-github-repos.py 14, compliance_log_common.py 7", "recommendation": "Replace Any with TypedDict where parsed shapes are fixed; keep Any only at dynamic edges.", "cve": ""},
  {"id": "CQ-04", "title": "Five tests assert only by absence of a raised exception", "domain": "code-quality", "severity": "Low", "effort": "S", "files": ["tests/unit/test_setup_org_rulesets.py"], "evidence": "test_setup_org_rulesets.py lines 34,46,51,211,227 use 'validate_solo_dev_safe(body)  # no exception' with no explicit assert", "recommendation": "Add an explicit assertion to make the success condition visible.", "cve": ""}
]
```
