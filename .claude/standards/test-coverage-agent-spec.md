# Test Coverage Agent — Design Specification

**Project Codename:** Hephaestus-Anvil
**Version:** 1.0-DRAFT
**Author:** Byron (OST Investment Division)
**Date:** 2026-03-14

---

## 1. Executive Summary

This specification defines a Claude Code agent that ensures Python (and secondary JS/TS) projects maintain adequate test coverage through three integrated capabilities: automated coverage gap analysis, AI-powered test generation with iterative validation, and CI/CD threshold enforcement. The agent is built on existing open-source components—CoverUp, pytest-cov, mutmut—orchestrated through Claude Code's skills system, hooks, and subagent architecture rather than developed from scratch.

The design follows a **multi-agent writer/reviewer pattern** validated in production environments (OpenObserve's 380→700+ test growth, Melnik's 30→50% coverage increase) and draws on the CoverUp algorithm's iterative dialog approach, which achieves 80% median coverage versus 47% for single-pass methods.

---

## 2. Goals and Non-Goals

### Goals

1. **Analyze** — Parse coverage.py JSON reports to identify uncovered functions, branches, and files, ranked by business criticality and coverage percentage
2. **Generate** — Produce idiomatic pytest tests targeting specific coverage gaps using an iterative generate→run→fix loop
3. **Enforce** — Block merges when coverage drops below configurable thresholds at project, file, and patch levels
4. **Validate** — Confirm generated test quality via mutation testing (mutmut) and reviewer subagent inspection
5. **Integrate** — Work seamlessly with existing cookiecutter project templates, pre-commit hooks, and GitHub Actions CI/CD pipelines

### Non-Goals

- Replacing human code review for test quality (agent assists, humans approve)
- Supporting languages beyond Python and JS/TS in v1
- Full integration testing or E2E test generation (unit tests only in v1)
- Replacing CoverUp's core algorithm (we orchestrate it, not reimplement it)

---

## 3. Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE HOST SESSION                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              SKILL: test-coverage (orchestrator)           │  │
│  │                                                            │  │
│  │  1. Detect framework (pytest/vitest) from pyproject.toml   │  │
│  │  2. Run coverage measurement                               │  │
│  │  3. Parse JSON → identify gaps                             │  │
│  │  4. Prioritize by criticality × coverage%                  │  │
│  │  5. Dispatch to subagents                                  │  │
│  │  6. Aggregate results → present report                     │  │
│  └────────┬───────────────────────────┬───────────────────────┘  │
│           │                           │                          │
│    ┌──────▼──────────┐    ┌───────────▼──────────┐               │
│    │  SUBAGENT:       │    │  SUBAGENT:            │              │
│    │  test-writer     │◄──►│  test-reviewer        │              │
│    │                  │    │                       │              │
│    │  • Reads source  │    │  • Read-only tools    │              │
│    │  • Writes tests  │    │  • Validates quality  │              │
│    │  • Runs pytest   │    │  • Checks patterns    │              │
│    │  • Iterates on   │    │  • Returns APPROVE    │              │
│    │    failures       │    │    or NEEDS_WORK      │              │
│    │                  │    │  • Flags anti-patterns│              │
│    │  Tools: Read,    │    │  Tools: Read, Grep,  │              │
│    │  Write, Edit,    │    │  Glob, Bash (read-   │              │
│    │  Bash, Grep,     │    │  only commands)      │              │
│    │  Glob            │    │                       │              │
│    └──────────────────┘    └───────────────────────┘              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    HOOKS LAYER                              │  │
│  │                                                            │  │
│  │  PostToolUse (Write|Edit) → pytest -x -q --tb=short       │  │
│  │  Stop → coverage report + threshold check                  │  │
│  │  PreCommit → pytest --cov --cov-fail-under=80             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              MCP SERVER: coverage-tools (optional)          │  │
│  │                                                            │  │
│  │  get_coverage_summary(source_dir) → structured JSON        │  │
│  │  get_uncovered_functions(file) → [{name, lines, pct}]     │  │
│  │  validate_test(test_file) → {passed, coverage_delta}      │  │
│  │  get_mutation_score(module) → {score, survivors}           │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘

                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    CI/CD LAYER (GitHub Actions)                   │
│                                                                  │
│  on: pull_request                                                │
│    1. pytest --cov --cov-report=json --cov-branch               │
│    2. Codecov patch-level check (90% new code)                  │
│    3. If below threshold → claude --bare -p "generate tests for gaps"  │
│    4. Claude opens PR with generated tests                      │
│    5. Weekly: mutmut run on critical modules                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Specifications

