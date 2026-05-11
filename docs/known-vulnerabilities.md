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

## PYSEC-2022-42969: py v1.11.0

| Field | Value |
| --- | --- |
| **Severity** | High |
| **CVSS Score** | 7.5 |
| **Affected package** | py >= 1.11.0 (all versions) |
| **Patched version** | None published; `py` is in maintenance-only mode |
| **Date documented** | 2026-05-11 |
| **Reassessment due** | 2026-07-10 |

**Exploitation scenario**: ReDoS (Regular Expression Denial of Service) in `py.path.svnwc` when processing attacker-controlled SVN working-copy path strings. Requires calling `py.path.svnwc` directly with untrusted input. This project uses `py` only as a transitive test dependency pulled in by pytest tooling; no code path calls `py.path.svnwc` or accepts SVN paths from external input.

**Why deferred**: The `py` package has no maintained release channel for security patches. The upstream project is effectively in maintenance-only mode with no published fix. The dependency cannot be dropped without removing pytest compatibility shims that would require broader test infrastructure changes.

**Compensating control**: `py` is a dev/test-only dependency not present in the production release. The vulnerable code path (`py.path.svnwc`) is never called in this project. No user-controlled input reaches the ReDoS pattern.

**Planned resolution**: Remove `py` when pytest fully deprecates its compatibility shim (expected with pytest 9.x). Reassess against the upstream issue tracker on 2026-07-10; if still unresolved and pytest 9 is stable, migrate and drop `py`.
