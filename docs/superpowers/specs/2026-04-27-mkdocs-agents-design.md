---
schema_type: common
title: MkDocs Agent Pair Design
status: published
owner: engineering
purpose: >
  Design spec for two new agents covering the full MkDocs lifecycle:
  mkdocs-auditor (config, nav, compliance) and mkdocs-specialist (content creation and style).
tags: [agents, mkdocs, documentation, compliance]
---

**Date:** 2026-04-27 | **Status:** Approved

**Trigger:** Review of GLEIF implementation identified recurring mkdocs.yml config gaps and
content uniformity issues that Claude produces without guardrails.

## Problem Statement

MkDocs projects accumulate two distinct categories of issues when built without agent oversight:

1. **Configuration gaps**: missing metadata fields (site_url, repo_url, copyright), unused
   extensions adding build overhead, and feature conflicts in the Material theme nav features.
2. **Content inconsistency**: pages authored at different times lack uniform structure,
   admonition usage, heading hierarchy, and writing style.

Neither the existing `doc-audit` skill (markdown content health) nor the `documentation-writer`
agent (general technical writing) covers these concerns specifically.

## Solution: Two-Agent Architecture

Following the `diagram-maintenance-agent` / `diagram-specialist` pattern, two focused agents
cover the full MkDocs lifecycle with a clean boundary between structural/config concerns and
content craft.

```text
mkdocs-auditor (update mode)
  → produces gap report
      → mkdocs-specialist (content creation)
          → authors missing/stale pages to style standard
              → mkdocs-auditor (audit mode) validates nav is clean
```

---

## Agent 1: mkdocs-auditor

**File:** `.claude/agents/mkdocs-auditor.md`
**Model:** sonnet
**Tools:** Read, Write, Edit, Bash, Grep, Glob

### Scope

Owns `mkdocs.yml` entirely and the nav structure within it. Never writes prose content
into markdown pages. Handoff to `mkdocs-specialist` for content authoring.

### Modes

#### create

Invoked when no `mkdocs.yml` exists in the project root. Scaffolds a compliant file with:

- All required metadata fields (see Required Fields below)
- Material theme with sensible feature defaults (no toc.integrate)
- Only always-safe extensions pre-enabled
- Nav stub with a Home entry pointing to `index.md` and a commented placeholder section

#### audit

Read-only. Emits `FINDING` blocks compatible with the repo-compliance coordinator format.
Checks all rules in the Config Rules and Nav Rules sections below.
Exit behavior: always exits 0, findings go to stdout as structured blocks.

Invoked by `repo-compliance` coordinator for the `mkdocs` domain.

#### remediate

Patches an existing `mkdocs.yml` for config violations:

- Adds missing required metadata fields (prompts for values if not inferable)
- Removes or comments out bloat extensions confirmed unused
- Resolves documented feature conflicts

Does not touch nav entries or page content.

#### update

Two-step process for post-sprint content sync:

**Step 1: Detect gaps:**

- Nav entries pointing to non-existent files in `docs/` (dead entries)
- Files in `docs/` not referenced anywhere in the nav (orphaned pages)
- Codebase items with no corresponding doc coverage: new agent files in
  `.claude/agents/`, new skill directories in `.claude/skills/`, new ADR files
  in `docs/architecture/adr/`, new hook entries in `settings.json`

**Step 2: Nav patch:**

- Removes dead nav entries
- Adds stub nav entries for detected gaps (pointing to the not-yet-written file path)
- Does NOT create content files

Ends by emitting an ordered action list for handoff to `mkdocs-specialist`:

```text
Content gaps requiring authoring (pass to mkdocs-specialist):
  - docs/reference/agents.md: 3 new agents not covered: X, Y, Z
  - docs/architecture/hook-pipeline.md: stale, hook count changed 4 → 7
  - docs/contributing/adding-hooks.md: missing file, nav stub added
```

### Config Rules

#### Required Fields (audit/remediate)

These fields must be present and non-empty in every `mkdocs.yml`:

| Field | Impact if missing |
| --- | --- |
| `site_url` | Canonical URLs broken, sitemap has no domain |
| `repo_url` | Material "Edit this page" button absent |
| `repo_name` | GitHub header link absent |
| `edit_uri` | Edit button points nowhere |
| `copyright` | Footer renders empty |
| `site_name` | Browser tab title is blank |
| `site_description` | SEO metadata absent |
| `site_author` | Attribution missing |

