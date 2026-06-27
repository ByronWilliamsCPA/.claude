#!/usr/bin/env bash
INPUT=$(cat)

[ -z "$INPUT" ] && exit 0

FILE_PATH=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    val = data.get('tool_input', {}).get('file_path', '') or ''
    print(val if isinstance(val, str) else '')
except Exception:
    pass
" <<< "$INPUT")

[ -z "$FILE_PATH" ] && exit 0

BASENAME=$(basename "$FILE_PATH")

case "$BASENAME" in
  pyproject.toml|uv.lock|requirements*.txt)
    echo "[Snyk] Dependency file modified. If SNYK_TOKEN is set, invoke snyk_test via the Snyk MCP Server before committing."
    ;;
esac

exit 0
