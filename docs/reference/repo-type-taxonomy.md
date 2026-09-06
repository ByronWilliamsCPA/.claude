---
schema_type: common
title: "Repository Type Taxonomy"
status: draft
owner: core-maintainer
purpose: "Defines the seven repository types used in the compliance catalog and their audit exemption profiles."
tags:
  - reference
  - taxonomy
  - compliance
  - technical
---

Every entry in `docs/reference/github-repos.json` carries a `repositoryType` field.
The repo-compliance skill reads this field to select which checks apply vs. which
are exempt. Type profiles are defined in `_meta.typeProfiles`.

## Types

| Type | Scorecard Floor | Scorecard Target | Notes |
|------|-----------------|------------------|-------|
| `python-package` | 7.0 | 8.5 | Published to PyPI; full toolchain applies |
| `python-app` | 7.0 | 8.5 | Deployed app; release/SBOM workflows exempt |
| `python-script` | 6.0 | 7.5 | Scripts/automation; basedpyright/docstrings exempt |
| `config` | 5.0 | 7.0 | Dotfiles/settings; Python toolchain fully exempt |
| `infrastructure` | 5.0 | 7.0 | IaC/homelab; Python toolchain fully exempt |
| `docs-only` | 4.0 | 6.0 | Docs/GitHub Pages; Python toolchain exempt |
| `template` | 5.0 | 7.5 | Cookiecutter templates; placeholder code exempt |

## Assigning a Type

When classifying a new or existing repo:

1. Does it have a `src/` layout and a PyPI publish workflow? -> `python-package`
2. Does it have Python code but no PyPI release? -> `python-app`
3. Does it have Python scripts only (no `src/`, no formal structure)? -> `python-script`
4. Is it primarily dotfiles, settings, or configuration files? -> `config`
5. Is it Terraform, Ansible, Helm, or homelab configs? -> `infrastructure`
6. Is it documentation pages with no executable code? -> `docs-only`
7. Is it a Cookiecutter or other project template? -> `template`

## Exemption Semantics

An exempt workflow/hook means the audit will not flag its absence as a FINDING.
The universal `idealEntry` still represents the full ideal; type profiles define
the minimum viable compliance floor per type.

## Boundary Cases

**`config` and `infrastructure` repos retain `detectSecrets`:** Secret scanning
is language-agnostic. Even repos that contain no Python code can contain
credentials, API keys, or tokens in configuration files. Exempting Python-specific
tools (ruff, basedpyright, bandit) does not exempt security hygiene.

**`codeql.yml` is retired fleet-wide (2026-09), not type-scoped:** GitHub's CodeQL
code scanning now requires paid GitHub Advanced Security (Code Security); the
former per-type exemption for `docs-only` (CodeQL cannot run on documentation
files alone) no longer applies because `codeql.yml` was removed from every repo
regardless of type. Do not log a `codeql.yml`-absence finding for any type.
`sonarcloud.yml` is unaffected: SonarCloud can analyze text-based content and
may still surface doc quality issues on `docs-only` repos; it remains in scope
unless a specific repo has no content SonarCloud can evaluate.

**Infrastructure repos with embedded Python:** Some Ansible playbooks or Terraform
modules include embedded Python scripts or Lambda functions. If a repo's Python
content exceeds incidental tooling, reclassify it as `python-script` or
`python-app`. The `infrastructure` type is intended for repos where Python is
absent or negligible.
