---
schema_type: common
title: Syncing with Cookiecutter Template
status: published
owner: engineering
tags: [documentation]
purpose: Describes how to maintain consistency between this Claude configuration source repository and the downstream cookiecutter project template.
---

> **Purpose**: This repository is the **source** for Claude configuration files, not a project generated from the cookiecutter template. This document explains how to maintain consistency between this repo and the cookiecutter template.

## Repository Relationship

```text
┌─────────────────────────────────────────┐
│ /home/byron/dev/.claude/                │
│ (This Repository - Template Source)     │
│                                          │
│ Contains:                                │
│ - .claude/ (Claude Code configuration)  │
│ - standards/ (detailed specs)           │
│ - Linting configuration                 │
└──────────────┬──────────────────────────┘
               │
               │ Manual Sync
               │ (bidirectional)
               ↓
┌─────────────────────────────────────────┐
│ cookiecutter-python-template/           │
│ {{cookiecutter.project_slug}}/.claude/  │
│                                          │
│ Pulls .claude/ configuration            │
│ into generated projects                 │
└──────────────┬──────────────────────────┘
               │
               │ cookiecutter/cruft
               │ (project generation)
               ↓
┌─────────────────────────────────────────┐
│ Downstream Projects                      │
│                                          │
│ Generated with .claude/ configuration   │
└─────────────────────────────────────────┘
```

## Why Not Cruft?

**Cruft is NOT appropriate for this repository** because:
- Cruft is designed for projects **generated FROM** templates
- This repo IS the template source, not a generated project
- Running `cruft update` tries to regenerate entire project structure
- We just cleaned up project structure (removed src/, fuzzing, etc.) because this is a template source, not a package

## Manual Sync Workflows

### Workflow 1: Update .claude/ Files in This Repo → Push to Cookiecutter

**When**: You make changes to .claude/ files here and want them in the cookiecutter template

**Steps**:
```bash
# 1. Make and test changes in this repo
cd /home/byron/dev/.claude
# ... edit files in .claude/ ...

# 2. Run linters to ensure quality
ruff check .
ruff format --check .
qlty check  # If qlty is installed

# 3. Commit changes here
git add .claude/
git commit -m "feat: update .claude configuration"
git push origin main

# 4. Copy to cookiecutter template
cp -r .claude/* /home/byron/dev/cookiecutter-python-template/{{cookiecutter.project_slug}}/.claude/

# 5. Commit in cookiecutter template
cd /home/byron/dev/cookiecutter-python-template
git add {{cookiecutter.project_slug}}/.claude/
git commit -m "feat: sync .claude from template source"
git push origin main
```

### Workflow 2: Pull Updates from Cookiecutter → Update This Repo

**When**: Cookiecutter template has .claude/ updates you want to pull back

**Steps**:
```bash
# 1. Copy from cookiecutter template
cd /home/byron/dev/.claude
cp -r /home/byron/dev/cookiecutter-python-template/{{cookiecutter.project_slug}}/.claude/* .claude/

# 2. Review changes
git status
git diff .claude/

# 3. Run linters to verify quality
ruff check .
ruff format --check .

# 4. Commit if acceptable
git add .claude/
git commit -m "chore: sync .claude from cookiecutter template"
git push origin main
```

### Workflow 3: Update Linting Configuration

**When**: Updating ruff, qlty, or other quality tools to prevent downstream issues

**Files to Update**:
- `pyproject.toml` - Ruff configuration
- `.pre-commit-config.yaml` - Pre-commit hooks
- `.qlty/qlty.toml` - Qlty configuration (if present)
- `.github/workflows/` - CI workflows

**Steps**:
```bash
cd /home/byron/dev/.claude

# 1. Update configuration files
# Edit pyproject.toml, .pre-commit-config.yaml, etc.

# 2. Test locally
ruff check .
ruff format .
uv run pre-commit run --all-files

# 3. Verify no downstream issues
# Test on a sample downstream project:
cd /path/to/test-project
# ... test linting ...

# 4. Commit and push
cd /home/byron/dev/.claude
git add pyproject.toml .pre-commit-config.yaml .qlty/
git commit -m "chore: update linting configuration"
git push origin main

# 5. Optionally sync to cookiecutter template
# (if you want new projects to have updated config)
```

## Quality Assurance Strategy

### Before Committing ANY Changes

**Always run these checks**:

