---
schema_type: common
title: MkDocs Agent Pair Implementation Plan
status: draft
owner: engineering
purpose: Step-by-step implementation plan for mkdocs-auditor and mkdocs-specialist agents and their repo-compliance integration.
tags: [agents, mkdocs, documentation, compliance]
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create two production-ready agents, `mkdocs-auditor` (config lifecycle) and `mkdocs-specialist` (content creation and style), wired into the repo-compliance system with PAL secondary analysis.

**Architecture:** Two markdown agent files in `.claude/agents/` following the `pre-commit-auditor` pattern. The auditor owns `mkdocs.yml` in four modes (create/audit/remediate/update); the specialist owns page content quality and receives gap lists from the auditor. Both invoke PAL secondary analysis (Tier 1, always available; no mcp_config.yaml changes needed). The auditor integrates into repo-compliance as the `mkdocs` domain.

**Tech Stack:** Claude agent markdown files, YAML (standards-manifest.yaml), pytest for validate_front_matter.py --exclude tests, pre-commit hooks.

**Spec:** `docs/superpowers/specs/2026-04-27-mkdocs-agents-design.md`

**Note:** The `--exclude` flag for `validate_front_matter.py` may already exist if the `feat/gate-jobs-implementation` branch was merged to main. Check first in Task 2 and skip the implementation steps if it's already present.

---

## Implementation Tasks

### Task 1: Branch and Worktree Setup

**Files:**


- Create: `.worktrees/feat-mkdocs-agent-pair/` (git worktree)

- [ ] **Step 1: Create the feature branch from main and worktree**

```bash
git worktree add .worktrees/feat-mkdocs-agent-pair -b feat/mkdocs-agent-pair main
```

If the branch already exists on origin:

```bash
git worktree add .worktrees/feat-mkdocs-agent-pair feat/mkdocs-agent-pair
```

- [ ] **Step 2: Verify the worktree is on the correct branch**

```bash
git -C .worktrees/feat-mkdocs-agent-pair branch --show-current
```

Expected output: `feat/mkdocs-agent-pair`

- [ ] **Step 3: All subsequent steps run from the worktree root**

```bash
cd /home/byron/dev/.claude/.worktrees/feat-mkdocs-agent-pair
```

---

### Task 2: Tests and Implementation for validate_front_matter.py --exclude

**Files:**

- Modify: `tests/unit/test_validate_front_matter.py`
- Modify (if not already present): `tools/validate_front_matter.py`
- Modify (if not already present): `.pre-commit-config.yaml`

- [ ] **Step 1: Check whether --exclude is already implemented**

```bash
grep -n "exclude" tools/validate_front_matter.py | head -5
```

If the output includes `def _collect_md_files` accepting an `exclude` parameter: skip Steps 2-6 and jump to Step 7.

- [ ] **Step 2: Write the failing tests**

Open `tests/unit/test_validate_front_matter.py` and add these three functions after the last existing test:

```python
def test_collect_md_files_excludes_directory(
    vfm: ValidateFrontMatterModule, tmp_path: Path
) -> None:
    """Excluded directories are skipped during collection."""
    (tmp_path / "included.md").write_text("# Included")
    excluded_dir = tmp_path / "excluded"
    excluded_dir.mkdir()
    (excluded_dir / "report.md").write_text("# Report")

    result = vfm._collect_md_files([str(tmp_path)], exclude=[str(excluded_dir)])
    result_names = {p.name for p in result}
    assert "included.md" in result_names
    assert "report.md" not in result_names


def test_collect_md_files_excludes_specific_file(
    vfm: ValidateFrontMatterModule, tmp_path: Path
) -> None:
    """A specific file path is excluded when listed in exclude."""
    (tmp_path / "keep.md").write_text("# Keep")
    (tmp_path / "skip.md").write_text("# Skip")

    result = vfm._collect_md_files(
        [str(tmp_path)], exclude=[str(tmp_path / "skip.md")]
    )
    result_names = {p.name for p in result}
    assert "keep.md" in result_names
    assert "skip.md" not in result_names


def test_collect_md_files_no_exclude_collects_all(
    vfm: ValidateFrontMatterModule, tmp_path: Path
) -> None:
    """Without exclude, all markdown files in a directory are collected."""
    (tmp_path / "a.md").write_text("# A")
    (tmp_path / "b.md").write_text("# B")

    result = vfm._collect_md_files([str(tmp_path)])
    assert len(result) == 2
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
uv run pytest tests/unit/test_validate_front_matter.py::test_collect_md_files_excludes_directory tests/unit/test_validate_front_matter.py::test_collect_md_files_excludes_specific_file tests/unit/test_validate_front_matter.py::test_collect_md_files_no_exclude_collects_all -v
```

