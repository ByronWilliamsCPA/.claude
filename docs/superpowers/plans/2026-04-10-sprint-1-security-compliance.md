---
schema_type: planning
title: "Sprint 1: Security & Compliance Standards Implementation Plan"
status: draft
owner: core-maintainer
purpose: "Implementation plan for adding FIPS compliance, pip-audit hook, SHA pinning guidance, and known vulnerability documentation to the global Claude implementation."
component: Development-Tools
source: "docs/superpowers/specs/2026-04-10-sprint-1-security-compliance-design.md"
tags:
  - planning
  - security
  - compliance
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four security and compliance standards to the global Claude implementation: pip-audit pre-push hook, FIPS 140-2/3 compliance guidance, GitHub Actions SHA pinning guidance, and known vulnerability documentation template.

**Architecture:** All changes are additive to existing files — no existing content removed. One tooling change (`.pre-commit-config.yaml`), four documentation additions to rules files, one new template file. No code to write; no tests to generate. Verification is manual hook execution and content inspection.

**Tech Stack:** pre-commit, uv, pip-audit, YAML, Markdown

---

## File Map

| File | Action | What Changes |
| --- | --- | --- |
| `.pre-commit-config.yaml` | Modify | Add pip-audit local hook block; add `pip-audit` to CI skip list |
| `.claude/rules/pre-commit.md` | Modify | Replace manual pip-audit checklist item with automatic-hook description |
| `.claude/rules/python.md` | Modify | Add FIPS 140-2/3 compliance section after BasedPyright section |
| `.claude/rules/git-workflow.md` | Modify | Add SHA pinning section after Gate System section |
| `CLAUDE.md` | Modify | Add unfixed CVE policy blockquote after Core Development Standards |
| `docs/known-vulnerabilities-template.md` | Create | New CVE documentation template with valid frontmatter |

---

## Task 1: Create Feature Branch

**Files:** none

- [ ] **Step 1: Ensure main is current**

```bash
git checkout main && git pull origin main
```

Expected: `Already up to date.` or fast-forward merge output.

- [ ] **Step 2: Create the feature branch**

```bash
git checkout -b docs/sprint-1-security-compliance
```

Expected: `Switched to a new branch 'docs/sprint-1-security-compliance'`

- [ ] **Step 3: Confirm branch**

```bash
git branch --show-current
```

Expected: `docs/sprint-1-security-compliance`

---

## Task 2: Wire pip-audit Pre-Push Hook

**Files:**

- Modify: `.pre-commit-config.yaml` (lines 15 and ~90)
- Modify: `.claude/rules/pre-commit.md` (line 26)

### Step 2a: Update CI skip list

- [ ] **Step 1: Confirm current skip list**

```bash
grep "skip:" .pre-commit-config.yaml
```

Expected output:
```text
  skip: [validate-front-matter, qlty-check, qlty-full, trufflehog, darglint, bandit, bandit-full]  # Skip local-only hooks
```

- [ ] **Step 2: Add pip-audit to skip list**

In `.pre-commit-config.yaml`, replace line 15:

```yaml
  skip: [validate-front-matter, qlty-check, qlty-full, trufflehog, darglint, bandit, bandit-full]  # Skip local-only hooks
```

With:

```yaml
  skip: [validate-front-matter, qlty-check, qlty-full, trufflehog, darglint, bandit, bandit-full, pip-audit]  # Skip local-only hooks
```

- [ ] **Step 3: Verify skip list change**

```bash
grep "skip:" .pre-commit-config.yaml
```

Expected: `skip: [..., pip-audit]  # Skip local-only hooks`

### Step 2b: Add pip-audit hook block

- [ ] **Step 4: Confirm insertion point exists**

```bash
grep -n "always_run: true" .pre-commit-config.yaml
```