### 4.1 Orchestrator Skill: `test-coverage`

**Location:** `.claude/skills/test-coverage/SKILL.md`

````markdown
---
name: test-coverage
description: >
  Analyze test coverage gaps, generate missing tests, and enforce coverage
  thresholds. Supports pytest (Python) and Vitest (JS/TS). Runs coverage
  measurement, identifies uncovered functions ranked by criticality, generates
  idiomatic tests via iterative refinement, and validates quality through
  a reviewer subagent.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Task
---

# Test Coverage Agent

## Invocation Modes

This skill supports three modes based on the arguments provided:

### Mode 1: Analyze (default)
When invoked with no arguments or `analyze`:
1. Auto-detect framework by checking pyproject.toml, pytest.ini, package.json
2. Run `pytest --cov=src --cov-report=json:coverage.json --cov-branch -q`
3. Parse coverage.json using the bundled parser script
4. Identify files below the project threshold (default: 80%)
5. For each under-covered file, identify uncovered functions via AST analysis
6. Rank gaps by: (a) zero-coverage functions first, (b) lowest coverage %,
   (c) most recently modified (git log), (d) highest cyclomatic complexity
7. Present a structured coverage report with actionable recommendations

### Mode 2: Generate
When invoked with `generate` or `generate <file_path>`:
1. Run Mode 1 analysis if no current coverage.json exists
2. For single-file targets, use annotate format for LLM-friendly context:
   `pytest --cov=<source_module> --cov-report=annotate:cov_annotate --cov-branch`
   Lines prefixed with `!` in the annotated output are uncovered.
3. For each target file (or specified file):
   a. Read the source file and any existing test file
   b. Spawn the test-writer subagent with source, uncovered lines, and
      existing test patterns as context
   c. Writer generates tests following project conventions from CLAUDE.md
   d. Run generated tests: `pytest <test_file> --cov=<source> -v`
   e. If tests fail, feed errors back to writer (up to 3 iterations)
   f. Once passing, spawn test-reviewer subagent for quality check
   g. If reviewer returns NEEDS_WORK, send feedback to writer (up to 2 rounds)
   h. If reviewer returns APPROVE, commit the test file
4. Re-run full coverage and present before/after comparison

### Mode 3: Enforce
When invoked with `enforce` or as part of a hook:
1. Run `pytest --cov=src --cov-report=json --cov-branch --cov-fail-under=80`
2. Parse results and check against per-file thresholds if configured
3. Apply quality gates (entry/exit criteria per ISO 25010):
   - Entry: all dependencies installed, database migrations current
   - Exit: coverage thresholds met, no CRITICAL security findings,
     type checking passes, SAST scan clean
4. Report pass/fail status with specific files that need attention
5. Exit with non-zero status if thresholds are not met

### Mode 4: Security Audit
When invoked with `security` or `security <path>`:
1. Run the OWASP dispatcher (see Hephaestus-Aegis spec) to detect
   applicable Top 10 lists based on codebase signals
2. For each applicable specialist, run review-code mode
3. For each applicable specialist, run review-tests mode
4. For CRITICAL/HIGH findings without test coverage, run generate mode
5. Present unified security report with findings by OWASP category

## Configuration

The skill reads thresholds and preferences from pyproject.toml:

```toml
[tool.test-coverage-agent]
default_threshold = 80
patch_threshold = 90        # for new/changed code
critical_modules = ["auth", "payment", "data_processing"]
critical_threshold = 90
exclude_patterns = ["*/migrations/*", "*/conftest.py"]
test_command = "pytest"
max_generation_iterations = 3
max_review_iterations = 2
```

## Output Format

Coverage reports use this structure:
- Project summary: overall line%, branch%, file count
- Files below threshold: sorted worst-first with missing line ranges
- Uncovered functions: name, file, line range, current coverage %
- Recommendations: prioritized list of what to test next
- Before/after comparison (when generating)

$ARGUMENTS
````

**Supporting Scripts:**

```text
.claude/skills/test-coverage/
├── SKILL.md
├── scripts/
│   ├── parse_coverage.py      # Parse coverage.json → structured gap report
│   ├── find_uncovered.py      # AST analysis to identify uncovered functions
│   ├── prioritize_gaps.py     # Rank gaps by criticality × coverage × recency
│   └── compare_coverage.py    # Before/after coverage diff
└── references/
    ├── pytest_conventions.md   # Project-specific test patterns
    └── edge_case_checklist.md  # Systematic edge case identification guide
```

