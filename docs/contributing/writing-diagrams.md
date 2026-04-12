---
title: "Writing Diagrams"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Guide for authoring and maintaining PlantUML architecture diagrams."
tags:
  - contributing
  - documentation
  - architecture
---

## PlantUML Conventions

- Store `.puml` sources under `docs/architecture/diagrams/`.
- Commit both the `.puml` source and a rendered `.svg` sibling.
- Use plain PlantUML (no external `!include` directives that require network access).
- Keep each diagram focused on one concept — if you need to show two things, use two diagrams.

## Offline Rendering

We do **not** render diagrams in CI. Rationale: no Graphviz/Java dependency at build time, faster mkdocs builds, and the `.svg` commit gives every reviewer a byte-identical artifact to inspect in PR diffs. This policy replaces the standalone ADR that v1 of the plan proposed.

## Regenerating SVGs

```bash
./scripts/render_diagrams.sh
```

Renders all `docs/architecture/diagrams/*.puml`. Pass a specific path to render one.

Alternatives:

- **`diagram-maintenance` skill** — use in a Claude Code session on a `.puml` source.
- **VS Code** — PlantUML extension, `Alt+D` to preview.
- **`plantuml -tsvg <file>.puml`** — direct CLI if `plantuml` is on PATH.

## When to Commit SVG Siblings

Always, in the same commit as the `.puml` source change. Reviewers see the `.svg` diff without having to render locally.

## Excluding PUML from the mkdocs Build

`mkdocs.yml` excludes `architecture/diagrams/*.puml` from the build because mkdocs cannot render PUML without an external plugin. The SVG siblings are rendered directly via standard markdown `![alt](file.svg)` embeds.

## See Also

- [Diagrams Index](../architecture/diagrams/index.md)
- [ADR-007 Dual-Audience Documentation Structure](../architecture/adr/ADR-007-dual-audience-docs.md)
