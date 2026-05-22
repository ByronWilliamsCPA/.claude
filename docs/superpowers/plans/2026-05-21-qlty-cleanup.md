---
schema_type: common
title: qlty Cleanup Implementation Plan
status: draft
owner: engineering
tags: [code_quality, compliance, standards]
purpose: Drive qlty smells from 523 to 5 and duplication from 30.7% to 5% by fixing a qlty.toml misconfiguration (drops 473 submodule false-positives) then refactoring 50 genuine own-code smells across 7 PRs, with no qlty-ignore escape hatches.
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive `qlty smells --all` from 523 to ≤5 and duplication from 30.7% to ≤5% by fixing a qlty.toml misconfiguration (drops 473 submodule false-positives) then refactoring 50 genuine own-code smells across 7 follow-on PRs, with no `qlty-ignore` escape hatches anywhere.

**Architecture:** Phase 1 fixes `.qlty/qlty.toml`: three config keys are silently ignored because they live under `[plugins]` instead of top-level/`[plugins.enabled]`, causing qlty to scan every file under `.submodules/`. Phase 2 refactors the ~50 real smells using four established patterns (dispatch table, early-return/extract-method, shared helper extraction, guard-clause consolidation), with test-first commits for each high-risk PR.

**Tech Stack:** Python 3.10+, qlty CLI, pytest (`pythonpath = [".", "src"]` set in pyproject.toml; no PYTHONPATH prefix needed), pre-commit

---

## Sequencing Rules

- PR 1 (Phase 1 config fix) **must merge first**. All qlty delta checks are meaningless until the submodule false-positives are gone.
- PRs 2A, 2B, 2F, 2G can be worked in parallel and in any order.
- PRs 2C, 2D, 2E are **serialized** with 48-hour soak windows between merges. Do not start 2D until 48 hours after 2C merges; same between 2D and 2E.
- Each PR ends with a qlty verification step confirming the predicted smell count decrease.

---

## PR 1: Fix .qlty/qlty.toml Configuration

### Task 1: Move qlty.toml keys to their correct sections

**Files:**
- Modify: `.qlty/qlty.toml`

- [ ] **Step 1: Understand what is broken**

  In the current file, `exclude_patterns`, `test_patterns`, and `enabled` all live under `[plugins]`. qlty only accepts `exclude_patterns` and `test_patterns` as **top-level** keys and `enabled` as a `[plugins.enabled]` **table** (not a flat list). qlty prints three warnings on every run and silently ignores all three, meaning every `.submodules/` file is analyzed. This is why qlty reports 523 smells when only ~50 are real.

- [ ] **Step 2: Apply the corrected configuration**

  Replace the `[plugins]` section (lines 7-37 in the current file) with:

  ```toml
  # File patterns to completely exclude from all analysis
  exclude_patterns = [
      "*.log",
      "**/__pycache__/**",
      "**/*.pyc",
      "**/*.pyo",
      "**/.pytest_cache/**",
      "**/.mypy_cache/**",
      "**/.ruff_cache/**",
      "**/node_modules/**",
      "**/.venv/**",
      "**/venv/**",
      "**/build/**",
      "**/dist/**",
      "**/*.egg-info/**",
      "**/data/**",
      "**/models/**",
      "**/.git/**",
      "**/.submodules/**",
      "**/.nox/**",
  ]

  # Patterns to identify test files for enhanced analysis
  test_patterns = [
      "**/tests/**",
      "**/test_*.py",
      "**/*_test.py",
  ]

  [plugins.enabled]
  ruff = "latest"
  basedpyright = "latest"
  bandit = "latest"
  ```

  Remove the now-redundant comment block that preceded `[plugins]`.

- [ ] **Step 3: Validate the configuration**

  ```bash
  qlty config validate
  ```

  Expected: exits 0 with **no warnings** about `plugins.exclude_patterns`, `plugins.enabled`, or `plugins.test_patterns`. If warnings appear, the key placement is still wrong.

- [ ] **Step 4: Verify smell count drops from 523 to ~50**

  ```bash
  qlty smells --all | wc -l
  ```

  Expected: approximately 50-60 lines (each line is one smell plus a header). If still in the hundreds, `.submodules/` is still being scanned.

- [ ] **Step 5: Verify submodule files are excluded**

  ```bash
  qlty smells --all | grep -E "^\.submodules" | wc -l
  ```

  Expected: `0`.

- [ ] **Step 6: Verify duplication drops**

  ```bash
  qlty metrics --all | grep -i duplicat
  ```

  Expected: percentage in single digits (from 30.7%).

- [ ] **Step 7: Run pre-commit and commit**

  ```bash
  pre-commit run --all-files
  git add .qlty/qlty.toml
  git commit -m "fix(qlty): move exclude_patterns/test_patterns to top level, enabled to [plugins.enabled]

  Keys under [plugins] were silently ignored, causing all .submodules/ files
  to be analyzed. Moves the three keys to their correct qlty.toml locations;
  drops smell count from 523 to ~50 and duplication from 30.7% to single digits.

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
  ```

- [ ] **Step 8: Update the submodule isolation memory note**

  Append one line to `~/.claude/projects/-home-byron-dev--claude/memory/feedback_submodule_isolation.md`:

  > "2026-05-21: qlty.toml now actively enforces the submodule isolation policy via top-level exclude_patterns; previously the patterns were silently ignored because they lived under [plugins]."

  This records that the policy moved from "agreed convention" to "config-enforced", which affects how future qlty results should be interpreted.

---

## PR 2A: Test Fixture Extraction

**Target smells:** ~7 duplication blocks (mass 67-148) across 4 test files.

### Task 2: Extract shared compliance log entry fixture to conftest.py

The `entry` dict literal in `tests/integration/test_compliance_log_append.py` (lines 30-53) is a 24-line duplicate of the `sample_entry` fixture in `tests/unit/test_compliance_log_common.py` (lines 14-39). Both have mass=148. Moving `sample_entry` to `tests/conftest.py` makes it available to both via pytest's automatic fixture discovery.

**Files:**
- Modify: `tests/conftest.py` (add `compliance_entry` fixture)
- Modify: `tests/integration/test_compliance_log_append.py` (use fixture, remove inline dict)
- Modify: `tests/unit/test_compliance_log_common.py` (use conftest fixture, remove local one)

- [ ] **Step 1: Confirm the duplication is byte-identical in structure**

  ```bash
  # The two blocks should have the same keys and schema_version
  grep -n "schema_version\|session_date\|session_id\|superseded_by" \
    tests/integration/test_compliance_log_append.py \
    tests/unit/test_compliance_log_common.py
  ```

  You should see the same 16-key structure in both files. The values differ slightly (different dates/repos), but the shape is identical.

- [ ] **Step 2: Add a `compliance_entry` fixture to tests/conftest.py**

  Open `tests/conftest.py` and add this fixture at the bottom (before the last line if the file has content):

  ```python
  @pytest.fixture
  def compliance_entry() -> dict:
      """Minimal valid compliance log entry for unit and integration tests.

      Keys match the schema enforced by scripts.compliance_log_common.validate_entry.
      Tests that need a different repo, date, or totals should override specific
      keys rather than duplicating this fixture.
      """
      return {
          "schema_version": 1,
          "session_date": "2026-05-16",
          "session_id": "2026-05-16T19:42:11Z-fdc2",
          "repo": "ByronWilliamsCPA/llc-manager",
          "repo_path": "/home/byron/dev/llc-manager",
          "audit_mode": "interactive",
          "repo_type": "python-app",
          "visibility": "public",
          "reconciled": False,
          "totals": {
              "critical": 0,
              "important": 3,
              "suggested": 7,
              "unclassified_candidates": 2,
              "overrides_applied": 1,
          },
          "findings_by_check": [],
          "unclassified_candidates": [],
          "fleet_action_proposals": [],
          "scope_expansion_flags": [],
          "links": {},
          "superseded_by": None,
      }
  ```

  If `pytest` is not already imported at the top of conftest.py, add `import pytest`.

- [ ] **Step 3: Update test_compliance_log_common.py to use conftest fixture**

  In `tests/unit/test_compliance_log_common.py`, delete the local `sample_entry` fixture (lines 14-39) and replace any test that accepted `sample_entry` as a parameter with `compliance_entry`. The function signatures change from `def test_...(sample_entry)` to `def test_...(compliance_entry)`, and `sample_entry` references in the test body become `compliance_entry`.

  Example (find all occurrences with `grep -n "sample_entry" tests/unit/test_compliance_log_common.py` and update each):

  ```python
  # Before
  def test_make_dedupe_key_returns_tuple(sample_entry: dict) -> None:
      from scripts.compliance_log_common import make_dedupe_key
      key = make_dedupe_key(sample_entry)
      assert key == ("2026-05-16", "ByronWilliamsCPA/llc-manager")

  # After
  def test_make_dedupe_key_returns_tuple(compliance_entry: dict) -> None:
      from scripts.compliance_log_common import make_dedupe_key
      key = make_dedupe_key(compliance_entry)
      assert key == ("2026-05-16", "ByronWilliamsCPA/llc-manager")
  ```

