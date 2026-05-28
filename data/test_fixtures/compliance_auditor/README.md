# Compliance Auditor Regression Fixtures

Each `defect_*` subdirectory is a minimal fake repo seeded with exactly one
known defect. The compliance auditor MUST produce a FAIL finding for the named
check when run against that directory. The `control/` directory is the clean
baseline and MUST produce PASS for every check the suite covers.

Every defect fixture is a copy of `control/` with one element removed or
corrupted, so the control-vs-defect diff isolates the single failure.

## Why this exists

Manifest `verify` fields are natural-language hints interpreted by LLM
subagents, not executable DSL. Audit logic can therefore degrade silently: a
reworded `verify` field or an agent-prompt change can make the auditor
interpret a check too leniently, producing false negatives (non-compliant repos
that look compliant) with no code change to trigger an alarm. This corpus
catches that drift by asserting the auditor still fails a known-bad repo.

## Contract

- `control/`: auditor must PASS every covered check.
- `defect_<CHECK_ID>/`: auditor must FAIL `<CHECK_ID>` (and only that check).

## Covered checks

| Fixture            | Check   | Seeded defect                                                        |
| ------------------ | ------- | -------------------------------------------------------------------- |
| `defect_FOUND-001` | FOUND-001 | `SECURITY.md` removed                                              |
| `defect_FOUND-002` | FOUND-002 | `CONTRIBUTING.md` removed                                          |
| `defect_CI-028`    | CI-028  | A `required_status_checks` entry in the org ruleset omits `integration_id: 15368` |
| `defect_CI-043`    | CI-043  | A workflow combines a `pull_request_target` trigger with `actions/checkout` of untrusted PR head |
| `defect_CI-061`    | CI-061  | Renovate Docker image uses a floating `:latest` tag, not a `@sha256:` digest pin |
| `defect_CI-018`    | CI-018  | `release.yml` has no SLSA provenance job calling `slsa-framework/slsa-github-generator` |

> Note: CI-028 covers ruleset `integration_id` pinning, not workflow script
> injection. Script-injection-style danger (privileged trigger plus checkout of
> untrusted code) is CI-043. Earlier drafts of this corpus conflated the two;
> verify each fixture against `docs/standards-manifest.yaml` before trusting it.

## How it is run

Two layers, deliberately separated:

1. **Structural seeding tests** (`tests/integration/test_auditor_regression.py`)
   run in every CI Gate pass. They assert each fixture still contains (or lacks)
   the expected content, so an accidental edit that un-seeds a defect is caught
   immediately. They are deterministic and require no API calls.
2. **Auditor regression run** (`scripts/run-auditor-regression.sh`) invokes the
   local auditor (`scripts/check-repo-compliance.py --local-path ... --check-id
   ... --output json`) against each fixture and asserts the expected PASS/FAIL.
   It runs weekly and on any manifest or agent-prompt change, not in the standard
   CI Gate.

## Exclusions

These fixtures intentionally violate standards, so they are excluded from every
quality gate:

- ruff: `data/test_fixtures/compliance_auditor` in `[tool.ruff] exclude` (also
  irrelevant: no `.py` files here).
- basedpyright: `include = ["src"]` already scopes it away; the path is also in
  `[tool.basedpyright] exclude`.
- bandit: `targets = ["src"]` and `data/` is not scanned.
- coverage: `testpaths = ["tests"]` excludes `data/`.
- pip-audit: no Python packages here.
- qlty: `**/data/**` is in `.qlty/qlty.toml` `exclude_patterns`.
- yamllint / markdownlint: the fixture path is listed in their ignore configs.

## Adding fixtures

1. Confirm the target check's `verify` field in `docs/standards-manifest.yaml`.
   Copy the exact check ID; do not guess.
2. Copy `control/` into `defect_<CHECK_ID>/`.
3. Introduce exactly one defect matching that `verify` field.
4. Add a structural assertion to
   `tests/integration/test_auditor_regression.py`.
5. Add a `run_check` line to `scripts/run-auditor-regression.sh`.
6. Teach `scripts/check-repo-compliance.py` to evaluate the check locally if it
   does not already.
7. Verify the auditor fails the defect and passes the control.
