---
schema_type: common
title: Org Workflow Pin Tracking Implementation Plan
status: draft
owner: engineering
tags: [compliance, ci_cd, github_actions, security, dependencies, standards]
purpose: Implementation plan for semver tagging on org .github repos, a pin registry in this .claude repo, a daily sync workflow, three new compliance checks (CI-055/056/057), and Renovate consumer PR automation.
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate the full lifecycle of org workflow SHA pins: semver tagging on `.github` repos per merged PR, a registry in this `.claude` repo, a daily sync workflow, three new compliance checks, and Renovate consumer PRs.

**Architecture:** A `release-tag.yml` workflow in each org `.github` repo cuts annotated semver tags on every main-branch push. A daily `sync-org-pins.yml` in this repo reads the latest tag from the GitHub API and opens a PR to update `docs/org-workflow-pins.yaml`. Three new manifest checks (CI-055/056/057) surface stale registry entries and stale consumer pins during `/repo-audit`. Renovate's `followTag` handles per-consumer SHA-update PRs automatically.

**Tech Stack:** GitHub Actions (bash bump logic, gh CLI), Python 3.12 (sync script, unit tests), PyYAML, pytest, CATALOG_REFRESH_PAT (fine-grained PAT, already in repo secrets).

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `docs/org-workflow-pins.yaml` | Create | Registry: `current_tag`, `current_sha`, `last_synced` per source org |
| `docs/standards-manifest.yaml` | Modify (line 1525) | Add CI-055, CI-056, CI-057 checks |
| `scripts/sync_org_pins.py` | Create | Python script called by workflow; reads registry, queries GitHub API, updates if stale |
| `tests/unit/test_sync_org_pins.py` | Create | Unit tests for sync script logic |
| `tests/unit/_load_sync_org_pins.py` | Create | Loader module for sync script (matches repo pattern) |
| `.github/workflows/sync-org-pins.yml` | Create | Daily schedule + workflow_dispatch; calls sync script, opens PR if changed |
| `ByronWilliamsCPA/.github` (cloned) | Create `.github/workflows/release-tag.yml` | Semver bump on every push to main |
| `williaby/.github` (cloned) | Create `.github/workflows/release-tag.yml` | Identical workflow; independent version history |

---

### Task 1: Create the pin registry file

**Files:**
- Create: `docs/org-workflow-pins.yaml`

Initial values use the real `v1.0.0` SHA that both repos share today. The sync workflow will update these once the release workflow cuts `v1.1.0`.

- [ ] **Step 1: Create the registry file**

```yaml
# Canonical SHA pins for org workflow source repos.
# Updated by .github/workflows/sync-org-pins.yml.
# Consumers should pin to current_sha.
# Compliance: CI-055 verifies registry matches latest tag on GitHub;
# CI-056 verifies consumer repos match registry current_sha;
# CI-057 verifies Renovate config targets org workflow sources.

sources:
  ByronWilliamsCPA/.github:
    current_tag: v1.0.0
    current_sha: ea8e19054eac195e6ab7bc93e9c2319632560b77  # pragma: allowlist secret
    last_synced: '2026-05-21'

  williaby/.github:
    current_tag: v1.0.0
    current_sha: ea8e19054eac195e6ab7bc93e9c2319632560b77  # pragma: allowlist secret
    last_synced: '2026-05-21'
```

Write to `docs/org-workflow-pins.yaml`.

- [ ] **Step 2: Validate YAML is well-formed**

```bash
python3 -c "import yaml; yaml.safe_load(open('docs/org-workflow-pins.yaml'))" && echo "OK"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add docs/org-workflow-pins.yaml
git commit -m "feat(pins): add org-workflow-pins registry with initial v1.0.0 values"
```

---

### Task 2: Add CI-055, CI-056, CI-057 to the standards manifest

**Files:**
- Modify: `docs/standards-manifest.yaml` (insert after line 1524, before line 1526)

- [ ] **Step 1: Verify the insertion point**

```bash
sed -n '1522,1528p' docs/standards-manifest.yaml
```

Expected output shows lines ending with `...clean; drift is per-repo, not template-sourced.` at line 1524, a blank line at 1525, then `  - id: FOUND-015` at line 1526. If line numbers differ, find the correct location with:

```bash
grep -n "drift is per-repo" docs/standards-manifest.yaml
grep -n "FOUND-015" docs/standards-manifest.yaml
```

- [ ] **Step 2: Insert three new CI checks after the blank line (line 1525)**

Use Edit to insert after the `...clean; drift is per-repo, not template-sourced.` line. The insert goes in the blank gap between the last CI-053 notes line and the FOUND-015 entry:

