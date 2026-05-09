#!/bin/bash
# Update Claude standards from the main repository
#
# This script pulls the latest Claude Code standards from the upstream
# repository using git subtree. The standards are maintained separately
# and shared across all projects.

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
# NOTE security-audit L-02: this targets a personal mirror, not the canonical
# ByronWilliamsCPA/.claude org repo. Verify the intended source before running.
# The post-pull `git verify-commit` below requires the upstream commits to be
# signed with a key in the local keyring; remove the pin override only if you
# accept unsigned commits from this remote.
SUBTREE_PREFIX=".claude/standard"
CLAUDE_REPO="https://github.com/williaby/.claude.git"
BRANCH="main"

# Check if we're in a git repository
if [[ ! -d ".git" ]]; then
    echo -e "${RED}Error: Not in a git repository${NC}" >&2
    echo "Please run this script from the root of your project" >&2
    exit 1
fi

# Check if the subtree exists
if [[ ! -d "$SUBTREE_PREFIX" ]]; then
    echo -e "${YELLOW}Warning: Claude standards subtree not found at $SUBTREE_PREFIX${NC}"
    echo ""
    read -p "Do you want to add it now? (Y/n): " -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        echo -e "${GREEN}Adding Claude standards subtree...${NC}"
        git subtree add --prefix "$SUBTREE_PREFIX" "$CLAUDE_REPO" "$BRANCH" --squash
        echo -e "${GREEN}✓ Claude standards added successfully${NC}"
        exit 0
    else
        echo "Cancelled."
        exit 1
    fi
fi

# Pull the latest changes
echo -e "${GREEN}Pulling latest Claude standards from $CLAUDE_REPO...${NC}"
echo ""

git subtree pull --prefix "$SUBTREE_PREFIX" "$CLAUDE_REPO" "$BRANCH" --squash

# Verify upstream provenance (security-audit L-02). git subtree pull --squash
# creates a local merge commit signed by the local key, so a HEAD signature
# only proves the local user merged, not that the upstream content was
# trusted. Verify the SOURCE commit on the remote branch directly. Capture
# stderr so we can distinguish "gpg missing" from "signature missing" from
# "key not in keyring", and require an explicit override to continue when
# verification fails.
if ! command -v gpg >/dev/null 2>&1; then
    echo -e "${RED}ERROR: gpg not installed; cannot verify upstream signature.${NC}" >&2
    echo "Install gpg or rerun with SKIP_SIGNATURE_VERIFY=1 to acknowledge." >&2
    [[ "${SKIP_SIGNATURE_VERIFY:-}" = "1" ]] || exit 1
fi

UPSTREAM_SHA=$(git ls-remote "$CLAUDE_REPO" "refs/heads/$BRANCH" 2>/dev/null | awk '{print $1}')
if [[ -z "$UPSTREAM_SHA" ]]; then
    echo -e "${YELLOW}WARNING: could not resolve upstream HEAD for verification.${NC}" >&2
elif ! VERIFY_OUT=$(git verify-commit "$UPSTREAM_SHA" 2>&1); then
    echo -e "${RED}ERROR: upstream commit ${UPSTREAM_SHA:0:12} failed signature verification.${NC}" >&2
    echo "git verify-commit output:" >&2
    echo "$VERIFY_OUT" >&2
    echo "" >&2
    echo "If the upstream commit is intentionally unsigned, rerun with" >&2
    echo "SKIP_SIGNATURE_VERIFY=1 to acknowledge and continue." >&2
    [[ "${SKIP_SIGNATURE_VERIFY:-}" = "1" ]] || exit 1
fi

echo ""
echo -e "${GREEN}✓ Claude standards updated successfully${NC}"
echo ""
echo "Updated files in $SUBTREE_PREFIX/"
echo ""
echo "Note: If there were conflicts, resolve them and commit the merge."