Expected: FAIL with `TypeError: _collect_md_files() got an unexpected keyword argument 'exclude'`.

- [ ] **Step 4: Replace _collect_md_files in tools/validate_front_matter.py**

Find and replace the entire `_collect_md_files` function:

```python
def _collect_md_files(paths: list[str], exclude: list[str] | None = None) -> list[Path]:
    """Collect Markdown files from the given path strings.

    Args:
        paths: List of file or directory path strings.
        exclude: Path prefixes to skip (matched against resolved path strings).

    Returns:
        List of Path objects for Markdown files found.
    """
    exclude_resolved = [Path(e).resolve() for e in (exclude or [])]
    md_files: list[Path] = []
    for path_str in paths:
        path = Path(path_str)
        if path.is_dir():
            for md in path.rglob("*.md"):
                resolved = md.resolve()
                if not any(
                    resolved == ex or ex in resolved.parents
                    for ex in exclude_resolved
                ):
                    md_files.append(md)
        elif path.suffix.lower() == ".md":
            resolved = path.resolve()
            if not any(
                resolved == ex or ex in resolved.parents for ex in exclude_resolved
            ):
                md_files.append(path)
    return md_files
```

- [ ] **Step 5: Add --exclude argument to argparse in tools/validate_front_matter.py**

Find `parser.add_argument("--emit-json", ...)` and add after it:

```python
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        metavar="PATH",
        help="Paths or directories to exclude from validation",
    )
```

- [ ] **Step 6: Wire exclude into the _collect_md_files call**

Find `md_files = _collect_md_files(args.paths)` and replace with:

```python
    md_files = _collect_md_files(args.paths, exclude=args.exclude)
```

Then update the `entry:` line in the `validate-front-matter` hook in `.pre-commit-config.yaml`:

```yaml
        entry: python tools/validate_front_matter.py docs --exclude docs/github-activity-reports docs/reference/github-repos.md
```

- [ ] **Step 7: Run the three tests and confirm all pass**

```bash
uv run pytest tests/unit/test_validate_front_matter.py::test_collect_md_files_excludes_directory tests/unit/test_validate_front_matter.py::test_collect_md_files_excludes_specific_file tests/unit/test_validate_front_matter.py::test_collect_md_files_no_exclude_collects_all -v
```

Expected: all three PASS.

- [ ] **Step 8: Run pre-commit on modified files**

```bash
git add tests/unit/test_validate_front_matter.py tools/validate_front_matter.py .pre-commit-config.yaml
pre-commit run --files tests/unit/test_validate_front_matter.py tools/validate_front_matter.py .pre-commit-config.yaml
```

Expected: all hooks PASS.

- [ ] **Step 9: Commit**

```bash
git commit -m "$(cat <<'EOF'
fix(tools): add --exclude flag to validate_front_matter.py

Allows the pre-commit hook to skip directories with non-conforming
frontmatter schemas (github-activity-reports, generated plan files).
Three tests added covering directory exclusion, file exclusion, and
the no-exclude baseline.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Add MKDOCS-* Checks to Standards Manifest

**Files:**

- Modify: `docs/standards-manifest.yaml`

- [ ] **Step 1: Find the last entry in the manifest**

```bash
grep -n "^- id:" docs/standards-manifest.yaml | tail -3
```

Note the last line number; you will append after it.

- [ ] **Step 2: Append MKDOCS-* entries at the end of docs/standards-manifest.yaml**

```yaml
# MkDocs Configuration Checks
- id: MKDOCS-001
  domain: mkdocs
  severity: critical
  description: "mkdocs.yml has site_url set"
  verify: "field_present: site_url"
  override_eligible: false

- id: MKDOCS-002
  domain: mkdocs
  severity: important
  description: "mkdocs.yml has repo_url set"
  verify: "field_present: repo_url"
  override_eligible: true

- id: MKDOCS-003
  domain: mkdocs
  severity: important
  description: "mkdocs.yml has repo_name set"
  verify: "field_present: repo_name"
  override_eligible: true

