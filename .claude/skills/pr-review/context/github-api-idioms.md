# GitHub API idioms shared by pr-review and pr-fix

Reference material for `workflows/pr-review.md` and `workflows/pr-fix.md`. Each
entry records an API behaviour that has produced a real defect in one or both
workflows. Read the relevant entry before writing any code that touches the
field it describes.

These are not style preferences. Every rule below is here because the obvious
implementation was written, shipped, and silently did the wrong thing.

---

## Reviewer bot identity: Copilot has two logins, not one

**The rule:** match reviewer logins case-insensitively on substring. Never use
exact equality.

Copilot posts under two different `user.login` values depending on what it
posted:

| What Copilot posted | `user.login` |
| --- | --- |
| A review submission (`/pulls/{n}/reviews`) | `copilot-pull-request-reviewer[bot]` |
| An inline comment on that review (`/pulls/{n}/comments`) | `Copilot` |

CodeRabbit is more consistent but still carries the suffix: `coderabbitai[bot]`.
The literal `[bot]` suffix is part of the login string for GitHub App accounts,
so `login == "coderabbitai"` matches nothing.

**Working filter:**

```bash
gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews" --paginate \
  --jq '[.[] | select(.user.login | test("^(Copilot|copilot-pull-request-reviewer(\\[bot\\])?|coderabbitai(\\[bot\\])?)$")) | .user.login] | unique'
```

**Two defects this caused, with different symptoms:**

1. In a *polling loop* the failure was loud in wall-clock terms. The reviewer
   wait compared against bare `copilot-pull-request-reviewer`, so its done-count
   was permanently zero and every run burned the full timeout before giving up.
2. In a *classifier* the failure was completely silent. Author classification
   ends in a catch-all (`All others --> Human`), so unmatched Copilot inline
   comments were relabelled as human change requests and triaged at the wrong
   priority, with no error anywhere.

The second case is the reason the patterns must be deliberately permissive: when
a classifier ends in a catch-all, a matching gap does not raise, it mislabels.

**Related trap:** a `coderabbitai` *status check* reports SUCCESS even when the
bot was rate-limited and produced no review at all. A green check is not
evidence a review happened. Count actual review submissions instead.

---

## `mergeStateStatus` and `mergeable`: settle first, then reject only

**The rule:** poll until the field is settled, then use it to reject, never to
confirm.

Both fields are computed asynchronously by GitHub. On a freshly opened or
freshly pushed PR they commonly read `null` or `UNKNOWN` for several seconds.
This produces two opposite errors, and a workflow can contain both at once:

- **Reading too early and passing.** If the only abort conditions are "PR is
  closed" and "metadata fetch fails", an unsettled read falls straight through
  to a silent proceed. An unsettled value means *retry*; it never means *passed*.
- **Trusting it as the ready signal.** Because the field lags, it is not
  evidence the branch is mergeable. Use it in the negative direction only: a
  settled `DIRTY`, `BEHIND`, or `CONFLICTING` is grounds to stop and surface,
  but a settled anything is never the signal that confirms readiness. Confirm
  readiness from the check runs themselves.

**Settling poll:**

```bash
for i in $(seq 1 10); do
  MS=$(gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" --json mergeStateStatus \
    --jq '.mergeStateStatus // "UNKNOWN"')
  [ "$MS" != "UNKNOWN" ] && [ -n "$MS" ] && break
  sleep 3
done
```

If the loop exits still unsettled, stop and surface it. Do not fall through.

**Why this is stated so emphatically:** `pr-fix.md` once held three incompatible
postures on this single field at the same time. Step 0 treated it as a hard
entry gate, Step 9 Phase A demoted it to "a supplementary signal only", and
Phase B, seventy-five lines later, promoted it back to "the authoritative gate".
Anyone copying a passage out of that file inherited whichever of the three they
happened to read first. One field, one posture: the one at the top of this
section.

---

## Renamed files: REST only, GraphQL cannot answer this

**The rule:** detect renames with the REST files endpoint. The GraphQL
`previousFilename` field no longer exists.

```bash
gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/files" --paginate \
  --jq '.[] | select(.previous_filename) | {from: .previous_filename, to: .filename}'
```

The GraphQL field `previousFilename` was removed from the schema. A query still
containing it fails outright rather than returning empty, so this is a loud
failure, but the fix is a different endpoint rather than a different field name.

Renames matter to both workflows: a review that treats a rename as
delete-plus-add reports the entire file as new, and a fix run that does the same
will rewrite a file that only moved.

---

## Scanner exit codes: a verdict, not a diagnosis

**The rule:** when a scanner ran with a file-output flag, read the artifact, not
the log.

Tools invoked as `osv-scanner --output=report.json`, `trivy --output`, or
`bandit -o report.json` write their findings to a file and print only a summary
plus an exit code to stdout. Grepping the job log therefore surfaces only
whichever noise *is* printed, typically filtered or disputed advisories and a
bare `Exit code: 1`, which actively misleads diagnosis toward the wrong cause.

When the failing step is a scanner:

1. Look for `--output`, `-o`, or `--format json` in the step's arguments. If
   present, download the report artifact (`gh run download -n <artifact>`) and
   parse it.
2. If the artifact is absent, which happens when the upload step was skipped
   because the scan aborted the job first, reproduce the scan locally against
   the worktree lockfiles with the same config and read the result there.

Treat `Exit code: 1` with no visible finding in the log as a signal to go to the
artifact, never as the finding itself.

---

## An unreachable MCP server is not an empty result set

**The rule:** record transport failure as `unavailable`, distinctly from "zero
findings".

The SonarQube MCP servers are Docker-backed and routinely unreachable. So are
other MCP-backed quality gates. Collapsing a connection failure into an empty
finding list makes a run report a clean quality gate it never actually queried,
which is the most dangerous possible outcome: a false all-clear.

This is the same failure shape as the catch-all classifier above. When the
absence of a signal and the absence of a *channel* for that signal are
represented identically, the system cannot tell "nothing is wrong" from "I did
not look."
