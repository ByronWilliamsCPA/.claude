---
title: "Architecture Decision Records (moved)"
schema_type: common
status: published
owner: core-maintainer
purpose: "Redirect to the canonical ADR location."
tags:
  - adr
  - architecture
  - decisions
---

The Architecture Decision Records have moved. The numbered ADR log and the working ADR
template now live in one place:

- **ADR index and log:** [`docs/architecture/adr/index.md`](../architecture/adr/index.md)
- **Slim working template (use this for new ADRs):** [`docs/architecture/adr/_template.md`](../architecture/adr/_template.md)
- **When to write an ADR and the full process:** [`docs/contributing/writing-adrs.md`](../contributing/writing-adrs.md)

This directory is retained only for [`adr-template.md`](adr-template.md), the longer
reference variant of the template kept for unusually consequential decisions and linked
from the slim template and `CONTRIBUTING.md`. Do not add new ADRs here; add them under
`docs/architecture/adr/`.

> Note: `docs/planning/adr/` is a separate, cookiecutter-scaffolded location used by the
> `project-planning` skill when generating ADRs for downstream projects. It is not this
> repository's ADR store.