- id: MKDOCS-004
  domain: mkdocs
  severity: suggested
  description: "mkdocs.yml has edit_uri set"
  verify: "field_present: edit_uri"
  override_eligible: true

- id: MKDOCS-005
  domain: mkdocs
  severity: important
  description: "mkdocs.yml has copyright set"
  verify: "field_present: copyright"
  override_eligible: true

- id: MKDOCS-006
  domain: mkdocs
  severity: critical
  description: "mkdocs.yml has site_name set"
  verify: "field_present: site_name"
  override_eligible: false

- id: MKDOCS-007
  domain: mkdocs
  severity: suggested
  description: "mkdocs.yml has site_description set"
  verify: "field_present: site_description"
  override_eligible: true

- id: MKDOCS-008
  domain: mkdocs
  severity: suggested
  description: "mkdocs.yml has site_author set"
  verify: "field_present: site_author"
  override_eligible: true

- id: MKDOCS-009
  domain: mkdocs
  severity: suggested
  description: "No unused needs-proof markdown extensions configured in mkdocs.yml"
  verify: "scan_docs_for_extension_usage"
  override_eligible: true

- id: MKDOCS-010
  domain: mkdocs
  severity: important
  description: "toc.integrate not combined with navigation.sections or navigation.tabs"
  verify: "feature_conflict: toc.integrate"
  override_eligible: true

- id: MKDOCS-011
  domain: mkdocs
  severity: suggested
  description: "mkdocs-material has an upper-bound version pin in pyproject.toml or requirements"
  verify: "version_upper_bound: mkdocs-material"
  override_eligible: true

- id: MKDOCS-012
  domain: mkdocs
  severity: suggested
  description: "CI workflow includes a mkdocs build step"
  verify: "ci_contains: mkdocs build"
  override_eligible: true
```

- [ ] **Step 3: Verify YAML is well-formed**

```bash
pre-commit run check-yaml --files docs/standards-manifest.yaml
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/standards-manifest.yaml
git commit -m "$(cat <<'EOF'
feat(compliance): add MKDOCS-001 through MKDOCS-012 to standards manifest

Twelve new checks: required metadata fields (001-008), extension bloat
(009), feature conflict (010), version pinning (011), and docs CI
validation (012).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Create mkdocs-auditor Agent

**Files:**

- Create: `.claude/agents/mkdocs-auditor.md`

- [ ] **Step 1: Create the agent file**

Create `.claude/agents/mkdocs-auditor.md` with the content below. Copy exactly: the description field appears verbatim in the AGENTS-AND-SKILLS catalog and must be a single unbroken value:

````markdown
---
name: mkdocs-auditor
description: MkDocs configuration lifecycle agent for any project. Audits mkdocs.yml for required metadata, extension bloat, feature conflicts, version pinning, and docs CI coverage; remediates config violations in place; scaffolds a compliant mkdocs.yml from scratch; detects nav and content gaps post-sprint. Invoke in audit mode via repo-compliance, or standalone for create, remediate, and update modes.
model: sonnet
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
---

# MkDocs Auditor

MkDocs configuration lifecycle agent. Owns `mkdocs.yml` and nav structure entirely. Never authors page prose; hand content gaps to `mkdocs-specialist`.

## Modes

### create

Invoked when no `mkdocs.yml` exists in the project root. Scaffold a compliant file with:

- All required metadata fields populated. Derive `site_name` from the project directory name. Derive `copyright` from the current year and author in `pyproject.toml` or `git config user.name`. Prompt for `site_url`, `repo_url`, and `repo_name` if they cannot be inferred from existing config.
- Material theme with sensible feature defaults: no `toc.integrate`
- Only always-safe extensions enabled (see Config Rules below)
- Nav stub: Home entry pointing to `index.md` with a commented placeholder section

### audit

Read-only. Emit `FINDING` blocks for every violated rule. Always exit 0. Invoked by the repo-compliance coordinator for the `mkdocs` domain. Skip all checks and exit immediately if no `mkdocs.yml` exists in the project root.

After running rule-based checks, invoke `mcp__pal__chat` with model `qwen/qwen3.5-plus-02-15`: pass the full `mkdocs.yml` content and the preliminary finding list; ask for any issues the rule-based pass may have missed. Add PAL findings tagged `[PAL]`. If PAL adds nothing, note: "PAL secondary analysis: no additional findings."

### remediate

Patch an existing `mkdocs.yml` for config violations:

