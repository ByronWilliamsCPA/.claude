# PR Preparation Workflow

Full pull request description generation workflow.

## Activation

Triggers on: prepare PR, prepare the PR, prepare a PR, create PR, create pull request,
PR description, pull request description, ready for PR, ready to PR, draft PR, write PR

## Workflow

### 0. Confirm CI gates are green

#### 0a. Fetch and freshness check

```bash
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
if [ "$BEHIND" -gt 0 ]; then
  echo "Branch is $BEHIND commit(s) behind origin. Rebase before continuing."
  git rebase origin/main
fi
```

If rebase produces conflicts, stop here. Resolve conflicts and re-run `/git pr`.

#### 0b. CI gate

Before creating the PR, confirm `/ci-fix` has been run and all gates are green. If not,
run it now:

```text
/ci-fix
```

Do not proceed with PR creation until all blockers are resolved. pip-audit findings
should be documented in the PR description if they cannot be resolved immediately.

### 1. Gather Context

```bash
# Current state
git status

# Commits on this branch vs main
git log $(git merge-base HEAD main)..HEAD --oneline

# Files changed
git diff $(git merge-base HEAD main)..HEAD --stat

# Actual diff (for smaller changes)
git diff $(git merge-base HEAD main)..HEAD
```

> If the base branch is not `main`, substitute the correct base (e.g., `develop`).

### 1b. Self-review

Before writing the description, scan the diff for common problems:

```bash
git diff $(git merge-base HEAD main)..HEAD
```

Check for:

- Debugging artifacts: `print()`, `console.log()`, `debugger`, `.only`, `TODO: remove`
- Committed secrets: API keys, tokens, passwords, private keys
- Unintended file changes: lock files with unexpected diffs, generated files, IDE config
- Incomplete work: `raise NotImplementedError`, `pass`, empty function bodies meant as stubs

If any of these are found, stop and ask the user to address them before continuing.

### 2. Analyze Changes

Identify:

- **Components modified**: Which files/modules changed
- **Purpose**: Why these changes were made
- **Impact**: Benefits, risks, breaking changes
- **Testing**: What validation was done or needed
- **CHANGELOG**: If any commit uses type `feat`, `fix`, `perf`, or includes `!` (breaking
  change), verify that `CHANGELOG.md` has been updated. If not, note it as a required
  action before PR creation.
- **Size**: Count total lines changed (`git diff $(git merge-base HEAD main)..HEAD --stat |
  tail -1`). If > 500 lines, consider whether the PR can be split. Recommend a split when
  changes span unrelated concerns (for example, a feature addition combined with a
  large refactor or documentation overhaul).

### 3. Generate PR Description

Use this template:

```markdown
## Summary

[1-3 sentences: what changed and why]

## Why

[Motivation. What problem does this solve, or what opportunity does it capture?
Link to the issue, ticket, or decision that drove this work.]

## Changes

- **[Component]**: [What changed and why]
- **[Component]**: [What changed and why]

## Impact

- ✅ [Key benefit or outcome]
- ✅ [Another benefit]
- ✅ No breaking changes

## Acceptance Criteria

- [ ] [Observable behaviour that confirms this works correctly]
- [ ] [Edge case or boundary condition that must hold]

## Migration and Rollback

[Required only for schema changes, API changes, config changes, or anything that
affects deployed state. Describe the migration steps and how to roll back if needed.
Omit this section for pure code changes with no deployment side-effects.]

## Testing

- [ ] Tests pass (`uv run pytest`)
- [ ] Format passes (`uv run ruff format --check`)
- [ ] Linting passes (`uv run ruff check`)
- [ ] Type checking passes (`uv run basedpyright`)
- [ ] CHANGELOG.md updated (required for feat, fix, perf, or breaking changes)

## Notes

[Optional: known issues, follow-up work, pip-audit findings that cannot be resolved
immediately, or other context reviewers should know.]
```

### 4. Suggest PR Title

Follow conventional commits format (see `context/conventional-commits.md`):

| Type | When to Use |
| ---- | ----------- |
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code restructuring |
| `test:` | Adding tests |
| `perf:` | Performance improvement |
| `chore:` | Maintenance, dependencies |

### 5. Create the PR

Use the `/git pr` skill to push and create the PR. This keeps the workflow consistent with
the documented path and ensures all PR safeguards are applied:

```text
/git pr
```

The skill handles `git push -u origin HEAD` and `gh pr create` with the correct title and
body generated in the steps above.

**Share the PR URL with the user immediately** after `gh pr create` returns it. Do not
wait for the review in Step 6 to complete before showing the URL.

### 6. Run automated code review

Immediately after `gh pr create` succeeds, invoke `/pr-review` with the new PR URL:

```text
/pr-review <PR URL returned by gh pr create>
```

This triggers GitHub Copilot review, fetches SonarQube PR-specific findings, and runs
up to 8 parallel agents (CLAUDE.md compliance, bug scan, git-history context, prior PR
comments, comment accuracy, silent failures, test coverage, type design). All findings
are reported in tiers (Critical / Important / Suggested / Informational); nothing is
filtered. Optionally posts a consolidated comment to the PR.

The PR URL was already shared with the user in Step 5. Present the final review report
to the user after the review completes.

---

## Example Interaction

**User**: "Can you prepare the PR for this branch?"

1. Run git commands to gather context
2. Analyze the changes
3. Output:

---

**Suggested Title**: `feat: add user authentication with OAuth2`

**PR Description**:

```markdown
## Summary

Add OAuth2 authentication supporting Google and GitHub providers.

## Why

Users currently have no SSO option, requiring manual password management. This
unblocks the enterprise customer pilot that requires SSO. Tracks #142.

## Changes

- **auth/oauth.py**: OAuth2 client implementation with token refresh
- **api/routes/auth.py**: Login, logout, and callback endpoints
- **models/user.py**: User model with OAuth provider fields

## Impact

- ✅ Users can sign in with Google or GitHub
- ✅ Secure session management with httponly cookies
- ✅ No breaking changes to existing API

## Acceptance Criteria

- [ ] Clicking "Sign in with Google" redirects and returns a valid session
- [ ] Expired tokens refresh automatically without user action

## Testing

- [x] Tests pass (`uv run pytest`)
- [x] Format passes (`uv run ruff format --check`)
- [x] Linting passes (`uv run ruff check`)
- [x] Type checking passes (`uv run basedpyright`)
- [x] CHANGELOG.md updated

## Notes

Follow-up: Add Microsoft provider support
```

---

Ready to copy! Create the PR using the `/git pr` skill:

```bash
/git pr
```
