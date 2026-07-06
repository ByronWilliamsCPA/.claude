#!/usr/bin/env bash
# SessionStart hook: delegation-aware wrapper around codebase-memory-mcp's
# session reminder. Replaces the binary-managed ~/.claude/hooks/
# cbm-session-reminder entry in settings.json so the wording survives
# codebase-memory-mcp binary upgrades (which rewrite that file).
#
# Registered in ~/.claude/settings.json under hooks.SessionStart with matchers
# startup|resume|clear|compact.
set -uo pipefail

cat <<'EOF'
Code Discovery Protocol:
1. Prefer codebase-memory-mcp tools for code exploration, in whichever
   context does the exploring (main session or subagent):
   - search_graph / query_graph for functions, classes, routes, patterns
   - trace_path for call chains and data flow
   - get_code_snippet for exact symbol source
   - get_architecture for project structure
   - search_code for graph-augmented text search
2. Multi-file exploration belongs in an Explore subagent (which applies the
   same tool preference); reserve main-session lookups for 1-2 known files.
3. If a project is not indexed yet, run index_repository first.
4. Use Grep/Glob/Read freely for prose, configs, and non-code files, and
   always Read a file before editing it.
EOF
