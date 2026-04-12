# PR Preparation Workflow

Full pull request description generation workflow.

## Activation

Triggers on: prepare PR, prepare the PR, prepare a PR, create PR, create pull request,
PR description, pull request description, ready for PR, ready to PR, draft PR, write PR

## Workflow

### 0. Confirm CI gates are green

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

### 2. Analyze Changes

Identify:

- **Components modified**: Which files/modules changed
- **Purpose**: Why these changes were made
- **Impact**: Benefits, risks, breaking changes
- **Testing**: What validation was done or needed

### 3. Generate PR Description

Use this template:

```markdown
## Summary

[1-3 sentences: what changed and why]

## Changes

- **[Component]**: [What changed and why]
- **[Component]**: [What changed and why]

## Impact

- ✅ [Key benefit or outcome]
- ✅ [Another benefit]
- ✅ No breaking changes

## Testing

- [ ] Tests pass (`uv run pytest`)
- [ ] Linting passes (`uv run ruff check`)

## Notes

[Optional: known issues, follow-up work, dependencies]
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

### 6. Run automated code review

Immediately after `gh pr create` succeeds, invoke `/pr-review` with the new PR URL:

```text
/pr-review <PR URL returned by gh pr create>
```

This triggers GitHub Copilot review, fetches SonarQube PR-specific findings, and runs
up to 8 parallel agents (CLAUDE.md compliance, bug scan, git-history context, prior PR
comments, comment accuracy, silent failures, test coverage, type design). All findings
are reported in tiers (Critical / Important / Suggested / Informational) — nothing is
filtered. Optionally posts a consolidated comment to the PR.

Only present the final PR URL to the user after the review completes.

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

## Changes

- **auth/oauth.py**: OAuth2 client implementation with token refresh
- **api/routes/auth.py**: Login, logout, and callback endpoints
- **models/user.py**: User model with OAuth provider fields

## Impact

- ✅ Users can sign in with Google or GitHub
- ✅ Secure session management with httponly cookies
- ✅ No breaking changes to existing API

## Testing

- [x] Tests pass (`uv run pytest`)
- [x] Linting passes (`uv run ruff check`)

## Notes

Follow-up: Add Microsoft provider support
```

---

Ready to copy! Create the PR using the `/git pr` skill:

```bash
/git pr
```
