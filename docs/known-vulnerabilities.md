---
schema_type: common
title: "Known Vulnerabilities"
status: published
owner: core-maintainer
purpose: "Tracks CVEs in project dependencies that cannot be immediately resolved."
tags:
  - security
  - dependencies
---

> Tracks CVEs that cannot be immediately resolved. Review quarterly.
> No entry may age past 60 days without reassessment; escalate or resolve.
> The OpenSSF release gate blocks releases for any vulnerability older than 60 days.

<!-- Add a new entry below for each CVE using the template format. -->

## No current vulnerabilities

No open CVEs as of 2026-04-21. Run `uv run pip-audit` to check for new findings.

When a vulnerability is found that cannot be resolved immediately, add an entry:

| Field | Value |
| --- | --- |
| **Severity** | Critical / High / Medium |
| **CVSS Score** | X.X |
| **Affected package** | package-name >= X.Y, < X.Z |
| **Patched version** | X.Z (not yet released / available but breaks X) |
| **Date documented** | YYYY-MM-DD |
| **Reassessment due** | YYYY-MM-DD (60 days max) |

**Exploitation scenario**: Describe what an attacker needs to exploit this in your context.

**Why deferred**: Specific reason: upstream unpatched, breaking API change required, etc.

**Compensating control**: What reduces the risk while the CVE remains open.

**Planned resolution**: Target version, migration path, or timeline.
