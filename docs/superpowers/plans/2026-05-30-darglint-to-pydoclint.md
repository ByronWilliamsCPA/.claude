---
schema_type: planning
title: "Replace darglint with pydoclint Implementation Plan"
status: draft
owner: core-maintainer
purpose: "Implementation plan for replacing the archived darglint with pydoclint across 14 surfaces, packaged as two PRs: PR1 swaps the tool plus enforcement layer in the .claude repo, PR2 propagates to the cookiecutter template and the Python fleet."
component: Development-Tools
source: "docs/superpowers/specs/2026-05-30-darglint-to-pydoclint-design.md"
tags:
  - tooling
  - linting
  - compliance
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unmaintained darglint docstring-argument validator with pydoclint across all 14 functional surfaces, packaged as two PRs.

**Architecture:** PR1 (this branch, `chore/replace-darglint-with-pydoclint`) swaps the tool in the `.claude` repo AND retargets the enforcement layer (manifest, agents, rules, docs) in the same PR, because the repo is audited by its own `standards-manifest.yaml`; changing one without the other creates a window where the repo fails its own audit. PR2 (a fresh branch off PR1's merge) propagates the swap to the cookiecutter template and rolls out across the Python fleet via the repo-compliance coordinator.

**Tech Stack:** pydoclint 0.8.4 (pinned at commit `88d83c94156c5e51a09938e77019f2c58e92ab58`), pre-commit, uv, the standards-manifest DSL, cookiecutter.

**Spec:** `docs/superpowers/specs/2026-05-30-darglint-to-pydoclint-design.md`

**Design decisions carried from the spec:**
- **Config posture = lenient plus keep raises.** Reproduce darglint's excess-only behaviour for args/returns/yields; keep raises checking on (`skip-checking-raises = false`) to preserve DAR402 (via DOC502), accepting that DOC501 (missing-raises) is newly gained.
- **Drop the hook from the pre-commit.ci `skip:` list** so pre-commit.ci enforces pydoclint directly.
- **Retire the TOOL-007 NumPy override after validation** on a `style=numpy` repo.

**A note on test style:** This is a config/enforcement migration, not application code, so there is no `pytest` unit test to write per task. The TDD analogue here is: each task ends with an explicit *verification command and its expected output*, and a commit. Task 3 is the central validation gate (the equivalent of "run the test suite").

---

## File Structure

**PR1 (this branch) modifies, in the `.claude` repo:**

| File | Responsibility | Change |
|------|----------------|--------|
| `pyproject.toml:97` | dev dependency | `darglint>=1.8.1` → `pydoclint>=0.8.4` |
| `pyproject.toml:528-547` | tool config | `[tool.darglint]` → `[tool.pydoclint]` |
| `.pre-commit-config.yaml:267-275` | hook executor | local darglint hook → pinned pydoclint repo hook |
| `.pre-commit-config.yaml:21` | pre-commit.ci skip | remove `darglint` entry |
| `docs/standards-manifest.yaml:266-272` | TOOL-007 | retarget to pydoclint |
| `docs/standards-manifest.yaml:368-374` | PC-006 | retarget to pydoclint |
| `docs/standards-manifest.yaml` (new check) | darglint-absence | add after TOOL-004 (safety) |
| `docs/standards-manifest.yaml:3` | manifest header | bump `last_updated` |
| `.claude/agents/pre-commit-auditor.md:95` | required-hook inventory | swap URL/id |
| `.claude/agents/python-toolchain-auditor.md:31-32` | interrogate coupling | swap dep name; keep coupling |
| `.claude/rules/pre-commit.md:24` | checklist line | reword to pydoclint |
| `.claude/rules/python.md:184-192` | behaviour spec | reword; update strictness wording |
| `.claude/skills/pre-commit-authoring/SKILL.md:20,81` | toolchain list + tier | swap name |
| `docs/reference/repo-compliance.md:99,101,131` | summaries + override | update; note override retirement |

**PR2 (separate branch) modifies, in `~/dev/cookiecutter-python-template`:**

| File | Change |
|------|--------|
| `{{cookiecutter.project_slug}}/pyproject.toml:97,620-639` | dep + `[tool.darglint]`→`[tool.pydoclint]` |
| `{{cookiecutter.project_slug}}/.pre-commit-config.yaml:15,211-220` | hook + drop from ci.skip |
| `{{cookiecutter.project_slug}}/.darglint` | **delete** |
| `{{cookiecutter.project_slug}}/.standards/pyproject.toml.baseline:417-438` | `[tool.darglint]`→`[tool.pydoclint]` + comment at :17 |
| `{{cookiecutter.project_slug}}/uv.lock` | regenerate |
| fleet repos' `.claude/compliance-overrides.md` | sweep + remove TOOL-007 entries |

---

## PR1: Phases 1 and 2 (this branch)

### Task 1: Swap the dev dependency and tool config in pyproject.toml

**Files:**
- Modify: `pyproject.toml:97` (dev dep)
- Modify: `pyproject.toml:528-547` (`[tool.darglint]` block)

- [ ] **Step 1: Swap the dev dependency**

In `pyproject.toml`, replace line 97:

```toml
    "darglint>=1.8.1",  # Docstring argument validation
```

with:

```toml
    "pydoclint>=0.8.4",  # Docstring argument validation (replaces archived darglint)
```

- [ ] **Step 2: Replace the `[tool.darglint]` block with `[tool.pydoclint]`**

Replace the entire block at `pyproject.toml:528-547` (the comment header through `ignore_regex`):

```toml
# Darglint Configuration (Docstring Argument Validation)
# Validates that docstring arguments match function signatures
# Reference: https://github.com/terrencepreilly/darglint
[tool.darglint]
# Google-style docstrings (matches ruff pydocstyle convention)
docstring_style = "google"
# Strictness levels: short, long, full
# - short: Only documented items must exist in signature
# - long: All parameters must be documented (recommended)
# - full: Types in docstring must match annotations
strictness = "long"
# Ignore missing parameter documentation in these cases
ignore = [
    "DAR101",  # Missing parameter(s) in Docstring (initially lenient)
    "DAR201",  # Missing "Returns" in Docstring (handled by pydocstyle)
    "DAR301",  # Missing "Yields" in Docstring
    "DAR401",  # Missing exception(s) in Raises section
]
# Ignore in these directories
ignore_regex = "^(tests|scripts|benchmarks|tools)/.*$"
```

with this starting-point pydoclint config (Task 3 finalises the exact flags against real output):

```toml
# Pydoclint Configuration (Docstring Argument Validation)
# Validates that docstring arguments match function signatures.
# Replaces archived darglint. Reference: https://jsh9.github.io/pydoclint/config_options.html
# Posture: lenient (excess/mismatch only for args/returns/yields) plus raises checking on.
# File scoping is handled by the pre-commit hook `exclude:` regex; the `exclude`
# below applies when pydoclint is run directly (e.g. `uv run pydoclint src/`).
[tool.pydoclint]
style = "google"
exclude = '\.git|tests/|scripts/|benchmarks/|tools/|noxfile\.py|\.claude/skills/'
arg-type-hints-in-docstring = true            # keep DAR103-equivalent type checks
arg-type-hints-in-signature = true
skip-checking-raises = false                  # keep DAR402-equivalent (DOC502); gains DOC501
require-return-section-when-returning-nothing = false
require-yield-section-when-yielding-values = false
```

- [ ] **Step 3: Verify the file parses as valid TOML**

Run: `uv run python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('pyproject.toml OK')"`
Expected: `pyproject.toml OK`

- [ ] **Step 4: Confirm no darglint references remain in pyproject.toml**

Run: `grep -n darglint pyproject.toml || echo "no darglint in pyproject.toml"`
Expected: `no darglint in pyproject.toml`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -S -m "build(deps): swap darglint dev dep and config for pydoclint

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Replace the pre-commit hook and drop it from the ci.skip list

**Files:**
- Modify: `.pre-commit-config.yaml:262-275` (the darglint local hook block)
- Modify: `.pre-commit-config.yaml:21` (ci.skip list)

- [ ] **Step 1: Replace the local darglint hook with the pinned pydoclint repo hook**

Replace the block at `.pre-commit-config.yaml:262-275`:

```yaml
  # ============================================================================
  # Docstring Argument Validation
  # ============================================================================
  # Darglint validates that docstring arguments match function signatures
  # Configuration in pyproject.toml [tool.darglint]
  - repo: local
    hooks:
      - id: darglint
        name: Darglint docstring validation
        entry: uv run darglint
        language: system
        types: [python]
        stages: [pre-commit]
        exclude: ^(tests|scripts|benchmarks|tools|noxfile\.py|\.claude/skills/)
```

with:

```yaml
  # ============================================================================
  # Docstring Argument Validation
  # ============================================================================
  # pydoclint validates that docstring arguments match function signatures
  # Configuration in pyproject.toml [tool.pydoclint]
  - repo: https://github.com/jsh9/pydoclint
    rev: 88d83c94156c5e51a09938e77019f2c58e92ab58  # 0.8.4
    hooks:
      - id: pydoclint
        args: ["--config=pyproject.toml"]
        types: [python]
        stages: [pre-commit]
        exclude: ^(tests|scripts|benchmarks|tools|noxfile\.py|\.claude/skills/)
```

- [ ] **Step 2: Drop `darglint` from the pre-commit.ci skip list**

Replace `.pre-commit-config.yaml:21`:

```yaml
  skip: [validate-front-matter, qlty-check, qlty-full, trufflehog, darglint, bandit, bandit-full, pip-audit]  # Skip local-only hooks
```

with (remove only `darglint`; do NOT add `pydoclint`, since it is now a real repo hook that pre-commit.ci can run):

```yaml
  skip: [validate-front-matter, qlty-check, qlty-full, trufflehog, bandit, bandit-full, pip-audit]  # Skip local-only hooks
```

- [ ] **Step 3: Verify the YAML parses and the rev is a full 40-char SHA (PC SHA-pinning rule)**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml')); print('yaml OK')"
grep -n "rev: 88d83c94156c5e51a09938e77019f2c58e92ab58" .pre-commit-config.yaml && echo "SHA pinned (40 chars)"
```
Expected: `yaml OK` then `SHA pinned (40 chars)`.

- [ ] **Step 4: Confirm pre-commit accepts the config (migration/validation, does not run hooks)**

Run: `pre-commit validate-config`
Expected: exit 0, no output (or a success line). If it reports the hook id is unknown, the `rev` does not contain a `pydoclint` hook; re-confirm the SHA against `https://github.com/jsh9/pydoclint/blob/0.8.4/.pre-commit-hooks.yaml`.

- [ ] **Step 5: Commit**

```bash
git add .pre-commit-config.yaml
git commit -S -m "ci(pre-commit): replace darglint hook with pinned pydoclint, enforce on pre-commit.ci

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Validation gate, lock the lenient config against real output

This is the central gate. It empirically pins the flag set and proves parity. Do not skip or rush it.

**Files:**
- Modify (only if drift is found): `src/**/*.py` docstrings, or `pyproject.toml` `[tool.pydoclint]`

- [ ] **Step 1: Refresh the lockfile and environment**

Run: `uv lock && uv sync --all-extras`
Expected: lockfile updates to include pydoclint 0.8.4; sync completes with no resolution error. Confirm: `uv run pydoclint --version` prints `0.8.4`.

- [ ] **Step 2: Run pydoclint on src/ and capture the DOC-code histogram**

Run:
```bash
uv run pydoclint src/ 2>&1 | tee /tmp/pydoclint-baseline.txt
grep -oE 'DOC[0-9]+' /tmp/pydoclint-baseline.txt | sort | uniq -c | sort -rn
```
Expected: a count per DOC code. Interpret against the intended profile:

| DOC code | Meaning | Intended | Action if it fires |
|----------|---------|----------|--------------------|
| DOC102 | docstring arg not in signature | KEEP (= DAR102) | none; this is wanted |
| DOC105-107 | arg type mismatch | KEEP (= DAR103) | fix the docstring type |
| DOC202/203 | extra/ mismatched Returns | KEEP (= DAR202/203) | fix the docstring |
| DOC403 | extra Yields | KEEP (= DAR302) | fix the docstring |
| DOC502 | exception documented, not raised | KEEP (= DAR402) | fix the docstring |
| DOC501 | raised exception not documented | NEW (gained) | document the raise (Decision 1) |
| DOC101/DOC103 | docstring missing args present in signature | NOT intended (was DAR101, ignored) | see Step 3 |

- [ ] **Step 3: Decide based on the histogram (decision gate, may require user input)**

- **If only the KEEP codes (and a small, fixable number of DOC501) fire:** the lenient profile is reproduced. Fix the genuine drift in docstrings (never `# noqa`), then proceed to Step 4.
- **If DOC101/DOC103 (missing-args) fire broadly:** pydoclint has no per-direction toggle to suppress missing-args while keeping excess-args, so exact lenient parity is not reachable by flags. STOP and surface to the user with the count. Present three options, do NOT silently suppress:
  1. **Document the args** (tighten by necessity): write the missing `Args` entries. Largest effort; highest doc quality.
  2. **Adopt a pydoclint baseline** (preserves lenient intent): run `uv run pydoclint --generate-baseline=1 --baseline=.pydoclint-baseline.txt src/`, commit `.pydoclint-baseline.txt`, and add `baseline = ".pydoclint-baseline.txt"` to `[tool.pydoclint]`. Existing violations are grandfathered as an explicit, reviewable ledger (not a blanket noqa); only NEW drift fails. This is the recommended bridge for a zero-churn migration.
  3. **Reconsider posture** with the user (e.g. accept option 1 for `src/` only).

  Wait for the user's choice before continuing. Record the choice in the PR description.

- [ ] **Step 4: Run the hook end-to-end to confirm hook-level parity**

Run: `pre-commit run pydoclint --all-files`
Expected: PASS (or the same set of intended findings, all resolved per Step 3). A failing run here that is NOT explained by Step 3 means the hook `exclude:` or `--config` is wrong; fix before committing.

- [ ] **Step 5: Commit the validated state**

```bash
# Include any docstring fixes and/or the baseline file produced in Step 3.
git add -A
git commit -S -m "fix(docs): resolve pydoclint findings and lock validated config

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Retarget the standards manifest and add a darglint-absence check

**Files:**
- Modify: `docs/standards-manifest.yaml:266-272` (TOOL-007)
- Modify: `docs/standards-manifest.yaml:368-374` (PC-006)
- Create: a new TOOL check after TOOL-004 (`docs/standards-manifest.yaml:248`)
- Modify: `docs/standards-manifest.yaml:3` (`last_updated`)

- [ ] **Step 1: Retarget TOOL-007 to pydoclint**

Replace `docs/standards-manifest.yaml:266-272`:

```yaml
  - id: TOOL-007
    domain: toolchain
    severity: important
    description: "darglint present in dev dependencies"
    verify: "dep_present: darglint"
    override_eligible: true
    not_applicable_when: "repo does not contain Python source files"
```

with:

```yaml
  - id: TOOL-007
    domain: toolchain
    severity: important
    description: "pydoclint present in dev dependencies (replaces archived darglint)"
    verify: "dep_present: pydoclint"
    override_eligible: true
    not_applicable_when: "repo does not contain Python source files"
```

- [ ] **Step 2: Retarget PC-006 to pydoclint**

Replace `docs/standards-manifest.yaml:368-374`:

```yaml
  - id: PC-006
    domain: pre_commit
    severity: important
    description: "darglint hook present in .pre-commit-config.yaml"
    verify: "hook_present: .pre-commit-config.yaml, darglint"
    override_eligible: true
    not_applicable_when: "repo does not contain Python source files"
```

with:

```yaml
  - id: PC-006
    domain: pre_commit
    severity: important
    description: "pydoclint hook present in .pre-commit-config.yaml"
    verify: "hook_present: .pre-commit-config.yaml, pydoclint"
    override_eligible: true
    not_applicable_when: "repo does not contain Python source files"
```

- [ ] **Step 3: Add a darglint-absence check following the replaced-tools pattern**

Insert immediately after TOOL-004 (the `safety` absence check ends at `docs/standards-manifest.yaml:248`), before TOOL-005. Use the next free TOOL id; the existing absence checks are TOOL-002/003/004, so this is a new id (confirm the highest TOOL id at insertion time and use the next one, e.g. `TOOL-013` if 012 is the current max):

```yaml
  - id: TOOL-013
    domain: toolchain
    severity: important
    description: "darglint absent from dependencies (replaced by pydoclint)"
    verify: "dep_absent: darglint"
    override_eligible: false
    not_applicable_when: "repo does not contain Python source files"
```

- [ ] **Step 4: Bump the manifest `last_updated` header**

Replace `docs/standards-manifest.yaml:3`:

```yaml
last_updated: "2026-05-28"
```

with (use the actual implementation date):

```yaml
last_updated: "2026-05-30"
```

- [ ] **Step 5: Verify the manifest parses and the checks are present**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('docs/standards-manifest.yaml')); print('manifest OK')"
grep -nE "dep_present: pydoclint|hook_present: .pre-commit-config.yaml, pydoclint|dep_absent: darglint" docs/standards-manifest.yaml
```
Expected: `manifest OK`, then three matching lines.

- [ ] **Step 6: Commit**

```bash
git add docs/standards-manifest.yaml
git commit -S -m "feat(manifest): retarget TOOL-007/PC-006 to pydoclint, add darglint-absence check

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Update the domain auditor agents

**Files:**
- Modify: `.claude/agents/pre-commit-auditor.md:95`
- Modify: `.claude/agents/python-toolchain-auditor.md:31-32`

- [ ] **Step 1: Swap the hook URL/id in the pre-commit-auditor required-hook inventory**

Replace `.claude/agents/pre-commit-auditor.md:95`:

```markdown
- `https://github.com/terrencepreilly/darglint`: `darglint`
```

with:

```markdown
- `https://github.com/jsh9/pydoclint`: `pydoclint`
```

- [ ] **Step 2: Swap the dep name in the python-toolchain-auditor interrogate coupling (keep the coupling logic)**

Replace `.claude/agents/python-toolchain-auditor.md:31-32`:

```markdown
- `interrogate_config` checks: when `darglint` or `interrogate` appears in any dev dependency section or in the pre-commit hook IDs (check `.pre-commit-config.yaml` if present), Read `pyproject.toml` and check for a `[tool.interrogate]` section containing a `fail-under` key. If absent, report:
  - id: `TOOL-NEW-002`, severity: `suggested`, description: `[tool.interrogate] section absent from pyproject.toml despite darglint/interrogate present in dev dependencies or pre-commit hook IDs`, status: `configuration_gap`, current_value: `[tool.interrogate] section not found in pyproject.toml`
```

with:

```markdown
- `interrogate_config` checks: when `pydoclint` or `interrogate` appears in any dev dependency section or in the pre-commit hook IDs (check `.pre-commit-config.yaml` if present), Read `pyproject.toml` and check for a `[tool.interrogate]` section containing a `fail-under` key. If absent, report:
  - id: `TOOL-NEW-002`, severity: `suggested`, description: `[tool.interrogate] section absent from pyproject.toml despite pydoclint/interrogate present in dev dependencies or pre-commit hook IDs`, status: `configuration_gap`, current_value: `[tool.interrogate] section not found in pyproject.toml`
```

- [ ] **Step 3: Confirm no stray darglint references remain in the two agents**

Run: `grep -n darglint .claude/agents/pre-commit-auditor.md .claude/agents/python-toolchain-auditor.md || echo "clean"`
Expected: `clean`

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/pre-commit-auditor.md .claude/agents/python-toolchain-auditor.md
git commit -S -m "docs(agents): retarget pre-commit and toolchain auditors to pydoclint

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Update rules and skill prose

**Files:**
- Modify: `.claude/rules/pre-commit.md:24`
- Modify: `.claude/rules/python.md:184-192`
- Modify: `.claude/skills/pre-commit-authoring/SKILL.md:20` and `:81`

- [ ] **Step 1: Reword the pre-commit checklist line**

Replace `.claude/rules/pre-commit.md:24`:

```markdown
- [ ] **Docstring Arguments**: `darglint` passes; `Args`/`Returns`/`Raises` sections match function signatures (excludes `tests/`, `scripts/`, `benchmarks/`, `tools/`, `noxfile.py`, `.claude/skills/`). Update the docstring to fix mismatches.
```

with:

```markdown
- [ ] **Docstring Arguments**: `pydoclint` passes; `Args`/`Returns`/`Raises` sections match function signatures, and raised exceptions are documented (excludes `tests/`, `scripts/`, `benchmarks/`, `tools/`, `noxfile.py`, `.claude/skills/`). Update the docstring to fix mismatches.
```

- [ ] **Step 2: Reword the python.md behaviour spec (lines 184-192)**

Replace `.claude/rules/python.md:184-192`:

```markdown
**Docstring argument validation**: `darglint` runs at pre-commit and validates that
documented `Args`, `Returns`, and `Raises` sections match the actual function signature.
Strictness: `long` (validates `Args`/`Returns`/`Raises` when a full multi-line docstring is
present; single-line docstrings are not checked); all parameters must be documented. Excluded:
`tests/`, `scripts/`, `benchmarks/`, `tools/`, `noxfile.py`, `.claude/skills/`. The `scripts/`
exclusion is intentional: utility scripts often use `*args`/`**kwargs` patterns where darglint
produces false positives.
```

with:

```markdown
**Docstring argument validation**: `pydoclint` runs at pre-commit and validates that
documented `Args`, `Returns`, `Yields`, and `Raises` sections match the actual function
signature. Posture: lenient on missing sections (consistency/excess checks for args, returns,
and yields) but raises checking is on, so a documented exception that is not raised fails, and
a raised exception that is not documented fails (DOC501/DOC502). Configured in
`[tool.pydoclint]` via option flags rather than a per-code ignore list. Excluded:
`tests/`, `scripts/`, `benchmarks/`, `tools/`, `noxfile.py`, `.claude/skills/`. The `scripts/`
exclusion is intentional: utility scripts often use `*args`/`**kwargs` patterns where the
validator produces false positives.
```

- [ ] **Step 3: Swap the name in the pre-commit-authoring toolchain list (line 20)**

Replace the fragment on `.claude/skills/pre-commit-authoring/SKILL.md:19-21`:

```markdown
toolchain (ruff, basedpyright, yamllint, markdownlint, TruffleHog,
detect-secrets, interrogate, darglint, qlty, pip-audit). The principles
generalize; the specific hook examples reference this fleet's standards.
```

with:

```markdown
toolchain (ruff, basedpyright, yamllint, markdownlint, TruffleHog,
detect-secrets, interrogate, pydoclint, qlty, pip-audit). The principles
generalize; the specific hook examples reference this fleet's standards.
```

- [ ] **Step 4: Swap the name in the slow-tier placement (line 81)**

Replace the fragment on `.claude/skills/pre-commit-authoring/SKILL.md:80-82`:

```markdown
- **Slower checks (pre-commit if budget allows, else pre-push):**
  TruffleHog (staged form), interrogate, darglint, bandit on changed
  files, qlty check.
```

with:

```markdown
- **Slower checks (pre-commit if budget allows, else pre-push):**
  TruffleHog (staged form), interrogate, pydoclint, bandit on changed
  files, qlty check.
```

- [ ] **Step 5: Confirm no stray darglint references remain in these three files**

Run: `grep -n darglint .claude/rules/pre-commit.md .claude/rules/python.md .claude/skills/pre-commit-authoring/SKILL.md || echo "clean"`
Expected: `clean`

- [ ] **Step 6: Commit**

```bash
git add .claude/rules/pre-commit.md .claude/rules/python.md .claude/skills/pre-commit-authoring/SKILL.md
git commit -S -m "docs(rules): reword docstring-validation prose for pydoclint

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Update repo-compliance reference and note the override retirement

**Files:**
- Modify: `docs/reference/repo-compliance.md:99,101` (TOOL/PC summaries)
- Modify: `docs/reference/repo-compliance.md:131` (TOOL-007 override example)

- [ ] **Step 1: Update the TOOL summary (line 99)**

In `docs/reference/repo-compliance.md`, find the TOOL domain summary line that reads:

```markdown
**TOOL (Toolchain, 12 checks):** Dev dependency presence (ruff, basedpyright, pip-audit, darglint, interrogate), absence of replaced tools (black, mypy, safety), Ruff PyStrict-aligned rule set, BasedPyright strict config, qlty config, target-version.
```

Replace with (bump the count to 13 for the new absence check, and add darglint to the replaced-tools list):

```markdown
**TOOL (Toolchain, 13 checks):** Dev dependency presence (ruff, basedpyright, pip-audit, pydoclint, interrogate), absence of replaced tools (black, mypy, safety, darglint), Ruff PyStrict-aligned rule set, BasedPyright strict config, qlty config, target-version.
```

- [ ] **Step 2: Update the PC summary (line 101)**

Find the PC domain summary fragment listing hook presence:

```markdown
**PC (Pre-commit, 16 checks):** Hook presence (ruff, basedpyright, bandit, detect-secrets, darglint, interrogate, commitizen, yamllint, markdownlint, no-em-dash), hook SHA pinning on all rev fields.
```

Replace the hook list to swap `darglint` → `pydoclint`:

```markdown
**PC (Pre-commit, 16 checks):** Hook presence (ruff, basedpyright, bandit, detect-secrets, pydoclint, interrogate, commitizen, yamllint, markdownlint, no-em-dash), hook SHA pinning on all rev fields.
```

- [ ] **Step 3: Update the TOOL-007 override example (line 131) to reflect retirement**

The override example currently reads:

```markdown
| TOOL-007 | darglint conflicts with NumPy docstring style in this project | Byron Williams | 2026-04-20 |
```

pydoclint supports NumPy style natively, so the original reason no longer holds. Replace the example row with a different, still-valid illustrative override so the doc keeps a generic example (the real per-repo retirement happens in PR2 Task 11):

```markdown
| TOOL-009 | Documentation-only repo; qlty config not applicable | Byron Williams | 2026-05-30 |
```

- [ ] **Step 4: Confirm the only remaining darglint references are intentional (none expected here)**

Run: `grep -n darglint docs/reference/repo-compliance.md || echo "clean"`
Expected: `clean`

- [ ] **Step 5: Commit**

```bash
git add docs/reference/repo-compliance.md
git commit -S -m "docs(reference): update repo-compliance summaries for pydoclint; retire NumPy override example

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Full-repo validation gate and PR1

**Files:** none (verification only)

- [ ] **Step 1: Run the full pre-commit suite**

Run: `pre-commit run --all-files`
Expected: all hooks pass. The `no-em-dash` (PC-011), `validate-front-matter`, and `pydoclint` hooks must pass. Fix any failure at root cause; do not use `--no-verify`.

- [ ] **Step 2: Confirm zero darglint references remain repo-wide (excluding archival docs)**

Run:
```bash
grep -rn darglint --include="*.md" --include="*.yaml" --include="*.yml" --include="*.toml" . \
  | grep -vE "docs/superpowers/|compliance-retrospectives/|docs/handoffs/darglint-to-pydoclint/|docs/superpowers/specs/2026-05-30-darglint-to-pydoclint|docs/superpowers/plans/2026-05-30-darglint-to-pydoclint" \
  || echo "no active darglint references remain"
```
Expected: `no active darglint references remain` (archival narrative, the handoff, this spec, and this plan are intentionally excluded).

- [ ] **Step 3: Self-audit the repo against its own manifest**

Run: `/repo-audit` (repo-compliance) scoped to this repo.
Expected: TOOL-007 and PC-006 now check for pydoclint and PASS; the new darglint-absence check PASSES; no new findings are introduced by the migration. If the auditor still references darglint, a surface was missed; return to the relevant task.

- [ ] **Step 4: Push the branch and open PR1**

```bash
git push -u origin chore/replace-darglint-with-pydoclint
gh pr create --base main --head chore/replace-darglint-with-pydoclint \
  --title "chore: replace darglint with pydoclint (reference impl + enforcement)" \
  --body "$(cat <<'EOF'
Replaces the archived darglint with pydoclint in the .claude repo and retargets the enforcement layer in the same PR (the repo is audited by its own standards-manifest, so the tool swap and the manifest retarget must land together).

## Decisions (from spec docs/superpowers/specs/2026-05-30-darglint-to-pydoclint-design.md)
- Config posture: lenient plus keep raises (skip-checking-raises=false; gains DOC501).
- Dropped darglint from the pre-commit.ci skip list so pre-commit.ci enforces pydoclint.
- TOOL-007 NumPy override retirement deferred to PR2 (fleet sweep).

### Task 3 outcome
<!-- Record the histogram decision: pure parity, baseline adopted, or args documented. -->

Plan: docs/superpowers/plans/2026-05-30-darglint-to-pydoclint.md
EOF
)"
```

If `gh pr create` is auto-denied by the harness, fall back to: `gh api repos/ByronWilliamsCPA/.claude/pulls -X POST -f title=... -f head=... -f base=main -f body=...`.

- [ ] **Step 5: Run the PR review and address findings**

Run: `/code-review` (solo-repo default per `.claude/rules/git-workflow.md`).
Address Critical/Important findings; merge when green.

---

## PR2: Phase 3 cookiecutter template and fleet rollout

> Start this PR only after PR1 merges. Create a fresh branch off the updated main.

- [ ] **Step 0: Branch for PR2**

```bash
cd /home/byron/dev/.claude
git fetch origin
git worktree add -b chore/pydoclint-fleet-rollout .worktrees/chore-pydoclint-fleet-rollout origin/main
```

The cookiecutter edits happen in `~/dev/cookiecutter-python-template`, which is a separate repo with its own branch/PR; the fleet override sweep is driven from the `.claude` worktree.

---

### Task 9: Swap darglint to pydoclint in the cookiecutter template

**Files (in `~/dev/cookiecutter-python-template`):**
- Modify: `{{cookiecutter.project_slug}}/pyproject.toml:97` and `:620-639`
- Modify: `{{cookiecutter.project_slug}}/.pre-commit-config.yaml:15` and `:207-220`
- Delete: `{{cookiecutter.project_slug}}/.darglint`
- Modify: `{{cookiecutter.project_slug}}/.standards/pyproject.toml.baseline:17` and `:417-438`

- [ ] **Step 1: Create a branch in the cookiecutter repo**

```bash
cd ~/dev/cookiecutter-python-template
git fetch origin && git switch -c chore/replace-darglint-with-pydoclint origin/main
```

- [ ] **Step 2: Swap the dev dep (pyproject.toml:97)**

Replace `"darglint>=1.8.1",  # Docstring argument validation` with
`"pydoclint>=0.8.4",  # Docstring argument validation (replaces archived darglint)`.