### 4.2 Subagent: test-writer

**Location:** `.claude/agents/test-writer.md`

```markdown
# Test Writer Agent

You are an expert Python test developer. You write idiomatic pytest tests
that target specific uncovered code paths.

## Rules

1. Follow the Arrange-Act-Assert pattern with blank line separators
2. One logical behavior per test function
3. Name tests: test_<function>_<scenario>_<expected_outcome>
4. Use pytest.parametrize for multiple input/output variations
5. Use monkeypatch for simple attribute/env replacement
6. Use mocker (pytest-mock) when you need call assertions or spec enforcement
7. Always use spec=True or autospec=True on mocks
8. Patch where imported, not where defined
9. Use tmp_path for filesystem operations, never hardcoded paths
10. Use freezegun or time-machine for datetime-dependent code
11. Include edge cases: empty inputs, None, boundary values, error paths
12. Keep each test under 20 lines
13. After writing tests, ALWAYS run them to verify they pass
14. If tests fail, read the error output and fix. Iterate up to 3 times.
15. Never write assert True, assert result is not None (unless None is a
    meaningful failure case), or other trivially-passing assertions
16. Prefer testing behavior through public interfaces over private methods

## Context You Receive

- Source file content with uncovered line numbers highlighted
- Existing test file (if any) for pattern matching
- Project test conventions from CLAUDE.md
- Coverage gaps: specific functions and line ranges to target

## Output

- Complete test file or additions to existing test file
- Each test must target specific previously-uncovered lines
- Run results showing all tests pass
```

### 4.3 Subagent: test-reviewer

**Location:** `.claude/agents/test-reviewer.md`

```markdown
# Test Reviewer Agent

You are a senior test quality reviewer. You evaluate AI-generated tests for
correctness, quality, and adherence to best practices. You have READ-ONLY
access and cannot modify code.

## Review Checklist

### Must-Pass (any failure → NEEDS_WORK)
- [ ] Every test has at least one meaningful assertion
- [ ] No trivially-passing assertions (assert True, assert x is not None
      when function never returns None)
- [ ] Tests actually exercise the target function (not just mocks)
- [ ] No tests that mirror implementation logic (testing the mock, not
      the behavior)
- [ ] Tests are deterministic (no unseeded randomness, no real network/time)
- [ ] No shared mutable state between tests

### Should-Pass (flag but don't block)
- [ ] Edge cases covered: empty, None, boundary, error paths
- [ ] Test names describe scenario and expected outcome
- [ ] Arrange-Act-Assert structure is clear
- [ ] Mocking is at the boundary, not internal implementation
- [ ] No over-mocking (>10 lines of mock setup for <3 lines of test)
- [ ] Uses parametrize where appropriate to reduce duplication
- [ ] Tests survive refactoring (test behavior, not implementation)
- [ ] ISTQB techniques applied: BVA at boundaries, EP for input groups
- [ ] Test IDs use standard prefixes (BVA-, EP-, id="descriptive-name")

### Security Coverage (verify when security-relevant code)
- [ ] Auth modules have OWASP specialist tests (owasp-web A01, A07)
- [ ] API endpoints have OWASP API specialist tests
- [ ] LLM integrations have OWASP LLM specialist tests
- [ ] All security tests reference OWASP category IDs in docstrings
- [ ] ASVS requirement IDs cited where applicable (e.g., v5.0.0-2.1.1)

### ISO 25010 Quality Characteristics (flag gaps for critical modules)
- [ ] Functional suitability: completeness and correctness verified
- [ ] Reliability: error recovery and fault tolerance tested
- [ ] Security: confidentiality, integrity, authorization tested
- [ ] Maintainability: tests are modular and independently runnable

## Response Format

Return one of:

APPROVE
- Brief summary of what was tested well
- Any minor suggestions (non-blocking)

NEEDS_WORK
- Specific issues found (reference line numbers)
- Concrete fix suggestions for each issue
- Which checklist items failed
```

### 4.4 Hooks Configuration

**Location:** `.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|MultiEdit|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'if [[ \"$CLAUDE_TOOL_INPUT\" == *\"test_\"* ]] || [[ \"$CLAUDE_TOOL_INPUT\" == *\"/tests/\"* ]]; then pytest -x -q --tb=short 2>&1 | tail -20; fi'"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'if [ -f pyproject.toml ] && grep -q pytest pyproject.toml 2>/dev/null; then echo \"=== Coverage Summary ===\"; pytest --cov=src --cov-report=term-missing --cov-branch -q 2>&1 | tail -30; fi'"
          }
        ]
      }
    ]
  }
}
```

