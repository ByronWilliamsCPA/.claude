---
title: "CI Repair Sprint Handoff"
schema_type: planning
status: published
owner: core-maintainer
component: Strategy
source: "Updated 2026-05-26T01:00Z (Wave 1C refresh). Phase 1 complete (PRs #155-#160 merged). Phase 2: 3 of 7 done (PRs #160, #166 merged; PR #165 ready for merge; PR #164 + #170 in flight). Phase 4 reactivated as issue #153 (SHA-pin sweep no longer punted). Trivy → Grype reshaped from defer to parallel-run (PR #169 + issue #152). Resume pointer for the next team."
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

**Phase 2 status: 3 of 7 done, 2 in flight, 2 not started.** Done: PR #160 (python-release), PR #166 (python-sonarcloud), PR #163 (merge_group trigger, bonus). In flight: PR #165 (python-sbom, gate=OK and CLEAN, ready to merge), PR #164 (python-precommit, gate=OK), PR #170 (sonarcloud-patterns-doc update). Not started: python-docs, python-mutation, python-performance-regression. **Phase 3 status: not started.** Per-repo work (SLSA × 7, CodeQL × 7, SonarCloud × 3) waits on Phase 2 to land. **Phase 4 status: REACTIVATED.** Originally punted; tracked at issue #153 and being actively worked in worktree `issue-153-sha-pin-sweep` (baseline CSV produced). **Trivy → Grype: REVISED.** Original Task 2.2 decision was "Option A only (defer migration)." User chose a different design: parallel-run Grype as a non-gating sibling scanner (PR #169 + tracking issue #152). Neither pure Option A nor Option B from the plan; a third path.

Two side merges since Phase 1 closure that aren't in the original plan but landed and are good to know:
- **PR #161** (`16430c9d`): pip-audit `--skip-editable` flag in python-ci for editable-only consumers.
- **PR #162** (`7fdf943a`): renovate matcher correction for `requires-python` suppression.

The full execution plan with phase-by-phase task structure, pattern selection guide, and verification protocols lives at `docs/superpowers/plans/2026-05-25-ci-repair-sprint-completion.md`. Read it before resuming any phase, but treat its task ordering as best-effort: parallel execution has already chosen a different sequence (sonarcloud before sbom; sbom-grype parallel-run instead of deferred).

## What's done

