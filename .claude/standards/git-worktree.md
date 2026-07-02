# Git Worktree Standards

> Worktree setup and teardown is handled by the `using-git-worktrees` and
> `finishing-a-development-branch` superpowers skills. Use those skills rather than
> running worktree commands manually.

## When to Use Worktrees

| Scenario | Use Worktree |
|----------|--------------|
| Long-running feature (>1 session) | Yes |
| Parallel agent work | Yes |
| PR review while working on something else | Yes |
| Hotfix during active feature work | Yes |
| Experimentation / spike | Yes |
| Simple single task | No — branch is sufficient |

## Sibling Directory Convention

Worktrees live at `.worktrees/<branch-slug>` inside the project root. The
`using-git-worktrees` skill enforces this and verifies `.worktrees/` is
git-ignored before creating the first worktree. Never create worktrees at
sibling paths or under user-config directories; see
`.claude/rules/git-workflow.md` for the rationale.

## Key Reminders

- Worktrees share git history but **not** virtual environments — run `uv sync` in each
- Clean up promptly after merging — `finishing-a-development-branch` handles this for
  merge and discard options automatically