- Add missing required metadata fields (prompt for values that cannot be inferred)
- Remove confirmed-unused needs-proof extensions; add comment `# removed: no usage found in docs/` before removing the line
- Remove `toc.integrate` when `navigation.sections` or `navigation.tabs` are also present
- Add upper-bound version pin to `mkdocs-material` in `pyproject.toml` or `requirements*.txt`
- Suggest adding `mkdocs build --strict` as a CI step (do not edit CI files directly)

Does not touch nav entries or page content.

### update

Two-step process for post-sprint content sync.

**Step 1: Detect gaps**

- Nav entries pointing to non-existent files in `docs/` (dead entries)
- Files in `docs/` not referenced anywhere in the nav (orphaned pages)
- New agent files in `.claude/agents/` not covered by a nav entry
- New skill directories in `.claude/skills/` not covered by a nav entry
- New ADR files in `docs/architecture/adr/` not in nav
- New hook entries in `settings.json` not reflected in nav

**Step 2: Nav patch**

- Remove dead nav entries from `mkdocs.yml`
- Add stub nav entries for detected gaps (pointing to the not-yet-written file path)

End by emitting an ordered action list for `mkdocs-specialist`:

```text
Content gaps requiring authoring (pass to mkdocs-specialist):
  - docs/reference/agents.md: N new agents not covered: X, Y, Z
  - docs/contributing/adding-hooks.md: missing file, nav stub added
```

After both steps, invoke PAL secondary analysis same as audit mode.

## Config Rules

### Required Fields

These fields must be present and non-empty in `mkdocs.yml`. Severity: ERROR if absent.

`site_url`, `repo_url`, `repo_name`, `edit_uri`, `copyright`, `site_name`, `site_description`, `site_author`

### Extension Allowlist

**Always-safe** (include without usage verification): `abbr`, `admonition`, `attr_list`, `def_list`, `tables`, `toc`, `pymdownx.betterem`, `pymdownx.caret`, `pymdownx.details`, `pymdownx.emoji`, `pymdownx.highlight`, `pymdownx.inlinehilite`, `pymdownx.keys`, `pymdownx.mark`, `pymdownx.smartsymbols`, `pymdownx.superfences`, `pymdownx.tasklist`, `pymdownx.tilde`

**Needs-usage-proof**: flag WARN if configured but no matching syntax found in `docs/`:

| Extension | Grep pattern |
| --- | --- |
| `footnotes` | `\[\^` |
| `md_in_html` | `markdown="1"` |
| `pymdownx.tabbed` | `=== "` |
| `pymdownx.arithmatex` | `\$\$` |
| `content.tabs.link` | `=== "` |

In remediate mode: remove confirmed-unused extensions.

### Feature Conflicts

WARN when `toc.integrate` appears alongside `navigation.sections` or `navigation.tabs`. These compete for left-panel space on smaller viewports. Remediation: remove `toc.integrate`.

### Version Pinning

WARN if `mkdocs-material` in `pyproject.toml` or `requirements*.txt` has no upper-bound version pin (e.g., `>=9.5` without `<10`).

### Docs CI Validation

WARN if no CI workflow in `.github/workflows/` contains `mkdocs build`.

## FINDING Block Format

```text
FINDING
  id: MKDOCS-001
  domain: mkdocs
  severity: ERROR | WARN | INFO
  check: <rule name>
  file: mkdocs.yml
  line: <line number; 0 when file-level>
  description: <what is wrong>
  remediation: <what to do>
END FINDING
```

## Self-Review Wrap-up

After completing any mode, assess whether the session surfaced issues not covered by current rules. If yes, emit:

```text
Self-review: consider adding to mkdocs-auditor rules:
  - [new pattern identified during this session]
```

## Use Cases

Invoke for: new project mkdocs.yml setup (create), repo-compliance sweeps (audit), fixing existing config issues (remediate), post-sprint nav and content gap detection (update).
````

- [ ] **Step 2: Run pre-commit on the new file**

```bash
git add .claude/agents/mkdocs-auditor.md
pre-commit run --files .claude/agents/mkdocs-auditor.md
```

Expected: all hooks PASS. Note: the `validate-front-matter` hook only runs on `docs/**/*.md` files, so agent files are not subject to the schema check; that is correct behavior.

- [ ] **Step 3: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(agents): add mkdocs-auditor agent

