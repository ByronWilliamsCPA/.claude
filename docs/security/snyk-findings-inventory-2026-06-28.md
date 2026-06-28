---
title: "Snyk Findings Inventory: .claude Repository"
schema_type: common
status: published
owner: core-maintainer
purpose: "Full inventory of Snyk IDE findings for the .claude repo as of 2026-06-28, categorized by ownership (vendored submodule vs gitignored venv vs owned source), with the authoritative owned-source residual confirmed by a live Snyk CLI scan after exclusions."
tags:
  - security
  - compliance
---

> **Date:** 2026-06-28
> **Branch:** `chore/snyk-scope-cleanup`
> **Tooling:** Snyk CLI 1.1305.2 (authed), Snyk IDE plugin (org: `williaby`)
> **Companion:** [snyk-remediation-plan-2026-06-28.md](snyk-remediation-plan-2026-06-28.md)

## Executive summary

The Snyk IDE panel reports **234 Code issues and ~229 Open Source vulnerabilities**.
A file-by-file mapping plus a live Snyk CLI scan establishes the decisive fact:

> **100% of the reported findings are in code this repository does not own.**
> Every flagged path resolves to a vendored submodule under `.submodules/` or
> the gitignored Python virtualenv under `.venv/`. After applying exclusions that
> mirror the repo's existing isolation policy, the **owned-source residual is 13
> Snyk Code findings, 0 critical, 0 high.**

This is therefore not a 234-issue code-fixing sprint. It is primarily a **Snyk
scope-configuration task**: make Snyk honor the same boundary that trufflehog,
ruff, basedpyright, bandit, interrogate, coverage, and qlty already respect.

## Why these findings are not owned

| Boundary | Evidence | Existing policy |
| --- | --- | --- |
| `.submodules/**` | 8 git submodules (vendored upstream repos). `git ls-files` confirms their contents are not tracked by this repo. | Excluded from every pre-commit hook and quality gate (`.pre-commit-config.yaml` lines 77-81, 403-417). "Never edit submodule content directly." |
| `.venv/**` | Gitignored Python virtualenv; installed packages, not source. | `git check-ignore .venv` = ignored. |
| `site/**` | mkdocs build output. | Gitignored. |

The owned, tracked source surface is small: **93 Python files and 1 JavaScript
file** (a meta-harness template asset). There are **zero owned `package.json`
files**, so every "Open Source Security" vulnerability in the panel belongs to a
dependency of a vendored submodule or an installed venv package.

## Part A: Open Source Security (~229 vulnerabilities) -- all vendored/venv

Mapping from the IDE panel labels to disk:

| Panel label | Vulns | Resolves to | Owned? |
| --- | --- | --- | --- |
| `package.json` staging | 55 | `.venv/.../jupyterlab/staging/package.json` | No (venv) |
| `package.json` staging (2nd) | 55 | duplicate venv jupyterlab manifest | No (venv) |
| `package.json` site | 31 | `.submodules/jeffallan-claude-skills/site/package.json` | No (submodule) |
| `package.json` server | 23 | `.submodules/agents-observe/app/server/package.json` | No (submodule) |
| `package.json` test-hyphens-underscore | 16 | submodule test fixture | No (submodule) |
| `package.json` (additional) | balance | other `.submodules/*` and `.venv/*` npm manifests | No |

There is no owned npm dependency tree to remediate. Owned **Python** dependency
risk is covered separately by `pip-audit` (the dependency scanner of record per
CLAUDE.md) and tracked in [known-vulnerabilities.md](../known-vulnerabilities.md).

## Part B: Code Security (158 issues in IDE) -- all vendored after exclusion

The IDE Code Security panel's visible entries all resolve to submodules:

| Panel label | Issues | Resolves to |
| --- | --- | --- |
| `server.cjs` scripts | 5 | `.submodules/superpowers/skills/brainstorming/scripts/server.cjs` |
| `server.ts` discord | 2 | `.submodules/anthropics-plugins/external_plugins/discord/server.ts` |
| `server.ts` fakechat | 2 | `.submodules/anthropics-plugins/external_plugins/fakechat/server.ts` |
| `redlining.py` validators | 4 | `.submodules/anthropics-skills/skills/{docx,xlsx,pptx}/scripts/office/validators/redlining.py` |

## Part C: Authoritative owned-source residual (live scan, post-exclusion)

`snyk code test` run against the main working tree with `.submodules/`, `.venv/`,
and `site/` excluded. **No vendored or venv path leaked through the exclusions.**

**Total: 13 findings -- 0 critical, 0 high, 2 warning (medium), 11 note (low).**

| Severity | Rule | File:line | Disposition |
| --- | --- | --- | --- |
| warning | `python/CommandInjection` | `scripts/populate-github-repos.py:82` | Real. Env var flows into `subprocess.run`. Review/sanitize. |
| warning | `python/Ssrf` | `scripts/check_quality_gate.py:69` | Real but low risk. CLI arg flows into `urllib.request.urlopen` in local CI tooling. Review or ignore-with-justification. |
| note | `python/InsecureHash/test` | `tests/fixtures/fips/bad_hashlib.py:8` | **Intentional fixture.** FIPS-compat negative test input. Ignore with justification. |
| note | `python/InsecureHash/test` | `tests/fixtures/fips/bad_new_call.py:16` | **Intentional fixture.** Ignore with justification. |
| note | `python/InsecureHash/test` | `tests/fixtures/fips/bad_sha1.py:15` | **Intentional fixture.** Ignore with justification. |
| note | `python/PT` (path traversal) | `.claude/skills/panel/scripts/consensus_cli.py:630` | CLI arg into `pathlib.Path`. Local tool; low risk. |
| note | `python/PT` | `.claude/skills/panel/scripts/consensus_cli.py:800` | Same pattern. |
| note | `python/PT` | `.claude/skills/test-coverage/scripts/parse_coverage.py:98` | CLI arg into `pathlib.Path`. |
| note | `python/PT` | `.claude/skills/test-coverage/scripts/parse_coverage.py:63` | CLI arg into `open`. |
| note | `python/PT` | `scripts/generate_python_tier_repos.py:53` | CLI arg into `pathlib.Path`. |
| note | `python/PT` | `scripts/doc-audit.py:176` | CLI arg into path concatenation. |
| note | `python/PT` | `scripts/doc-audit.py:566` | CLI arg into path concatenation. |
| note | `python/PT` | `scripts/populate-github-repos.py:332` | CLI arg into `os.replace`. |

### Blocked: Snyk Open Source on owned Python deps

`snyk test` could not run: `uv 0.9.26 is not supported. Minimum required version
is 0.9.29`. Owned Python dependency scanning remains covered by `pip-audit`;
enabling Snyk OSS here is optional (see remediation plan, item 5).

## Counts at a glance

| Bucket | Count | Actionable in this repo? |
| --- | --- | --- |
| OSS vulns in `.venv/` npm manifests | ~110 | No (not owned, gitignored) |
| OSS vulns in `.submodules/` npm manifests | ~119 | No (upstream's responsibility) |
| Code issues in `.submodules/` | ~145 | No (upstream's responsibility) |
| Owned Code findings, intentional fixtures | 3 | Ignore-with-justification |
| Owned Code findings, real (medium) | 2 | Yes -- triage/fix |
| Owned Code findings, low (CLI path inputs) | 8 | Yes -- review, fix or ignore |
| Owned OSS (Python deps) | unknown (scan blocked) | Covered by pip-audit |