**Hook Behavior:**

| Hook | Trigger | Action | Purpose |
|------|---------|--------|---------|
| PostToolUse | Write/Edit on test files | `pytest -x -q --tb=short` | Immediate feedback on test changes |
| Stop | Claude finishes any task | Coverage summary | Awareness of coverage state |

### 4.5 MCP Server: coverage-tools (Optional Enhancement)

For projects that want structured tool access rather than raw bash parsing:

**Location:** `.mcp.json` at project root

```json
{
  "mcpServers": {
    "coverage-tools": {
      "command": "python",
      "args": ["-m", "coverage_mcp_server"],
      "env": {
        "PROJECT_ROOT": ".",
        "DEFAULT_THRESHOLD": "80"
      }
    }
  }
}
```

**Tools Exposed:**

| Tool | Input | Output |
|------|-------|--------|
| `get_coverage_summary` | `source_dir: str` | Project-wide coverage stats + per-file breakdown |
| `get_uncovered_functions` | `file_path: str` | List of uncovered functions with line ranges, coverage % |
| `validate_test` | `test_file: str, source_file: str` | Pass/fail, coverage delta, new lines covered |
| `get_mutation_score` | `module_path: str` | Mutation score, list of survived mutants |
| `check_thresholds` | `config_path: str` | Pass/fail per threshold rule |

The MCP server wraps deterministic operations (running pytest-cov, parsing JSON, running mutmut) that benefit from consistent execution rather than LLM-interpreted bash output.

---

## 5. Core Algorithm: Coverage-Guided Iterative Generation

The generation loop follows CoverUp's validated approach, adapted for Claude Code's subagent model:

```text
┌─────────────────┐
│  1. MEASURE      │
│  pytest --cov    │──────────────────────────────────────┐
│  --cov-report=   │                                      │
│  json --branch   │                                      │
└────────┬────────┘                                      │
         │                                                │
         ▼                                                │
┌─────────────────┐                                      │
│  2. PARSE & RANK │                                      │
│  coverage.json → │                                      │
│  uncovered       │                                      │
│  functions by    │                                      │
│  priority        │                                      │
└────────┬────────┘                                      │
         │                                                │
         ▼                                                │
┌─────────────────┐     ┌──────────────┐                 │
│  3. GENERATE     │     │  Fail:       │                 │
│  test-writer     │────►│  Feed errors │──┐              │
│  subagent writes │     │  back to     │  │  max 3x      │
│  tests for top   │◄────│  writer      │◄─┘              │
│  priority gaps   │     └──────────────┘                 │
└────────┬────────┘                                      │
         │ pass                                           │
         ▼                                                │
┌─────────────────┐     ┌──────────────┐                 │
│  4. REVIEW       │     │  NEEDS_WORK: │                 │
│  test-reviewer   │────►│  Send fixes  │──┐              │
│  subagent checks │     │  back to     │  │  max 2x      │
│  quality         │◄────│  writer      │◄─┘              │
└────────┬────────┘                                      │
         │ APPROVE                                        │
         ▼                                                │
┌─────────────────┐                                      │
│  5. VALIDATE     │                                      │
│  Full test suite │                                      │
│  (existing +     │                                      │
│  new) passes?    │                                      │
└────────┬────────┘                                      │
         │ yes                                            │
         ▼                                                │
┌─────────────────┐                                      │
│  6. COMMIT       │     More gaps?                       │
│  Stage test file │────────────────────────────────────►─┘
│  Update report   │     yes → loop to step 3
└─────────────────┘     no  → present final report
```

### 5.1 Coverage Parsing Script

