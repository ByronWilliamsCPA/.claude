#!/usr/bin/env bash
# =============================================================================
# Diagram Renderer — docs/architecture/diagrams/*.puml → *.svg
# =============================================================================
# Renders PlantUML sources to SVG siblings. Idempotent: safe to re-run.
#
# Usage:
#   ./scripts/render_diagrams.sh                    # render all .puml files
#   ./scripts/render_diagrams.sh path/to/one.puml   # render one file
#
# Requirements (one of):
#   - plantuml on PATH (Debian: apt install plantuml; Mac: brew install plantuml)
#   - docker (falls back to plantuml/plantuml image if local binary missing)
#
# Exit codes:
#   0 — all sources rendered successfully
#   1 — at least one render failed
#   2 — no renderer available (neither plantuml nor docker)
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIAGRAM_DIR="${REPO_ROOT}/docs/architecture/diagrams"

if [[ ! -d "$DIAGRAM_DIR" ]]; then
    echo "error: diagram directory not found: $DIAGRAM_DIR" >&2
    exit 1
fi

# Collect sources: args if given, otherwise every .puml under DIAGRAM_DIR.
if [[ $# -gt 0 ]]; then
    sources=("$@")
else
    mapfile -t sources < <(find "$DIAGRAM_DIR" -maxdepth 1 -name '*.puml' -type f | sort)
fi

if [[ ${#sources[@]} -eq 0 ]]; then
    echo "warn: no .puml sources found in $DIAGRAM_DIR" >&2
    exit 0
fi

# Pick a renderer.
if command -v plantuml >/dev/null 2>&1; then
    renderer="native"
elif command -v docker >/dev/null 2>&1; then
    renderer="docker"
else
    echo "error: neither 'plantuml' nor 'docker' found on PATH" >&2
    echo "install plantuml locally or run with docker available" >&2
    exit 2
fi

echo "renderer: $renderer"
echo "sources:  ${#sources[@]} file(s)"

failed=0
for src in "${sources[@]}"; do
    if [[ ! -f "$src" ]]; then
        echo "  skip $src (not found)"
        failed=1
        continue
    fi

    case "$renderer" in
        native)
            if plantuml -tsvg "$src"; then
                echo "  ok   $src"
            else
                echo "  FAIL $src" >&2
                failed=1
            fi
            ;;
        docker)
            # Mount the diagram directory and run plantuml inside the container.
            # Run as the invoking user so output SVGs are not root-owned.
            dir="$(dirname "$(realpath "$src")")"
            name="$(basename "$src")"
            if docker run --rm \
                --user "$(id -u):$(id -g)" \
                -v "$dir:/work" -w /work \
                plantuml/plantuml -tsvg "$name" >/dev/null; then
                echo "  ok   $src"
            else
                echo "  FAIL $src" >&2
                failed=1
            fi
            ;;
    esac
done

exit "$failed"
