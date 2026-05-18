---
title: "ADR-008: Two-Tier Scanner Allowlist for CI-007 and CI-007b"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Records the redesign of CI-007/007b scanner detection from inline manifest regex to a tiered external allowlist driven primarily by uses: refs."
tags:
  - adr
  - decisions
  - compliance
  - ci_cd
  - security
  - architecture
---

> **Status**: Proposed
>
> **Decision date**: 2026-05-18
>
> **Deciders**: Byron Williams

## Context

PR #116 (merged 2026-05-17) broadened CI-007 to scan every workflow file and added
CI-007b for command-line exit-code suppression patterns. The post-merge `/pr-review`
analysis surfaced two coverage gaps that the PR did not address, marked as
follow-up:

1. The scanner allowlist (`bandit|safety|osv-scanner|semgrep|trufflehog|gitleaks|pip-audit`)
   omits common cloud-native scanners: `trivy`, `grype`, `checkov`, `kics`, `snyk`,
   `tfsec`. The XXE-escape pattern that motivated PR #116 generalizes to all of
   these tools, but the manifest does not currently catch them.

2. The detection mechanism is regex-only against `run:` block content. This is
   imprecise on two axes:

   - **False positives from incidental text matches**: `run: echo "installing
     trivy now"` would match a substring-based addition for `trivy`. The current
     allowlist is mostly safe because the entries (`bandit`, `pip-audit`,
     `osv-scanner`) rarely appear outside actual invocations. Expanding the list
     to common-word scanners (`safety`, `snyk`) amplifies this risk.
   - **False negatives on tool-flag suppression**: scanners increasingly support
     first-class suppression flags (`trivy ... --exit-code 0`, `checkov
     --soft-fail`, `bandit --exit-zero`, `semgrep --error=0`) that achieve the
     same outcome as `|| true` but in different syntax. CI-007b's regex catches
     the shell-operator form only.

3. The manifest does not distinguish between scanners that block by intent
   (`bandit`, `pip-audit`, `semgrep --error`, `gitleaks`) and scanners that are
   advisory by design (`snyk monitor`, `trivy` without `--exit-code`, `checkov
   --soft-fail`). Adding the advisory tools to a blanket suppression check would
   flag legitimate intentional patterns.

