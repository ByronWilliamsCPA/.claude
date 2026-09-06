# Watch-and-Refix Loop (Step 9)

Full procedure for `workflows/pr-fix.md` Step 9, "Watch-and-refix loop".
Covers the three phases: A (wait for CI and reviewer stabilization), B
(assess results), and C (automatic re-fix pass, bounded at 2 cycles). The
`mergeStateStatus`/`mergeable` handling throughout this step follows the
settle-then-reject-only rule in
[context/github-api-idioms.md](github-api-idioms.md) ("`mergeStateStatus`
and `mergeable`: settle first, then reject only"); that shared entry also
documents why this file states the rule so emphatically. The workflow's own
version of the rule, including the Phase A/Phase B interaction, is kept
verbatim below.

After pushing (Options 1 or 2), enter a bounded watch loop that monitors CI
and review bots. This eliminates the manual "push, wait, come back, re-run"
cycle that dominated both PR #20 and dna#1.

## Phase A: Wait for CI + reviewer stabilization (up to 10 minutes)

Record `PUSH_SHA` (the HEAD SHA after this push) and anchor every check query to it.
Poll in parallel every 60 seconds:

1. **CI checks (anchored to PUSH_SHA, not `gh pr checks`).** After any push, status
   queries race against run registration: a zero-pending result immediately post-push is
   ambiguous between "all done" and "nothing started yet", and `gh pr checks` can report
   only stale old-run data before GitHub creates the new commit's check runs. Query the
   new SHA's check-runs directly:

   ```bash
   gh api repos/{OWNER}/{REPO}/commits/$PUSH_SHA/check-runs --paginate \
     --jq '[.[]? // empty] | length' >/dev/null  # see structured query below
   ACTIVE=$(gh api repos/{OWNER}/{REPO}/commits/$PUSH_SHA/check-runs --paginate \
     | jq -s '[.[].check_runs[] | select(.status != "completed")] | length')
   ACTIVE=${ACTIVE:-99}   # empty/failed poll = still active, never "done"
   ```

   A check is non-terminal when `status` is any of `queued`, `in_progress`, `waiting`,
   `pending`, `requested` (enumerate the non-terminal set explicitly; do NOT test for a
   single known pending value). Terminal = `status == "completed"` (with `conclusion` in
   `{success, skipped, neutral, cancelled, failure}`). Treat an empty or failed poll
   response as still-active, never as done.

   **Debounce the exit.** Do not exit on the first all-terminal poll. Require EITHER a
   minimum elapsed time of 2 minutes since the push, OR two consecutive all-terminal
   polls, before declaring CI settled.

2. **Review comments:** `gh api repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/comments --jq 'length'`
   - Track: comment count stabilizes (same count for 2 consecutive polls)
3. **PR state (when AUTO_MERGE=true):** `gh pr view --json state --jq '.state'`
   - If `state == "MERGED"`: stop immediately. The PR merged between cycles.
     Any staged fixes must go to a follow-up PR.

**Confirm each REQUIRED context actually re-ran on the new head SHA.** GitHub evaluates
required status contexts against the head SHA. A fix commit that touches only files outside
a required path-filtered workflow's trigger paths does NOT re-run that workflow; its required
context then has no status on the new head, reads as unsatisfied-on-head, and
`mergeStateStatus` stays or returns to BLOCKED even though every check that DID run is green.
After pushing a narrow fix, check `gh api repos/{OWNER}/{REPO}/commits/$PUSH_SHA/check-runs`
for each required context; if a required context is missing on the head, the PR is silently
blocked. Re-trigger it by ensuring the final push touches that workflow's trigger paths (for
example, bundle the fixes so the last commit also edits a path the required workflow watches,
such as a file under that workflow's `paths:` filter). This is the same phantom/never-reported required-check failure
mode pr-review documents, surfacing here via path-filtered re-triggers; a green prior run does
not carry forward to a new head.

**Do not block on `mergeStateStatus` for the all-green signal.** That field (and
`mergeable`) is computed asynchronously and can return `null` or lag by minutes even when
the underlying data is settled. The authoritative green signal is two direct-data checks:
(1) all `check-runs` for `PUSH_SHA` are `completed` with `conclusion` in
`{success, skipped, neutral}`, and (2) `mergeable_state == "clean"` from the pull
endpoint. If both hold, the branch is all-green regardless of `mergeStateStatus`; reserve
`mergeStateStatus` as a supplementary signal only.

Exit the wait when all conditions are met, or after 10 minutes (whichever
comes first).

## Phase B: Assess results

**Stale comment filter:** Before classifying new comments as work items, filter
out comments where `commit_id` predates the push SHA. For each comment, compare
`commit_id` to the HEAD SHA after this push. If older, verify the cited file
still contains the flagged pattern at the cited line:

```bash
gh api repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/comments \
  --jq '[.[] | select(.commit_id != "{PUSH_SHA}") | {id:.id, path:.path, line:.line, commit:.commit_id}]'
```

Mark comments with an older `commit_id` AND whose cited content is absent from
current HEAD as `STALE`. Include them in the Phase C summary as "Reply-only
({N} stale comments already addressed in {PUSH_SHA})" rather than as new
findings requiring a code-change cycle.

**Reusable-workflow startup_failure (no jobs, no logs).** A `completed/startup_failure`
conclusion (distinct from `completed/failure`) means no job ran, so logs and annotations
will be absent: diagnose at the file/reference level, not by reading logs that do not exist.
The common cause is a `uses: org/repo/...@<sha>` reusable ref pinned to a commit orphaned by
a squash-merge (`gh api repos/<owner>/<repo>/compare/<default>...<sha>` returns `diverged`).
Re-pin to a SHA reachable from the reusable repo's default branch; `contents?ref=<sha>`
still serves dangling commits, so use `compare`, not existence. Validate the fix cheaply via
`workflow_dispatch` on a throwaway branch (startup validation runs at load time, before job
`if:`). When the failure appeared right after an edit, confirm causation by reverting the
suspected change on the current base before committing to a fix direction.

**SARIF / code-scanning orphan checks, CodeQL only (legacy, pre-2026-09):** `codeql.yml` and
`dependency-review.yml` were deleted fleet-wide (2026-09; `actions/dependency-review-action` now
requires paid GitHub Advanced Security). A "CodeQL" or "Code scanning results / CodeQL" check
visible on a new PR is therefore a leftover from before the deletion, not a live analysis: treat
it as permanently orphaned (not merely path-filtered) and, if it recurs, have the repo owner
disable "Code scanning: Default setup" in repo Settings > Code security so GitHub stops
registering the check context. This does NOT apply to other SARIF-producing workflows: `sbom.yml`
still runs `github/codeql-action/upload-sarif` for its Grype and OSV-Scanner jobs (categories
`grype-runtime-deps`, `osv-sbom-runtime-deps`), so those checks are live, not orphaned. The
pre-2026-09 mechanics below (queued indefinitely because the upstream analysis job was
path-filtered or skipped on config-only/docs-only PRs) still apply to those and to any other
SARIF-producing workflow, such as a Trivy or Snyk scan that guards a path filter.

```bash
gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" --json mergeable,mergeStateStatus \
  --jq '{mergeable:.mergeable, state:.mergeStateStatus}'
```

If `mergeable: MERGEABLE` (button is active), a queued (not orphaned-CodeQL) SARIF check is a
non-blocking advisory check, not a CI failure. Classify it as "advisory pending (path-filtered
upstream job)" and do NOT trigger a re-fix cycle. The PR is safe to merge.

