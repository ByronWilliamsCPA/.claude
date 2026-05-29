# 00 - Holistic Legacy and Architecture Audit: Final Report

- Repository: `ByronWilliamsCPA/.claude`
- Commit audited: `bf912e1`
- Date (UTC): 2026-05-29
- Subagent reports: `01-dependencies.md`, `02-legacy-code.md`, `03-code-quality.md`, `04-architecture.md`, `05-security.md`, `06-cicd.md`, `07-docs.md`

## 1. Repo map

| Dimension | Finding |
| --- | --- |
| Type | Claude Code configuration and automation repo: skills, agents, commands, rules, standards, plus a Python tooling tier |
| Size | 689 tracked files; 15,686 Python LOC, 4,640 shell LOC, 85,381 markdown LOC across 350 `.md` files |
| Python layout | `src/claude_config/` is 5 files / 132 LOC; the real logic (6,490 LOC) sits in `scripts/` (18 files) and `tools/` (5 files) |
| Runtime | Python `>=3.10,<3.15`, `target-version = py310`; clean uv setup, no migration residue |
| Build / deps | `uv.lock` (200 packages, SHA-256 hashes, zero drift); 7 git submodules |
| Tests | 54 test files (27 unit, 6 integration, plus fuzz and fips); `pytest` minversion 7.0 |
| CI / tooling | 22 GitHub workflows; large `.pre-commit-config.yaml`; bandit, semgrep, trivy, osv-scanner, codeql, scorecard, slsa, sbom, reuse |
| History | Shallow: 50 commits over 5 days (since 2026-05-24). Git-blame age analysis is uninformative; this is a fresh init carrying a mature config, not an aged codebase |
| Most-churned | `docs/standards-manifest.yaml` (19), `CHANGELOG.md` (16), `.github/workflows/release.yml` (10) |

Subagent team: all seven domains were run. The repo is large and tooling-dense enough that none could be skipped. Architecture lost two Low-severity items in subagent return truncation; they were omitted rather than recorded without evidence.

## 2. Code quality: critical view

Quality hygiene is strong and the weak spots are narrow. `ruff check` passes fully against the house standard (C901 <=10, PLR0912 <=12, PLR0915 <=50, PLR0913 <=5). There are zero real debt markers, every `# type: ignore`, `# noqa`, and `cast` carries a justification, and there are no `assert True` test anti-patterns. That is a genuinely clean surface.

The one structural quality defect is the coverage gate (CQ-01). `pyproject.toml:484` measures only `source = ["src"]`, so `--cov-fail-under=80` certifies 132 lines while the 6,490 LOC that do the actual work go unmeasured. Tests for those scripts exist (283 test functions), so this is a measurement gap, not a testing gap; the gate currently provides false assurance. Beyond that, the quality findings are localized: a `gh` wrapper duplicated across scripts (CQ-02), 61 boundary `Any` annotations (CQ-03), and five tests that assert only by absence of an exception (CQ-04). None of these is severe on its own.

## 3. Architecture: critical view

This is where the repo works against its maintainers. The package boundary is inverted (ARCH-01): the only importable module, `src/claude_config` (132 LOC), is imported by nothing and is the sole content of the wheel, while the 6,490 LOC that matter live in `scripts/` and are reachable only through `pythonpath` and `sys.path.insert` hacks in three files (ARCH-04). Because there is no shared package, the same helper is rebuilt repeatedly: a `gh` client appears six-plus times and once more via `urllib` (ARCH-02), two YAML libraries coexist (ARCH-05), and `ORGS` is declared twice with divergent types (ARCH-06). The import graph itself is a clean DAG with no cycles, and `compliance_log_common.py` proves the maintainer knows how to extract a shared module; the rest of the script tier simply never got the same treatment.

The second architectural concern is convention drift in the config layer. `supervisor.md:131` and ADR-004 state plainly that skills do not invoke agents, yet two skills spawn subagents (ARCH-03). The repo writes standards faster than the code conforms to them.

