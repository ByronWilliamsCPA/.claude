# Handoff: Test Compliance Verification Tools

> **For**: Cookiecutter Python Template Team
> **From**: Claude Code Standards Team
> **Date**: 2025-01-29
> **Priority**: Medium

## Overview

This document contains test compliance verification tools developed during Claude Code standards work. These tools should be incorporated into the `cookiecutter-python-template` to ensure consistent testing practices across all generated projects.

## Files to Add

### 1. Directory Structure

```
{{cookiecutter.project_slug}}/
├── scripts/
│   ├── verify_test_structure.py
│   ├── check_test_ratios.py
│   ├── audit_test_coverage.py
│   └── weekly_test_audit.py
├── .github/workflows/
│   └── test-compliance.yml
└── tests/
    ├── unit/
    │   └── .gitkeep
    ├── integration/
    │   └── .gitkeep
    ├── fixtures/
    │   ├── __init__.py
    │   ├── expected/
    │   │   └── .gitkeep
    │   └── README.md
    └── conftest.py  # Add marker tracking hooks
```

---

## Script Files

### scripts/verify_test_structure.py

```python
#!/usr/bin/env python3
"""Verify test directory structure matches project standards.

Usage:
    uv run python scripts/verify_test_structure.py

Exit codes:
    0 - All required directories present
    1 - Missing required directories
"""
from pathlib import Path
import sys

REQUIRED_DIRS = ["unit", "integration", "fixtures"]
RECOMMENDED_DIRS = ["e2e", "security", "benchmark", "api"]


def verify_structure(tests_path: Path) -> tuple[list[str], list[str]]:
    """Check for required and recommended test directories.

    Args:
        tests_path: Path to tests directory

    Returns:
        Tuple of (missing_required, missing_recommended) directory names
    """
    missing_required = []
    missing_recommended = []

    for dir_name in REQUIRED_DIRS:
        if not (tests_path / dir_name).is_dir():
            missing_required.append(dir_name)

    for dir_name in RECOMMENDED_DIRS:
        if not (tests_path / dir_name).is_dir():
            missing_recommended.append(dir_name)

    return missing_required, missing_recommended


def main() -> int:
    """Main entry point."""
    tests_path = Path("tests")

    if not tests_path.exists():
        print("ERROR: tests/ directory not found")
        return 1

    missing_req, missing_rec = verify_structure(tests_path)

    if missing_req:
        print(f"ERROR: Missing required directories: {missing_req}")
        return 1

    if missing_rec:
        print(f"WARNING: Missing recommended directories: {missing_rec}")

    print("✓ Test structure verification passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### scripts/check_test_ratios.py

```python
#!/usr/bin/env python3
"""Enforce healthy test pyramid ratios.

Target ratios (configurable):
    - Unit tests: 70%
    - Integration tests: 20%
    - E2E tests: 10%

Usage:
    uv run python scripts/check_test_ratios.py

Exit codes:
    0 - Ratios within tolerance
    1 - Ratio violations detected
"""
import subprocess
import sys

# Target ratios (unit:integration:e2e) - adjust per project type
TARGET_RATIOS = {
    "unit": 0.70,
    "integration": 0.20,
    "e2e": 0.10,
}

TOLERANCE = 0.10  # Allow 10% deviation


def get_test_counts() -> dict[str, int]:
    """Count tests by marker using pytest collection."""
    counts = {"unit": 0, "integration": 0, "e2e": 0, "other": 0}

    for marker in ["unit", "integration", "e2e"]:
        result = subprocess.run(
            ["uv", "run", "pytest", "--collect-only", "-q", "-m", marker],
            capture_output=True,
            text=True,
        )
        # Count lines that look like test items
        counts[marker] = len(
            [l for l in result.stdout.split("\n") if "::" in l and "test_" in l]
        )

    return counts


def check_ratios(counts: dict[str, int]) -> list[str]:
    """Check if test ratios are within tolerance.

    Args:
        counts: Dict mapping marker name to test count

    Returns:
        List of violation messages (empty if all pass)
    """
    total = sum(counts.values())
    if total == 0:
        return ["ERROR: No tests found"]

    violations = []
    for marker, target in TARGET_RATIOS.items():
        actual = counts.get(marker, 0) / total
        if actual < target - TOLERANCE:
            needed = int((target - actual) * total)
            violations.append(
                f"{marker}: {actual:.1%} (target: {target:.0%}, need {needed} more)"
            )

    return violations


