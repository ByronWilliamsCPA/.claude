---
name: pre-commit-authoring
description: >
  Pre-commit hook authoring and audit reference. Use when adding a new
  pre-commit hook, auditing an existing `.pre-commit-config.yaml`, or
  diagnosing hook misbehavior (false positives, slow commits, hooks that
  block on unrelated files). Captures the staged-scope invariant, fast/slow
  tier placement, fail-vs-warn semantics, and a common-gotchas list.
  Auto-activates on: add a hook, write a pre-commit hook, audit pre-commit,
  fix pre-commit hook, why is this hook slow, hook false positive,
  /pre-commit-authoring.
user-invocable: true
---

# Pre-Commit Hook Authoring

Reference for designing, adding, and auditing entries in
`.pre-commit-config.yaml`. Internal skill: assumes the user's existing
toolchain (ruff, basedpyright, yamllint, markdownlint, TruffleHog,
detect-secrets, interrogate, darglint, qlty, pip-audit). The principles
generalize; the specific hook examples reference this fleet's standards.

## Authoring decision tree

Before adding any hook, answer in order:

1. **Does the check belong at commit time at all?** Pre-commit hooks fire on
   every commit and add latency to every developer's flow. If the check is
   slow (more than ~10 seconds on a typical change, matching the
   file-scoped-linter tier budget below), runs against state the developer
   cannot see (full git history, remote artifacts, network resources), or
   only matters at PR/release time, put it in CI instead.
2. **Pre-commit or pre-push?** Use `pre-commit` for fast checks against the
   diff. Use `pre-push` for slower checks that must run before the change
   leaves the developer's machine but can amortise across many commits
   (e.g., `pip-audit`, full-test sweeps, full-history secret scans). Set
   `stages: [pre-commit]` or `stages: [pre-push]` explicitly; do not rely
   on the default.
3. **Does the hook scope to staged files only?** See PC-HOOK-STAGED-SCOPE
   invariant below. Hooks that traverse the local git object store will
   surface findings from unmerged remote branches.

## Scope invariant (most-violated rule)

**Pre-commit hooks must scope to staged files only.** Full-git-history
modes belong in CI, not pre-commit.

The local git object store almost always contains commits from fetched
remote branches that are not reachable from `HEAD` (e.g.,
`origin/feature-x`, abandoned `claude/...` branches, dependabot PRs).
Hooks that scan the full history will surface placeholder credentials,
test fixtures, and known-fake examples from those branches on every
unrelated commit, blocking work indefinitely.

| Tool | Wrong (full history) | Right (staged) |
|---|---|---|
| TruffleHog | `trufflehog git file://. --since-commit HEAD` | `git diff --cached -z --diff-filter=d --name-only \| xargs -0 -r trufflehog filesystem` |
| gitleaks | `gitleaks detect --log-opts="--all"` | `gitleaks git --staged` (gitleaks v8.19+; older versions use `gitleaks protect --staged`) |
| detect-secrets | `detect-secrets scan --baseline .secrets.baseline` (regenerates from full repo) | `git diff --cached -z --diff-filter=d --name-only \| xargs -0 -r detect-secrets-hook --baseline .secrets.baseline` |

The `-z` / `-0` pair handles filenames with spaces; `--diff-filter=d`
excludes deleted files. `xargs -r` prevents the tool from running on an
empty input when no files match.

If full-history scanning is genuinely desired (a periodic audit, a
release-time gate), move the check to a CI workflow where the runner
clones with controlled remote refs.

## Performance tier placement

Group hooks into tiers so commits stay fast:

- **Fast file checks (every commit, target <2s):** trailing whitespace,
  end-of-file fixer, check-yaml, check-json, mixed-line-ending,
  check-added-large-files. These pre-existing pre-commit-hooks repo
  utilities are cheap and catch high-frequency mistakes early.
- **File-scoped linters (every commit, target <10s):** ruff, basedpyright
  (strict), yamllint, markdownlint, detect-private-key, no-em-dash. Scope
  to staged files only.
- **Slower checks (pre-commit if budget allows, else pre-push):**
  TruffleHog (staged form), interrogate, darglint, bandit on changed
  files, qlty check.
- **Pre-push only (full sweeps):** `pip-audit` on dependency files,
  `pre-commit run --all-files`, `pytest -x`, full-history secret scans
  if any.