```python
#!/usr/bin/env python3
"""parse_coverage.py — Parse coverage.json into structured gap report."""

import json
import ast
import sys
from pathlib import Path
from dataclasses import dataclass


@dataclass
class UncoveredFunction:
    file: str
    name: str
    start_line: int
    end_line: int
    missing_lines: list[int]
    total_lines: int
    coverage_pct: float
    is_critical: bool = False


def parse_coverage(
    coverage_path: str = "coverage.json",
    source_dir: str = "src",
    critical_modules: list[str] | None = None,
    threshold: float = 80.0,
) -> dict:
    """Parse coverage.json and return structured gap analysis."""
    critical_modules = critical_modules or []

    with open(coverage_path) as f:
        data = json.load(f)

    results = {
        "summary": {
            "total_statements": 0,
            "covered_statements": 0,
            "total_branches": 0,
            "covered_branches": 0,
        },
        "files_below_threshold": [],
        "uncovered_functions": [],
    }

    for filepath, file_data in data.get("files", {}).items():
        summary = file_data.get("summary", {})
        line_pct = summary.get("percent_covered", 100)

        results["summary"]["total_statements"] += summary.get("num_statements", 0)
        results["summary"]["covered_statements"] += (
            summary.get("num_statements", 0) - summary.get("missing_lines", 0)
        )

        if line_pct < threshold:
            results["files_below_threshold"].append(
                {
                    "file": filepath,
                    "line_coverage": line_pct,
                    "branch_coverage": summary.get("percent_covered_branches", 0),
                    "missing_lines": file_data.get("missing_lines", []),
                    "missing_branches": file_data.get("missing_branches", []),
                }
            )

        # AST analysis for uncovered functions
        source_path = Path(filepath)
        if source_path.exists():
            missing = set(file_data.get("missing_lines", []))
            try:
                tree = ast.parse(source_path.read_text())
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_lines = set(range(node.lineno, (node.end_lineno or node.lineno) + 1))
                    func_missing = func_lines & missing
                    if func_missing:
                        total = len(func_lines)
                        covered = total - len(func_missing)
                        is_crit = any(m in filepath for m in critical_modules)
                        results["uncovered_functions"].append(
                            UncoveredFunction(
                                file=filepath,
                                name=node.name,
                                start_line=node.lineno,
                                end_line=node.end_lineno or node.lineno,
                                missing_lines=sorted(func_missing),
                                total_lines=total,
                                coverage_pct=round(covered / total * 100, 1),
                                is_critical=is_crit,
                            )
                        )

    # Sort: critical first, then by coverage ascending
    results["uncovered_functions"].sort(
        key=lambda f: (not f.is_critical, f.coverage_pct)
    )
    results["files_below_threshold"].sort(key=lambda f: f["line_coverage"])

    overall_pct = 0
    if results["summary"]["total_statements"]:
        overall_pct = round(
            results["summary"]["covered_statements"]
            / results["summary"]["total_statements"]
            * 100,
            1,
        )
    results["summary"]["overall_coverage"] = overall_pct

    return results


if __name__ == "__main__":
    report = parse_coverage(
        coverage_path=sys.argv[1] if len(sys.argv) > 1 else "coverage.json"
    )
    print(json.dumps(report, indent=2, default=vars))
```

### 5.2 Prompt Template for Test Generation

The test-writer subagent receives this structured context:

````markdown
## Source File: {file_path}

```python
{source_code_with_line_numbers}
```

## Uncovered Lines
Lines {missing_lines} are not covered by existing tests.
Specifically, the function `{function_name}` (lines {start}-{end}) has
{coverage_pct}% coverage with these lines uncovered: {missing_lines}

## Existing Tests
```python
{existing_test_file_content}
```

## Project Test Conventions
{from_claude_md_testing_section}

## Instructions
Write pytest tests targeting the uncovered lines listed above. Follow AAA
pattern, use parametrize for multiple cases, include edge cases (empty,
None, boundary, error paths). Use monkeypatch for simple replacements,
mocker with spec=True for call verification. Run the tests after writing
to confirm they pass.
````

---

## 6. CLAUDE.md Testing Section

This block should be added to every project's CLAUDE.md to configure the agent's behavior:

```markdown
## Testing

### Commands
- Run all tests: `pytest -q --cov=src --cov-branch --cov-report=term-missing`
- Run single file: `pytest tests/path/test_file.py -v`
- Run single test: `pytest tests/path/test_file.py::test_name -v`
- Coverage JSON (for tooling): `pytest --cov=src --cov-report=json:coverage.json --cov-branch`
- Coverage annotated (LLM-friendly): `pytest --cov=src --cov-report=annotate:cov_annotate --cov-branch`
- Mutation testing: `mutmut run --paths-to-mutate=src/module.py`
- Type checking: `uv run basedpyright src/`
- Security scan: `uv run pip-audit`

### Test Writing Rules
- Framework: pytest with pytest-cov, pytest-mock, monkeypatch
- ALL new functions MUST have corresponding tests before marking work complete
- Pattern: Arrange-Act-Assert with blank line separators
- Naming: test_<function>_<scenario>_<expected_outcome>
- Use pytest.parametrize for multiple input/output cases
- Use monkeypatch for attribute/env replacement; mocker (pytest-mock) for
  call verification. Always use spec=True or autospec=True.
- Patch where imported, not where defined
- Each test verifies ONE behavior; keep tests under 20 lines
- MUST include edge cases: empty inputs, None, boundary values, error paths
- Tests must be deterministic: no unseeded randomness, no network calls
- No hardcoded file paths; use tmp_path fixture
- After writing tests, ALWAYS run them to verify they pass
- Never write trivially-passing assertions (assert True, assert x is not None)
- Prefer testing behavior through public interfaces over private methods

### Coverage Thresholds
- Project minimum: 80% line coverage, 70% branch coverage
- Critical modules (auth, data_processing): 90% line coverage
- New code (patch-level): 90% coverage
- Mutation score target (weekly check): >60% on critical modules
```

