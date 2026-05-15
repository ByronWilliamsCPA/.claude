# Aggregate Skill Observations

Scan all repositories under `~/dev/` for local `skill-observations/log.md`
files that have not been merged into the global observation log. This
catches cases where the task-observer wrote observations to a project-local
directory instead of the canonical global path.

## Steps

### 1. Identify stray observation logs

Search all repos for skill-observation logs, excluding the canonical one:

```bash
find /home/byron/dev -name "log.md" -path "*/skill-observations/*" \
  | grep -v "^/home/byron/dev/.claude/skill-observations/"
```

If no files are found, report: "No stray observation logs found. All
observations are already in the global log." Stop here.

### 2. For each stray log found

Read the file and extract all observations. For each observation, check
whether it already exists in the canonical log at
`/home/byron/.claude/skill-observations/log.md` by searching for its
title (the text after `### Observation N: `).

Produce a table showing:
- Source repo path
- Observation number (local) and title
- Status (OPEN / ACTIONED / DECLINED)
- Already in global log? (yes / no)

Present this table to the user before doing anything.

### 3. Ask the user which observations to import

For any observation NOT already in the global log:
- Default: import all OPEN observations; skip ACTIONED and DECLINED
- Ask the user to confirm or adjust before proceeding

### 4. Import approved observations

For each observation to import:

a. Determine the next observation number in the global log:
   ```bash
   grep -oP '### Observation \K\d+' \
     /home/byron/.claude/skill-observations/log.md \
     | sort -n | tail -1
   ```

b. Append the observation to the global log with the new number.
   Preserve all fields exactly; add a note to the Session context field:
   `[imported from: /path/to/source/repo]`

c. Verify the number does not collide (post-write check per the
   task-observer collision protocol).

### 5. Archive or remove the stray log

After importing, ask the user whether to:
- Delete the stray log (it is now merged)
- Leave it in place (the repo's .gitignore may not cover it)

If the stray log lives inside a repo that does NOT have
`skill-observations/` in its `.gitignore`, offer to add the entry.

### 6. Confirm and summarise

Report:
- How many observations were imported
- Which were skipped (already present or not OPEN)
- Which stray logs were removed or left in place
- Whether any .gitignore files were updated
