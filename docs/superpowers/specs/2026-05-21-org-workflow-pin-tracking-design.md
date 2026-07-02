---
schema_type: common
title: Org Workflow Pin Tracking Design
status: draft
owner: engineering
tags: [compliance, ci_cd, github_actions, security, dependencies, standards]
purpose: Design for tracking canonical SHA pins for org-owned reusable workflows, detecting stale pins in consumer repos, and automating updates via Renovate-driven PRs on a semver release cadence.
---

**Date**: 2026-05-21
**Status**: Draft
**Author**: Byron Williams

> **Superseded in part (2026-07-02)**: the `followTag: "v1"` mechanism this
> design specifies is being retired via ByronWilliamsCPA/.github PR #244
> (open as of 2026-07-02; the `v1` tag itself is already deleted on both
> orgs). The org tag-protection ruleset forbids re-pointing `v*` tags, so
> the floating `v1` tag froze at the v1.1.0 commit and `followTag` silently
> froze all consumer SHA-pin updates with it. Since `release-tag.yml` cuts
> an immutable `vX.Y.Z` tag on every push to main, plain semver tracking
> (no `followTag`) delivers the release-cadence behavior this design wanted.
> CI-057 now requires the absence of `followTag`. The registry-currency
> (CI-055) and stale-pin detection (CI-056) portions of this design remain
> valid. Sections below that describe the retired mechanism carry their own
> historical markers.

---

## Problem

Repos across `ByronWilliamsCPA` and `williaby` pin to org reusable workflows
using full 40-character commit SHAs, satisfying CI-005. Example:

```yaml
uses: ByronWilliamsCPA/.github/.github/workflows/python-ci.yml@eb529609e38f05eb713419e4ee9cfff9cc95decc  # main
```

When the org updates a workflow (security fix, new feature, breaking change),
there is no mechanism to:

1. Know what the canonical "current" SHA is for consumers to target
2. Detect which consumer repos are behind
3. Push updates to those repos in a consistent, auditable way

The `ByronWilliamsCPA/.github` repo has had `v1.0.0` and `v1` tags since
2026-05-09, but both point to the same commit and main is 45+ commits ahead.
No release workflow exists. Consumers are not systematically updated when
workflows change.

## Goals

- Cut a semver tag on `ByronWilliamsCPA/.github` on every merge to main
- Maintain a registry in this repo documenting the canonical current tag and
  SHA per source org
- Surface stale pins as compliance findings during `/repo-audit`
- Let Renovate handle the actual per-consumer PR workflow automatically
- Keep CI-005 passing: consumers always pin to a full SHA, never a mutable ref

## Non-Goals

