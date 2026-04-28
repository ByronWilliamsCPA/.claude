# Project Scripts

Utility scripts for Claude Code Configuration.

## Available Scripts

### update-claude-standards.sh

Updates the Claude Code standards from the upstream repository.

**Usage**:
```bash
./scripts/update-claude-standards.sh
```

**What it does**:
- Pulls the latest Claude Code standards from [williaby/.claude](https://github.com/williaby/.claude)
- Updates the `.claude/standard/` directory via git subtree
- Preserves project-specific configuration in `.claude/claude.md`

**When to run**:
- Periodically to get latest standards and best practices
- When new Claude Code features are announced
- When security or quality updates are released

**Note**: The update uses `git subtree pull --squash` to maintain a clean commit history.

### install-hooks.sh

Installs the pre-push hook from `.github/hooks/pre-push` into the active `.git/hooks/` directory.

**Usage**:

```bash
./scripts/install-hooks.sh
```

**What it does**:

- Copies `.github/hooks/pre-push` to the correct hooks directory (uses `git rev-parse --git-common-dir` so it works in git worktrees)
- Makes the installed hook executable

**When to run**:

- Once after cloning the repository
- Safe to re-run at any time; re-running overwrites the previous install with no side effects

**Note**: To skip the hook on a specific push, use `git push --no-verify`.

## Adding New Scripts

When adding new scripts to this directory:

1. Make them executable: `chmod +x scripts/your-script.sh`
2. Add shebang line: `#!/bin/bash` (or appropriate interpreter)
3. Add usage documentation to this README
4. Use `set -e` to exit on errors
5. Add colorized output for better UX

## Script Conventions

- **Exit codes**: 0 for success, non-zero for errors
- **Output**: Use colors (GREEN for success, YELLOW for warnings, RED for errors)
- **Error handling**: Always check preconditions (e.g., git repo exists)
- **User interaction**: Confirm destructive operations
- **Documentation**: Include usage examples in this README