```yaml

  - id: CI-055
    domain: ci
    severity: important
    override_eligible: true
    description: >-
      docs/org-workflow-pins.yaml current_sha matches the latest tag SHA
      on GitHub for each source repo. Findings older than 24 hours from
      the tag creation date are reported; within 24 hours the daily sync
      job may simply not have run yet.
    verify: "registry_current: docs/org-workflow-pins.yaml, source=github_tags, max_lag_hours=24"

  - id: CI-056
    domain: ci
    severity: important
    override_eligible: true
    description: >-
      All uses: references to org workflow source repos in
      .github/workflows/*.yml match the current_sha in
      docs/org-workflow-pins.yaml. Fires on any consumer repo where a
      uses: ByronWilliamsCPA/.github/...@<sha> or
      uses: williaby/.github/...@<sha> does not match the registry value.
    verify: "uses_sha_matches_registry: .github/workflows/*.yml, docs/org-workflow-pins.yaml"

  - id: CI-057
    domain: ci
    severity: important
    override_eligible: true
    not_applicable_when: >-
      Repo does not use org reusable workflows (no
      ByronWilliamsCPA/.github or williaby/.github reference in
      .github/workflows/*.yml). Skip silently when not applicable.
    description: >-
      renovate.json contains a packageRules entry targeting org workflow
      source repos with followTag set to the floating major version tag
      (v1). Without this, Renovate either ignores org workflow updates or
      opens PRs on every non-tagged commit.
    verify: "content_present: renovate.json, ByronWilliamsCPA/.github"

```

- [ ] **Step 3: Verify IDs were inserted correctly**

```bash
grep -n "CI-055\|CI-056\|CI-057" docs/standards-manifest.yaml
```

Expected: three hits -- CI-055, CI-056, CI-057.

- [ ] **Step 4: Validate YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('docs/standards-manifest.yaml'))" && echo "OK"
```

Expected: `OK`

- [ ] **Step 5: Run pre-commit on changed files**

```bash
pre-commit run --files docs/standards-manifest.yaml
```

Fix any findings before committing.

- [ ] **Step 6: Commit**

```bash
git add docs/standards-manifest.yaml
git commit -m "feat(manifest): add CI-055 CI-056 CI-057 org workflow pin tracking checks"
```

---

### Task 3: Write tests for sync_org_pins.py (TDD -- write tests first)

**Files:**
- Create: `tests/unit/_load_sync_org_pins.py`
- Create: `tests/unit/test_sync_org_pins.py`

The sync script needs three testable units: parsing the registry YAML, diffing current vs registry state, and producing the updated registry content. Tests use in-memory fixtures; no real GitHub API calls.

- [ ] **Step 1: Create the loader module**

```python
# tests/unit/_load_sync_org_pins.py
"""Loader so test_sync_org_pins can import scripts/sync_org_pins.py."""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "sync_org_pins",
    Path(__file__).parents[2] / "scripts" / "sync_org_pins.py",
)
module = importlib.util.module_from_spec(spec)
sys.modules["sync_org_pins"] = module
spec.loader.exec_module(module)
```

- [ ] **Step 2: Create the test file with failing tests**

```python
# tests/unit/test_sync_org_pins.py
"""Unit tests for scripts/sync_org_pins.py."""
import textwrap
from datetime import date

import pytest
import yaml

import tests.unit._load_sync_org_pins  # noqa: F401
from sync_org_pins import (
    load_registry,
    needs_update,
    build_updated_registry,
)


REGISTRY_YAML = textwrap.dedent("""\
    sources:
      ByronWilliamsCPA/.github:
        current_tag: v1.0.0
        current_sha: ea8e19054eac195e6ab7bc93e9c2319632560b77  # pragma: allowlist secret
        last_synced: '2026-05-21'
      williaby/.github:
        current_tag: v1.0.0
        current_sha: ea8e19054eac195e6ab7bc93e9c2319632560b77  # pragma: allowlist secret
        last_synced: '2026-05-21'
""")


class TestLoadRegistry:
    def test_parses_sources(self, tmp_path):
        reg_file = tmp_path / "org-workflow-pins.yaml"
        reg_file.write_text(REGISTRY_YAML)
        registry = load_registry(reg_file)
        assert "ByronWilliamsCPA/.github" in registry["sources"]
        assert registry["sources"]["ByronWilliamsCPA/.github"]["current_tag"] == "v1.0.0"

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_registry(tmp_path / "nonexistent.yaml")

    def test_raises_on_invalid_yaml(self, tmp_path):
        bad = tmp_path / "org-workflow-pins.yaml"
        bad.write_text("sources: [not: a: mapping]")
        with pytest.raises(yaml.YAMLError):
            load_registry(bad)


