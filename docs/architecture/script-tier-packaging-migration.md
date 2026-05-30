---
title: "Script-Tier Packaging Migration (ARCH-01)"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Design for relocating the scripts tier into the claude_config package."
tags:
  - architecture
  - packaging
---

> Status: Proposed | Design doc | Author: audit remediation | Date: 2026-05-29
> Tracks finding ARCH-01 from `docs/audit/2026-05-29/`. Resolves ARCH-01, ARCH-02,
> ARCH-04, ARCH-05, ARCH-06, CQ-01, and CQ-02.

## 1. Problem

The runnable logic of this repo (6,490 LOC across 18 files) lives in `scripts/`, outside
the only packaged module (`src/claude_config`, 132 LOC). Consequences: 6,490 LOC are not in
the coverage source (`pyproject.toml:484` `source = ["src"]`), the `gh` client is
re-implemented six-plus times, two YAML libraries and a duplicated `ORGS` constant coexist,
six files have hyphenated names that cannot be imported (forcing `importlib` file-loaders in
tests), and three compliance scripts carry `sys.path.insert` hacks to reach a sibling helper.

## 2. The hard constraint that shapes the fix

This repo is the global control point. `setup.sh` installs it by symlink only:
`setup.sh:381` runs `ln -sfn $REPO_DIR/scripts ~/.claude/scripts`. There is no
`pip install`, `uv pip install`, or `uv sync` of the `claude-config` package anywhere in
`setup.sh`, and `src/` is not symlinked into `~/.claude`. Every hook and permission entry
invokes scripts by absolute path, for example `hooks.json:96`
`python3 $HOME/.claude/scripts/pr-review-reminder.py` and the `.claude/settings.json`
allowlist entries for `compliance_log_render.py`, `compliance_rollup_reconcile.py`, and
`compliance_log_append.py`.

Confirmed against current Claude Code docs (https://code.claude.com/docs/en/hooks and
/plugins-reference, 2026-05-29): hook and skill commands run in a plain shell with no
injected `PYTHONPATH`, no virtualenv, no `uv run` wrapper, and no PEP 723 support. Plugins
are file-copied, not installed. There is no supported mechanism for a hook to declare or
install Python dependencies.

Therefore:

- `[project.scripts]` console entry points and `python -m claude_config.x` resolve only
  where the package is installed (dev machine, CI after `uv sync`). They would break every
  downstream instance, which only symlinks files.
- The downstream contract must remain: a file that physically exists at
  `~/.claude/scripts/<name>.py`, invoked by path, that resolves its own imports.

## 3. Decision

Move the logic into `src/claude_config/` subpackages. Keep the executable entrypoints as
thin path-invoked shim files in `scripts/`, with their current filenames unchanged
(hyphens included), so no hook, allowlist, or workflow path changes. Add `[project.scripts]`
console entry points as an optional convenience for installed and CI use only.

Each shim resolves the package through the symlink without an install:

```python
# scripts/pr-review-reminder.py  (filename unchanged; hooks.json:96 keeps working)
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from claude_config.reminders.pr_review import main

if __name__ == "__main__":
    raise SystemExit(main())
```

`Path(__file__).resolve()` follows the `~/.claude/scripts` symlink to the real checkout, so
`parents[1] / "src"` is the real `src/`. This is the same bootstrap already present at
`compliance_log_append.py:36`, repointed from repo root to `src/`. Dependency availability
is unchanged: the shim imports the same third-party packages the original script did, under
the same `python3`.

`scripts/` gains no `__init__.py`. It stays a directory of standalone files, preserving the
ruff `INP` exemption ("Scripts are not packages"). Only `src/claude_config` subpackages get
`__init__.py`.

### 3.1 Raising relocated code to the strict ruleset (no suppression)

`pyproject.toml:310-324` relaxes a large rule set for `scripts/**` (`ANN`, `D`, `T20`,
`TRY`, `PTH`, `PLR`, `EM`, `BLE`, `C901`, `S603`, `S607`, and more). Code under `src/` gets
the full strict ruleset with no such relaxation. Relocation therefore raises every moved
file to library grade. This is the chosen approach: bring the code up, do not add a
per-file ignore for the moved subtree. Suppression is barred by the repo code-quality rule.

