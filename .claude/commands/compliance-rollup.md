# Compliance Rollup

Reconcile per-repo compliance retrospectives into the central master log.
Walks every repo in `~/.claude/docs/reference/github-repos.json`, parses
`docs/compliance-reports/lessons-learned/*.md` files by fixed headings,
and appends any (session_date, repo) pair not already in
`~/.claude/docs/compliance-reports/master-log.jsonl`. New entries are
marked `reconciled=true`. The master-log.md view is regenerated when any
new entry is appended.

This is the reconcile-side actor for the compliance aggregation system.
The write-side (compliance-retrospective agent) pushes at audit time;
this command catches anything written out-of-band or before the push
hook was wired in.

## Arguments

- `--dry-run` -- walk and report what would be appended, without
  modifying the master log.
- `--since YYYY-MM-DD` -- only consider per-repo files dated on or after
  this ISO date. Useful when onboarding new repos or after a long
  absence.

## Steps

### 1. Run the reconciler

```bash
PYTHONPATH=$HOME/.claude python3 \
  $HOME/.claude/scripts/compliance_rollup_reconcile.py "$@"
```

The script prints a one-line summary to stdout and appends it to
`docs/compliance-reports/state/reconcile-log.txt`. Parse failures are
reported per-file with the path; investigate each one (usually a
heading rename in the source agent template).

### 2. Inspect what changed

```bash
git status docs/compliance-reports/master-log.jsonl \
           docs/compliance-reports/master-log.md
git diff docs/compliance-reports/master-log.md | head -100
```

The JSONL grows by one line per appended entry. The Markdown view
regenerates whole.

### 3. Commit the result (if not a dry run)

```bash
git add docs/compliance-reports/master-log.jsonl \
        docs/compliance-reports/master-log.md
git commit -m "chore(compliance): reconcile per-repo retrospectives

Backfilled N entries from per-repo lessons-learned files into the
central master log. See state/reconcile-log.txt for the sweep summary."
```

## Hard rules

- Never modify per-repo files. The reconciler is read-only on every
  `<repo>/docs/compliance-reports/lessons-learned/` file it visits.
- Never silently drop parse failures. They are written to
  `reconcile-log.txt` with the path so they can be fixed at source.
- Repos in the catalog without a local clone are skipped, not flagged.