- [ ] **Step 4: Update test_compliance_log_append.py to use conftest fixture**

  In `tests/integration/test_compliance_log_append.py`, find the inline `entry` dict (lines 30-53) and replace it with the fixture. The test function needs `compliance_entry: dict` as a parameter:

  ```python
  # Before: test function builds its own dict
  def test_append_helper_writes_to_central_log_regardless_of_cwd(
      tmp_path: Path,
      monkeypatch: pytest.MonkeyPatch,
  ) -> None:
      foreign_cwd = tmp_path / "some_other_repo"
      foreign_cwd.mkdir()
      monkeypatch.chdir(foreign_cwd)
      entry = {
          "schema_version": 1,
          "session_date": "2026-05-17",
          # ... 20 more lines
      }

  # After: fixture supplies the entry; override only the fields that matter
  def test_append_helper_writes_to_central_log_regardless_of_cwd(
      tmp_path: Path,
      monkeypatch: pytest.MonkeyPatch,
      compliance_entry: dict,
  ) -> None:
      foreign_cwd = tmp_path / "some_other_repo"
      foreign_cwd.mkdir()
      monkeypatch.chdir(foreign_cwd)
      entry = {**compliance_entry, "session_date": "2026-05-17", "repo_path": str(foreign_cwd)}
  ```

- [ ] **Step 5: Run tests to verify nothing broke**

  ```bash
  pytest tests/unit/test_compliance_log_common.py \
         tests/integration/test_compliance_log_append.py -v
  ```

  Expected: all tests PASS. If a test fails because a key is missing, check that the `compliance_entry` fixture includes all required keys (see `scripts/compliance_log_common.REQUIRED_KEYS`).

- [ ] **Step 6: Verify the duplication blocks are gone**

  ```bash
  qlty smells --all | grep -E "test_compliance_log"
  ```

  Expected: 0 lines (no duplication smells in these two files anymore).

- [ ] **Step 7: Run pre-commit and commit**

  ```bash
  pre-commit run --all-files
  git add tests/conftest.py \
          tests/unit/test_compliance_log_common.py \
          tests/integration/test_compliance_log_append.py
  git commit -m "refactor(tests): extract compliance_entry to shared conftest fixture

  Eliminates mass=148 duplication between integration and unit test files
  by moving the shared entry shape to tests/conftest.py where pytest
  discovers it automatically.

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
  ```

### Task 3: Extract shared importlib loader and collapse remaining test duplication

`tests/unit/_load_check_repo_compliance.py` and `tests/unit/_load_populate_github_repos.py` are 41-line files that differ only in their script path and module name string; qlty flags them as mass=142 duplicates. Extract the shared boilerplate to a helper, then refactor any remaining mass-67 and mass-74 duplication blocks inside `tests/unit/test_apply_williaby_repo_rulesets.py`.

**Files:**
- Create: `tests/unit/_importlib_loader.py`
- Modify: `tests/unit/_load_check_repo_compliance.py`
- Modify: `tests/unit/_load_populate_github_repos.py`
- Modify: `tests/unit/test_apply_williaby_repo_rulesets.py`

- [ ] **Step 1: Create the shared loader helper**

  Create `tests/unit/_importlib_loader.py`:

  ```python
  """Shared importlib.util loader for scripts with hyphenated filenames.

  Scripts whose filenames contain hyphens cannot be imported via the normal
  import machinery because hyphens are not valid in Python identifiers.
  This module centralises the spec-from-file-location boilerplate so each
  _load_*.py helper is a one-liner.
  """

  from __future__ import annotations

  import functools
  import importlib.abc
  import importlib.util
  import sys
  from pathlib import Path
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from types import ModuleType

  _PROJECT_ROOT = Path(__file__).resolve().parents[2]


  @functools.cache
  def load_script(script_name: str, module_name: str) -> ModuleType:
      """Load a hyphenated script file as a Python module.

      Args:
          script_name: Filename under scripts/, e.g. "check-repo-compliance.py".
          module_name: Identifier to register in sys.modules, e.g.
              "check_repo_compliance". Must be a valid Python identifier.

      Returns:
          The loaded module object, cached after first load.
      """
      script_path = _PROJECT_ROOT / "scripts" / script_name
      spec = importlib.util.spec_from_file_location(module_name, script_path)
      assert spec is not None, f"Script not found: {script_path}"
      module = importlib.util.module_from_spec(spec)
      sys.modules[module_name] = module
      assert isinstance(spec.loader, importlib.abc.Loader)
      spec.loader.exec_module(module)
      return module
  ```

- [ ] **Step 2: Collapse _load_check_repo_compliance.py to a thin wrapper**

  Replace the entire content of `tests/unit/_load_check_repo_compliance.py` with:

  ```python
  """Load scripts/check-repo-compliance.py as a Python module."""

  from __future__ import annotations

  from typing import TYPE_CHECKING

  from tests.unit._importlib_loader import load_script

  if TYPE_CHECKING:
      from types import ModuleType


  def load_module() -> ModuleType:
      return load_script("check-repo-compliance.py", "check_repo_compliance")
  ```

- [ ] **Step 3: Collapse _load_populate_github_repos.py to a thin wrapper**

  Replace the entire content of `tests/unit/_load_populate_github_repos.py` with:

  ```python
  """Load scripts/populate-github-repos.py as a Python module."""

  from __future__ import annotations

  from typing import TYPE_CHECKING

  from tests.unit._importlib_loader import load_script

  if TYPE_CHECKING:
      from types import ModuleType


  def load_module() -> ModuleType:
      return load_script("populate-github-repos.py", "populate_github_repos")
  ```

- [ ] **Step 4: Find and extract duplicated setup blocks in test_apply_williaby_repo_rulesets.py**

  ```bash
  qlty smells --all | grep test_apply_williaby
  ```

  For each mass-67 and mass-74 duplication pair reported, identify the repeated block, move it to a pytest fixture or a `conftest.py` helper, and replace both occurrences. The pattern will be repeated dict literals (ruleset body shapes) or repeated `gh api` mock setups. Apply Pattern C: extract to a parameterized fixture or a module-level constant.

  Example pattern: if two tests both define the same ruleset body shape inline, extract it:

  ```python
  # In tests/unit/test_apply_williaby_repo_rulesets.py, before any test class
  _BRANCH_RULESET_BODY: dict = {
      "name": "Branch Protection",
      "target": "branch",
      "enforcement": "active",
      "rules": [{"type": "required_signatures"}],
      "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  }

  # Tests then reference _BRANCH_RULESET_BODY instead of repeating the dict
  ```

- [ ] **Step 5: Run the full test suite**

  ```bash
  pytest tests/unit/ -v --tb=short
  ```

  Expected: all tests PASS. If `functools.cache` collides across test runs due to module re-use, switch to `functools.lru_cache(maxsize=None)` (identical behavior, clearer intent for shared state).

- [ ] **Step 6: Verify duplication smells are gone for these files**

  ```bash
  qlty smells --all | grep -E "_load_|test_apply_williaby"
  ```

  Expected: 0 lines.

- [ ] **Step 7: Run pre-commit and commit**

  ```bash
  pre-commit run --all-files
  git add tests/unit/_importlib_loader.py \
          tests/unit/_load_check_repo_compliance.py \
          tests/unit/_load_populate_github_repos.py \
          tests/unit/test_apply_williaby_repo_rulesets.py
  git commit -m "refactor(tests): extract shared importlib loader, collapse test duplication

  Creates tests/unit/_importlib_loader.py so each _load_*.py file is a
  3-line wrapper rather than 41 lines of identical boilerplate. Also
  extracts repeated ruleset body shapes in test_apply_williaby_repo_rulesets.py
  to module-level constants.

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
  ```

---

## PR 2B: Planning + Coverage Skill Refactors

**Target smells:** 5 complexity, 2 nesting, 2 duplication blocks (110-mass twins in validate-planning-docs.py).

### Task 4: Extract _validate_doc helper from twin validators

`validate_tech_spec` and `validate_roadmap` in `.claude/skills/project-planning/scripts/validate-planning-docs.py` are structurally identical: both call `count_words`, `check_required_sections`, `check_tldr`, `check_placeholders` with only the `max_words` and `required_sections` differing. qlty flags them as 110-mass duplicates.