---

## 7. CI/CD Integration

### 7.1 GitHub Actions Workflow

```yaml
# .github/workflows/test-coverage.yml
name: Test Coverage

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          uv sync --all-extras

      - name: Run tests with coverage
        run: |
          uv run pytest --cov=src --cov-report=json:coverage.json \
                 --cov-report=xml:coverage.xml \
                 --cov-report=term-missing \
                 --cov-branch \
                 --cov-fail-under=80

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

  # Optional: AI-powered test generation for gaps
  generate-tests:
    needs: test
    if: failure()  # only runs when coverage check fails
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            The test coverage check failed. Run pytest --cov=src
            --cov-report=json:coverage.json --cov-branch.
            Parse coverage.json and identify the top 5 files with
            lowest coverage. For each, generate pytest tests targeting
            uncovered functions. Follow the testing conventions in
            CLAUDE.md. Run tests to verify they pass. Commit passing
            tests to a new branch named fix/test-coverage-$(date +%s).

  # Weekly: mutation testing on critical modules
  mutation-testing:
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run mutation testing
        run: |
          uv add --dev mutmut
          uv run mutmut run --paths-to-mutate=src/auth,src/data_processing \
                     --tests-dir=tests/ \
                     --runner="pytest -x -q"
          mutmut results
```

### 7.2 Codecov Configuration

```yaml
# codecov.yml
coverage:
  status:
    project:
      default:
        target: 80%
        threshold: 2%
    patch:
      default:
        target: 90%
  # Per-module overrides
  flags:
    critical:
      paths:
        - src/auth/
        - src/data_processing/
      carryforward: true
      target: 90%
```

### 7.3 Pre-commit Hook

```yaml
# .pre-commit-config.yaml (addition)
repos:
  - repo: local
    hooks:
      - id: pytest-fast
        name: pytest (fast unit tests)
        entry: pytest tests/unit/ -x -q --no-header --tb=line
        language: system
        types: [python]
        pass_filenames: false
        always_run: true
        stages: [pre-commit]

      - id: pytest-coverage
        name: pytest coverage check
        entry: pytest --cov=src --cov-fail-under=80 --cov-branch -q --no-header
        language: system
        types: [python]
        pass_filenames: false
        always_run: true
        stages: [pre-push]
```

---

## 8. pyproject.toml Configuration Block

```toml
# === Testing Configuration ===

[tool.pytest.ini_options]
minversion = "8.0"
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--import-mode=importlib",
]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: integration tests requiring external services",
]
filterwarnings = ["error"]
xfail_strict = true

[tool.coverage.run]
source_pkgs = ["mypackage"]
branch = true

[tool.coverage.report]
show_missing = true
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "@(abc\\.)?abstractmethod",
    "if __name__ == .__main__.:",
    "\\.\\.\\.",           # ellipsis (abstract methods)
]

[tool.coverage.html]
directory = "htmlcov"

[tool.mutmut]
paths_to_mutate = "src/"
tests_dir = "tests/"
runner = "pytest -x -q --tb=no"

# === Test Coverage Agent Configuration ===

[tool.test-coverage-agent]
default_threshold = 80
patch_threshold = 90
critical_modules = ["auth", "data_processing"]
critical_threshold = 90
exclude_patterns = ["*/migrations/*", "*/conftest.py", "*/__main__.py"]
max_generation_iterations = 3
max_review_iterations = 2
```

---

## 9. Directory Structure