## 4. Cross-cutting themes

These recur across domains and no single subagent owned them.

1. One root cause, many symptoms. The missing package boundary is the upstream of ARCH-01, ARCH-02, ARCH-04, ARCH-06, CQ-01, and CQ-02. Six findings across two domains collapse into one decision: the script tier was never packaged. Fixing that one thing retires all six.

2. Stated standards outrun conformance. The repo is intensely self-documenting, and reality has drifted from the documentation in at least six places: the merge-queue rules it mandates are not implemented (CICD-01, CICD-02), the skill/agent boundary it defines is violated (ARCH-03), and three count claims are stale (DOC-05 submodules 5 vs 7, DOC-06 permissions 22 vs 30, DOC-07 agent catalog missing three). The governance content is ahead of the artifacts it governs.

3. Committed run artifacts are both cruft and exposure. The two HTML session reports surface independently in the legacy domain (LEG-01, 464KB not gitignored) and the security domain (SEC-01, leaking `/home/byron`, `byron@dadslaptop`, five private repo names, and verbatim session text). One removal closes both.

4. Age does not explain the debt. With only 5 days of history, this is not accreted legacy; it is a mature surface dropped onto a fresh init. The debt is structural-from-birth, which is the good news: there is no decade of coupling to unwind, just a packaging decision to make and a documentation set to reconcile.

5. Divergence, not decay, is the AI-pattern tell. The code is free of the usual AI giveaways (no banned filler, near-zero TODOs, uniform lint). The signature instead is the same problem solved more than one way across files (two YAML libs, the `gh` client six ways, `ORGS` two ways): the fingerprint of multiple generation passes that were never reconciled against each other.

## 5. Prioritized remediation backlog

Sorted by severity, then effort (S before M before L).

