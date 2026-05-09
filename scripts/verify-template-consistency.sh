#!/usr/bin/env bash
# verify-template-consistency.sh
# Purpose: Verify this repo's .claude/ matches cookiecutter template structure

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COOKIECUTTER_TEMPLATE="${HOME}/dev/cookiecutter-python-template/{{cookiecutter.project_slug}}/.claude"

echo -e "${GREEN}=== Template Consistency Verification ===${NC}"
echo ""

if [[ ! -d "$COOKIECUTTER_TEMPLATE" ]]; then
    echo -e "${RED}Error: Cookiecutter template not found at $COOKIECUTTER_TEMPLATE${NC}" >&2
    exit 1
fi

# Function to check file existence
check_file_exists() {
    local file="$1"
    local source="$2"
    if [[ ! -f "$file" ]]; then
        echo -e "${RED}✗ Missing: $file${NC}"
        echo -e "  ${YELLOW}Source: $source${NC}"
        return 1
    else
        echo -e "${GREEN}✓ Present: $file${NC}"
        return 0
    fi
}

# Function to compare files
compare_files() {
    local file1="$1"
    local file2="$2"
    local name="$3"

    if [[ ! -f "$file1" ]]; then
        echo -e "${RED}✗ Missing in this repo: $name${NC}"
        return 1
    fi

    if [[ ! -f "$file2" ]]; then
        echo -e "${YELLOW}⚠ Not in cookiecutter: $name${NC}"
        return 0
    fi

    if diff -q "$file1" "$file2" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Identical: $name${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Different: $name${NC}"
        echo -e "  Run: diff $file1 $file2"
        return 1
    fi
}

echo -e "${GREEN}Checking .claude/ directory structure...${NC}"
echo ""

# Check for files that should exist (from cookiecutter)
echo -e "${GREEN}=== Files in Cookiecutter Template ===${NC}"

cd "$COOKIECUTTER_TEMPLATE"
COOKIECUTTER_FILES=$(find . -type f -not -path "*/.*" | sort)

missing_count=0
different_count=0
identical_count=0

for file in $COOKIECUTTER_FILES; do
    repo_file="$REPO_ROOT/.claude/$file"
    cc_file="$COOKIECUTTER_TEMPLATE/$file"

    if [[ ! -f "$repo_file" ]]; then
        echo -e "${RED}✗ Missing: $file${NC}"
        ((missing_count++))
    elif ! diff -q "$repo_file" "$cc_file" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Different: $file${NC}"
        ((different_count++))
    else
        echo -e "${GREEN}✓ Identical: $file${NC}"
        ((identical_count++))
    fi
done

echo ""
echo -e "${GREEN}=== Extra Files in This Repo ===${NC}"

cd "$REPO_ROOT/.claude"
REPO_FILES=$(find . -type f -not -path "*/.*" | sort)

extra_count=0

for file in $REPO_FILES; do
    cc_file="$COOKIECUTTER_TEMPLATE/$file"

    if [[ ! -f "$cc_file" ]]; then
        echo -e "${YELLOW}⚠ Extra (not in cookiecutter): $file${NC}"
        ((extra_count++))
    fi
done

echo ""
echo -e "${GREEN}=== Summary ===${NC}"
echo -e "Identical files: ${GREEN}$identical_count${NC}"
echo -e "Different files: ${YELLOW}$different_count${NC}"
echo -e "Missing files: ${RED}$missing_count${NC}"
echo -e "Extra files: ${YELLOW}$extra_count${NC}"
echo ""

if [[ $missing_count -eq 0 ]] && [[ $different_count -eq 0 ]] && [[ $extra_count -eq 0 ]]; then
    echo -e "${GREEN}✓ .claude/ directory is fully consistent with cookiecutter template${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ .claude/ directory has inconsistencies with cookiecutter template${NC}"
    echo ""
    echo "To sync missing files from cookiecutter:"
    echo "  cd $REPO_ROOT"
    echo "  cp -r $COOKIECUTTER_TEMPLATE/* .claude/"
    echo ""
    echo "To review differences:"
    echo "  diff -r .claude/ $COOKIECUTTER_TEMPLATE/"
    exit 1
fi