Measured gap (logging cluster of 4 files, linted under the effective `src/` ruleset): 24
errors, of which 10 are `T201` (`print`), 5 are complexity (`C901`, `PLR0912`, `PLR0915`),
3 are `EM102`, 2 are `S603`, plus `PTH`/`ANN`. Repo-wide there are 139 `print()` calls
across 16 of 18 scripts, so the print conversion and the complexity refactors, not the file
move, are the dominant work.

Conventions for the raise:

- Output. Replace `print()` per its role. Diagnostic and progress messages go through the
  structlog logger in `src/claude_config/utils/logging.py` (stderr). Genuine stdout payloads
  (rendered Markdown, JSON results) use a `rich.console.Console` writer (`rich>=13.5.0` is
  already a dependency); `Console.print` is not the builtin and does not trip `T201`. Tools
  that already write their product to a file keep doing so.
- Complexity. Functions over `C901` (10), `PLR0912` (12 branches), or `PLR0915` (50
  statements) are decomposed into named helpers. This is real refactoring, reviewed per
  function, not a mechanical move.
- Exceptions. `EM102`/`TRY` fixes assign the message to a variable before `raise`; `BLE`
  blind excepts are narrowed to typed exceptions (see `.claude/rules/python.md`).
- Subprocess. `S603`/`S607` calls (the `gh` and `python` invocations) are not exempt under
  `src/`. Centralize them in `common/gh.py` and `common/proc.py` with one reviewed
  `# noqa: S603` carrying a justification at the single call site, rather than scattering
  the call (and the suppression) across modules. This is the documented-suppression
  exception in the code-quality rule, not a blanket dodge.
- Docstrings and types. Full `ANN` signatures and Google-style `D` docstrings; `darglint`
  validates that `Args`/`Returns`/`Raises` match the signature; `interrogate` holds `src/`
  at 80%.

## 4. Target layout

```text
src/claude_config/
  common/            # NEW shared layer (folds in ARCH-02, ARCH-05, ARCH-06)
    __init__.py
    gh.py            # one gh-subprocess + JSON client, replaces 6+ copies
    proc.py          # single justified S603 subprocess wrapper
    yaml_io.py       # one YAML load/dump path (standardize on ruamel)
    orgs.py          # single ORGS constant
    output.py        # rich.Console writer for stdout payloads (replaces print)
  compliance/
    __init__.py
    log_common.py    repo_check.py     required_checks.py
    log_append.py    log_render.py     rollup_reconcile.py
  rulesets/
    __init__.py
    setup_org.py     setup_repo.py     sync_org_pins.py
  catalog/
    __init__.py
    populate_repos.py  python_tier_repos.py  workflow_registry.py
  checks/
    __init__.py
    quality_gate.py  type_hints.py  fips_compatibility.py  assuredoss.py
  docs/
    __init__.py
    doc_audit.py
  reminders/
    __init__.py
    pr_review.py
```

The hatch wheel target (`pyproject.toml:136-137`, `packages = ["src/claude_config"]`) picks
up new subpackages automatically. Coverage `source = ["src"]` measures them automatically,
which closes CQ-01 with no config change.

## 5. File-by-file mapping (all 18 scripts)

Every runnable script keeps a same-named shim in `scripts/`. `compliance_log_common.py` is
helper-only (no `main()`), so it has no shim and no entry point.