**Files:**
- Modify: `.claude/skills/project-planning/scripts/validate-planning-docs.py`

- [ ] **Step 1: Write a failing test for the extracted helper**

  Create `tests/unit/test_validate_planning_docs.py` (if it does not already exist):

  ```python
  """Tests for validate-planning-docs.py skill script."""

  from __future__ import annotations

  import sys
  from pathlib import Path

  import pytest

  _SCRIPT = Path(__file__).resolve().parents[2] / ".claude" / "skills" / \
            "project-planning" / "scripts" / "validate-planning-docs.py"


  def _load() -> object:
      import importlib.util
      spec = importlib.util.spec_from_file_location("validate_planning_docs", _SCRIPT)
      assert spec is not None
      mod = importlib.util.module_from_spec(spec)
      assert isinstance(spec.loader, __import__("importlib.abc", fromlist=["Loader"]).Loader)
      spec.loader.exec_module(mod)
      return mod


  def test_validate_doc_helper_exists() -> None:
      mod = _load()
      assert hasattr(mod, "_validate_doc"), "_validate_doc helper not found"


  def test_validate_doc_word_count_issue() -> None:
      mod = _load()
      content = " ".join(["word"] * 2001)
      issues = mod._validate_doc(
          content, Path("fake.md"),
          name="test_doc",
          max_words=2000,
          required_sections=["Architecture"],
      )
      assert any("Too long" in i for i in issues)


  def test_validate_doc_no_issues_for_compliant_content() -> None:
      mod = _load()
      content = "## Architecture\n\n## TL;DR\n\n" + " ".join(["word"] * 100)
      issues = mod._validate_doc(
          content, Path("fake.md"),
          name="test_doc",
          max_words=2000,
          required_sections=["Architecture"],
      )
      assert issues == []
  ```

- [ ] **Step 2: Run the test to verify it fails**

  ```bash
  pytest tests/unit/test_validate_planning_docs.py::test_validate_doc_helper_exists -v
  ```

  Expected: FAIL with `AssertionError: _validate_doc helper not found`.

- [ ] **Step 3: Extract _validate_doc and update the twin functions**

  In `.claude/skills/project-planning/scripts/validate-planning-docs.py`, add this function immediately before `validate_tech_spec` (currently around line 116):

  ```python
  def _validate_doc(
      content: str,
      filepath: Path,
      *,
      name: str,
      max_words: int,
      required_sections: list[str],
  ) -> list[str]:
      """Shared validator for any planning doc with a word-count cap and required sections."""
      issues: list[str] = []
      word_count = count_words(content)
      if word_count > max_words:
          issues.append(f"{filepath}: Too long ({word_count} words, max {max_words})")
      issues.extend(check_required_sections(content, filepath, required_sections))
      issues.extend(check_tldr(content, filepath))
      issues.extend(check_placeholders(content, filepath))
      return issues
  ```

  Then replace `validate_tech_spec` and `validate_roadmap` bodies:

  ```python
  def validate_tech_spec(content: str, filepath: Path) -> list[str]:
      """Validate Technical Specification document."""
      return _validate_doc(
          content, filepath,
          name="tech_spec",
          max_words=2000,
          required_sections=["Technology Stack", "Architecture", "Data Model"],
      )


  def validate_roadmap(content: str, filepath: Path) -> list[str]:
      """Validate Development Roadmap document."""
      return _validate_doc(
          content, filepath,
          name="roadmap",
          max_words=1500,
          required_sections=["Timeline", "Phase", "Milestone"],
      )
  ```

- [ ] **Step 4: Run all three tests**

  ```bash
  pytest tests/unit/test_validate_planning_docs.py -v
  ```

  Expected: all 3 PASS.

- [ ] **Step 5: Verify duplication smells gone for this file**

  ```bash
  qlty smells --all | grep validate-planning-docs
  ```

  Expected: 0 duplication smells. Complexity smells for `main` (cc=24) are addressed in the next step.

### Task 5: Decompose parse_coverage and validate_email

**Files:**
- Modify: `.claude/skills/test-coverage/scripts/parse_coverage.py`
- Modify: `.claude/skills/testing/evals/files/validators.py`

- [ ] **Step 1: Fix validate_email many-returns (Pattern D)**

  `validate_email` in `.claude/skills/testing/evals/files/validators.py` has 5+ return statements. Read it first:

  ```bash
  cat .claude/skills/testing/evals/files/validators.py
  ```

  Apply Pattern D: collapse guard clauses for invalid input, end with a single computed return. The typical many-returns pattern for an email validator:

  ```python
  # Before (many returns):
  def validate_email(address: str) -> bool:
      if not address:
          return False
      if "@" not in address:
          return False
      parts = address.split("@")
      if len(parts) != 2:
          return False
      local, domain = parts
      if not local:
          return False
      if "." not in domain:
          return False
      return True

  # After (guard clauses + single computed return):
  def validate_email(address: str) -> bool:
      if not address or "@" not in address:
          return False
      local, domain = address.split("@", 1)
      return bool(local) and "." in domain
  ```

  Read the actual function, then apply this pattern to whatever the real body is.

- [ ] **Step 2: Identify and reduce complexity in parse_coverage**

  `parse_coverage` in `.claude/skills/test-coverage/scripts/parse_coverage.py` has cc=23 and a deep-nesting smell. Apply Pattern B (early-return + extract-method):

  ```bash
  cat .claude/skills/test-coverage/scripts/parse_coverage.py
  ```

  Find the deepest nesting level (the innermost for/if blocks). Extract the inner block into a named helper. Example structure:

  ```python
  # Before: three levels of nesting inside parse_coverage
  def parse_coverage(coverage_path, _source_dir, critical_modules, threshold):
      ...
      for file_path, data in coverage_data.items():
          if file_path in excluded:
              continue
          for line_no, hits in data["executed_lines"].items():
              if hits == 0:
                  ...append uncovered function...

  # After: inner block extracted
  def _uncovered_lines(file_path: str, data: dict, threshold: int) -> list[UncoveredFunction]:
      """Return uncovered functions from a single file's coverage data."""
      result = []
      for line_no, hits in data.get("executed_lines", {}).items():
          if hits == 0:
              result.append(UncoveredFunction(file=file_path, line=int(line_no)))
      return result

  def parse_coverage(coverage_path, _source_dir, critical_modules, threshold):
      ...
      for file_path, data in coverage_data.items():
          if file_path in excluded:
              continue
          uncovered.extend(_uncovered_lines(file_path, data, threshold))
  ```

  The actual code may differ; read it and apply this pattern to whatever the deepest nesting is.

- [ ] **Step 3: Run pre-commit and the full test suite**

  ```bash
  pytest tests/ -v --tb=short
  pre-commit run --all-files
  ```

  Expected: all PASS.

- [ ] **Step 4: Verify smell counts reduced**

  ```bash
  qlty smells --all | grep -E "validators\.py|parse_coverage\.py"
  ```

  Expected: 0 smells for these two files.

- [ ] **Step 5: Commit**

  ```bash
  git add .claude/skills/project-planning/scripts/validate-planning-docs.py \
          .claude/skills/test-coverage/scripts/parse_coverage.py \
          .claude/skills/testing/evals/files/validators.py \
          tests/unit/test_validate_planning_docs.py
  git commit -m "refactor(skills): extract _validate_doc helper, reduce parse_coverage nesting

  Collapses validate_tech_spec + validate_roadmap 110-mass duplication into
  a shared _validate_doc helper. Flattens parse_coverage nesting via
  _uncovered_lines extractor. Reduces validate_email to guard+single-return.

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
  ```

---

## PR 2C: FIPS AST Walker Refactor (High Risk, 48h Soak)

**Target smells:** cc=51 `visit_Call`, cc=20 `main`, cc=14 `check_pyproject_toml`, 3 nesting, 2 duplication.
**Two-commit rule:** Commit 1 adds tests against the unrefactored code. Commit 2 does the refactor. If commit-2 tests fail, the refactor is wrong.

### Task 6: Build FIPS AST test suite (Commit 1 of 2C)

`scripts/check_fips_compatibility.py` has **no test coverage**. This commit builds a fixture-based test suite before any refactoring touches the script.

**Files:**
- Create: `tests/unit/test_check_fips_compatibility.py`
- Create: `tests/fixtures/fips/` (directory of sample Python files)

