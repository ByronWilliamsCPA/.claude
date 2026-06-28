---
title: "Snyk Remediation Plan: .claude Repository"
schema_type: planning
status: published
owner: core-maintainer
component: Strategy
source: "Created 2026-06-28 on branch chore/snyk-scope-cleanup. Driven by the Snyk IDE panel reporting 234 Code + ~229 OSS findings, all of which map to vendored submodules or the gitignored venv. Authoritative owned-source residual (13 Snyk Code findings, 0 critical/high) confirmed by live Snyk CLI 1.1305.2 scan after exclusions."
purpose: "Prioritized, sequenced plan to remediate Snyk findings in the .claude repo by first scoping Snyk to owned code (mirroring the existing isolation policy), then triaging the small owned-source residual. Companion to the findings inventory."
tags:
  - planning
  - security
  - compliance
---

> **Companion inventory:** [snyk-findings-inventory-2026-06-28.md](snyk-findings-inventory-2026-06-28.md)
> **Strategy decision (owner-approved 2026-06-28):** Scope Snyk to owned code,
> then triage only the residual. Do **not** patch vendored submodule code
> (conflicts with the "never edit submodule content directly" policy).

## Guiding principle

Every other quality gate in this repo already ignores `.submodules/` and
`.venv/`. Snyk is the lone outlier with no scope config, which is the entire
reason the IDE lights up. The highest-leverage action is to align Snyk with the
established boundary; that alone removes ~99% of the findings as non-actionable
noise. What remains (13 owned Snyk Code findings, 0 critical/high) is small and
triageable in a single sitting.

## Prioritization rationale

Ordered by leverage and risk, not by raw count. Suppressing vendored noise is
P0 because it is what makes the residual visible and keeps the gate signal
trustworthy going forward. The two real medium findings come next. Intentional
fixtures and low CLI-path notes follow. Optional tooling cleanup is last.

---

## P0 -- Scope Snyk to owned code (the core remediation)

This is the bulk of the value and is already drafted on this branch.

1. **Commit the `.snyk` exclusion policy** (already authored at repo root on this
   branch). It excludes `.submodules/**`, `.venv/**`, `site/**`, and nested
   `node_modules/`. Verified: drops Snyk Code from ~158 to 13 owned findings with
   zero vendored/venv leakage.
2. **Add IDE-level folder exclusions for Open Source scanning.** The `.snyk`
   `exclude:` block governs Snyk Code; the Snyk VS Code plugin scans OSS
   manifests separately. In VS Code settings (`Snyk › Advanced`), add the
   submodule and venv folders to "Files to scan" exclusions, or set additional
   CLI parameters, so the ~229 vendored `package.json` OSS findings stop
   populating the panel. Document the exact setting in `docs/security/`.
3. **Verify in-IDE.** After reload, confirm the Open Source and Code Security
   panels show only owned-source results (target: 0 OSS, 13 Code pre-triage).

**Acceptance:** `.snyk` committed; IDE panels reflect owned scope only; a
`snyk code test` from repo root reports the 13 owned findings and nothing under
`.submodules/`, `.venv/`, or `site/`.

---

## P1 -- The two "medium" findings are verified false positives (no code change)

Both were read in full. Each already implements the correct guard, so per the
code-quality rule ("fix the actual issue; do not paper over it") there is no
issue to fix, and a code edit would be cargo-cult.

4. **`python/CommandInjection` -- `scripts/populate-github-repos.py:82`.**
   The call uses list-form argv (no `shell=True`); the only env-derived value
   (`GH_BINARY`) is resolved through `shutil.which()` and existence-checked. The
   flagged `org` is a positional list element, never shell-interpolated. Snyk's
   taint tracker fires on `os.environ -> subprocess.run` regardless. **Disposition:
   verified false positive. No code change.**
