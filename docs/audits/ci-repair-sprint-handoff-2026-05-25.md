---
title: "CI Repair Sprint Handoff"
schema_type: planning
status: published
owner: core-maintainer
component: Strategy
source: "Updated 2026-05-25T22:15Z. Phase 1 (in-flight PR remediation) complete: all 6 reusable-workflow PRs merged (#155-#160). Phase 2.1 (python-release.yml) complete via PR #160. Six Phase 2 reusable workflows + Phase 3 per-repo work remaining. Resume pointer for the next team."
purpose: "Resume context for the CI Repair Sprint: the workstream that emerged after Phase 3C (poetry to pep621) discovered the underlying CI workflows were broken on main across most P0-4 target repos. Includes inventory, in-flight PR queue, established fix pattern, remaining workflow queue, and migration tracking issues."
tags:
  - planning
  - dependencies
  - automation
  - compliance
---

## Resume context

The original Phase 3C plan was to land 9 poetry-to-pep621 PRs across uv-managed repos with broken Renovate configs. Mid-execution, investigation revealed that **the underlying CI workflows on most P0-4 target repos are broken on main**, blocking any PR from getting through their required-check gates. This required a pivot from Path 1 (triage individual PRs) to Path 2 (CI Repair Sprint) per user decision 2026-05-25 18:30 UTC.

The sprint inventory found **155 failing workflow runs across 44 active repos, concentrated in 8 reusable workflow types**. Fixing each reusable workflow once repairs 7-16 repos at a time (high leverage).