#### Extension Allowlist

**Always-safe**: these may be included without usage verification:

```text
abbr, admonition, attr_list, def_list, tables, toc,
pymdownx.betterem, pymdownx.caret, pymdownx.details, pymdownx.emoji,
pymdownx.highlight, pymdownx.inlinehilite, pymdownx.keys, pymdownx.mark,
pymdownx.smartsymbols, pymdownx.superfences, pymdownx.tasklist, pymdownx.tilde
```

**Needs-usage-proof**: flag as WARN if configured but no matching syntax found in `docs/`:

| Extension | Syntax to scan for |
| --- | --- |
| `footnotes` | `[^` (footnote reference pattern) |
| `md_in_html` | `markdown="1"` attribute |
| `pymdownx.tabbed` | `=== "` (tabbed block opener) |
| `pymdownx.arithmatex` | `$$` or `$[^$]` (math delimiters) |
| `content.tabs.link` | tabbed content (same scan as tabbed) |

In remediate mode: remove confirmed-unused needs-proof extensions. Add a comment in the
file noting the removal reason before deleting the entry.

#### Feature Conflicts

Flag as WARN when `toc.integrate` appears alongside `navigation.sections` or
`navigation.tabs`. These three features compete for left-panel space on smaller viewports.
Remediation: remove `toc.integrate` and let the TOC occupy the standard right-side
position (Material default).

#### Dependency Version Pinning

Flag as WARN if `mkdocs-material` in `pyproject.toml` or `requirements*.txt` has no
upper-bound version pin (e.g., `mkdocs-material>=9.5` without `<10`). Major version bumps
break `toc.integrate`, nav rendering, and pymdownx interplay without warning.
Remediation: add `<N+1` upper bound matching the currently installed major version.

#### Docs CI Validation

Flag as WARN if no CI workflow file in `.github/workflows/` contains a `mkdocs build`
step. Without a build step, broken internal links and config errors go undetected in PRs.
Remediation: suggest adding `mkdocs build --strict` as a CI step.

### PAL Secondary Analysis

In audit and update modes, after completing the initial rule-based analysis and before
emitting final findings, invoke `mcp__pal__chat` with model `qwen/qwen3.5-plus-02-15` to
perform a secondary review. Pass the full `mkdocs.yml` content and the preliminary finding
list. Ask PAL to identify any issues the rule-based pass may have missed.

Incorporate any new findings into the final output, tagged `[PAL]` to distinguish them
from rule-based findings. If PAL confirms existing findings without adding new ones, note
"PAL secondary analysis: no additional findings."

Do not invoke PAL in create or remediate modes; those are deterministic operations.

### Self-Review Wrap-up (all modes)

After completing any mode, the agent assesses whether the session surfaced issues not
covered by current rules. If yes, it emits a brief note:

```text
Self-review: consider adding to mkdocs-auditor rules:
  - [new pattern or check identified during this session]

Self-review: consider adding to mkdocs-specialist standards:
  - [new content pattern identified during this session]
```

This output is informational only. The agent does not self-modify. The note is addressed
to the developer to decide whether to update the agent files.

### FINDING Block Format

```text
FINDING
  id: MKDOCS-001
  domain: mkdocs
  severity: ERROR | WARN | INFO
  check: <rule name>
  file: mkdocs.yml
  line: <line number; 0 when the finding is file-level>
  description: <what is wrong>
  remediation: <what to do>
END FINDING
```

---

## Agent 2: mkdocs-specialist

**File:** `.claude/agents/mkdocs-specialist.md`
**Model:** sonnet
**Tools:** Read, Write, Edit, Grep, Glob

### Scope

Owns the quality and uniformity of mkdocs page content. Invoked when:

- `mkdocs-auditor` update mode produces a gap list requiring authoring
- A contributor is writing a new doc page and wants style enforcement
- Existing pages need content review and consistency updates

Never modifies `mkdocs.yml`. Nav changes route back to `mkdocs-auditor`.

### Page Structure Standard

Every page must follow this top-down order:

1. **Frontmatter** (required; see below)
2. **H1 title** matching the nav label
3. **Purpose admonition** (`!!! info` or `!!! abstract`): one or two sentences stating
   what this page covers and who should read it
