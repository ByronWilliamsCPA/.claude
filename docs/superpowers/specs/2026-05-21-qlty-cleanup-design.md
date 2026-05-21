---
schema_type: common
title: qlty Smell and Duplication Cleanup
status: draft
owner: engineering
tags: [code_quality, compliance, standards]
purpose: Design for cleaning up qlty's 523 reported smells and 30.7% duplication, by first fixing a qlty.toml misconfiguration that lets submodules dominate the report (drops count to ~50), then refactoring 18 high-complexity functions, 8 deep-nesting smells, 6 many-returns, and 10 duplication blocks in own code across 7 sequenced PRs over 4-5 weeks without any qlty-ignore escape hatches.
---

## Context

`qlty` reports 523 smells and 30.7% duplication on `main`, with `base.py`
flagged as a security hotspot. Investigation revealed two distinct problems:

1. **Configuration bug (root cause of 90%+ of the count).** `.qlty/qlty.toml`
   places `exclude_patterns`, `test_patterns`, and `enabled` under
   `[plugins]`, but qlty only accepts these as top-level keys (and
   `enabled` as a `[plugins.enabled]` table). Three warnings are printed
   on every `qlty` run; the warnings are correct and the keys are silently
   ignored. Result: every Python file under `.submodules/` is analyzed
   even though the existing submodule-isolation policy says they should
   be inert from quality gates.

2. **Genuine own-code smells (~50).** 12 files in `scripts/`, 5 in
   `tests/`, and 3 in `.claude/skills/` carry real complexity, nesting,
   many-return, and duplication smells. Several functions are at
   maintainability-risk thresholds: `visit_Call` cc=51, `reconcile`
   cc=39, `check_repo` cc=36.

The "base.py security hotspot" framing in `qlty.sh` is an artifact of
problem 1: every project-tree `base.py` is in `.submodules/` or `.nox/`
(third-party). There is no project-level `base.py`.

Distribution of the 523 smells:

| Area | Files | Smell instances |
|---|---|---|
| `.submodules/` (third-party) | 81 | 473 |
| `.claude/skills/`, `scripts/`, `tests/` (own code) | 20 | 50 |
| Other (cross-file dup pairs) | 0 | ~11 |

## Goal

Drive `qlty smells --all` from 523 to ≤ 5 and duplication from 30.7% to
single-digit percent, **without** using `qlty-ignore` comments or relaxing
smell thresholds in `.claude/skills/`, `scripts/`, or `tests/`.

## Scope

### In scope

- `.qlty/qlty.toml` configuration fix
- All 18 high-complexity functions in own code (cyclomatic complexity
  ≥ 12 after the Python-specific threshold override)
- All 8 deep-nesting smells in own code
- All 6 many-returns smells in own code
- All 10 duplication blocks in own code
- Test coverage protecting each refactored function (add tests before
  refactoring when prior coverage is thin)

### Out of scope

- Anything under `.submodules/`, `.nox/`, `.venv/` (the config fix makes
  these invisible to qlty; existing submodule-isolation policy forbids
  editing submodule internals)
- Smell threshold changes beyond the misconfiguration fix
- The bandit security plugin overlap with pre-commit (separate cleanup)
- Performance refactors or feature additions

## Success Criteria

1. `qlty smells --all` reports ≤ 5 smells, each with a documented
   inherent-complexity reason
2. `qlty metrics --all` reports duplication ≤ 5%
3. `pre-commit run --all-files` passes
4. All existing tests pass; new tests added for any function refactored
   without prior coverage
5. No `qlty-ignore` comments added in `scripts/`, `tests/`, or
   `.claude/skills/` Python files

## Phase 1: Configuration Fix (single PR)

Mechanical change to `.qlty/qlty.toml`. No code touched.

### Diff summary

