# 07 - Documentation and Developer Experience

The primary entry docs (README, CLAUDE.md) have zero broken internal links and `docs/getting-started/install.md` is accurate and complete. The problems cluster in three places: the README Quick Start omits the submodule and setup steps that the install guide documents (so a copy-paste Quick Start leaves a broken checkout), `AGENTS-AND-SKILLS.md` uses 83 root-absolute links that 404 on GitHub, and the MkDocs strict build has 85-plus pages that are neither in nav nor excluded. Several count claims (submodules, permissions, agents) have drifted from reality.

## DOC-01 - README Quick Start omits submodule init and setup.sh

- Severity: High
- Effort: S (align the Quick Start block with the install guide; basis: a few lines)
- Evidence: `README.md:80-92` Quick Start omits both `git clone --recurse-submodules` and `./setup.sh`. The correct sequence appears only later at `README.md:283-284` and in `docs/getting-started/install.md:29-48`. This checkout demonstrates the failure mode: 14 dangling `.claude/agents/` symlinks point into unpopulated submodules.
- Recommendation: Update the Quick Start to include `--recurse-submodules` (or a `git submodule update --init`) and `./setup.sh` so the first copy-paste produces a working install.

## DOC-02 - 83 root-absolute links in AGENTS-AND-SKILLS.md 404 on GitHub

- Severity: High
- Effort: M (convert 83 links to relative paths; basis: bulk edit plus link verification)
- Evidence: `AGENTS-AND-SKILLS.md` uses 83 links of the form `](/.claude/...)`. Root-absolute paths resolve against the web host, so they 404 on GitHub and break under MkDocs. README and CLAUDE.md use zero such links (0 broken).
- Recommendation: Rewrite the 83 links as repo-relative paths (`.claude/...` or `../...`) and add a link-check to CI for this file.

## DOC-03 - ADR-008 missing from mkdocs.yml nav

- Severity: Medium
- Effort: S (one nav line; basis: single edit)
- Evidence: ADR-008 exists on disk and in the ADR index, but `mkdocs.yml` nav stops at ADR-007.
- Recommendation: Add ADR-008 to the mkdocs nav under the ADR section.

## DOC-04 - MkDocs strict build has 85-plus pages not in nav and not excluded

- Severity: High
- Effort: M (triage 85-plus pages into nav or exclude_docs; basis: per-page decision across several dirs)
- Evidence: `.github/workflows/docs.yml:57` runs `mkdocs build --strict`. Roughly 85-plus docs, including `docs/superpowers/` (44) and `docs/development/` (14), are neither listed in nav nor in `exclude_docs`, which `--strict` treats as an error. (If the docs CI is currently green, an exclusion the audit did not locate is in play; verify before bulk-editing.)
- Recommendation: Add the orphaned pages to nav or to `exclude_docs` in `mkdocs.yml`. Confirm the current docs.yml run status first to scope the gap precisely.

## DOC-05 - Submodule count and names drift in install docs

- Severity: Medium
- Effort: S (correct the count and names; basis: text edit)
- Evidence: `docs/getting-started/install.md:32` says "five submodules"; `.gitmodules` defines 7. README submodule names also mismatch the actual `.gitmodules` entries.
- Recommendation: Update install.md and README to list all 7 submodules by their actual names from `.gitmodules`.

## DOC-06 - permissions.ask count claim is stale

- Severity: Medium
- Effort: S (update one number; basis: text edit)
- Evidence: `.claude/rules/settings-and-permissions.md:40` claims 22 `permissions.ask` entries; `settings.json` actually has 30.
- Recommendation: Update the claim to 30, or replace the hard number with a generated count to stop future drift.

## DOC-07 - Three local agents undocumented; doc-audit agent count off by one

- Severity: Medium
- Effort: S (add three catalog entries, fix the counter; basis: catalog edits plus one-line script fix)
- Evidence: Three agents present locally are missing from the catalog: `cleanup-backlog-scout`, `compliance-synthesis`, `ossf-criteria-reference`. `scripts/doc-audit.py` agent count is off by one because it counts `.claude/agents/CLAUDE.md` as an agent.
- Recommendation: Add the three agents to `AGENTS-AND-SKILLS.md` and exclude `CLAUDE.md` from the agent count in `doc-audit.py`.

## DOC-08 - CHANGELOG format is inconsistent