def main() -> int:
    """Main entry point."""
    counts = get_test_counts()
    total = sum(counts.values())

    print("Test counts by marker:")
    for marker, count in sorted(counts.items()):
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {marker}: {count} ({pct:.1f}%)")

    violations = check_ratios(counts)
    if violations:
        print("\nTest ratio violations:")
        for v in violations:
            print(f"  ⚠ {v}")
        return 1

    print("\n✓ Test ratios within acceptable range")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### scripts/audit_test_coverage.py

```python
#!/usr/bin/env python3
"""Audit which source modules have corresponding test files.

Usage:
    uv run python scripts/audit_test_coverage.py

Exit codes:
    0 - 80%+ modules have tests
    1 - Less than 80% module coverage
"""
from pathlib import Path
import sys


def find_untested_modules(src_path: Path, tests_path: Path) -> list[Path]:
    """Find source modules without corresponding test files.

    Args:
        src_path: Path to source directory
        tests_path: Path to tests directory

    Returns:
        List of source file paths without tests
    """
    untested = []

    for src_file in src_path.rglob("*.py"):
        # Skip private/internal modules
        if src_file.name.startswith("_"):
            continue

        # Expected test file patterns
        relative = src_file.relative_to(src_path)
        test_patterns = [
            tests_path / "unit" / f"test_{relative}",
            tests_path / "unit" / relative.parent / f"test_{relative.name}",
            tests_path / f"test_{relative.stem}.py",
        ]

        if not any(p.exists() for p in test_patterns):
            untested.append(src_file)

    return untested


def generate_report(untested: list[Path], src_path: Path) -> str:
    """Generate coverage audit report.

    Args:
        untested: List of untested module paths
        src_path: Path to source directory

    Returns:
        Markdown formatted report
    """
    all_modules = [p for p in src_path.rglob("*.py") if not p.name.startswith("_")]
    total_modules = len(all_modules)
    tested = total_modules - len(untested)
    coverage = (tested / total_modules) * 100 if total_modules else 0

    report = [
        "# Test Coverage Audit Report",
        "",
        f"**Module Coverage**: {tested}/{total_modules} ({coverage:.1f}%)",
        "",
    ]

    if untested:
        report.extend(
            [
                "## Untested Modules",
                "",
                *[f"- `{p}`" for p in sorted(untested)],
            ]
        )
    else:
        report.append("All modules have corresponding test files!")

    return "\n".join(report)


def main() -> int:
    """Main entry point."""
    src_path = Path("src")
    tests_path = Path("tests")

    if not src_path.exists():
        print("ERROR: src/ directory not found")
        return 1

    untested = find_untested_modules(src_path, tests_path)
    report = generate_report(untested, src_path)
    print(report)

    # Fail if less than 80% modules have tests
    all_modules = [p for p in src_path.rglob("*.py") if not p.name.startswith("_")]
    total = len(all_modules)

    if total > 0 and len(untested) / total > 0.20:
        print("\n❌ Less than 80% of modules have test files")
        return 1

    print("\n✓ Module coverage meets 80% threshold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### scripts/weekly_test_audit.py

```python
#!/usr/bin/env python3
"""Generate weekly test health report.

Usage:
    uv run python scripts/weekly_test_audit.py

Outputs:
    - Console summary
    - reports/test-audit-YYYYMMDD.md
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path


def run_audit() -> dict:
    """Collect all test metrics.

    Returns:
        Dict containing all test health metrics
    """
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "structure": {"passed": False},
        "ratios": {},
        "coverage": {"line": 0, "branch": 0},
        "mutation_score": None,
    }

    # Structure check
    result = subprocess.run(
        ["uv", "run", "python", "scripts/verify_test_structure.py"],
        capture_output=True,
        text=True,
    )
    metrics["structure"]["passed"] = result.returncode == 0

    # Coverage
    result = subprocess.run(
        ["uv", "run", "pytest", "--cov=src", "--cov-report=json", "-q", "--tb=no"],
        capture_output=True,
        text=True,
    )
    coverage_file = Path("coverage.json")
    if coverage_file.exists():
        with open(coverage_file) as f:
            cov_data = json.load(f)
            metrics["coverage"] = {
                "line": cov_data["totals"]["percent_covered"],
                "branch": cov_data["totals"].get("covered_branches", 0)
                / max(cov_data["totals"].get("num_branches", 1), 1)
                * 100,
            }
        coverage_file.unlink()  # Clean up

    return metrics


def generate_recommendations(metrics: dict) -> str:
    """Generate actionable recommendations based on metrics.

    Args:
        metrics: Test health metrics dict

    Returns:
        Markdown formatted recommendations
    """
    recs = []

    if metrics["coverage"].get("line", 0) < 80:
        recs.append("- Increase line coverage to meet 80% minimum")
    if metrics["coverage"].get("branch", 0) < 80:
        recs.append("- Add tests for uncovered branches")
    if not metrics["structure"].get("passed"):
        recs.append("- Fix test directory structure")

    return "\n".join(recs) if recs else "All checks passing! 🎉"


def format_report(metrics: dict) -> str:
    """Format metrics as markdown report.

    Args:
        metrics: Test health metrics dict

    Returns:
        Markdown formatted report
    """
    return f"""# Weekly Test Audit Report