Classify the outcome:

| CI status | New (non-stale) comments | Action |
| --- | --- | --- |
| All green | None | Report success, clean up worktree, done |
| All green | New comments arrived | Enter Phase C (re-fix pass) |
| Failures | Any | Enter Phase C (re-fix pass) |
| SARIF checks queued + `mergeable: MERGEABLE` | Any | Classify as advisory pending; proceed to merge or Phase C for comments only |
| Hard-FAILED check NOT in required contexts + `mergeStateStatus: UNSTABLE` + `mergeable: MERGEABLE` | Any | Advisory; do NOT enter Phase C for it (see below). Phase C still applies to any genuinely required failure or new comment |
| All green + `mergeStateStatus: BLOCKED` | None | Unresolved-conversation block (see below); resolve threads, NOT a re-fix cycle |
| Timed out | Any | Report current state, offer manual options |

**A hard-FAILED check is not automatically a merge blocker.** A check sitting in a
terminal `failure`/`error` state is advisory, not blocking, when it is (a) absent from the
branch's required-status-check contexts AND (b) on a PR whose `mergeStateStatus` is
`UNSTABLE` (not `BLOCKED`) and `mergeable` is `MERGEABLE`. `UNSTABLE` plus `MERGEABLE`
means the failing check is non-required regardless of its red state, and no PR-side code
change can clear it. Before treating any single FAILURE as a blocker that warrants a
Phase C re-fix cycle, run `gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" --json
mergeable,mergeStateStatus` and a required-contexts lookup; classify by the merge-
eligibility API and the required-context list, not by the check's terminal color alone.
The worked example (pre-2026-09, when CodeQL default setup was still free) was a CodeQL
default-setup job ("Analyze (javascript-typescript)") failing "no source code seen during
build" on a repo with zero JS/TS source: it was enabled org-wide by the recommended
code-security config, was non-required, and merged straight through. CodeQL now requires
paid GitHub Advanced Security and no longer runs fleet-wide, so this specific check should
not reappear; the underlying advisory logic (non-required + `UNSTABLE` + `MERGEABLE` merges
through regardless of terminal color) still applies to any other non-required check.

**Green-but-BLOCKED: distinguish the cause before acting.** "All checks green" is
necessary but not sufficient for mergeability. Use `mergeStateStatus` here only in
the negative direction, consistent with Phase A above: a settled `BLOCKED` is
grounds to stop and diagnose, but it is never the signal that confirms the branch
is ready. Phase A's rule stands, this does not override it. BLOCKED has multiple
independent causes that each need a different, non-code action. When CI is all
green AND there are no new non-stale comments AND `mergeStateStatus` is BLOCKED:

