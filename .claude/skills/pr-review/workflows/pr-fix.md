# PR Fix Workflow

Fixes identified review findings on the PR branch in an isolated worktree.
Called from `pr-review.md` Step 10 after the user chooses to fix issues.

## Input

Expects these values from the calling workflow:

- `OWNER`, `REPO`, `PR_NUMBER` — from the review
- `HEAD_BRANCH` — the PR's head branch (branch to check out)
- `FINDINGS` — deduplicated, scored findings list from the review (in context)

---

## Step F1 — Announce and categorize

Announce: "Starting PR fix workflow for {OWNER}/{REPO}#{PR_NUMBER}."

### SonarQube findings — always fix, no prompt

SonarQube findings are deterministic with prescribed remediation. Add all
`SONAR_FINDINGS` from the review workflow directly to the top of the fix
queue. Do not ask the user whether to include them.

### Agent findings — scope prompt

Split agent findings into tiers:

| Tier | Includes | Default |
| --- | --- | --- |
| **Tier A** | Critical + Important | Always fix |
| **Tier B** | Suggested | Ask |
| **Tier C** | Informational | Never auto-fix |

Present the scope prompt:

```text
Ready to fix review findings on branch {HEAD_BRANCH}.

Automatic ({N_sonar} SonarQube findings — always included)

Agent finding scope:
1. Critical + Important only  ({N_A} agent findings — recommended)
2. Critical + Important + Suggested  ({N_A + N_B} agent findings)

Which scope?
```

Record the choice as `FIX_SCOPE`. Build `FIX_LIST` in this order:

1. All SonarQube findings (by file, line order)
2. Critical agent findings
3. Important agent findings
4. Suggested agent findings (only if scope 2)

---

## Step F2 — Set up worktree

Create an isolated worktree on the PR branch. The worktree directory is
always project-local per CLAUDE.md.

```bash
# Fetch the latest state of the PR branch
git fetch origin {HEAD_BRANCH}

# Create the worktree at the project-local path
git worktree add .worktrees/fix-pr{PR_NUMBER} {HEAD_BRANCH}
```

Record `WORKTREE_PATH=.worktrees/fix-pr{PR_NUMBER}`.

All subsequent file edits happen inside `WORKTREE_PATH`. Never touch the
main working tree.

**Error handling:**

- If `.worktrees/fix-pr{PR_NUMBER}` already exists: remove it first with
  `git worktree remove --force .worktrees/fix-pr{PR_NUMBER}` and re-create.
- If the branch is not found locally: ensure `git fetch origin` ran first.

---

## Step F3 — Execute fixes

Work through `FIX_LIST` in order. For each finding:

1. Announce: "Fixing [{tier}] `{file}:{line}` — {description}"
2. Read the file in the worktree before editing.
3. Apply the fix using the Edit tool (path: `{WORKTREE_PATH}/{file}`).
4. Do not fix anything outside the stated finding. Do not refactor
   surrounding code. Do not add comments beyond what the fix requires.

### Fix guidelines by finding type

**Shell script bugs** (CLAUDE_TOOL_INPUT, stdin patterns, unquoted variables,
missing `set -e`, unsafe echo, bare python calls, etc.)

- Read the surrounding 20 lines for context before editing.
- Match the stdin-reading pattern used by existing scripts in `scripts/`:
  `CONTEXT=$(cat); FIELD=$(jq -r '.field // empty' <<< "$CONTEXT")`.
- Bare `python` or `python3` calls in projects that use `uv` → `uv run python`.
  Check for a `pyproject.toml` or `uv.lock` before applying this fix.
- Do not rewrite the whole script — fix the specific line(s) identified.

**Documentation accuracy** (wrong counts, undocumented hook types, wrong
paths, unsourced claims)

- Fix only the specific claim or field identified.
- For ADR amendments: append an `## Amendment` section at the end of the ADR
  rather than editing the original context section. ADRs are append-only.
- For frontmatter field fixes (`status: draft` → `status: published`): edit
  the frontmatter block only.

**Em-dashes** (if present in FIX_LIST)

- Replace each `—` with the contextually appropriate alternative:
  - Parenthetical aside: comma or parentheses
  - Clause separator: semicolon or period
  - Colon-like introduction: colon
- Process em-dashes file by file, not with a global search-replace that
  might produce incorrect substitutions.

**SonarQube shell findings** (missing `default *` case, missing `return`,
nested if merge)

- Apply the minimal fix: add the `*) ;;` case, add `return`, or flatten the
  nested `if`. Do not restructure control flow beyond what is required.

**Configuration fixes** (`permissions.ask` count, hook type documentation,
hard-coded absolute paths)

- Edit only the specific field or line identified.
- Hard-coded absolute paths (e.g., `/home/username/...`) in shared JSON
  settings → use `~` or `$HOME` portable equivalents. Check that the tool
  consuming the value supports `~` expansion before applying this fix.

**Pre-commit config issues** (missing `types:` filter, wrong `stages:`,
conflicting hook settings)

- Add missing `types: [python]` (or other language filter) to hooks that are
  language-specific but lack a filter.
- Add missing `stages:` entries when the config uses stages elsewhere and
  the hook's absence from a stage is clearly an oversight.
- Do not reorganize the hook order or add new hooks — fix only the specific
  field identified.

**Python code antipatterns** (Agent B simple, unambiguous findings)

- `x == None` / `x != None` → `x is None` / `x is not None`.
- Comparison of incompatible types when the fix is obvious from the
  surrounding code (e.g., `if count == "0"` → `if count == 0`).
- Only fix patterns where the correct code is unambiguous from context.
  Do not attempt fixes that require understanding business logic.

**Docstring and comment accuracy** (Agent E mechanical findings)

- Update a parameter name in a docstring when the function signature changed
  and the old name is clearly wrong.
