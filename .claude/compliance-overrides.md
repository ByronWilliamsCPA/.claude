---
schema_type: internal
title: Compliance Overrides
status: published
owner: engineering
tags: [compliance]
purpose: Documents intentional deviations from global standards for this repository. Each entry suppresses the named check during compliance audits.
---

## Compliance Overrides

Add one row per intentional deviation. Only checks marked `override_eligible: true`
in the standards manifest can be suppressed here. Critical security checks
(`override_eligible: false`) are always enforced regardless of entries here.

| Check ID | Reason | Approved By | Date |
|----------|--------|-------------|------|

## How to Add an Override

1. Find the check ID in `~/.claude/docs/standards-manifest.yaml`
   (`~/.claude/` is the global Claude standards repo; run `setup.sh` from that
   repo if you see "no such file")
2. Confirm `override_eligible: true` for that check
3. Add a row above with the check ID, business reason, your name, and today's date
4. Commit the change with message: `chore(compliance): add override for <CHECK-ID>`