- Changing how CI-005 validates SHA pinning (it continues to require 40-char SHAs)
- Managing third-party action pins (those stay under Renovate's standard `github-actions` config)
- Building a cross-repo write automation for the registry (a scheduled sync job handles this)

## Architecture

```text
ByronWilliamsCPA/.github (source)
        |
        |  1. PR merges to main
        |  2. release-tag.yml cuts a semver tag (v1.1.0 + floating v1)
        v
     GitHub tag on .github repo
        |
        |  3. sync-org-pins.yml runs daily in ByronWilliamsCPA/.claude
        |     reads latest tag + SHA via GitHub API, updates registry file
        v
docs/org-workflow-pins.yaml  <-- source of truth for current canonical pin
        |
        |  4. /repo-audit dispatches CI agent
        |     CI-055: registry matches latest tag on GitHub?
        |     CI-056: consumer repo pins match registry current_sha?
        |     CI-057: consumer repo Renovate config targets org workflow source?
        v
  Compliance findings (stale pins surfaced per-repo)
        |
        |  5. Renovate (running in each consumer repo)
        |     reads ByronWilliamsCPA/.github directly, detects new tag,
        |     opens SHA-update PR to the consumer repo
        v
  Consumer repo PR: update @old_sha -> @new_sha # v1.1.0
```

## Components

### 1. Release Tagging Workflow (`ByronWilliamsCPA/.github`)

> **Historical (superseded 2026-07-02)**: steps 5-6 and the closing
> paragraph below describe force-moving a floating `v1` tag.
> `release-tag.yml` no longer maintains any floating major tag; the `v1`
> tag is deleted and the org tag-protection ruleset makes every `v*` tag
> immutable. Steps 1-4 (immutable `vX.Y.Z` tagging) remain current.

**File**: `.github/workflows/release-tag.yml`
**Trigger**: `push` to `main`
**Permissions**: `contents: write`

Steps:
1. Fetch the most recent semver tag on the repo to determine the previous version
2. Inspect the merge commit message for conventional commit type:
   - `BREAKING CHANGE` footer or `!` modifier: major bump
   - `feat:` prefix: minor bump
   - `fix:`, `chore:`, `docs:`, `ci:`, `refactor:`, `perf:`, `test:`: patch bump
3. Compute the new version string
4. Create an annotated tag (`v1.1.0`) at HEAD with the version in the tag message
5. Force-move the floating major-version tag (`v1`) to HEAD
6. Push both tags via `GITHUB_TOKEN` (no external secret required)

Annotated tags are used (not lightweight) so creation date and tagger identity
are preserved for audit queries.

The floating `v1` tag is safe to maintain because CI-005 enforces full SHA pins
in consumer repos. The `v1` tag is human-readable documentation; nothing actually
pins to it at runtime.

### 2. Pin Registry (`docs/org-workflow-pins.yaml`)

A new file in this repo, separate from `docs/reusable-workflow-jobs.yaml`.
Separation of concerns: `reusable-workflow-jobs.yaml` tracks what check names
workflows produce; this file tracks what version consumers should pin to.

```yaml
# Canonical SHA pins for org workflow source repos.
# Updated by sync-org-pins.yml. Consumers should pin to current_sha.
# Compliance: CI-055 verifies registry matches latest tag; CI-056 verifies
# consumer repos match registry current_sha; CI-057 verifies Renovate config.

sources:
  ByronWilliamsCPA/.github:
    current_tag: v1.1.0
    current_sha: 1b2d33c47cc11a96b9757b49f41873c54e75f57c
    last_synced: '2026-05-21'

  williaby/.github:
    current_tag: v1.0.0
    current_sha: ea8e19054eac195e6ab7bc93e9c2319632560b77
    last_synced: '2026-05-21'
```

One entry per source repo, not per workflow file. A single tag covers the entire
repo, so all consumers use the same SHA regardless of which workflow they call.

### 3. Registry Sync Workflow (`ByronWilliamsCPA/.claude`)

**File**: `.github/workflows/sync-org-pins.yml`
**Trigger**: `schedule: cron: '0 6 * * *'` and `workflow_dispatch`
**Permissions**: `contents: write`

Steps:
1. For each source in `docs/org-workflow-pins.yaml`, call
   `gh api repos/<org>/<repo>/tags` to get the latest tag name and commit SHA
2. Compare against `current_tag` and `current_sha` in the file
3. If different: update the YAML in place, set `last_synced` to today, commit
   with message `chore(pins): sync org workflow pins to <tag>`, push to main
4. If no change: exit cleanly with a log note

Uses the repo's own `GITHUB_TOKEN`. Only reads from source repos (public,
no special token needed) and writes to this repo (its own token). No
cross-repo secret required.

The daily cadence means up to 24h lag between a tag being cut and the registry
updating. `workflow_dispatch` lets an operator sync immediately after a release.

### 4. New Compliance Checks

Three new entries added to `docs/standards-manifest.yaml` in the CI domain.

**CI-055** (severity: important)
```yaml
description: "docs/org-workflow-pins.yaml current_sha matches the latest tag SHA
  on GitHub for each source repo"
verify: "registry_current: docs/org-workflow-pins.yaml, source=github_tags, max_lag_hours=24"
override_eligible: true
```
Fires when the sync job has not run since a new tag was cut. The CI agent
fetches the latest tag SHA from the GitHub API and diffs it against the file.
Findings older than 24 hours from the tag creation date are reported.

**CI-056** (severity: important)
```yaml
description: "All uses: references to org workflow source repos in .github/workflows/*.yml
  match the current_sha in docs/org-workflow-pins.yaml"
verify: "uses_sha_matches_registry: .github/workflows/*.yml, docs/org-workflow-pins.yaml"
override_eligible: true
```
Fires on any consumer repo where a `uses: ByronWilliamsCPA/.github/...@<sha>` or
`uses: williaby/.github/...@<sha>` does not match the registry's `current_sha`.