- Remove documented parameters that no longer exist in the function signature.
- Fix a stated return type that demonstrably does not match the actual return.
- Do NOT add entirely new docstrings to functions — that is new content
  requiring judgment. Mark those as "requires manual fix" and skip.

**Bare exception handling** (Agent F mechanical findings only)

- `except:` (bare) → `except Exception` — always wrong, always fix.
- `except Exception: pass` — add a minimal `logger.exception(...)` call
  before the pass if a logger is already imported in the file. If no logger
  exists, mark as "requires manual fix" and skip rather than introducing a
  new dependency.
- Do not change the broader error-handling strategy. Deciding whether to
  retry, re-raise, or suppress is a design decision — skip those findings.

### Findings that always require manual fix

Mark the following finding types as "requires manual fix", skip them, and
include them in the completion summary for the user to address:

| Finding type | Reason |
| --- | --- |
| Test coverage gaps (Agent G) | Writing new tests requires understanding intent |
| Type design issues (Agent H) | Architectural judgment, not mechanical edits |
| Complex logic bugs (Agent B) | Algorithm or business logic errors need human review |
| Security vulnerabilities (Agent B) | Security fixes must not be auto-patched |
| Silent failures needing new error infrastructure (Agent F) | Error strategy is a design decision |
| Prior PR comment findings (Agent D) | Often unresolved design debates |
| PlantUML diagram accuracy | Requires cross-referencing multiple settings files and SVG regeneration |

---

## Step F4 — Run pre-commit

After all fixes are applied, run pre-commit from inside the worktree:

```bash
cd {WORKTREE_PATH} && pre-commit run --all-files 2>&1
```

If pre-commit fails:

- Read the failure output.
- Fix only the issues pre-commit identifies — do not expand scope.
- Re-run until clean or until 3 attempts have been made.
- If still failing after 3 attempts: report the remaining failures and ask
  the user whether to commit with known pre-commit issues or stop.

---

## Step F5 — Commit in logical batches

Group the fixed findings into logical commits. Use conventional commit format.
Each commit message must describe *why*, not just *what*.

Suggested groupings (combine if small, split if large):

| Group | Commit type | Example message |
| --- | --- | --- |
| Shell script bugs | `fix(hooks)` | `fix(hooks): read tool input from stdin in rad-strict-hook.sh` |
| Hook config issues | `fix(settings)` | `fix(settings): lower Stop hook timeout; add -e flag comment` |
| Documentation accuracy | `docs` | `docs: correct hook type count and permissions.ask entry count` |
| Em-dash removal | `fix(writing)` | `fix(writing): replace em-dashes in ADRs and narrative pages` |
| SonarQube shell fixes | `fix` | `fix: add default case and explicit return to shell scripts` |
| Pre-commit config | `fix(ci)` | `fix(ci): add types filter to vulture hook in pre-commit config` |
| Python code antipatterns | `fix(code)` | `fix(code): replace == None comparisons with is None` |
| Docstring accuracy | `docs` | `docs: update parameter names in docstrings after signature changes` |
| Bare exception handling | `fix(errors)` | `fix(errors): replace bare except clauses with except Exception` |

Do not bundle unrelated changes into a single commit. One logical concern
per commit.

Sign each commit:

```bash
git -C {WORKTREE_PATH} commit -S -m "..."
```

---

## Step F6 — Present completion options

Once all commits are clean, present exactly these options:

```text
Fixes applied. {N} commits on {HEAD_BRANCH} in {WORKTREE_PATH}.

What would you like to do?

1. Push fixes and add a comment to the PR
2. Push fixes only (no PR comment)
3. Keep worktree — I will review and push manually
4. Discard all fixes

Which option?
```

### Option 1 — Push and comment

```bash
git -C {WORKTREE_PATH} push origin {HEAD_BRANCH}
```

Then post a follow-up comment on the PR:

```bash
gh pr comment {PR_NUMBER} --repo {OWNER}/{REPO} --body "$(cat <<'EOF'
### Fixes Applied

Addressed {N} findings from the review above:

{bullet list of each fix: `[{tier}] {file}:{line} — {one-line description}`}

Pre-commit passing. Ready for re-review.

🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

Then clean up the worktree:

```bash
git worktree remove {WORKTREE_PATH}
```

### Option 2 — Push only

```bash
git -C {WORKTREE_PATH} push origin {HEAD_BRANCH}
git worktree remove {WORKTREE_PATH}
```

### Option 3 — Keep worktree

Report:

```text
Worktree preserved at {WORKTREE_PATH} on branch {HEAD_BRANCH}.
Push when ready: git -C {WORKTREE_PATH} push origin {HEAD_BRANCH}
```

Do not clean up the worktree.

### Option 4 — Discard

Confirm before discarding:

```text
This will permanently delete all {N} fix commits. Type 'discard' to confirm.
```

Wait for the exact word "discard". If confirmed:

```bash
git worktree remove --force {WORKTREE_PATH}
git branch -D {HEAD_BRANCH}-fixes 2>/dev/null || true
```

Do not delete `{HEAD_BRANCH}` itself — that is the original PR branch.

---

## Error Handling

| Situation | Action |
| --- | --- |
| `git fetch` fails | Stop. Check network and `gh auth status`. |
| Worktree already exists | Remove with `--force` and re-create. |
| Pre-commit fails after 3 attempts | Report failures, ask whether to commit anyway or stop. |
| A finding cannot be auto-fixed (needs design judgment) | Note it as "requires manual fix", skip it, continue with others. Report skipped findings in the completion summary. |
| Push rejected (branch protected or diverged) | Report the error. Offer Option 3 (keep worktree for manual push). |
| User picks Option 4 but does not type 'discard' | Do nothing. Re-present the options. |