4. Most modern security scans in GitHub Actions run through official actions
   (`aquasecurity/trivy-action`, `anchore/scan-action`, `bridgecrewio/checkov-action`)
   rather than direct shell invocations. Detection via the `uses:` ref is both
   more precise (no false positives from text matches) and more durable (action
   refs don't change syntax across versions). The current manifest does not use
   this signal.

5. The scanner list is duplicated across CI-007's `verify` scope qualifier and
   CI-007b's `verify` forbidden pattern. Additions require editing two regex
   alternations in YAML, which is error-prone and easy to drift.

## Decision

We will separate the scanner allowlist into a dedicated configuration file with
explicit tier classification, and rewrite CI-007 and CI-007b to consume the
allowlist via a defined interface. The audit-mode logic in
`.claude/agents/devops-deployment-agent.md` will dispatch by `uses:` ref first
(precise), falling back to `run:` regex (catch-all) only when the action-based
detection does not match.

The change is recorded as **Proposed** here; **Accepted** transitions to
implementation in a follow-up PR that ships the new config file, the manifest
changes, and the agent doc updates together.

### The allowlist file

Location: `docs/standards/scanner-allowlist.yaml` (adjacent to `standards-manifest.yaml`
for proximity to consumers; not under `.claude/standards/` because it is data, not
agent-loaded prose).

Schema sketch (final shape to be locked during implementation):

```yaml
schema_version: 1
scanners:
  - id: bandit
    tier: must_block          # tier 1: deterministic, exit-code-driven
    detect:
      uses:                   # GitHub Action refs that invoke this scanner
        - PyCQA/bandit-action
      run_pattern: '\bbandit\b'  # PCRE; used by run: fallback
    suppression_flags:        # tool-flag forms that defeat the check
      - '--exit-zero'
      - '--exit-code\s*[02-9]\d*'

  - id: snyk
    tier: advisory_by_intent  # tier 2: subcommand- or flag-dependent
    detect:
      uses:
        - snyk/actions/python
      run_pattern: '\bsnyk\s+test\b'  # only `snyk test`; `snyk monitor` excluded by design
    suppression_flags: []
    notes: >
      `snyk monitor` always returns 0 by design (reporting-only). Only `snyk test`
      is subject to CI-007b.

  - id: trivy
    tier: must_block
    detect:
      uses:
        - aquasecurity/trivy-action
      run_pattern: '\btrivy\b'
    suppression_flags:
      - '--exit-code\s*0'
      - '--severity\s+UNKNOWN'  # equivalent: only "unknown" severity reported
```

Tier semantics:

- **`must_block`**: scanner is gate-quality. Any suppression (via shell `||` or
  via tool flag) is a CI-007b violation. CI-007 also applies if such a job
  carries `continue-on-error: true`.

- **`advisory_by_intent`**: scanner is reporting-only by design for the listed
  invocation pattern. CI-007b does NOT apply. CI-007 still applies if the
  enclosing job carries `continue-on-error: true` and is name-matched.

### CI-007 and CI-007b after the redesign

CI-007's `verify` references the allowlist by tier:

```yaml
verify: |
  content_absent: continue-on-error: true within jobs matching scanner-allowlist tier:must_block.
  Scope source: docs/standards/scanner-allowlist.yaml (tier=must_block entries).
  Also flag continue-on-error: true on per-step entries whose uses: or run: invokes
  any must_block scanner per the allowlist's detect block.
```

CI-007b's `verify` references the allowlist's `run_pattern` union plus the
`suppression_flags` union, both restricted to tier `must_block`:

```yaml
verify: |
  pattern_absent: .github/workflows/*.yml
  For each scanner in docs/standards/scanner-allowlist.yaml where tier == must_block:
    1. Match invocation: <run_pattern>
    2. Forbidden suffix patterns:
       - shell suppressors:  \|\|\s*(echo|true|:|exit\s+0)
       - tool-flag suppressors: <suppression_flags union>
  Evaluate with `rg` (ripgrep) or `grep -P` (PCRE).
```

### The agent's audit logic

`.claude/agents/devops-deployment-agent.md` Audit Workflow gains a `scanner_allowlist`
handler:

1. Read `docs/standards/scanner-allowlist.yaml`. Collect tier-must_block scanners.
2. For each workflow file in `.github/workflows/*.yml`:
   a. Walk `jobs.*.steps[*]` (YAML, not regex). For each step:
      - If `uses:` matches any allowlist `detect.uses` ref, mark the step as a
        scanner invocation (precise path).
      - If `run:` matches any allowlist `detect.run_pattern`, mark the step as a
        scanner invocation (fallback path; flag a lower-confidence finding).
   b. For each marked step:
      - CI-007 check: scan the enclosing job and the step itself for
        `continue-on-error: true`. Allow only on non-scanner steps inside a job
        that has at least one marked step.
      - CI-007b check: scan the `run:` body for any `suppression_flags` regex or
        the universal shell-suppression regex.
3. Emit findings with `<file>:<line>` precision and tier annotation.

The `uses:`-first dispatch closes the false-positive risk from incidental text
matches: an `echo "installing trivy"` line is in `run:` content but does not
match any allowlist `uses:` ref AND is excluded from `run_pattern` matching when
the pattern is anchored on `\b<tool>\b\s+(<subcommand>|-)` rather than just
`\b<tool>\b`. The detect block lets per-scanner configuration encode this.

## Alternatives Considered

**Option A: Expand the inline regex alternation in CI-007 and CI-007b only.**
The cheapest possible change. Adds entries directly to the YAML strings. Pros:
one PR, no new files. Cons: doesn't address the tool-flag suppression gap;
multiplies false-positive risk because `safety`, `snyk`, and `trivy` appear in
non-tool contexts more often than `bandit` does; the same regex is now
duplicated in CI-007 and CI-007b with no enforcement that they stay in sync.
Rejected because it fixes the smallest dimension (coverage breadth) while
amplifying the other two (precision, drift).

**Option B: `uses:`-only detection, no `run:` fallback.** Tighter still. Pros:
near-zero false positives (an action ref unambiguously identifies the tool).
Cons: misses ad-hoc shell invocations entirely. Repos that install scanners
via `pip install bandit && bandit -r src/` would not be checked. Rejected
because PR #116's incident (pp-security-master) used shell invocation, not an
action.

**Option C: Per-scanner check IDs (CI-007c-trivy, CI-007d-checkov, etc.).**
Each scanner gets its own check entry. Pros: maximum precision per-scanner;
straightforward to reason about. Cons: ID explosion (10+ new IDs for the
common scanner set); each new scanner addition requires a new manifest entry
and CHANGELOG note; consumers see one logical rule fragmented across many IDs.
Rejected as not scalable to the security tooling landscape.

**Option D: Move detection logic entirely into a Python script
(`scripts/check-repo-compliance.py` already exists for CI-020/021 and BP-4/5).**
Pros: the verify field becomes a thin reference to the script; arbitrary logic
is possible. Cons: pulls the manifest-LLM-interpreter contract into Python
land for one check pair, breaking the consistency of how `repo-compliance`
agents read the manifest; harder for non-coding contributors to add scanners.
**Rejected for now (deferred for re-evaluation):** if the YAML allowlist's
expressivity proves insufficient (e.g., conditional dispatch based on
workflow-level inputs the agent cannot statically resolve), this option
re-opens.

## Consequences

### Positive

- The scanner allowlist becomes a single source of truth, edited in one file
  instead of two regex alternations.
- New scanners are added by appending to a YAML list with a clear schema, not
  by editing alternation strings. Lower error rate; reviewable as a discrete
  data change.
- Tier classification captures the deterministic-vs-advisory distinction
  explicitly, preventing the noise that pure regex expansion would create on
  intentional advisory invocations (`snyk monitor`, `trivy` without
  `--exit-code`).
- `uses:`-first detection dramatically reduces false positives from incidental
  text matches in `run:` content.
- Tool-flag suppression detection (`--exit-zero`, `--exit-code 0`,
  `--soft-fail`) becomes expressible per-scanner.
- The pattern generalizes: if future checks need similar lookup-table
  semantics (e.g., a CI-014 "approved license list" or BP-006 "approved
  base image registry"), the same external-config pattern applies.

### Negative

- Adds a new file to maintain. Drift between `scanner-allowlist.yaml` and
  real-world scanner releases is the new failure mode. Mitigation: an
  optional `/loop` recipe that checks the allowlist against current scanner
  release notes quarterly (deferred to its own follow-up).
- The agent's audit logic grows more complex: it must parse the allowlist
  YAML, then walk workflow YAML structurally (not just regex). Implementation
  cost is roughly one new section of audit-workflow logic.
- The verify field of CI-007 and CI-007b now references a non-manifest file.
  Any agent that consumes the manifest must read both. This is consistent
  with other multi-file verify references (e.g., the Codecov filename
  resolution in CI-009/010/011) but expands the surface.

### Neutral

- The implementation PR will be classified `feat(compliance):` per the
  policy in `.claude/standards/manifest-changes.md`: it expands enforcement
  to a new dimension (tier-aware scanner detection) rather than fixing a
  bug in existing detection. The CHANGELOG entry will appear under `### Feat`.
- The current scanner allowlist (`bandit`, `safety`, `osv-scanner`, `semgrep`,
  `trufflehog`, `gitleaks`, `pip-audit`) is preserved in the new file with
  appropriate tier classification. No existing check loses coverage.

## Implementation plan

The implementation lands in a separate `feat(compliance):` PR with these
steps. Each step gets its own commit for traceability:

1. Create `docs/standards/scanner-allowlist.yaml` with the existing seven
   scanners pre-populated at tier `must_block` plus the six expansion
   scanners (`trivy`, `grype`, `checkov`, `kics`, `snyk`, `tfsec`) classified
   per real-world usage.

2. Update `docs/standards-manifest.yaml` CI-007 and CI-007b `verify` fields
   to reference the allowlist instead of inlining the regex.

3. Update `.claude/agents/devops-deployment-agent.md` Audit Workflow with
   the `scanner_allowlist` handler (`uses:`-first, `run:` fallback, tier-aware).

4. Update the same file's Remediation Workflow to reference the new dispatch
   path.

5. Add a section to `docs/known-vulnerabilities.md` (or a new section in the
   manifest's `notes:` field) explaining the tier rationale for any
   tier=`advisory_by_intent` entries, so future reviewers don't try to "fix"
   them.

6. CHANGELOG entry under `### Feat`.

The implementation PR is gated on this ADR transitioning to **Accepted** via
review.

## Security Considerations

- The scanner allowlist file becomes a high-value config: an attacker who can
  modify it can demote a `must_block` scanner to `advisory_by_intent`,
  silently disabling the suppression check for that scanner. Mitigation: the
  file is covered by the same signed-commit and branch-protection rules as the
  rest of `docs/standards/`. Per ADR-006's security considerations, standards
  files that affect detection behavior are high-value targets and must be
  covered by signed-commit enforcement.
- The tier classification is auditable: every tier=`advisory_by_intent` entry
  must carry a `notes:` field explaining why blocking semantics do not apply.
  A reviewer can challenge the demotion without needing additional context.
- The implementation must not silently fall back to an empty allowlist if the
  file is missing or malformed. Failure to read the allowlist should emit a
  FINDING (audit mode) or abort (remediation mode), not a vacuous PASS.

## References

- PR #116 ([merged 2026-05-17](https://github.com/ByronWilliamsCPA/.claude/pull/116)):
  the change that exposed the coverage and precision gaps closed here.
- `docs/standards-manifest.yaml` checks CI-007 and CI-007b: the consumers
  this ADR modifies.
- `.claude/agents/devops-deployment-agent.md` Audit and Remediation
  Workflows: the agent logic this ADR rewrites.
- `.claude/standards/manifest-changes.md`: the policy that classifies this
  ADR's implementation PR as `feat(compliance):`.
- [ADR-006](ADR-006-rules-vs-standards.md): why the allowlist file is data
  (`docs/standards/`) rather than agent-loaded prose (`.claude/standards/`).
- [Conventional Commits 1.0](https://www.conventionalcommits.org/)