| ID | Finding | Domain | Severity | Effort | Files |
| --- | --- | --- | --- | --- | --- |
| CICD-01 | Required-check workflows do not emit on merge_group | cicd | High | S | ci.yml, security-analysis.yml, reuse.yml, pr-validation.yml |
| DOC-01 | README Quick Start omits submodule init and setup.sh | docs | High | S | README.md |
| ARCH-02 | gh API client re-implemented six-plus times | architecture | High | M | scripts/check-repo-compliance.py, check-required-checks.py, setup_org_rulesets.py, +4 |
| ARCH-03 | Skills spawn agents, violating the repo's own rule | architecture | High | M | .claude/skills/test-coverage/SKILL.md, pr-review/workflows/pr-review.md |
| CQ-01 | Coverage gate measures only src/, ~7,700 LOC ungated | code-quality | High | M | pyproject.toml |
| CICD-02 | No merge-queue rule declared despite automerge config | cicd | High | M | docs/reference/repo-rulesets/, scripts/setup_repo_rulesets.py |
| DOC-02 | 83 root-absolute links in AGENTS-AND-SKILLS.md 404 | docs | High | M | AGENTS-AND-SKILLS.md |
| DOC-04 | MkDocs strict build has 85-plus pages not in nav/excluded | docs | High | M | .github/workflows/docs.yml, mkdocs.yml |
| ARCH-01 | Inverted package boundary: real logic outside the package | architecture | High | L | pyproject.toml, scripts/ |
| SEC-01 | Committed HTML session reports expose personal data | security | Medium | S | session-report-20260521-2145.html, session-report-20260521-2204.html |
| LEG-01 | Two session-report HTML files committed at repo root | legacy-code | Medium | S | session-report-*.html, .gitignore |
| ARCH-04 | sys.path.insert bootstrapping hacks in compliance scripts | architecture | Medium | S | scripts/compliance_log_append.py, compliance_rollup_reconcile.py, compliance_log_render.py |
| ARCH-06 | ORGS constant duplicated as divergent literals | architecture | Medium | S | scripts/check-repo-compliance.py, populate-github-repos.py |
| DOC-03 | ADR-008 missing from mkdocs.yml nav | docs | Medium | S | mkdocs.yml |
| DOC-05 | Submodule count and names drift in install docs | docs | Medium | S | docs/getting-started/install.md, README.md |
| DOC-06 | permissions.ask count claim is stale (22 vs 30) | docs | Medium | S | .claude/rules/settings-and-permissions.md, settings.json |
| DOC-07 | Three local agents undocumented; agent count off by one | docs | Medium | S | AGENTS-AND-SKILLS.md, scripts/doc-audit.py |
| ARCH-05 | Two YAML libraries in use across the same layer | architecture | Medium | M | scripts/, tools/ |
| SEC-02 | release.yml missing top-level permissions deny-all | security | Low | S | .github/workflows/release.yml |
| SEC-03 | Bare except Exception swallows YAML parse failures | security | Low | S | tools/validate_front_matter.py |
| CQ-04 | Five tests assert only by absence of an exception | code-quality | Low | S | tests/unit/test_setup_org_rulesets.py |
| CICD-03 | setup-python steps without dependency caching | cicd | Low | S | sync-org-pins.yml, pr-validation.yml, codeql.yml |
| CICD-04 | .mutmut_config is a stub while mutation CI runs | cicd | Low | S | .mutmut_config, .github/workflows/mutation-testing.yml |
| LEG-02 | Eight .disabled MCP config files retained as dead toggles | legacy-code | Low | S | mcp/zen-server.json.disabled, mcp/disabled/ |
| DEP-01 | Python 3.10 floor reaches EOL in five months | dependencies | Low | S | pyproject.toml |
| DEP-04 | Renovate dev-dependency grouping rule never matches | dependencies | Low | S | renovate.json, pyproject.toml |
| CQ-02 | Near-duplicate gh subprocess wrappers | code-quality | Low | M | scripts/check-repo-compliance.py, check-required-checks.py |
| CQ-03 | 61 production Any annotations at decode boundaries | code-quality | Low | M | scripts/check-required-checks.py, populate-github-repos.py, compliance_log_common.py |
| DEP-03 | Submodule pin freshness unverifiable in this tree | dependencies | Low | M | .gitmodules |
| DOC-08 | CHANGELOG format is inconsistent | docs | Low | M | CHANGELOG.md |

Excluded from the backlog (verified clean or accepted, with rationale): DEP-02 (stale dev-only `py` 1.11.0, already ignored with a documented disputed-CVE rationale, no action); SEC-04 through SEC-09 (secrets baseline verified accurate, all third-party actions SHA-pinned, no script-injection sinks, `yaml.load` is a ruamel safe-loader, no `pickle`/`eval`/`exec`, no confirmed CVEs in locked versions). One caveat: `pip-audit` was not installed in the audit environment, so the dependency CVE check was manual; CI-side scanning should be confirmed running.

## 6. Verdict

Drifting. The hygiene layer is in good shape: dependencies are current and hash-locked, every third-party action is SHA-pinned, lint and type gates pass, and there are no live secrets or confirmed CVEs. What is drifting is the gap between the script tier's size and its structure, and the gap between the standards the repo writes and the artifacts it ships. Left alone, both widen: more scripts will copy the duplicated `gh` client, and more documentation will drift from a growing config surface.

The three changes that move it most:

1. Package the `scripts/` tier into `claude_config` with entry points. This single restructure retires ARCH-01, ARCH-02, ARCH-04, ARCH-06, CQ-01, and CQ-02 and makes 6,490 LOC importable, testable, and coverage-gated.
2. Reconcile stated standards with reality: implement the merge-queue rules (CICD-01, CICD-02), resolve the skills-invoke-agents violation (ARCH-03) by fixing the code or amending ADR-004, and correct the three count-drift docs (DOC-05, DOC-06, DOC-07).
3. Remove the committed session-report HTML, add `session-report-*.html` to `.gitignore`, and record the policy in `SECURITY.md` (closes SEC-01 and LEG-01 together).
