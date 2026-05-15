# Aggregate Skill Observations

Scan all repositories under `~/dev/` for local `skill-observations/log.md`
files that have not been merged into the global observation log. This
catches cases where the task-observer wrote observations to a project-local
directory instead of the canonical global path.

## Steps

### 1. Identify stray observation logs

Search all repos for skill-observation logs:

```bash
find ~/dev -name "log.md" -path "*/skill-observations/*"
```

Any `log.md` found here is a stray: the canonical global log lives at
`~/.claude/skill-observations/log.md`, which is outside the `~/dev/`
search tree and therefore never appears in these results.

If no files are found, report: "No stray observation logs found. All
observations are already in the global log." Stop here.

### 2. For each stray log found

Read the file and extract all observations. For each observation, check
whether it already exists in the canonical log at
`~/.claude/skill-observations/log.md` by searching for a match on both
the observation **title** (the text after `### Observation N: `) and
**date** (the `Date:` field). Both must match to treat it as a duplicate;
a title-only match is not sufficient because two observations from
different repos or sessions can share a title but capture distinct events.

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

For **each** observation to import, independently:

a. Determine the next observation number by reading the current global log:
   ```bash
   grep -oP '### Observation \K\d+' \
     ~/.claude/skill-observations/log.md \
     | sort -n | tail -1
   ```
   Add 1 to this value. Re-run this command before each import, not once
   before the loop, so concurrent appends do not cause number collisions.

b. Append the observation to the global log with the new number.
   Preserve all fields exactly; add a note to the Session context field:
   `[imported from: /path/to/source/repo]`

c. Verify no collision occurred with a post-write check:
   ```bash
   grep -c "### Observation ${NEW_NUMBER}:" \
     ~/.claude/skill-observations/log.md
   ```
   The count must be exactly 1. If it is 0, the write did not land; if it
   is 2 or more, a concurrent write collided. In either case, stop
   immediately and alert the user before importing any further observations.

### 5. Verify import, then archive or remove the stray log

Before offering to delete the stray log, confirm each imported observation
is present in the canonical log by searching for its title and date.
Only offer deletion after this verification passes.

Then ask the user whether to:
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