| Current `scripts/` file | LOC | New module | Shim kept? | Entry point |
| --- | --- | --- | --- | --- |
| check-repo-compliance.py | 745 | compliance/repo_check.py | yes | claude-check-repo-compliance |
| check-required-checks.py | 872 | compliance/required_checks.py | yes | claude-check-required-checks |
| compliance_log_common.py | 150 | compliance/log_common.py | no (helper) | none |
| compliance_log_append.py | 266 | compliance/log_append.py | yes | claude-compliance-log-append |
| compliance_log_render.py | 173 | compliance/log_render.py | yes | claude-compliance-log-render |
| compliance_rollup_reconcile.py | 513 | compliance/rollup_reconcile.py | yes | claude-compliance-rollup-reconcile |
| setup_org_rulesets.py | 426 | rulesets/setup_org.py | yes | claude-setup-org-rulesets |
| setup_repo_rulesets.py | 136 | rulesets/setup_repo.py | yes | claude-setup-repo-rulesets |
| sync_org_pins.py | 196 | rulesets/sync_org_pins.py | yes | claude-sync-org-pins |
| populate-github-repos.py | 389 | catalog/populate_repos.py | yes | claude-populate-github-repos |
| generate_python_tier_repos.py | 60 | catalog/python_tier_repos.py | yes | claude-generate-python-tier-repos |
| seed-reusable-workflow-registry.py | 137 | catalog/workflow_registry.py | yes | claude-seed-workflow-registry |
| check_quality_gate.py | 369 | checks/quality_gate.py | yes | claude-check-quality-gate |
| check_type_hints.py | 381 | checks/type_hints.py | yes | claude-check-type-hints |
| check_fips_compatibility.py | 533 | checks/fips_compatibility.py | yes | claude-check-fips-compatibility |
| validate_assuredoss.py | 176 | checks/assuredoss.py | yes | claude-validate-assuredoss |
| doc-audit.py | 794 | docs/doc_audit.py | yes | claude-doc-audit |
| pr-review-reminder.py | 174 | reminders/pr_review.py | yes | claude-pr-review-reminder |

All 17 runnable scripts already expose `def main(` plus a `__main__` guard (verified
2026-05-29), so the shim contract `raise SystemExit(main())` requires no signature change to
the logic. `main()` keeps reading `sys.argv` as it does today.

## 6. Shared layer API (folds in ARCH-02, ARCH-05, ARCH-06)

`common/gh.py`: one client extracted from `check-repo-compliance.py:141/159`,
`check-required-checks.py:629`, `setup_org_rulesets.py:171/209`, `setup_repo_rulesets.py:34/89`,
`sync_org_pins.py:65`, `populate-github-repos.py:75`, and the `urllib` variant at
`check_quality_gate.py:31-45`. Minimum surface:

```python
def gh(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]: ...
def gh_json(args: list[str]) -> Any: ...           # run + parse JSON
def gh_paginated(args: list[str]) -> list[Any]: ... # --paginate aggregation
```

`common/yaml_io.py`: standardize on ruamel (the safe-load path already used in tests). Drop
PyYAML from the script layer.

`common/orgs.py`: `ORGS: tuple[str, ...] = ("ByronWilliamsCPA", "williaby")`, replacing the
divergent literals at `check-repo-compliance.py:34` (list) and `populate-github-repos.py:36`
(tuple).

## 7. Test and config changes

- Delete the `importlib` file-loaders once the modules are importable:
  `tests/unit/_load_check_required_checks.py`, `_load_check_repo_compliance.py`,
  `_load_check_fips_compatibility.py`, `_load_populate_github_repos.py`,
  `_importlib_loader.py`, and the `spec_from_file_location` calls in
  `tests/integration/test_scripts.py` and `tests/unit/test_validate_planning_docs.py`.
  Replace with direct `from claude_config.<pkg>.<mod> import ...`.
- Rewrite `from scripts.compliance_log_common import ...`
  (`compliance_log_append.py:38`, `compliance_log_render.py:21`,
  `compliance_rollup_reconcile.py:28`) to `from claude_config.compliance.log_common import ...`.
  The `sys.path.insert(parent.parent)` lines in those three files are deleted; the only
  remaining `sys.path` line lives in the shim.
- `pyproject.toml`: add `[project.scripts]` with the 17 entry points from the mapping table.
  No change to `[tool.coverage.run] source`; it already reads `["src"]`.
- `noxfile.py:298,428`: switch `session.run("python", "scripts/...py")` to the entry-point
  console scripts (CI installs the package).

## 8. Call-site impact