- [ ] **Step 1: Create sample Python fixture files for known-good and known-bad patterns**

  ```bash
  mkdir -p tests/fixtures/fips
  ```

  Create `tests/fixtures/fips/bad_hashlib.py`:

  ```python
  """Sample file with FIPS-incompatible hashlib usage."""
  import hashlib

  def compute(data: bytes) -> str:
      # md5 without usedforsecurity=False -- should be flagged
      return hashlib.md5(data).hexdigest()
  ```

  Create `tests/fixtures/fips/good_hashlib.py`:

  ```python
  """Sample file with FIPS-safe hashlib usage (usedforsecurity=False)."""
  import hashlib

  def compute(data: bytes) -> str:
      return hashlib.md5(data, usedforsecurity=False).hexdigest()
  ```

  Create `tests/fixtures/fips/bad_sha1.py`:

  ```python
  """Sample file with SHA-1 usage."""
  import hashlib

  def digest(data: bytes) -> str:
      return hashlib.sha1(data).hexdigest()
  ```

  Create `tests/fixtures/fips/clean.py`:

  ```python
  """Sample file with no FIPS issues."""

  def add(a: int, b: int) -> int:
      return a + b
  ```

  Create `tests/fixtures/fips/bad_new_call.py`:

  ```python
  """Sample file using .new() with a non-FIPS algorithm name."""
  import hashlib

  def digest(data: bytes) -> str:
      h = hashlib.new("md5", data)
      return h.hexdigest()
  ```

- [ ] **Step 2: Write the test file**

  Create `tests/unit/test_check_fips_compatibility.py`:

  ```python
  """Tests for scripts/check_fips_compatibility.py."""

  from __future__ import annotations

  from pathlib import Path

  import pytest

  _FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fips"


  @pytest.fixture(scope="module")
  def fips_module():
      """Import check_fips_compatibility as a module."""
      from scripts import check_fips_compatibility
      return check_fips_compatibility


  def test_bad_hashlib_md5_flagged(fips_module) -> None:
      issues = fips_module.check_python_file(_FIXTURES / "bad_hashlib.py")
      assert any(
          "md5" in i.message.lower() and i.severity == "error"
          for i in issues
      ), f"Expected md5 error, got: {[i.message for i in issues]}"


  def test_good_hashlib_md5_not_flagged(fips_module) -> None:
      issues = fips_module.check_python_file(_FIXTURES / "good_hashlib.py")
      hash_issues = [i for i in issues if "md5" in i.message.lower()]
      assert hash_issues == [], f"usedforsecurity=False should suppress: {hash_issues}"


  def test_sha1_flagged_as_warning(fips_module) -> None:
      issues = fips_module.check_python_file(_FIXTURES / "bad_sha1.py")
      assert any(
          "sha1" in i.message.lower() and i.severity == "warning"
          for i in issues
      ), f"Expected sha1 warning, got: {[i.message for i in issues]}"


  def test_clean_file_has_no_issues(fips_module) -> None:
      issues = fips_module.check_python_file(_FIXTURES / "clean.py")
      assert issues == [], f"Clean file should have no issues, got: {issues}"


  def test_new_call_with_md5_string_flagged(fips_module) -> None:
      issues = fips_module.check_python_file(_FIXTURES / "bad_new_call.py")
      assert any("md5" in i.message.lower() for i in issues), (
          f"Expected md5 finding from .new() call, got: {[i.message for i in issues]}"
      )
  ```

- [ ] **Step 3: Run the tests to verify they pass against unrefactored code**

  ```bash
  pytest tests/unit/test_check_fips_compatibility.py -v
  ```

  Expected: all 5 PASS. If any fail, fix the test fixtures (not the script) until they pass.

- [ ] **Step 4: Commit the test suite only**

  ```bash
  pre-commit run --all-files
  git add tests/unit/test_check_fips_compatibility.py \
          tests/fixtures/fips/
  git commit -m "test(fips): add fixture-based AST walker test suite

  Builds test coverage for check_fips_compatibility.py from scratch.
  Tests run against the unrefactored code to prove they exercise the
  right behavior before the refactor commit follows.

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
  ```

### Task 7: Decompose visit_Call via dispatch table (Commit 2 of 2C)

**Files:**
- Modify: `scripts/check_fips_compatibility.py`

- [ ] **Step 1: Capture a pre-refactor output baseline**

  ```bash
  PYTHONPATH=. python scripts/check_fips_compatibility.py \
    --strict tests/fixtures/fips/ > /tmp/fips-before.txt 2>&1 || true
  cat /tmp/fips-before.txt
  ```

  Save this output. After the refactor, output must be byte-identical (same findings, same order).

- [ ] **Step 2: Extract atomic checker functions from visit_Call**

  In `scripts/check_fips_compatibility.py`, add these helper functions immediately before the `FipsCodeVisitor` class. Each handles exactly one detection case:

  ```python
  def _check_hashlib_attr(node: ast.Call, func_name: str, file_path: Path) -> FipsIssue | None:
      """Check hashlib.<algo>() calls for FIPS compliance."""
      if func_name not in NON_FIPS_HASHES:
          return None
      for keyword in node.keywords:
          if (
              keyword.arg == "usedforsecurity"
              and isinstance(keyword.value, ast.Constant)
              and keyword.value.value is False
          ):
              return None
      severity = "error" if func_name in {"md5", "md4"} else "warning"
      return FipsIssue(
          file_path=file_path,
          line_number=node.lineno,
          severity=severity,
          category="hash",
          message=f"hashlib.{func_name}() is not FIPS-approved",
          fix_hint=(
              f"Add usedforsecurity=False if not used for security: "
              f"hashlib.{func_name}(..., usedforsecurity=False)"
          ),
      )


  def _check_cipher_attr(node: ast.Call, func_name: str, file_path: Path) -> FipsIssue | None:
      """Check non-FIPS cipher attribute calls."""
      if func_name not in NON_FIPS_CIPHERS and not any(
          c in func_name for c in NON_FIPS_CIPHERS
      ):
          return None
      return FipsIssue(
          file_path=file_path,
          line_number=node.lineno,
          severity="error",
          category="cipher",
          message=f"Non-FIPS cipher detected: {func_name}",
          fix_hint="Use AES, ChaCha20-Poly1305, or other FIPS-approved algorithms",
      )


  def _check_new_call(node: ast.Call, file_path: Path) -> list[FipsIssue]:
      """Check .new('md5') style calls."""
      if not (isinstance(node.func, ast.Attribute) and node.func.attr == "new"):
          return []
      issues = []
      for arg in node.args:
          if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
              continue
          algo = arg.value.lower()
          if algo in NON_FIPS_HASHES or algo in NON_FIPS_CIPHERS:
              issues.append(FipsIssue(
                  file_path=file_path,
                  line_number=node.lineno,
                  severity="error",
                  category="cipher" if algo in NON_FIPS_CIPHERS else "hash",
                  message=f"Non-FIPS algorithm: {algo}",
                  fix_hint="Use FIPS-approved algorithms (AES, SHA-256, etc.)",
              ))
      return issues
  ```

- [ ] **Step 3: Replace visit_Call body with dispatch logic**

  Replace the existing `visit_Call` method body (lines 100-169) with:

  ```python
  def visit_Call(self, node: ast.Call) -> None:
      """Visit function calls to detect crypto usage."""
      if isinstance(node.func, ast.Attribute):
          func_name = node.func.attr.lower()
          if (
              isinstance(node.func.value, ast.Name)
              and node.func.value.id == "hashlib"
          ):
              if issue := _check_hashlib_attr(node, func_name, self.file_path):
                  self.issues.append(issue)
          elif issue := _check_cipher_attr(node, func_name, self.file_path):
              self.issues.append(issue)
      self.issues.extend(_check_new_call(node, self.file_path))
      self.generic_visit(node)
  ```

- [ ] **Step 4: Run the test suite against the refactored code**

  ```bash
  pytest tests/unit/test_check_fips_compatibility.py -v
  ```

  Expected: all 5 PASS. If any fail, the refactor changed detection behavior; do not suppress, fix the logic.

- [ ] **Step 5: Verify output is byte-identical to the pre-refactor baseline**

  ```bash
  PYTHONPATH=. python scripts/check_fips_compatibility.py \
    --strict tests/fixtures/fips/ > /tmp/fips-after.txt 2>&1 || true
  diff /tmp/fips-before.txt /tmp/fips-after.txt
  ```

  Expected: no diff output. Any difference means the refactor changed behavior and must be investigated before merging.

- [ ] **Step 6: Check qlty smell count for this file**

  ```bash
  qlty smells --all | grep check_fips_compatibility
  ```

  Expected: 0 or at most 1 residual smell (if `check_pyproject_toml` cc=14 cannot be reduced below the threshold after extract).