**Generated**: {metrics['timestamp']}

## Summary

| Metric | Value | Status |
|--------|-------|--------|
| Structure Valid | {metrics['structure'].get('passed', 'N/A')} | {'✅' if metrics['structure'].get('passed') else '❌'} |
| Line Coverage | {metrics['coverage'].get('line', 0):.1f}% | {'✅' if metrics['coverage'].get('line', 0) >= 80 else '❌'} |
| Branch Coverage | {metrics['coverage'].get('branch', 0):.1f}% | {'✅' if metrics['coverage'].get('branch', 0) >= 80 else '❌'} |

## Recommendations

{generate_recommendations(metrics)}
"""


def main() -> None:
    """Main entry point."""
    metrics = run_audit()
    report = format_report(metrics)

    # Save report
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / f"test-audit-{datetime.now():%Y%m%d}.md"
    report_path.write_text(report)

    print(f"Report saved to {report_path}")
    print()
    print(report)


if __name__ == "__main__":
    main()
```

---

## GitHub Actions Workflow

### .github/workflows/test-compliance.yml

```yaml
name: Test Compliance

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  verify-structure:
    name: Verify Test Structure
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Verify test structure
        run: uv run python scripts/verify_test_structure.py

      - name: Check test ratios
        run: uv run python scripts/check_test_ratios.py
        continue-on-error: true  # Warning only for new projects

      - name: Audit module coverage
        run: uv run python scripts/audit_test_coverage.py

  marker-coverage:
    name: Test Marker Coverage
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Run tests with marker report
        run: |
          uv run pytest --tb=no -q 2>&1 | tee test-output.txt

          # Check for unmarked tests (warning threshold)
          if grep -q "UNMARKED:" test-output.txt; then
            UNMARKED=$(grep "UNMARKED:" test-output.txt | grep -oP '\d+' | head -1)
            if [ -n "$UNMARKED" ] && [ "$UNMARKED" -gt 10 ]; then
              echo "::warning::Found $UNMARKED unmarked tests"
            fi
          fi
```

---

## Pre-commit Configuration

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  # ... existing repos ...

  - repo: local
    hooks:
      - id: verify-test-structure
        name: Verify test structure
        entry: uv run python scripts/verify_test_structure.py
        language: system
        pass_filenames: false
        stages: [pre-push]

      - id: new-code-has-tests
        name: Check new code has tests
        entry: uv run python -c "
import subprocess
import sys
from pathlib import Path

result = subprocess.run(
    ['git', 'diff', '--cached', '--name-only', '--diff-filter=A'],
    capture_output=True, text=True
)
new_files = [
    f for f in result.stdout.strip().split('\n')
    if f.startswith('src/') and f.endswith('.py') and not f.split('/')[-1].startswith('_')
]

missing = []
for src_file in new_files:
    stem = Path(src_file).stem
    test_patterns = [
        f'tests/unit/test_{stem}.py',
        f'tests/test_{stem}.py',
    ]
    if not any(Path(p).exists() for p in test_patterns):
        missing.append(src_file)

if missing:
    print('New source files without tests:')
    for f in missing:
        print(f'  - {f}')
    print('\\nCreate test files before committing.')
    sys.exit(1)
"
        language: system
        pass_filenames: false
        stages: [pre-commit]
```

---

## conftest.py Additions

Add marker tracking to the project's `tests/conftest.py`:

```python
"""Pytest configuration and shared fixtures."""
from collections import Counter

import pytest

# ============================================================================
# Test Marker Coverage Tracking
# ============================================================================

_marker_counts: Counter[str] = Counter()
_unmarked_tests: list[str] = []

TRACKED_MARKERS = {"unit", "integration", "e2e", "benchmark", "security"}


def pytest_collection_finish(session):
    """Analyze test marker distribution after collection."""
    for item in session.items:
        markers = {m.name for m in item.iter_markers()}
        relevant = markers & TRACKED_MARKERS

        if relevant:
            for marker in relevant:
                _marker_counts[marker] += 1
        else:
            _unmarked_tests.append(item.nodeid)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Report marker coverage in test summary."""
    if not _marker_counts and not _unmarked_tests:
        return

    terminalreporter.write_sep("=", "Test Marker Coverage")

    total = sum(_marker_counts.values()) + len(_unmarked_tests)
    for marker, count in sorted(_marker_counts.items()):
        pct = (count / total) * 100
        terminalreporter.write_line(f"  {marker}: {count} ({pct:.1f}%)")

    if _unmarked_tests:
        pct = len(_unmarked_tests) / total * 100
        terminalreporter.write_line(f"  UNMARKED: {len(_unmarked_tests)} ({pct:.1f}%)")
        if len(_unmarked_tests) <= 10:
            for test in _unmarked_tests:
                terminalreporter.write_line(f"    - {test}")


