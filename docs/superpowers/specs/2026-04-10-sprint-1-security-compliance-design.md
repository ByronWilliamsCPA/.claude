---
schema_type: common
title: "Sprint 1: Security & Compliance Standards"
status: draft
owner: core-maintainer
purpose: "Design spec for adding FIPS compliance, pip-audit hook, SHA pinning guidance, and known vulnerability documentation to the global Claude implementation."
tags:
  - security
  - compliance
  - tooling
  - documentation
---

> **Date**: 2026-04-10
> **Status**: Draft
> **Scope**: Global `~/.claude` standards (dev repo at `~/dev/.claude`)

## Overview

This sprint adds four security and compliance standards to the global Claude implementation,
closing gaps identified in the 2026-04-09 cross-project CLAUDE.md audit. All items appeared
in 3+ project CLAUDE.md files but were absent from the global standard.

**Approach**: Documentation-only for three items; one tooling change (pip-audit hook). No
enforcement hook for SHA pinning — CodeRabbit's existing `.github/workflows/**` path
instructions provide the review-time gate.

---

## Item 1: pip-audit Pre-Push Hook

**Problem**: `pip-audit` is in dev dependencies and documented as a manual step in
`rules/pre-commit.md`. It does not run automatically. Developers can commit and push
vulnerable dependencies without triggering a scan.

**Solution**: Add a local hook to `.pre-commit-config.yaml` at the `pre-push` stage,
scoped to trigger only when dependency files change.

**Hook definition** — add after the Bandit section, before Conventional Commits:

```yaml
# ============================================================================
# Dependency Vulnerability Scanning - pip-audit
# ============================================================================
# Runs on pre-push, scoped to dep file changes only, to avoid per-commit overhead.
# Exit code 64 = advisory found. Medium+ severity blocks push.
- repo: local
  hooks:
    - id: pip-audit
      name: pip-audit (dependency vulnerability scan)
      entry: uv run pip-audit
      language: system
      pass_filenames: false
      stages: [pre-push]
      files: ^(pyproject\.toml|requirements.*\.txt|uv\.lock)$
```

**CI skip list** — add `pip-audit` to the existing `ci: skip:` line:

```yaml
skip: [validate-front-matter, qlty-check, qlty-full, trufflehog, darglint, bandit, bandit-full, pip-audit]
```

**`rules/pre-commit.md` Security section** — replace the current pip-audit manual step.

Before:

```text
- [ ] **Security Scanning**: No known vulnerabilities — medium+ severity blocks commit (`uv run pip-audit`; exit code 64 = advisory found)
```

After:

```text
- [ ] **Security Scanning**: pip-audit runs automatically on pre-push when dependency files
      change (pyproject.toml, requirements*.txt, uv.lock). Exit code 64 = advisory found —
      medium+ severity blocks push. For manual audit: `uv run pip-audit`
```

---

## Item 2: FIPS 140-2/3 Compliance

**Problem**: Six or more cookiecutter-generated projects document FIPS compliance requirements,
but the global `rules/python.md` has no mention of prohibited algorithms, approved alternatives,
or the `usedforsecurity=False` pattern.

**Solution**: Add a new section to `rules/python.md` after "Type Checking with BasedPyright"
and before "PyStrict-Aligned Ruff Rules". No frontmatter change needed — the existing `paths:`
filter (`**/*.py`, `pyproject.toml`) correctly scopes this to Python contexts.

**Section content to add:**

```markdown
## FIPS 140-2/3 Compliance

Do not use these algorithms in any security context:

| Category | Prohibited | Approved Alternative |
|----------|-----------|---------------------|
| Hash | MD5, SHA-1 | SHA-256, SHA-384, SHA-512 |
| Symmetric | Blowfish, RC4, RC2, DES, 3DES | AES-128, AES-256 |
| Key exchange | RSA < 2048-bit, DH < 2048-bit | RSA-2048+, Curve25519, X25519 |

When using hashlib for non-security purposes (checksums, caching),
pass `usedforsecurity=False`:

    # OK: cache key or checksum, not cryptographic
    hashlib.md5(data, usedforsecurity=False)

Never pass `usedforsecurity=False` for: password hashing, HMAC, signatures,
or token generation.
```

---

## Item 3: GitHub Actions SHA Pinning

**Problem**: No guidance in `rules/git-workflow.md` about GitHub Actions pin strategy.
Projects can reference actions by mutable version tags, which are vulnerable to supply chain
attacks via tag mutation.

**Solution**: Add a new section to `rules/git-workflow.md` after the Gate System section and
before Git Worktrees. Guidance-only — CodeRabbit's existing `.github/workflows/**` path
instructions provide review-time enforcement.

**Section content to add:**

