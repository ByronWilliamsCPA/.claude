---
schema_type: common
title: Replace darglint with pydoclint
status: draft
owner: engineering
tags: [tooling, linting, compliance, standards, documentation]
purpose: Design for replacing the unmaintained darglint docstring-argument validator with pydoclint across all 14 functional surfaces (the .claude config repo, the standards manifest, domain auditor agents, rules/skills prose, the cookiecutter template, and the Python fleet), packaged as two PRs. PR1 swaps the tool and its enforcement layer together so the repo never fails its own self-audit; PR2 propagates to the cookiecutter template and rolls out across the fleet via the repo-compliance coordinator. The pydoclint profile targets a "lenient plus keep raises" posture, accepting one slight tightening (gaining DOC501 missing-raises) that the config-model mismatch makes unavoidable if DAR402 is to be preserved.
---

## Context

`darglint` has been archived and unmaintained since 2022. It validates that
docstring arguments match function signatures (the consistency dimension),
distinct from `interrogate`, which measures docstring coverage (the percentage
of functions documented). `interrogate` stays; only `darglint` is the
replacement target.

A prior investigation session (handoff at
`docs/handoffs/darglint-to-pydoclint/README.md`) mapped darglint's complete
functional footprint to 14 active surfaces, confirmed the replacement decision
(pydoclint over Ruff DOC rules), and left three decisions open. This design
resolves those decisions and specifies the rollout.

### Why pydoclint, not Ruff DOC rules