- [ ] **Step 7: Run pre-commit and commit**

  ```bash
  pre-commit run --all-files
  git add scripts/check_fips_compatibility.py
  git commit -m "refactor(fips): decompose visit_Call cc=51 into atomic checker helpers

  Extracts _check_hashlib_attr, _check_cipher_attr, _check_new_call from
  the cc=51 visit_Call monolith. Output is byte-identical to pre-refactor
  baseline (verified with diff). No qlty-ignore comments added.

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
  ```

> **48-hour soak:** Do not start PR 2D for at least 48 hours after this merges. Monitor for any FIPS detection regressions in the fleet.

---

## PR 2D: Repo Compliance Refactor (High Risk, 48h Soak)

**Target smells:** cc=36 `check_repo`, cc=34 `_admins_enforced`, cc=32 `main`, 2 nesting, 2 many-returns.
**Two-commit rule applies.**

### Task 8: Add tests for check_repo and _admins_enforced (Commit 1 of 2D)

**Files:**
- Modify: `tests/unit/test_check_repo_compliance.py`

- [ ] **Step 1: Add tests that cover the key branches of check_repo**

  Open `tests/unit/test_check_repo_compliance.py` and append these tests (they use `unittest.mock.patch` to avoid live GitHub calls):

  ```python
  def test_check_repo_marks_exempt_repos_na_for_branch_protection() -> None:
      from unittest.mock import patch, MagicMock
      mod = load_module()
      catalog = {"williaby/homelab-agent-configs": {"branchProtectionExempt": True}}
      with patch.object(mod, "file_exists", return_value=True), \
           patch.object(mod, "_signatures_enforced", return_value=True), \
           patch.object(mod, "_admins_enforced", return_value=True):
          result = mod.check_repo("williaby", "homelab-agent-configs", catalog)
      assert result.bp_4 == "N/A"
      assert result.bp_5 == "N/A"
      assert result.ci_020 == "PASS"


  def test_check_repo_fails_ci020_when_renovate_missing() -> None:
      from unittest.mock import patch
      mod = load_module()
      with patch.object(mod, "file_exists", return_value=False), \
           patch.object(mod, "_signatures_enforced", return_value=False), \
           patch.object(mod, "_admins_enforced", return_value=False):
          result = mod.check_repo("ByronWilliamsCPA", "test-repo", {})
      assert result.ci_020 == "FAIL"


  def test_admins_enforced_returns_false_when_bypass_actor_id_5_present() -> None:
      from unittest.mock import patch
      mod = load_module()
      ruleset_with_bypass = {
          "bypass_actors": [{"actor_type": "RepositoryRole", "actor_id": 5}],
          "rules": [],
      }
      with patch.object(mod, "gh") as mock_gh:
          mock_gh.side_effect = [
              ([{"ruleset_source_type": "Organization", "ruleset_source": "testorg",
                 "ruleset_id": 99, "type": "required_signatures"}], None),
              (ruleset_with_bypass, None),
          ]
          result = mod._admins_enforced("testorg", "testrepo", "main")
      assert result is False


  def test_admins_enforced_returns_true_when_no_bypass() -> None:
      from unittest.mock import patch
      mod = load_module()
      clean_ruleset = {"bypass_actors": [], "rules": []}
      with patch.object(mod, "gh") as mock_gh:
          mock_gh.side_effect = [
              ([{"ruleset_source_type": "Organization", "ruleset_source": "testorg",
                 "ruleset_id": 99, "type": "required_signatures"}], None),
              (clean_ruleset, None),
          ]
          result = mod._admins_enforced("testorg", "testrepo", "main")
      assert result is True
  ```

- [ ] **Step 2: Run the new tests against unrefactored code**

  ```bash
  pytest tests/unit/test_check_repo_compliance.py -v
  ```

  Expected: all PASS. Fix any test that fails before committing.

- [ ] **Step 3: Commit the test additions**

  ```bash
  pre-commit run --all-files
  git add tests/unit/test_check_repo_compliance.py
  git commit -m "test(compliance): add branch coverage for check_repo and _admins_enforced

  Tests run against unrefactored code to prove they exercise the right
  behavior before the refactor commit follows.

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
  ```

### Task 9: Decompose check_repo and _admins_enforced (Commit 2 of 2D)

**Files:**
- Modify: `scripts/check-repo-compliance.py`

- [ ] **Step 1: Capture pre-refactor output baseline**

  ```bash
  # Run against a real repo (dry-run equivalent: just check structure output)
  PYTHONPATH=. python scripts/check-repo-compliance.py --org ByronWilliamsCPA \
    2>/dev/null | head -30 > /tmp/compliance-before.txt || true
  ```

- [ ] **Step 2: Extract API compliance checks from check_repo (Pattern A)**

  `check_repo` has cc=36 because it handles CI-020, CI-021, BP-4, BP-5, and five API checks all in one body. Extract the API section (API-001..005) into a helper:

  ```python
  def _check_api_fields(
      org: str,
      repo: str,
      branch: str,
      api_info: dict,
  ) -> dict[str, str]:
      """Check API-001..005 for a repo with api.servesApi=true.

      Returns a dict of field_name -> "PASS"/"FAIL" for each check.
      """
      results: dict[str, str] = {}
      results["api_001_openapi_spec"] = (
          "PASS" if file_exists(org, repo, "docs/api/openapi.yaml", branch) else "FAIL"
      )
      results["api_002_postman_collection"] = (
          "PASS"
          if file_exists(org, repo, "docs/api/postman-collection.json", branch)
          else "FAIL"
      )
      results["api_003_ci_workflow"] = (
          "PASS"
          if file_exists(org, repo, ".github/workflows/postman-api-tests.yml", branch)
          else "FAIL"
      )
      last_audited = api_info.get("lastAudited")
      if last_audited is None:
          results["api_004_last_audited"] = "FAIL"
      else:
          try:
              audited_date = datetime.date.fromisoformat(last_audited)
              today = datetime.datetime.now(tz=datetime.timezone.utc).date()
              results["api_004_last_audited"] = (
                  "PASS" if (today - audited_date).days <= 90 else "FAIL"
              )
          except ValueError:
              results["api_004_last_audited"] = "FAIL"
      test_status = api_info.get("testStatus")
      results["api_005_test_status"] = (
          "PASS" if test_status == "passing" else "FAIL"
      )
      return results
  ```

  Then replace the API block inside `check_repo` (the `if applies_to_api_repos(...)` block) with:

  ```python
  if applies_to_api_repos(org, repo, catalog):
      api_info = (catalog.get(slug, {}).get("api") or {})
      for field, value in _check_api_fields(org, repo, branch, api_info).items():
          setattr(result, field, value)
  ```

- [ ] **Step 3: Extract the ruleset bypass loop from _admins_enforced (Pattern B)**

  The inner loop over `ruleset_refs` in `_admins_enforced` is the deep-nesting source. Extract it:

  ```python
  def _find_admin_bypass(
      org: str,
      repo: str,
      ruleset_refs: set[tuple[str, str, int]],
  ) -> tuple[bool, bool]:
      """Check each active ruleset for an admin bypass actor.

      Returns:
          (bypass_found, all_fetches_failed) tuple.
          bypass_found=True means at least one ruleset has actor_id=5 bypass.
          all_fetches_failed=True means every fetch errored (fall through to classic).
      """
      fetch_failures = 0
      for rs_type, rs_src, rs_id in ruleset_refs:
          path = (
              f"orgs/{rs_src}/rulesets/{rs_id}"
              if rs_type == "Organization"
              else f"repos/{org}/{repo}/rulesets/{rs_id}"
          )
          body, err = gh(path)
          if err is not None:
              fetch_failures += 1
              print(
                  f"warning: BP-5 ruleset body fetch failed for "
                  f"{org}/{repo} (rs_type={rs_type}, rs_id={rs_id}): {err}",
                  file=sys.stderr,
              )
              continue
          try:
              ruleset = json.loads(body) if isinstance(body, str) else body
          except json.JSONDecodeError:
              continue
          for actor in ruleset.get("bypass_actors", []) or []:
              if (
                  actor.get("actor_type") == "RepositoryRole"
                  and actor.get("actor_id") == 5
              ):
                  return True, False
      return False, fetch_failures == len(ruleset_refs) and bool(ruleset_refs)
  ```

  Then replace the loop inside `_admins_enforced` with:

  ```python
  bypass_found, all_fetches_failed = _find_admin_bypass(org, repo, ruleset_refs)
  if bypass_found:
      return False
  if all_fetches_failed:
      print(
          f"warning: BP-5 all ruleset body fetches failed for "
          f"{org}/{repo}@{branch}; falling back to classic enforce_admins.",
          file=sys.stderr,
      )
  elif ruleset_refs:
      return True
  ```

