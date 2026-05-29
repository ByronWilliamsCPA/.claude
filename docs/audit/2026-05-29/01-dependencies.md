# 01 - Dependencies and Supply Chain

Supply chain is healthy. `uv lock --locked` resolved 200 packages with zero drift, every row carries SHA-256 hashes, and all direct dependencies sit on current 2025-2026 releases. No migration residue, no Dockerfiles, no stale base images. Four low-severity items remain: a Python floor that reaches EOL in five months, one stale dev-only transitive (already ignored with a documented reason), unverifiable submodule pins, and a Renovate grouping rule that never matches.

## DEP-01 - Python 3.10 floor reaches EOL in five months

- Severity: Low
- Effort: S (single-line edit to `requires-python` plus a CI matrix trim; basis: one config change, test matrix already covers 3.11-3.14)
- Evidence: `pyproject.toml` `requires-python = ">=3.10,<3.15"` and `target-version = "py310"`. CPython 3.10 security support ends 2026-10, roughly five months from 2026-05-29.
- Recommendation: Plan a floor bump to `>=3.11` in Q4 2026 once 3.10 is EOL. This unlocks newer typing syntax without runtime guards.

## DEP-02 - Stale dev-only transitive `py` 1.11.0

- Severity: Low
- Effort: S (no action required beyond the existing ignore; basis: already mitigated)
- Evidence: `uv.lock` pins transitive `py` 1.11.0, last released 2021-11-04 (4.5 years). Pulled dev-only via `interrogate`. Already suppressed with a documented reason (PYSEC-2022-42969, disputed and unreachable in this usage).
- Recommendation: Leave as-is. Drop the dependency if `interrogate` releases a version that no longer requires `py`.

## DEP-03 - Submodule pin freshness unverifiable in this tree

- Severity: Low
- Effort: M (requires a full recursive checkout plus per-upstream release comparison for the 3 third-party modules; basis: 7 submodules, network fetch per module)
- Evidence: `.gitmodules` declares 7 submodules under `.submodules/`; all are uninitialized in this working tree, so commit-pin currency cannot be checked here. Three point at third-party upstreams (obra/superpowers, rebelytics/one-skill-to-rule-them-all, Jeffallan/claude-skills).
- Recommendation: Run `git submodule update --init --remote --recursive` in a maintenance pass and compare pinned SHAs to upstream HEAD; flag any third-party module with no upstream commit in 12+ months.

## DEP-04 - Renovate dev-dependency grouping rule never matches

- Severity: Low
- Effort: S (one-field correction in `renovate.json`; basis: single rule edit)
- Evidence: `renovate.json` packageRule targets `matchDepTypes: ["tool.uv.dev-dependencies"]`, but this project declares dev dependencies under `[project.optional-dependencies].dev` in `pyproject.toml`. The rule never matches, so dev-dependency PRs land ungrouped.
- Recommendation: Change the rule to `matchDepTypes: ["optional-dependencies"]` (or the Renovate dep-type Renovate assigns to PEP 621 optional groups) so dev bumps batch into one PR.

## Clean areas

- Lockfile health: `uv lock --locked` resolved 200 packages with zero drift; 1364 hash lines across 398 wheel and sdist rows; security overrides `idna>=3.15` and `pymdown-extensions>=10.21.3` present and resolved.
- Migration residue: none (no `requirements*.txt`, `setup.py`, `setup.cfg`, `poetry.lock`, or `Pipfile`).
- Base images: no Dockerfiles, so no stale base-image pins.
- SBOM and dependency-review: `.github/workflows/sbom.yml` and `dependency-review.yml` are SHA-pinned and correctly configured.

## Machine-readable findings

```json
[
  {"id": "DEP-01", "title": "Python 3.10 floor reaches EOL in five months", "domain": "dependencies", "severity": "Low", "effort": "S", "files": ["pyproject.toml"], "evidence": "pyproject.toml requires-python = \">=3.10,<3.15\", target-version py310; CPython 3.10 EOL 2026-10", "recommendation": "Bump floor to >=3.11 in Q4 2026 after 3.10 EOL; CI matrix already covers 3.11-3.14.", "cve": ""},
  {"id": "DEP-02", "title": "Stale dev-only transitive py 1.11.0", "domain": "dependencies", "severity": "Low", "effort": "S", "files": ["uv.lock"], "evidence": "uv.lock pins py 1.11.0 (released 2021-11-04), dev-only via interrogate; already ignored, PYSEC-2022-42969 disputed/unreachable", "recommendation": "Leave as-is; drop when interrogate no longer requires py.", "cve": ""},
  {"id": "DEP-03", "title": "Submodule pin freshness unverifiable in this tree", "domain": "dependencies", "severity": "Low", "effort": "M", "files": [".gitmodules"], "evidence": ".gitmodules declares 7 submodules, all uninitialized in this tree; 3 are third-party upstreams", "recommendation": "Init submodules and compare pinned SHAs to upstream HEAD; flag any third-party module with no commit in 12+ months.", "cve": ""},
  {"id": "DEP-04", "title": "Renovate dev-dependency grouping rule never matches", "domain": "dependencies", "severity": "Low", "effort": "S", "files": ["renovate.json", "pyproject.toml"], "evidence": "renovate.json matchDepTypes [\"tool.uv.dev-dependencies\"] but dev deps live under [project.optional-dependencies].dev", "recommendation": "Correct matchDepTypes to the PEP 621 optional-dependencies dep-type so dev bumps group into one PR.", "cve": ""}
]
```
