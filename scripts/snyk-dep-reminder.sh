#!/usr/bin/env bash
INPUT=$(cat)

[ -z "$INPUT" ] && exit 0

FILE_PATH=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    print(data.get('tool_input', {}).get('file_path', ''))
except Exception:
    pass
" <<< "$INPUT")

[ -z "$FILE_PATH" ] && exit 0

BASE=$(basename "$FILE_PATH")

case "$BASE" in
    pyproject.toml|uv.lock)
        MATCH=1
        ;;
    requirements*.txt)
        MATCH=1
        ;;
    *)
        MATCH=0
        ;;
esac

if [ "$MATCH" -eq 1 ]; then
    echo "[Snyk] Dependency file modified. If SNYK_TOKEN is set, invoke snyk_test via the Snyk MCP Server before committing."
fi

exit 0
