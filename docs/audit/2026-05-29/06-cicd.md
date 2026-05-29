---
title: "Audit: CI/CD and Tooling"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Audit of GitHub Actions, static-analysis config, and gate coverage."
tags:
  - ci_cd
  - analysis
---

CI hygiene is strong: 22 workflows, all third-party action `uses:` SHA-pinned, no deprecated action APIs (`set-output`, `save-state`, `::set-env`), no node12/16 runtimes, and the three stated pre-commit invariants (PC-YAMLLINT-FILE-REF, PC-MARKDOWNLINT-MD040, PC-HOOK-STAGED-SCOPE) all hold. The two High findings are a matched pair: the repo enables Renovate automerge but has neither the `merge_group` workflow trigger nor the merge-queue ruleset that its own rules require to make automerge safe. Note: actionlint and yamllint were not installed in this environment, so workflow linting relied on grep plus the in-repo `check-github-workflows` jsonschema hook.

## CICD-01 - Required-check workflows do not emit on `merge_group`

- Severity: High
- Effort: S (add a `merge_group` trigger to four workflows; basis: four single-block YAML edits)
- Evidence: `renovate.json:63-66` enables `automerge: true`, `platformAutomerge`, and `prConcurrentLimit: 5`. The four required checks trigger only on `pull_request`/`push`: `ci.yml:68`, `security-analysis.yml:58`, `reuse.yml:30`, `pr-validation.yml:199`. The repo's own `.claude/rules/git-workflow.md` CI-040 states required-check workflows must emit on `merge_group` or a queue stalls until timeout.
- Recommendation: Add `merge_group:` to the `on:` block of all four required-check workflows before enabling the merge queue.

## CICD-02 - No merge-queue rule declared despite automerge config

- Severity: High
- Effort: M (author and apply a ruleset change across the org-ruleset tooling; basis: ruleset edit plus apply-script run and verification)
- Evidence: No `merge_queue` rule exists in any ruleset under `docs/reference/repo-rulesets/` or in `setup_repo_rulesets.py`. The repo's `.claude/rules/git-workflow.md` CI-062 says the main-branch ruleset must declare the queue once automerge plus 5-or-more weekly dependency PRs are in play, a trigger the Renovate config meets.
- Recommendation: Add a `merge_queue` rule (`merge_method: SQUASH`, `max_entries_to_build: 5`, `min_entries_to_merge: 1`, `min_entries_to_merge_wait_minutes: 5`) to the main-branch ruleset. Pairs with CICD-01.

## CICD-03 - `actions/setup-python` steps without dependency caching

- Severity: Low
- Effort: S (add `cache:` keys or rely on adjacent setup-uv cache; basis: three small edits)
- Evidence: `sync-org-pins.yml:49` runs `actions/setup-python` with no `cache:` and no uv step, so it is fully uncached. `pr-validation.yml:63` and `codeql.yml:60` also omit `cache:` but are mitigated by an adjacent cache-enabled `setup-uv`.
- Recommendation: Add `cache: pip` (or a uv cache) to `sync-org-pins.yml:49`; the other two are low priority given the adjacent uv cache.

## CICD-04 - `.mutmut_config` is a cookiecutter stub while mutation CI runs

- Severity: Low
- Effort: S (delete or populate the stub; basis: one file)
- Evidence: `.mutmut_config` is a "NOT CONFIGURED" cookiecutter placeholder, but `mutation-testing.yml:37` actually invokes the org reusable `python-mutation.yml` on a weekly schedule. The stub misleads readers into thinking mutation testing is unconfigured.
- Recommendation: Either remove `.mutmut_config` (the reusable workflow drives the run) or replace the stub with the real configuration so local and CI agree.

## Clean areas

- No deprecated action APIs (`set-output`, `save-state`, `::set-env`); no node12/node16 runtimes; every third-party action `uses:` is SHA-pinned.
- All `setup-uv` steps are cache-enabled; all four required-check contexts map to real job names.
- Pre-commit invariants PC-YAMLLINT-FILE-REF, PC-MARKDOWNLINT-MD040, PC-HOOK-STAGED-SCOPE all satisfied; ruff `target-version=py310` aligns with `requires-python` and the compatibility matrix.
- The only `continue-on-error: true` (`pr-validation.yml:181`) is correctly guarded by a downstream `outcome == 'success'` check, so it is not a swallowed gate.

## Machine-readable findings

```json
[
  {"id": "CICD-01", "title": "Required-check workflows do not emit on merge_group", "domain": "cicd", "severity": "High", "effort": "S", "files": [".github/workflows/ci.yml", ".github/workflows/security-analysis.yml", ".github/workflows/reuse.yml", ".github/workflows/pr-validation.yml", "renovate.json"], "evidence": "renovate.json:63-66 enables automerge; ci.yml:68, security-analysis.yml:58, reuse.yml:30, pr-validation.yml:199 trigger only on pull_request/push; git-workflow.md CI-040 requires merge_group", "recommendation": "Add a merge_group trigger to the on: block of all four required-check workflows before enabling the merge queue.", "cve": ""},
  {"id": "CICD-02", "title": "No merge-queue rule declared despite automerge config", "domain": "cicd", "severity": "High", "effort": "M", "files": ["docs/reference/repo-rulesets/", "scripts/setup_repo_rulesets.py", "renovate.json"], "evidence": "No merge_queue rule in any ruleset or setup_repo_rulesets.py; git-workflow.md CI-062 requires it once automerge is enabled", "recommendation": "Add a merge_queue rule (SQUASH, max_entries_to_build 5, min_entries_to_merge 1, wait 5min) to the main-branch ruleset.", "cve": ""},
  {"id": "CICD-03", "title": "setup-python steps without dependency caching", "domain": "cicd", "severity": "Low", "effort": "S", "files": [".github/workflows/sync-org-pins.yml", ".github/workflows/pr-validation.yml", ".github/workflows/codeql.yml"], "evidence": "sync-org-pins.yml:49 fully uncached; pr-validation.yml:63 and codeql.yml:60 omit cache: but have adjacent cached setup-uv", "recommendation": "Add cache: to sync-org-pins.yml:49; the other two are low priority.", "cve": ""},
  {"id": "CICD-04", "title": ".mutmut_config is a stub while mutation CI runs", "domain": "cicd", "severity": "Low", "effort": "S", "files": [".mutmut_config", ".github/workflows/mutation-testing.yml"], "evidence": ".mutmut_config is a NOT CONFIGURED cookiecutter stub; mutation-testing.yml:37 invokes the reusable python-mutation.yml weekly", "recommendation": "Remove the stub or populate it so local config matches the running CI.", "cve": ""}
]
```