class TestNeedsUpdate:
    def test_returns_true_when_sha_differs(self):
        entry = {"current_tag": "v1.0.0", "current_sha": "abc123", "last_synced": "2026-05-21"}
        assert needs_update(entry, tag="v1.1.0", sha="def456") is True

    def test_returns_true_when_tag_only_differs(self):
        entry = {"current_tag": "v1.0.0", "current_sha": "abc123", "last_synced": "2026-05-21"}
        assert needs_update(entry, tag="v1.0.1", sha="abc123") is True

    def test_returns_false_when_both_match(self):
        entry = {"current_tag": "v1.0.0", "current_sha": "abc123", "last_synced": "2026-05-21"}
        assert needs_update(entry, tag="v1.0.0", sha="abc123") is False


class TestBuildUpdatedRegistry:
    def test_updates_tag_sha_and_date(self):
        registry = yaml.safe_load(REGISTRY_YAML)
        today = date(2026, 5, 22)
        updated = build_updated_registry(
            registry,
            repo="ByronWilliamsCPA/.github",
            new_tag="v1.1.0",
            new_sha="deadbeef" * 5,
            sync_date=today,
        )
        src = updated["sources"]["ByronWilliamsCPA/.github"]
        assert src["current_tag"] == "v1.1.0"
        assert src["current_sha"] == "deadbeef" * 5
        assert src["last_synced"] == "2026-05-22"

    def test_does_not_mutate_other_entries(self):
        registry = yaml.safe_load(REGISTRY_YAML)
        today = date(2026, 5, 22)
        updated = build_updated_registry(
            registry,
            repo="ByronWilliamsCPA/.github",
            new_tag="v1.1.0",
            new_sha="deadbeef" * 5,
            sync_date=today,
        )
        # williaby entry must be untouched
        src = updated["sources"]["williaby/.github"]
        assert src["current_tag"] == "v1.0.0"
        assert src["current_sha"] == "ea8e19054eac195e6ab7bc93e9c2319632560b77"  # pragma: allowlist secret
```

- [ ] **Step 3: Run tests, confirm they fail because the module doesn't exist yet**

```bash
PYTHONPATH=. pytest tests/unit/test_sync_org_pins.py -v 2>&1 | head -30
```

Expected: import error or `ModuleNotFoundError: No module named 'sync_org_pins'`

---

### Task 4: Implement sync_org_pins.py

**Files:**
- Create: `scripts/sync_org_pins.py`

- [ ] **Step 1: Write the implementation**

```python
# scripts/sync_org_pins.py
"""
Sync org workflow pin registry against latest GitHub tags.

Called by .github/workflows/sync-org-pins.yml. Reads
docs/org-workflow-pins.yaml, queries the GitHub API for the latest
semver tag on each source repo, and rewrites the file if any entry is
stale. Exits 0 whether or not changes were made; the workflow detects
changes via git diff.

Usage:
    PYTHONPATH=. python3 scripts/sync_org_pins.py [--registry PATH]

Environment:
    GH_TOKEN  GitHub token for API calls (set by workflow).
"""
import argparse
import json
import subprocess
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path

import yaml

_DEFAULT_REGISTRY = Path("docs/org-workflow-pins.yaml")


def load_registry(path: Path) -> dict:
    """Load and parse the pin registry YAML file."""
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open() as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data.get("sources"), dict):
        raise yaml.YAMLError(f"Expected 'sources' mapping in {path}")
    return data


def _latest_tag(repo: str) -> tuple[str, str]:
    """Return (tag_name, commit_sha) for the most recent semver tag.

    Raises RuntimeError when no tags exist or the API call fails.
    """
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/tags", "--jq", ".[0] | {name, sha: .commit.sha}"],
        capture_output=True,
        text=True,
        check=True,
    )
    tag_data = json.loads(result.stdout.strip())
    if not tag_data or tag_data.get("name") is None:
        raise RuntimeError(f"No tags found on {repo}")
    return tag_data["name"], tag_data["sha"]


def needs_update(entry: dict, *, tag: str, sha: str) -> bool:
    """Return True when either tag or sha differs from the registry entry."""
    return entry["current_tag"] != tag or entry["current_sha"] != sha


def build_updated_registry(
    registry: dict,
    *,
    repo: str,
    new_tag: str,
    new_sha: str,
    sync_date: date,
) -> dict:
    """Return a deep-copy of registry with one source entry updated."""
    updated = deepcopy(registry)
    updated["sources"][repo]["current_tag"] = new_tag
    updated["sources"][repo]["current_sha"] = new_sha
    updated["sources"][repo]["last_synced"] = str(sync_date)
    return updated