```bash
# 1. Format code
ruff format .

# 2. Check linting
ruff check .

# 3. Run all quality checks (if qlty installed)
qlty check

# 4. Verify no issues
echo "If all checks pass, proceed to commit"
```

### Pre-Commit Hook

The `.pre-commit-config.yaml` automatically runs quality checks:
- Ruff formatting
- Ruff linting
- YAML linting
- Markdown linting
- Secret detection (trufflehog, gitleaks)

**To skip hooks** (only for exceptional cases like cleanup commits):
```bash
git commit --no-verify -m "..."
```

### CI/CD Validation

GitHub Actions runs on every push:
- `.github/workflows/ci.yml` - Full CI suite
- `.github/workflows/pr-validation.yml` - PR checks
- `.github/workflows/security-analysis.yml` - Security scanning

**View CI status**: Check GitHub Actions tab after pushing

## Preventing Downstream Issues

### Strategy

1. **Test Changes Locally First**
   - Run all linters before committing
   - Test on a sample downstream project if possible

2. **Use Conventional Commits**
   - `feat:` - New features (minor version bump)
   - `fix:` - Bug fixes (patch version bump)
   - `chore:` - Maintenance (no version bump)
   - `BREAKING CHANGE:` - Breaking changes (major version bump)

3. **Document Breaking Changes**
   - Put a `BREAKING CHANGE:` footer in the commit message so python-semantic-release
     records it in the generated changelog at release (do not hand-edit CHANGELOG.md)
   - Add migration guide if needed
   - Notify downstream project maintainers

4. **Version Tagging**
   - Tag releases: `git tag v1.1.0`
   - Push tags: `git push origin v1.1.0`
   - Downstream projects can pin to specific versions

### Example: Adding New Ruff Rule

```bash
# 1. Add rule to pyproject.toml
vim pyproject.toml
# Add "NEW" to select = [...] list

# 2. Test on this repo
ruff check .
# Fix any issues found

# 3. Test on downstream project
cd /path/to/downstream-project
ruff check .
# Ensure no new issues or document fixes needed

# 4. Commit with clear message
cd /home/byron/dev/.claude
git add pyproject.toml
git commit -m "feat(lint): add NEW rule to ruff configuration

- Adds NEW rule for better code quality
- Tested on template source and sample downstream project
- No breaking changes for compliant code"

# 5. Push and sync to cookiecutter
git push origin main
# ... sync to cookiecutter template ...
```

## File Sync Checklist

When syncing .claude/, ensure these files are included:

**Core Files**:
- [ ] `.claude/README.md`
- [ ] `.claude/settings.local.json.example`

**Directories**:
- [ ] `.claude/agents/` (all agent definitions)
- [ ] `.claude/commands/` (all command definitions)
- [ ] `.claude/context/` (all context files)
- [ ] `.claude/skills/` (all skill directories)

**Verify After Sync**:
```bash
# Count files
find .claude -type f | wc -l
# Should match cookiecutter template

# Check for differences
diff -r .claude/ /home/byron/dev/cookiecutter-python-template/{{cookiecutter.project_slug}}/.claude/
# Should show no differences (or expected differences only)
```

## Troubleshooting

### Issue: Lint Errors After Sync

**Solution**:
```bash
# Auto-fix what's possible
ruff check --fix .
ruff format .

# Review remaining issues
ruff check .

# Fix manually or add to ignore list in pyproject.toml
```

### Issue: Pre-commit Hook Failures

**Solution**:
```bash
# Update pre-commit hooks
uv run pre-commit autoupdate

# Run manually to see issues
uv run pre-commit run --all-files

# Fix issues or update configuration
```

### Issue: Cookiecutter Template Diverged

**Solution**:
```bash
# Compare directories
diff -r .claude/ /home/byron/dev/cookiecutter-python-template/{{cookiecutter.project_slug}}/.claude/

# Decide which is authoritative
# Then copy from authoritative source to other location
```

## Regular Maintenance

### Weekly
- [ ] Check for lint configuration updates
- [ ] Review pre-commit hook versions
- [ ] Scan for security updates

### Monthly
- [ ] Review and update dependencies
- [ ] Check GitHub Actions for failures
- [ ] Verify downstream projects using template

### Quarterly
- [ ] Major version review
- [ ] Breaking change planning
- [ ] Documentation updates

---

**Remember**: This repo is the source, not a generated project. Quality here affects all downstream projects!
