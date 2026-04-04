---
description: Generate a handoff document for session continuity
allowed-tools: [Read, Write, Bash, Glob]
---

Create a structured handoff document for the current work session.

1. Gather state:
   - `git branch --show-current`
   - `git status`
   - `git log --oneline -10`
   - `git diff --stat`
2. Check any in-progress TODO items
3. Write to `tmp_cleanup/.tmp-handoff-$(date +%Y%m%d-%H%M).md` with sections:
   - **What Was Done**: completed items with file paths
   - **What Remains**: incomplete items, ordered by priority
   - **Key Decisions**: architecture/design decisions with rationale
   - **Files Modified**: from git diff --stat
   - **How to Resume**: exact next steps with commands
   - **Gotchas**: non-obvious context the next session needs
4. Output the path to the generated file