| Caller | Changes? | Why |
| --- | --- | --- |
| `hooks.json` (pr-review-reminder.py and bash hooks) | no | shim keeps the path and name |
| `.claude/settings.json` allowlist (3 compliance scripts) | no | shim keeps the 3 filenames |
| CI workflows invoking `python scripts/x.py` (4 files) | optional | may switch to entry points under `uv run`, or leave path calls; both work in CI |
| `noxfile.py` (2 calls) | yes | switch to entry points |
| Tests | yes | drop file-loaders, import the package |
| Downstream instances (symlink only) | no | path-invoked shims unchanged |

## 9. Phased PR plan

Because the move raises each file to strict (section 3.1), per-PR size is set by the print
conversion and complexity refactors, not the file move. Clusters are sized to keep each PR
reviewable; the two largest check scripts get their own PR. Each PR leaves the tree green.

1. PR 1a, foundation plus logging pilot. Add `common/` scaffolding (`gh.py`, `proc.py`,
   `yaml_io.py`, `orgs.py`, `output.py`) and migrate the compliance logging cluster
   (`log_common`, `log_render`, `log_append`, `rollup_reconcile`) to strict, with shims.
   These are the 3 allowlisted scripts plus the helper, the truest cascade test. Measured
   gap: 24 ruff errors to clear.
2. PR 1b, compliance checks. `repo_check` (745 LOC) and `required_checks` (872 LOC) through
   `common/gh.py`. Largest complexity-refactor load; isolated so its diff is reviewable.
3. PR 2, rulesets. `setup_org`, `setup_repo`, `sync_org_pins` through `common/gh.py`.
4. PR 3, catalog and checks. `populate_repos`, `python_tier_repos`, `workflow_registry`,
   `quality_gate`, `type_hints`, `fips_compatibility`, `assuredoss`.
5. PR 4, docs and cleanup. `doc_audit`, `pr_review`; delete all `importlib` loaders; add
   `[project.scripts]`; switch `noxfile.py` to entry points.

## 10. Verification per PR

- `uv run ruff check src/claude_config/<pkg>` clean under strict (zero errors, no added
  per-file ignore for the subtree); `uv run basedpyright src/claude_config/<pkg>` clean.
- `uv run pytest` green; coverage reported for the migrated modules (expected to rise from
  the src-only baseline of 132 LOC).
- `pre-commit run --all-files` green (ruff, basedpyright, interrogate at 85% on `scripts/`
  and 80% on `src/`, darglint on `src/`).
- Output behavior preserved: capture stdout of the old script and the new entrypoint on a
  representative input and diff them, so the print-to-Console/logger conversion did not move
  a payload from stdout to stderr or vice versa.
- Downstream smoke test: for each migrated shim, run `python3 scripts/<name>.py --help`
  (bare interpreter, by path, not via entry point) and confirm imports resolve and exit code
  is 0 or the script's own usage code. This is the test that guarantees the cascade still
  works.
- Confirm `git grep "from scripts\."` returns nothing after PR 4.

## 11. Risks

- A shim's bootstrap fails if `src/` is missing from the checkout. Mitigation: the smoke
  test in section 10; `src/` ships in every clone and is not gitignored.
- A migrated `main()` that relied on `__file__` for repo-relative paths now resolves
  `__file__` inside `src/claude_config/...`. Audit each `Path(__file__)` use during
  migration and repoint to a resolved repo root or a passed argument.
- Downstream `python3` lacking the third-party deps is a pre-existing condition, not new.
  Document the required interpreter in `docs/getting-started/` if not already stated.
- The print conversion can silently relocate output between stdout and stderr, breaking any
  caller that parses a script's stdout. Mitigation: the output-diff check in section 10, and
  routing only diagnostics (not payloads) to the logger.
- Complexity refactors change internal structure of large functions (`repo_check`,
  `required_checks`). Mitigation: these land in their own PR (1b) with the existing tests as
  the behavioral contract; no refactor merges without the prior test suite green.

## 12. Out of scope

`tools/` (5 files, 1,230 LOC, includes the `frontmatter_contract` package and
`validate_front_matter.py` invoked by pre-commit) is a separate cluster. Migrate it as a
follow-up using the same shim pattern once the `scripts/` migration is proven.
