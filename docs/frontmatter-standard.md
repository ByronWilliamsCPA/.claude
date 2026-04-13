---
title: "Frontmatter Standard"
schema_type: common
status: published
owner: core-maintainer
purpose: "Reference for the YAML frontmatter schema used in docs/ files."
tags:
  - documentation
  - reference
  - front_matter
---

Every markdown file under `docs/` that is part of the built site carries YAML frontmatter. The schema is enforced by `tools/validate_front_matter.py` using Pydantic models defined in `tools/frontmatter_contract/models.py`. The validator has `extra="forbid"`: unknown fields cause hard errors, so treat the schema as closed.

## Required Fields (CommonFM)

Every page uses `schema_type: common` unless it is a script, knowledge, or planning doc (see below for those variants).

```yaml
---
title: "Page title"
schema_type: common
status: draft | in-review | published
owner: core-maintainer | team-lead | documentation | engineering
purpose: "One-sentence summary that ends with a period."
tags:
  - tag_one
  - tag_two
---
```

| Field | Required | Constraints |
| --- | --- | --- |
| `title` | yes | String. Renders as H1 when the body has no `# Heading`. |
| `schema_type` | yes | Literal `common`, `script`, `knowledge`, or `planning`. |
| `status` | yes | One of `draft`, `in-review`, `published`. There is no `deprecated` or `superseded`; use an H2 banner in the body if needed. |
| `owner` | yes | Must match a key in [docs/_data/owners.yml](_data/owners.yml). Currently: `core-maintainer`, `team-lead`, `documentation`, `engineering`. |
| `purpose` | yes | Must end with `.`, `!`, or `?`. |
| `tags` | yes | List of snake_case strings. Every tag must be present in [docs/_data/tags.yml](_data/tags.yml). |

## Optional Fields

- `description`: longer prose summary; falls through to search engines.
- `review_cycle_days`: integer in `[1, 365]` for periodic review scheduling.
- `authors`: list of `{name, orcid}` objects.
- `model` / `dataset`: schema.org-aligned metadata for ML-related content.

## Audience Is a Tag, Not a Field

The plan calls for dual-audience documentation (new developer vs technical maintainer). Because the schema is closed, "audience" is represented via tags rather than a dedicated field:

| Audience | Tag |
| --- | --- |
| New developer onboarding | `new_dev` |
| Technical maintainer / architecture reader | `technical` |
| Both | use both tags |

The `nav:` block in `mkdocs.yml` drives what readers actually see; tags are metadata for search, future filtering, and maintainer intent.

## Variants

- **`schema_type: script`**: adds `name`, `usage`, `behavior`, and `category` for tool/script pages.
- **`schema_type: knowledge`**: adds `agent_id` for AI-assisted workflow knowledge base entries.
- **`schema_type: planning`**: adds `component` and `source` for planning and strategy documents.

See `tools/frontmatter_contract/models.py` for the full Pydantic definitions.

## Validation

Run the validator locally before committing docs changes:

```bash
uv run python tools/validate_front_matter.py docs
```

Add `--fix` to apply safe autofixes (tag normalization, punctuation). Add `--emit-json` for machine-readable output.

## Why no `audience` field

The plan originally proposed adding `audience`, `category`, and `last_updated` fields. All three would require a schema change to `CommonFM` and would break every existing doc on first validation run. Tags are sufficient for metadata and discovery; navigation drives the reader experience directly via `mkdocs.yml`. This is captured in `docs/architecture/adr/ADR-007-dual-audience-docs.md`.
