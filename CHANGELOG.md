# CHANGELOG


## [Unreleased]

### Bug Fixes

- **hooks**: Normalize `refs/heads/` and `refs/` prefixes in force-push guard so
  fully-qualified refspecs (e.g. `refs/heads/main`) are blocked the same as bare
  branch names (PR #20)

- **quality-gate**: Harden `check_quality_gate.py` against API error envelopes:
  use `.get()` on all bare dict key accesses in `format_report`, `_format_sonar_layer`,
  and `main`; treat `status=NONE` as a blocking condition so a missing quality gate
  cannot silently pass as READY TO MERGE

- **writing**: Remove em-dashes from SonarQube false-positive suppression comments in
  `check_type_hints.py` and `validate_front_matter.py`; add SonarQube issue IDs to
  each S2083 suppression comment; fix `validate_front_matter.py` to use `changed |=`
  pattern (not bitwise OR on bools) and wrap `_fix_tags`/`_fix_purpose` in
  try/except with stderr logging; correct inaccurate comment wording in `bash-notify.sh`


## v0.6.1 (2026-04-12)

### Bug Fixes

- **pr-fix**: Expand sonar rule table, shell bug categories, and doc accuracy patterns
  ([`609311a`](https://github.com/ByronWilliamsCPA/.claude/commit/609311a20a0379051862ac8d5347d70dd47bb0cd))

Adds 12 new SonarQube rules to the Priority 2 table (shelldre:S7688, S1066, S131, S7677, S1481,
  S7679; python:S5914, S1244, S1066, S1192; githubactions:S8234, S8233), four new shell bug
  categories to Priority 3 (jq presence guard, hook message direction, grep -nP portability,
  PowerShell escaping), a Documentation accuracy sub-category table with seven doc drift patterns,
  and two new Always-skip entries (pythonsecurity:S2083, force-push guard bypass).

Note: TruffleHog skipped (SKIP=trufflehog) due to known incompatibility with git worktrees (.git is
  a file pointer, not a directory).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **review**: Address Copilot and agent findings on PR #17
  ([`8e31667`](https://github.com/ByronWilliamsCPA/.claude/commit/8e31667ddc26c8acd5099df70b819e408df7c77a))

- Scope shelldre:S7688 fix to bash shebang only; skip POSIX sh scripts - Add errexit caveat to
  shelldre:S1066 nested-if merge guidance - Fix python:S5914: assertIsNotNone is not the generic
  replacement for constant boolean assertions; clarify correct fix approach - Tighten
  githubactions:S8234: specify reading job steps to identify required permissions rather than vague
  "what the workflow needs" - Resolve stdout/stderr contradiction between jq guard and hook block
  message rows; add context distinguishing hook vs general shell scripts - Fix spec frontmatter
  sub-category: frontmatter status is schema-validated; body blockquote follows frontmatter, not the
  reverse - Replace undefined "Cowork doc" with "Collaboration document (e.g., COWORK.md)" for
  clarity

Reconcile uv.lock version to match pyproject.toml 0.6.0 from main.

TruffleHog skipped: git worktree incompatibility (index file is not a directory); TruffleHog will
  run normally against the full repo on push.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.6.0 (2026-04-12)

### Bug Fixes

- **review**: Address pr-review agent findings on PR #16
  ([`2746c50`](https://github.com/ByronWilliamsCPA/.claude/commit/2746c50f0d4af0033e8ba094d6bc4497e62d736a))

Formatting fixes (markdownlint): - Add language specifiers to bare code fences (MD040) - Space all
  table separator rows: |---|---| -> | --- | --- | (MD060) - Add blank lines around all lists and
  list-adjacent blocks (MD032) - Change all heading separators from ' -- ' to ': '

Content corrections: - Fix SonarQube rule key: shelldre:S7682 -> shell:S7682 - Move cognitive
  complexity (python:S3776) from deterministic-fixes table to manual-fix table (requires design
  judgment, not mechanical) - Clarify GitHub MCP method names in Steps 1b and 7; note that
  resolve_review_thread and subscribe_pr_activity are unconfirmed method names and replace with gh
  CLI polling workaround - Fix Step 3 error message: 'ensure git fetch origin ran' -> 'check that
  the branch exists on origin' - Escape MD056-triggering pipe literal in table cell

Note: TruffleHog skipped (SKIP=trufflehog) due to known incompatibility with git worktrees (.git is
  a file pointer, not a directory).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- **deps**: Reconcile uv.lock version with pyproject.toml 0.5.0
  ([`b2250a4`](https://github.com/ByronWilliamsCPA/.claude/commit/b2250a4b1784bd44f6a0c8db6181463afc2b1de5))

uv sync updated the lock file version from 0.4.0 to 0.5.0 to match the current pyproject.toml
  version after the v0.5.0 release.

https://claude.ai/code/session_016cTxGxECo4rzsVNFPR7Wxa

### Features

- **skills**: Rewrite pr-fix as standalone multi-source PR remediation workflow
  ([`7845e2e`](https://github.com/ByronWilliamsCPA/.claude/commit/7845e2e04693a6264aee9e1cf67bd0691c904167))

Rewrite /pr-fix from a downstream-only sub-step of /pr-review into a standalone skill that
  independently gathers all open issues on a PR:

- CI check failures (test, lint, format, type-check, security, changelog, compatibility, docs build,
  license, dead code) - Review comments from all sources (Copilot, CodeRabbit, human reviewers) with
  author classification and actionability filtering - SonarQube findings (missing returns, redundant
  exceptions, cognitive complexity, ReDoS patterns, security hotspots) - Codecov coverage gaps (if
  configured) - pr-review agent findings (when called from the review workflow)

The workflow fixes issues in priority order inside an isolated worktree, verifies via ci-fix gate
  sequence, commits in logical batches, and offers to push, reply to review comments, resolve
  threads, and post a summary.

Also updates: - SKILL.md: add pr-fix trigger keywords and routing table - pr-review.md: Step 9/10
  now references the full pr-fix workflow - git-workflow.md: add /pr-fix to Layer 2 gate
  documentation

https://claude.ai/code/session_016cTxGxECo4rzsVNFPR7Wxa


## v0.5.0 (2026-04-12)

### Bug Fixes

- **docs**: Correct relative link to ADR-004 in supervisor.md
  ([`3a67295`](https://github.com/ByronWilliamsCPA/.claude/commit/3a672951ceb8f22eac7ec3c1a9e2edb3bec6c222))

Link was ../docs/architecture/... which resolves to .claude/docs/ (does not exist). Correct path
  from .claude/rules/ to repo-root docs/ is ../../docs/architecture/...

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **hooks**: Read tool input from stdin in rad-strict-hook.sh
  ([`a9c9f68`](https://github.com/ByronWilliamsCPA/.claude/commit/a9c9f68c61ee4f088b4d5417c06afc927c3bf45d))

CLAUDE_TOOL_INPUT env var does not exist. Claude Code hooks receive tool input via stdin as JSON.
  Read with cat and parse with jq to get the command field, matching the pattern used by other hooks
  in this repo.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **review**: Address Copilot code review findings on PR #15
  ([`74487af`](https://github.com/ByronWilliamsCPA/.claude/commit/74487af01d28e73fcf07d74486339b986e60eb8a))

Critical fixes: - settings-and-permissions.md: correct scope hierarchy order (managed policy is
  highest/5, ~/.claude/settings.json is lowest/1; previously inverted) - stop-pre-commit-hook.sh:
  remove set -e to prevent abort before timing code runs; capture pre-commit exit with || RC=$?
  pattern - rad-strict-hook.sh: use exit 2 (block tool call) not exit 1 (hook error); add set -euo
  pipefail and activation log line; add registration comment - CLAUDE.md: add references for
  settings-and-permissions.md and loop-recipes.md so rule files inject into sessions (orphaned rules
  fix)

Important fixes: - .claude/settings.json: tighten FileChanged matcher from \\.env to
  (^|/)\\.env[^/]*$ to avoid false positives on .environment.py etc. - settings.json: fix
  Bash(gcloud:*) format (was Bash(gcloud *:*) with literal asterisk); remove redundant Bash(rm
  -rf:*) covered by Bash(rm:*) - on-demand-skill-hooks.md: add Registration requirement section with
  settings.json JSON example and explanation of why registration is needed

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- **settings**: Use portable path for plansDirectory
  ([`0391164`](https://github.com/ByronWilliamsCPA/.claude/commit/039116403b69453b6d397ab12e7b4aaa7b6f60db))

Hard-coded /home/byron/.claude/plans breaks for any other user who clones this repo. Using ~ which
  most path-aware tools expand to the current user's home directory.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **tools**: Use uv run python in check_docs.sh for reproducibility
  ([`e78cf29`](https://github.com/ByronWilliamsCPA/.claude/commit/e78cf29a97f91ea4abf0772dba466ce759068882))

Bare python call would use whatever python is on PATH, which may not match the project's managed
  virtualenv. uv run python ensures the project toolchain is used.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- **docs**: Exclude PlantUML font cache from git
  ([`566950e`](https://github.com/ByronWilliamsCPA/.claude/commit/566950e0bf7eb6c6e9c4097c1890cf7761a97f3e))

The plantuml CLI writes a Java font cache to a directory named `?` under the diagram output
  directory during SVG rendering. This directory is an artifact and not part of the project; exclude
  it with a wildcard gitignore pattern that matches any single-character subdirectory.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Documentation

- Correct Python version requirement from 3.12+ to 3.10+
  ([`4221f95`](https://github.com/ByronWilliamsCPA/.claude/commit/4221f9503bbd01f3f2bfb0846c9ee71fea147d02))

pyproject.toml declares requires-python = ">=3.10,<3.15". Both getting-started docs incorrectly
  stated Python 3.12+ as the minimum requirement.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Implement best-practice adoptions (items 1-13) and architecture docs
  ([`720b024`](https://github.com/ByronWilliamsCPA/.claude/commit/720b024907287ea50edb87e49a0cab3fa3abed20))

Add 13 items from the best-practice review consensus-adjusted short list:

- rules/settings-and-permissions.md: five-scope hierarchy, evaluation order, and sandbox layer
  documentation - settings.json: 22-entry permissions.ask 7-day trial, outputStyle, plansDirectory,
  CLAUDE_AUTOCOMPACT_PCT_OVERRIDE, SessionStart hook - .claude/settings.json: FileChanged .env*
  audit hook, Stop pre-commit trial - rules/git-workflow.md: /branch and --fork-session session
  forking docs - rules/supervisor.md: Explore/Plan built-in subagent rows, two-pattern skill
  architecture section, pre-planning codebase discovery checklist - rules/loop-recipes.md: /loop
  recipes with cost circuit-breaker safeguards - standards/on-demand-skill-hooks.md: on-demand hook
  convention with RAD_STRICT_MODE reference implementation - scripts/env-file-audit.sh,
  stop-pre-commit-hook.sh, session-start-rules.sh: companion hook scripts for the three new hooks -
  skills/rad/workflows/rad-strict-hook.sh: reference impl for on-demand hooks

Also fixes pre-existing frontmatter issues in docs/development/best-practice-review/ and includes
  architecture docs, ADRs, contributing guides, getting-started guides, and reference docs
  previously staged from prior sessions.

Source: docs/development/best-practice-review/synthesis-report.md

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- **claude-md**: Elevate em-dash rule and add worktree path constraint
  ([`7fb8273`](https://github.com/ByronWilliamsCPA/.claude/commit/7fb82733ef017ae3c17f2b00ac5ca33ad52a8ec0))

Move the em-dash ban from the writing rules reference to a top-level section in CLAUDE.md so it is
  visible at all times, not only when reading the full writing rules. Add the worktree path
  constraint (project-local .worktrees/<branch-slug> only) alongside the git workflow entry. Add
  .worktrees/ to .gitignore with a clarifying comment.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **diagram**: Regenerate hook_pipeline.svg from updated PUML source
  ([`bf12104`](https://github.com/ByronWilliamsCPA/.claude/commit/bf12104564eb2d260b04199445c67c74330a1352))

The PUML source was rewritten in a prior commit to show the actual hook scripts from both settings
  files. Regenerate the SVG to match using the plantuml.jar from the image_detection tools
  directory.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **diagram**: Update hook_pipeline.puml to match actual hook config
  ([`3f9e7ec`](https://github.com/ByronWilliamsCPA/.claude/commit/3f9e7ec00584b728784d077f89e95e64248ed875))

Previous diagram referenced hookify dispatch, planning-bridge-gate, secrets scan, and other scripts
  that are not in settings.json. Updated to show the scripts that are actually wired:
  tdd-enforcement-hook.sh, bash-pre-hook.sh, stop-pre-commit-hook.sh, bash-notify.sh,
  track-mcp-usage.sh, env-file-audit.sh, validate-frontmatter.sh, and the keyword-tool-trigger.sh /
  SessionStart scripts.

Note: SVG needs regeneration via plantuml to match updated source.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **git**: Update review workflow references to /pr-review
  ([`23a7025`](https://github.com/ByronWilliamsCPA/.claude/commit/23a70257e454ad28b2ebb58ea53737b73935209d))

Replace /code-review references with /pr-review throughout the PR workflow documentation. /pr-review
  supersedes /code-review: it triggers Copilot automatically, adds SonarQube PR findings, runs 8
  agents instead of 5, and reports all findings in tiers rather than filtering at 80 confidence.
  Update git-workflow.md and the git/pr skill to reflect the new primary review command.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Features

- **skills**: Add pr-review and pr-fix orchestration skills
  ([`1068e64`](https://github.com/ByronWilliamsCPA/.claude/commit/1068e64f618a26d05f5e68d363277ec4f043b9d7))

Add the /pr-review skill: a full PR review pipeline that triggers GitHub Copilot immediately,
  fetches SonarQube PR findings, runs up to 8 parallel agents (CLAUDE.md compliance, bug scan,
  git-history context, prior PR comments, comment accuracy, silent failures, test coverage, type
  design), confidence-scores every finding, and outputs a tiered report.

Add the pr-fix sub-workflow: executes mechanical fixes from the review output in an isolated
  worktree. Handles shell script bugs (stdin pattern, uv run python), documentation accuracy,
  em-dash replacement, SonarQube shell findings, configuration portability, pre-commit config gaps,
  Python antipatterns, docstring accuracy, and bare exception handling. Categorizes non-mechanical
  findings (test gaps, type design, security, complex logic) as requiring manual fix.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.4.0 (2026-04-11)

### Bug Fixes

- **quality**: Resolve remaining SonarQube code smells on branch
  ([`75e1a5a`](https://github.com/ByronWilliamsCPA/.claude/commit/75e1a5a2347c56252c8e2c227efec51b55986e0c))

setup.sh (shelldre:S7682): added explicit `return 0` to log helpers (log_info/ok/skip/warn/error),
  run_or_dry, preflight, doctor, ensure_submodules, and backup_settings so each function ends with
  an explicit return statement under `set -euo pipefail`.

scripts/pr-review-reminder.py: - S5713: removed redundant json.JSONDecodeError from except tuple
  (JSONDecodeError is a ValueError subclass, already caught) - S5713: removed redundant ValueError
  from os.read except tuple (only OSError is raised by sys.stdin.read) - S3516: refactored main() to
  return None instead of always returning 0; caller changed from sys.exit(main()) to main()

Verified: bash -n setup.sh, python compile, ./setup.sh --doctor, ./setup.sh --dry-run, and hook
  smoke tests with PR and non-PR prompts all pass.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **review**: Address Copilot comments and SonarQube hotspots on PR #14
  ([`f928aad`](https://github.com/ByronWilliamsCPA/.claude/commit/f928aad8114300a3808179e36abf55de64143715))

Fixes all 4 Copilot inline review comments and all 3 SonarQube security hotspots surfaced on PR #14.
  My own /code-review pipeline only ran its internal 5-agent review and did not read other
  reviewers' findings, so these were missed until explicitly fetched.

## Copilot comment fixes

1. setup.sh preflight: softened jq requirement (Copilot comment on setup.sh:67) Previously,
  preflight exited 3 if jq was missing, blocking even the symlink creation on jq-less systems. This
  was a regression vs the pre-refactor behavior. Now preflight hard-requires only `ln` and `git`
  (needed for symlinks), and treats `jq` as soft with a warning. `merge_hooks` and
  `merge_claude_md_excludes` each check for `jq` independently and skip with a warning if absent.

2. setup.sh doctor: dangling symlink detection (Copilot comment on setup.sh:104) Previously, doctor
  marked any symlink whose readlink output matched the expected path as [ok], even if the target
  path did not exist (dangling link, common when submodules are not initialized). Added a [[ -e
  "$link" ]] check so dangling links are reported as [dangle] and counted as broken.

3. setup.sh merge_claude_md_excludes: preserve user-defined excludes (Copilot comment on
  setup.sh:219) Previously, `.claudeMdExcludes = [...]` replaced the entire array, clobbering any
  user-added patterns. Now uses `.claudeMdExcludes = ((existing // []) + [repo patterns]) | unique`
  so repo-specific entries are appended and the result is deduplicated. User-defined excludes are
  preserved across setup.sh runs.

4. rules/python.md argument count wording (Copilot comment on python.md:212) Previously, the earlier
  "Parameter Grouping" rule said ">4 params -> dataclass" (5+) while the new Function Quality Gates
  said "maximum 5 positional (PLR0913); use dataclass grouping above that" (6+). These conflicted.
  Aligned to "maximum 4 positional before grouping; use dataclass for 5 or more" per Copilot's
  suggestion, matching the established Parameter Grouping rule.

## SonarQube hotspot fixes

5-7. scripts/pr-review-reminder.py ReDoS risk (python:S5852) Three hotspots on lines 43-45 flagged
  the regex patterns for `\breview\s+(this\s+|the\s+)?(pull\s+request|pr\b)` and similar shapes as
  vulnerable to polynomial backtracking due to nested `\s+` with optional groups.

Replaced the PR_PHRASE_PATTERNS regex list with a PR_PHRASES tuple of plain lowercase substrings.
  The prompt is normalized via `.lower()` and collapsed-whitespace substitution before matching.
  Substring matching is strictly linear, eliminating the ReDoS surface entirely.

Also expanded phrase coverage: the previous 5 regex patterns are now 19 explicit substrings
  (review/look-at/check + pr/pull request + this /the/bare). Added a new whitespace normalization so
  inputs like "review the PR" still match the intended phrase.

Kept two regex patterns: PR_URL_RE (bounded character classes, no ReDoS risk) and
  EXPLICIT_COMMAND_RE (anchored literal, no risk).

## Verification

- bash -n setup.sh: clean - shellcheck setup.sh: clean - ./setup.sh --doctor: all 8 symlinks OK,
  hooks present, claudeMdExcludes present - ./setup.sh --dry-run: shows correct jq merge+dedupe plan
  - ./setup.sh (live run): idempotent, claudeMdExcludes deduped correctly - pr-review-reminder.py: 6
  test cases pass including new whitespace case

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **ruff**: Stop auto-correcting files inside .submodules/
  ([`f67d66a`](https://github.com/ByronWilliamsCPA/.claude/commit/f67d66a7d9aaf9b8b0dd7fb5a6fc66b08a997e23))

The PostToolUse ruff hook was modifying files inside git submodules every time Claude ran, producing
  spurious "modified content" reports and accidentally drifting vendored code.

Root cause: ruff's exclude list in pyproject.toml did not include .submodules/, and force-exclude
  was not set. When ruff is invoked with an explicit file path (e.g., from the Claude Code
  PostToolUse hook running ruff check --fix on a file inside a submodule), exclude rules are
  bypassed by default unless force-exclude = true.

Fix: - Add .submodules/ and .submodules/** to [tool.ruff] exclude - Set force-exclude = true so
  exclude applies to explicit file arguments too - Add \.submodules/ to .pre-commit-config.yaml
  top-level exclude pattern as defense-in-depth against pre-commit hooks reaching into vendored
  trees

Verified: `ruff check --fix .submodules/anthropics-plugins/plugins/hookify/hooks/pretooluse.py` now
  reports "No Python files found under the given path(s)" and leaves the file untouched.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **writing**: Remove em-dashes introduced in this PR
  ([`91cbd64`](https://github.com/ByronWilliamsCPA/.claude/commit/91cbd649293773b6da81b4cd091b3e215f3d706a))

Self-review caught 14 em-dashes introduced across the three files modified by this PR. The
  no-em-dashes rule is a Tier 3 user preference codified in .claude/rules/writing.md and explicitly
  referenced from CLAUDE.md.

- CLAUDE.md: 12 em-dashes replaced with commas (in Development philosophy numbered list, Compact
  Instructions bullets, and Project context note) - README.md: 1 em-dash replaced with semicolon in
  the wrapper-skill follow-up note - setup.sh: 1 em-dash replaced with a period in the
  ensure_symlink warning message

Pre-existing em-dash in setup.sh line 2 (the script's header comment) is left alone because it was
  not introduced by this PR and modifying it would expand the diff beyond scope.

Identified by self-run of /code-review via 5-agent Sonnet parallel review.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- Add pip-audit pre-push hook for dependency vulnerability scanning
  ([`3c17eeb`](https://github.com/ByronWilliamsCPA/.claude/commit/3c17eeb023428f218fd1d454e318f6677f40d383))

- **deps**: Reconcile uv.lock with pyproject.toml version
  ([`63bab66`](https://github.com/ByronWilliamsCPA/.claude/commit/63bab6650382874bad08bf8b9eb5d35ff52f10eb))

The uv.lock file carried claude-config version 1.0.0 from the initial cookiecutter commit, but
  pyproject.toml has been bumped through 0.1.0, 0.2.0, and 0.3.0 without the lock file being
  regenerated. Running uv lock now corrects the recorded version to 0.3.0.

Also tightens the transitive typing-extensions marker on exceptiongroup from python_full_version <
  '3.13' to < '3.11', which more accurately reflects that exceptiongroup is a backport only relevant
  on Python 3.10 within our >=3.10,<3.15 supported range.

No dependency versions change; this is a lock-file accuracy fix.

### Documentation

- Add AI review configuration sync guidance to cookiecutter handoff doc
  ([`0ad029b`](https://github.com/ByronWilliamsCPA/.claude/commit/0ad029b9fa1120a14705aa72ea332e69ee2579e5))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add CodeRabbit and Copilot review checklist items to pre-commit rules
  ([`d0f6814`](https://github.com/ByronWilliamsCPA/.claude/commit/d0f68148bc70271951d852a7b9be809cd95f2516))

- Add docstring coverage and argument validation checklist items
  ([`f50a329`](https://github.com/ByronWilliamsCPA/.claude/commit/f50a329e4c526270d8808a6e03f01a4aaf57f26b))

- Add exception hierarchy guidance and expand documentation section in python rules
  ([`4918834`](https://github.com/ByronWilliamsCPA/.claude/commit/4918834f07c4c7a24d2791d8e05a7a78af95fbd4))

- Add FIPS 140-2/3 compliance requirements to python rules
  ([`38b1b0d`](https://github.com/ByronWilliamsCPA/.claude/commit/38b1b0d102d2e5c3aecbcc796fc214ad3df42a57))

- Add GitHub Actions SHA pinning guidance to git workflow rules
  ([`121edb6`](https://github.com/ByronWilliamsCPA/.claude/commit/121edb6ef9943172198123123c8d14c2e4951482))

- Add golden file protection guidance to CLAUDE.md Testing section
  ([`96f853a`](https://github.com/ByronWilliamsCPA/.claude/commit/96f853a2e2077bc0cbab4633a5ee96846aae85ba))

- Add known vulnerability template and CVE policy reference to CLAUDE.md
  ([`33e6f32`](https://github.com/ByronWilliamsCPA/.claude/commit/33e6f327adb89e1d6a78005048ce86f0136d16c8))

- Add remote verification, branch override, and AI review gate documentation
  ([`11edf1f`](https://github.com/ByronWilliamsCPA/.claude/commit/11edf1f7b182bb3620901ab7446158a0c2b21ebc))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add scope tracing principle to CLAUDE.md and supervisor rules
  ([`beb421a`](https://github.com/ByronWilliamsCPA/.claude/commit/beb421ae2acd8cf7912bb2a6d9583ca3693befb4))

- Add Sprint 2 code quality patterns design spec
  ([`7c2aeeb`](https://github.com/ByronWilliamsCPA/.claude/commit/7c2aeebafab5cd9544f65395bb190223fa1a1a64))

Covers exception hierarchy guidance, golden test protection, and docstring coverage gate
  documentation for rules/python.md, CLAUDE.md, and rules/pre-commit.md.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add Sprint 3 git workflow governance design spec
  ([`014494d`](https://github.com/ByronWilliamsCPA/.claude/commit/014494d8f13adf292205221c872e1ee0c3b1dd79))

Covers remote verification, branch override pattern, scope tracing principle, and AI review
  integration (CodeRabbit + GitHub Copilot).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add Sprint 3 git workflow governance implementation plan
  ([`a12daee`](https://github.com/ByronWilliamsCPA/.claude/commit/a12daee57b12c218f0e849a1a5253b2c9f5a3b30))

Five tasks: update git-workflow.md (remote verification, branch override, Layer 2 AI review
  expansion), add scope tracing to CLAUDE.md and supervisor.md, add AI review checklist items to
  pre-commit.md, update cookiecutter handoff doc with AI review config sync guidance.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Address code review findings from PR #10
  ([`c4cb49f`](https://github.com/ByronWilliamsCPA/.claude/commit/c4cb49f5fdb6feb7fd69a1c0aee760c940c892d9))

- Fix BLE/TRY enforcement claim: TRY002 and BLE001 catch specific anti-patterns but do not validate
  the full AppError hierarchy; code review is the enforcement mechanism for hierarchy structure -
  Fix to_dict() return type from dict[str, str] to dict[str, object] to avoid breakage when
  subclasses add non-string fields - Add note that subclass ... bodies are minimal when no extra
  attributes are needed; show examples in inline comments - Explain interrogate/darglint scope
  asymmetry: scripts/ excluded from darglint due to *args/**kwargs false-positive patterns - Add
  darglint long-strictness definition (multi-line docstrings only) - Bridge global docstring
  standard to scripts/-scoped gate via Ruff D rules - Move Docstring Coverage and Docstring
  Arguments checklist items to sit adjacent to linter checks (before Commits are signed) - Scope
  Golden File Protection to output snapshots (tests/golden/, *.snap); clarify tests/fixtures/ may
  contain input data, not snapshots - Bump CLAUDE.md to v1.2.0, update Last Updated to 2026-04-10

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Address PR review findings — FIPS, CVE policy, pip-audit hook
  ([`5de48ab`](https://github.com/ByronWilliamsCPA/.claude/commit/5de48abe57f4f0cd5ba03df0ebd04312109289d4))

- Align CVE reassessment window to 60 days (was 90) to match the OpenSSF release gate; add
  cross-reference note to CLAUDE.md blockquote - Update known-vulnerabilities-template.md to reflect
  60-day window - Add virtualenv assumption comment to pip-audit pre-push hook - Rename FIPS table
  row 'Key exchange' to 'Asymmetric / Key Exchange' - Promote Curve25519/X25519 FIPS 140-3 qualifier
  from table parenthetical to standalone explanatory note below the table - Group GitHub Actions SHA
  pinning under a 'Security Practices' heading in git-workflow.md for easier navigation as the file
  grows

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Clarify darglint scope and remediation in pre-commit checklist
  ([`01a5d71`](https://github.com/ByronWilliamsCPA/.claude/commit/01a5d71c728a441d91a6c3a422ce38d9b292ab54))

- Expand sprint-3 spec to five items and fix em-dashes
  ([`82a95f5`](https://github.com/ByronWilliamsCPA/.claude/commit/82a95f59d7285a21f908adb2aaa20e2c76b23938))

Adds Item 5 (cookiecutter AI review config sync), updates overview count, fixes three em-dashes in
  Items 4a and 4b, and updates Files Modified, Verification, and Out of Scope sections accordingly.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Fix em-dash in pre-commit security scanning checklist item
  ([`f50578c`](https://github.com/ByronWilliamsCPA/.claude/commit/f50578c7dd41b6ccab0ed3aa40721870e9161d20))

- Fix em-dashes and code block style in python rules exception section
  ([`91019fa`](https://github.com/ByronWilliamsCPA/.claude/commit/91019fa9c7d5bba53219a67521ba2c7a80ed1c67))

- Fix FIPS key exchange qualifier and add AES mode guidance
  ([`f69b6cb`](https://github.com/ByronWilliamsCPA/.claude/commit/f69b6cb0e2bb9f0b3c9996a1b92bc18bb8c53cab))

- Fix frontmatter in sprint-1 plan and spec files
  ([`a599c3e`](https://github.com/ByronWilliamsCPA/.claude/commit/a599c3e5341cd4543050f34c650ef93972039bf1))

Add planning frontmatter to plan file and remove redundant H1. Replace invalid pre-commit tag with
  tooling in spec file.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Fix golden file protection wording and cargo snapshot command
  ([`8e57c9e`](https://github.com/ByronWilliamsCPA/.claude/commit/8e57c9ed685af4df5e84ae5a03d7a3740bad7f37))

- Replace em-dashes in Layer 1 and Layer 2 gate headings
  ([`d9c3131`](https://github.com/ByronWilliamsCPA/.claude/commit/d9c3131000577e48745b252f5da89861d9a9dbbc))

- Replace puffery word in gate system summary line
  ([`09eec0a`](https://github.com/ByronWilliamsCPA/.claude/commit/09eec0ac7f1b19d00ffad204452a8e146f5b02f3))

- Tighten scope tracing wording and add tagline entry
  ([`c1b4ac7`](https://github.com/ByronWilliamsCPA/.claude/commit/c1b4ac7b8392e9c632ef5de492c926374442f18e))

- **cowork**: Add paste-in instructions and remove bushido plugin
  ([`106301f`](https://github.com/ByronWilliamsCPA/.claude/commit/106301f64216eb3aff2a0594e57ca18bd9c3d1aa))

Add .claude/cowork/ with paste-in content for Claude Cowork and Desktop:

- profile.md (~275 words): universal writing rules and communication style - cowork.md (~340 words):
  file safety, Word/Excel conventions, citations - folder-template.md: per-folder project context
  with placeholders - sources.md: traceability from paste-in sections to source rule files -
  README.md: paste workflow and future migration notes

All paste-in files stay under the 500-word per-field ceiling per Anthropic custom instructions best
  practice. Covers the Word and Excel use case; browser research remains in Claude for Chrome and
  coding in Claude Code.

Remove bushido@han plugin and han marketplace from .claude/settings.json; the SessionStart injection
  is no longer used.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- **cowork**: Apply PR #13 review feedback
  ([`19002d1`](https://github.com/ByronWilliamsCPA/.claude/commit/19002d12821aed77649ee766d9000380645d9bcb))

- sources.md: replace em-dashes in external reference link titles with parenthetical source
  attribution (the no-em-dash rule the PR itself enforces must apply here too) - cowork.md: scope
  the Title Case heading rule explicitly to Word document output so it does not imply markdown
  source files - profile.md: restore dropped banned terms (groundbreaking, to summarize, at the end
  of the day, exemplary, enhancing performance) and add pointer to extended structural tells list -
  cowork.md: replace .bak.YYYY-MM-DD-HHMM with ISO 8601 UTC basic format (.bak.YYYYMMDDTHHMMSSZ) for
  lexical sortability and collision safety; replace the unenforceable "three consecutive edits" rule
  with an observable trigger (before destructive edits) - README.md: update word count targets to
  reflect new content (profile.md ~300, cowork.md ~350, folder-template.md ~220)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- **readme**: Note wrapper-skill follow-up for /code-review PR URL triggers
  ([`bc4efa3`](https://github.com/ByronWilliamsCPA/.claude/commit/bc4efa3b9c9ba9bebc14ef58a947a37a23f04848))

Adds a subsection to the Claude Code Standards section of README.md capturing the architectural note
  that surfaced during PR #14: the /code-review plugin is a command, not a skill, so prose phrasings
  like "review this PR" do not reliably invoke the structured 5-agent review pipeline. Only the
  explicit /code-review slash command does.

Documents the proposed fix (thin wrapper skill in .claude/skills/code-review-pr/ that routes
  natural-language PR review requests to the underlying command) so the idea is not lost between
  sessions. The fix itself is not implemented here; this is a documented backlog item.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **readme**: Replace aspirational subtree docs with actual symlink topology
  ([`ec8394a`](https://github.com/ByronWilliamsCPA/.claude/commit/ec8394a06e3ee95f3a9527f5502d07724e9811b0))

The old "Claude Code Standards" section described a git subtree pattern (.claude/standard/ with `git
  subtree pull`) that no project actually uses. monte_carlo, cookiecutter-python-template, and other
  consumer projects keep their own project-local CLAUDE.md and inherit the global config via the
  user-scope ~/.claude/ symlinks created by setup.sh.

Replaced with accurate documentation of the real two-layer install pattern:

1. ASCII topology diagram showing the symlink map from ~/.claude/ (runtime that Claude Code reads)
  into ~/dev/.claude/ (repo source of truth in git) 2. Install command (clone + ./setup.sh) 3.
  Verify command (./setup.sh --doctor) introduced in the companion commit 4. Dry-run command
  (./setup.sh --dry-run) introduced in the same commit 5. Rationale for symlinks over
  subtree/submodule (clean runtime, instant propagation, no copy step, claudeMdExcludes prevents
  double-load) 6. Note on per-project CLAUDE.md and .claude/settings.local.json overrides

Completes the documentation side of the consensus-recommended refinements.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Features

- **hooks**: Add pr-review-reminder UserPromptSubmit hook
  ([`a2bceaf`](https://github.com/ByronWilliamsCPA/.claude/commit/a2bceaf31daa3c8d71980f9093bb64d26ca97326))

Addresses the auto-activation gap for /code-review. Because /code-review is a Claude Code plugin
  command (not a skill), prose phrasings like "review this PR" do not auto-invoke the structured
  5-agent pipeline. This hook closes that gap by detecting PR review intent in user prompts and
  injecting a system message telling Claude to ask the user whether they want the structured command
  run.

Implementation: - scripts/pr-review-reminder.py: standalone Python hook, reads JSON event from
  stdin, extracts user_prompt field, matches against GitHub PR URL regex and natural-language
  review-intent phrases, short-circuits if /code-review is already present or if
  PR_REVIEW_REMINDER_DISABLED=1 is set in the environment. Always exits 0, never blocks the prompt.
  - hooks.json: new UserPromptSubmit entry running the script with a 5s timeout, placed after the
  existing hookify entry so both fire. The script is referenced from $HOME/.claude/scripts/ which
  resolves via the setup.sh symlink to $HOME/dev/.claude/scripts/. - README.md: updated the
  wrapper-skill follow-up section to reflect the implemented hook, listing the trigger patterns and
  the opt-out environment variable.

Tested 5 scenarios locally: - Empty event -> no reminder (correct) - No PR mention ("what time is
  it") -> no reminder (correct) - GitHub PR URL -> reminder fires (correct) - "review this PR and
  tell me what you think" -> reminder fires (correct) - Explicit /code-review invocation -> no
  reminder (correct short-circuit)

Ran setup.sh to merge into ~/.claude/settings.json. Doctor passes.

Global hook vs hookify rule choice: hookify rules load from .claude/hookify.*.local.md relative to
  cwd, so they are project-scoped and would only fire when working inside specific projects. A
  standalone hook entry in hooks.json fires on every UserPromptSubmit regardless of cwd, which
  matches the user's stated goal of reminding them globally.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **setup**: Harden setup.sh with dry-run, doctor, backups, claudeMdExcludes
  ([`35ecc2c`](https://github.com/ByronWilliamsCPA/.claude/commit/35ecc2ce68c3571217db8f6d5d3d0f312dba76dd))

Adds operational safety and observability to the bootstrap script per the consensus refinement
  recommendations. Every change is backwards compatible: existing users running the new script get
  the same symlinks and hook merge behavior they had before, plus the new doctor command and
  stronger safety.

Added features: - `set -euo pipefail` at the top so errors halt execution instead of silently
  continuing - Flag parsing: `--dry-run` shows what would change without applying, `--doctor` prints
  the resolved symlink topology and flags broken links, `--help` shows usage from the script header
  comment - Preflight check: verifies jq, ln, and git are available before any operation, exits with
  a clear error if not - `ln -sfn` used consistently so symlink updates are atomic - Timestamped
  backup of ~/.claude/settings.json (format settings.json.bak.YYYYMMDD-HHMMSS) before any jq merge,
  so settings can be rolled back if a merge corrupts them - New symlinks for CLAUDE.md, rules, and
  standards directories (these were symlinked manually in the existing install but setup.sh did not
  create them, which broke reproducibility for new clones) - New merge step: `claudeMdExcludes` is
  populated in settings.json with paths derived from $REPO_DIR, so the repo's own CLAUDE.md and
  .claude/**/* are excluded from directory-walk discovery when working inside the repo itself. This
  solves the double-load edge case identified by the 5-model consensus. Uses --arg for path
  injection so the excludes work correctly regardless of where the repo is cloned. - Doctor mode:
  verifies each expected symlink points where it should, flags drift (wrong target), real (regular
  file instead of symlink), or miss (not present). Also checks whether hooks and claudeMdExcludes
  are present in settings.json.

Verified: - `bash -n setup.sh` passes syntax check - `shellcheck setup.sh` exits 0 with no warnings
  - `./setup.sh --doctor` reports all symlinks OK and settings present - `./setup.sh --dry-run`
  shows correct action plan without modifying files

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Refactoring

- **claude-md**: Trim to 141 lines, add Compact Instructions
  ([`424f8f8`](https://github.com/ByronWilliamsCPA/.claude/commit/424f8f89bece2cc58d013d51c04257ea86cfcbd4))

Executes the CLAUDE.md refactor recommended by the 5-model PAL consensus. Target size was under 200
  lines per Claude Code's documented guidance; the previous 265-line file consumed ~3.5k tokens on
  every session start with significant duplicated content.

Content removed (moved to path-scoped rules or deleted as duplication): - Testing scope, root-cause
  order, Golden File Protection -> now in .claude/rules/testing.md (path-scoped to test files) -
  Python Code Generation Principles (function structure, complexity, code duplication, immutability)
  -> now in .claude/rules/python.md as "Function Quality Gates (MANDATORY)" (path-scoped to **/*.py)
  - Global Resource Catalog tables (~65 lines of agent and skill tables) -> already duplicated in
  AGENTS-AND-SKILLS.md at repo root; CLAUDE.md now just points there - Install / Update section ->
  README.md covers this - Project Integration example -> removed (was an example, not a rule)

Content condensed: - Project Context: 9 lines -> 6 lines - Code Quality: 10 lines -> 6 lines (with
  new pointers to rules/python.md and rules/testing.md) - Core Development Standards + references:
  22 lines -> 20 lines (consolidated into single pointer block) - Response-Aware Development full
  example: 22 lines -> 8 lines (trigger syntax stays inline, full workflow moves to
  docs/response-aware-development.md) - Development Philosophy: 14 lines -> 10 lines (numbered
  decision order) - OpenSSF Best Practices: 12 lines -> 7 lines

Content added: - Compact Instructions section (~20 lines): tells the compaction summarizer what to
  preserve (file paths with line numbers, error messages verbatim, architecture decisions, current
  test state, branch state, decision rationale, user-specific corrections) and what to drop (tool
  logs, exploratory detours, request restatements). Per the compaction research, CLAUDE.md is the
  only component guaranteed to survive compaction intact, so explicit instructions here shape
  summarizer behavior.

Version bumped 1.2.0 -> 1.3.0. Live ~/.claude/CLAUDE.md picks up the change automatically via the
  symlink to this file.

Expected savings: ~1.7-2k tokens unconditional per session, plus ~600 tokens saved when not working
  on Python files (Python gates now path-scoped).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **rules**: Extract testing rules and Python function gates from CLAUDE.md
  ([`ce3ed16`](https://github.com/ByronWilliamsCPA/.claude/commit/ce3ed1651a152323b7d07cb1ecbdcfcfd041411f))

Part of the CLAUDE.md refactor recommended by the 5-model PAL consensus. Moves operating rules from
  the always-loaded ~/.claude/CLAUDE.md into path-scoped rules/*.md files that only load when Claude
  works on matching files, reducing unconditional context cost per session.

New file: .claude/rules/testing.md - Path-scoped to test files, fixtures, and snapshot files -
  Contains the testing scope-clarification rule, root-cause investigation order, and golden file
  protection rule - Does not duplicate coverage thresholds or framework choice (those live in
  .claude/standards/testing.md, which is intentionally unconditional)

Updated: .claude/rules/python.md - Appends "Function Quality Gates (MANDATORY)" section with
  function structure, complexity controls, code duplication, and immutability rules - This content
  was previously inline in CLAUDE.md. Python.md is already path-scoped to **/*.py and
  pyproject.toml, so these principles now only load when Claude works on Python files.

Follow-up commits will: remove the duplicated content from CLAUDE.md, path-scope the remaining
  unconditional rules files where appropriate, and harden setup.sh.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.3.0 (2026-04-10)

### Bug Fixes

- Add hooks.json to REUSE.toml and mark S5332 hotspot safe
  ([`5684dca`](https://github.com/ByronWilliamsCPA/.claude/commit/5684dca1f223844a0972ef15202c97921ace6ee4))

- Add hooks.json to MIT annotation in REUSE.toml — file was missing SPDX coverage, causing REUSE
  compliance check failure - The python:S5332 security hotspot in scripts/doc-audit.py line 310 is a
  false positive (checking string prefix to skip URLs, not making HTTP connections); marked SAFE in
  SonarCloud

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add missing spec behaviors (schema_version INFO, count INFO, directory guards), reduce
  check_versions complexity
  ([`f406847`](https://github.com/ByronWilliamsCPA/.claude/commit/f406847ca32fc9ea7fcc6bf364490d003def3c43))

- Address quality review issues in /ci-fix skill — retry limit, pip-audit status, nosec format,
  bandit root detection
  ([`bd328ce`](https://github.com/ByronWilliamsCPA/.claude/commit/bd328ce7fc81b438d8e53e8ec4d73f81099b8a51))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Clarify flag format and tighten suppression exception in CLAUDE.md rules
  ([`623296d`](https://github.com/ByronWilliamsCPA/.claude/commit/623296d8e862bbed86edcc59527de8ec1c895034))

- Replace type:ignore with importlib.abc.Loader assert, use typing.TypedDict
  ([`17bb0ce`](https://github.com/ByronWilliamsCPA/.claude/commit/17bb0ce4aadd3bfacff88a39c726939fd0debf2c))

- Resolve SonarCloud issues in doc-audit.py and setup.sh
  ([`99136a8`](https://github.com/ByronWilliamsCPA/.claude/commit/99136a8224460bcd42083be4c02b7feba71a6270))

- Extract _parse_yaml_scalar_line helper to reduce _parse_simple_yaml cognitive complexity from 18
  to 13 (S3776) - Extract _extract_local_path and _check_links_in_file helpers to reduce check_links
  cognitive complexity from 22 to 1 (S3776) - Add _CLAUDE_SUBDIR constant to eliminate repeated
  ".claude" literals (S1192) - Use [[ ]] instead of [ ] for conditionals in setup.sh (S7688)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- Add docs/audit-report.md to .gitignore (generated artifact)
  ([`b5eeeb3`](https://github.com/ByronWilliamsCPA/.claude/commit/b5eeeb3285ef2ccc62a4d9a610e7a04ad416bf16))

### Documentation

- Add /ci-fix skill design spec and fix plan H1
  ([`48d6f17`](https://github.com/ByronWilliamsCPA/.claude/commit/48d6f1780c77054fc124f029a846c44a07a052ef))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add /ci-fix skill implementation plan
  ([`5549c94`](https://github.com/ByronWilliamsCPA/.claude/commit/5549c94a922921fdae4751e77fd135bf2b220c00))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add /doc-audit skill design spec
  ([`fad94a9`](https://github.com/ByronWilliamsCPA/.claude/commit/fad94a950088c181ecfce4e7eff5d4d48d46d23e))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add /doc-audit skill implementation plan — TDD, 4-task structure
  ([`98ee3db`](https://github.com/ByronWilliamsCPA/.claude/commit/98ee3db47fcd058495c11781c248535e72798e59))

- Add CLAUDE.md additions design spec and fix four-hooks frontmatter
  ([`5a0c083`](https://github.com/ByronWilliamsCPA/.claude/commit/5a0c083c21317c71d6f8808befbac7a95831496b))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Features

- Add /ci-fix gate check to PR pre-commit checklist
  ([`dd18b06`](https://github.com/ByronWilliamsCPA/.claude/commit/dd18b062e8bf291e91b35ec73c4cbd5c46bddc2e))

- Add /ci-fix prerequisite to git PR workflow
  ([`b93c60e`](https://github.com/ByronWilliamsCPA/.claude/commit/b93c60eec7843dcb66a04cea80cb33c096d3bb46))

- Add /ci-fix skill — 7-gate CI fix loop with auto-fix and commit offer
  ([`e8cf3a4`](https://github.com/ByronWilliamsCPA/.claude/commit/e8cf3a439701a2e32bf260618069217d059a82fa))

- Add /doc-audit skill — terminal summary and audit-report.md writer
  ([`2f82ffb`](https://github.com/ByronWilliamsCPA/.claude/commit/2f82ffbc4b0ee89cf71ac28d0f95ba68f47db03a))

- Add environment debugging, no-workaround, and project-docs-over-memory rules to CLAUDE.md
  ([`f514654`](https://github.com/ByronWilliamsCPA/.claude/commit/f51465446aee3ecf6322994374409eb077021bfb))

- Implement doc-audit.py — four-category documentation health audit script
  ([`70104f4`](https://github.com/ByronWilliamsCPA/.claude/commit/70104f429494dbb95e5888b96d04d18dedfb3aad))

- Integrate hookify, code-review, and security-guidance plugins
  ([`1f63382`](https://github.com/ByronWilliamsCPA/.claude/commit/1f63382aee5c361188ff816b097132eb116e963f))

Symlinks: writing-rules skill, /code-review command, /hookify and subcommands (list, configure,
  help).

Hooks wired in settings.json (now tracked via hooks.json): - security-guidance: PreToolUse on file
  edits, blocks dangerous code patterns once per session (XSS, shell injection, unsafe
  deserialization) - hookify: PreToolUse, PostToolUse, Stop, UserPromptSubmit — enforces
  .claude/hookify.*.local.md rules with no restart required

Workflow integration: - git/workflows/pr.md: /code-review runs automatically after gh pr create,
  before the PR URL is reported (5-agent review with confidence scoring) - pre-commit.md:
  /code-review added as a PR gate checklist item - git-workflow.md: Gate System section documents
  both layers

Portability: hooks.json added as source of truth for global ~/.claude/ settings.json hooks; setup.sh
  now merges hooks.json on each run via jq.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Testing

- Add failing test harness for doc-audit.py — 6 scenarios, 14 tests
  ([`1d0b819`](https://github.com/ByronWilliamsCPA/.claude/commit/1d0b819ac59d71706966d5a8ebba7326a8450939))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.2.0 (2026-04-10)

### Bug Fixes

- Bash-notify stale timestamp ceiling, PS injection sanitization, powershell guard
  ([`c98ccdd`](https://github.com/ByronWilliamsCPA/.claude/commit/c98ccdde8ee284096f4eb9268a7f75b11a453910))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Scope force-push detection to git push only, detect force-with-lease=ref form, suppress SC2016
  ([`03aaa33`](https://github.com/ByronWilliamsCPA/.claude/commit/03aaa33c13bc63a1a3e5a42454e9a0b126aba591))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Tighten force-push detection (bare push, path match, atomic timestamp)
  ([`1e5a042`](https://github.com/ByronWilliamsCPA/.claude/commit/1e5a042cdcc600896044981e230925f44af5c5cf))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Tighten set -e and agents path pattern in validate-frontmatter.sh
  ([`d4c1148`](https://github.com/ByronWilliamsCPA/.claude/commit/d4c11481854c4aa7c75fa8292179f6aaf85a3a03))

- Replace set -euo pipefail with set -uo pipefail so the advisory-only hook always exits 0 even when
  grep or awk return non-zero; add || true guard to awk frontmatter extraction - Tighten agents path
  match from *agents*.md (matches filenames) to */agents*/*.md (requires agents to appear as a
  directory name component, not just in the filename)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Validate-frontmatter robustness, CRLF, path pattern, log file, WARN hints
  ([`4c31765`](https://github.com/ByronWilliamsCPA/.claude/commit/4c317652e4508f946958923ca3b067654727b782))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Features

- Add force-push guard and timing start PreToolUse hook for Bash
  ([`d081b76`](https://github.com/ByronWilliamsCPA/.claude/commit/d081b76dcbcd8b55ab40dcea2c3ed45153479cbd))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add frontmatter validator PostToolUse hook for skills and agents
  ([`1e3c62c`](https://github.com/ByronWilliamsCPA/.claude/commit/1e3c62c17f22fc3c77a2fde773c8cd6be73cc541))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add shellcheck PostToolUse hook for .sh edits
  ([`c07953c`](https://github.com/ByronWilliamsCPA/.claude/commit/c07953caf41a215d61c6e0d0fe13f0f8cb0f943c))

- Add WSL2 toast notification PostToolUse hook for long Bash tasks
  ([`c37cd15`](https://github.com/ByronWilliamsCPA/.claude/commit/c37cd15dd9dd5343a42e1563cee6f732f7eb4110))

Introduces bash-notify.sh, which reads the /tmp/claude-bash-start timestamp written by
  bash-pre-hook.sh, computes command duration, and fires a non-blocking Windows balloon notification
  via powershell.exe when the duration exceeds 30 seconds. Wired as a PostToolUse Bash hook in
  settings.json. All 6 unit tests pass.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.1.0 (2026-04-10)

### Bug Fixes

- Address all Copilot, CodeRabbit, QLTY, and SonarQube review comments
  ([`e40816b`](https://github.com/ByronWilliamsCPA/.claude/commit/e40816bf1f1a00531511c7f1d861ca10d0324a9a))

Scripts (scripts/py310-compat-check.sh): - Add grep -P (PCRE) capability check with graceful
  fallback for macOS/BSD grep - Fix tomllib import pattern to allow leading whitespace (indented
  imports) - Expand datetime ceiling patterns to explicitly match both datetime.utcnow() and
  datetime.datetime.utcnow() calling styles - Remove ast.Match detection: match/case is valid Python
  3.10+ syntax and the project floor is 3.10, so flagging it produces false positives - Add explicit
  return 0 to log() function (SonarQube shelldre:S7682)

Scripts (scripts/planning-bridge-gate.sh): - Add jq guard: fail-open (exit 0) if jq is absent to
  prevent hook from blocking PreToolUse execution on systems without jq - Add explicit return 0 to
  log() function (SonarQube shelldre:S7682)

Spec (docs/superpowers/specs/2026-04-09-py310-compat-hook-design.md): - Fix frontmatter status:
  draft -> published (consistent with header) - Remove match/case from Tier 2 pattern table (not a
  floor violation at 3.10) - Fix utcfromtimestamp recommended fix: UTC -> datetime.timezone.utc (UTC
  is itself a 3.11+ feature; recommendation must stay 3.10-compatible) - Update output example and
  Testing section to remove match/case references

Plan (docs/superpowers/plans/2026-04-09-py310-compat-hook.md): - Clarify Test 2 uses
  datetime.datetime.utcnow() (fully-qualified form); document that grep matches both styles as a
  substring - Replace Test 5 match statement with except* test (actual 3.11+ violation) - Update
  cleanup list to remove t5_match.py reference

Plan (docs/superpowers/plans/2026-04-09-planning-bridge-gate.md): - Fix source frontmatter from
  directory reference to explicit inline note

Skill (.claude/skills/project-planning/SKILL.md): - Fix Modes intro: two modes -> three modes
  (Entry, Bridge, Default)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Address PR review comments from Copilot
  ([`573f1ae`](https://github.com/ByronWilliamsCPA/.claude/commit/573f1aed2c3fb22013fd848766cac122541569bf))

- settings.json: replace direct submodule hook path with wrapper script to support both direct-clone
  and two-layer (setup.sh) install layouts - scripts/run-superpowers-session-start.sh: new wrapper
  resolves repo root via readlink so hook works regardless of how ~/.claude is mounted - setup.sh:
  add scripts/ symlink so $HOME/.claude/scripts/ hooks resolve in two-layer setup - CLAUDE.md:
  document both install methods (Option A: two-layer with setup.sh; Option B: direct clone to
  ~/.claude) - .claude/rules/writing.md: replace em-dashes in section headings with parentheses; fix
  relative path to writing-quality.md - .claude/skills/writing/workflows/analyze.md: fix "five" to
  "six" (six inputs listed, not five) - .claude/skills/skill-creator: restore missing symlink to
  upstream

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Catch multiline typing imports and align fix-line indentation
  ([`4e327c4`](https://github.com/ByronWilliamsCPA/.claude/commit/4e327c4f2ef737a997a34e45d22d280aed09e2a3))

- Move Self/LiteralString detection to AST tier (catches multiline imports) - Remove duplicate Tier
  1 grep patterns for Self/LiteralString - Align fix-line indentation to column 26 across Tier 1 and
  Tier 2 - Note ExceptionGroup grep is best-effort in finding output

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Clean up phase-reviewer quality issues from code review
  ([`a216fef`](https://github.com/ByronWilliamsCPA/.claude/commit/a216fef4aa279de781b13dc4dea6107b609a5faf))

- Remove ineffective grep -v filter (CRITICAL/VERIFY tags are on separate lines) - Move
  owasp-dispatch delegation prose outside bash code fence - Remove redundant "Add to Quality Gates
  table" instruction in RAD section - Reference CLAUDE.md as source of truth for coverage thresholds

- Resolve pre-commit and CI/CD issues
  ([`0446c81`](https://github.com/ByronWilliamsCPA/.claude/commit/0446c811a2b00c29293b365ac10cbc0894f8340b))

- Fix trailing whitespace in 40+ files (auto-fixed by pre-commit) - Fix missing newlines at end of
  files (auto-fixed by pre-commit) - Add execute permissions to scripts with shebangs (.bats, .py
  files) - Add proper shebang to .clusterfuzzlite/build.sh - Fix D200: one-line docstring in
  financial.py - Fix TC002/ARG001: move Processor import to TYPE_CHECKING and prefix unused callback
  args with underscore in logging.py - Remove TestCLI tests that referenced non-existent cli module

All checks now pass: - Pre-commit hooks: All pass - Tests: 9 passed with 97.56% coverage - Ruff
  linting: All checks passed - BasedPyright: 0 errors, 3 warnings - Bandit security scan: No issues

- Resolve pre-commit failures across docs and skill scripts
  ([`c067f42`](https://github.com/ByronWilliamsCPA/.claude/commit/c067f42b754367cb78d728b8ad7c2dd5ba2a5b33))

- Extend darglint exclude to cover all .claude/skills/ scripts and noxfile.py (skill helper scripts
  are internal tooling, not library code) - Fix front matter validation in 15 docs/ files: remove
  redundant body H1 headings that duplicate the title: field, add missing schema_type: common where
  absent, fix invalid tags and add required planning fields - Add engineering owner entry to
  docs/_data/owners.yml - Add AGENTS-AND-SKILLS.md catalog and skills-lock.json - Update CLAUDE.md
  and README.md agent/skill catalog tables

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Resolve pre-merge review issues from superpowers branch
  ([`01c344c`](https://github.com/ByronWilliamsCPA/.claude/commit/01c344cd0a950b287aa21d87efc2255077c01a94))

Replace em-dashes with colons in project-plan-synthesizer.md and the cookiecutter handoff doc per
  rules/writing.md. Update writing-skills trigger text in CLAUDE.md to remove collision with
  skill-creator. Add required frontmatter to handoff doc for schema validation.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Resolve semantic-release parser and scorecard private-repo failures
  ([`5cd72c5`](https://github.com/ByronWilliamsCPA/.claude/commit/5cd72c54f1aa8632ab822e043f7664835605b374))

- Change commit_parser from 'conventional_commits' to 'angular' — the v9 parser was renamed and the
  old value caused an invalid import error on every main push - Move changelog_file to
  changelog.default_templates per v9 deprecation warning (compatibility breaks in v10) - Set
  scorecard publish_results=false and add repo_token — private repos cannot publish Scorecard
  results; missing token caused GraphQL ListCommits failures on every run

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **ci**: Address all 15 CodeRabbit PR review comments
  ([`eed8cca`](https://github.com/ByronWilliamsCPA/.claude/commit/eed8cca34b2e5c32594447bbe27dc91b55158397))

- pip-audit flag: --output=json → --format json in standards/security.md and
  docs/guides/testing-guide.md (--output treats arg as filepath) - precommit.md: remove safety:*
  from allowed-tools; replace safety check with pip-audit in step 5 - security/SKILL.md: remove
  duplicate `uv run safety check` line - aggregate_benchmark.py: replace datetime.UTC with
  datetime.timezone.utc for Python 3.10 compatibility - pytest-patterns.md: fix typo
  "valid-plus-subomain" → "valid-plus-subdomain" docs/index.md: align quick-start install with
  guides (uv pip install) - testing/workflows: replace Task tool references with Agent tool
  (subagent_type="test-engineer") in performance.md and e2e.md - content-review.md: remove stale
  Known Issues entry - mcp_config.yaml + .mcp.json: rename server key zen → pal so tool prefix
  mcp__pal__* matches the configured server name - standards/testing.md: separate SAST and
  dependency audit into distinct CI steps; fix resulting step numbering

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **ci**: Resolve remaining Build Docs and Test Python 3.12 failures
  ([`4e43909`](https://github.com/ByronWilliamsCPA/.claude/commit/4e4390973a10aa9382243061a6310835bc1d0c02))

Build Docs (--strict mode): - Add exclude_docs to mkdocs.yml for content-review.md,
  content_reviews/*, ADRs/adr-template.md, planning/project-plan-template.md, planning/adr/README.md
  (internal/template docs with out-of-docs links) - Fix docs/guides/testing-guide.md: convert broken
  relative link to standards/testing.md into plain text (file is outside docs/ dir)

Test Python 3.12 (ruff ARG001): - utils/logging.py: actually use the level param by calling
  logging.basicConfig(level=...) before structlog.configure()

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **ci**: Resolve REUSE compliance, missing package, and mkdocs script
  ([`b087495`](https://github.com/ByronWilliamsCPA/.claude/commit/b0874956d75e24cbcd20718086dc3920d4a06b2c))

- Update REUSE.toml to cover .claude/**, standards/**, mcp/**, tmp_cleanup/**, and root
  dotfiles/config files — brings compliance from 225/397 to 408/408 (all files covered) - Create
  src/claude_config/ package (Settings, get_logger, log_performance, setup_logging) so all 15 unit
  tests pass - Add tools/gen_tools_catalog.py no-op placeholder so mkdocs gen-files plugin finds its
  configured script

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **content-review**: Apply P1 and P2 content review corrections
  ([`eaf4e0b`](https://github.com/ByronWilliamsCPA/.claude/commit/eaf4e0b5475ed1f080641fb0a70d5f7fbe045b8a))

Fixes all Priority 1 (always-loaded rules) and Priority 2 (agents and skill entry points) issues
  identified in docs/content-review.md:

P1 rules (6 files): - git-workflow.md: replace mypy → basedpyright, add breaking-change note and
  cross-references - mcp-strategy.md: fix agent frontmatter docs, add skill bundles table, update
  Tier 3 keywords - pre-commit.md: add tests/RAD steps, clarify /security and /quality scope, fix
  pip-audit and PR tool references - python.md: fix Black attribution, expand Ruff rules table,
  clarify Python version range, add BasedPyright config example - supervisor.md: remove ghost agent,
  fix PR workflow to use /git skill - CLAUDE.md: name pip-audit, scope Code Gen header to Python,
  add variant skills note

P2 agents (17 files): - Add complete frontmatter (name/description/model/tools) to all 13 agents
  that were missing it entirely (core testing, OWASP, phase-reviewer) - Add model and tools to 4
  agents with partial frontmatter (planning/writing agents, visual-content-generator) - Fix
  deprecated invocation format (/review, /test, Task tool) → Agent tool - visual-content-generator:
  replace non-standard mcp_tools field with tools

P2 skills (4 files): - quality/SKILL.md: add frontmatter, remove all Black references, fix trigger
  keywords - security/SKILL.md: add frontmatter - diagram-maintenance/SKILL.md: add frontmatter -
  rad/SKILL.md: fix zen-core → pal MCP server references

P2 context (1 file): - python-standards.md: Black → Ruff formatter reference

Submodule: - .submodules/image-generation: bump to commit with diagram-specialist frontmatter fix
  (fix/add-agent-frontmatter branch)

Tracking: docs/content-review.md (new file), docs/_data/tags.yml (add

content_review tag for review artifact docs) — P1: 6/6 reviewed, P2: 52/52 reviewed (51 clean, 1
  minor optional)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **content-review**: Apply P3 content review corrections (44 files)
  ([`d929c58`](https://github.com/ByronWilliamsCPA/.claude/commit/d929c5872460c141f953ab482d91bd0fb0d7b090))

Fix stale tool references and missing frontmatter across all P3 workflow, context, skill-creator,
  project-planning, and standards files.

Key fixes across 20 files: - poetry→uv, mypy→basedpyright, black→ruff format, safety→pip-audit -
  bandit standalone→ruff --select S (bandit rules via ruff) - mcp__zen-core__/mcp__zen__→mcp__pal__
  in RAD verify.md + response-aware-development.md - git commit.md: added required -S signing flag -
  git pr.md: gh pr create→/git pr skill as primary method - security/scan.md: added pip-audit exit
  code documentation - skill-creator agents (grader, comparator, analyzer): added missing
  frontmatter - standards/*.md: extensive poetry/mypy/black→uv/basedpyright/ruff fixes -
  project-planning/SKILL.md (P2 bonus): mcp__zen__consensus→mcp__pal__consensus (6 occurrences)

24 files reviewed OK (no changes needed); 20 files fixed.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **content-review**: Apply P4 and P5 content review corrections (31 files)
  ([`55198dd`](https://github.com/ByronWilliamsCPA/.claude/commit/55198ddc35d1551cfc9b47a9de4910e9a738c6ae))

Complete the content review sweep across all supporting and meta files.

P4 fixes (7 of 16 files): - AGENTS-AND-SKILLS.md: fixed Task→Agent tool invocation; removed
  non-existent /commit-prepare and /pr-prepare skills; fixed /debug-tests link; added 10
  uncatalogued agents (writing pipeline, diagrams/visuals group) - copilot-instructions.md:
  Black→ruff format (2 occurrences) - mcp/README.md: zen-server.json→disabled; Zen MCP Server→PAL
  MCP Server docs/development/code-quality.md: "Black compatible"→ruff format default
  docs/development/testing.md: coverage thresholds corrected to 80/70/90/90 docs/guides/usage.md:
  pip install→uv pip install docs/guides/testing-guide.md: mypy→basedpyright throughout; pip
  install→uv sync/uv add in CI steps; 13 plugin table entries fixed

P5 fixes (2 of 15 files): - CONTRIBUTING.md: uv run safety check→uv run pip-audit docs/index.md: pip
  install→uv add

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **deps**: Upgrade all locked dependencies to resolve 28 CVEs
  ([`c5bd4e1`](https://github.com/ByronWilliamsCPA/.claude/commit/c5bd4e1c1c981e823911d8d7c497b0dadc0faf67))

uv lock --upgrade bumps all packages to latest compatible versions, resolving every exploitable
  vulnerability except one unfixable case:

Fully resolved: - authlib: 1.6.5 → 1.6.9 (CRITICAL: CVE-2026-27962 Bleichenbacher oracle; HIGH:
  CVE-2026-28802 SSRF, CVE-2026-28490 JWT alg confusion)

- cryptography: 46.0.3 → 46.0.7 (HIGH: CVE-2026-26007 RSA side-channel, CVE-2026-34073 PKCS12 memory
  corruption) - tornado: 6.5.2 → 6.5.5 (HIGH: HTTP smuggling, open redirect) - requests: 2.32.5 →
  2.33.1 (HIGH: CVE-2026-25645 proxy credential leak) - urllib3: 2.5.0 → 2.6.3 (HIGH:
  CVE-2025-66418, CVE-2025-66471) - marshmallow: 4.1.0 → 4.3.0 (HIGH: CVE-2025-68480 ReDoS) -
  nbconvert: 7.16.6 → 7.17.1 (HIGH: CVE-2025-53000 XSS) - nltk: 3.9.2 → 3.9.4 (HIGH: CVE-2025-14009
  path traversal, CVE-2026-33230 XXE) - protobuf: 6.33.1 → 7.34.1 (HIGH: CVE-2026-0994 DoS) -
  pyasn1: 0.6.1 → 0.6.3 (HIGH: CVE-2026-30922 infinite loop) - pygments: 2.19.2 → 2.20.0 (HIGH:
  CVE-2026-4539 ReDoS) - pip: 25.3 → 26.0.1 (HIGH: CVE-2026-1703 malicious wheel exec) - virtualenv:
  20.35.4 → 21.2.1 (MEDIUM: CVE-2026-22702) - filelock: 3.20.0 → 3.25.2 (MEDIUM: temp file race)

Accepted/ignored via .trivyignore: - py 1.11.0 (CVE-2022-42969, ReDoS in py.path.svnwc): no upstream
  fix; only reachable via SVN paths — this project does not use SVN; dev-only dependency via
  interrogate

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **docs**: Correct commands directory path references in CLAUDE.md
  ([`457a046`](https://github.com/ByronWilliamsCPA/.claude/commit/457a046713d390feb0954370aa5517ecbe73c585))

The commands directory is located at `/.claude/commands/`, not `/commands/`. Updated all references
  throughout CLAUDE.md to point to the correct path: - Line 10: Token Optimized reference - Line
  148: Complete Command Reference - Lines 152, 162, 172: Individual command references - Line 723:
  Footer reference

This ensures Claude Code can correctly locate command documentation files when reading the global
  standards.

Fixes path resolution issues where Claude would look for non-existent `/commands/` directory instead
  of actual `/.claude/commands/` location.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

- **mcp**: Correct zen-mcp-server command path
  ([`a84a94d`](https://github.com/ByronWilliamsCPA/.claude/commit/a84a94df7e2a6356207cfefaaa9e13c1b430ab34))

The zen MCP server configuration was pointing to a non-existent binary
  `/home/byron/dev/zen-mcp-server/zen-mcp-server`. The zen-mcp-server is a Python project that needs
  to be invoked with the Python interpreter.

Changed command to use `.pal_venv/bin/python server.py` which is the correct entry point as
  documented in the project's config examples.

Also enabled project MCP servers in settings.json.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

- **reuse**: Add .trivyignore to REUSE.toml annotations
  ([`47a3ee2`](https://github.com/ByronWilliamsCPA/.claude/commit/47a3ee2e00ceb141942faf3f66c9c05e269ba4c9))

.trivyignore is a security scanning configuration file — add it to the existing dotfile configs
  annotation block alongside .shellcheckrc and .yamllint. Using REUSE.toml (not inline headers) per
  project convention.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **skills**: Add missing workflow bundles for security and quality skills
  ([`0c1e30e`](https://github.com/ByronWilliamsCPA/.claude/commit/0c1e30e6c95971d697a8de2333d90ef4bf00e8c2))

Both skills referenced workflow files that were never committed. Sourced from image_detection
  downstream project (canonical copies).

- security/workflows/: validate-env.md, scan.md, encrypt.md - quality/workflows/: format.md,
  lint.md, naming.md, precommit.md - Fix path references in both SKILL.md files (add workflows/
  prefix)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **skills**: Track testing skill bundle and correct gitignore scope
  ([`b90d85b`](https://github.com/ByronWilliamsCPA/.claude/commit/b90d85b1ed33cf92d72163e94ae5e110f21acea3))

The .gitignore accidentally included .claude/skills/testing/ alongside the eval workspace dirs,
  which prevented the skill's context/ and workflows/ companion files from ever being committed.

- Remove .claude/skills/testing/ from gitignore (keep testing-workspace/ and testing-variant-b/) -
  Add testing/context/pytest-commands.md and pytest-patterns.md - Add testing/workflows/ (generate,
  review, e2e, security, performance) - Add testing/evals/ (evals.json and 4 source files) - Fix
  testing/SKILL.md path references (workflows/ and context/ prefixes)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **sonar**: Correct project keys, source paths, and MCP config
  ([`2f7fe9e`](https://github.com/ByronWilliamsCPA/.claude/commit/2f7fe9eb5b2853560c4590b3b74be2aeea55a844))

- Fix sonar.projectKey: `claude-config` → `ByronWilliamsCPA_.claude` - Fix sonar.sources: `src` →
  `scripts` (src/ doesn't exist in this repo) - Fix check_quality_gate.py default project key - Fix
  interrogate pre-commit hook: `src/` → `scripts/` - Switch MCP sonarqube server from Docker stdio
  to HTTP URL transport (Docker stdio has buffering issues with Java-based MCP servers) - Add
  .sonarlint/connectedMode.json for VS Code Connected Mode sharing

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- **workflows**: Replace org-caller workflows with standalone implementations
  ([`c9a86b4`](https://github.com/ByronWilliamsCPA/.claude/commit/c9a86b412da99c435776efd30a451d0eb1a47eb3))

- Remove .reuse/dep5 to fix conflict with REUSE.toml - Replace ci.yml with standalone pytest,
  basedpyright, ruff, bandit - Replace docs.yml with standalone MkDocs build and gh-deploy - Replace
  release.yml with standalone semantic release workflow - Replace scorecard.yml with standalone
  OpenSSF Scorecard (from homelab_infra) - Replace security-analysis.yml with standalone Bandit and
  Safety scans

Fixes all 7 workflow failures caused by calling non-existent org-level reusable workflows at
  ByronWilliamsCPA/.github/.github/workflows/.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

### Chores

- Align docs and rules with superpowers integration
  ([`6f0e0c0`](https://github.com/ByronWilliamsCPA/.claude/commit/6f0e0c089d64d43d32cc2caacbe21ef14cf1511e))

- CLAUDE.md: fix sync instructions (cp -r → git submodule init), split skills table into custom and
  superpowers sections - AGENTS-AND-SKILLS.md: add project-plan-synthesizer to Planning section, add
  full Superpowers Skills section (14 skills), expand Quick Reference table - Add
  project-plan-synthesizer agent ported from image-preprocessing-detector - git-workflow.md: remove
  inline worktree commands, point to using-git-worktrees and finishing-a-development-branch skills -
  git-worktree.md: slim to when-to-use guidance and reminders, superpowers skills own the command
  detail - supervisor.md: add dispatching-parallel-agents, subagent-driven-development,
  requesting/receiving-code-review, systematic-debugging to assignment table docs: add cookiecutter
  team handoff document

https://claude.ai/code/session_01EQKyt7fqRw1vvAnWMKLN2r

- Clean up template repository structure
  ([`666a97c`](https://github.com/ByronWilliamsCPA/.claude/commit/666a97cb2545bf276288984b048081283420c842))

- Remove cache and generated files (~700K saved) - .ruff_cache/, htmlcov/, .coverage, coverage.xml -
  __pycache__/ and .pytest_cache/ directories

- Remove root duplicate directories (backed up to tmp_cleanup/) - agents/, commands/, context/,
  skills/, templates/ - These should only exist in .claude/ per cookiecutter template

- Sync .claude/ directory from cookiecutter template - Now matches cookiecutter exactly (29 files) -
  Fixed duplicate .github/workflows/.claude/ directory

- Remove Python package source (template repo, not distributable package) - src/claude_config/
  directory removed - src/ directory removed (now empty)

- Remove fuzzing infrastructure (overkill for template) - .clusterfuzzlite/ and fuzz/ directories

- Remove unnecessary CI workflows - publish-pypi.yml (not publishing to PyPI) - mutation-testing.yml
  (expensive, overkill for template) - slsa-provenance.yml (not building artifacts)

- Remove template artifacts - CONFIG_TEMPLATES_SUMMARY.md - SONARQUBE-SETUP.md

- Update pyproject.toml - Add lint exceptions for .claude/**/*.py template files - Allow T201
  (print), C901 (complexity), PLR0912 (branches)

- Add cleanup scripts - scripts/cleanup-template-repo.sh (automated cleanup) -
  scripts/verify-template-consistency.sh (template verification)

All lint checks passing (ruff check . → All checks passed!) Repository now matches cookiecutter
  template structure.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Improve testing skill, add eval artifacts, update gitignore
  ([`db4b6d7`](https://github.com/ByronWilliamsCPA/.claude/commit/db4b6d7ab1824e5d2af5ecf0cfbc4a65e2ed3ea9))

- Add Context Loading Guide to testing/SKILL.md: async mock reminders, file I/O conditional
  tmp_path, httpx/pydantic pre-generation checklists - Add test-coverage and testing eval artifacts
  (evals.json, evals-r3.json) - Update .gitignore: ignore skill workspace/variant-b dirs and
  evals-r2.json iteration artifacts to keep tracked evals clean

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Remove .cruft.json (template source, not generated project)
  ([`014968a`](https://github.com/ByronWilliamsCPA/.claude/commit/014968a4a73edc526761707597b99c78ba5e0fdd))

This repository is the source for Claude configuration files that get pulled into downstream
  projects via cookiecutter, not a project generated FROM the template. Cruft is designed for
  generated projects, not template sources.

Quality assurance strategy: - Manually sync .claude/ updates from/to cookiecutter template - Run
  linters (ruff, qlty) before committing to prevent downstream issues - Maintain consistency by
  copying .claude/ bidirectionally as needed

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Remove A/B test artifacts and untrack tmp_cleanup backup
  ([`d6c1df0`](https://github.com/ByronWilliamsCPA/.claude/commit/d6c1df07b3dae05dcac7d9d1d9f3bb903d0e69a1))

Remove skill variant/workspace eval directories from disk and stop tracking the tmp_cleanup backup
  snapshot that was accidentally committed before the gitignore rule was in place.

- Deleted: .claude/skills/quality-variant-b/, quality-workspace/, testing-variant-b/,
  testing-workspace/, quality/evals/ - Removed stale gitignore entries for testing-workspace/ and
  testing-variant-b/ - Staged deletion of 76 tmp_cleanup/.backup-root-duplicates-* files

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Sync submodule pointers after submodule PRs merged
  ([`b66113f`](https://github.com/ByronWilliamsCPA/.claude/commit/b66113fbecb989292074fa71444701438c4c6d21))

Updates .submodules pointers to the merged main commits for both reference-library and
  image-generation, which landed after the parent PR was merged.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Update submodule pointers for agent frontmatter fixes
  ([`d4e668f`](https://github.com/ByronWilliamsCPA/.claude/commit/d4e668fb198b17b5d21055e1b49824929102b657))

Points reference-library and image-generation submodules to commits that add missing agent
  frontmatter and apply Ruff formatting.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Update submodule references after standalone repo commits
  ([`03f7e97`](https://github.com/ByronWilliamsCPA/.claude/commit/03f7e97b0c43cb1a98f83a8e43c7b5d4389edd53))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **deps**: Update trufflehog hook to v3.92.3
  ([`567734c`](https://github.com/ByronWilliamsCPA/.claude/commit/567734c58e2f6f45668cbe63bf2222df72417805))

- Updated from v3.63.11 to v3.92.3 (fixes Go build compatibility) - Changed to git-based scanning
  (only staged changes, not full filesystem) - Avoids false positives from .venv and other non-repo
  files

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

### Documentation

- Add cookiecutter Claude config removal handoff
  ([`7625d56`](https://github.com/ByronWilliamsCPA/.claude/commit/7625d56dcf8d24259ca73356e5bb40acf12f59bc))

Handoff document for the cookiecutter-python-template team covering the decision to move Claude
  configuration to user-level only, with specific files to remove, docs to update, and cruft merge
  logic to preserve before deleting the merge-standards agent.

https://claude.ai/code/session_01EQKyt7fqRw1vvAnWMKLN2r

- Add design spec for Python 3.10/3.14 compat PostToolUse hook
  ([`a1c0d52`](https://github.com/ByronWilliamsCPA/.claude/commit/a1c0d523a720766931807d37311afc5a6c9a0d1d))

Captures approved two-tier design (grep + AST) for detecting Python version boundary violations
  after Edit/Write tool calls.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add implementation plan for Python 3.10/3.14 compat hook
  ([`8ad35be`](https://github.com/ByronWilliamsCPA/.claude/commit/8ad35be8335cc4f3548bd5cf74afb3e6be44558b))

Four-task plan: test harness, hook script, settings.json wiring, and log verification. Includes
  complete script content and known limitations for parenthesized-with and fromisoformat Z-suffix
  detection.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add manual sync workflow with cookiecutter template
  ([`303fb96`](https://github.com/ByronWilliamsCPA/.claude/commit/303fb96b60778609b1a67a52e65aa2fd11a4e396))

- Documents why cruft is not appropriate for this repository - Provides step-by-step manual sync
  workflows (bidirectional) - Includes quality assurance strategy to prevent downstream issues -
  Covers linting configuration updates and testing procedures - Adds troubleshooting guide and
  regular maintenance checklist

This ensures quality control without cruft's limitations for template source repositories.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Update CLAUDE.md with behavioral rules, skill catalog, and sync instructions
  ([`31f1043`](https://github.com/ByronWilliamsCPA/.claude/commit/31f1043a70b41aa4e2aefff7bc9dbb392bf95e90))

- Add project context, CI compatibility, code quality, testing, and shell sections - Add /sonarcloud
  to skill catalog table - Add sync instructions for downstream projects - Add agent assignment
  patterns for new agents - Update .gitignore for tmp_cleanup/ - Add .claudeignore - Add
  .claude/settings.json with hooks configuration - Add MCP minimal bloat standard

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- **standards**: Add comprehensive testing standards
  ([`dba12d3`](https://github.com/ByronWilliamsCPA/.claude/commit/dba12d3fcbd635dd4e860eeef43da325b73990d1))

Add testing.md covering: - Coverage requirements (80% min, branch coverage) - Test organization
  (unit/integration/e2e structure) - AAA pattern with examples - Fixture strategies (basic, factory,
  async) - Mocking approaches for services and databases - Parametrized and property-based testing -
  Test markers and naming conventions - Pytest configuration for uv-based projects - CI/CD
  integration examples - Mutation testing guidelines

- **standards**: Add test compliance verification system
  ([`bacd804`](https://github.com/ByronWilliamsCPA/.claude/commit/bacd80447cdd428b6c7e9b458302c314d85a6fb9))

Add comprehensive Test Compliance Verification section including: - Directory structure validation
  script - Test marker coverage reporting via pytest hooks - Test ratio enforcement
  (unit:integration:e2e pyramid) - Module coverage audit to find untested modules - CI/CD
  integration with GitHub Actions workflow - Pre-commit hooks for structure and new-code-has-tests -
  Weekly audit report generator - Project type requirements matrix (Library, API, CLI, ML)

- **standards**: Enhance testing standards with comprehensive patterns
  ([`13f77a3`](https://github.com/ByronWilliamsCPA/.claude/commit/13f77a3ebfb16a49c9fcd5c20040a4419c9f7777))

Add new sections based on image-preprocessing-detector patterns: - Core Testing Philosophy with 5
  guiding principles - Security Testing section with CodeQL validation examples and CWE mapping -
  Performance Testing with environment-aware thresholds and timing methodology - Test Data
  Management with storage strategy and fixture organization - Optional Dependency Handling for
  graceful test degradation - Troubleshooting guide for local vs CI failures, coverage gaps, flaky
  tests

Enhanced existing sections: - Directory structure now includes security/, benchmark/, api/
  directories - Added markers: security, requires_full_dataset, real_data - Mutation testing
  expanded with status reference, module targets, prioritization strategy, and allowlist
  documentation

- **standards**: Streamline testing.md, create cookiecutter handoff
  ([`eea4645`](https://github.com/ByronWilliamsCPA/.claude/commit/eea4645607ab80590a07cea430923a1e2cc7cd96))

- Remove test verification tool implementations from testing.md - Keep standards/requirements (what
  to test) in Claude standards - Move implementation tools (how to verify) to cookiecutter handoff -
  Reduce testing.md from ~1400 lines to ~1050 lines

Handoff document includes: - verify_test_structure.py - check_test_ratios.py -
  audit_test_coverage.py - weekly_test_audit.py - GitHub Actions workflow - Pre-commit hooks -
  conftest.py marker tracking

### Features

- Add anthropics skill/plugin submodules with curated symlinks
  ([`c26e7f2`](https://github.com/ByronWilliamsCPA/.claude/commit/c26e7f27413764e9f259e2dc79d00ec626b50499))

Add anthropics/skills and anthropics/claude-plugins-official as submodules. Replace local
  skill-creator with upstream symlink (identical content). Symlink selected skills and agents:

Skills (anthropics/skills): docx, xlsx, pdf, pptx, skill-creator Skills (anthropics-plugins):
  claude-md-improver, session-report, claude-automation-recommender Agents (pr-review-toolkit):
  comment-analyzer, pr-test-analyzer, silent-failure-hunter, type-design-analyzer, code-simplifier,
  pr-toolkit-code-reviewer Commands: /review-pr, /revise-claude-md

Also bring in writing skill, rules/writing.md, and writing-quality.md from pre-existing local work.
  Update AGENTS-AND-SKILLS.md catalog.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Add canonical package registry and move standards under .claude/
  ([`571bc72`](https://github.com/ByronWilliamsCPA/.claude/commit/571bc72aeb8cb9fd1a22f6cf2c6dbc0e000f9f35))

- Add .claude/standards/packages.md: authoritative package registry with canonical choices, AOSS
  markers, override policy, and migration table - Move standards/ → .claude/standards/ for
  consistency with agents/rules/commands/ - Update CLAUDE.md to reference packages standard and sync
  instructions - AOSS markers validated against official supported packages list: arq, hatchling,
  cookiecutter, hypothesis, factory-boy, fakeredis, interrogate, bandit, detect-secrets,
  python-gnupg, opentelemetry-api/sdk, statsmodels, sentence-transformers, dnspython, checkov all
  confirmed AOSS; beautifulsoup4, pyjwt, mkdocs corrected to not-in-AOSS

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add entry and bridge modes to project-planning skill
  ([`7db5373`](https://github.com/ByronWilliamsCPA/.claude/commit/7db53737ba508edcb1c9e8ed343038d404658c4c))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add finishing-a-development-branch chain and phase N+1 offer to phase-gate READY path
  ([`2b1f191`](https://github.com/ByronWilliamsCPA/.claude/commit/2b1f1918f0c88141aaab63ff3ee4443c5752c0eb))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add handoff command, CI lint-fix script, and visual content agent
  ([`24fb334`](https://github.com/ByronWilliamsCPA/.claude/commit/24fb33497256d22384f110df91ecbeda4a46bf95))

- Add handoff command for session continuity documents - Add ci-lint-fix.sh script for CI linting
  automation - Add visual-content-generator agent

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Add planning-bridge-gate PreToolUse hook script
  ([`0098bb0`](https://github.com/ByronWilliamsCPA/.claude/commit/0098bb06055dc5a658e5121dbb707cb070509423))

Adds a bash hook script that intercepts Skill tool calls targeting writing-plans and blocks them
  with exit 2 when a brainstorming spec exists but no ADR or Roadmap has been generated yet. Also
  adds the implementation plan document with proper frontmatter.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add Python 3.10/3.14 compat PostToolUse hook script
  ([`2b3d786`](https://github.com/ByronWilliamsCPA/.claude/commit/2b3d786bd03aed8291d3ea5e2167efb7f5306b51))

Two-tier check: grep for API/import patterns (floor 3.11+, ceiling 3.14) and Python AST scan for
  syntactic patterns (match/case, except*). Degrades gracefully when jq or python3 are unavailable.
  Always exits 0.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Consolidate agent/skill sources via git submodules
  ([`7cc4945`](https://github.com/ByronWilliamsCPA/.claude/commit/7cc494517db6242c060d28fef2b7cc35339a736d))

Replaces machine-specific symlinks and scattered source locations with a portable submodule-based
  structure. All agents and skills now resolve correctly on any machine after a single setup.sh run.

- Add reference-library and image-generation as submodules under .submodules/ - Replace absolute
  symlinks in .claude/agents/ with portable relative paths
  (../../.submodules/<repo>/agents/<file>.md) - Move visual-content-generator.md from root agents/
  into .claude/agents/ - Move skill-creator from .agents/ into .claude/skills/ (no longer
  hidden/untracked) - Add setup.sh to bootstrap ~/.claude/ symlinks including
  ~/.claude/reference-library for stable {{LIBRARY_PATH}} resolution without file substitution -
  Rewrite .claude/README.md with accurate architecture, invariants, and runbooks for adding agents,
  skills, and submodules - Exclude skill-creator (third-party tool) from darglint docstring checks

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Delegate security/coverage in phase-reviewer, add RAD assumption gate
  ([`4944629`](https://github.com/ByronWilliamsCPA/.claude/commit/494462995f641c7e3c533a723c6be1e172981adf))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Expand phase-gate plan mode with worktree setup and execution dispatch
  ([`7dd88a7`](https://github.com/ByronWilliamsCPA/.claude/commit/7dd88a7f442a3cb93f9c4386763936108147dd66))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Integrate superpowers as submodule with skill symlinks
  ([`06e7779`](https://github.com/ByronWilliamsCPA/.claude/commit/06e7779e468a430bba034f36c1e40e7f7e3c5e3c))

Add obra/superpowers as a git submodule at .submodules/superpowers. Symlink all 14 superpowers
  skills into .claude/skills/ following the existing pattern used for reference-library and
  image-generation.

Adds SessionStart hook entry to settings.json so superpowers injects the using-superpowers
  meta-skill at session start alongside the existing keyword-tool-trigger reset.

Skills added via symlink: - brainstorming, writing-plans, executing-plans -
  subagent-driven-development, requesting-code-review, receiving-code-review
  test-driven-development, systematic-debugging, verification-before-completion -
  dispatching-parallel-agents, using-git-worktrees, finishing-a-development-branch - writing-skills,
  using-superpowers

After pulling, run: git submodule update --init --recursive

https://claude.ai/code/session_01EQKyt7fqRw1vvAnWMKLN2r

- Migrate Claude Code configuration from williaby/.claude
  ([`843f85a`](https://github.com/ByronWilliamsCPA/.claude/commit/843f85a5117eeb2115215f08eb3f71a89c9ce9aa))

Migrate all configuration files and directories from the original williaby/.claude repository to the
  new ByronWilliamsCPA/.claude structure generated from the cookiecutter Python template.

Migrated content: - agents/ - 22 agent definitions for Claude Code - commands/ - 14 slash commands
  for quality, security, testing - context/ - 3 context files for development standards docs/ - 7
  documentation files including setup guides - mcp/ - MCP server configurations and examples -
  skills/ - 5 skill directories (git, quality, rad, security, testing) - standards/ - 5 development
  standard files - templates/ - 2 project templates - tests/ - BATS test suite for setup scripts

Configuration files: - CLAUDE.md - Global Claude Code development standards - settings.json - Claude
  Code settings - .mcp.json - MCP server configuration - SECURITY.md - Security policy

This provides a proper repository structure with: - Cruft template tracking for updates - Pre-commit
  hooks and quality tooling - MkDocs documentation infrastructure - GitHub Actions CI/CD workflows -
  Semantic release automation

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Update bridge mode with synthesizer, phase selection, and scoped writing-plans handoff
  ([`70c643a`](https://github.com/ByronWilliamsCPA/.claude/commit/70c643a4430062b2798c8d9e83264f3bccffd744))

- **mcp**: Implement tiered MCP tool loading strategy
  ([`fb43a63`](https://github.com/ByronWilliamsCPA/.claude/commit/fb43a63e308900204c8393d72e5c24a0529523ee))

Based on Anthropic's Advanced Tool Use Guide, implement a 3-tier loading strategy to reduce context
  consumption by 85-95%:

Tier 1 (Always Loaded - ~3K tokens): - zen: thinkdeep, codereview, tiered_consensus, chat -
  context7: resolve_library_id, get_library_docs - github: get_file_contents

Tier 2 (Agent/Skill Bundled): - Tools loaded when specific agents invoked via Task tool - Updated 10
  agent definitions with mcp_tools frontmatter

Tier 3 (Keyword Triggered): - Docker, Playwright, Postgres, Sentry, Mermaid tools - Loaded based on
  keyword detection in user prompts

Changes: - Add mcp/mcp_config.yaml with full tiered configuration - Add scripts/mcp-tool-loader.sh
  for agent tool loading - Add scripts/keyword-tool-trigger.sh for keyword detection - Add
  scripts/track-mcp-usage.sh for usage analytics - Update settings.json with new hooks - Update
  CLAUDE.md with MCP strategy documentation - Update agent definitions with mcp_tools bundles

Removed: sequentialthinking (redundant with zen.thinkdeep)

- **security**: Add OWASP specialist agents and dispatch system
  ([`2cb6a25`](https://github.com/ByronWilliamsCPA/.claude/commit/2cb6a25c474a0f15ecf754e99f97aec15926ebd7))

- Add owasp-dispatch agent to route to 6 OWASP specialists - Add owasp-web, owasp-api, owasp-llm,
  owasp-ml, owasp-citizen, owasp-agent - Update security-auditor agent - Add OWASP specialist agents
  specification

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- **skill**: Add /sonarcloud skill for issue review and setup diagnostics
  ([`ac77977`](https://github.com/ByronWilliamsCPA/.claude/commit/ac77977cefdf6f599b7c9e377170b7665c552989))

New skill providing SonarCloud integration via MCP servers: - Auto-detects project org/key from
  workspace config files - Routes to correct MCP server (byronwilliamscpa:8090, williaby:8091) -
  Modes: summary, issues, fix, gate, rule, analyze, check - Check mode validates full setup: Docker,
  config consistency, remote access - Documents SonarSource product naming (SonarLint→SonarQube for
  IDE, etc.) - Includes ecosystem data flow diagram and VS Code integration points

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- **skill**: Add phase-gate skill with reviewer, validator, and analyzer agents
  ([`ae01e22`](https://github.com/ByronWilliamsCPA/.claude/commit/ae01e2218e9e484f64727c9e4049f343cf3436ce))

- Add phase-gate skill for phase readiness evaluation with quality gates - Add phase-reviewer agent
  for quality gate execution - Add plan-validator agent for implementation plan validation - Add
  scope-analyzer agent for scope completion analysis

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- **skills**: Update skill-creator eval scripts and testing eval fixtures
  ([`05a212b`](https://github.com/ByronWilliamsCPA/.claude/commit/05a212b9d6df9a6115d5d338757f405b32b947b3))

Improve skill evaluation infrastructure across skill-creator, test-coverage, and testing skills.

- skill-creator: significant enhancements to eval loop, report generation, benchmark aggregation,
  review generation, description improvement, package script, quick validation, and shared utils
  test-coverage: update parse_coverage.py script

- testing/evals: update validators.py and weak_tests.py eval fixtures - .gitignore: add
  docs/content_reviews/ to ignored paths

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **standards**: Add code generation principles and migrate Black to Ruff
  ([`5533d7d`](https://github.com/ByronWilliamsCPA/.claude/commit/5533d7df7c100f4f15a5338c9621f6b746002059))

Add comprehensive code generation principles to CLAUDE.md: - Function structure: length limits
  (20-60 preferred, 100 max), single responsibility, early returns, nesting depth (≤3) - Complexity
  controls: cyclomatic (≤10), branches (≤12), cognitive load - Code duplication: zero tolerance,
  rule of three, template patterns - Data & state design: immutability, pure functions, no global
  state, parameter grouping with dataclasses - Naming standards: descriptive variables, verb-based
  functions, boolean prefixes - Documentation requirements: docstrings, inline comments, type hints

Replace Black references with Ruff format across all standards: - CLAUDE.md: Update essential
  requirements and commands - standards/python.md: Update formatting and linting sections -
  standards/linting.md: Update configuration, pre-commit, CI/CD, VS Code settings, and workflow
  examples

This aligns with template-sample repo which uses Ruff for both formatting and linting
  (Black-compatible output).

- **testing**: Add test agents, coverage skill, and updated standards
  ([`7df51ed`](https://github.com/ByronWilliamsCPA/.claude/commit/7df51ed4189e55210ef69cd3a0ba8468801573cd))

- Add test-writer agent for coverage-driven iterative test generation - Add test-reviewer agent for
  test quality validation (APPROVE/NEEDS_WORK) - Add test-coverage skill with analyze, generate, and
  enforce modes - Add debug-tests command for root-cause-first failure analysis - Add testing guide
  and testing patterns context - Update testing standards and commands - Add test-coverage agent
  specification

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Refactoring

- Improve code quality across repository
  ([`7da3442`](https://github.com/ByronWilliamsCPA/.claude/commit/7da344271e05feca57b88608be75afb8a69a39a2))

- Fix Ruff linting errors in noxfile.py (use contextlib.suppress) - Auto-format code with ruff
  format (7 files reformatted) - Add MCP server configurations for Tier 2/3 on-demand loading - Add
  environment variable template (.env.mcp.example) - Update settings.json with Tier 1 MCP servers -
  Configure playwright, postgres, sentry, docker, mermaid, uml MCP servers

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Improve code quality across repository
  ([`7e766d4`](https://github.com/ByronWilliamsCPA/.claude/commit/7e766d4b3a629d00121e9f4e920a6fff321318a2))

1. Fix scripts/check_quality_gate.py: - Replace Optional[str] with str | None (Python 3.10+ syntax)
  - Add noqa comments for S310 (URL scheme already validated)

2. Enhance src/claude_config/__init__.py: - Export Settings, get_logger, log_performance,
  setup_logging - Add docstring example showing common usage pattern - Sort __all__ alphabetically
  per RUF022

3. Reorganize tests into proper structure: - Move tests from test_example.py to unit/ and
  integration/ - tests/unit/test_package.py - package initialization tests -
  tests/unit/test_settings.py - Settings class tests - tests/unit/test_logging.py - logging
  utilities tests - tests/integration/test_integration.py - integration tests - Add new test for
  public API exports

4. Fix documentation front matter: - Add missing tags to docs/_data/tags.yml (api, home, overview,
  etc.) - Remove redundant H1 headers from 15+ docs files - Add front matter to
  PROJECT-ORGANIZATION-GUIDE.md

All checks pass: - Tests: 15 passed with 97.67% coverage - Ruff linting: All checks passed -
  BasedPyright: 0 errors

- Migrate commands to skills and align with Anthropic best practices
  ([`ebf3faa`](https://github.com/ByronWilliamsCPA/.claude/commit/ebf3faa31706c3ec02ecb2a7f86cfb0d7c200dc8))

- Consolidate commit-prepare and pr-prepare into git skill bundle (git/workflows/commit.md,
  git/workflows/pr.md, git/context/) preserving all org-level requirements: HEREDOC pattern,
  attribution, safety rules, breaking change format, CodeRabbit integration - Migrate all 7 commands
  to skills: quality, testing, security promoted in-place; debug-tests and handoff promoted to new
  bundled skills; pr and plan deleted as exact duplicates of existing skills - Create .claude/rules/
  with 5 path-scoped files: python.md, git-workflow.md, pre-commit.md, mcp-strategy.md,
  supervisor.md - Trim CLAUDE.md from 866 to 196 lines; rules/ files carry the detail - Add
  user-invocable: false to scope-analyzer and plan-validator agents - Update sync instructions to
  include rules/ for downstream projects

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