Ruff's pydoclint port implements only the DOC2xx/4xx/5xx family
(returns/yields/raises) and they are preview-only. The DOC1xx argument family
is unimplemented (Ruff issue #12434), so Ruff cannot replace **DAR102**
("documented a parameter not in the signature"), one of the actively enforced
checks and a common real-world drift case. pydoclint covers it (DOC102). This
trade-off was evaluated and rejected in the handoff; it is not reopened here.

### The actually-enforced darglint profile

The behaviour that must be reproduced is what the *config* enforces, not
darglint's nominal feature set. With `strictness = "long"` and
`ignore = [DAR101, DAR201, DAR301, DAR401]`, the `.claude` repo enforces only
the **excess/mismatch direction**: it flags docstrings that describe a
parameter, return, yield, or raised exception the function no longer has. It
does **not** require missing sections to be added.

Active checks: DAR102 (doc param not in signature), DAR103 (param type
mismatch), DAR202 (extra Returns), DAR203 (return type mismatch), DAR302 (extra
Yields), DAR402 (exception documented but not raised).

## Key decisions

### Decision 1: config posture = "lenient plus keep raises"

The profile reproduces darglint's excess-only behaviour for the
args/returns/yields families, but **keeps raises checking enabled**.

The config models differ in a way that makes exact replication impossible for
the raises family. darglint suppresses *per code* (`ignore = [DAR401]` turns off
missing-raises while leaving DAR402 excess-raises active). pydoclint's
`skip-checking-raises` is a **single binary** that toggles DOC501 (missing) and
DOC502 (excess) together; there is no per-direction switch. The two reachable
options were therefore:

- Disable raises checking (`skip-checking-raises = true`): zero new failures,
  but **loses DAR402** (excess raises), a check darglint currently enforces.
- Enable raises checking (`skip-checking-raises = false`): **preserves DAR402**
  via DOC502, but **gains DOC501** (missing-raises), a check darglint did not
  enforce here, which may surface new failures in existing docstrings.

Decision: enable raises checking (`skip-checking-raises = false`). Rationale:
losing a real consistency check (DAR402) is a regression; gaining DOC501 is a
slight tightening that improves docstring quality. New DOC501 failures are
treated as genuine drift and fixed in the docstrings, not suppressed (per the
global "fix the actual issue" standard).

### Decision 2: drop the hook from the pre-commit.ci skip list

darglint is in the pre-commit.ci `skip:` list (`.pre-commit-config.yaml:21`)
because it was a `repo: local` / `language: system` hook that pre-commit.ci
cannot run. A pinned pydoclint pre-commit repo hook **can** run on
pre-commit.ci. Decision: remove `darglint` from the skip list so pre-commit.ci
enforces pydoclint directly, adding a second enforcement point alongside the
org `python-precommit.yml` CI workflow.

### Decision 3: retire the TOOL-007 NumPy override after validation

The TOOL-007 override (documented in `repo-compliance.md:131` and present in
some repos' `.claude/compliance-overrides.md`) exists specifically because
darglint conflicted with NumPy-style docstrings. pydoclint supports NumPy style
natively (`style = "numpy"`). Decision: retire the override, but **only after**
confirming pydoclint with `style = "numpy"` passes clean on a repo that
currently carries the override. Retirement touches both the doc example and the
real per-repo override files.

### Decision 4: PR packaging = Approach B

- **PR1** (`chore/replace-darglint-with-pydoclint`): Phases 1+2 together. The
  `.claude` repo is audited by its own `standards-manifest.yaml`. Changing the
  tool without changing the check (or vice versa) creates a window where the
  repo violates its own standard. The tool swap and the enforcement-layer
  retarget must therefore land together.
- **PR2**: Phase 3 (cookiecutter template + fleet rollout). No coupling to the
  `.claude` repo self-audit, different blast radius, so it is isolated.

## Scope: the 14 surfaces

| # | Location | Change | Phase / PR |
|---|----------|--------|------------|
| 1 | `.pre-commit-config.yaml:267-275` | Replace `repo: local` darglint hook with pinned pydoclint repo hook | P1 / PR1 |
| 2 | `.pre-commit-config.yaml:21` | Remove `darglint` from `ci.skip` (Decision 2) | P1 / PR1 |
| 3 | `pyproject.toml:97` | Swap dev dep `darglint>=1.8.1` → `pydoclint>=0.8.4` | P1 / PR1 |
| 4 | `pyproject.toml:531-547` | Replace `[tool.darglint]` with `[tool.pydoclint]` (Decision 1) | P1 / PR1 |
| 5 | org `python-precommit.yml:132` | No file change; verify pydoclint resolves in the `uv sync --frozen` CI env | P1 / PR1 |
| 6 | `standards-manifest.yaml:266-272` | Retarget TOOL-007 to pydoclint | P2 / PR1 |
| 7 | `standards-manifest.yaml:368-374` | Retarget PC-006 to pydoclint | P2 / PR1 |
| - | `standards-manifest.yaml` (new) | Add darglint-absence check (replaced-tools pattern) | P2 / PR1 |
| 8 | `.claude/agents/pre-commit-auditor.md:95` | Swap hook URL/id to pydoclint | P2 / PR1 |
| 9 | `.claude/agents/python-toolchain-auditor.md:31-32` | Swap dep name; keep interrogate coupling | P2 / PR1 |
| 10 | `.claude/rules/pre-commit.md:24` | Reword checklist line to pydoclint | P2 / PR1 |
| 11 | `.claude/rules/python.md:184-192` | Reword behaviour spec; update strictness wording | P2 / PR1 |
| 12 | `.claude/skills/pre-commit-authoring/SKILL.md:20,81` | Swap name in toolchain list + tier placement | P2 / PR1 |
| 13 | `docs/reference/repo-compliance.md:99,101,131` | Update TOOL/PC summaries; retire NumPy override (Decision 3) | P2 / PR1 |
| 14 | `~/dev/cookiecutter-python-template/` | Swap files; delete `{{cookiecutter.project_slug}}/.darglint` | P3 / PR2 |
| - | Python fleet | Roll out via repo-compliance coordinator | P3 / PR2 |

## Architecture and data flow

The change has no runtime/application component; it is a toolchain and
enforcement-config migration. The "data flow" is the enforcement topology:

```text
developer commit ──► pre-commit (local pydoclint hook) ──► blocks on excess-drift
                          │
                          ├─► pre-commit.ci (now runs pydoclint; Decision 2)
                          │
push / PR ────────────► org python-precommit.yml ──► `pre-commit run --all-files`
                                                          (runs pydoclint in uv env)

/repo-audit ──► standards-manifest.yaml ──► TOOL-007 + PC-006 check pydoclint
                                            + darglint-absence check
```

The enforcement layer (manifest + agents) is what makes the fleet audit check
for the right tool. The self-audit invariant (PR1 couples surfaces 1-4 with
6-13) exists because the `.claude` repo is itself a target of that audit.

### pydoclint config translation (Phase 1 crux)

The exact `[tool.pydoclint]` flag set is **pinned empirically in Phase 1**, not
guessed from docs, because the args/returns/yields direction toggles are not a
clean 1:1 with darglint's per-code ignore list. The intended starting point:

```toml
[tool.pydoclint]
style = "google"
arg-type-hints-in-docstring = true      # preserve DAR103-equivalent type checks
skip-checking-raises = false            # Decision 1: keep DAR402, accept DOC501
# Suppress the missing-direction equivalents (DAR101/201/301) per the lenient
# posture; the exact flags are confirmed by reading actual emitted DOC codes
# during validation.
```

Validation procedure: `uv run pydoclint src/`, read the emitted DOC codes,
adjust flags until only the intended excess checks (plus raises) fire, fix any
genuine new DOC501 drift in docstrings, then lock the config. This validation
is the proof that the translation is correct, replacing the unreliable
"reproduce from the docs" approach.

## Validation strategy

- **Phase 1 gate**: `uv lock && uv sync --all-extras` → `uv run pydoclint src/`
  (achieve parity with the darglint baseline; fix real new drift, never
  suppress) → `pre-commit run pydoclint --all-files`.
- **Phase 2 gate**: `/repo-audit` on `.claude` confirms the manifest now checks
  for pydoclint and flags darglint's absence, with zero new findings introduced
  by the migration.
- **SHA-pinning**: the new pydoclint hook introduces a `rev:` field. The PC
  SHA-pinning checks require it to be a full commit SHA, not a tag. Resolve the
  SHA for the chosen pydoclint release at implementation time and pin it.
- **CI path**: confirm pydoclint resolves under `uv sync --frozen` in the org
  `python-precommit.yml` env. Note the `.claude` repo's own `ci.yml` calls
  `python-ci.yml`, not `python-precommit.yml`, so verify which reusable
  workflow each target repo wires before assuming CI coverage.

## Phase 3: propagation and fleet rollout

- **Cookiecutter** (`~/dev/cookiecutter-python-template`): swap `pyproject.toml`,
  `.pre-commit-config.yaml`, `.standards/pyproject.toml.baseline`, and `uv.lock`
  in the `{{cookiecutter.project_slug}}/` rendered tree, plus the template-root
  copies; **delete `{{cookiecutter.project_slug}}/.darglint`** (pydoclint config
  lives in pyproject `[tool.pydoclint]`).
- **NumPy override retirement** (Decision 3): validate `style = "numpy"` passes
  clean on a NumPy-style repo that carries the override, then sweep real
  `.claude/compliance-overrides.md` files for TOOL-007 entries and remove them.
- **Fleet scope** = manifest applicability (any repo with Python source)
  cross-referenced with `docs/reference/github-repos.json`, **not** the local
  clone count (clones are inflated by `.worktrees/`, branch-named checkouts, and
  dash/underscore duplicate clones). Drive via `/repo-audit` once PR1's manifest
  is live; each fleet repo gets its own PR so a bad rollout is contained.

## Risks and rollback

- **New DOC501 failures** (from Decision 1) may be larger than expected. Mitigated
  by the Phase 1 validation gate, which surfaces the count before commit; fix is
  bounded to docstring edits.
- **SHA-pin churn**: the new `rev:` field must be a commit SHA; a tag would fail
  the PC checks. Mitigated by resolving the SHA at implementation.
- **Rollback**: PR1 is a single revertable change set. Phase 3 repos each get an
  isolated PR, so a bad fleet rollout is contained per-repo, not global.

## Out of scope

- Historical docs under `docs/superpowers/` and `compliance-retrospectives/`
  that mention darglint are archival narrative, not active enforcement, and stay
  untouched.
- Tightening the docstring bar beyond "lenient plus keep raises" (requiring
  missing sections) is explicitly deferred; it is a separate future decision.
- Migrating to Ruff DOC rules (rejected; see Context).
