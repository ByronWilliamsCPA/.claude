# 04 - Architecture and Structure

The dominant structural problem is an inverted package boundary: the only importable module (`src/claude_config`, 132 LOC) is imported by nothing, while the 6,490 LOC of real compliance, ruleset, and audit logic in `scripts/` is unpackaged and reachable only via `pythonpath` plus per-file `sys.path.insert` hacks. With no shared package, core helpers are re-implemented per script (a `gh` client appears six-plus times). No circular imports were found; the local import graph is a clean DAG and `compliance_log_common.py` is one correctly-extracted shared helper. The subagent reported two additional Low-severity items whose detail did not survive transit; they are omitted here rather than recorded without evidence.

## ARCH-01 - Inverted package boundary: real logic lives outside the only package

- Severity: High
- Effort: L (move `scripts/` logic into the `claude_config` package, add entry points, rewire imports and tests; basis: ~6.5K LOC restructure)
- Evidence: `pyproject.toml:137` ships `packages = ["src/claude_config"]` (132 LOC: a pydantic `Settings` plus a structlog wrapper), imported by nothing. The 6,490 LOC of actual logic in `scripts/` is unpackaged, reachable only through `pyproject.toml:457` `pythonpath = [".", "src"]` and per-file `sys.path.insert` calls (`scripts/compliance_log_append.py:36`, `compliance_rollup_reconcile.py:26`, `compliance_log_render.py:19`).
- Recommendation: Promote the script logic into `src/claude_config/` submodules with console-script entry points, so the code is importable, testable, and coverage-measurable as a unit. This is the root cause behind ARCH-02, ARCH-04, and CQ-01.

## ARCH-02 - The `gh` API client is re-implemented six-plus times

- Severity: High
- Effort: M (extract one client module and route all call sites; basis: cross-file refactor with test updates)
- Evidence: A `gh`-subprocess-plus-JSON client is duplicated across `check-repo-compliance.py:141` and `:159`, `check-required-checks.py:629`, `setup_org_rulesets.py:171` and `:209`, `setup_repo_rulesets.py:34` and `:89`, `sync_org_pins.py:65`, and `populate-github-repos.py:75`. `check_quality_gate.py:31-45` solves the same problem a different way using `urllib`.
- Recommendation: Extract a single `gh_api_common.py` (mirroring the existing `compliance_log_common.py` pattern) and migrate every call site. Folds in CQ-02.

## ARCH-03 - Skills spawn agents, violating the repo's own Command->Agent->Skill rule

- Severity: High
- Effort: M (rework the two skills to return work to the orchestrator instead of spawning; basis: two skill rewrites plus doc reconciliation)
- Evidence: `.claude/rules/supervisor.md:131` and ADR-004 state "Skills do not invoke agents." Two skills break it: `.claude/skills/test-coverage/SKILL.md:54` and `.claude/skills/pr-review/workflows/pr-review.md:691` both spawn subagents.
- Recommendation: Either refactor the two skills to a Pattern-B output-only shape, or amend ADR-004 and supervisor.md if skill-spawned subagents are now intended. The rule and the code must agree, since the repo's own tooling cites this boundary.

## ARCH-04 - `sys.path.insert` bootstrapping hacks across compliance scripts

- Severity: Medium
- Effort: S (removed once ARCH-01 lands; basis: deletions, not new code)
- Evidence: Three compliance scripts mutate `sys.path` at import time to find their shared module: `compliance_log_append.py:36`, `compliance_rollup_reconcile.py:26`, `compliance_log_render.py:19`. This is the runtime symptom of the missing package boundary (ARCH-01).
- Recommendation: Delete these inserts after ARCH-01 packages the logic. Until then they are a fragile import mechanism that breaks under any CWD change.

## ARCH-05 - Two YAML libraries in use across the same code layer

- Severity: Medium
- Effort: M (standardize on one library; basis: audit every load/dump call and migrate)
- Evidence: `scripts/` and `tools/` import PyYAML in 2 files and `ruamel.yaml` in 3. Two parsers with different round-trip and safety semantics solve one problem.
- Recommendation: Pick one (ruamel for round-trip preservation, PyYAML safe-load for read-only parsing) and document the choice in a rule. Mixed parsers cause subtle formatting and quoting drift.

## ARCH-06 - `ORGS` constant duplicated as divergent literals

