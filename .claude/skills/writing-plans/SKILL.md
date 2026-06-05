---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** This should be run in a dedicated worktree (created by brainstorming skill).

**Save plans to:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
- (User preferences for plan location override this default)

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans, one per subsystem. Each plan should produce working, testable software on its own.

## Codebase Discovery

Before mapping the File Structure, run a read-only discovery pass using the built-in
Explore subagent (`subagent_type: "Explore"` in the Agent tool):

- [ ] Confirm which existing files will be modified (paths, line counts, naming patterns in use)
- [ ] Identify abstractions, types, or utilities the new code should reuse rather than duplicate
- [ ] Note the test file location convention (`tests/unit/`, `tests/`, etc.)
- [ ] Check for existing patterns the plan should follow (error handling style, import conventions)
- [ ] **Verify-prior-claims:** If the source spec asserts a pattern is "proven" or "established,"
      sample-check the actual state of one or more cited proofs before treating the pattern as
      authoritative. For PR-claimed proofs, check the PR's required-check states (especially
      external gates like SonarCloud) via API, not just git mergeability. For commit-claimed
      proofs, verify the cited code against the cited check. A "proven" pattern in a handoff
      is a claim about a past moment, not a present property -- plans that inherit broken
      patterns multiply the rework across every task built on them.

Skip this step only if the plan covers a brand-new, isolated repository with no existing code.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Task Dependencies

When writing a task that depends on an earlier one, annotate the dependency type:

- **`depends-on: TaskN [output]`** -- this task reads or transforms an artifact produced by Task N. Cannot be parallelized.
- **`depends-on: TaskN [completion]`** -- this task conceptually follows Task N but does not consume its output. Can be started as soon as Task N's commits exist on the branch.

Most plan authors implicitly serialize all tasks. Scan each task for steps that don't read or transform an earlier task's artifact; those are candidates for parallelization. Calling them out saves controller cognitive load and shortens wall-clock execution.

## Plan Document Header

**Every plan MUST start with a YAML frontmatter block followed by the plan body.** Check the repo's frontmatter validator before writing (look for `validate-front-matter` in `.pre-commit-config.yaml` or `scripts/`). Common repo-level overrides:

- Repos with a frontmatter `title:` field do NOT allow a body `# H1` heading; all section headers start at `##`. Using `# FeatureName` as the title AND `title: FeatureName` in frontmatter causes a "redundant H1" rejection.
- `schema_type: planning` may require additional fields (e.g., `component:`, `source:`) beyond the `common` schema. Check `docs/_data/` or the validator script for the required-field list.
- Tags must come from the repo's controlled vocabulary. Check `docs/_data/tags.yml` or equivalent before adding tags.

When frontmatter is required:

```markdown
---
title: [Feature Name] Implementation Plan
schema_type: planning
component: [component name]
source: [spec file path]
tags: [valid-tag-1, valid-tag-2]
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Goal

[One sentence describing what this builds]

## Architecture

[2-3 sentences about approach]

## Tech Stack

[Key technologies/libraries]

---
```

When frontmatter is NOT used (simpler repos), keep the original H1 header:

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: ...
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures**; never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code, as the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Exact file paths always
- Complete code in every step; if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it. This is a checklist you run yourself, not a subagent dispatch.

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Placeholder scan:** Search your plan for red flags; any of the patterns from the "No Placeholders" section above should be fixed.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug.

**4. Shell command environment:** For each task that prescribes a shell command, verify any required environment setup is explicit in the command itself. If a script imports its own package (e.g., `from scripts.X import Y`), the invocation must include `PYTHONPATH=.` or the script must self-bootstrap `sys.path`. Test runners set `sys.path` implicitly; documented CLI commands do not. If a working companion script already uses `PYTHONPATH=.`, copy that prefix verbatim -- copying flags without copying environment setup is a silent failure that only appears when someone runs the command as written.

    Also check cwd-sensitivity: scripts whose default path is relative to their own location (not the caller's cwd) require an explicit `--dir` or `--path` flag when invoked via absolute path from a different directory. Document the override flag; do not assume the default works cross-directory.

**5. Capability probe before bulk API operations:** If the plan uses a managed cloud API with a mode flag (`enforcement`, `tier`, `region`, `availability_zone`, etc.), include an early task that sends the smallest possible real call to confirm the mode is supported on the target account before any bulk operation. Dry-run output and validation tooling do not exercise the capability validation layer that returns errors like "Enterprise plan required." One probe call at the start is far cheaper than diagnosing a partial failure mid-bulk-run.

**6. Test-helper consistency check:** If the plan adds new test cases to an existing test file, grep that file for helper functions, fixtures, stub patterns, and `load 'libs/...'` statements. Reference them by name in the plan, or explicitly state when new helpers are intentional. Skipping this audit causes implementers to invent parallel infrastructure that often pollutes the production code under test (test-induced design damage: production code that exists only to satisfy a test's incidental quirks). A grep for `_helper`, `_stub`, `setup()`, `@pytest.fixture` in an existing test file takes seconds; skipping it costs hours of rework.

**7. Tool-replacement coupling table:** If the plan involves replacing one lint, validation, or configuration tool with another, produce an explicit coupling table for each check/code the old tool enforces or suppresses:

    | Old per-code control | New flag | What else that flag forces |
    |---|---|---|

    Every row where "what else" is non-empty is a posture decision that must be surfaced to the user before the plan ships. Discovering config-option coupling at validation time means the posture is decided by whoever happens to be fixing the failures, not deliberately. This applies equally to tool migrations at scale: a single coupled flag (like "require docstring type hints") can turn a zero-churn swap into a hundreds-of-edits fleet rollout.

**8. Nox/pytest session names:** If the plan references nox sessions or pytest marks by name, grep the actual `noxfile.py` (`grep -n '^def '`) or `conftest.py` to confirm the exact names. Session names in nox are function names verbatim; a plan that says `sessions = ["typecheck"]` when the file declares `def type_check(session)` fails immediately.

**9. pytest config sanity:** If the plan preserves or migrates `[tool.pytest.*]` sections in `pyproject.toml`, verify with `pytest --collect-only -q 2>&1 | head -5` that no namespace conflict exists between `[tool.pytest]` (native TOML) and `[tool.pytest.ini_options]` (INI format). Plugin-config sections like `[tool.pytest.benchmark]` must use the hyphenated form `[tool.pytest-benchmark]` to avoid this conflict.

If you find issues, fix them inline; no need to re-review. If you find a spec requirement with no task, add the task.

## Execution Handoff

After saving the plan, offer execution choice:

**"Plan complete and saved to `docs/superpowers/plans/<filename>.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?"**

**If Subagent-Driven chosen:**
- **REQUIRED SUB-SKILL:** Use superpowers:subagent-driven-development
- Fresh subagent per task + two-stage review

**If Inline Execution chosen:**
- **REQUIRED SUB-SKILL:** Use superpowers:executing-plans
- Batch execution with checkpoints for review