- [ ] **Step 4: Run the full test suite**

  ```bash
  pytest tests/unit/test_check_repo_compliance.py -v
  ```

  Expected: all PASS including the 4 tests added in Task 8.

- [ ] **Step 5: Verify output is byte-identical**

  ```bash
  PYTHONPATH=. python scripts/check-repo-compliance.py --org ByronWilliamsCPA \
    2>/dev/null | head -30 > /tmp/compliance-after.txt || true
  diff /tmp/compliance-before.txt /tmp/compliance-after.txt
  ```

  Expected: no diff. Any difference requires investigation before merge.

- [ ] **Step 6: Check qlty smell count**

  ```bash
  qlty smells --all | grep check-repo-compliance
  ```

  Expected: 0 or ≤1 residual (if `main` cc=32 lands at 28-32 after the API extraction).

- [ ] **Step 7: Run pre-commit and commit**

  ```bash
  pre-commit run --all-files
  git add scripts/check-repo-compliance.py
  git commit -m "refactor(compliance): extract _check_api_fields and _find_admin_bypass helpers

  Decomposes check_repo (cc=36) and _admins_enforced (cc=34) into targeted
  helpers. Output byte-identical to pre-refactor baseline. No qlty-ignore added.

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
  ```

> **48-hour soak:** Do not start PR 2E for at least 48 hours after this merges.

---

## PR 2E: Compliance Logging + Reconciler Refactor (High Risk, 48h Soak)

**Target smells:** cc=39 `reconcile`, cc=27 `_atomic_supersede_and_append`, cc=16 `_parse_unclassified_candidates`, cc=14 `load_entries`.
**Two-commit rule applies.**

### Task 10: Add tests for the file-locking functions (Commit 1 of 2E)

**Files:**
- Modify: `tests/integration/test_compliance_log_append.py`
- Modify: `tests/unit/test_compliance_rollup_reconcile.py`

- [ ] **Step 1: Add a test for supersede behavior in _atomic_supersede_and_append**

  Append to `tests/integration/test_compliance_log_append.py`:

  ```python
  def test_atomic_supersede_marks_prior_entry_superseded(
      tmp_path: Path,
      compliance_entry: dict,
  ) -> None:
      """Second append for the same (session_date, repo) must supersede the first."""
      from scripts.compliance_log_append import append_entry

      log = tmp_path / "test-log.jsonl"
      first_entry = {**compliance_entry, "session_id": "2026-05-16T10:00:00Z-aaaa"}
      append_entry(first_entry, jsonl_path=log, render=False)

      second_entry = {**compliance_entry, "session_id": "2026-05-16T11:00:00Z-bbbb"}
      append_entry(second_entry, jsonl_path=log, render=False)

      lines = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
      entries = [l for l in lines if l.get("type") != "header"]
      assert len(entries) == 2
      first_written = next(e for e in entries if e["session_id"].endswith("aaaa"))
      assert first_written["superseded_by"] == "2026-05-16T11:00:00Z-bbbb"
      second_written = next(e for e in entries if e["session_id"].endswith("bbbb"))
      assert second_written["superseded_by"] is None
  ```

- [ ] **Step 2: Add a test for reconcile dry-run behavior**

  In `tests/unit/test_compliance_rollup_reconcile.py`, append:

  ```python
  def test_reconcile_dry_run_does_not_write(tmp_path: Path) -> None:
      """dry_run=True should increment appended counter but not touch the JSONL."""
      from scripts.compliance_rollup_reconcile import reconcile
      from scripts.compliance_log_common import SCHEMA_VERSION

      catalog = tmp_path / "catalog.json"
      catalog.write_text('{"repos": []}', encoding="utf-8")
      jsonl = tmp_path / "log.jsonl"

      result = reconcile(catalog_path=catalog, jsonl_path=jsonl, dry_run=True)

      assert result.walked == 0
      assert not jsonl.exists(), "dry_run should not create the JSONL"


  def test_reconcile_skips_archived_repos(tmp_path: Path) -> None:
      """Repos with isArchived=true must be skipped silently."""
      from scripts.compliance_rollup_reconcile import reconcile

      catalog = tmp_path / "catalog.json"
      catalog.write_text(
          '{"repos": [{"name": "old-repo", "org": "testorg", "isArchived": true}]}',
          encoding="utf-8",
      )
      jsonl = tmp_path / "log.jsonl"

      result = reconcile(catalog_path=catalog, jsonl_path=jsonl, dry_run=False)

      assert result.walked == 0
  ```

- [ ] **Step 3: Run all new tests against unrefactored code**

  ```bash
  pytest tests/integration/test_compliance_log_append.py \
         tests/unit/test_compliance_rollup_reconcile.py -v
  ```

  Expected: all PASS.

- [ ] **Step 4: Commit the tests**

  ```bash
  pre-commit run --all-files
  git add tests/integration/test_compliance_log_append.py \
          tests/unit/test_compliance_rollup_reconcile.py
  git commit -m "test(logging): add supersede behavior and reconcile dry-run coverage

  Tests run against unrefactored code to prove they exercise the right
  behavior before the refactor commit follows.

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
  ```

### Task 11: Decompose _atomic_supersede_and_append and reconcile (Commit 2 of 2E)

**Files:**
- Modify: `scripts/compliance_log_append.py`
- Modify: `scripts/compliance_rollup_reconcile.py`

- [ ] **Step 1: Capture pre-refactor output baselines**

  ```bash
  # For reconcile: dry-run against production log
  PYTHONPATH=. python scripts/compliance_rollup_reconcile.py --dry-run \
    2>/dev/null > /tmp/reconcile-before.txt || true
  ```

- [ ] **Step 2: Extract helpers from _atomic_supersede_and_append**

  In `scripts/compliance_log_append.py`, add two helpers immediately before `_atomic_supersede_and_append`:

  ```python
  def _parse_jsonl_lines(
      raw: str,
  ) -> list[tuple[str, dict | None]]:
      """Parse raw JSONL text into (line, parsed_obj_or_None) tuples."""
      result: list[tuple[str, dict | None]] = []
      for line in raw.splitlines(keepends=True):
          if not line.strip():
              result.append((line, None))
              continue
          try:
              result.append((line, json.loads(line)))
          except json.JSONDecodeError:
              result.append((line, None))
      return result


  def _find_supersede_target(
      existing_lines: list[tuple[str, dict | None]],
      key: object,
  ) -> tuple[int | None, str]:
      """Find the index and session_id of the latest active entry matching key."""
      target_idx: int | None = None
      target_session = ""
      for idx, (_, obj) in enumerate(existing_lines):
          if obj is None or obj.get("type") == "header":
              continue
          if make_dedupe_key(obj) != key:
              continue
          if obj.get("superseded_by") is not None:
              continue
          session_id = obj.get("session_id", "")
          if target_idx is None or session_id > target_session:
              target_idx = idx
              target_session = session_id
      return target_idx, target_session


  def _atomic_write(
      jsonl_path: Path,
      lines: list[tuple[str, dict | None]],
      new_entry: dict,
  ) -> None:
      """Write updated lines plus new_entry to jsonl_path via atomic rename."""
      body = "".join(line for line, _ in lines)
      if body and not body.endswith("\n"):
          body += "\n"
      body += json.dumps(new_entry) + "\n"
      fd, tmp_path = tempfile.mkstemp(
          prefix=".master-log.", suffix=".tmp", dir=str(jsonl_path.parent)
      )
      try:
          os.close(fd)
          Path(tmp_path).write_text(body, encoding="utf-8")
          os.replace(tmp_path, jsonl_path)
      except OSError:
          with contextlib.suppress(OSError):
              os.unlink(tmp_path)
          raise
  ```

  Then replace the body of `_atomic_supersede_and_append` with:

  ```python
  def _atomic_supersede_and_append(
      jsonl_path: Path,
      new_entry: dict[str, Any],
  ) -> None:
      """Rewrite the JSONL with optional supersede and the new entry, atomically."""
      key = make_dedupe_key(new_entry)
      new_session_id = new_entry["session_id"]
      if not isinstance(new_session_id, str):
          msg = f"session_id must be str, got {type(new_session_id).__name__}"
          raise TypeError(msg)

      existing_lines = _parse_jsonl_lines(jsonl_path.read_text(encoding="utf-8"))
      target_idx, _ = _find_supersede_target(existing_lines, key)

      if target_idx is not None:
          target_obj = existing_lines[target_idx][1]
          if target_obj is None:
              msg = "internal: target entry resolved to None during supersede"
              raise RuntimeError(msg)
          target_obj["superseded_by"] = new_session_id
          existing_lines[target_idx] = (json.dumps(target_obj) + "\n", target_obj)

      _atomic_write(jsonl_path, existing_lines, new_entry)
  ```

