# Standards Manifest Change Policy

> **Status**: Active | Reference Standard | **Version**: 1.1.0 | **Last Updated**: 2026-05-28
>
> Conventional-commits classification, CHANGELOG conventions, and PR-splitting guidance
> for changes to `docs/standards-manifest.yaml`. Load on demand when modifying the manifest.

## Scope

This standard applies to any commit that adds, removes, or modifies an entry in
`docs/standards-manifest.yaml`. Per [ADR-006](../../docs/architecture/adr/ADR-006-rules-vs-standards.md),
it lives in `.claude/standards/` rather than `.claude/rules/` because it only matters
when working on the manifest, not on every session.

It does NOT govern:

- Changes to consumers of the manifest (e.g., `.claude/agents/devops-deployment-agent.md`
  audit-workflow updates that don't touch the manifest itself). Those follow the parent
  rule in `.claude/rules/git-workflow.md`.
- Changes to manifest tooling (`scripts/check-repo-compliance.py`, etc.). Treat those as
  ordinary code changes under the same rule.

When a single PR touches both the manifest and its consumers, classify by the manifest
change (the higher-impact half).

## Why this exists

PR #116 review (2026-05-17) surfaced a real classification ambiguity: the PR broadened
an existing check's scope (`fix:` is natural) AND added a brand-new check ID (`feat:`
is natural). The two halves shipped together because the vulnerability they closed
required both. The chosen prefix (`fix:`) was defensible but not the only honest answer.

Conventional Commits 1.0 leaves "fix vs feat" intentionally underspecified. Without a
codified rule for this manifest, every new check addition triggers the same debate.
This standard fixes the rule so the debate happens once.

## Classification rule

| Change | Type | Rationale |
| --- | --- | --- |
| Add CI-014 for a previously-unchecked enforcement area | `feat(compliance):` | No preceding gap; new capability |
| Add CI-007b to close a documented XXE-escape path | `fix(compliance):` | New ID, but closes incident; PR #116 precedent. NOTE: PR #116 also broadened CI-007's scope in the same commits; the combined PR took `fix:` per the inseparability exception below. A hypothetical standalone CI-007b addition that closes the same incident is still `fix:` because the dominant motivation is incident closure, not new capability. |
| Broaden CI-007 verify from one file to all workflows | `fix(compliance):` | Scope was a bug in the original check |
| Add a new `severity:` tier to the schema | `feat(compliance):` | New capability dimension |
| Invert `override_eligible` on CI-005 from true to false | `feat!(compliance):` | Consumers who overrode can no longer do so |
| Fix a typo in CI-003's `description:` | `docs(compliance):` | Editorial; no detection change |
| Remove CI-099 (obsolete after tool deprecation) | `feat!(compliance):` | Consumers lose the finding stream |
| Add a `notes:` field to CI-001 explaining historical context | `docs(compliance):` | Editorial annotation |
| Add `pattern_absent` semantics to support a new check shape | `feat(compliance):` | New capability for the verify DSL |
| Tighten a regex in CI-007b to reduce false positives | `fix(compliance):` | Detection was imprecise |

## Regression fixtures for critical checks

When you add a new check that is `severity: critical` with
`override_eligible: false`, or promote an existing check into that tier, add a
matching regression fixture under `data/test_fixtures/compliance_auditor/`:

1. Copy `control/` to `defect_<CHECK_ID>/` and introduce exactly one defect that
   the check's `verify` field must catch.
2. Add a structural assertion to `tests/integration/test_auditor_regression.py`.
3. If the check can be evaluated by local file inspection, add a `local_*`
   handler and `LOCAL_CHECKS` entry in `scripts/check-repo-compliance.py`, plus a
   `run_check` line in `scripts/run-auditor-regression.sh`.

This corpus is the first signal when an LLM auditor silently drifts into
interpreting a `verify` field too leniently. A critical check without a fixture
can degrade to a no-op with no alarm. See
`data/test_fixtures/compliance_auditor/README.md` for the contract.

## When a single PR does multiple types

The PR-splitting rule: when a single PR contains changes that map to two different
types, prefer to split.

Exception: split is not required when the changes are operationally inseparable.
PR #116 is the canonical example: closing the XXE escape path required BOTH the
manifest broadening (`fix:`) AND the new check ID (`feat:`). Shipping only one
would leave the same vulnerability exploitable. Splitting would have created two
PRs that each individually weren't ready to merge.

When operational inseparability forces a combined PR, pick the type that matches
the dominant motivation in the PR description's "Why" section. If the dominant
motivation is "close an incident," use `fix:`. If it's "ship a new capability,"
use `feat:`.

Document the choice in the PR description so the next contributor sees the
classification logic, not just the result.

## CHANGELOG conventions

CHANGELOG entries follow the same type derivation. The section headers must match:

- `fix(compliance):` -> `### Fix` section under `[Unreleased]`
- `feat(compliance):` -> `### Feat` section under `[Unreleased]`
- `feat!(compliance):` -> `### Breaking` section under `[Unreleased]`; include a
  `BREAKING CHANGE:` footer in the commit message describing what consumers must do
- `docs(compliance):` -> no CHANGELOG entry required for editorial changes to existing
  manifest entries (typo fixes, rewording, `notes:` additions). When a `docs(compliance):`
  commit adds an entirely new doc that explains manifest policy or design (e.g., a new
  standard like this file, a new ADR), log a CHANGELOG entry under `### Docs` so
  consumers can find the new reference.

When a combined PR (per the inseparability exception above) is classified `fix:`,
the CHANGELOG entry should still describe both halves in the body so consumers
can see the full scope of what changed.

## Decision authority

If a manifest change does not fit any case in the table, the contributor proposes a
type in the PR description with reasoning. Add a new row to the examples table so the
precedent applies to future cases.

## References

- [Conventional Commits 1.0](https://www.conventionalcommits.org/)
- [`.claude/rules/git-workflow.md`](../rules/git-workflow.md): parent rule with the
  full branch-type-to-commit-type mapping for non-manifest changes
- [ADR-006](../../docs/architecture/adr/ADR-006-rules-vs-standards.md): why this is
  a standard (on-demand) and not a rule (session-injected)
- [ADR-008](../../docs/architecture/adr/ADR-008-scanner-allowlist-tiers.md): the
  scanner allowlist redesign that exercises this policy on its first non-trivial case
- PR #116: the triggering case that exposed the classification ambiguity
