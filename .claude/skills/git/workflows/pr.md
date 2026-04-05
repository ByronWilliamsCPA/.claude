# PR Preparation Workflow

Full pull request description generation workflow.

## Activation

Triggers on: prepare PR, prepare the PR, prepare a PR, create PR, create pull request,
PR description, pull request description, ready for PR, ready to PR, draft PR, write PR

## Workflow

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

### 5. Output

Present the complete PR description ready to copy-paste into GitHub.

Remind the user:
- CodeRabbit will auto-fill `@coderabbitai summary` placeholder if present
- Push and create PR with:

```bash
git push -u origin HEAD
gh pr create --fill
```

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

Ready to copy! Push with:
```bash
git push -u origin HEAD
gh pr create --fill
```
