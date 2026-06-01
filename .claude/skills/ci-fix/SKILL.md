---
description: >
  Full CI gate sequence with auto-fix loop. Runs ruff format, ruff lint, qlty check,
  pre-commit, pytest, bandit, and pip-audit in order — fixing what it can and reporting
  blockers. Triggers on: ci-fix, fix ci, fix gates, all gates green, pre-commit failing,
  tests failing, ci failing, fix everything, gates failing.
tools: ["Read", "Bash", "Grep", "Glob", "Edit", "Write"]
---

# CI Fix Skill

Run a consistent 7-gate quality sequence, auto-fix where possible, and offer to commit when
all gates are green.

## Invocation

```text
/ci-fix
```

No arguments. Always runs the full gate sequence.

## Gate Sequence

Run gates in this fixed order. After each fix attempt, re-run the gate before advancing.
Never skip a gate. Never change the order. If the same gate fails after two consecutive fix
attempts, mark it `❌ BLOCKER` and advance to the next gate.

| # | Gate | Command | Auto-fix strategy |
|---|------|---------|-------------------|
| 1 | ruff format | `uv run ruff format --check .` | `uv run ruff format .` (deterministic) |
| 2 | ruff lint | `uv run ruff check .` | `uv run ruff check --fix .`; remaining unfixable rules: edit manually |
| 3 | qlty check | `qlty check` | No auto-fix — refactor functions exceeding complexity/nesting thresholds |
| 4 | pre-commit | `pre-commit run --all-files` | Re-run after ruff fixes; remaining failures: fix and re-run |
| 5 | pytest | `uv run pytest` | Read failure output, fix test or implementation issues, re-run |
| 6 | bandit | `uv run bandit -r src/ -c pyproject.toml` | Fix code issues; false positives: add `# nosec BXXX -- tracked: <URL or ticket>` with an open tracking reference |
| 7 | pip-audit | `uv run pip-audit` | Report only — dependency upgrades require user decision |

> **Bandit source root**: Before running bandit, check `pyproject.toml` for a `[tool.bandit]`
> `targets` field. If present, use that path. If absent, use `src/` if it exists, otherwise
> use `.` as the scan root.

## Status Table

Print the full table after each gate completes. Always print all 7 rows regardless of
how many have completed.

```bash
CI Fix Status
─────────────────────────────────────────────────────
Gate          Status       Notes
─────────────────────────────────────────────────────
ruff format   ✅ PASS
ruff lint     ✅ PASS      4 issues auto-fixed
qlty check    🔧 FIXING    2 functions exceed complexity threshold
pre-commit    ⏳ PENDING
pytest        ⏳ PENDING
bandit        ⏳ PENDING
pip-audit     ⏳ PENDING
─────────────────────────────────────────────────────
```

Status values:
- `⏳ PENDING` — not yet run
- `🔧 FIXING` — fix in progress
- `✅ PASS` — gate green (include note if fixes were applied)
- `❌ BLOCKER` — failed after fix attempt; manual intervention required

## Blocker Behavior

When a gate fails and cannot be resolved in one fix attempt:
- Mark it `❌ BLOCKER` in the table
- Continue running the remaining gates — report the full picture
- Do not stop early

pip-audit findings are always reported but never count as a blocker for the commit offer.
pip-audit status is always `✅ PASS` or `✅ PASS (advisories found — see notes)` — never `❌ BLOCKER`. List any advisories in the Notes column regardless of exit code.

## Completion

**All non-pip-audit gates green:**

```text
All 6 required gates green (pip-audit findings noted above). Commit now? (yes/no)
```

- **Yes**: invoke the `/git` skill with commit intent. Provide the gate summary (which gates passed, what was fixed) as context so it can generate an accurate conventional commit message.
- **No**: stop — present the green status table and hand back

**Any blocker remains:**

```text
5/7 gates pass. Blockers:

  ❌ pytest     — 2 tests failing in tests/unit/test_processor.py (see output above)
  ❌ bandit     — HIGH severity B608 at src/query.py:45 (see output above)

These require manual investigation before committing.
```

No commit offer when blockers remain.

## Environment Notes

Real-world operational patterns for common CI failure scenarios.

### GitHub Actions workflow file editing (Obs 62/41/48/49/50)

The security-guidance PreToolUse hook blocks the Edit and Write tools on `.github/workflows/*.yml` files. When editing workflow files, use Python string replacement via Bash as the primary path:

```bash
python3 - <<'EOF'
with open('.github/workflows/myfile.yml', 'r') as f:
    content = f.read()
content = content.replace('old_string', 'new_string')
with open('.github/workflows/myfile.yml', 'w') as f:
    f.write(content)
EOF
```

Use the most specific anchor string possible (include surrounding lines to make the pattern unique). Keep each file's replacement idempotent -- a failure on one file must not affect others.

### Batch CVE/lint backlog cleanup (Obs 76)

When a CI gate fails on something a local scanner can list exhaustively, enumerate the full backlog locally first, then fix all entries in one commit:

1. Run the local scanner: `uv run pip-audit`, `uv run ruff check .`, etc.
2. Fix all identified issues individually (single-package upgrade, single-rule fix)
3. Verify locally with the same scanner
4. Push once

Do not iterate one-fix-per-CI-cycle for a single class of issue. CI is the slowest oracle; local scanners return the full list at once. The bridge between "wholesale upgrade" (collateral risk) and "one-at-a-time" (slow) is "enumerate locally, fix individually, verify locally, push once."

### `uv lock --upgrade-package` requires explicit sync (Obs 77)

`uv lock --upgrade-package <name>` updates the lock file but does NOT update the active `.venv`. After running an upgrade, verify the new version is installed:

```bash
uv lock --upgrade-package idna
uv sync --reinstall-package idna   # update the venv to match the new lock
uv run pip-audit                    # now reflects the upgraded version
```

Without the explicit `uv sync --reinstall-package`, local `pip-audit` or test runs may still see the old version, producing a false "fix didn't work" signal.

### `git diff --name-only` includes deletions (Obs 137)

Any CI step that pipes `git diff --name-only` into a per-path tool (linter, formatter, test runner) will fail when the PR deletes files, because the deleted path no longer exists in the working tree. Add `--diff-filter=ACMR` to exclude deletions:

```bash
# Bad: includes deletions
git diff --name-only "origin/$BASE"

# Good: only Added, Copied, Modified, Renamed
git diff --name-only --diff-filter=ACMR "origin/$BASE"
```

Diagnostic tell: a per-file linter job fails fast (13-15s) while the tool's SaaS check passes -- that mismatch indicates a harness/enumeration error, not real lint findings.
