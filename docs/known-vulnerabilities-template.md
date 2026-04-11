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

> Tracks CVEs that cannot be immediately resolved. Review quarterly.
> No entry may age past 60 days without reassessment — escalate or resolve.

<!-- Copy the entry below for each new CVE. Delete this comment in your project's file. -->

## CVE-YYYY-XXXXX — Package Name vX.Y

| Field | Value |
| --- | --- |
| **Severity** | Critical / High / Medium |
| **CVSS Score** | X.X |
| **Affected package** | package-name >= X.Y, < X.Z |
| **Patched version** | X.Z (not yet released / available but breaks X) |
| **Date documented** | YYYY-MM-DD |
| **Reassessment due** | YYYY-MM-DD (60 days max) |

**Exploitation scenario**: Describe what an attacker needs to exploit this in your context.

**Why deferred**: Specific reason — upstream unpatched, breaking API change required, etc.

**Compensating control**: What reduces the risk while the CVE remains open.

**Planned resolution**: Target version, migration path, or timeline.
