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

mkdir -p "${OBS_DIR}"

TMP_OUT="$(mktemp)"
trap 'rm -f "${TMP_OUT}"' EXIT

{
    echo "# Available Skills"
    echo "# Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo ""

    if [[ -d "${SKILLS_DIR}" ]]; then
        # Collect skill files and their display names into parallel arrays.
        declare -a skill_files=()
        declare -a skill_names=()

        # Directory-based skills: each named subdirectory contains a SKILL.md.
        for entry in "${SKILLS_DIR}"/*/; do
            [[ -d "${entry}" ]] || continue
            skill_file="${entry}SKILL.md"
            [[ -f "${skill_file}" ]] || continue
            skill_files+=("${skill_file}")
            skill_names+=("$(basename "${entry}")")
        done

        # Flat .md skill files directly in skills/.
        for f in "${SKILLS_DIR}"/*.md; do
            [[ -f "${f}" ]] || continue
            skill_files+=("${f}")
            skill_names+=("$(basename "${f}" .md)")
        done

        if [[ ${#skill_files[@]} -gt 0 ]]; then
            # Single awk pass across all skill files: one process for all N files
            # instead of N separate awk subprocesses.
            # Strategy: at each FNR==1 (file boundary), emit the previous file's block
            # and reset state; emit the final block in END.
            awk -v names="$(IFS=':'; echo "${skill_names[*]}")" '
                BEGIN { split(names, name_arr, ":"); file_idx = 0 }
                FNR == 1 {
                    if (file_idx > 0) {
                        print "## " skill_name
                        if (desc != "") print desc
                        print ""
                    }
                    file_idx++
                    skill_name = name_arr[file_idx]
                    fm_count = 0; desc = ""
                }
                /^---/ { fm_count++; next }
                fm_count == 1 && /^description:/ {
                    sub(/^description:[[:space:]]*/, "")
                    desc = $0
                }
                END {
                    if (file_idx > 0) {
                        print "## " skill_name
                        if (desc != "") print desc
                        print ""
                    }
                }
            ' "${skill_files[@]}"
        fi
    fi
} > "${TMP_OUT}"

mv "${TMP_OUT}" "${OUTPUT}"
