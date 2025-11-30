#!/usr/bin/env bash
# cleanup-template-repo.sh
# Purpose: Clean up template repository to match cookiecutter structure
# Safe to run - creates backup before deletion

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${GREEN}=== Template Repository Cleanup ===${NC}"
echo "Repo root: $REPO_ROOT"
echo ""

# Function to confirm action
confirm() {
    local prompt="$1"
    read -p "$(echo -e ${YELLOW}${prompt}${NC}) (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# Function to create backup
create_backup() {
    local backup_dir="$REPO_ROOT/.cleanup-backup-$(date +%Y%m%d-%H%M%S)"
    echo -e "${GREEN}Creating backup at: $backup_dir${NC}"
    mkdir -p "$backup_dir"
    echo "$backup_dir"
}

# Phase 1: Safe deletions (cache/generated files)
phase1_safe_deletions() {
    echo -e "${GREEN}=== Phase 1: Safe Deletions (Cache & Generated Files) ===${NC}"

    if ! confirm "Delete cache and generated files? (Safe - all regenerable)"; then
        echo "Skipping Phase 1"
        return
    fi

    cd "$REPO_ROOT"

    # Remove cache directories
    echo "Removing .ruff_cache/..."
    rm -rf .ruff_cache/

    echo "Removing htmlcov/..."
    rm -rf htmlcov/

    echo "Removing coverage files..."
    rm -f .coverage coverage.xml

    echo "Removing __pycache__ directories..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

    echo "Removing .pytest_cache directories..."
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

    # Remove empty directories
    echo "Removing empty data/ and configs/ directories..."
    rm -rf data/ configs/

    echo -e "${GREEN}✓ Phase 1 complete${NC}"
    echo ""
}

# Phase 2: Template artifacts
phase2_template_artifacts() {
    echo -e "${GREEN}=== Phase 2: Template Artifacts ===${NC}"

    if ! confirm "Remove template documentation artifacts?"; then
        echo "Skipping Phase 2"
        return
    fi

    cd "$REPO_ROOT"

    if [ -f "CONFIG_TEMPLATES_SUMMARY.md" ]; then
        echo "Removing CONFIG_TEMPLATES_SUMMARY.md..."
        rm -f CONFIG_TEMPLATES_SUMMARY.md
    fi

    echo -e "${GREEN}✓ Phase 2 complete${NC}"
    echo ""
}

# Phase 3: Root-level duplicates (with backup)
phase3_root_duplicates() {
    echo -e "${GREEN}=== Phase 3: Root-Level Duplicate Directories ===${NC}"
    echo "These directories exist at root but are NOT in cookiecutter template:"
    echo "  - agents/"
    echo "  - commands/"
    echo "  - context/"
    echo "  - skills/"
    echo "  - templates/"
    echo ""
    echo "They should live in .claude/ directory instead."
    echo ""

    if ! confirm "Remove root-level duplicate directories? (Will backup first)"; then
        echo "Skipping Phase 3"
        return
    fi

    # Create backup
    backup_dir=$(create_backup)

    cd "$REPO_ROOT"

    # Backup before deletion
    for dir in agents commands context skills templates; do
        if [ -d "$dir" ]; then
            echo "Backing up $dir/ to $backup_dir/$dir/"
            cp -r "$dir" "$backup_dir/"
            echo "Removing $dir/..."
            rm -rf "$dir"
        fi
    done

    echo -e "${GREEN}✓ Phase 3 complete${NC}"
    echo -e "${YELLOW}Backup saved at: $backup_dir${NC}"
    echo ""
}

# Phase 4: Python package source
phase4_package_source() {
    echo -e "${GREEN}=== Phase 4: Python Package Source ===${NC}"
    echo "This is a template repository, not a distributable Python package."
    echo ""

    if ! confirm "Remove src/claude_config/ directory?"; then
        echo "Skipping Phase 4"
        return
    fi

    cd "$REPO_ROOT"

    if [ -d "src/claude_config" ]; then
        echo "Removing src/claude_config/..."
        rm -rf src/claude_config/

        # Check if src/ is now empty
        if [ -z "$(ls -A src/)" ]; then
            echo "Removing empty src/ directory..."
            rm -rf src/
        fi
    fi

    echo -e "${GREEN}✓ Phase 4 complete${NC}"
    echo ""
}

# Phase 5: Fuzzing infrastructure
phase5_fuzzing() {
    echo -e "${GREEN}=== Phase 5: Fuzzing Infrastructure ===${NC}"
    echo "Fuzzing is likely overkill for a template repository."
    echo ""

    if ! confirm "Remove fuzzing infrastructure (.clusterfuzzlite/, fuzz/)?"; then
        echo "Skipping Phase 5"
        return
    fi

    cd "$REPO_ROOT"

    if [ -d ".clusterfuzzlite" ]; then
        echo "Removing .clusterfuzzlite/..."
        rm -rf .clusterfuzzlite/
    fi

    if [ -d "fuzz" ]; then
        echo "Removing fuzz/..."
        rm -rf fuzz/
    fi

    echo -e "${GREEN}✓ Phase 5 complete${NC}"
    echo ""
}

# Phase 6: Unnecessary CI workflows
phase6_ci_workflows() {
    echo -e "${GREEN}=== Phase 6: Unnecessary CI Workflows ===${NC}"
    echo "Suggested removals for template repository:"
    echo "  - publish-pypi.yml (not publishing package)"
    echo "  - mutation-testing.yml (excessive for template)"
    echo "  - slsa-provenance.yml (not building artifacts)"
    echo ""

    if ! confirm "Remove unnecessary CI workflows?"; then
        echo "Skipping Phase 6"
        return
    fi

    cd "$REPO_ROOT/.github/workflows"

    for workflow in publish-pypi.yml mutation-testing.yml slsa-provenance.yml; do
        if [ -f "$workflow" ]; then
            echo "Removing $workflow..."
            rm -f "$workflow"
        fi
    done

    echo -e "${GREEN}✓ Phase 6 complete${NC}"
    echo ""
}

# Phase 7: Update .gitignore
phase7_gitignore() {
    echo -e "${GREEN}=== Phase 7: Update .gitignore ===${NC}"

    if ! confirm "Update .gitignore to prevent cache buildup?"; then
        echo "Skipping Phase 7"
        return
    fi

    cd "$REPO_ROOT"

    # Entries to ensure are in .gitignore
    IGNORE_ENTRIES=(
        "__pycache__/"
        "*.pyc"
        ".pytest_cache/"
        ".coverage"
        "coverage.xml"
        "htmlcov/"
        ".ruff_cache/"
        ".mypy_cache/"
    )

    for entry in "${IGNORE_ENTRIES[@]}"; do
        if ! grep -qF "$entry" .gitignore 2>/dev/null; then
            echo "Adding $entry to .gitignore"
            echo "$entry" >> .gitignore
        fi
    done

    echo -e "${GREEN}✓ Phase 7 complete${NC}"
    echo ""
}

# Summary
show_summary() {
    echo -e "${GREEN}=== Cleanup Summary ===${NC}"
    echo ""
    echo "Completed cleanup phases. Next steps:"
    echo ""
    echo "1. Verify .claude/ directory matches cookiecutter template:"
    echo "   $ diff -r .claude/ /home/byron/dev/cookiecutter-python-template/{{cookiecutter.project_slug}}/.claude/"
    echo ""
    echo "2. Run linters to verify nothing broke:"
    echo "   $ ruff check ."
    echo "   $ ruff format --check ."
    echo ""
    echo "3. Commit changes:"
    echo "   $ git add -A"
    echo "   $ git status"
    echo "   $ git commit -m 'chore: clean up template repository structure'"
    echo ""
    echo "4. Sync any missing files from cookiecutter template (see .tmp-template-cleanup-plan.md)"
    echo ""
}

# Main execution
main() {
    echo "This script will clean up the template repository in phases."
    echo "You can skip any phase you don't want to execute."
    echo ""

    if ! confirm "Proceed with cleanup?"; then
        echo "Cleanup cancelled."
        exit 0
    fi

    echo ""

    # Execute phases
    phase1_safe_deletions
    phase2_template_artifacts
    phase3_root_duplicates
    phase4_package_source
    phase5_fuzzing
    phase6_ci_workflows
    phase7_gitignore

    show_summary

    echo -e "${GREEN}Cleanup script complete!${NC}"
}

# Run main
main
