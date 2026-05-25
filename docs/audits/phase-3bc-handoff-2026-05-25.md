---
title: "Phase 3B/3C Sweep Handoff"
schema_type: planning
status: published
owner: core-maintainer
component: Strategy
source: "Handoff at end of 2026-05-25 session after Phase 3A (manifest reconciliation) PR #144 merged. Phases 3B/3C deferred to next session per user request."
purpose: "Resume pointer for the next session to execute Phase 3B (36 dependabot.yml deletes) and Phase 3C (9 poetry to pep621 fixes) as two separate PR series."
tags:
  - planning
  - dependencies
  - automation
  - compliance
---

## Resume context

The v43 cutover (Phases 0-2) and the manifest reconciliation (Phase 3A) are **complete and merged**. The remaining work is two fleet-wide sweep PR series:

| Phase | Work | Repo count | Estimated PRs |
|---|---|---|---|
| **3B** | Delete `.github/dependabot.yml` (CI-021 violation: dual PR engines) | 36 | 36 |
| **3C** | Replace `"poetry"` with `"pep621"` in `enabledManagers` (silent zero-PR bug) | 9 | 9 |
| **3D** | Promote CI-058/059/060/PC-016 from `suggested` → `important` in manifest | 1 PR | 1 |

**User decision (end of 2026-05-25 session):** separate PRs per change type. No consolidation of 3B and 3C even when both apply to the same repo. Total: 45 PRs across the fleet.

## Phase 3B: 36 dependabot.yml deletes

### Repos with `.github/dependabot.yml` to delete

Per the 2026-05-24 fleet audit. Confirmed pattern: every Renovate-enabled repo EXCEPT three categories has the duplicate-engine condition.

**Exclusions (do NOT touch):**
- `xero-crypto` (no dependabot.yml on origin/main)
- `template-sample` (no renovate.json, not applicable)
- 6 repos missing renovate.json (CI-020 gap, separate from CI-021): `williaby/{exercise-competition, ledgerbase, zen-mcp-server, pp-security-master, GCS, testing}`
- 2 exempt-from-Renovate repos that keep dependabot.yml intentionally: `williaby/{dart-frog-paludarium, homelab-agent-configs}`

**Refresh the canonical list at session start with:**

```bash
# For each org, list repos with both renovate.json AND dependabot.yml
for org in ByronWilliamsCPA williaby; do
  while read -r repo; do
    has_ren=$(gh api "repos/$org/$repo/contents/renovate.json" 2>/dev/null | jq -r .name 2>/dev/null)
    has_dep=$(gh api "repos/$org/$repo/contents/.github/dependabot.yml" 2>/dev/null | jq -r .name 2>/dev/null)
    if [ "$has_ren" = "renovate.json" ] && [ "$has_dep" = "dependabot.yml" ]; then
      echo "$org/$repo"
    fi
  done < <(gh repo list "$org" --limit 50 --no-archived --json name -q '.[].name')
done
```

### Per-repo PR template

- **Branch:** `chore/remove-dependabot-yml-ci-021`
- **Title:** `chore(deps): remove dependabot.yml superseded by Renovate (CI-021)`
- **Commit message:**
  ```text
  chore(deps): remove dependabot.yml superseded by Renovate (CI-021)

  This repo has both renovate.json AND .github/dependabot.yml, violating
  manifest check CI-021 (dependabot.yml must be absent when renovate.json
  is present). Running both creates duplicate dependency PRs and conflicting
  automerge rules.

  Renovate has been the canonical dependency-update engine across the fleet
  since the 2026-05 standardization. Dependabot Alerts (the security
  feature) remains enabled at the org level and continues to work; only
  the .github/dependabot.yml file (the version-updates config) is removed
  here.

  Reference: docs/audits/dependency-management-improvement-plan-2026-05-24.md
  P0-5 (36 repos identified in the 2026-05-24 fleet audit).
  ```
- **PR body:** brief, references the manifest check and the improvement plan

### Per-repo workflow

```bash
# Per repo:
gh repo clone "$org/$repo" "/tmp/sweep-3b/$repo" 2>/dev/null || (cd "/tmp/sweep-3b/$repo" && git fetch origin main --quiet)
cd "/tmp/sweep-3b/$repo"
git worktree add ".worktrees/remove-dependabot-yml" -b chore/remove-dependabot-yml-ci-021 origin/main 2>&1 || git checkout -b chore/remove-dependabot-yml-ci-021 origin/main
cd ".worktrees/remove-dependabot-yml"
git rm .github/dependabot.yml
SKIP=compose-validation git commit -m "..."
git push -u origin chore/remove-dependabot-yml-ci-021
gh pr create --base main --title "..." --body "..."
```

## Phase 3C: 9 poetry to pep621 fixes

### Repos with `"poetry"` declared on uv-managed projects

**Canonical list** (do NOT add or remove without re-auditing pyproject.toml for `[project]` vs `[tool.poetry]`):

1. `ByronWilliamsCPA/Unify`
2. `ByronWilliamsCPA/audio-processor`
3. `ByronWilliamsCPA/cookiecutter-template-sample`
4. `ByronWilliamsCPA/fragrance-rater`
5. `ByronWilliamsCPA/maester-tests`
6. `ByronWilliamsCPA/python-libs`
7. `ByronWilliamsCPA/rag-processor`
8. `williaby/dna`
9. `williaby/image-preprocessing-detector`

**Per-repo verification before editing:** confirm `pyproject.toml` has `[project]` and that `[tool.poetry]` is either absent or the build-backend is something other than `poetry.core.masonry.api`. If a repo legitimately uses poetry as its build backend, do NOT include it in 3C; it needs a different remediation.