Expected: single line result, e.g. `90:        always_run: true` (the bandit-full hook's last line).

- [ ] **Step 5: Add pip-audit hook block**

In `.pre-commit-config.yaml`, after the `always_run: true` line of the `bandit-full` hook and before the `# Conventional Commits Enforcement` comment block, insert:

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

- [ ] **Step 6: Verify YAML is valid**

```bash
python -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))" && echo "YAML valid"
```

Expected: `YAML valid`

- [ ] **Step 7: Verify hook is recognized by pre-commit**

```bash
pre-commit run pip-audit --hook-stage pre-push --all-files
```

Expected: Either `pip-audit...Passed` or `pip-audit...Failed` (with CVE output) — either confirms the hook runs. If output is `pip-audit (no files to check)Skipped`, the `files:` filter is working and no dep files matched (unlikely since `pyproject.toml` exists — if this happens, check the regex).

### Step 2c: Update pre-commit checklist

- [ ] **Step 8: Confirm current checklist line**

```bash
grep -n "Security Scanning" .claude/rules/pre-commit.md
```

Expected: `26:- [ ] **Security Scanning**: No known vulnerabilities — medium+ severity blocks commit...`

- [ ] **Step 9: Replace the manual pip-audit checklist item**

In `.claude/rules/pre-commit.md`, replace:

```text
- [ ] **Security Scanning**: No known vulnerabilities — medium+ severity blocks commit (`uv run pip-audit`; exit code 64 = advisory found)
```

With:

```text
- [ ] **Security Scanning**: pip-audit runs automatically on pre-push when dependency files change (pyproject.toml, requirements*.txt, uv.lock). Exit code 64 = advisory found — medium+ severity blocks push. For manual audit: `uv run pip-audit`
```

- [ ] **Step 10: Verify the change**

```bash
grep -A1 "Security Scanning" .claude/rules/pre-commit.md
```

Expected: shows the new text with "runs automatically on pre-push".

- [ ] **Step 11: Commit Task 2**

```bash
git add .pre-commit-config.yaml .claude/rules/pre-commit.md
git commit -m "chore: add pip-audit pre-push hook for dependency vulnerability scanning"
```

Expected: commit succeeds, pre-commit hooks pass.

---

## Task 3: Add FIPS 140-2/3 Compliance Section

**Files:**

- Modify: `.claude/rules/python.md` (after line 35, before `## PyStrict-Aligned Ruff Rules`)

- [ ] **Step 1: Confirm insertion point**

```bash
grep -n "PyStrict-Aligned Ruff Rules" .claude/rules/python.md
```

Expected: single result, e.g. `37:## PyStrict-Aligned Ruff Rules`

- [ ] **Step 2: Insert FIPS section**

In `.claude/rules/python.md`, insert the FIPS section before the `## PyStrict-Aligned Ruff Rules`
heading confirmed in Step 1. Use the Edit tool with:

- `old_string`: `## PyStrict-Aligned Ruff Rules`
- `new_string`: the block below followed by `## PyStrict-Aligned Ruff Rules`

Content to insert (everything before the heading):

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
```

Then immediately after the table block, add the python example as an indented code block
and the closing rule — here is the complete `new_string` value for the Edit call:

```text
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

## PyStrict-Aligned Ruff Rules
```

- [ ] **Step 3: Verify section is present**

```bash
grep -n "FIPS" .claude/rules/python.md
```

Expected: lines showing `## FIPS 140-2/3 Compliance` and the table content.

- [ ] **Step 4: Verify section order is correct**

```bash
grep -n "^## " .claude/rules/python.md
```

Expected heading order:

```text
## File-Type Standards
## Type Checking with BasedPyright
## FIPS 140-2/3 Compliance
## PyStrict-Aligned Ruff Rules
## Code Generation — Python-Specific
```

- [ ] **Step 5: Commit Task 3**

```bash
git add .claude/rules/python.md
git commit -m "docs: add FIPS 140-2/3 compliance requirements to python rules"
```

---

## Task 4: Add GitHub Actions SHA Pinning Section

**Files:**

- Modify: `.claude/rules/git-workflow.md` (after Gate System section, before Git Worktrees)

- [ ] **Step 1: Confirm insertion point**

```bash
grep -n "^## Git Worktrees" .claude/rules/git-workflow.md
```

Expected: single result, e.g. `61:## Git Worktrees`

- [ ] **Step 2: Insert SHA pinning section**

In `.claude/rules/git-workflow.md`, use the Edit tool with:

- `old_string`: `## Git Worktrees`
- `new_string`: the full section below followed by `## Git Worktrees`

Complete `new_string` value — the yaml example uses indented code blocks to avoid nesting:

```text
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

## Git Worktrees
```

- [ ] **Step 3: Verify section is present and ordered correctly**

```bash
grep -n "^## " .claude/rules/git-workflow.md
```

Expected heading order:

```text
## Branch Strategy (MANDATORY)
## Gate System
## GitHub Actions: Pin to Commit SHAs
## Git Worktrees
```

- [ ] **Step 4: Commit Task 4**

```bash
git add .claude/rules/git-workflow.md
git commit -m "docs: add GitHub Actions SHA pinning guidance to git workflow rules"
```

---

## Task 5: Create Known Vulnerability Template and CLAUDE.md Reference

**Files:**

- Create: `docs/known-vulnerabilities-template.md`
- Modify: `CLAUDE.md` (after line 70)

### Step 5a: Create the template file

- [ ] **Step 1: Create the file**

Create `docs/known-vulnerabilities-template.md` with this exact content:

```markdown
---
schema_type: common
title: "Known Vulnerabilities Template"
status: published
owner: core-maintainer
purpose: "Template for documenting CVEs that cannot be immediately resolved in project dependencies."
tags:
  - security
  - dependencies
---

# Known Vulnerabilities

> Tracks CVEs that cannot be immediately resolved. Review quarterly.
> No entry may age past 90 days without reassessment — escalate or resolve.

<!-- Copy the entry below for each new CVE. Delete this comment in your project's file. -->

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

- [ ] **Step 2: Verify it passes the front-matter validation hook**

```bash
pre-commit run validate-front-matter --files docs/known-vulnerabilities-template.md
```

Expected: `validate-front-matter...Passed`

If it fails, the frontmatter schema is more strict than expected — read the error output from `tools/validate_front_matter.py` and adjust the frontmatter fields accordingly before proceeding.

### Step 5b: Add CLAUDE.md policy reference

- [ ] **Step 3: Confirm insertion point**

```bash
grep -n "Writing quality thresholds" CLAUDE.md
```

Expected: single result, e.g. `70:> **Writing quality thresholds...`

- [ ] **Step 4: Insert the CVE policy blockquote**

In `CLAUDE.md`, replace:

```text
> **Writing quality thresholds (pipeline stages, stylometry targets, pass/fail)**: See `.claude/standards/writing-quality.md`

## Response-Aware Development (RAD)
```

With:

```text
> **Writing quality thresholds (pipeline stages, stylometry targets, pass/fail)**: See `.claude/standards/writing-quality.md`
>
> **Unfixed CVEs**: When pip-audit finds a vulnerability that cannot be immediately resolved,
> document it in `docs/known-vulnerabilities.md` using the template at
> `docs/known-vulnerabilities-template.md`. Never suppress pip-audit output without a
> documented entry. Review quarterly; no entry ages past 90 days without reassessment.

## Response-Aware Development (RAD)
```

- [ ] **Step 5: Verify the blockquote is present**

```bash
grep -n "Unfixed CVEs" CLAUDE.md
```

Expected: single result showing the new blockquote line.

- [ ] **Step 6: Commit Task 5**

```bash
git add docs/known-vulnerabilities-template.md CLAUDE.md
git commit -m "docs: add known vulnerability template and CVE policy reference to CLAUDE.md"
```

---

## Task 6: End-to-End Verification

**Files:** none (read-only verification)

- [ ] **Step 1: Run full pre-commit suite**

```bash
pre-commit run --all-files
```

Expected: all hooks pass. If `validate-front-matter` fails on the new template file, re-read its error output and fix the frontmatter fields.

- [ ] **Step 2: Verify pip-audit hook fires on dep files**

```bash
pre-commit run pip-audit --hook-stage pre-push --all-files
```

Expected: `pip-audit...Passed` (no vulnerabilities) or `pip-audit...Failed` with CVE output. Either outcome confirms the hook is wired. A `Skipped` result means the `files:` regex didn't match — check the pattern against `pyproject.toml`.

- [ ] **Step 3: Confirm all six section headings are present**

```bash
grep -n "FIPS" .claude/rules/python.md && \
grep -n "GitHub Actions: Pin to Commit SHAs" .claude/rules/git-workflow.md && \
grep -n "Unfixed CVEs" CLAUDE.md && \
grep -n "pip-audit runs automatically" .claude/rules/pre-commit.md && \
grep -n "pip-audit" .pre-commit-config.yaml | grep -v "skip:" | head -3 && \
grep -n "Known Vulnerabilities Template" docs/known-vulnerabilities-template.md
```

Expected: all six commands return at least one matching line.

- [ ] **Step 4: Verify section ordering in python.md**

```bash
grep -n "^## " .claude/rules/python.md
```

Expected:

```text
17:## File-Type Standards
18:## (blank)  <- not a heading, skip
...## Type Checking with BasedPyright
## FIPS 140-2/3 Compliance
## PyStrict-Aligned Ruff Rules
## Code Generation — Python-Specific
```

- [ ] **Step 5: Verify section ordering in git-workflow.md**

```bash
grep -n "^## " .claude/rules/git-workflow.md
```

Expected:

```text
## Branch Strategy (MANDATORY)
## Gate System
## GitHub Actions: Pin to Commit SHAs
## Git Worktrees
```

- [ ] **Step 6: Final commit if any fixup changes were needed**

If verification in Steps 1-5 required any corrections, stage and commit those:

```bash
git add -p  # review each hunk before staging
git commit -m "docs: fixup sprint-1 security compliance changes"
```

If no corrections were needed, skip this step.

---

## Completion Checklist

All items from the spec verified:

- [ ] pip-audit hook fires on dep file changes at pre-push stage
- [ ] pip-audit is in the CI skip list
- [ ] `rules/pre-commit.md` describes pip-audit as automatic, not manual
- [ ] `rules/python.md` contains the FIPS 140-2/3 compliance section with algorithm table
- [ ] `rules/git-workflow.md` contains the SHA pinning section between Gate System and Git Worktrees
- [ ] `docs/known-vulnerabilities-template.md` exists with valid frontmatter and passes `validate-front-matter`
- [ ] `CLAUDE.md` contains the unfixed CVE policy blockquote
- [ ] All pre-commit hooks pass on `--all-files`
- [ ] Branch is `docs/sprint-1-security-compliance` with clean, conventional commits