```text
project-root/
├── .claude/
│   ├── settings.json              # Hooks configuration
│   ├── skills/
│   │   └── test-coverage/
│   │       ├── SKILL.md           # Orchestrator skill
│   │       ├── scripts/
│   │       │   ├── parse_coverage.py
│   │       │   ├── find_uncovered.py
│   │       │   ├── prioritize_gaps.py
│   │       │   └── compare_coverage.py
│   │       └── references/
│   │           ├── pytest_conventions.md
│   │           └── edge_case_checklist.md
│   └── agents/
│       ├── test-writer.md         # Writer subagent
│       └── test-reviewer.md       # Reviewer subagent
├── .mcp.json                      # MCP server config (optional)
├── CLAUDE.md                      # Project config with testing section
├── pyproject.toml                 # pytest, coverage, mutmut, agent config
├── codecov.yml                    # Codecov thresholds
├── .github/
│   └── workflows/
│       └── test-coverage.yml      # CI/CD workflow
├── src/
│   └── mypackage/
│       └── ...
└── tests/
    ├── conftest.py
    ├── unit/
    │   └── ...
    └── integration/
        └── ...
```

---

## 10. Installation from Existing Components

Rather than building everything from scratch, the agent composes these
existing resources:

| Component | Source | What We Use |
|-----------|--------|-------------|
| Coverage parsing pattern | CoverUp (plasma-umass) | Iterative dialog algorithm, SlipCover-style gap detection |
| Test coverage skill | everything-claude-code `test-coverage.md` | Framework auto-detection, gap prioritization logic |
| TDD enforcement | TDD Guard (nizos/tdd-guard) | PostToolUse hook pattern, pytest reporter format |
| pytest MCP server | mcp-pytest-runner (jwilger) | Structured test execution tool (optional) |
| Writer/Reviewer pattern | Melnik DEV Community article | Two-agent architecture with feedback loop |
| Test quality checklist | claude-plugins.dev testing-anti-patterns | Reviewer checklist items |
| Coverage thresholds | Codecov patch-level config | Graduated enforcement strategy |
| Mutation testing | mutmut (boxed/mutmut) | Weekly quality validation |

### Quick Start

```bash
# 1. Install the skill from skills.sh (test-coverage-analyzer)
npx skills add jeremylongshore/claude-code-plugins-plus-skills \
  --skill test-coverage-analyzer -a claude-code

# 2. Install the pytest MCP server
claude mcp add mcp-pytest-runner -- uvx mcp-pytest-runner

# 3. Install TDD Guard hooks
git clone https://github.com/nizos/tdd-guard.git /tmp/tdd-guard
cp /tmp/tdd-guard/.claude/settings.json .claude/settings.json

# 4. Copy custom subagents from this spec
# (test-writer.md, test-reviewer.md → .claude/agents/)

# 5. Add testing section to CLAUDE.md (see Section 6)

# 6. Add agent config to pyproject.toml (see Section 8)

# 7. Install Python testing dependencies
uv add --dev pytest pytest-cov pytest-mock pytest-randomly pytest-xdist mutmut
```

---

## 11. Quality Metrics and Monitoring

### Coverage Metrics Hierarchy

| Metric | Target | Measurement | Frequency |
|--------|--------|-------------|-----------|
| Line coverage | ≥80% project, ≥90% critical | `pytest --cov` | Every PR |
| Branch coverage | ≥70% project, ≥80% critical | `pytest --cov --cov-branch` | Every PR |
| Patch coverage | ≥90% new/changed code | Codecov patch check | Every PR |
| Mutation score | ≥60% on critical modules | `mutmut run` | Weekly |
| Test reliability | 0 flaky tests | `pytest-randomly` + CI tracking | Continuous |

### Agent Performance Metrics

Track these to evaluate and tune the agent over time:

| Metric | Measurement | Target |
|--------|-------------|--------|
| Generation success rate | Tests that pass on first run ÷ total generated | >70% |
| Iteration efficiency | Tests passing after ≤3 iterations ÷ total | >90% |
| Review approval rate | Tests approved by reviewer on first pass | >60% |
| Coverage delta | Average coverage increase per generation run | >5% per file |
| False coverage | Tests that pass but don't actually test behavior | <10% (measured by mutation testing) |

---

## 12. Rollout Plan

### Phase 1: Foundation (Week 1-2)
- Add CLAUDE.md testing section to all active projects
- Configure pyproject.toml with pytest, coverage, and agent settings
- Install hooks (PostToolUse for test feedback, Stop for coverage summary)
- Install pytest-randomly across all projects to surface hidden dependencies

### Phase 2: Analysis (Week 3-4)
- Deploy the orchestrator skill in analyze-only mode
- Run against all active projects to establish baseline coverage metrics
- Identify critical gaps and prioritize target modules
- Validate parse_coverage.py against real project coverage data

### Phase 3: Generation (Week 5-8)
- Enable the test-writer and test-reviewer subagents
- Run generation against 2-3 pilot projects (low-risk, moderate coverage)
- Human review of all generated tests during pilot
- Tune prompts and reviewer checklist based on pilot results
- Measure generation success rate and iteration efficiency

