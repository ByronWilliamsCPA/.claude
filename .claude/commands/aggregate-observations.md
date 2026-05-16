# Aggregate Skill Observations

Scan all repositories under `~/dev/` for local `skill-observations/log.md`
files that have not been merged into the global observation log. This
catches cases where the task-observer wrote observations to a project-local
directory instead of the canonical global path.

## Steps

### 1. Identify stray observation logs

Search all repos for skill-observation logs:

```bash
find -L ~/dev -maxdepth 6 -name "log.md" -path "*/skill-observations/*"
```

`-L` follows symlinks so any `skill-observations/` directory symlinked
into a repo is also scanned. `-maxdepth 6` prevents runaway traversal
in a large dev tree. Users whose repositories live outside `~/dev/`
should substitute their own dev root.

Any `log.md` found here is likely a stray. Filter out the canonical
global log path (`~/.claude/skill-observations/log.md`) if it appears
in the results, which is possible when this repo itself is cloned
under `~/dev/`.

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
   before the loop, to prevent number collisions with a live task-observer
   running in another session. (Requires PCRE-capable grep, i.e. GNU
   `grep -P` on Linux/WSL.)

b. Append the observation to the global log with the new number.
   Preserve all fields exactly; add a note to the Session context field:
   `[imported from: <source repo path>]`. If the source observation lacks
   a `Session context:` field (older skill versions omitted it), append
   the field as a new line after the last existing field and before the
   observation body.

c. Verify no collision occurred by searching the global log for the
   heading you just wrote (`### Observation <N>:` where `<N>` is the
   number assigned in step a):
   ```bash
   # Replace <N> with the actual observation number before running
   grep -c "### Observation <N>:" ~/.claude/skill-observations/log.md
   ```
   The count must be exactly 1. If it is 0, the write did not land; if it
   is 2 or more, a concurrent write collided. In either case, stop
   immediately and alert the user before importing any further observations.
   The collision logic assumes the numbering in the global log is strictly
   monotonic; manually inserted out-of-order numbers will not collide but
   may break the sequence assumption downstream.

### 5. Verify import, then archive or remove the stray log

Before offering to delete the stray log, confirm each imported observation
is present in the canonical log by searching for its title and date.
Only offer deletion after this verification passes.

Then ask the user whether to:
- Delete the stray log (it is now merged)
- Leave it in place (the repo's .gitignore may not cover it)

If the stray log lives inside a repo that does NOT have
`skill-observations/` in its `.gitignore`, offer to add the entry.

### 6. Confirm and summarize

Report:
- How many observations were imported
- Which were skipped (already present or not OPEN)
- Which stray logs were removed or left in place
- Whether any .gitignore files were updated