Set `stages: [pre-commit]` or `stages: [pre-push]` explicitly on every
hook to control when it runs. Use
`default_install_hook_types: [pre-commit, pre-push]` separately so
`pre-commit install` registers both git-hook scripts in `.git/hooks`;
the `stages:` value on each hook still selects the actual stage.

## Fail-vs-warn semantics

- **Fail (exit non-zero, blocks commit):** correctness checks (lint,
  type, secrets, syntax). Fix the underlying issue before committing;
  `--no-verify` is only permitted when the user has explicitly requested
  it for a specific commit.
- **Warn (exit zero, prints output):** informational checks (TODO
  inventory, complexity reports, coverage trends). Most check tools
  default to fail; use `verbose: true` in the hook config to surface
  output without blocking.

Never set a correctness check to warn-only "to unblock the team": the
absence of a fail is the absence of the check.

## Hook config invariants in this project

The `.claude/rules/pre-commit.md` file (path-scoped) hosts the project's
codified invariants. Cross-reference when adding a new hook:

- **PC-YAMLLINT-FILE-REF:** yamllint must use `--config-file .yamllint`,
  not inline `-d "{rules: ...}"`.
- **PC-MARKDOWNLINT-MD040:** markdownlint must run with a config that
  enables MD040 (fenced-code-blocks-language).
- **PC-HOOK-STAGED-SCOPE:** every secret-scanning, lint, or content-check
  hook must scope to staged files only.

Add a new `PC-*` invariant whenever a hook authoring decision must be
preserved across the fleet (e.g., a specific arg flag, a config-file
location, a stage assignment that prevents a known failure mode).

## Authoring checklist

Before merging a PR that adds or modifies a hook:

- [ ] Hook is pinned to a SHA in the `rev:` field, not a mutable tag
- [ ] `stages:` is explicit (`[pre-commit]` or `[pre-push]`)
- [ ] Scope is staged files (no full-history flags)
- [ ] Config is in a file (`--config <path>`) not inline (`-d "..."`)
- [ ] Hook entry tested via `pre-commit run <hook-id> --all-files` and
      `pre-commit run <hook-id>` against a small staged change
- [ ] Failure output is actionable (the developer can tell what to fix)
- [ ] If new failure modes are introduced, an invariant is documented in
      `.claude/rules/pre-commit.md`

## Audit pattern

For an existing `.pre-commit-config.yaml`:

```bash
# 1. Find unpinned hooks (mutable refs)
grep -n 'rev: v\|rev: main\|rev: master' .pre-commit-config.yaml

# 2. Find hooks that scan full history
grep -nE '(--since-commit|--all|--log-opts|git file://)' .pre-commit-config.yaml

# 3. Find hooks without explicit stages
awk '/^  - id:/{name=$3; have_stage=0} /stages:/{have_stage=1} /^  - id:/{if(name && !have_stage) print prev_name" missing stages"} {prev_name=name}' .pre-commit-config.yaml

# 4. Find inline configs that should be file-ref
grep -nE 'args:.*-d ' .pre-commit-config.yaml
```

Patch any findings against the invariants above before committing the audit fix.

## Common gotchas

- **TruffleHog `git file://. --since-commit HEAD`** scans every commit not
  reachable from HEAD, including fetched remote branches. Always use the
  staged-file form.
- **detect-secrets baseline regenerated from full repo** can include
  secrets from old branches. Regenerate against staged files or a clean
  clone in CI.
- **`pip-audit` at pre-commit** is too slow for every commit. Move to
  pre-push or limit to dependency-file changes via `files:` filter.
- **`pre-commit run --all-files` inside a hook entry** creates infinite
  recursion. Use `pre-commit run` against staged paths only.
- **Hook order matters when one fixes and another checks the result.**
  Ruff format must run before ruff check; whitespace fixers must run
  before linters that fail on trailing whitespace.

## Sources

- pre-commit framework: <https://pre-commit.com/>
- TruffleHog pre-commit guidance: <https://docs.trufflesecurity.com/pre-commit-hooks>
- Cross-cutting principle 2 in `~/.claude/skill-observations/cross-cutting-principles.md`
  (procedural git rules, including the no-bypass-on-`--no-verify` rule)