**CI-057** (severity: important)

> **Historical (superseded 2026-07-02)**: the entry below is the original
> followTag-mandating version. The live manifest entry now requires the
> ABSENCE of `followTag`; see `docs/standards-manifest.yaml` CI-057.

```yaml
description: "renovate.json contains a packageRules entry targeting org workflow
  source repos with followTag set to the floating major version tag"
verify: "content_present: renovate.json, ByronWilliamsCPA/.github"
override_eligible: true
not_applicable_when: "repo does not use org reusable workflows (no ByronWilliamsCPA/.github
  or williaby/.github in .github/workflows/*.yml)"
```
Verifies Renovate is configured to track org workflow pins. Skipped silently if
the repo does not call any org reusable workflow.

All three checks are `override_eligible: true` because a legitimate reason
to stay on an older SHA (incident investigation, staged rollout) should be
documentable in `.claude/compliance-overrides.md`.

### 5. Renovate Consumer Config

> **Historical (superseded 2026-07-02)**: the example and explanation below
> show the retired `followTag` mechanism. Current consumer config omits
> `followTag` entirely and relies on plain semver tag tracking; CI-057 now
> FAILS any renovate.json that sets a `"followTag":` key.

Each consumer repo's `renovate.json` needs a `packageRules` entry:

```json
{
  "packageRules": [
    {
      "matchManagers": ["github-actions"],
      "matchPackagePatterns": ["ByronWilliamsCPA/.github", "williaby/.github"],
      "versioning": "semver",
      "followTag": "v1"
    }
  ]
}
```

`followTag: "v1"` tells Renovate to resolve against the floating major-version
tag rather than raw HEAD commits. Every non-tagged commit to `.github` (docs,
config tweaks) does not trigger a consumer PR; only tagged releases do.

The PR Renovate opens replaces the old SHA with the tag's SHA and adds a
`# v1.x.x` comment. CI-005 continues to pass because the pin is still a full
40-char SHA.

## Data Flow: Full Lifecycle

1. A PR merges to `ByronWilliamsCPA/.github` with commit message `feat(ci): add vulture dead-code scan`
2. `release-tag.yml` detects `feat:` prefix, bumps minor version, creates `v1.2.0` and moves `v1`
3. At 06:00 UTC the next day, `sync-org-pins.yml` runs in `.claude`, detects the new tag, updates `docs/org-workflow-pins.yaml` to `current_tag: v1.2.0`, commits
4. During the next `/repo-audit` sweep, the CI agent runs CI-056 on each consumer, finds repos still pinned to the old SHA, emits FINDING
5. Renovate (running on its own schedule in each consumer) detects the `v1` tag has moved, opens a PR: `chore(deps): update ByronWilliamsCPA/.github org workflows to v1.2.0`
6. Consumer merges the Renovate PR; CI-056 FINDING clears on the next audit

## Error Handling

- **No tags on source repo**: `sync-org-pins.yml` logs a warning and exits without modifying the registry. CI-055 fires, prompting manual tagging.
- **Semver parse failure** (no prior tag, malformed tag): `release-tag.yml` defaults to `v0.1.0` as the initial version and logs the fallback.
- **Registry write conflict**: The sync workflow uses `git pull --rebase` before committing to handle concurrent runs cleanly.
- **Consumer repo has no Renovate**: CI-057 fires as an important finding; remediation adds the `packageRules` entry.

## Files Changed

| Repo | File | Action |
|------|------|--------|
| `ByronWilliamsCPA/.github` | `.github/workflows/release-tag.yml` | Create |
| `williaby/.github` | `.github/workflows/release-tag.yml` | Create (identical workflow; both repos are synchronized and need independent version tags) |
| `ByronWilliamsCPA/.claude` | `docs/org-workflow-pins.yaml` | Create |
| `ByronWilliamsCPA/.claude` | `.github/workflows/sync-org-pins.yml` | Create |
| `ByronWilliamsCPA/.claude` | `docs/standards-manifest.yaml` | Add CI-055, CI-056, CI-057 |
| Each consumer repo | `renovate.json` | Add `packageRules` entry (fleet sweep) |

## Open Questions

None. All design decisions resolved during brainstorming session 2026-05-21.