- Severity: Low
- Effort: M (normalize to Keep a Changelog and one generator; basis: large file cleanup)
- Evidence: 3,645-line CHANGELOG with no Keep-a-Changelog header, a mix of manual and semantic-release formatting, and HTML-escaped arrows.
- Recommendation: Add the Keep-a-Changelog header and let `python-semantic-release` own the format going forward; do not hand-edit released sections.

## Clean areas

- README and CLAUDE.md internal links: 0 broken. All 39 MkDocs nav targets that are listed resolve.
- Frontmatter present on all non-vendored docs. `docs/getting-started/install.md` is accurate and complete; all referenced scripts and paths exist.

## Machine-readable findings

```json
[
  {"id": "DOC-01", "title": "README Quick Start omits submodule init and setup.sh", "domain": "docs", "severity": "High", "effort": "S", "files": ["README.md"], "evidence": "README.md:80-92 Quick Start omits --recurse-submodules and ./setup.sh; correct sequence only at README.md:283-284 and docs/getting-started/install.md:29-48; checkout shows 14 dangling .claude/agents/ symlinks", "recommendation": "Add --recurse-submodules (or submodule update --init) and ./setup.sh to the Quick Start block.", "cve": ""},
  {"id": "DOC-02", "title": "83 root-absolute links in AGENTS-AND-SKILLS.md 404 on GitHub", "domain": "docs", "severity": "High", "effort": "M", "files": ["AGENTS-AND-SKILLS.md"], "evidence": "AGENTS-AND-SKILLS.md uses 83 ](/.claude/...) root-absolute links that 404 on GitHub and break in MkDocs; README and CLAUDE.md have 0", "recommendation": "Rewrite the 83 links as repo-relative paths and add a link-check to CI.", "cve": ""},
  {"id": "DOC-03", "title": "ADR-008 missing from mkdocs.yml nav", "domain": "docs", "severity": "Medium", "effort": "S", "files": ["mkdocs.yml"], "evidence": "ADR-008 exists on disk and in the ADR index but mkdocs nav stops at ADR-007", "recommendation": "Add ADR-008 to the mkdocs nav under the ADR section.", "cve": ""},
  {"id": "DOC-04", "title": "MkDocs strict build has 85-plus pages not in nav and not excluded", "domain": "docs", "severity": "High", "effort": "M", "files": [".github/workflows/docs.yml", "mkdocs.yml"], "evidence": "docs.yml:57 runs mkdocs build --strict; ~85+ docs (docs/superpowers/ 44, docs/development/ 14, others) are neither in nav nor exclude_docs", "recommendation": "Add orphaned pages to nav or exclude_docs; confirm current docs.yml run status first.", "cve": ""},
  {"id": "DOC-05", "title": "Submodule count and names drift in install docs", "domain": "docs", "severity": "Medium", "effort": "S", "files": ["docs/getting-started/install.md", "README.md"], "evidence": "install.md:32 says five submodules; .gitmodules defines 7; README submodule names also mismatch", "recommendation": "Update install.md and README to list all 7 submodules by their actual .gitmodules names.", "cve": ""},
  {"id": "DOC-06", "title": "permissions.ask count claim is stale", "domain": "docs", "severity": "Medium", "effort": "S", "files": [".claude/rules/settings-and-permissions.md", "settings.json"], "evidence": "settings-and-permissions.md:40 claims 22 permissions.ask entries; settings.json has 30", "recommendation": "Update the claim to 30 or replace the hard number with a generated count.", "cve": ""},
  {"id": "DOC-07", "title": "Three local agents undocumented; doc-audit agent count off by one", "domain": "docs", "severity": "Medium", "effort": "S", "files": ["AGENTS-AND-SKILLS.md", "scripts/doc-audit.py"], "evidence": "cleanup-backlog-scout, compliance-synthesis, ossf-criteria-reference missing from the catalog; doc-audit.py counts .claude/agents/CLAUDE.md as an agent", "recommendation": "Add the three agents to the catalog and exclude CLAUDE.md from the agent count in doc-audit.py.", "cve": ""},
  {"id": "DOC-08", "title": "CHANGELOG format is inconsistent", "domain": "docs", "severity": "Low", "effort": "M", "files": ["CHANGELOG.md"], "evidence": "3645-line CHANGELOG with no Keep-a-Changelog header, mixed manual/semantic-release format, HTML-escaped arrows", "recommendation": "Add the Keep-a-Changelog header and let python-semantic-release own the format; stop hand-editing released sections.", "cve": ""}
]
```
