---
schema_type: common
title: "OpenSSF Scorecard policy for solo-maintainer repos"
status: published
owner: core-maintainer
purpose: "Documents which Scorecard checks are intentionally capped on solo-dev repos and the conditions under which the cap would lift."
tags:
  - compliance
  - reference
  - standards
---

This policy documents the OpenSSF Scorecard checks where solo-maintainer
constraints intentionally cap the score below the default target. It does
not waive the checks; it records the structural reason each cap exists,
the restoration condition, and the explicit decision to accept the score
penalty rather than introduce friction that produces no review value.

Cross-reference: the shared `validate_solo_dev_safe` guard enforces this
policy at the ruleset layer. Both `scripts/setup_org_rulesets.py` (for
the ByronWilliamsCPA organization) and `scripts/setup_repo_rulesets.py`
(for williaby per-repo rulesets) import the same guard. Any body with
`required_approving_review_count > 0` raises `SoloDevViolationError` and
exits non-zero before the API call. The guard is the structural backstop
for what this doc declares as policy.

## Scope

Applies to every repo across both maintained owners: the ByronWilliamsCPA
GitHub organization and the williaby user account. All projects under
both owners are solo-maintained with no second contributor.

## Capped checks

### Branch-Protection (Scorecard default 6+, accepted floor 4)

**Scorecard default target:** 6+ (Tier 2: 1 required reviewer, dismiss
stale reviews, require up-to-date branches).

**Accepted score:** 4 (Tier 1: required status checks present, no
required reviewers).

**Why capped:** Tier 2 requires `required_approving_review_count >= 1`.
GitHub does not allow a PR author to approve their own PR. On a solo-dev
repo, setting any non-zero value would block every merge unconditionally.
The accepted ruleset baseline is therefore `required_approving_review_count: 0`,
which caps the Branch-Protection score at Tier 1.

**Restoration condition:** A second contributor joins one of the
maintained owners and is willing to participate in PR review on a regular
cadence. At that point:

1. Update the universal ruleset JSON bodies in
   `docs/reference/org-rulesets/` to set
   `required_approving_review_count: 1`. Optionally also set
   `require_last_push_approval: true` for stricter post-approval push
   gating (the solo baseline intentionally keeps this `false` because
   there is only one actor; switching to `true` is the recommended
   hardening once a real second reviewer exists).
2. Update the williaby per-repo ruleset bodies in
   `docs/reference/repo-rulesets/` (`_williaby-template-universal.json`
   and `_williaby-template-python.json`) to the same values.
3. Remove or relax the `validate_solo_dev_safe` guard in
   `scripts/setup_org_rulesets.py` and `scripts/setup_repo_rulesets.py`.
4. Re-apply both org rulesets and the williaby per-repo rulesets.
5. Update cross-referencing docs that currently state the solo-dev
   assumption. Before declaring the restoration complete, grep
   `docs/` for `required_approving_review_count` and `solo.dev` and
   reconcile each hit. Known references include
   `docs/reference/repo-compliance.md` (Solo-Developer Constraints),
   `docs/PROJECT_SETUP.md`, `docs/reference/github-workflow-audit.md`
   (BP-6 exception note), and any plan documents under
   `docs/superpowers/plans/`.

### Code-Review (target 4, accepted floor 0)

**Default target:** 4+ (40%+ of recent commits went through a PR with
review).

**Accepted score:** 0 in practice (no PR is reviewed by a second party).

**Why capped:** The metric measures actual merge history. On solo-dev
repos every PR is opened and merged by the same account. The
git-workflow.md policy ("Never commit directly to `main`, `master`, or
`develop`") satisfies a procedural review trail but the Scorecard tool
reads GitHub's merge data directly, not the policy.

**Restoration condition:** Same as Branch-Protection. Once a second
contributor reviews 40%+ of merged commits over the rolling Scorecard
window, the score climbs without further config change.

## Checks that are NOT capped by this policy

The following Scorecard checks remain at their default targets and any
failure is a real finding, not a policy-accepted gap. The list reflects
the Scorecard check set as of 2026-05 and may need refreshing when
OpenSSF adds new checks upstream:

- Binary-Artifacts
- CI-Tests
- CII-Best-Practices (Passing badge target; the check name remains
  `CII-Best-Practices` upstream even though the badge itself rebranded
  to "OpenSSF Best Practices")
- Dangerous-Workflow
- Dependency-Update-Tool
- Fuzzing (Silver-only)
- License
- Maintained
- Packaging (when applicable)
- Pinned-Dependencies
- SAST
- Security-Policy
- Signed-Releases (when applicable)
- Token-Permissions
- Vulnerabilities

Any agent or auditor that produces remediation copy for these checks
must continue to recommend the standard remediation. The cap only
applies to Branch-Protection and Code-Review.

### Soft carve-out (not a formal cap)

**Contributors** remains at its default target and is NOT subject to
the formal cap mechanics above, but a Contributors score of 0-3 is
acceptable for solo repos pursuing only the Passing badge level. Do
not lift to 4 by fabricating contributor activity; an auditor should
note the score informationally rather than emit it as a finding. This
is a soft carve-out tied to badge ambition, not a structural cap.

## How this interacts with audit findings

When the `ossf-compliance-auditor` agent or any other compliance auditor
runs:

- Branch-Protection scoring 4 with the standard ruleset applied is
  **not** a finding. Do not generate remediation copy that recommends
  lifting `required_approving_review_count` above 0.
- Branch-Protection scoring below 4 (e.g., no required status checks,
  no required reviewers, or no protection at all on the default branch)
  **is** a finding. The cap only applies to the reviewer-count
  requirement; other Scorecard criteria measured by this check still
  drive the score. Note: org-ruleset rules such as `copilot_code_review`
  and signature requirements are tracked separately from the Scorecard
  Branch-Protection metric and do not affect this check's score.
- Code-Review scoring below 4 is **not** a finding. Do not generate
  remediation copy that suggests the score will rise once
  Branch-Protection Tier 2 is enforced; that path is closed by this
  policy.
- Any other Scorecard check below its target is a finding and should
  receive standard remediation.

## Review cadence

This policy is reviewed annually or when the maintainer composition
changes. The most recent review confirms the solo-dev assumption is
unchanged across both owners.

| Field | Value |
| --- | --- |
| Policy first declared | 2026-04-29 |
| Last reviewed | 2026-05-16 |
| Next scheduled review | 2027-04-29 |
| Restoration trigger | Second contributor joins either owner |