4. **Main content**: H2 sections, H3 subsections, never skipping levels
5. **Related links** section at the bottom (optional but encouraged)

### Frontmatter Standard

Every page must open with valid frontmatter:

```yaml
---
schema_type: common          # common | planning | adr
title: Page Title
status: active               # active | draft | deprecated
owner: Byron Williams
purpose: One-line description of this page's function
tags: [tag1, tag2]
---
```

### Material Theme Feature Usage

Use Material features consistently across pages:

| Feature | When to use |
| --- | --- |
| `!!! note / tip / warning / danger` | Callouts with semantic meaning; don't decorate neutral text |
| `??? details` | Collapsible sections for optional deep-dives |
| Code blocks with language | Always specify language; never bare triple backtick |
| `=== "Tab"` tabbed blocks | Only when genuinely comparing alternatives side-by-side |

Do not mix admonition types arbitrarily. A `!!! tip` is actionable advice; a `!!! note` is
neutral information. Use `!!! warning` only for genuine risk of data loss or misconfiguration.

### Writing Style

- Active voice, second person for instructions: "Run the command" not "The command should be run"
- Present tense for current-state descriptions
- Imperative mood for step-by-step procedures
- No em-dashes anywhere (hard rule from global CLAUDE.md)
- Relative paths for all internal cross-references, never absolute URLs to the same site
- Heading text must be unique within a page (duplicate headings break anchor links)

### Gap Authoring Workflow

When receiving a gap list from `mkdocs-auditor`:

1. Read the existing page (if stale) or understand the subject from codebase sources
2. Draft content following the Page Structure Standard
3. Apply frontmatter
4. Check that all cross-references resolve to existing files
5. Report completion: list of files written or updated, any links that need manual resolution

### Content Review Mode

When invoked to review existing pages for consistency:

- Check each page for frontmatter completeness
- Flag pages that skip the purpose admonition
- Flag heading level violations (H1 to H3 without H2)
- Flag bare code blocks with no language
- Flag admonitions used with wrong semantic intent
- Flag OS-specific shell commands (`open`, `xdg-open`, `start`) without
  cross-platform alternatives or OS callouts
- Flag CLI reference pages that document commands without exit code tables
- Flag pages that mention significant disk or memory requirements without
  a callout block quantifying the cost
- Flag undefined acronyms or domain terms used before being defined
- Emit a findings list; apply fixes on request

### PAL Secondary Analysis

After completing a content review pass or gap authoring task, invoke `mcp__pal__chat`
with model `qwen/qwen3.5-plus-02-15` to perform a secondary quality check. Pass the
page content and the preliminary findings list. Ask PAL to identify gaps in coverage,
missing user-facing elements (exit codes, OS callouts, undefined terms), or structural
issues the initial review missed.

Incorporate PAL findings tagged `[PAL]` into the final output. If PAL confirms the
existing review without additions, note "PAL secondary analysis: no additional findings."

### Self-Review Wrap-up

After completing any authoring or review task, assess whether the session surfaced
content patterns, recurring gaps, or style issues not covered by current standards.
If yes, emit a note following the same format as the mkdocs-auditor self-review.
The agent does not self-modify; the note is for the developer to act on.

---

## Repo-Compliance Integration

The `repo-compliance` coordinator invokes `mkdocs-auditor` in audit mode only when a
`mkdocs.yml` is present in the project root. The coordinator passes domain `mkdocs` to
distinguish these findings from other domains.

`mkdocs-specialist` is not part of the compliance sweep; it is a standalone creative/authoring
agent.

---

## Registration

After implementation, both agents must be added to `AGENTS-AND-SKILLS.md` under the
Documentation section and `pre-commit run --all-files` must pass.

Both agents require PAL MCP access for secondary analysis. Add both agent names to the
appropriate bundle in `mcp/mcp_config.yaml` under `tier_2_agent_bundles` so the
`mcp__pal__chat` tool is available to them at runtime.

---

## Out of Scope

- `mike` versioning support (no versioning plugin in use)
- `mkdocstrings` autodoc configuration (Python API documentation)
- Custom theme overrides (the `overrides/` directory)
- Build validation (`mkdocs build --strict`); left to CI