| Workstream | Outcome |
|---|---|
| Renovate v43 cutover (Task #1) | Complete and merged (homelab-infra PRs #422, #425, #431, #432, #433) |
| Close obsolete-after-v43 PRs (Task #4) | Done: cookiecutter-python-template #79 and PromptCraft #317 closed with supersession comments |
| Enable Dependabot Alerts (Task #5) | Done: 23 of 26 disabled repos enabled (3 edge cases skipped: template-sample deleted, dart-frog-paludarium and homelab-agent-configs RENOVATE_IGNORED). 41 of 44 active repos now have alerts. |
| Fleet CI failure inventory | Complete: `/tmp/ci-failure-inventory.tsv` (155 rows, 44 repos surveyed). Top broken workflows: OpenSSF Scorecard (16), Python Compatibility (15), SBOM (11), Security Analysis (10), FIPS Compatibility (10), Semantic Release (8), CI (8), CodeQL (7), SLSA (7). |
| **Phase 1: in-flight PR remediation** | **COMPLETE.** All 6 PRs merged on `BWCPA/.github`. Mid-sprint discovery: the original "proven NOSONAR detect-state pattern" was empirically wrong for one of two SonarCloud failure modes. Three PRs (#157/#158/#159) were re-architected to use the split-install pattern (validated by `BWCPA/.github`:`docs/sonarcloud-nosonar-patterns.md`). |
| **Phase 2.1: python-release.yml** | **COMPLETE.** PR #160 merged 2026-05-25T22:12:32Z (`4fcc7319`). 6 uv-sync/run lines refactored. Spec-compliant; code-quality approved with 3 Minor follow-ups (see "Phase 7 follow-ups" below). |
| **Phase 2.3: python-sonarcloud.yml** | **COMPLETE.** PR #166 merged 2026-05-26T00:50:14Z (`c7d2dce3`). Detect-state pattern applied. Note: this jumped ahead of Phase 2.2 in the parallel execution order. Per-repo SonarCloud variants (python-libs wildcards, cookiecutter Jinja, Unify cache) still pending in Phase 3.3. |
| **Bonus: PR #161** | **COMPLETE.** pip-audit `--skip-editable` flag for editable-only consumers. Merged 2026-05-25 (`16430c9d`). Not in original plan. |
| **Bonus: PR #162** | **COMPLETE.** Renovate matcher correction for `requires-python` suppression. Merged 2026-05-25 (`7fdf943a`). Not in original plan. |
| **Bonus: PR #163** | **COMPLETE.** Adds `merge_group` trigger to workflow-templates for GitHub merge queue. Merged 2026-05-25 (`51a0025a`). Not in original plan. |

## In-flight + recently merged PRs (BWCPA/.github)

### Phase 1 PRs: all merged

The simplified single-install-step pattern with `FROZEN_FLAG` env + `# NOSONAR S8541` (originally adopted after team review of #156) turned out to be **broken for one of two SonarCloud failure modes**. The current canonical pattern is the **split-install detect-state pattern** documented below (and at `BWCPA/.github`:`docs/sonarcloud-nosonar-patterns.md`).

| PR | Workflow | Pattern | State | Action needed |
|---|---|---|---|---|
| [#155](https://github.com/ByronWilliamsCPA/.github/pull/155) | python-scorecard.yml | continue-on-error on Scorecard step + Verify SARIF step | **MERGED 2026-05-25** | none |
| [#156](https://github.com/ByronWilliamsCPA/.github/pull/156) | python-compatibility.yml | split-install pattern (Pattern A + B, dynamic FROZEN_FLAG removed) | **MERGED 2026-05-25T20:59:51Z** | none |
| [#157](https://github.com/ByronWilliamsCPA/.github/pull/157) | python-fips-compatibility.yml | Pattern B (literal `--frozen` + preceding-line NOSONAR(S8541)) | **MERGED 2026-05-25T21:32:05Z** | none |
| [#158](https://github.com/ByronWilliamsCPA/.github/pull/158) | python-security-analysis.yml | Pattern A inline + Pattern B preceding-line, split-install refactor | **MERGED 2026-05-25T21:53Z** | none |
| [#159](https://github.com/ByronWilliamsCPA/.github/pull/159) | python-ci.yml | Pattern A + B throughout, split-install refactor, layout precondition preserved | **MERGED 2026-05-25T21:46:58Z** (8f6d040eba7c7779f320aaca2a8bea83c60a08af) | none |

### Phase 2 PRs: in flight + recently merged

| PR | Workflow / Scope | State | Gate | Action needed |
|---|---|---|---|---|
| [#160](https://github.com/ByronWilliamsCPA/.github/pull/160) | python-release.yml (Phase 2.1) | **MERGED 2026-05-25T22:12:32Z** (`4fcc7319`) | OK | none |
| [#161](https://github.com/ByronWilliamsCPA/.github/pull/161) | python-ci pip-audit `--skip-editable` (bonus) | **MERGED 2026-05-25** (`16430c9d`) | OK | none |
| [#162](https://github.com/ByronWilliamsCPA/.github/pull/162) | renovate matcher fix (bonus) | **MERGED 2026-05-25** (`7fdf943a`) | OK | none |
| [#163](https://github.com/ByronWilliamsCPA/.github/pull/163) | merge_group trigger added to workflow-templates (bonus) | **MERGED 2026-05-25** (`51a0025a`) | OK | none |
| [#164](https://github.com/ByronWilliamsCPA/.github/pull/164) | python-precommit.yml (Phase 2.4) | OPEN | OK, vulns=0 | review + merge (CI status UNKNOWN; verify before merge) |
| [#165](https://github.com/ByronWilliamsCPA/.github/pull/165) | python-sbom.yml (Phase 2.2) | OPEN, MERGEABLE/CLEAN | OK, vulns=0 | **review + merge (ready)** |
| [#166](https://github.com/ByronWilliamsCPA/.github/pull/166) | python-sonarcloud.yml (Phase 2.3) | **MERGED 2026-05-26T00:50:14Z** (`c7d2dce3`) | OK | none |
| [#169](https://github.com/ByronWilliamsCPA/.github/pull/169) | python-sbom Grype parallel-run (Phase 2.8 bonus, tracks issue #152) | OPEN | OK, vulns=0 | review + merge (CI status UNKNOWN; verify before merge) |
| [#170](https://github.com/ByronWilliamsCPA/.github/pull/170) | sonarcloud-nosonar-patterns.md update with Wave 1C finding (Phase 2.9 bonus, doc-only) | OPEN, MERGEABLE/UNSTABLE | n/a (doc) | check what Wave 1C finding is; merge if applicable |

### Other open PRs

| PR | Branch | Notes |
|---|---|---|
| [#148](https://github.com/ByronWilliamsCPA/.github/pull/148) | renovate/github-actions | Preexisting renovate PR (chore deps update). Not part of sprint. Triage separately. |

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
| ~~Done~~ | ~~python-sonarcloud.yml~~ | ~~3 + .github~~ | ✅ **MERGED PR #166** (c7d2dce3, 2026-05-26T00:50Z) | family-office-portal | Detect-state pattern applied. Per-repo SonarCloud variants still pending in Phase 3.3. |
| In flight | python-sbom.yml | 11 | ⏳ **PR #165 ready to merge** (MERGEABLE/CLEAN, gate=OK) | fragrance-rater | Detect-state fix piece. **Trivy → Grype decision REVISED 2026-05-25:** Original "Option A defer" was overridden. User chose parallel-run approach: PR #169 adds Grype as non-gating sibling scanner alongside Trivy (tracked at issue #152). Both PRs ship together. |
| In flight | python-precommit.yml | varies | ⏳ **PR #164 open** (gate=OK; CI UNKNOWN) | any uv repo | Smallest file (101 lines, 6 uv-sync). Verify CI before merge. |
| Then | python-docs.yml | varies | pending | audio-processor | 151 lines, 4 uv-sync. |
| Then | python-mutation.yml | varies | pending | maester-tests | 382 lines, 7 uv-sync/run; 2 lines already use NOSONAR. AUDIT existing placements first; apply patterns only to gaps. Per `[[feedback_mutation_testing_pr_trigger]]`, trigger must remain `workflow_call + schedule + workflow_dispatch` only (CI-053). |
| Then | python-performance-regression.yml | varies | pending | python-libs | **Largest fix:** 642 lines, 19 uv-sync/run. Allocate 60-90 min for refactor alone. Single PR preferred for atomic revert. |
| Doc-only | sonarcloud-nosonar-patterns.md | 0 | ⏳ **PR #170 open** (MERGEABLE/UNSTABLE) | n/a | Adds a "Wave 1C" empirical finding to the canonical NOSONAR placement doc. Read before applying NOSONAR to any of the four remaining workflows above; there may be a new placement caveat. |

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

| Task | Repos affected | Status | Notes |
|---|---|---|---|
| SLSA per-repo fixes | 7 | not started | python-slsa.yml in BWCPA/.github is a copy-paste template, NOT a reusable workflow (GitHub forbids nested reusable workflow calls for the SLSA Generic Generator). Each downstream repo has its OWN .github/workflows/slsa-provenance.yml that needs the detect-state pattern applied per repo. See `feedback_slsa_provenance_pattern` (auto-memory). |
| CodeQL per-repo | 7 | not started | The SARIF upload bug in python-libs is private-repo-specific (likely GHAS Code Scanning configuration). Public repos (e.g., .github) pass CodeQL cleanly. Per-repo investigation needed. |
| SonarCloud per-repo | 3 + variations | not started | python-libs has `sonar.tests=tests/,packages/*/tests/` wildcards; cookiecutter-python-template has Jinja `{{cookiecutter.project_slug}}` placeholder; Unify has stale 2026-05-08 cache miss. (The reusable-workflow piece is done via PR #166; these per-repo variants are independent.) |

## Phase 3 scoping (2026-05-26): bucketed action plan

A read-only Explore subagent investigated all 17 affected repos. Inventory rows reclassified into buckets:

### Bucket D: SLSA rebuild violation (7 repos, high leverage)

All 7 SLSA failures share identical root cause: `uv build` at line 89 of `slsa-provenance.yml` rebuilds artifacts instead of downloading the pre-built distribution from PyPI/GitHub Actions artifact store. Per `[[feedback_slsa_provenance_pattern]]`, the attestation must match what PyPI received, not a fresh local build.

| Repo | Last failure SHA |
|---|---|
| ByronWilliamsCPA/.claude | b905c75838 |
| ByronWilliamsCPA/Unify | 65f254a3db |
| ByronWilliamsCPA/fragrance-rater | 6253bd293 |
| ByronWilliamsCPA/homelab-infra | ca5f136c27 |
| ByronWilliamsCPA/rag-processor | 57ceded204 |
| williaby/dna | dc650269a4 |
| williaby/zen-mcp-server | 7ba0a45c47 |

**Fix recipe:** Replace `uv build` step with a download-artifact action + hash computation step. Same recipe per repo. Estimate 30-60 min per fix; parallelizable 3-way for ~2 hours total wall-clock.

### Bucket E: Per-repo Sonar quirk (1 repo)

| Repo | Issue |
|---|---|
| ByronWilliamsCPA/cookiecutter-python-template | Jinja2 `{{cookiecutter.project_slug}}` placeholder in `sonar-project.properties` (lines 17, 53-56, 73) breaks SonarCloud parsing. Either move under rendered template dir or add `.sonarcloud.yml` override skipping analysis. ~30 min. |

### Bucket G: Investigated (4 repos, much smaller scope than estimated)

Follow-up read-only subagent (2026-05-26) returned definitive root causes for all four. Effort dropped from ~2 hrs to ~20 min total.

**G.1 setup-uv cache without lockfile (3 repos, identical recipe):**

| Repo | Workflow | Failed step | Root cause |
|---|---|---|---|
| williaby/GCS | CodeQL Analysis | Install uv | `astral-sh/setup-uv@v4.2.0` with `enable-cache: true` fails: `No file matched to [**/uv.lock]` |
| williaby/data_ingestor | CodeQL Analysis | Install uv | Same as GCS |
| williaby/testing | CodeQL Analysis | Install uv | Same as GCS |

Fix recipe: either set `enable-cache: false` OR `cache-dependency-glob: ''` on the setup-uv step OR commit a `uv.lock` to the repo. The first two are 1-line changes per repo (~5 min each, ~15 min wall-clock total for all three).

**G.2 setup-python pip cache with UV (1 repo):**

| Repo | Workflow | Failed step | Root cause |
|---|---|---|---|
| ByronWilliamsCPA/Unify | SonarCloud Analysis | Post Set up Python | `setup-python@v5.3.0` with `cache: 'pip'` runs a pip-cache post-step that fails because the repo uses UV (curl-installed) not pip. Pip cache dir is never populated. |

Fix recipe: remove `cache: 'pip'` from setup-python OR switch the install to `astral-sh/setup-uv` action. ~3 min.

### Bucket C: Admin config (1 repo, no code fix)

| Repo | Disposition |
|---|---|
| ByronWilliamsCPA/family-office-portal | SonarCloud project has no Quality Gate set. Filed as ByronWilliamsCPA/family-office-portal#26. Admin/UI task, not code. |

### Bucket F: Inventory false positives (4 repos, no work)

These appeared in `docs/audits/ci-failure-inventory-2026-05-25.tsv` but are NOT Phase 3 work after deeper read:

| Repo | Workflow | Disposition |
|---|---|---|
| ByronWilliamsCPA/python-libs | CodeQL Analysis | Uses org reusable `security-analysis.yml`, not a per-repo CodeQL workflow. Already covered by Phase 1 reusable-workflow fixes (PR #158 merged). Strike from Phase 3 list. |
| williaby/CR-10- | CodeQL Analysis | No CodeQL workflow file exists in the repo. Inventory false positive. Strike. |
| williaby/LifeSphere | CodeQL Analysis | No CodeQL workflow file exists. Inventory false positive. Strike. |
| williaby/ledgerbase | CodeQL Analysis | No recent failures returned by `gh run list`; already passing or intermittent. Strike from Phase 3 list; re-add only if it fails again. |

### Phase 3 effort estimate

| Bucket | Repos | Serial effort | Parallel effort (3-way) |
|---|---|---|---|
| D (SLSA) | 7 | ~5 hrs | ~2 hrs |
| E (Sonar Jinja) | 1 | ~30 min | ~30 min |
| G (1-line cache fixes) | 4 | ~20 min | ~15 min |
| C (admin) | 1 | 0 (issue filed: family-office-portal#26) | 0 |
| F (false positive) | 4 | 0 (struck) | 0 |
| **Total** | 17 | **~6 hrs** | **~2.5 hrs** |

### Dispatch trigger

Phase 3 implementer subagents need ALL Phase 2 PRs (#164, #165, #171, #172, #173, plus the doc PRs #170 #174) on main before dispatch. Until then, per-repo workflows would call stale versions of the reusable workflows and re-discover the patterns already fixed.

## Phase 4: SHA-pin sweep (REACTIVATED)

**Original decision 2026-05-25:** punt to Renovate's next cycle.

**Revised:** in flight. Tracked at issue #153 (improvement plan S-4). Active work in worktree `/home/byron/dev/.github/.worktrees/issue-153-sha-pin-sweep` on branch `claude/issue-153-sha-pin-sweep`. Baseline CSV produced at `docs/audits/2026-05-25-sha-pin-sweep-baseline.csv` (in that worktree). No PR yet; sweep is in baseline-and-plan phase.

When this lands, downstream callers pinning to old SHAs of `BWCPA/.github` reusable workflows will be bumped en bloc rather than incrementally by Renovate. Coordinate with Phase 5 (Phase 3B/3C resume) so the SHA bumps and the pep621/dependabot deletes don't step on each other.

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

- `feedback_subagent_relay_citations` (auto-memory): When relaying user feedback to subagents via SendMessage, include verifiable file:line citations. The python-ci agent correctly refused a pattern change because the relay's load-bearing claim ("line 292 has NOSONAR") was false (NOSONAR actually lives at python-mutation.yml lines 159-169).
- `feedback_sonarcloud_nosonar_placement` (auto-memory): S8541/S8544 honor inline-on-YAML-line NOSONAR for any rule combination, but preceding-line NOSONAR inside `run: |` with dynamic `$FROZEN_FLAG` is NOT honored. Restructure to expose literal `--frozen` or split into single-line `run:` with inline NOSONAR. PRs #157/#158/#159 had ERROR gates because of this; all remediated using the split-install pattern.

## Phase 7 follow-ups (track separately)

Three Minor items surfaced by code-quality review of PR #160. Not blockers; appropriate for the retrospective phase or a separate cleanup PR:

1. **Hash step guard tightening (python-release.yml).** `Generate artifact hashes` (line 334) has no `if:` guard on `steps.detect.outputs.state`, and `Upload distribution artifacts` (line 393, `if: always()`) retains its pre-existing always-run guard. No current runtime bug (detect-state error currently terminates the job), but the pairing would emit confusing `sha256sum: ./*: No such file or directory` errors if detect-state ever adopts `continue-on-error: true` for observability. Add explicit guards: `if: steps.detect.outputs.state == 'uv-locked' || steps.detect.outputs.state == 'uv-no-lock'` to hash; conjunct same to upload's `always()`.

2. **Composite action for detect-state.** The detect-state step is now duplicated nearly verbatim across four merged workflows (python-compatibility.yml, python-fips-compatibility.yml, python-ci.yml, python-release.yml) and will appear in all six remaining Phase 2 targets. A composite action at `.github/actions/detect-uv-state/` with an output named `state` would deduplicate ~20 lines × 10 workflows. Extract once Phase 2 is complete (deferring now would change the convention mid-sprint).

3. **`uv run --frozen` safety comment.** Test job's `uv-no-lock` path should include a one-sentence comment explaining that `uv sync` creates `uv.lock` so subsequent `uv run --frozen` is safe (matches the convention in python-compatibility.yml:316-321). Small documentation gap.

## Audit docs updated/created

- `docs/audits/cve-scan-coverage-2026-05-25.md` (created earlier in session, now has CI Repair Sprint addendum)
- `docs/audits/ci-repair-sprint-handoff-2026-05-25.md` (this document, refreshed 2026-05-26T01:00Z; previous: 22:15Z)
- `docs/superpowers/plans/2026-05-25-ci-repair-sprint-completion.md` (full execution plan with Pattern Selection Guide, Task Template, and per-phase tasks; created this session)

## Quick session-start checklist for the next team

1. Read this handoff doc (you are here).
2. **Re-verify current PR state.** Multiple PRs were in flight at handoff time. Run:
   ```bash
   gh pr list --repo ByronWilliamsCPA/.github --state open --json number,title,mergeable,mergeStateStatus,headRefName --limit 20
   for pr in 164 165 169 170; do
     curl -s "https://sonarcloud.io/api/qualitygates/project_status?projectKey=ByronWilliamsCPA_.github&pullRequest=$pr" | jq -r ".projectStatus.status" | xargs -I {} echo "PR #$pr SonarCloud: {}"
   done
   ```
3. Read `docs/superpowers/plans/2026-05-25-ci-repair-sprint-completion.md`. This is the canonical execution plan. Pay specific attention to the **Pattern Selection Guide** in the Phase 2 header and the **Task Template** (T-Step 1 through T-Step 9). **Note:** the plan's Task 2.2 prescribes "Option A only" for the Trivy → Grype question; that decision was OVERRIDDEN by the user. Parallel-run approach is in flight as PR #169 + issue #152. Use the current handoff doc table (above) as the source of truth for sequencing.
4. Read `BWCPA/.github`:`docs/sonarcloud-nosonar-patterns.md` (merged via PR #157). This is the empirical evidence for why the original "proven" pattern was wrong and which patterns actually work. **Required reading before touching any reusable workflow with NOSONAR.** ALSO: check PR #170 in flight; it adds a "Wave 1C" empirical finding to this doc. If PR #170 has merged by the time you read this, the doc on main is already updated.
5. Read `docs/audits/dependency-management-improvement-plan-2026-05-24.md` for the broader 90-day plan that this sprint serves.
6. Read `docs/audits/phase-3bc-handoff-2026-05-25.md` for the Phase 3B/3C resume context (poetry-to-pep621 + dependabot.yml deletes).
7. **Triage the in-flight PR queue (highest leverage first):**
   - **PR #165 (python-sbom)** is MERGEABLE/CLEAN with gate=OK. Merge as soon as you've reviewed it; this unblocks the 11 repos failing on `SBOM & Security Scan`.
   - **PR #164 (python-precommit)** has gate=OK; CI status was UNKNOWN at handoff time. Verify CI and merge.
   - **PR #169 (Grype parallel-run)** is the sibling Grype add. Review and merge after PR #165 lands (avoid intermediate-state confusion).
   - **PR #170 (sonarcloud-nosonar-patterns.md update)** is doc-only with MERGEABLE/UNSTABLE state. Read what Wave 1C found; if it implies a pattern change for the remaining workflows, fold the change in before continuing Phase 2.
8. **Continue Phase 2** with the three remaining workflows in priority order: python-docs.yml → python-mutation.yml → python-performance-regression.yml. Use PR #160 (`gh pr diff 160 --repo ByronWilliamsCPA/.github`) or the more recent PR #166 as the working exemplar.
9. **Phase 4 (SHA-pin sweep) is REACTIVATED.** Continue work in worktree `/home/byron/dev/.github/.worktrees/issue-153-sha-pin-sweep`. Coordinate with Phase 5 so the SHA bumps and dependabot/pep621 work don't collide.
10. **Phase 3 (per-repo work):** SLSA × 7 repos, CodeQL × 7 repos, SonarCloud × 3 repos. Detailed task structure in the plan. Order by failure count.
11. Resume **Phase 5 (Phase 3B/3C)** per `docs/audits/phase-3bc-handoff-2026-05-25.md`. The python-libs CHANGELOG worktree at `~/dev/python-libs/.worktrees/renovate-pep621-fix/` needs rebase first.
12. **Phase 6:** re-baseline coverage audit and re-compare to Snyk (Task #7) to make the Renovate-vs-Snyk consolidation decision.
13. **Phase 7:** sprint retro + cleanup + repo-compliance sweep. Address the three Phase 7 follow-ups noted below.

### Subagent-driven cadence (recommended)

The 2026-05-25 session used `superpowers:subagent-driven-development`: fresh implementer subagent per workflow fix, followed by spec-compliance reviewer + code-quality reviewer subagents, then merge. The cadence worked well on PR #160 (clean first try; spec reviewer + code reviewer both passed). User retained merge authority on all PRs.

For the next team: same pattern recommended. If you want to parallelize, dispatch implementers sequentially (the skill's Red Flags warn against parallel implementers on the same repo because of branch/index conflicts), but multiple subagents on DIFFERENT phases (e.g., one on Phase 2 workflow fix + one on Phase 3 per-repo SLSA) is safe since they target different repos.

### Outstanding task list snapshot (TodoWrite/TaskList)

| # | Subject | Status |
|---|---|---|
| 9 | Phase 2.2: python-sbom.yml (Option A only) | in_progress (PR #165 ready) |
| 10 | Phase 2.3: python-sonarcloud.yml | completed (PR #166) |
| 11 | Phase 2.4: python-precommit.yml | in_progress (PR #164 open) |
| 12 | Phase 2.5: python-docs.yml | pending |
| 13 | Phase 2.6: python-mutation.yml | pending |
| 14 | Phase 2.7: python-performance-regression.yml | pending |
| 15 | Phase 3.1: SLSA per-repo (7 repos) | pending |
| 16 | Phase 3.2: CodeQL per-repo (7 repos) | pending |
| 17 | Phase 3.3: SonarCloud per-repo (3 repos) | pending |
| 18 | Phase 5: Phase 3B/3C resume | pending |
| 19 | Phase 6: CVE coverage re-baseline | pending |
| 20 | Phase 7: Sprint cleanup + retro | pending |
| 21 | Phase 2.8 bonus: Grype parallel-run (PR #169, issue #152) | in_progress |
| 22 | Phase 2.9 bonus: NOSONAR patterns doc update (PR #170) | in_progress |
| 23 | Phase 4 (REACTIVATED): SHA-pin sweep (issue #153) | in_progress |

## Hard rules reminders

- **NEVER use em-dashes (U+2014)** in any commit message, PR body, code comment, or doc; use comma/semicolon/colon/parens instead. Pre-commit hook PC-011 enforces this; CLAUDE.md elevates to top-level rule.
- **Never `--no-verify` or `--no-gpg-sign`**. Pre-commit and signed commits are mandatory. See `[[project_bypass_flag_guards]]`.
- **Worktrees go inside the project at `.worktrees/<branch-slug>`**, never at `~/.config/` or global paths.
- **Suppression comments need rationale**. NOSONAR is acceptable when the analyzer genuinely cannot resolve dynamic env-var indirection (the S8541 case here). Cite the verifiable precedent (`python-mutation.yml` lines 159-169) in any future revision discussions.
- **CLAUDE.md says "fix the actual issue, not suppress"** for most cases. NOSONAR for S8541 specifically is an explicit exception because the alternative (step-level branching) doesn't actually fix S8541, it just shuffles the finding.
- **When relaying user feedback to subagents**, cite verifiable file:line evidence. Agents that verify and refuse are doing their job; that resistance is a feature.

## Artifacts on disk

- `/tmp/ci-failure-inventory.tsv`: 155 failing-on-main workflow runs across 44 repos (original session). Baseline copy committed at `docs/audits/ci-failure-inventory-2026-05-25.tsv`.
- `/tmp/cve-scan-results.tsv`: the package-manager + renovate + dependabot inventory from earlier in the session.
- **`~/dev/.github/.worktrees/`** active worktrees as of 2026-05-26T01:00Z:
  - `issue-153-sha-pin-sweep` (branch `claude/issue-153-sha-pin-sweep`): Phase 4 SHA-pin sweep in baseline-and-plan phase.
  - `python-precommit-detect-state` (branch `chore/python-precommit-detect-state`): PR #164 source.
  - `python-sbom-detect-state` (branch `chore/python-sbom-detect-state`): PR #165 source.
  - `renovate-pep621-matcher` (branch `claude/renovate-pep621-matcher-147`): unrelated to sprint; preexisting.
  - `sbom-grype-parallel-run-152` (branch `claude/sbom-grype-parallel-run-152`): PR #169 source.
  - `sonarcloud-patterns-doc-update` (branch `chore/sonarcloud-patterns-doc-update`): PR #170 source.
  - The five Phase 1 worktrees and the Phase 2.1 `python-release-detect-state` worktree were cleaned earlier.
- `~/dev/python-libs/.worktrees/renovate-pep621-fix/`: python-libs CHANGELOG fix; will need rebase after Phase 5 picks up (per Phase 3B/3C handoff).
- `~/.claude/skill-observations/log.md`: Observation #88 logged this session: writing-plans skill relied on stale "proven" claims in source handoff without verifying empirical state. Suggests adding a verify-prior-claims line item to the Codebase Discovery checklist. OPEN; review with skill author.
- **Tracking issues** (BWCPA/.github):
  - [#152](https://github.com/ByronWilliamsCPA/.github/issues/152) OPEN: Migrate python-sbom.yml from Trivy to Grype (improvement plan S-6). Parallel-run prep work in PR #169.
  - [#153](https://github.com/ByronWilliamsCPA/.github/issues/153) OPEN: Pin all third-party GitHub Actions to commit SHAs (improvement plan S-4). Sweep in flight in `issue-153-sha-pin-sweep` worktree.
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