def _write_registry(path: Path, registry: dict) -> None:
    header = (
        "# Canonical SHA pins for org workflow source repos.\n"
        "# Updated by .github/workflows/sync-org-pins.yml.\n"
        "# Consumers should pin to current_sha.\n"
        "# Compliance: CI-055 verifies registry matches latest tag on GitHub;\n"
        "# CI-056 verifies consumer repos match registry current_sha;\n"
        "# CI-057 verifies Renovate config targets org workflow sources.\n"
        "\n"
    )
    body = yaml.dump(registry, default_flow_style=False, sort_keys=False)
    path.write_text(header + body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=_DEFAULT_REGISTRY)
    args = parser.parse_args(argv)

    registry = load_registry(args.registry)
    today = date.today()
    changed = False

    for repo, entry in registry["sources"].items():
        try:
            tag, sha = _latest_tag(repo)
        except (RuntimeError, subprocess.CalledProcessError) as exc:
            print(f"::warning::Could not fetch tags for {repo}: {exc}", file=sys.stderr)
            continue

        if needs_update(entry, tag=tag, sha=sha):
            print(f"Updating {repo}: {entry['current_tag']} -> {tag}")
            registry = build_updated_registry(
                registry, repo=repo, new_tag=tag, new_sha=sha, sync_date=today
            )
            changed = True
        else:
            print(f"No change for {repo}: already at {tag}")

    if changed:
        _write_registry(args.registry, registry)
        print(f"Registry updated: {args.registry}")
    else:
        print("Registry is current; no changes written.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the unit tests**

```bash
PYTHONPATH=. pytest tests/unit/test_sync_org_pins.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 3: Run linting**

```bash
ruff check scripts/sync_org_pins.py
ruff format --check scripts/sync_org_pins.py
```

Fix any findings before committing.

- [ ] **Step 4: Commit**

```bash
git add scripts/sync_org_pins.py tests/unit/_load_sync_org_pins.py tests/unit/test_sync_org_pins.py
git commit -m "feat(pins): add sync_org_pins.py with unit tests"
```

---

### Task 5: Create the sync workflow

**Files:**
- Create: `.github/workflows/sync-org-pins.yml`

Follows the `catalog-refresh.yml` pattern exactly: branch + bot commit + `gh pr create`, never a direct push to main. Uses `CATALOG_REFRESH_PAT` (same PAT that already has `contents: write` and `pull-requests: write` on this repo).

- [ ] **Step 1: Create the workflow file**

```yaml
# Sync docs/org-workflow-pins.yaml against latest tags on org .github repos.
#
# Triggers:
#   - schedule: daily at 06:00 UTC (up to 24h after a tag is cut)
#   - workflow_dispatch: immediate sync after a manual release
#
# Behaviour: calls scripts/sync_org_pins.py. If the registry changes,
# opens a follow-up PR (never pushes directly to main).
#
# Security note: GH_TOKEN is read-only for the source repos (public).
# The CATALOG_REFRESH_PAT secret is required only for the PR-creation
# step, same as catalog-refresh.yml.

name: Sync Org Workflow Pins

on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch:

permissions: {}

concurrency:
  group: sync-org-pins
  cancel-in-progress: false

jobs:
  sync:
    name: Sync org-workflow-pins.yaml
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: write
      pull-requests: write
    steps:
      - name: Harden the runner
        uses: step-security/harden-runner@9ca718d3bf646d6534007c269a635b3e54cadf99  # v2.19.2
        with:
          egress-policy: audit

      - name: Checkout main
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          ref: main
          token: ${{ secrets.CATALOG_REFRESH_PAT || secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5.6.0
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install pyyaml

      - name: Run sync script
        env:
          GH_TOKEN: ${{ secrets.CATALOG_REFRESH_PAT || secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          PYTHONPATH=. python3 scripts/sync_org_pins.py

      - name: Detect changes
        id: diff
        run: |
          set -euo pipefail
          rc=0
          git diff --quiet -- docs/org-workflow-pins.yaml || rc=$?
          case "$rc" in
            0)
              echo "changed=false" >> "$GITHUB_OUTPUT"
              echo "Registry is current; no PR needed."
              ;;
            1)
              echo "changed=true" >> "$GITHUB_OUTPUT"
              git diff --stat -- docs/org-workflow-pins.yaml
              ;;
            *)
              echo "::error::git diff failed with exit code $rc"
              exit "$rc"
              ;;
          esac

      - name: Verify CATALOG_REFRESH_PAT before push
        if: steps.diff.outputs.changed == 'true'
        env:
          PAT: ${{ secrets.CATALOG_REFRESH_PAT }}
        run: |
          set -euo pipefail
          if [ -z "${PAT:-}" ]; then
            echo "::error::CATALOG_REFRESH_PAT secret is required to open the follow-up PR."
            exit 1
          fi

      - name: Open follow-up PR
        if: steps.diff.outputs.changed == 'true'
        env:
          GH_TOKEN: ${{ secrets.CATALOG_REFRESH_PAT || secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          BRANCH="chore/sync-org-pins-$(date -u +%Y%m%d-%H%M%S)"
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git checkout -b "$BRANCH"
          git add docs/org-workflow-pins.yaml
          git commit -m "chore(pins): sync org workflow pins from latest tags"
          git push -u origin "$BRANCH"
          gh pr create \
            --base main \
            --head "$BRANCH" \
            --title "chore(pins): sync org workflow pins" \
            --body "Auto-generated by .github/workflows/sync-org-pins.yml.

          Updates docs/org-workflow-pins.yaml to reflect the latest semver
          tags on ByronWilliamsCPA/.github and williaby/.github.

          Review the diff before merging. Once merged, CI-055 will clear on
          the next /repo-audit run. Consumer repos will receive Renovate PRs
          automatically after this merges."
```

Get the `actions/setup-python` SHA:

```bash
gh api repos/actions/setup-python/git/refs/tags/v5.6.0 --jq '.object.sha' 2>/dev/null || echo "look up manually"
```

If the above returns a tag object SHA (not a commit SHA), resolve it:

```bash
gh api repos/actions/setup-python/git/tags/<tag-object-sha> --jq '.object.sha'
```

Replace the placeholder `a26af69be951a213d495a4c3e4e4022e16d87065` with the resolved commit SHA and update the comment to match the actual version. The SHA shown above is illustrative; always resolve before writing the file.

- [ ] **Step 2: Run actionlint**

```bash
actionlint .github/workflows/sync-org-pins.yml
```

Fix any findings.

- [ ] **Step 3: Run pre-commit**

```bash
pre-commit run --files .github/workflows/sync-org-pins.yml
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/sync-org-pins.yml
git commit -m "feat(ci): add sync-org-pins.yml daily registry sync workflow"
```

---

### Task 6: Create release-tag.yml in ByronWilliamsCPA/.github

**Files:**
- Clone `ByronWilliamsCPA/.github` into `.worktrees/bwcpa-github-release-tag`
- Create: `.github/workflows/release-tag.yml` in that worktree

- [ ] **Step 1: Clone the repo into a worktree directory**

```bash
mkdir -p .worktrees
git clone git@github.com:ByronWilliamsCPA/.github.git .worktrees/bwcpa-github-release-tag
cd .worktrees/bwcpa-github-release-tag
git checkout -b feat/add-release-tag-workflow
```

- [ ] **Step 2: Find the harden-runner SHA used in this repo**

```bash
grep -r "harden-runner@" .github/workflows/ | head -3
```

Use the SHA found. If none exists, use `9ca718d3bf646d6534007c269a635b3e54cadf99` (v2.19.2, same as ByronWilliamsCPA/.claude).

- [ ] **Step 3: Create .github/workflows/release-tag.yml**

```yaml
# Cut a semver tag on every push to main.
#
# Bump rules (conventional commits):
#   BREAKING CHANGE footer or ! modifier: major bump
#   feat: prefix: minor bump
#   all other types (fix, chore, ci, docs, refactor, perf, test): patch bump
#
# Creates an annotated tag (v1.x.y) and force-moves the floating major
# tag (v1) to HEAD. Both are pushed via GITHUB_TOKEN.
#
# The floating v1 tag is safe because all consumers pin to full 40-char
# SHAs (CI-005 enforcement); v1 is human-readable documentation only.

name: Release Tag

on:
  push:
    branches:
      - main

permissions: {}

jobs:
  tag:
    name: Cut semver release tag
    runs-on: ubuntu-latest
    timeout-minutes: 5
    permissions:
      contents: write
    steps:
      - name: Harden the runner
        uses: step-security/harden-runner@9ca718d3bf646d6534007c269a635b3e54cadf99  # v2.19.2
        with:
          egress-policy: audit

      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0

      - name: Compute next version and tag
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail

          # Fetch all tags so git describe works on a fresh checkout.
          git fetch --tags --quiet

          PREV=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
          MAJOR=$(echo "${PREV#v}" | cut -d. -f1)
          MINOR=$(echo "${PREV#v}" | cut -d. -f2)
          PATCH=$(echo "${PREV#v}" | cut -d. -f3)

          MSG=$(git log -1 --pretty=%B)

          if echo "$MSG" | grep -qE "BREAKING[[:space:]]CHANGE|^[a-z]+(\(.+\))?!:"; then
            MAJOR=$((MAJOR+1)); MINOR=0; PATCH=0
          elif echo "$MSG" | grep -qE "^feat(\(.+\))?:"; then
            MINOR=$((MINOR+1)); PATCH=0
          else
            PATCH=$((PATCH+1))
          fi

          NEW_TAG="v${MAJOR}.${MINOR}.${PATCH}"
          FLOATING="v${MAJOR}"

          echo "Previous tag: $PREV"
          echo "New tag:      $NEW_TAG"
          echo "Floating tag: $FLOATING"

          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          git tag -a "$NEW_TAG" -m "Release $NEW_TAG"
          git tag -f "$FLOATING" -m "Latest $FLOATING release: $NEW_TAG"

          git push origin "$NEW_TAG"
          git push origin "$FLOATING" --force
```

- [ ] **Step 4: Run pre-commit in the worktree**

```bash
cd .worktrees/bwcpa-github-release-tag
pre-commit run --files .github/workflows/release-tag.yml 2>/dev/null || echo "no pre-commit config; validate manually"
```

If pre-commit is not configured in that repo, validate with actionlint from the parent repo:

```bash
actionlint .worktrees/bwcpa-github-release-tag/.github/workflows/release-tag.yml
```

- [ ] **Step 5: Commit and push the branch**

```bash
cd .worktrees/bwcpa-github-release-tag
git add .github/workflows/release-tag.yml
git commit -m "feat(ci): add release-tag workflow for semver tagging on main push"
git push -u origin feat/add-release-tag-workflow
```

- [ ] **Step 6: Open a PR**

```bash
cd .worktrees/bwcpa-github-release-tag
gh pr create \
  --base main \
  --head feat/add-release-tag-workflow \
  --title "feat(ci): add release-tag workflow" \
  --body "Cuts an annotated semver tag on every push to main.

Bump logic follows conventional commits: BREAKING CHANGE or ! = major,
feat = minor, all others = patch. Also force-moves the floating major
tag (v1) to HEAD.

Required by the org workflow pin tracking system (ByronWilliamsCPA/.claude
docs/org-workflow-pins.yaml). Once merged, the daily sync-org-pins.yml
workflow will update the registry to reflect the new tag."
```

Record the PR number for the merge step.

---

### Task 7: Create release-tag.yml in williaby/.github

**Files:**
- Clone `williaby/.github` into `.worktrees/williaby-github-release-tag`
- Create: `.github/workflows/release-tag.yml` (identical to Task 6)

- [ ] **Step 1: Clone and branch**

```bash
git clone git@github.com:williaby/.github.git .worktrees/williaby-github-release-tag
cd .worktrees/williaby-github-release-tag
git checkout -b feat/add-release-tag-workflow
```

- [ ] **Step 2: Copy the workflow file**

```bash
cp .worktrees/bwcpa-github-release-tag/.github/workflows/release-tag.yml \
   .worktrees/williaby-github-release-tag/.github/workflows/release-tag.yml
```

- [ ] **Step 3: Validate**

```bash
actionlint .worktrees/williaby-github-release-tag/.github/workflows/release-tag.yml
```

- [ ] **Step 4: Commit, push, open PR**

```bash
cd .worktrees/williaby-github-release-tag
git add .github/workflows/release-tag.yml
git commit -m "feat(ci): add release-tag workflow for semver tagging on main push"
git push -u origin feat/add-release-tag-workflow
gh pr create \
  --base main \
  --head feat/add-release-tag-workflow \
  --title "feat(ci): add release-tag workflow" \
  --body "Cuts an annotated semver tag on every push to main.

Identical to the workflow added to ByronWilliamsCPA/.github. Both repos
are synchronized and need independent version tags (same codebase, same
cadence). Required by the org workflow pin tracking system."
```

---

### Task 8: Merge the release-tag PRs and verify tagging

**Prerequisites:** Both PRs from Tasks 6 and 7 must be approved and pass CI before this task.

- [ ] **Step 1: Merge the ByronWilliamsCPA/.github PR**

```bash
gh pr merge --repo ByronWilliamsCPA/.github --squash <PR_NUMBER_FROM_TASK_6>
```

- [ ] **Step 2: Confirm the tag was created**

Wait ~60 seconds for the workflow to run, then:

```bash
gh api repos/ByronWilliamsCPA/.github/tags --jq '.[0]'
```

Expected: `{"name": "v1.0.1", "sha": "<new-sha>"}` (patch bump because the commit message starts with `feat(ci):` which triggers a minor bump, so actually expect `v1.1.0`).

Actual bump: `feat(ci):` prefix triggers **minor bump**: `v1.0.0` becomes `v1.1.0`.

Expected: `{"name": "v1.1.0", "sha": "<new-sha>"}`

- [ ] **Step 3: Merge the williaby/.github PR**

```bash
gh pr merge --repo williaby/.github --squash <PR_NUMBER_FROM_TASK_7>
```

- [ ] **Step 4: Confirm williaby tag**

```bash
gh api repos/williaby/.github/tags --jq '.[0]'
```

Expected: `{"name": "v1.1.0", "sha": "<new-sha>"}`

Note both SHAs. They will differ because the repos have separate commit histories.

- [ ] **Step 5: Manually trigger sync-org-pins.yml to populate real values**

```bash
gh workflow run sync-org-pins.yml --repo ByronWilliamsCPA/.claude
```

Monitor the run:

```bash
gh run list --workflow=sync-org-pins.yml --repo ByronWilliamsCPA/.claude --limit 3
```

Wait for the run to complete (typically 2-3 minutes). It will open a PR to update `docs/org-workflow-pins.yaml`.

- [ ] **Step 6: Review and merge the sync PR**

```bash
gh pr list --repo ByronWilliamsCPA/.claude --search "chore/sync-org-pins"
```

Review the diff to confirm it updated both sources to `v1.1.0` with the correct SHAs, then merge.

---

### Task 9: Fleet sweep -- add Renovate packageRules to consumer repos

**Scope:** All repos across `ByronWilliamsCPA` and `williaby` that have a `uses: ByronWilliamsCPA/.github/` or `uses: williaby/.github/` reference in any `.github/workflows/*.yml` file.

- [ ] **Step 1: Find all consumer repos**

```bash
python3 - <<'EOF'
import json, pathlib
catalog = json.loads(pathlib.Path("docs/reference/github-repos.json").read_text())
for repo in catalog["repos"]:
    slug = f"{repo['org']}/{repo['name']}"
    print(slug)
EOF
```

Then for each repo, check if it calls org workflows (or use the catalog's `review.workflows` field if populated).

Faster: use the already-built catalog and check live:

```bash
for repo in $(python3 -c "
import json, pathlib
c = json.loads(pathlib.Path('docs/reference/github-repos.json').read_text())
for r in c['repos']:
    print(f\"{r['org']}/{r['name']}\")
"); do
    COUNT=$(gh api "repos/${repo}/contents/.github/workflows" 2>/dev/null | \
      python3 -c "
import json,sys
files=[f['name'] for f in json.load(sys.stdin) if f['type']=='file']
print('\n'.join(files))" 2>/dev/null | \
      xargs -I{} gh api "repos/${repo}/contents/.github/workflows/{}" --jq '.content' 2>/dev/null | \
      base64 -d 2>/dev/null | grep -c "ByronWilliamsCPA/.github\|williaby/.github" || true)
    if [ "$COUNT" -gt 0 ]; then echo "CONSUMER: $repo"; fi
done
```

Note: this is slow. A faster alternative using the catalog's pre-fetched `review.workflows` field:

```bash
python3 - <<'EOF'
import json, pathlib
catalog = json.loads(pathlib.Path("docs/reference/github-repos.json").read_text())
for repo in catalog["repos"]:
    wf = repo.get("review", {}).get("workflows", [])
    if any("ByronWilliamsCPA/.github" in str(w) or "williaby/.github" in str(w) for w in wf):
        print(f"{repo['org']}/{repo['name']}")
EOF
```

Record the list of consumer repos.

- [ ] **Step 2: For each consumer repo, clone and add the packageRules entry**

For each repo in the consumer list, open a clone in `.worktrees/<repo-slug>/` and run this pattern (illustrated for one repo; repeat for each):

```bash
REPO="ByronWilliamsCPA/some-repo"
SLUG=$(echo "$REPO" | tr '/' '-')
git clone "git@github.com:${REPO}.git" ".worktrees/${SLUG}-renovate"
cd ".worktrees/${SLUG}-renovate"
git checkout -b "chore/add-renovate-org-workflow-rule"
```

Read the existing `renovate.json`:

```bash
cat renovate.json
```

If `packageRules` array already exists, append to it. If it does not exist, add it. The entry to add (must not duplicate if `ByronWilliamsCPA/.github` already appears in `packageRules`):

```json
{
  "matchManagers": ["github-actions"],
  "matchPackagePatterns": ["ByronWilliamsCPA/.github", "williaby/.github"],
  "versioning": "semver",
  "followTag": "v1"
}
```

Commit and open a PR:

```bash
git add renovate.json
git commit -m "chore(deps): add Renovate rule for org workflow SHA pin updates"
git push -u origin chore/add-renovate-org-workflow-rule
gh pr create \
  --base main \
  --head chore/add-renovate-org-workflow-rule \
  --title "chore(deps): add Renovate rule for org workflow SHA pins" \
  --body "Adds a packageRules entry so Renovate tracks the v1 floating tag on
ByronWilliamsCPA/.github and williaby/.github and opens SHA-update PRs when
the org cuts a new release.

CI-057 compliance requirement. See ByronWilliamsCPA/.claude
docs/org-workflow-pins.yaml for the pin registry."
```

Repeat for all consumer repos identified in Step 1.

- [ ] **Step 3: Merge consumer PRs**

After CI passes on each PR, merge them. Renovate will open SHA-update PRs automatically within its next scheduled run (typically within 1 hour of merge).

---

### Task 10: Verify end-to-end

- [ ] **Step 1: Confirm CI-055 clears after sync PR merges**

Run `/repo-audit ByronWilliamsCPA/.claude` (or use the CI agent locally):

```bash
python3 - <<'EOF'
import yaml
registry = yaml.safe_load(open("docs/org-workflow-pins.yaml"))
import subprocess, json
for repo, entry in registry["sources"].items():
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/tags", "--jq", ".[0] | {name, sha: .commit.sha}"],
        capture_output=True, text=True
    )
    live = json.loads(result.stdout.strip())
    match = (entry["current_tag"] == live["name"] and entry["current_sha"] == live["sha"])
    status = "PASS" if match else "FAIL"
    print(f"{status} {repo}: registry={entry['current_tag']} live={live['name']}")
EOF
```

Expected: both repos show `PASS`.

- [ ] **Step 2: Confirm CI-056 state on a consumer repo**

Pick one consumer repo that has been updated with the Renovate rule. Check whether its `uses:` pins match the registry:

```bash
CONSUMER_REPO="ByronWilliamsCPA/some-consumer-repo"
REGISTRY_SHA=$(python3 -c "
import yaml
r = yaml.safe_load(open('docs/org-workflow-pins.yaml'))
print(r['sources']['ByronWilliamsCPA/.github']['current_sha'])
")
gh api "repos/${CONSUMER_REPO}/git/trees/main" --jq '.tree[] | select(.path | startswith(".github/workflows")) | .path' | \
  xargs -I{} sh -c "
    CONTENT=\$(gh api 'repos/${CONSUMER_REPO}/contents/{}' --jq '.content' | base64 -d)
    echo \"\$CONTENT\" | grep -o 'ByronWilliamsCPA/.github[^@]*@[a-f0-9]*' | while read match; do
      PIN=\$(echo \"\$match\" | grep -o '@[a-f0-9]*' | tr -d '@')
      if [ \"\$PIN\" = '${REGISTRY_SHA}' ]; then
        echo \"PASS: \$match\"
      else
        echo \"FAIL: \$match (registry: ${REGISTRY_SHA})\"
      fi
    done
  "
```

After Renovate's PR merges: expected all pins show `PASS`.

- [ ] **Step 3: Run the full test suite**

```bash
PYTHONPATH=. pytest tests/unit/test_sync_org_pins.py tests/integration/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Final commit for this repo (if any files are staged)**

```bash
git status
pre-commit run --all-files
git add -p
git commit -m "chore(pins): post-verification cleanup"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Covered by task |
|-----------------|----------------|
| Semver tagging on `.github` repos | Tasks 6, 7, 8 |
| Pin registry `docs/org-workflow-pins.yaml` | Task 1 |
| Daily sync workflow `sync-org-pins.yml` | Task 5 |
| CI-055 registry freshness check | Task 2 |
| CI-056 consumer pin match check | Task 2 |
| CI-057 Renovate config check | Task 2 |
| Renovate `packageRules` fleet sweep | Task 9 |
| End-to-end verification | Task 10 |

**Potential issues:**

- Task 5 uses `actions/setup-python@<sha>` with a placeholder SHA. Resolve the real SHA before writing the file (Step 1 of Task 5 includes the resolution command).
- Task 9 fleet sweep is the most operationally complex step. Not all consumer repos may have a `renovate.json`; create one if absent following the repo's existing Renovate config pattern (check for `.renovaterc.json` as an alternative filename).
- Task 8 Step 2 notes that `feat(ci):` triggers a minor bump to `v1.1.0`, not a patch bump. Confirm this matches expectations before merging.