Four-mode config lifecycle agent for mkdocs.yml: create (scaffold),
audit (FINDING blocks for repo-compliance), remediate (patch violations),
update (nav/content gap detection with mkdocs-specialist handoff).
Includes PAL secondary analysis with qwen/qwen3.5-plus-02-15 and
self-review wrap-up.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Create mkdocs-specialist Agent

**Files:**

- Create: `.claude/agents/mkdocs-specialist.md`

- [ ] **Step 1: Create the agent file**

Create `.claude/agents/mkdocs-specialist.md` with the content below:

````markdown
---
name: mkdocs-specialist
description: MkDocs page content creation and style enforcement agent. Authors missing or stale docs pages to a consistent Material theme standard covering required frontmatter, purpose admonition, heading hierarchy, semantic admonition usage, and OS-agnostic commands. Invoked after mkdocs-auditor update mode surfaces content gaps, or standalone for page authoring and content review.
model: sonnet
tools: ["Read", "Write", "Edit", "Grep", "Glob"]
---

# MkDocs Specialist

Content creation and style enforcement agent for MkDocs projects. Owns the quality and uniformity of page content. Never modifies `mkdocs.yml`; route nav changes to `mkdocs-auditor`.

## Page Structure Standard

Every page must follow this top-down order:

1. **Frontmatter** (required; see below)
2. **H1 title** matching the nav label exactly
3. **Purpose admonition** (`!!! info` or `!!! abstract`): one or two sentences stating what this page covers and who should read it
4. **Main content**: H2 sections, H3 subsections; never skip heading levels
5. **Related links** section at the bottom (optional but encouraged)

## Frontmatter Standard

```yaml
---
schema_type: common
title: Page Title
status: active
owner: engineering
purpose: One-line description of this page's function.
tags: [tag1, tag2]
---
```

## Material Theme Feature Usage

| Feature | When to use |
| --- | --- |
| `!!! note / tip / warning / danger` | Callouts with semantic meaning; don't decorate neutral text |
| `??? details` | Collapsible sections for optional deep-dives |
| Code blocks with language | Always specify language; never bare triple backtick |
| `=== "Tab"` tabbed blocks | Only when genuinely comparing alternatives side-by-side |

Admonition semantics: `!!! tip` is actionable advice; `!!! note` is neutral information; `!!! warning` is for genuine risk of data loss or misconfiguration only.

## Writing Style

- Active voice, second person for instructions: "Run the command" not "The command should be run"
- Present tense for current-state descriptions
- Imperative mood for step-by-step procedures
- No em-dashes anywhere
- Relative paths for all internal cross-references; never absolute URLs to the same site
- Unique heading text within each page (duplicate headings break anchor links)
- Define all domain acronyms at first use on each page

## Content Review Checks

When reviewing existing pages, flag:

- Frontmatter with missing required fields
- Pages without a purpose admonition immediately after the H1
- Heading level violations (H1 to H3 without H2, or H2 to H4 without H3)
- Bare code blocks with no language specified
- Admonitions used with wrong semantic intent
- OS-specific shell commands (`open`, `xdg-open`, `start`) without cross-platform alternatives or OS callouts
- CLI command documentation missing exit code tables
- Pages that mention significant disk or memory requirements without a callout block quantifying the cost
- Undefined acronyms or domain terms used before being defined

## Gap Authoring Workflow

When receiving a gap list from `mkdocs-auditor`:

1. Read the existing page (if stale) or examine codebase sources to understand the subject
2. Draft content following the Page Structure Standard above
3. Apply complete frontmatter
4. Verify all cross-references resolve to existing files
5. Report completion: list files written or updated; flag any links that need manual resolution

## PAL Secondary Analysis

After completing a content review or gap authoring task, invoke `mcp__pal__chat` with model `qwen/qwen3.5-plus-02-15`. Pass the page content and preliminary findings; ask for gaps in coverage, missing user-facing elements, or structural issues the initial review missed. Add PAL findings tagged `[PAL]`. If PAL adds nothing, note: "PAL secondary analysis: no additional findings."

## Self-Review Wrap-up

After completing any task, assess whether the session surfaced content patterns or style issues not covered by current standards. If yes, emit:

```text
Self-review: consider adding to mkdocs-specialist standards:
  - [new pattern identified during this session]
```

## Use Cases

Invoke for: authoring pages surfaced by mkdocs-auditor update mode, reviewing existing pages for style consistency, writing new documentation to Material theme standards.
````

