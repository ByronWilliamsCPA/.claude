#!/usr/bin/env bash
# CI-compatible lint and fix script
# Usage: ./scripts/ci-lint-fix.sh [--fix] [--target-version py3XX]
set -euo pipefail

FIX_MODE=false
TARGET_VERSION="py310"

while [[ $# -gt 0 ]]; do
  case $1 in
    --fix) FIX_MODE=true; shift ;;
    --target-version) TARGET_VERSION="$2"; shift 2 ;;
    -h|--help) echo "Usage: $0 [--fix] [--target-version py3XX]"; exit 0 ;;
    *) shift ;;
  esac
done

echo "=== Ruff Format ==="
if $FIX_MODE; then ruff format .; else ruff format --check .; fi

echo "=== Ruff Lint ==="
if $FIX_MODE; then
  ruff check --fix --target-version "$TARGET_VERSION" .
else
  ruff check --target-version "$TARGET_VERSION" .
fi

echo "=== Pre-commit ==="
pre-commit run --all-files

echo "=== All checks passed ==="