- [ ] **Step 3: Extract per-repo lesson walker from reconcile**

  In `scripts/compliance_rollup_reconcile.py`, add a helper immediately before `reconcile`:

  ```python
  def _process_repo_lessons(
      repo_org: str,
      repo_name: str,
      clone: Path,
      known_keys: set,
      jsonl_path: Path,
      since: str | None,
      dry_run: bool,
      result: ReconcileResult,
  ) -> None:
      """Process all lessons-learned Markdown files for one repo clone."""
      repo_full = f"{repo_org}/{repo_name}"
      lessons_dir = clone / "docs" / "compliance-reports" / "lessons-learned"
      if not lessons_dir.is_dir():
          return
      for md in sorted(lessons_dir.glob("*.md")):
          try:
              parsed = parse_lessons_learned(md, clone)
          except InvalidRetrospectiveError as exc:
              result.parse_failures.append(f"{md}: {exc}")
              continue
          except (OSError, UnicodeDecodeError) as exc:
              result.parse_failures.append(
                  f"{md}: read failed: {type(exc).__name__}: {exc}"
              )
              continue
          if since and parsed["session_date"] < since:
              continue
          key = (parsed["session_date"], repo_full)
          if key in known_keys:
              result.duplicates_skipped += 1
              continue
          entry = _build_entry(repo_full, parsed)
          if not dry_run:
              _append_entry(jsonl_path, entry)
          known_keys.add(key)
          result.appended += 1
  ```

  Then replace the inner body of `reconcile`'s main for-loop with a call to the helper:

  ```python
  for repo in catalog.get("repos", []):
      if repo.get("isArchived"):
          continue
      repo_name = repo.get("name")
      repo_org = repo.get("org")
      if not repo_name or not repo_org:
          result.parse_failures.append(f"catalog entry missing name/org: {repo!r}")
          continue
      result.walked += 1
      clone = resolve_local_clone(repo_name, repos_root)
      if clone is None:
          result.skipped_no_clone += 1
          continue
      result.with_clone += 1
      _process_repo_lessons(
          repo_org, repo_name, clone, known_keys, jsonl_path, since, dry_run, result
      )
  ```

- [ ] **Step 4: Run the full test suite**

  ```bash
  pytest tests/unit/test_compliance_rollup_reconcile.py \
         tests/unit/test_compliance_log_common.py \
         tests/integration/test_compliance_log_append.py -v
  ```

  Expected: all PASS including the 3 tests added in Task 10.

- [ ] **Step 5: Verify reconcile output is byte-identical**

  ```bash
  PYTHONPATH=. python scripts/compliance_rollup_reconcile.py --dry-run \
    2>/dev/null > /tmp/reconcile-after.txt || true
  diff /tmp/reconcile-before.txt /tmp/reconcile-after.txt
  ```

  Expected: no diff.

- [ ] **Step 6: Check qlty smell count**

  ```bash
  qlty smells --all | grep -E "compliance_log_append|compliance_rollup_reconcile"
  ```

  Expected: 0 smells for these two files.

- [ ] **Step 7: Run pre-commit and commit**

  ```bash
  pre-commit run --all-files
  git add scripts/compliance_log_append.py \
          scripts/compliance_rollup_reconcile.py
  git commit -m "refactor(logging): decompose _atomic_supersede_and_append and reconcile

  Extracts _parse_jsonl_lines, _find_supersede_target, _atomic_write from
  the cc=27 _atomic_supersede_and_append. Extracts _process_repo_lessons
  from the cc=39 reconcile. Output byte-identical to pre-refactor baseline.

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
  ```

> **48-hour soak:** Do not run final verification until 48 hours after this merges.

---

## PR 2F: Doc Audit + Supporting Checkers (Medium Risk)

**Target smells:** 9 complexity smells, 2 nesting across `doc-audit.py`, `check_type_hints.py`, `check-required-checks.py`, `populate-github-repos.py`.

### Task 12: Reduce complexity in doc-audit.py and check_type_hints.py

**Files:**
- Modify: `scripts/doc-audit.py`
- Modify: `scripts/check_type_hints.py`

- [ ] **Step 1: Identify the exact smell locations**

  ```bash
  qlty smells --all | grep -E "doc-audit|check_type_hints"
  ```

  Note the function name, line number, and smell type for each finding. This is your work list. Common candidates: `check_frontmatter` (complex frontmatter parsing), `check_versions` (multi-branch version ref logic), `_check_python_version` (nested conditionals).

- [ ] **Step 2: Apply Pattern B (early-return + extract) to each deep-nesting smell**

  For each nesting-level-4 smell, find the innermost block and extract it to a named helper. Example from `check_frontmatter`:

  ```python
  # Before: three levels of nesting inside check_frontmatter
  for md_file in scope.glob("**/*.md"):
      content = md_file.read_text()
      frontmatter = _parse_frontmatter(content)
      if frontmatter:
          for key in required_keys:
              if key not in frontmatter:
                  findings.append(...)

  # After: extract inner check
  def _missing_required_keys(
      frontmatter: dict, required_keys: list[str], filepath: Path
  ) -> list[Finding]:
      return [
          Finding(filepath=filepath, message=f"Missing required key: {key}")
          for key in required_keys
          if key not in frontmatter
      ]

  for md_file in scope.glob("**/*.md"):
      content = md_file.read_text()
      if frontmatter := _parse_frontmatter(content):
          findings.extend(_missing_required_keys(frontmatter, required_keys, md_file))
  ```

- [ ] **Step 3: Apply Pattern A (dispatch) to complexity smells in check_versions**

  If `check_versions` has a long if/elif chain over version-reference types, extract each branch into a named checker and dispatch via a dict:

  ```python
  _VERSION_CHECKERS: dict[str, Callable[[str, Path, int], list[Finding]]] = {
      "python": _check_python_version,
      "model": _check_model_names,
      "schema": _check_schema_version_refs,
  }

  def check_versions(scope: Path, repo_root: Path) -> list[Finding]:
      findings: list[Finding] = []
      for version_type, checker in _VERSION_CHECKERS.items():
          findings.extend(checker(scope, repo_root))
      return findings
  ```

- [ ] **Step 4: Reduce _collect_python_files nesting in check_type_hints.py**

  Find the deep nesting in `check_type_hints.py` (likely in `_collect_python_files` or `_process_files`) and apply Pattern B:

  ```bash
  grep -n "def " scripts/check_type_hints.py
  qlty smells --all | grep check_type_hints
  ```

  Extract the innermost for/if block to a named helper. Pattern:

  ```python
  def _should_include_file(path: Path, args) -> bool:
      """Return True if this Python file should be checked."""
      if path.name.startswith("."):
          return False
      if any(excluded in path.parts for excluded in args.exclude):
          return False
      return True

  def _collect_python_files(args) -> list[Path]:
      return [
          p for p in Path(args.path).rglob("*.py")
          if _should_include_file(p, args)
      ]
  ```

- [ ] **Step 5: Run tests and verify smell count**

  ```bash
  pytest tests/ -v --tb=short
  qlty smells --all | grep -E "doc-audit|check_type_hints"
  ```

  Expected: tests PASS, 0 smells for these files.

### Task 13: Reduce complexity in check-required-checks.py and populate-github-repos.py

**Files:**
- Modify: `scripts/check-required-checks.py`
- Modify: `scripts/populate-github-repos.py`

- [ ] **Step 1: Identify the exact smell locations**

  ```bash
  qlty smells --all | grep -E "check-required-checks|populate-github-repos"
  ```

- [ ] **Step 2: Extract matrix interpolation helpers in check-required-checks.py (Pattern A)**

  The `_expand_matrix_combinations` and `_interpolate_matrix` functions have complex branches for handling different matrix axis types. Extract each case into a named handler:

  ```python
  def _interpolate_single_axis(template: str, key: str, value: str) -> str:
      """Replace all ${{ matrix.KEY }} occurrences in template."""
      import re
      pattern = rf"\${{{{[\s]*matrix\.{re.escape(key)}[\s]*}}}}"
      return re.sub(pattern, value, template)

  def _interpolate_matrix(template: str, combo: dict[str, str]) -> str:
      """Replace all matrix variable references in template."""
      result = template
      for key, value in combo.items():
          result = _interpolate_single_axis(result, key, value)
      return result
  ```