5. **`python/Ssrf` -- `scripts/check_quality_gate.py:69`.**
   The code already validates the URL scheme against an `ALLOWED_SCHEMES`
   allowlist before `urlopen` and carries a documented `# noqa: S310` for
   bandit's equivalent rule. The host is operator-supplied CI config.
   **Disposition: verified false positive. No code change.**

**Local-ignore limitation (verified):** a `.snyk` `ignore:` block is not honored
by `snyk code test` in this CLI version; only file-level `exclude:` works
locally. Excluding a whole real source file to hide one false positive would
blind Snyk to future real bugs in that file, so do not. Apply the two
suppressions as **Snyk platform UI ignores** instead, citing the analysis above.

**Acceptance:** the two false positives are recorded (in the inventory and, when
convenient, as Snyk UI ignores); no suppressions added to real source files.

---

## P2 -- Disposition the 11 owned low (note) findings

6. **3x `python/InsecureHash/test` in `tests/fixtures/fips/bad_*.py`. DONE.**
   Resolved on this branch: `.snyk` now excludes `tests/fixtures/fips/**`
   (deliberate insecure-hash/cipher fixtures for the FIPS-compat checker, not
   production code). Verified the residual dropped from 13 to 10 with 0 fixture
   findings remaining.
7. **8x `python/PT` (path traversal) across `consensus_cli.py`,
   `parse_coverage.py`, `generate_python_tier_repos.py`, `doc-audit.py`,
   `populate-github-repos.py`.** In every case the "untrusted input" is the
   operator's own command-line argument to a local developer tool. Decide per the
   project's risk appetite:
   - Lightweight hardening: resolve and validate paths (`Path.resolve()` plus a
     containment check) where cheap; or
   - Ignore-with-justification noting these are local CLI tools with
     operator-supplied paths.

**Acceptance:** each note finding is either hardened or carries a scoped,
justified `.snyk` ignore. The goal is a clean, intentional Snyk panel, not
suppression for its own sake.

---

## P3 -- Optional tooling and durability

8. **(Optional) Unblock Snyk Open Source on owned Python deps.** `snyk test`
   currently fails on `uv 0.9.26 < required 0.9.29`. Upgrading uv would let Snyk
   OSS scan `pyproject.toml`/`uv.lock`. This is **optional** because `pip-audit`
   is already the dependency scanner of record (CLAUDE.md) and feeds
   `docs/known-vulnerabilities.md`. Pursue only if Snyk OSS parity is wanted.
9. **Document the Snyk scope decision** as a short note in `docs/security/`
   (or an ADR) so future contributors understand why `.snyk` excludes the
   vendored tree, mirroring the submodule isolation policy.
10. **Optional CI wiring.** If Snyk should run in CI, add a `snyk code test`
    step that relies on the committed `.snyk`. Keep it advisory (non-blocking)
    initially, consistent with how new gates are rolled out at `suggested`
    status before enforcement.

---

## Sequenced checklist

- [x] Commit `.snyk` exclusion policy (P0.1)
- [ ] Add + document IDE OSS folder exclusions (P0.2)
- [ ] Verify IDE panels show owned scope only (P0.3)
- [x] `CommandInjection` analyzed: verified false positive, no code change (P1.4)
- [x] `Ssrf` analyzed: verified false positive, no code change (P1.5)
- [x] `.snyk` exclude for FIPS fixtures; residual 13 -> 10 (P2.6)
- [ ] Disposition 8 path-traversal notes: accepted risk, optional UI ignores (P2.7)
- [ ] (Optional) Apply the 2 false-positive ignores in the Snyk UI
- [ ] (Optional) uv upgrade for Snyk OSS / scope-decision note / CI wiring (P3)
- [ ] Open PR from `chore/snyk-scope-cleanup`; run `pre-commit run --all-files`

## Out of scope (explicitly)

- Editing any file under `.submodules/` to patch upstream vulnerabilities.
  Vendored code is upstream's responsibility; report or upgrade the submodule
  pin upstream if a specific CVE matters, but do not modify submodule contents.
- npm dependency remediation: there is no owned npm dependency tree.