```markdown
## GitHub Actions: Pin to Commit SHAs

Never reference GitHub Actions by mutable version tags. Tags can be rewritten by the action
author after the fact, enabling supply chain attacks via tag mutation.

Always pin to the full commit SHA:

    # Bad — tag is mutable, can be rewritten after you reference it
    - uses: actions/checkout@v4

    # Good — SHA is immutable
    - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2

To find the SHA: navigate to the action's releases page on GitHub, click the commit link for
the version you want, and copy the full 40-character SHA. Add the version as a comment so the
pin stays human-readable.

Dependabot keeps SHA pins current when configured in `.github/dependabot.yml` with
`package-ecosystem: github-actions`.
```

---

## Item 4: Known Vulnerability Documentation

**Problem**: When `pip-audit` flags a CVE that cannot be immediately fixed (no patched version,
breaking API change required), developers have two bad options: suppress the warning or feel
blocked from shipping. Neither is documented. No template exists for structured trade-off
documentation.

**Solution**: Create `docs/known-vulnerabilities-template.md` as the canonical pattern for all
projects, and add a policy reference to `CLAUDE.md`.

Projects create their own `docs/known-vulnerabilities.md` by copying from this template; the
template itself lives in the global `.claude` repo.

**`docs/known-vulnerabilities-template.md`** — must include valid frontmatter to pass the
`validate-front-matter` pre-commit hook (which scans all `docs/**/*.md` files):

```markdown
---
schema_type: common
title: "Known Vulnerabilities Template"
status: published
owner: core-maintainer
purpose: "Template for documenting CVEs that cannot be immediately resolved."
tags:
  - security
  - dependencies
---

# Known Vulnerabilities

> Tracks CVEs that cannot be immediately resolved. Review quarterly.
> No entry may age past 90 days without reassessment — escalate or resolve.

## CVE-YYYY-XXXXX — Package Name vX.Y

| Field | Value |
| --- | --- |
| **Severity** | Critical / High / Medium |
| **CVSS Score** | X.X |
| **Affected package** | package-name >= X.Y, < X.Z |
| **Patched version** | X.Z (not yet released / available but breaks X) |
| **Date documented** | YYYY-MM-DD |
| **Reassessment due** | YYYY-MM-DD (90 days max) |

**Exploitation scenario**: Describe what an attacker needs to exploit this in your context.

**Why deferred**: Specific reason — upstream unpatched, breaking API change required, etc.

**Compensating control**: What reduces the risk while the CVE remains open.

**Planned resolution**: Target version, migration path, or timeline.
```

**`CLAUDE.md` addition** — after the last blockquote in Core Development Standards
(after `> **Writing quality thresholds...`):

```markdown
> **Unfixed CVEs**: When pip-audit finds a vulnerability that cannot be immediately resolved,
> document it in `docs/known-vulnerabilities.md` using the template at
> `docs/known-vulnerabilities-template.md`. Never suppress pip-audit output without a
> documented entry. Review quarterly; no entry ages past 90 days without reassessment.
```

---

## Files Modified

| File | Change Type | Description |
| --- | --- | --- |
| `.pre-commit-config.yaml` | Tooling | Add pip-audit local hook at pre-push stage |
| `.claude/rules/pre-commit.md` | Documentation | Update pip-audit entry to reflect automatic execution |
| `.claude/rules/python.md` | Documentation | Add FIPS 140-2/3 compliance section |
| `.claude/rules/git-workflow.md` | Documentation | Add GitHub Actions SHA pinning section |
| `CLAUDE.md` | Documentation | Add unfixed CVE policy reference |
| `docs/known-vulnerabilities-template.md` | New file | CVE documentation template |

---

## Verification

1. **pip-audit hook fires**: Modify `uv.lock` or `pyproject.toml`, run
   `pre-commit run pip-audit --hook-stage pre-push`, confirm hook executes
2. **pip-audit hook skips**: Run the hook against a commit with only `.py` changes,
   confirm it does not run
3. **CI skip**: Confirm `pip-audit` appears in the `ci: skip:` list
4. **FIPS content visible**: Open a `.py` file — `rules/python.md` is context-injected,
   making FIPS rules visible to Claude
5. **SHA pinning section**: Confirm section appears in `git-workflow.md` between Gate System
   and Git Worktrees
6. **Template well-formed**: `docs/known-vulnerabilities-template.md` passes
   `pre-commit run validate-front-matter`

---

## Out of Scope

- SHA pinning enforcement hook (rejected; CodeRabbit handles review-time gate)
- Updating downstream project `CLAUDE.md` files to reference the known-vuln template
- Adding pip-audit to CI pipeline (separate from pre-commit; out of sprint scope)