# ============================================================================
# Existing fixtures below...
# ============================================================================
```

---

## pyproject.toml Additions

Add marker definitions:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: Fast isolated tests with no dependencies",
    "integration: Tests requiring external services",
    "e2e: End-to-end workflow tests",
    "slow: Tests taking more than 5 seconds",
    "benchmark: Performance benchmarking tests",
    "security: Security validation tests",
    "requires_full_dataset: Tests needing large datasets (skip in CI)",
    "real_data: Tests using real fixtures rather than synthetic data",
]
```

---

## tests/fixtures/README.md

```markdown
# Test Fixtures

This directory contains test data and fixtures.

## Organization

| Directory | Purpose | Git Status |
|-----------|---------|------------|
| `small/` | Small fixtures (<1MB) | Committed |
| `expected/` | Expected outputs for snapshot testing | Committed |
| `generated/` | Script-generated data | .gitignored |

## Large Files (>1MB)

For files over 1MB, use Git LFS:

```bash
git lfs track "tests/fixtures/*.parquet"
git lfs track "tests/fixtures/large/*"
```

## Data Generation

If fixtures need to be generated, add scripts to `tests/fixtures/scripts/` and document usage here.
```

---

## Project Type Configurations

The scripts use default ratios suitable for libraries. For different project types, create a `tests/compliance-config.toml`:

```toml
# tests/compliance-config.toml

[ratios]
# Adjust based on project type:
# Library/SDK: unit=0.80, integration=0.15, e2e=0.05
# API Service: unit=0.60, integration=0.30, e2e=0.10
# CLI Tool: unit=0.70, integration=0.20, e2e=0.10
# ML Pipeline: unit=0.50, integration=0.30, e2e=0.20

unit = 0.70
integration = 0.20
e2e = 0.10
tolerance = 0.10

[structure]
required = ["unit", "integration", "fixtures"]
recommended = ["e2e", "security", "benchmark"]

[coverage]
min_line = 80
min_branch = 80
min_module = 80
```

Then update scripts to read from this config file.

---

## Integration Checklist

- [ ] Add scripts to `{{cookiecutter.project_slug}}/scripts/`
- [ ] Add workflow to `{{cookiecutter.project_slug}}/.github/workflows/`
- [ ] Update pre-commit config
- [ ] Add marker tracking to conftest.py template
- [ ] Update pyproject.toml template with markers
- [ ] Create tests/fixtures/ structure with README
- [ ] Add compliance-config.toml with project type options
- [ ] Update cookiecutter prompts to select project type
- [ ] Document in template README

---

## Questions for Cookiecutter Team

1. Should project type selection auto-configure test ratios?
2. Should the weekly audit be a scheduled GitHub Action or manual?
3. Any preference on report output location (`reports/` vs `.reports/`)?
4. Should we add a `make test-audit` or similar Makefile target?

---

*Generated from Claude Code standards development session*