**Phase 1 status: COMPLETE.** All six in-flight reusable-workflow PRs (#155, #156, #157, #158, #159, #160) are merged on `BWCPA/.github` main. The detect-state pattern was empirically validated and corrected mid-sprint (see "The corrected NOSONAR detect-state pattern" section below for the canonical template).

**Phase 2 status: 1 of 7 complete.** PR #160 (python-release.yml) merged 2026-05-25T22:12:32Z. Six reusable workflows remain. **Phase 3 status: not started.** Per-repo work (SLSA × 7, CodeQL × 7, SonarCloud × 3) waits on Phase 2 to land.

The full execution plan with phase-by-phase task structure, pattern selection guide, and verification protocols lives at `docs/superpowers/plans/2026-05-25-ci-repair-sprint-completion.md`. Read it before resuming any phase.

## What's done

| Workstream | Outcome |
|---|---|
| Renovate v43 cutover (Task #1) | Complete and merged (homelab-infra PRs #422, #425, #431, #432, #433) |
| Close obsolete-after-v43 PRs (Task #4) | Done: cookiecutter-python-template #79 and PromptCraft #317 closed with supersession comments |
| Enable Dependabot Alerts (Task #5) | Done: 23 of 26 disabled repos enabled (3 edge cases skipped: template-sample deleted, dart-frog-paludarium and homelab-agent-configs RENOVATE_IGNORED). 41 of 44 active repos now have alerts. |
| Fleet CI failure inventory | Complete: `/tmp/ci-failure-inventory.tsv` (155 rows, 44 repos surveyed). Top broken workflows: OpenSSF Scorecard (16), Python Compatibility (15), SBOM (11), Security Analysis (10), FIPS Compatibility (10), Semantic Release (8), CI (8), CodeQL (7), SLSA (7). |
| **Phase 1: in-flight PR remediation** | **COMPLETE.** All 6 PRs merged on `BWCPA/.github`. Mid-sprint discovery: the original "proven NOSONAR detect-state pattern" was empirically wrong for one of two SonarCloud failure modes. Three PRs (#157/#158/#159) were re-architected to use the split-install pattern (validated by `BWCPA/.github`:`docs/sonarcloud-nosonar-patterns.md`). |
| **Phase 2.1: python-release.yml** | **COMPLETE.** PR #160 merged 2026-05-25T22:12:32Z (`4fcc7319`). 6 uv-sync/run lines refactored. Spec-compliant; code-quality approved with 3 Minor follow-ups (see "Phase 7 follow-ups" below). |

## In-flight PRs (BWCPA/.github): all closed

All six Phase 1 PRs are merged. The simplified single-install-step pattern with `FROZEN_FLAG` env + `# NOSONAR S8541` (originally adopted after team review of #156) turned out to be **broken for one of two SonarCloud failure modes**. The current canonical pattern is the **split-install detect-state pattern** documented below (and at `BWCPA/.github`:`docs/sonarcloud-nosonar-patterns.md`).

| PR | Workflow | Pattern | State | Action needed |
|---|---|---|---|---|
| [#155](https://github.com/ByronWilliamsCPA/.github/pull/155) | python-scorecard.yml | continue-on-error on Scorecard step + Verify SARIF step | **MERGED 2026-05-25** | none |
| [#156](https://github.com/ByronWilliamsCPA/.github/pull/156) | python-compatibility.yml | split-install pattern (Pattern A + B, dynamic FROZEN_FLAG removed) | **MERGED 2026-05-25T20:59:51Z** | none |
| [#157](https://github.com/ByronWilliamsCPA/.github/pull/157) | python-fips-compatibility.yml | Pattern B (literal `--frozen` + preceding-line NOSONAR(S8541)) | **MERGED 2026-05-25T21:32:05Z** | none |
| [#158](https://github.com/ByronWilliamsCPA/.github/pull/158) | python-security-analysis.yml | Pattern A inline + Pattern B preceding-line, split-install refactor | **MERGED 2026-05-25T21:53Z** | none |
| [#159](https://github.com/ByronWilliamsCPA/.github/pull/159) | python-ci.yml | Pattern A + B throughout, split-install refactor, layout precondition preserved | **MERGED 2026-05-25T21:46:58Z** (8f6d040eba7c7779f320aaca2a8bea83c60a08af) | none |

### The corrected NOSONAR detect-state pattern (CORRECTION 2026-05-25 post-handoff)

**The original "proven NOSONAR detect-state pattern" below this section was empirically wrong** for one of two SonarCloud failure modes. PRs #157, #158, and #159 all shipped with that pattern and all had SonarCloud quality gate = ERROR (4, 2, and 28 open vulnerabilities respectively) until restructured.

**Canonical reference:** `BWCPA/.github`:`docs/sonarcloud-nosonar-patterns.md` (in PR #157 worktree at session pause). Read this BEFORE applying any new NOSONAR to a reusable workflow.

**Use the Pattern Selection Guide from the completion plan** at `/home/byron/dev/.claude/docs/superpowers/plans/2026-05-25-ci-repair-sprint-completion.md` (Phase 2 header). Summary:

| Shape | Pattern | Suppression |
|---|---|---|
| Single-line `run: uv ...` | **Pattern A** | Inline: `run: uv sync ... $NO_BUILD_FLAG  # NOSONAR(S8541,S8544): <rationale>`. Honors comma-separated rule list. |
| Multi-line `run: \|` with literal `--frozen` (install ran first) | **Pattern B** | Preceding-line `# NOSONAR(S8541): ...` for `--no-build` only. Literal `--frozen` prevents S8544. |
| Multi-line `run: \|` with dynamic `$FROZEN_FLAG` | **ANTI-PATTERN** | NOSONAR not honored. Restructure: split install into two `if:`-guarded steps with literal flags so `$FROZEN_FLAG` env var is never needed. |

**Detect-state step shape unchanged** (still the right shape; pasted below).

### The detect-state step (still correct)

```yaml
# Detect repo state for the uv sync/run commands below. The reusable workflow
# is uv-only by org policy (poetry repos are being converted to uv in separate
# work). Poetry repos fail fast with an actionable error.
- name: Detect repo state
  id: detect
  run: |
    if [ ! -f pyproject.toml ]; then
      echo "state=skip" >> $GITHUB_OUTPUT
      echo "::notice::No pyproject.toml found at repo root; <workflow name> will be skipped."
    elif [ -f poetry.lock ] || grep -qE '^\[tool\.poetry(\.|])' pyproject.toml; then
      echo "state=poetry-not-supported" >> $GITHUB_OUTPUT
      echo "::error::This repo uses Poetry. <workflow file> is uv-only by org policy. Convert to uv before re-enabling."
      exit 1
    elif [ -f uv.lock ]; then
      echo "state=uv-locked" >> $GITHUB_OUTPUT
    else
      echo "state=uv-no-lock" >> $GITHUB_OUTPUT
    fi
  shell: bash
```

### Install step (corrected: split into two `if:`-guarded steps, literal flags)

```yaml
- name: Install dependencies (uv-locked)
  if: steps.detect.outputs.state == 'uv-locked'
  run: uv sync --all-extras --frozen $NO_BUILD_FLAG  # NOSONAR(S8541): --no-build is opt-out via `no-build` input

- name: Install dependencies (uv-no-lock)
  if: steps.detect.outputs.state == 'uv-no-lock'
  run: uv sync --all-extras $NO_BUILD_FLAG  # NOSONAR(S8541,S8544): --no-build via input; no uv.lock by design on this path
```

Downstream `uv run` steps can then use literal `--frozen` because the install step guaranteed `uv.lock` exists. Apply Pattern B (preceding-line `# NOSONAR(S8541)`) for multi-line blocks or Pattern A (inline) for single-line.

### Anti-pattern (the original "proven" template, do NOT use)

```yaml
# DO NOT USE: dynamic FROZEN_FLAG + preceding-line NOSONAR inside run: |
# SonarCloud's githubactions rule set does NOT honor this placement.
- name: <step>
  if: steps.detect.outputs.state == 'uv-locked' || steps.detect.outputs.state == 'uv-no-lock'
  env:
    FROZEN_FLAG: ${{ steps.detect.outputs.state == 'uv-locked' && '--frozen' || '' }}
  run: |
    # NOSONAR(S8541,S8544): <rationale>
    uv run $FROZEN_FLAG $NO_BUILD_FLAG <command>
```

**Why this fails:** SonarCloud pattern-matches against the literal text of `run:` block scalars. When `$FROZEN_FLAG` is dynamic, the scanner cannot follow the env-var indirection and fires both S8541 and S8544. Preceding-line NOSONAR inside `run: |` is ignored by the `githubactions` rule set for dynamic-flag lines (empirically confirmed via PR #157 commit `e797676` failing to clear gate). The fix is structural: expose literal `--frozen` so S8544 cannot fire, then suppress only S8541 (which IS honored in preceding-line position when the underlying line is otherwise clean).

## Remaining reusable-workflow fix queue

Per `/tmp/ci-failure-inventory.tsv`, ranked by leverage (repos affected). All match the detect-state pattern unless flagged.

| Priority | Workflow | Repos affected | Status | Sample downstream | Notes |
|---|---|---|---|---|---|
| ~~Done~~ | ~~python-release.yml~~ | ~~8~~ | ✅ **MERGED PR #160** (4fcc7319, 2026-05-25T22:12Z) | homelab-infra | 6 uv-sync/run lines refactored using split-install pattern. 3 Minor follow-ups in "Phase 7 follow-ups" below. |
| Next | python-sbom.yml | 11 | pending | fragrance-rater | **DECISION 2026-05-25:** Option A only (detect-state fix). Defer Trivy → Grype migration (S-6 improvement) to follow-up issue. Open tracking issue post-merge. |
| Next | python-sonarcloud.yml | 3 directly + .github | pending | family-office-portal | 6 uv-sync lines. Per-repo SonarCloud variants (python-libs wildcards, cookiecutter Jinja, Unify cache) live in Phase 3.3 below. |
| Next | python-precommit.yml | varies | pending | any uv repo | Smallest file (101 lines, 6 uv-sync). Good warm-up if contributors splitting Phase 2. |
| Then | python-docs.yml | varies | pending | audio-processor | 151 lines, 4 uv-sync. |
| Then | python-mutation.yml | varies | pending | maester-tests | 382 lines, 7 uv-sync/run; 2 lines already use NOSONAR. AUDIT existing placements first; apply patterns only to gaps. Per `[[feedback_mutation_testing_pr_trigger]]`, trigger must remain `workflow_call + schedule + workflow_dispatch` only (CI-053). |
| Then | python-performance-regression.yml | varies | pending | python-libs | **Largest fix:** 642 lines, 19 uv-sync/run. Allocate 60-90 min for refactor alone. Single PR preferred for atomic revert. |

**Use the corrected split-install detect-state pattern** documented above in "The corrected NOSONAR detect-state pattern" section. Use PR #160 (`gh pr diff 160 --repo ByronWilliamsCPA/.github`) as the most directly applicable working exemplar; PRs #156 and #159 are also good references.

**Verification protocol per PR:**
1. `actionlint .github/workflows/<file>.yml` (use `-shellcheck=` to silence embedded shellcheck if it complains spuriously per `[[feedback_actionlint_shellcheck_embed]]`)
2. After push: `gh pr checks <PR> --watch`
3. **DO NOT SKIP:** SonarCloud quality-gate verification (gate=OK, vulns=0). actionlint + CI green is NOT sufficient. Public-project API:
   ```bash
   curl -s "https://sonarcloud.io/api/qualitygates/project_status?projectKey=ByronWilliamsCPA_.github&pullRequest=<PR>" | jq '.projectStatus.status'
   curl -s "https://sonarcloud.io/api/issues/search?componentKeys=ByronWilliamsCPA_.github&pullRequest=<PR>&types=VULNERABILITY&ps=20&statuses=OPEN,CONFIRMED" | jq '.total'
   ```
4. After merge: one sample downstream `gh workflow run` to confirm the new reusable workflow runs end-to-end on a caller (one of the "Sample downstream" repos above).

## Per-repo (not reusable-workflow) work

| Task | Repos affected | Notes |
|---|---|---|
| SLSA per-repo fixes (Task #11) | 7 | python-slsa.yml in BWCPA/.github is a copy-paste template, NOT a reusable workflow (GitHub forbids nested reusable workflow calls for the SLSA Generic Generator). Each downstream repo has its OWN .github/workflows/slsa-provenance.yml that needs the detect-state pattern applied per repo. See [feedback_slsa_provenance_pattern.md](../../memory/feedback_slsa_provenance_pattern.md). |
| CodeQL per-repo | 7 | The SARIF upload bug in python-libs is private-repo-specific (likely GHAS Code Scanning configuration). Public repos (e.g., .github) pass CodeQL cleanly. Per-repo investigation needed. |
| SonarCloud per-repo | 3 + variations | python-libs has `sonar.tests=tests/,packages/*/tests/` wildcards; cookiecutter-python-template has Jinja `{{cookiecutter.project_slug}}` placeholder; Unify has stale 2026-05-08 cache miss. |

## Phase 3 blocked tasks (resume after CI Repair Sprint)

| Task | Description | Status |
|---|---|---|
| #2 | Phase 3C: 9 poetry-to-pep621 fixes | BLOCKED. After CI is repaired, the 9 PRs (or fresh ones per `docs/audits/phase-3bc-handoff-2026-05-25.md` template) can land. |
| #6 | Phase 3B: 36 dependabot.yml deletes | BLOCKED. After CI is repaired, the sweep can proceed per `docs/audits/phase-3bc-handoff-2026-05-25.md`. |
| #3 | CI-020 gap repos (6 repos missing renovate.json) | Deferred; separate workstream from Phase 3. |
| #8 | Changelog pre-commit hook | Deferred to post-Phase 3. |
| #10 | Poetry-to-uv migration on 4 williaby repos | Issues filed: williaby/PromptCraft#328, williaby/ledgerbase#147, williaby/data_ingestor#38, williaby/pp-security-master#38. |

## Other open PRs in the queue (pre-session)

These are not part of the CI Repair Sprint but should be resolved during the broader workstream:

| PR | Repo | State | Action |
|---|---|---|---|
| [#190](https://github.com/williaby/image-preprocessing-detector/pull/190) | williaby/image-preprocessing-detector | CLEAN | merge directly |
| [#53](https://github.com/ByronWilliamsCPA/rag-processor/pull/53) | BWCPA/rag-processor | BLOCKED on action_required workflow approval | approve pending workflow runs in Actions tab |
| [#43](https://github.com/ByronWilliamsCPA/python-libs/pull/43) | BWCPA/python-libs | BLOCKED on CodeQL + Sonar (pre-existing on main) | wait for CodeQL + Sonar repairs |
| [#40](https://github.com/ByronWilliamsCPA/audio-processor/pull/40) | BWCPA/audio-processor | BLOCKED on multiple CI failures | retry after CI Repair Sprint |
| [#14](https://github.com/ByronWilliamsCPA/cookiecutter-template-sample/pull/14) | BWCPA/cookiecutter-template-sample | BLOCKED on REUSE + PR Body + Title | per-repo fixes |
| [#30](https://github.com/ByronWilliamsCPA/fragrance-rater/pull/30) | BWCPA/fragrance-rater | BLOCKED on 5 CI failures | retry after CI Repair Sprint |
| [#26](https://github.com/ByronWilliamsCPA/maester-tests/pull/26) | BWCPA/maester-tests | BLOCKED on Core Validation | retry after CI Repair Sprint |
| [#22](https://github.com/williaby/dna/pull/22) | williaby/dna | BLOCKED on 16 CI failures | retry after CI Repair Sprint |

`Unify` has no pep621 fix PR; one will need to be drafted (per Phase 3C handoff template).

## Memory entries created this session

- [feedback_subagent_relay_citations.md](../../memory/feedback_subagent_relay_citations.md): When relaying user feedback to subagents via SendMessage, include verifiable file:line citations. The python-ci agent correctly refused a pattern change because the relay's load-bearing claim ("line 292 has NOSONAR") was false (NOSONAR actually lives at python-mutation.yml lines 159-169).
- [feedback_sonarcloud_nosonar_placement.md](../../memory/feedback_sonarcloud_nosonar_placement.md): S8541/S8544 honor inline-on-YAML-line NOSONAR for any rule combination, but preceding-line NOSONAR inside `run: |` with dynamic `$FROZEN_FLAG` is NOT honored. Restructure to expose literal `--frozen` or split into single-line `run:` with inline NOSONAR. PRs #157/#158/#159 had ERROR gates because of this; all remediated using the split-install pattern.

## Phase 7 follow-ups (track separately)

Three Minor items surfaced by code-quality review of PR #160. Not blockers; appropriate for the retrospective phase or a separate cleanup PR:

1. **Hash step guard tightening (python-release.yml).** `Generate artifact hashes` (line 334) has no `if:` guard on `steps.detect.outputs.state`, and `Upload distribution artifacts` (line 393, `if: always()`) retains its pre-existing always-run guard. No current runtime bug (detect-state error currently terminates the job), but the pairing would emit confusing `sha256sum: ./*: No such file or directory` errors if detect-state ever adopts `continue-on-error: true` for observability. Add explicit guards: `if: steps.detect.outputs.state == 'uv-locked' || steps.detect.outputs.state == 'uv-no-lock'` to hash; conjunct same to upload's `always()`.

2. **Composite action for detect-state.** The detect-state step is now duplicated nearly verbatim across four merged workflows (python-compatibility.yml, python-fips-compatibility.yml, python-ci.yml, python-release.yml) and will appear in all six remaining Phase 2 targets. A composite action at `.github/actions/detect-uv-state/` with an output named `state` would deduplicate ~20 lines × 10 workflows. Extract once Phase 2 is complete (deferring now would change the convention mid-sprint).

3. **`uv run --frozen` safety comment.** Test job's `uv-no-lock` path should include a one-sentence comment explaining that `uv sync` creates `uv.lock` so subsequent `uv run --frozen` is safe (matches the convention in python-compatibility.yml:316-321). Small documentation gap.

## Audit docs updated/created

- `docs/audits/cve-scan-coverage-2026-05-25.md` (created earlier in session, now has CI Repair Sprint addendum)
- `docs/audits/ci-repair-sprint-handoff-2026-05-25.md` (this document, updated 2026-05-25T22:15Z)
- `docs/superpowers/plans/2026-05-25-ci-repair-sprint-completion.md` (full execution plan with Pattern Selection Guide, Task Template, and per-phase tasks; created this session)

## Quick session-start checklist for the next team

1. Read this handoff doc (you are here).
2. Read `docs/superpowers/plans/2026-05-25-ci-repair-sprint-completion.md`. This is the canonical execution plan. Pay specific attention to the **Pattern Selection Guide** in the Phase 2 header and the **Task Template** (T-Step 1 through T-Step 9). The plan supersedes any conflicting guidance in this handoff.
3. Read `BWCPA/.github`:`docs/sonarcloud-nosonar-patterns.md` (merged via PR #157). This is the empirical evidence for why the original "proven" pattern was wrong and which patterns actually work. **Required reading before touching any reusable workflow with NOSONAR.**
4. Read `docs/audits/dependency-management-improvement-plan-2026-05-24.md` for the broader 90-day plan that this sprint serves.
5. Read `docs/audits/phase-3bc-handoff-2026-05-25.md` for the Phase 3B/3C resume context (poetry-to-pep621 + dependabot.yml deletes).
6. **Confirm Phase 1 closure:** all six PRs (#155-#160) on `BWCPA/.github` should show MERGED. If any regressed, treat the regression as Phase 1.X and fix before continuing Phase 2.
7. **Start Phase 2.2: python-sbom.yml.** Use PR #160 as the working exemplar (`gh pr diff 160 --repo ByronWilliamsCPA/.github`). Apply the same split-install detect-state pattern. **Option A only per user decision 2026-05-25:** detect-state fix only; defer Trivy → Grype migration to a separate follow-up issue (open the issue immediately after PR #160's pattern lands here).
8. Continue Phase 2 in priority order from the queue above (python-sonarcloud → python-precommit → python-docs → python-mutation → python-performance-regression).
9. **Phase 4 (SHA-pin sweep) is PUNTED per user decision 2026-05-25.** Renovate handles pin bumps on its next cycle. If a specific Phase 5 PR is blocked on a stale pin, bump that one inline; do not batch-sweep.
10. **Phase 3 (per-repo work):** SLSA × 7 repos, CodeQL × 7 repos, SonarCloud × 3 repos. Detailed task structure in the plan. Order by failure count.
11. Resume **Phase 5 (Phase 3B/3C)** per `docs/audits/phase-3bc-handoff-2026-05-25.md`. The python-libs CHANGELOG worktree at `~/dev/python-libs/.worktrees/renovate-pep621-fix/` needs rebase first.
12. **Phase 6:** re-baseline coverage audit and re-compare to Snyk (Task #7) to make the Renovate-vs-Snyk consolidation decision.
13. **Phase 7:** sprint retro + cleanup + repo-compliance sweep. Address the three Phase 7 follow-ups noted above.

### Subagent-driven cadence (recommended)

This session used `superpowers:subagent-driven-development`: fresh implementer subagent per workflow fix, followed by spec-compliance reviewer + code-quality reviewer subagents, then merge. The cadence worked well on PR #160 (clean first try; spec reviewer + code reviewer both passed). User retained merge authority on all PRs.

For the next team: same pattern recommended. If you want to parallelize, dispatch implementers sequentially (the skill's Red Flags warn against parallel implementers on the same repo because of branch/index conflicts), but multiple subagents on DIFFERENT phases (e.g., one on Phase 2 workflow fix + one on Phase 3 per-repo SLSA) is safe since they target different repos.

## Hard rules reminders

- **NEVER use em-dashes (U+2014)** in any commit message, PR body, code comment, or doc; use comma/semicolon/colon/parens instead. Pre-commit hook PC-011 enforces this; CLAUDE.md elevates to top-level rule.
- **Never `--no-verify` or `--no-gpg-sign`**. Pre-commit and signed commits are mandatory. See `[[project_bypass_flag_guards]]`.
- **Worktrees go inside the project at `.worktrees/<branch-slug>`**, never at `~/.config/` or global paths.
- **Suppression comments need rationale**. NOSONAR is acceptable when the analyzer genuinely cannot resolve dynamic env-var indirection (the S8541 case here). Cite the verifiable precedent (`python-mutation.yml` lines 159-169) in any future revision discussions.
- **CLAUDE.md says "fix the actual issue, not suppress"** for most cases. NOSONAR for S8541 specifically is an explicit exception because the alternative (step-level branching) doesn't actually fix S8541, it just shuffles the finding.
- **When relaying user feedback to subagents**, cite verifiable file:line evidence. Agents that verify and refuse are doing their job; that resistance is a feature.

## Artifacts on disk

- `/tmp/ci-failure-inventory.tsv`: 155 failing-on-main workflow runs across 44 repos (original session). May be stale; baseline copy at `docs/audits/ci-failure-inventory-2026-05-25.tsv` if Phase 0 Step 3 was completed.
- `/tmp/cve-scan-results.tsv`: the package-manager + renovate + dependabot inventory from earlier in the session
- `~/dev/.github/.worktrees/`: all five Phase 1 worktrees PLUS the Phase 2.1 `python-release-detect-state` worktree have been cleaned. Only unrelated `renovate-pep621-matcher` remains.
- `~/dev/python-libs/.worktrees/renovate-pep621-fix/`: python-libs CHANGELOG fix; will need rebase after Phase 5 picks up (per Phase 3B/3C handoff).
- `~/.claude/skill-observations/log.md`: Observation #88 logged this session: writing-plans skill relied on stale "proven" claims in source handoff without verifying empirical state. Suggests adding a verify-prior-claims line item to the Codebase Discovery checklist. OPEN; review with skill author.

## References

- CVE scan coverage audit: `docs/audits/cve-scan-coverage-2026-05-25.md`
- Dependency management improvement plan: `docs/audits/dependency-management-improvement-plan-2026-05-24.md`
- Phase 3B/3C handoff: `docs/audits/phase-3bc-handoff-2026-05-25.md`
- v43 readiness audit: `docs/audits/v43-readiness-2026-05-24.md`
- Renovate architecture reference: `docs/reference/renovate-architecture.md`
- GitHub repo catalog: `docs/reference/github-repos.md` (gitignored)
- Memory: `[[feedback_subagent_relay_citations]]`, `[[feedback_slsa_provenance_pattern]]`, `[[project_bypass_flag_guards]]`, `[[feedback_renovate_uv_manager_trap]]`, `[[project_python_ci_audit_2026_05]]`, `[[feedback_sonarcloud_nosonar_placement]]`
- Completion plan: `docs/superpowers/plans/2026-05-25-ci-repair-sprint-completion.md`
- SonarCloud NOSONAR empirical patterns (canonical): `BWCPA/.github`:`docs/sonarcloud-nosonar-patterns.md` (delivered in PR #157 worktree)