- **Unresolved review threads** (branch protection enforces conversation resolution):
  check `reviewThreads.nodes` for `isResolved == false` whose findings are already
  addressed, and resolve them via the `resolveReviewThread` GraphQL mutation (already
  implied by Step 8). This clears BLOCKED -> CLEAN without any code change.
- **Phantom or name-mismatched required checks** (a required context that is never
  reported sits pending forever): clears by fixing branch protection / the workflow job
  name, not by resolving threads.

Neither cause is a re-fix cycle. Identify which one applies before acting.

## Phase C: Automatic re-fix pass (up to 2 cycles)

**Completion conditions (exit the loop immediately when any are met):**

- Phase A returns all-green with no new non-stale comments: report success, clean up worktree, done.
- User declines a re-fix pass: report remaining items, keep worktree, done.
- User selects "stop" in the delta prompt: same as decline above.
- Cycle count reaches 2 and issues remain: run stuck-loop diagnosis, present final options, done.

If Phase B indicates issues:

1. Gather the new failures and comments (same as Step 1 sources)
2. Present a delta summary (format below)
3. If the user confirms: apply fixes (same rules as Step 4), verify (Step 5),
   commit (Step 6), push, and re-enter Phase A
4. If the user declines or selects "stop": report remaining items and offer to keep the worktree; exit the loop

**Step 5a precondition behavior in re-fix cycles.** If Step 5a's "Default
gate unavailable" precondition fired in a prior cycle and the user picked
Option 1 ("Skip Step 5a entirely and document the gap"), the same condition
will fire again here. Do NOT silently skip on subsequent cycles. Re-prompt
the user every cycle. Each "skip" decision must be recorded in the commit
message of the cycle that produced it (e.g., `[default-gate skipped: pyproject.toml missing]`)
so the audit trail shows which cycles ran without static analysis. If the
user picked Option 2 ("Abort /pr-fix") in the original cycle, the workflow
already exited; this branch does not apply.

Delta summary format:

```text
Post-push findings (cycle {N}/2):
  CI failures:     {list}
  New comments:    {N} ({authors})
  Stale comments:  {N} (reply-only, already addressed in {PUSH_SHA})

Auto-fix these? (yes / review details / stop)
```

**Cycle limit:** Maximum 2 automatic re-fix cycles. After 2 cycles, if issues
remain, run a stuck-loop diagnosis before stopping:

```text
Skill("panel")(
  mode:           "tiered-review",
  level:          PANEL_TIERED_LEVEL,
  domain:         "code_review",
  prompt: "A PR fix workflow has completed 2 automatic re-fix cycles but CI
           failures or review comments still remain unresolved. Diagnose why
           the fix attempts are not clearing and suggest a resolution path.

           Remaining failures after 2 cycles:
           {list of remaining CI failures with error output}

           Fixes attempted in each cycle:
           Cycle 1: {summary of fixes applied}
           Cycle 2: {summary of fixes applied}

           Questions:
           1. Are the remaining failures fixable by further automated attempts,
              or do they require human judgment?
           2. Is there a root cause being missed that is causing the same
              symptoms to recur?
           3. What is the most likely path to resolution?

           Return only a JSON object with this shape (no surrounding prose):

             {
               \"can_retry\": <bool>,
               \"root_cause\": \"<one paragraph>\",
               \"blocker\": \"<specific reason automation cannot resolve this; required when can_retry is false>\",
               \"proposed_fix\": \"<specific targeted fix to attempt; required when can_retry is true>\"
             }"
)
```

Use the `can_retry` field to drive the exit presentation:

- If `can_retry: true`: present `proposed_fix` as Option 1 for a targeted third attempt
- If `can_retry: false`: surface `blocker` as the reason automation is exhausted

Include the panel diagnosis in the report presented to the user, then stop:

```text
Completed 2 re-fix cycles. Remaining issues:
  {list with reasons}

Panel diagnosis:
  Root cause:    {root_cause from the panel tiered review}
  Can retry:     {yes, proposed fix: {proposed_fix} | no, blocker: {blocker}}

Options:
1. {If can_retry: "Apply targeted fix: {proposed_fix}" / If not: "Keep worktree for manual work"}
2. Push current state and stop
3. Discard all changes
```

**Worktree cleanup:** Clean up the worktree only after the loop completes
with all-green status, or when the user explicitly chooses to discard.

```bash
git worktree remove {WORKTREE_PATH}
```

`git worktree remove` deletes the worktree directory before returning, which collapses the
shell's CWD if the shell is currently inside that worktree. In that case the command emits
`pwd: error retrieving current directory: getcwd: ...` and exits 1 even on success; a retry
then prints `fatal: '<path>' is not a working tree` (it was already removed), which looks
like a second error. Exit code 1 here does NOT mean failure: verify cleanup via
`git worktree list`, not the remove command's exit code. Safer still, `cd` to the repo root
before running `git worktree remove`.