- Severity: Medium
- Effort: S (move to one shared constant; basis: one definition plus two import edits)
- Evidence: `scripts/check-repo-compliance.py:34` defines `ORGS = ["ByronWilliamsCPA", "williaby"]` (list); `scripts/populate-github-repos.py:36` defines `ORGS: tuple[str, ...] = ("ByronWilliamsCPA", "williaby")` (tuple). Same data, two declarations, divergent types; they will drift.
- Recommendation: Define `ORGS` once in a shared config module and import it. Pairs with the ARCH-01 packaging fix.

## Clean areas

- No circular imports; the local import graph is a clean DAG.
- `compliance_log_common.py` is a correctly-extracted shared helper and the model the other duplications should follow.

## Machine-readable findings

```json
[
  {"id": "ARCH-01", "title": "Inverted package boundary: real logic lives outside the only package", "domain": "architecture", "severity": "High", "effort": "L", "files": ["pyproject.toml", "scripts/"], "evidence": "pyproject.toml:137 packages=[\"src/claude_config\"] (132 LOC, imported by nothing); 6490 LOC in scripts/ unpackaged, reached via pyproject.toml:457 pythonpath + sys.path.insert in compliance_log_append.py:36, compliance_rollup_reconcile.py:26, compliance_log_render.py:19", "recommendation": "Promote script logic into src/claude_config submodules with console-script entry points so it is importable, testable, and coverage-measurable.", "cve": ""},
  {"id": "ARCH-02", "title": "The gh API client is re-implemented six-plus times", "domain": "architecture", "severity": "High", "effort": "M", "files": ["scripts/check-repo-compliance.py", "scripts/check-required-checks.py", "scripts/setup_org_rulesets.py", "scripts/setup_repo_rulesets.py", "scripts/sync_org_pins.py", "scripts/populate-github-repos.py", "scripts/check_quality_gate.py"], "evidence": "gh client duplicated at check-repo-compliance.py:141/159, check-required-checks.py:629, setup_org_rulesets.py:171/209, setup_repo_rulesets.py:34/89, sync_org_pins.py:65, populate-github-repos.py:75; check_quality_gate.py:31-45 uses urllib instead", "recommendation": "Extract one gh_api_common.py (mirroring compliance_log_common.py) and migrate every call site.", "cve": ""},
  {"id": "ARCH-03", "title": "Skills spawn agents, violating the repo's Command->Agent->Skill rule", "domain": "architecture", "severity": "High", "effort": "M", "files": [".claude/skills/test-coverage/SKILL.md", ".claude/skills/pr-review/workflows/pr-review.md", ".claude/rules/supervisor.md"], "evidence": "supervisor.md:131 and ADR-004 state skills do not invoke agents; test-coverage/SKILL.md:54 and pr-review/workflows/pr-review.md:691 both spawn subagents", "recommendation": "Refactor the two skills to output-only, or amend ADR-004 and supervisor.md so the rule and code agree.", "cve": ""},
  {"id": "ARCH-04", "title": "sys.path.insert bootstrapping hacks across compliance scripts", "domain": "architecture", "severity": "Medium", "effort": "S", "files": ["scripts/compliance_log_append.py", "scripts/compliance_rollup_reconcile.py", "scripts/compliance_log_render.py"], "evidence": "sys.path.insert at compliance_log_append.py:36, compliance_rollup_reconcile.py:26, compliance_log_render.py:19; runtime symptom of the missing package boundary", "recommendation": "Delete these inserts after ARCH-01 packages the logic; they break under any CWD change.", "cve": ""},
  {"id": "ARCH-05", "title": "Two YAML libraries in use across the same code layer", "domain": "architecture", "severity": "Medium", "effort": "M", "files": ["scripts/", "tools/"], "evidence": "PyYAML imported in 2 files, ruamel.yaml in 3, across scripts/ and tools/; two parsers with different semantics for one job", "recommendation": "Standardize on one YAML library and document the choice in a rule.", "cve": ""},
  {"id": "ARCH-06", "title": "ORGS constant duplicated as divergent literals", "domain": "architecture", "severity": "Medium", "effort": "S", "files": ["scripts/check-repo-compliance.py", "scripts/populate-github-repos.py"], "evidence": "check-repo-compliance.py:34 ORGS list vs populate-github-repos.py:36 ORGS tuple; same data, divergent types", "recommendation": "Define ORGS once in a shared config module and import it.", "cve": ""}
]
```