### Per-repo PR template

- **Branch:** `chore/renovate-poetry-to-pep621`
- **Title:** `fix(renovate): use pep621 manager instead of poetry for uv-managed project`
- **Commit message:**
  ```text
  fix(renovate): use pep621 manager instead of poetry for uv-managed project

  This repo's pyproject.toml uses the PEP 621 [project] table (uv-managed),
  but renovate.json declared "poetry" in enabledManagers. The Renovate
  poetry manager looks for [tool.poetry], not [project], so it silently
  produced zero PRs for this repo's Python dependencies despite Renovate
  being enabled.

  Replacing "poetry" with "pep621" restores normal PR generation. The
  pep621 manager correctly reads PEP 621 [project.dependencies].

  Reference: docs/audits/dependency-management-improvement-plan-2026-05-24.md
  P0-4 (9 repos identified in the 2026-05-24 fleet audit). Likely explains
  most of the 47% BLOCKED_BY_CONFIG finding in
  docs/audits/dependabot-renovate-coverage-2026-05-24.md.
  ```

### Per-repo edit

The change is one line per repo: in `renovate.json`, replace `"poetry"` with `"pep621"` inside the `enabledManagers` array. Some repos may have it inside `matchManagers` arrays in packageRules too; those can either be left alone (silently no-op since `pep621` replaces) or also updated for clarity.

## Phase 3D: manifest severity promotions (after 3B + 3C land)

Single PR to `ByronWilliamsCPA/.claude` updating `docs/standards-manifest.yaml`:

| Check ID | Current severity | New severity | Reasoning |
|---|---|---|---|
| CI-058 | suggested | important | After 3B+3C lands, the SBOM workflow caller gap is the only remaining major rollout gap; promote to important once those are filled in a follow-up |
| CI-059 | suggested | important | Lint script needs to be written + deployed first; promote when fleet-wide enforcement reaches 100% |
| CI-060 | suggested | important | After fleet-wide SHA-pin sweep (separate from 3B/3C) |
| PC-016 | suggested | critical | After homelab-infra deploys the pre-commit hook for the global config |

**Important:** CI-058/060/PC-016 promotion is gated on additional follow-up work beyond Phases 3B/3C. Only CI-059 promotion is gated solely on 3B/3C. Phase 3D may end up promoting just CI-059 and deferring the others to later sweep phases.

## Hard rules reminders

- Worktrees inside the project at `.worktrees/<branch-slug>` (never global paths)
- Pre-commit before each commit (`SKIP=compose-validation` if WSL has no docker)
- Signed commits (default; do NOT use `--no-gpg-sign`)
- Never use em-dashes (U+2014) in any commit message, PR body, or doc; comma/semicolon/colon/parens instead
- Conventional Commits: `chore(deps):` for 3B, `fix(renovate):` for 3C
- Per `feedback_github_contents_api.md`: signed commits required; use local clone → commit → push, never the GitHub Contents API

## Quick session-start checklist

1. Read this handoff doc (you are here)
2. Read `docs/audits/dependency-management-improvement-plan-2026-05-24.md` for full context
3. Read `docs/superpowers/plans/immutable-inventing-pinwheel.md` for the v43 cutover plan
4. Re-run the canonical list refresh commands above (the fleet shifts daily)
5. Pick 3B or 3C to start (3B is bigger but simpler)
6. Dispatch parallel subagents (~6 batches) OR run a serial script
7. Track PR URLs as they land; aggregate for the final summary

## Open PRs at session boundary

| Phase | PR | Repo | State |
|---|---|---|---|
| 0 (P0-2) | [#79](https://github.com/ByronWilliamsCPA/cookiecutter-python-template/pull/79) | cookiecutter-python-template | Open (cookiecutter uv→pep621 fix) |
| 0 (P0-3) | [#317](https://github.com/williaby/PromptCraft/pull/317) | williaby/PromptCraft | Open (vulnerabilityAlerts.prPriority fix) |
| 0 (cosmetic) | [#422](https://github.com/ByronWilliamsCPA/homelab-infra/pull/422) | homelab-infra | **MERGED** |
| 2 cutover | [#425](https://github.com/ByronWilliamsCPA/homelab-infra/pull/425) | homelab-infra | **MERGED** |
| 2 symlink | [#431](https://github.com/ByronWilliamsCPA/homelab-infra/pull/431) | homelab-infra | **MERGED** |
| 2 customEnvVariables | [#432](https://github.com/ByronWilliamsCPA/homelab-infra/pull/432) | homelab-infra | **MERGED** (inert but harmless) |
| 2 GPG bind-mount | [#433](https://github.com/ByronWilliamsCPA/homelab-infra/pull/433) | homelab-infra | **MERGED** |
| 3A manifest | [#144](https://github.com/ByronWilliamsCPA/.claude/pull/144) | .claude | **MERGED** |

Phase 0 PRs #79 and #317 remain open. They were superseded by the v43 cutover (v43 auto-migrates the syntax they fix), so they're no longer urgent. Can be closed-without-merge or left open as documentation. User's choice.

## Tracking issues for deferred-from-plan items (still open, not part of Phase 3)

- ByronWilliamsCPA/homelab-infra#418 (S-5: minimumReleaseAge 3d → 14d)
- ByronWilliamsCPA/homelab-infra#419 (Pr-1: lockFileMaintenance automerge true)
- ByronWilliamsCPA/homelab-infra#420 (S-8: Loki alert rule wiring)
- ByronWilliamsCPA/.github#152 (S-6: Trivy → Grype migration)
- ByronWilliamsCPA/.github#153 (S-4: third-party Action SHA pinning sweep)

These are separate workstreams; do NOT bundle them into Phase 3.