### Phase 4: Enforcement (Week 9-12)
- Enable CI/CD threshold enforcement (project-level first, then patch-level)
- Deploy Codecov with patch-level thresholds on new code
- Add pre-push coverage check via pre-commit hooks
- Enable weekly mutation testing on critical modules

### Phase 5: Automation (Week 13+)
- Enable Claude Code GitHub Action for auto-generating tests on coverage failures
- Integrate with cookiecutter template so new projects inherit all configuration
- Monitor agent performance metrics and tune thresholds quarterly
- Evaluate MCP server deployment for projects that would benefit from structured tool access

---

## 13. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Generated tests validate bugs (pass on buggy code) | Medium | High | Writer/reviewer separation; mutation testing catches this; human review during pilot |
| Over-mocking produces tests with no real coverage value | Medium | Medium | Reviewer checklist flags >10 lines mock setup; mutation score reveals weak tests |
| Agent generates flaky tests | Low | High | pytest-randomly in CI; determinism rules in writer instructions; reviewer checks |
| Coverage threshold blocks legitimate PRs | Medium | Medium | 2% threshold tolerance in Codecov; per-file overrides for known legacy gaps |
| Token costs escalate with large codebases | Low | Medium | Limit generation to top-5 gaps per run; use Sonnet for writer, Opus for reviewer |

---

## Appendix A: Edge Case Checklist

For reference by the test-writer subagent (`references/edge_case_checklist.md`):

**Input boundaries:**
- Empty string, empty list, empty dict
- None / missing arguments
- Single-element collections
- Maximum/minimum integer values
- Zero (for numeric operations)
- Negative numbers (when only positives expected)
- Unicode, emoji, whitespace-only strings
- Very long strings (>10K characters)

**State boundaries:**
- First call (uninitialized state)
- Repeated identical calls (idempotency)
- Concurrent access (if applicable)
- Resource exhaustion (full disk, OOM)
- Connection failures (timeout, refused)

**Type boundaries:**
- Wrong type passed (str where int expected)
- Subclass of expected type
- Duck-typed objects that match interface

**Error paths:**
- Exception propagation from dependencies
- Partial failure in batch operations
- Cleanup after exception (resource leaks)
- Error message content and type

---

## Appendix B: Key References

### Agent and Skill Sources
- CoverUp: https://github.com/plasma-umass/coverup (coverage-guided generation algorithm)
- everything-claude-code: https://github.com/affaan-m/everything-claude-code (test-coverage command)
- TDD Guard: https://github.com/nizos/tdd-guard (hook-based enforcement)
- mcp-pytest-runner: https://github.com/jwilger/mcp-pytest-runner (MCP server for pytest)
- skills.sh: https://skills.sh (skill registry and CLI)
- awesome-copilot/pytest-coverage: annotate report format pattern
- awesome-copilot/breakdown-test: ISTQB/ISO 25010 test planning framework
- Agent Skills Spec: https://github.com/anthropics/skills (official format specification)
- Claude Code Skills Docs: https://code.claude.com/docs/en/skills
- Claude Code Hooks Docs: https://docs.anthropic.com/en/docs/claude-code/hooks-guide
- Melnik article: https://dev.to/melnikkk/how-we-use-claude-agents-to-automate-test-coverage-3bfa
- OpenObserve case study: https://openobserve.ai/blog/autonomous-qa-testing-ai-agents-claude-code/

### Security Frameworks
- OWASP ASVS 5.0: https://owasp.org/www-project-application-security-verification-standard/
- OWASP WSTG: https://owasp.org/www-project-web-security-testing-guide/
- OWASP Top 10 (2025): https://owasp.org/Top10/2025/
- OWASP LLM Top 10 (2025): https://genai.owasp.org/llm-top-10/
- OWASP Agentic Top 10 (2026): https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- MITRE ATLAS: https://atlas.mitre.org

### Testing Standards
- ISTQB Foundation Level Syllabus v4.0: https://www.istqb.org
- ISO 25010 Quality Model: Software product quality characteristics
- Software Engineering at Google, Chapters 11–14: https://abseil.io/resources/swe-book

### Companion Documents
- TESTING_STANDARDS.md: organizational testing requirements (RFC 2119)
- TESTING_GUIDE.md: detailed patterns, examples, and rationale
- OWASP_SPECIALIST_AGENTS_SPEC.md: Hephaestus-Aegis security agent system