- [ ] **Step 3: Extract catalog write logic in populate-github-repos.py (Pattern B)**

  `refresh_catalog` (cc=19) builds a catalog from live GitHub data. Extract the per-repo processing:

  ```python
  def _build_updated_entry(
      org: str, raw: dict, existing: dict | None
  ) -> dict:
      """Merge a live GitHub API response with an existing catalog entry."""
      live = _normalise_live_entry(org, raw)
      return _merge_entry(existing, live) if existing else live
  ```

- [ ] **Step 4: Run tests and verify smell count**

  ```bash
  pytest tests/unit/test_check_required_checks.py \
         tests/unit/test_populate_github_repos.py -v
  qlty smells --all | grep -E "check-required-checks|populate-github-repos"
  ```

  Expected: tests PASS, 0 smells.

- [ ] **Step 5: Run pre-commit and commit PR 2F**

  ```bash
  pre-commit run --all-files
  git add scripts/doc-audit.py \
          scripts/check_type_hints.py \
          scripts/check-required-checks.py \
          scripts/populate-github-repos.py
  git commit -m "refactor(scripts): reduce complexity in doc-audit, type hints, required checks

  Applies Pattern B (early-return + extract-method) to nesting smells and
  Pattern A (dispatch table) to complexity smells across 4 scripts. No
  qlty-ignore comments added.

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
  ```

---

## PR 2G: Many-Returns Cleanup (Low Risk)

**Target smells:** 4 many-returns smells across 3 files.

### Task 14: Consolidate returns in _should_remind and main() functions

**Files:**
- Modify: `scripts/pr-review-reminder.py`
- Modify: `scripts/setup_org_rulesets.py`
- Modify: `scripts/setup_repo_rulesets.py`

- [ ] **Step 1: Apply Pattern D to _should_remind (pr-review-reminder.py)**

  The current `_should_remind` has 5 return statements (2× False, 1 True for URL, 1 True for phrase, 1 False final). Collapse to 2 via guard clauses:

  Replace the body of `_should_remind` (lines 147-159) with:

  ```python
  def _should_remind(prompt: str) -> bool:
      """Decide whether to inject the reminder for this prompt."""
      if not prompt or EXPLICIT_COMMAND_RE.search(prompt):
          return False
      normalized = _WHITESPACE_RUN.sub(" ", prompt.lower())
      return PR_URL_RE.search(prompt) is not None or any(
          phrase in normalized for phrase in PR_PHRASES
      )
  ```

- [ ] **Step 2: Verify existing tests still pass**

  ```bash
  pytest tests/ -k "pr_review" -v 2>/dev/null || \
  python -c "
  import subprocess, sys
  r = subprocess.run(['python', 'scripts/pr-review-reminder.py'],
    input='{\"user_prompt\": \"review PR 123\"}', text=True, capture_output=True)
  assert r.returncode == 0
  import json; out = json.loads(r.stdout)
  assert 'systemMessage' in out, f'Expected reminder, got: {out}'
  print('PASS: reminder injected for PR mention')
  "
  ```

- [ ] **Step 3: Add exception dispatch table to setup_org_rulesets.py main()**

  `main()` in `setup_org_rulesets.py` has 8 distinct return points across separate `except` blocks. Add a dispatch table before `main()` and collapse the exception handling:

  Add these constants immediately before the `def main(argv)` function:

  ```python
  _POLICY_EXCEPTION_EXIT: dict[type[Exception], int] = {
      SoloDevViolationError: EXIT_SOLO_DEV_VIOLATION,
      TargetRuleMismatchError: EXIT_TARGET_RULE_MISMATCH,
      RulesetDriftError: EXIT_DRIFT_DETECTED,
  }

  _POLICY_EXCEPTION_PREFIX: dict[type[Exception], str] = {
      SoloDevViolationError: "REFUSED",
      TargetRuleMismatchError: "REFUSED",
      RulesetDriftError: "DRIFT",
  }
  ```

  Replace the existing `main()` exception handling with:

  ```python
  def main(argv: list[str]) -> int:
      """CLI entry point."""
      parser = argparse.ArgumentParser()
      parser.add_argument("--org", required=True)
      parser.add_argument("--body", required=True, type=Path)
      parser.add_argument("--enforcement", choices=("active", "evaluate", "disabled"))
      parser.add_argument("--catalog", type=Path, default=CATALOG_DEFAULT)
      parser.add_argument("--dry-run", action="store_true")
      args = parser.parse_args(argv)
      try:
          apply(args.org, args.body, args.enforcement, args.catalog, args.dry_run)
      except (SoloDevViolationError, TargetRuleMismatchError, RulesetDriftError) as exc:
          prefix = _POLICY_EXCEPTION_PREFIX[type(exc)]
          print(f"{prefix}: {exc}", file=sys.stderr)
          return _POLICY_EXCEPTION_EXIT[type(exc)]
      except subprocess.TimeoutExpired as exc:
          print(
              f"gh command timed out after {_GH_TIMEOUT_SECONDS}s: {exc}",
              file=sys.stderr,
          )
          return EXIT_GH_FAILURE
      except json.JSONDecodeError as exc:
          print(f"gh produced unparseable JSON output: {exc}", file=sys.stderr)
          return EXIT_GH_FAILURE
      except FileNotFoundError as exc:
          label = "gh CLI not on PATH" if exc.filename == "gh" else f"body file not found: {exc.filename}"
          print(f"{label}: {exc}", file=sys.stderr)
          return EXIT_GH_FAILURE
      except subprocess.CalledProcessError as exc:
          print(f"gh command failed: {exc}", file=sys.stderr)
          return EXIT_GH_FAILURE
      return EXIT_OK
  ```

- [ ] **Step 4: Apply the same pattern to setup_repo_rulesets.py main()**

  `main()` in `setup_repo_rulesets.py` has 5 return paths. Add the dispatch approach (this script has fewer exception types):

  ```python
  def main(argv: list[str]) -> int:
      """CLI entry point."""
      parser = argparse.ArgumentParser()
      parser.add_argument("--repo", required=True, help="owner/repo slug")
      parser.add_argument("--body", required=True, type=Path)
      parser.add_argument("--enforcement", choices=("active", "evaluate", "disabled"))
      parser.add_argument("--dry-run", action="store_true")
      args = parser.parse_args(argv)
      try:
          apply(args.repo, args.body, args.enforcement, args.dry_run)
      except SoloDevViolationError as exc:
          print(f"REFUSED: {exc}", file=sys.stderr)
          return EXIT_SOLO_DEV_VIOLATION
      except (
          subprocess.CalledProcessError,
          subprocess.TimeoutExpired,
          FileNotFoundError,
      ) as exc:
          print(f"gh command failed: {exc}", file=sys.stderr)
          return EXIT_GH_FAILURE
      return EXIT_OK
  ```

- [ ] **Step 5: Run the full test suite**

  ```bash
  pytest tests/unit/test_setup_org_rulesets.py \
         tests/unit/test_setup_repo_rulesets.py -v
  ```

  Expected: all PASS.

- [ ] **Step 6: Verify smell count**

  ```bash
  qlty smells --all | grep -E "pr-review-reminder|setup_org_rulesets|setup_repo_rulesets"
  ```

  Expected: 0 smells.

- [ ] **Step 7: Run pre-commit and commit**

  ```bash
  pre-commit run --all-files
  git add scripts/pr-review-reminder.py \
          scripts/setup_org_rulesets.py \
          scripts/setup_repo_rulesets.py
  git commit -m "refactor(scripts): collapse many-returns via guard clauses and dispatch tables

  _should_remind: 5 returns -> 2 (Pattern D guard + single computed return).
  setup_org_rulesets main: 8 returns -> dispatch table + 2 except groups.
  setup_repo_rulesets main: 5 returns -> single policy except + gh group.

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
  ```

---

## Final Verification (After All PRs Merge + 48h After 2E)

- [ ] **Step 1: Full smell audit**

  ```bash
  qlty smells --all
  ```

  Expected: ≤5 total smells. For any residual smell, document the inherent-complexity reason in a comment in the function (not a qlty-ignore). If the count is 6-10 with documented reasons, that may be acceptable; the spec's open question acknowledges AST walkers can be inherently complex.

- [ ] **Step 2: Duplication audit**

  ```bash
  qlty metrics --all | grep -i duplicat
  ```

  Expected: ≤5%.

- [ ] **Step 3: Full test suite**

  ```bash
  pytest --tb=short
  ```

  Expected: all PASS, coverage ≥80%.

- [ ] **Step 4: Pre-commit clean**

  ```bash
  pre-commit run --all-files
  ```

  Expected: all hooks PASS.

- [ ] **Step 5: Confirm no qlty-ignore escape hatches were added**

  ```bash
  grep -r "qlty-ignore\|qlty_ignore" scripts/ tests/ .claude/skills/ --include="*.py"
  ```

  Expected: no output.