- Move `exclude_patterns` from `[plugins]` to top level
- Move `test_patterns` from `[plugins]` to top level
- Add `**/.nox/**` to `exclude_patterns` explicitly
- Replace `[plugins] enabled = [...]` flat list with
  `[plugins.enabled]` TOML table:

  ```toml
  [plugins.enabled]
  ruff = "latest"
  basedpyright = "latest"
  bandit = "latest"
  ```

- `[smells]`, `[smells.*]`, `[language.python.smells]` sections
  unchanged (valid syntax, already applied correctly)

### Verification steps

1. `qlty config validate` exits clean with no warnings about
   `plugins.exclude_patterns`, `plugins.enabled`, or
   `plugins.test_patterns`
2. `qlty config show` confirms resolved config places the three keys
   at the right scope
3. `qlty smells --all` smell count drops from 523 to ~50
4. `qlty smells --all | grep -E "^\.submodules" | wc -l` returns 0
5. `qlty metrics --all` duplication percentage drops to single digits

### Risk

Near-zero. `qlty config validate` catches invalid TOML before merge.

### Post-merge memory update

Append a one-line note to `feedback_submodule_isolation.md` recording
that qlty.toml now actively enforces the policy (it didn't before).

## Phase 2: Refactor Sweep (7 PRs)

Grouped by logical area so each PR has a coherent reviewer narrative.
Low-risk PRs ship first to build confidence; high-risk PRs are
serialized with 48-hour soak windows between them.

| PR | Area | Files | Kills | Risk |
|---|---|---|---|---|
| 2A | Test fixture extraction | `tests/integration/test_compliance_log_append.py`, `tests/unit/test_compliance_log_common.py`, `tests/unit/_load_*.py`, `tests/unit/test_apply_williaby_repo_rulesets.py` | ~7 duplication blocks (148-mass, 142-mass, two 67-mass, two 74-mass) | Low |
| 2B | Planning + coverage skills | `.claude/skills/project-planning/scripts/validate-planning-docs.py`, `.claude/skills/test-coverage/scripts/parse_coverage.py`, `.claude/skills/testing/evals/files/validators.py` | 5 complexity, 2 nesting, 2 dup (110-mass twins → `_validate_doc()` helper) | Medium |
| 2C | FIPS AST walker | `scripts/check_fips_compatibility.py` | 3 complexity (cc=51 `visit_Call` is the worst function in the repo), 3 nesting, 2 dup | High (fleet-wide FIPS detection) |
| 2D | Repo compliance | `scripts/check-repo-compliance.py` | 3 complexity (cc=36, 34, 32), 2 nesting, 2 many-returns | High (drives compliance scoring) |
| 2E | Compliance logging + reconciler | `scripts/compliance_log_append.py`, `scripts/compliance_rollup_reconcile.py`, `scripts/compliance_log_common.py` | 5 complexity (cc=39 `reconcile`, cc=27 `_atomic_supersede_and_append`) | High (file-locking + atomic-write on master log) |
| 2F | Doc audit + supporting checkers | `scripts/doc-audit.py`, `scripts/check_type_hints.py`, `scripts/populate-github-repos.py`, `scripts/check-required-checks.py` | 9 complexity, 2 nesting | Medium |
| 2G | Many-returns cleanup | `scripts/pr-review-reminder.py`, `scripts/setup_org_rulesets.py`, `scripts/setup_repo_rulesets.py` | 4 many-returns | Low |

### Sequencing rules

- Phase 1 must merge first (hard dependency). Until then, per-PR delta
  verification is meaningless because the baseline includes 473
  submodule false-positives
- 2A and 2G can ship in parallel
- 2B and 2F can run in parallel with anything else
- 2C, 2D, 2E are serialized with 48-hour soak windows between merges

## Refactor Pattern Catalog

Every refactor in Phase 2 uses one of four patterns. The implementer
picks the pattern that matches the smell type; no per-function design
re-litigation.

### Pattern A: High-complexity orchestrator → dispatch table

Applies to: `visit_Call` (cc=51), `reconcile` (cc=39), `check_repo`
(cc=36), `_admins_enforced` (cc=34), `main` variants (cc=32, 24, 20).

Replace a long if/elif chain or nested branch tree with a dict mapping
case-discriminator → small handler function. Each handler is ≤ cc=5,
individually testable; the dispatch dict doubles as documentation.

```python
_FIPS_CHECKERS: dict[str, Callable[[ast.Call], FipsFinding | None]] = {
    "hashlib.md5": _check_hashlib_md5,
    "Crypto.Hash.MD5": _check_pycrypto_md5,
}

def visit_Call(self, node: ast.Call) -> None:
    qname = _qualified_name(node.func)
    if checker := _FIPS_CHECKERS.get(qname):
        if finding := checker(node):
            self.findings.append(finding)
```

### Pattern B: Deep nesting → early-return + extract-method

Applies to: 8 deep-nesting smells (level = 4) across 5 files.

Invert nested conditionals with `continue` / `return` early-outs;
extract the innermost block into a named helper.

```python
for item in items:
    if not item.active:
        continue
    for child in item.children:
        if not child.valid:
            continue
        _process_child(item, child)
```

### Pattern C: Duplication → shared fixture or helper

Test code (PR 2A): extract duplicated dict literals and setup boilerplate
to `tests/conftest.py` fixtures.

Non-test code (PR 2B `validate_tech_spec` ↔ `validate_roadmap`,
PR 2C `check_fips_compatibility.py` internal twins): extract the shared
body into a parameterized helper.

```python
def _validate_doc(content, filepath, *, name, word_range, required_sections):
    issues = []
    word_count = count_words(content)
    if not (word_range[0] <= word_count <= word_range[1]):
        issues.append(f"{name}: word count {word_count} outside {word_range}")
    for section in required_sections:
        if section not in content:
            issues.append(f"{name}: missing section '{section}'")
    return issues
```

### Pattern D: Many returns → guard clauses + single happy-path return

Applies to: 6 many-returns smells (count = 5) across 4 files.

Collapse early-returns that share a return type into guard clauses for
invalid input plus a single computed final return.

```python
def _signatures_enforced(rules: dict) -> bool:
    if not rules or "signatures" not in rules:
        return False
    sig = rules["signatures"]
    return bool(sig.get("enabled")) and sig.get("scope") == "all"
```

**Exception:** if the function's early-returns form a distinct validation
chain where each return is a different failure mode that needs different
error reporting, use Pattern A (dispatch) instead. Collapsing genuine
validation chains to single-return often reduces clarity.

### Anti-patterns explicitly forbidden in this work

- `# noqa`, `# qlty-ignore`, `# type: ignore`
- Threshold relaxations in `[language.python.smells]`
- `try/except` wrappers added solely to flatten nesting
- Splitting a function into two functions of cc=11 each just to dodge
  the threshold (this is metric-gaming, not maintainability)

## Testing and Rollback Strategy

### Per-PR gating (all PRs)

1. `pytest` full suite green
2. `pre-commit run --all-files` clean
3. `qlty smells --all` delta matches the predicted reduction for that
   PR within ±1. A surprise means the refactor moved a smell rather
   than killing it
4. `qlty metrics --all` duplication trending down for dup-touching
   PRs; non-regressing for others
5. **For 2C/2D/2E only:** dry-run the script against a representative
   repo and diff output against a pre-refactor baseline. Output must
   be byte-identical. Any intentional output change requires its own
   PR, not bundled with the refactor

### Test-add-before-refactor rule (PRs 2C, 2D, 2E)

Each high-risk PR has at least two commits:

```text
commit 1: test: add coverage for <function> behavior
commit 2: refactor: decompose <function> into helpers
```

Commit 1 lands against the unrefactored code and proves it tests the
right behavior (tests pass on `main`). Commit 2 is the refactor; if
commit-1 tests fail after commit 2, the refactor is wrong and reviewers
catch it immediately.

Existing test coverage to build on:

- `tests/unit/_load_check_repo_compliance.py` → starting point for 2D
- `tests/integration/test_compliance_log_append.py` and
  `tests/unit/test_compliance_log_common.py` → starting point for 2E
- `tests/unit/test_apply_williaby_repo_rulesets.py` → starting point
  for 2A

**Gap:** `scripts/check_fips_compatibility.py` (PR 2C) has no test
coverage in the residual list. Commit 1 of 2C must build a fixture-based
AST test suite from scratch: run the walker against a directory of
known-good and known-bad sample Python files and snapshot the findings.

### Rollback

- Every PR reverts via `git revert <merge-commit>` if a regression is
  found within 48 hours
- High-risk PRs (2C/2D/2E) get a post-merge soak window: the next PR
  in the sequence does not merge for at least 48 hours
- If 2D breaks compliance scoring fleet-wide, the revert restores
  pre-refactor behavior immediately. The added test coverage (commit 1)
  stays, since those tests are useful regardless

### Final verification (after 2G merges)

```bash
qlty smells --all              # expect <= 5
qlty metrics --all             # expect duplication <= 5%
pytest                         # green
pre-commit run --all-files     # clean
```

Any residual smell above the target requires a follow-up PR (Approach 2
commits to zero `qlty-ignore`). Realistically, a function might land at
cc=13 after refactor when the threshold is 12; the follow-up decides
case-by-case whether a further split is genuinely clearer or whether
the residual is the right answer.

## Timeline

```text
Week 1:   [ Phase 1: Config fix ] -> merge -> 523 -> ~50

Week 1-2: [ 2A: Test fixtures ]  --+  parallel
          [ 2G: Many-returns ]   --+  (low risk, no soak)
          [ 2B: Skill validators]--+

Week 2:   [ 2F: Doc audit etc. ]    (can overlap with 2B)

Week 3:   [ 2C: FIPS AST walker ]   high risk
            +-> 48h soak +->
Week 3-4: [ 2D: Repo compliance ]   high risk
            +-> 48h soak +->
Week 4:   [ 2E: Compliance log ]    high risk
            +-> 48h soak +->
Week 4-5: Final verification + cleanup
```

### Effort by PR

| PR | Coding | Testing | Soak | Total |
|---|---|---|---|---|
| 1 | 30 min | 1h verify | 0 | ½ day |
| 2A | 1 day | ½ day | 0 | 1½ days |
| 2B | 1 day | 1 day | 0 | 2 days |
| 2C | 2 days | 2 days (build AST test suite from scratch) | 2 days | 6 days |
| 2D | 2 days | 1½ days | 2 days | 5½ days |
| 2E | 2 days | 1½ days | 2 days | 5½ days |
| 2F | 1½ days | 1 day | 0 | 2½ days |
| 2G | ½ day | ½ day | 0 | 1 day |

**Wall-clock estimate:** 4-5 weeks if one person works the high-risk
PRs sequentially. Compresses to ~3 weeks if 2A/2B/2F/2G are batched
during 2C/2D/2E soak windows. Cannot compress further without violating
the soak window rule.

## Open Questions / Known Unknowns

1. PR 2C effort (6 days) has the highest uncertainty since it builds a
   FIPS test suite from scratch. Could stretch to 8 days if the rule
   set is denser than the visit_Call cc=51 metric suggests
2. The ≤ 5 final smell target may be optimistic for AST walkers; some
   functions are inherently complex (state machines). If we land at
   8-10 residual with documented inherent-complexity reasons, that may
   be the right stopping point even under Approach 2's no-ignore rule
3. The byte-identical output check for compliance scripts may be too
   strict for benign reorderings (YAML key order, dict iteration
   order). If a refactor surfaces this, the PR adds a normalized-output
   comparator rather than relaxing the check
