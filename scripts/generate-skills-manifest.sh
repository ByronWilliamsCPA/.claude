#!/usr/bin/env bash
# SessionStart hook: generates skill-observations/available-skills.md by enumerating
# ~/.claude/skills/ and extracting frontmatter descriptions.
# Replaces Cowork's <available_skills> system prompt injection for Claude Code environments.
# Silent on success.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SKILLS_DIR="${HOME}/.claude/skills"
OBS_DIR="${REPO_ROOT}/skill-observations"
OUTPUT="${OBS_DIR}/available-skills.md"

mkdir -p "${OBS_DIR}/archive"

{
    echo "# Available Skills"
    echo "# Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo ""

    if [[ -d "${SKILLS_DIR}" ]]; then
        # Directory-based skills: each has a SKILL.md inside a named subdirectory
        for entry in "${SKILLS_DIR}"/*/; do
            [[ -d "${entry}" ]] || continue
            skill_name="$(basename "${entry}")"
            skill_file="${entry}SKILL.md"
            [[ -f "${skill_file}" ]] || continue

            description="$(awk '
                /^---/ { n++; next }
                n == 1 && /^description:/ {
                    sub(/^description:[[:space:]]*/, "")
                    print
                    exit
                }
            ' "${skill_file}")"

            echo "## ${skill_name}"
            [[ -n "${description}" ]] && echo "${description}"
            echo ""
        done

        # Flat .md skill files directly in skills/
        for skill_file in "${SKILLS_DIR}"/*.md; do
            [[ -f "${skill_file}" ]] || continue
            skill_name="$(basename "${skill_file}" .md)"

            description="$(awk '
                /^---/ { n++; next }
                n == 1 && /^description:/ {
                    sub(/^description:[[:space:]]*/, "")
                    print
                    exit
                }
            ' "${skill_file}")"

            echo "## ${skill_name}"
            [[ -n "${description}" ]] && echo "${description}"
            echo ""
        done
    fi
} > "${OUTPUT}"