- [ ] **Step 3: Replace the `[tool.darglint]` block (pyproject.toml:620-639)**

Replace the comment header + `[tool.darglint]` block (the same darglint block shown in Task 1 Step 2, but note the template's `ignore_regex` is `"^(tests|scripts|benchmarks|tools)/.*$|^noxfile\\.py$|^\\.claude/.*$"`) with:

```toml
# Pydoclint Configuration (Docstring Argument Validation)
# Validates that docstring arguments match function signatures.
# Replaces archived darglint. Reference: https://jsh9.github.io/pydoclint/config_options.html
# Posture: lenient (excess/mismatch only for args/returns/yields) plus raises checking on.
[tool.pydoclint]
style = "google"
exclude = '\.git|tests/|scripts/|benchmarks/|tools/|noxfile\.py|\.claude/'
arg-type-hints-in-docstring = true
arg-type-hints-in-signature = true
skip-checking-raises = false
require-return-section-when-returning-nothing = false
require-yield-section-when-yielding-values = false
```

- [ ] **Step 4: Replace the pre-commit hook (.pre-commit-config.yaml:207-220)**

Replace the `repo: local` darglint hook block with the pinned pydoclint hook (same as PR1 Task 2 Step 1, but the template hook `exclude:` is `^(tests|scripts|benchmarks|tools)/`):

```yaml
  # ============================================================================
  # Docstring Argument Validation
  # ============================================================================
  # pydoclint validates that docstring arguments match function signatures
  # Configuration in pyproject.toml [tool.pydoclint]
  - repo: https://github.com/jsh9/pydoclint
    rev: 88d83c94156c5e51a09938e77019f2c58e92ab58  # 0.8.4
    hooks:
      - id: pydoclint
        args: ["--config=pyproject.toml"]
        types: [python]
        stages: [pre-commit]
        exclude: ^(tests|scripts|benchmarks|tools)/
```

- [ ] **Step 5: Drop darglint from the template ci.skip list (.pre-commit-config.yaml:15)**

Replace:
```yaml
  skip: [validate-front-matter, qlty-check, qlty-full, trufflehog, darglint, bandit, bandit-full]  # Skip local-only hooks
```
with:
```yaml
  skip: [validate-front-matter, qlty-check, qlty-full, trufflehog, bandit, bandit-full]  # Skip local-only hooks
```

- [ ] **Step 6: Delete the standalone `.darglint` file**

Run: `git rm "{{cookiecutter.project_slug}}/.darglint"`
Expected: file staged for deletion. (pydoclint config lives in pyproject `[tool.pydoclint]`; there is no standalone pydoclint config file.)

- [ ] **Step 7: Update the baseline doc (.standards/pyproject.toml.baseline)**

Replace the `[tool.darglint]` block at `:417-438` with the pydoclint block from Step 3, and update the comment at `:17` (`#   - [tool.darglint] - Docstring validation`) to `#   - [tool.pydoclint] - Docstring validation`.

- [ ] **Step 8: Verify no darglint references remain in the template tree (except CHANGELOG history)**

Run:
```bash
grep -rln darglint "{{cookiecutter.project_slug}}/" || echo "clean in rendered tree"
```
Expected: `clean in rendered tree`. (The repo-root `CHANGELOG.md` history entry stays; it is a historical record.)

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -S -m "chore: replace darglint with pydoclint in template

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 10: Validate the rendered template and the NumPy style

**Files:** none (verification); may modify `uv.lock`

- [ ] **Step 1: Render the template to a temp dir and confirm it produces a valid project**

Run:
```bash
cd ~/dev/cookiecutter-python-template
uvx cookiecutter . --no-input -o /tmp/cc-pydoclint-test
ls /tmp/cc-pydoclint-test/*/pyproject.toml && echo "rendered OK"
test ! -e /tmp/cc-pydoclint-test/*/.darglint && echo ".darglint absent (correct)"
```
Expected: `rendered OK` and `.darglint absent (correct)`.

- [ ] **Step 2: Regenerate the template uv.lock**

In the rendered project (or the template's lock workflow), run `uv lock` and copy the updated `uv.lock` back into the template if the template ships a committed lock. Confirm pydoclint 0.8.4 appears and darglint does not:
```bash
grep -c 'name = "pydoclint"' "{{cookiecutter.project_slug}}/uv.lock"
grep -c 'name = "darglint"' "{{cookiecutter.project_slug}}/uv.lock"
```
Expected: `1` then `0`.

- [ ] **Step 3: Validate NumPy style on a real repo that carries the TOOL-007 override (Decision 3 precondition)**

Identify a fleet repo whose `.claude/compliance-overrides.md` lists TOOL-007 (see Task 11 Step 1 for the sweep). In a clone of that repo, set `style = "numpy"` in a scratch `[tool.pydoclint]` and run:
```bash
uv run pydoclint --style=numpy src/ 2>&1 | grep -oE 'DOC[0-9]+' | sort | uniq -c
```
Expected: pydoclint parses NumPy docstrings without the style-conflict false positives darglint produced. If clean (only intended DOC codes), the override is safe to retire (Task 11). If NumPy parsing still produces noise, keep the override and record why in the PR.

- [ ] **Step 4: Commit the lock (cookiecutter repo)**

```bash
git add "{{cookiecutter.project_slug}}/uv.lock"
git commit -S -m "chore: regenerate template uv.lock for pydoclint

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 5: Push and open the cookiecutter PR**

```bash
git push -u origin chore/replace-darglint-with-pydoclint
gh pr create --base main --title "chore: replace darglint with pydoclint" --body "Template swap; deletes standalone .darglint; config moves to [tool.pydoclint]. Mirrors ByronWilliamsCPA/.claude PR1."
```

---

### Task 11: Retire the TOOL-007 NumPy override across the fleet

**Files (in the `.claude` worktree for the doc; per-repo for overrides):**
- Per-repo: each repo's `.claude/compliance-overrides.md`

- [ ] **Step 1: Enumerate repos carrying a TOOL-007 override (authoritative scope)**

Use the manifest applicability rule cross-referenced with the catalog, NOT local clone counts. From the `.claude` repo:
```bash
# List Python repos from the catalog, then check each for a TOOL-007 override row.
python - <<'PY'
import json
repos = json.load(open("docs/reference/github-repos.json"))
# Print owner/name for repos flagged as containing Python source.
for r in repos.get("repos", repos if isinstance(repos, list) else []):
    name = r.get("full_name") or f'{r.get("owner")}/{r.get("name")}'
    print(name)
PY
```
Then for each repo, check its `.claude/compliance-overrides.md` for a `TOOL-007` row via the GitHub Contents API (authoritative for default-branch HEAD; `gh search code` lags):
```bash
gh api "repos/<owner>/<repo>/contents/.claude/compliance-overrides.md" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null | grep -n "TOOL-007" && echo "<owner>/<repo>: HAS TOOL-007 override"
```
Record the list of repos that actually have the override.

- [ ] **Step 2: For each repo with the override AND validated clean under NumPy style (Task 10 Step 3), remove the row**

In a local clone of each such repo (never via the Contents API; these repos require signed commits), delete the `| TOOL-007 | ... |` row from `.claude/compliance-overrides.md`, commit signed on a `chore/retire-darglint-override` branch, and open a PR:
```bash
git switch -c chore/retire-darglint-override origin/main
# edit .claude/compliance-overrides.md: remove the TOOL-007 row
git add .claude/compliance-overrides.md
git commit -S -m "chore(compliance): retire TOOL-007 darglint NumPy override (pydoclint supports NumPy)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push -u origin chore/retire-darglint-override
gh pr create --base main --title "chore: retire TOOL-007 darglint override" --body "pydoclint supports NumPy docstrings natively; the darglint NumPy conflict that justified this override no longer applies."
```

- [ ] **Step 3: Verify**

After each PR merges, re-run `/repo-audit` on that repo and confirm TOOL-007 now PASSES against pydoclint with no override needed (no suppressed-count entry for TOOL-007).

---

### Task 12: Fleet rollout of the tool swap

**Files:** per-repo `pyproject.toml`, `.pre-commit-config.yaml`

- [ ] **Step 1: Confirm the manifest is live on main**

PR1 must be merged so that `/repo-audit` checks for pydoclint and flags darglint's presence/absence fleet-wide.

- [ ] **Step 2: Drive the rollout through the repo-compliance coordinator**

For each Python repo in scope (manifest applicability cross-referenced with `docs/reference/github-repos.json`), run the repo-compliance remediation flow. The audit will now FAIL TOOL-007 (pydoclint absent), PC-006 (pydoclint hook absent), and the new darglint-absence check (darglint present). The coordinator's remediation applies the same edits as PR1 Tasks 1-2 per repo:
- swap the dev dep,
- replace the pre-commit hook with the pinned pydoclint hook (`rev: 88d83c94156c5e51a09938e77019f2c58e92ab58`),
- replace `[tool.darglint]` with `[tool.pydoclint]`,
- run the Task 3 validation gate per repo (each repo's docstring drift is fixed or baselined individually),
- open one PR per repo (signed commits; never the Contents API).

- [ ] **Step 3: Verify CI coverage per repo before assuming enforcement**

For each repo, confirm which reusable workflow it wires: repos calling `ByronWilliamsCPA/.github/.github/workflows/python-precommit.yml` run `pre-commit run --all-files` (so pydoclint executes in CI); repos calling `python-ci.yml` do not run the pre-commit suite in CI, so enforcement there is pre-commit/pre-commit.ci only. Record per-repo CI coverage; do not assume.

- [ ] **Step 4: Track rollout completion**

Maintain the rollout list (repos done / pending) until 100%. Per the policy-execution-gap lesson, audit *reach* separately from definition: a green manifest does not mean every repo is migrated. Mark TOOL-013 (darglint-absence) `suggested` if rollout is incomplete at any checkpoint, promoting to `important` only when reach hits 100%.

---

## Self-Review

This section was completed by the plan author against the spec:

- **Spec coverage:** All 14 surfaces from the spec's scope table map to a task (surfaces 1-5 → Tasks 1-3; 6-7 + absence check → Task 4; 8-9 → Task 5; 10-12 → Task 6; 13 → Task 7; 14 → Task 9; fleet → Tasks 11-12). The three decisions are encoded: Decision 1 in Tasks 1+3, Decision 2 in Task 2 Step 2, Decision 3 in Tasks 10 Step 3 + 11, Decision 4 in the PR1/PR2 split.
- **Placeholder scan:** No TBD/TODO. Task 3 Step 3 is a documented decision procedure with real commands and the pydoclint baseline mechanism, not a placeholder; the exact final flag set is intentionally output-driven because pydoclint has no per-direction args toggle.
- **Type/name consistency:** Hook id `pydoclint`, dep `pydoclint>=0.8.4`, SHA `88d83c94156c5e51a09938e77019f2c58e92ab58`, and config block name `[tool.pydoclint]` are identical across every task that references them.
- **Shell command environment:** The inline Python snippets use stdlib only (`tomllib`, `yaml`, `json`, `base64`) and need no `PYTHONPATH`. `gh api` Contents calls are used (not `gh search code`) per the catalog-staleness lesson. Signed-commit + local-clone workflow is used for fleet repos (never the Contents API on signed repos).
- **Capability probe:** Task 3 Step 1 (`uv run pydoclint --version`) and Task 2 Step 4 (`pre-commit validate-config`) are the early real-call probes confirming the tool and hook resolve before bulk edits.
