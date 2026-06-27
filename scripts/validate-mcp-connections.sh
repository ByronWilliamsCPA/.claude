#!/usr/bin/env bash
# Validates MCP server connectivity from any project directory.
# Usage: bash ~/.claude/scripts/validate-mcp-connections.sh

set -euo pipefail

PASS=0
FAIL=0
WARN=0

check() {
  local name="$1"
  local result="$2"
  local detail="$3"
  if [[ "$result" == "ok" ]]; then
    echo "  [OK]   $name: $detail"
    PASS=$((PASS + 1))
  elif [[ "$result" == "warn" ]]; then
    echo "  [WARN] $name: $detail"
    WARN=$((WARN + 1))
  else
    echo "  [FAIL] $name: $detail"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== MCP Connection Validation ==="
echo ""

echo "-- Environment --"
if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
  GH_USER=$(curl -sf -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
    https://api.github.com/user 2>/dev/null \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('login','unknown'))" 2>/dev/null \
    || echo "error")
  if [[ "$GH_USER" == "error" ]]; then
    check "GITHUB_PERSONAL_ACCESS_TOKEN" "fail" "set but GitHub auth failed: token may be expired"
  else
    check "GITHUB_PERSONAL_ACCESS_TOKEN" "ok" "authenticates as $GH_USER"
  fi
else
  check "GITHUB_PERSONAL_ACCESS_TOKEN" "fail" "NOT SET: add to ~/.bashrc"
fi

if [[ -n "${SONARQUBE_TOKEN:-}" ]]; then
  check "SONARQUBE_TOKEN" "ok" "set (${#SONARQUBE_TOKEN} chars)"
else
  check "SONARQUBE_TOKEN" "fail" "NOT SET: add to ~/.bashrc"
fi

if [[ -n "${SNYK_TOKEN:-}" ]]; then
  check "SNYK_TOKEN" "ok" "set"
else
  check "SNYK_TOKEN" "warn" "NOT SET: snyk MCP tools will fail auth"
fi

echo ""
echo "-- Servers --"

# zen/pal: check if python venv and server.py exist
ZEN_PY="/home/byron/dev/zen-mcp-server/.pal_venv/bin/python"
ZEN_SRV="/home/byron/dev/zen-mcp-server/server.py"
if [[ -x "$ZEN_PY" && -f "$ZEN_SRV" ]]; then
  check "zen (pal)" "ok" "venv and server.py present"
else
  check "zen (pal)" "fail" "missing venv or server.py at $ZEN_PY / $ZEN_SRV"
fi

# context7: check npx reachable
NPX_PATH=$(which npx 2>/dev/null || echo "")
if [[ -n "$NPX_PATH" ]]; then
  check "context7" "ok" "npx found at $NPX_PATH"
else
  check "context7" "fail" "npx not in PATH: VSCode extension may need absolute path in settings.json"
fi

# github MCP: check docker running and PAT set
if docker info &>/dev/null; then
  if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
    check "github" "ok" "docker running and PAT set"
  else
    check "github" "fail" "docker running but GITHUB_PERSONAL_ACCESS_TOKEN not set"
  fi
else
  check "github" "fail" "docker not running: start Docker Desktop"
fi

# sonarqube and sonarqube-williaby: check HTTP endpoints
# Note: use -s (silent) without -f so 4xx responses still emit the code via -w.
# curl connection failures produce empty output; default to "000" with ${var:-000}.
for port in 8090 8091; do
  name="sonarqube"
  [[ "$port" == "8091" ]] && name="sonarqube-williaby"
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${SONARQUBE_TOKEN:-}" \
    "http://localhost:$port/mcp" 2>/dev/null)
  HTTP_CODE="${HTTP_CODE:-000}"
  if [[ "$HTTP_CODE" == "405" || "$HTTP_CODE" == "200" ]]; then
    check "$name" "ok" "port $port responding (HTTP $HTTP_CODE)"
  elif [[ "$HTTP_CODE" == "000" ]]; then
    check "$name" "fail" "port $port unreachable: is the Docker container running?"
  else
    check "$name" "warn" "port $port returned HTTP $HTTP_CODE"
  fi
done

# codebase-memory-mcp: check binary presence
if command -v codebase-memory-mcp &>/dev/null; then
  CBM_VERSION=$(codebase-memory-mcp --version 2>/dev/null || echo "unknown")
  check "codebase-memory-mcp" "ok" "binary present ($CBM_VERSION)"
else
  check "codebase-memory-mcp" "fail" "binary not found: run codebase-memory-mcp install"
fi

# snyk: check SNYK_TOKEN (already checked above in env section, but also check npx)
if command -v npx &>/dev/null && [[ -n "${SNYK_TOKEN:-}" ]]; then
  check "snyk" "ok" "npx reachable and SNYK_TOKEN set"
elif command -v npx &>/dev/null; then
  check "snyk" "warn" "npx reachable but SNYK_TOKEN not set"
else
  check "snyk" "fail" "npx not in PATH: snyk MCP cannot start"
fi

echo ""
echo "=== Summary: $PASS ok, $WARN warn, $FAIL fail ==="
[[ $FAIL -gt 0 ]] && exit 1 || exit 0