- [ ] **Step 2: Run pre-commit on the new file**

```bash
git add .claude/agents/mkdocs-specialist.md
pre-commit run --files .claude/agents/mkdocs-specialist.md
```

Expected: all hooks PASS.

- [ ] **Step 3: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(agents): add mkdocs-specialist agent

Content creation and style enforcement agent for MkDocs pages.
Enforces page structure standard, frontmatter schema, Material theme
feature semantics, writing style, and content review checks including
OS-agnostic commands, exit code tables, and undefined term detection.
Includes PAL secondary analysis and self-review wrap-up.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Register Both Agents in AGENTS-AND-SKILLS.md

**Files:**

- Modify: `AGENTS-AND-SKILLS.md`

- [ ] **Step 1: Find where to insert the new entries**

```bash
grep -n "documentation\|Documentation\|Writing\|writing" AGENTS-AND-SKILLS.md | head -15
```

Locate the Writing and Documentation section. Find the last agent entry in that section before the next `##` heading begins.

- [ ] **Step 2: Insert a new MkDocs subsection after the last documentation agent entry**

Add the following block before the next section heading:

```markdown
### MkDocs

**[mkdocs-auditor](/.claude/agents/mkdocs-auditor.md)**
MkDocs configuration lifecycle agent for any project. Audits `mkdocs.yml` for required
metadata fields, extension bloat, feature conflicts, version pinning, and docs CI coverage.
Remediates violations in place, scaffolds a compliant `mkdocs.yml` from scratch, and
detects nav and content gaps post-sprint with a structured handoff to `mkdocs-specialist`.
Invoke in audit mode via repo-compliance, or standalone for create, remediate, and update modes.

**[mkdocs-specialist](/.claude/agents/mkdocs-specialist.md)**
MkDocs page content creation and style enforcement agent. Authors missing or stale docs
pages to a consistent Material theme standard: required frontmatter, purpose admonition,
heading hierarchy, semantic admonition usage, and OS-agnostic shell commands. Invoked
after `mkdocs-auditor` surfaces content gaps via update mode, or standalone for
content review and page authoring.
```

- [ ] **Step 3: Run pre-commit on AGENTS-AND-SKILLS.md**

```bash
git add AGENTS-AND-SKILLS.md
pre-commit run --files AGENTS-AND-SKILLS.md
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
docs(agents): register mkdocs-auditor and mkdocs-specialist in catalog

Add MkDocs subsection under Writing and Documentation in
AGENTS-AND-SKILLS.md with full descriptions for both agents.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Update Repo-Compliance Coordinator

**Files:**

- Modify: `.claude/skills/repo-compliance/SKILL.md`
- Modify: `.claude/skills/repo-compliance/workflows/interactive-mode.md`

- [ ] **Step 1: Find the Domain Agents table in SKILL.md**

```bash
grep -n "domain\|foundations\|pre_commit\|ossf" .claude/skills/repo-compliance/SKILL.md | head -15
```

Locate the table row format (e.g., `| foundations | repo-foundations-auditor | FOUND-* |`).

- [ ] **Step 2: Add mkdocs row to the Domain Agents table**

Insert the following row at the end of the domain table in `.claude/skills/repo-compliance/SKILL.md`:

```markdown
| mkdocs | mkdocs-auditor | MKDOCS-* (skipped when mkdocs.yml absent) |
```

- [ ] **Step 3: Find the dispatch list in interactive-mode.md**

```bash
grep -n "repo-foundations-auditor\|parallel\|dispatch" .claude/skills/repo-compliance/workflows/interactive-mode.md | head -10
```

Locate the bullet list of agents dispatched in parallel.

- [ ] **Step 4: Add mkdocs-auditor to the dispatch list**

Append one line to the parallel dispatch list:

```markdown
- `mkdocs-auditor` in audit mode (MKDOCS-* checks; skipped automatically when no mkdocs.yml is present in the project root)
```

- [ ] **Step 5: Run pre-commit on both modified files**

```bash
git add .claude/skills/repo-compliance/SKILL.md .claude/skills/repo-compliance/workflows/interactive-mode.md
pre-commit run --files .claude/skills/repo-compliance/SKILL.md .claude/skills/repo-compliance/workflows/interactive-mode.md
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(compliance): wire mkdocs-auditor into repo-compliance coordinator

