# Scheduled Mode Workflow

Report-only org-wide sweep. No approval loop and no remediation.

## Steps

### 1. Discover Repos

```bash
# Local repos
find ~/dev -maxdepth 2 -name ".git" -type d \
  | grep -v "/.worktrees/" \
  | xargs -I{} dirname {} \
  | sort > /tmp/local-repos.txt

# Remote repos -- williaby org
gh repo list williaby --limit 100 --json nameWithOwner,sshUrl \
  | jq -r '.[].sshUrl' > /tmp/remote-repos.txt

# Remote repos -- ByronWilliamsCPA org
gh repo list ByronWilliamsCPA --limit 100 --json nameWithOwner,sshUrl \
  | jq -r '.[].sshUrl' >> /tmp/remote-repos.txt

sort -u /tmp/local-repos.txt /tmp/remote-repos.txt > /tmp/all-repos.txt
```

Read `~/.claude/docs/compliance-exclusions.yaml`. For each exclusion entry, remove matching repos from the list. Match against the GitHub repository name (the basename of the SSH URL or the local directory name). The sweep normalizes both sources to the GitHub repo slug before applying exclusions.

Read `~/.claude/docs/reference/github-repos.json` if it exists. For each repo in the sweep list, look up its slug in the catalog's `repos[]` array. If found, extract the `review` object to pre-populate domain agent prompts with cached data. Note the `_meta.lastUpdated` date at the top of the sweep report; flag cached data older than 30 days as potentially stale.

### 2. For Each Repo

For local repos: use the path directly.
For remote-only repos: clone to a temp directory under `/tmp/compliance-<date>/`.

Run steps 2-4 from interactive-mode.md (parallel audit dispatch, merge findings, sort by severity). Skip the approval loop, remediation dispatch, and PR creation.

Write one report file per repo using the template at `templates/compliance-report.md`.
Path: `~/.claude/docs/compliance-reports/<YYYY-MM-DD>-<repo-slug>.md`

### 3. Retrospective

After all repos are processed, dispatch `compliance-retrospective` with all findings from the full session.

Output path: `~/.claude/docs/compliance-reports/lessons-learned/<YYYY-MM-DD>.md`

Print: "Scheduled run complete. Reports written to ~/.claude/docs/compliance-reports/. Review lessons-learned/<date>.md before next run."

### 4. Cleanup

```bash
rm -rf /tmp/compliance-<date>/
rm -f /tmp/local-repos.txt /tmp/remote-repos.txt /tmp/all-repos.txt
```
