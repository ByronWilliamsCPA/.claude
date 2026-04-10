# PR Preparation Workflow

Full pull request description generation workflow.

## Activation

Triggers on: prepare PR, prepare the PR, prepare a PR, create PR, create pull request,
PR description, pull request description, ready for PR, ready to PR, draft PR, write PR

## Workflow

### 0. Confirm CI gates are green

Before creating the PR, confirm `/ci-fix` has been run and all gates are green. If not,
run it now:

```
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
|------|-------------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code restructuring |
| `test:` | Adding tests |
| `perf:` | Performance improvement |
| `chore:` | Maintenance, dependencies |

### 5. Create the PR

Push the branch and create the PR:

```bash
git push -u origin HEAD
gh pr create --title "<title>" --body "<description>"
```

### 6. Run automated code review

Immediately after `gh pr create` succeeds, invoke the `/code-review` command to run the 5-agent review against the new PR:

```
/code-review
```

This runs before notifying the user the PR is ready. The review posts a comment on the PR with any issues scoring ≥80 confidence (CLAUDE.md compliance, bug scan, git history context, comment compliance). If no issues are found, it posts a clean confirmation.

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