Add mkdocs domain to the domain agents table in SKILL.md and to the
parallel dispatch list in interactive-mode.md. The auditor exits
immediately when no mkdocs.yml is present.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Final Validation

**Files:**

- No new files

- [ ] **Step 1: Run the full unit test suite**

```bash
uv run pytest tests/unit/ -v
```

Expected: all tests PASS, including the three new `--exclude` tests from Task 2.

- [ ] **Step 2: Run pre-commit across all staged files**

```bash
pre-commit run --all-files 2>&1 | grep -v "^docs/github-activity-reports\|^docs/superpowers/plans/i-need-you" | grep -E "Failed|Error|Passed" | head -30
```

Expected: all hooks show PASS. The excluded files in `docs/github-activity-reports/` and the one plans file are known pre-existing issues not caused by this branch.

- [ ] **Step 3: Confirm both agent files exist and are non-empty**

```bash
wc -l .claude/agents/mkdocs-auditor.md .claude/agents/mkdocs-specialist.md
```

Expected: both files have more than 50 lines.

- [ ] **Step 4: Confirm MKDOCS-* entries are in the manifest**

```bash
grep "domain: mkdocs" docs/standards-manifest.yaml | wc -l
```

Expected: `12`

- [ ] **Step 5: Create the pull request**

```bash
git push -u origin feat/mkdocs-agent-pair
gh pr create --title "feat: add mkdocs-auditor and mkdocs-specialist agents" --body "$(cat <<'EOF'
## Summary

- Creates `mkdocs-auditor`: four-mode config lifecycle agent (create/audit/remediate/update) with PAL secondary analysis using qwen/qwen3.5-plus-02-15 and self-review wrap-up
- Creates `mkdocs-specialist`: content creation and style enforcement following Material theme standards with PAL secondary analysis
- Adds MKDOCS-001 through MKDOCS-012 checks to `docs/standards-manifest.yaml`
- Wires `mkdocs-auditor` into repo-compliance coordinator (skipped when mkdocs.yml absent)
- Registers both agents in `AGENTS-AND-SKILLS.md`
- Adds `--exclude` flag to `validate_front_matter.py` with three new tests

## Test plan

- [ ] Three new pytest tests for `--exclude` all pass (`uv run pytest tests/unit/ -v`)
- [ ] Both agent files exist and have more than 50 lines each
- [ ] `docs/standards-manifest.yaml` contains exactly 12 MKDOCS-* entries
- [ ] `pre-commit run --all-files` shows no new failures beyond pre-existing ones
- [ ] `mkdocs-auditor` and `mkdocs-specialist` appear in `AGENTS-AND-SKILLS.md`
- [ ] repo-compliance `SKILL.md` shows mkdocs row in the domain agents table
- [ ] repo-compliance `interactive-mode.md` lists mkdocs-auditor in dispatch list

Generated with [Claude Code](https://claude.ai/claude-code)
EOF
)"
```

---

## Self-Review Notes

**Spec coverage check:**

| Spec requirement | Task |
| --- | --- |
| mkdocs-auditor: create mode | Task 4 |
| mkdocs-auditor: audit mode with FINDING blocks | Task 4 |
| mkdocs-auditor: remediate mode | Task 4 |
| mkdocs-auditor: update mode with gap report | Task 4 |
| PAL secondary analysis (auditor) | Task 4 |
| Self-review wrap-up (auditor) | Task 4 |
| Extension allowlist (always-safe vs needs-proof) | Task 4 |
| Feature conflict rule (toc.integrate) | Tasks 3, 4 |
| Version pinning rule | Tasks 3, 4 |
| Docs CI validation rule | Tasks 3, 4 |
| Required metadata fields | Tasks 3, 4 |
| mkdocs-specialist: page structure standard | Task 5 |
| mkdocs-specialist: content review checks | Task 5 |
| mkdocs-specialist: OS-specific command flag | Task 5 |
| mkdocs-specialist: exit code table check | Task 5 |
| PAL secondary analysis (specialist) | Task 5 |
| Self-review wrap-up (specialist) | Task 5 |
| AGENTS-AND-SKILLS.md registration | Task 6 |
| repo-compliance integration (audit mode only) | Task 7 |
| MKDOCS-* manifest entries | Task 3 |
| validate_front_matter.py --exclude tests | Task 2 |
| PAL uses qwen/qwen3.5-plus-02-15 | Tasks 4, 5 |
