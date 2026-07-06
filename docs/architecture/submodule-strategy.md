---
title: "Submodule Strategy"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Narrative description of how git submodules integrate external capabilities into the repo, the trust level of each, and the admission bar for new ones."
tags:
  - architecture
  - submodules
  - technical
---

The repo extends Claude's capabilities by incorporating external trees as git
submodules under `.submodules/`. Each submodule is a separately maintained
upstream repository, pinned to a specific commit (the gitlink). `setup.sh`
wires them into the runtime config (`~/.claude/`) via symlinks, making them
first-class citizens of the Claude Code install without vendor-copying their
contents.

For the reasoning behind this design, see
[ADR-005](adr/ADR-005-submodule-extension-model.md).

`.gitmodules` is the authoritative submodule list. The inventory table below
must cover every entry in it; `tests/unit/test_submodule_strategy_sync.py`
fails CI when the two disagree on paths or upstream slugs.

## Submodule Inventory

| Submodule path | Upstream | What it provides | Wiring into runtime | Trust level |
| --- | --- | --- | --- | --- |
| `.submodules/reference-library/` | `ByronWilliamsCPA/reference-library` | Agent prompt templates using `{{LIBRARY_PATH}}` placeholders | Symlinked whole at `~/.claude/reference-library/`; writing-pipeline agents symlinked into `.claude/agents/` | First-party (same maintainer) |
| `.submodules/image-generation/` | `williaby/image-generation` | Agents and utilities for image generation workflows | `diagram-specialist` agent symlinked into `.claude/agents/` | First-party (same maintainer) |
| `.submodules/superpowers/` | `obra/superpowers` | Community skills: brainstorming, TDD, systematic debugging, plan execution, review patterns | Selected skills symlinked into `.claude/skills/`; several others maintained as deliberate local forks | Third-party, reviewed; see [skills deep dive](../tool-evals/skills-deep-dive-2026-06.md) |
| `.submodules/anthropics-skills/` | `anthropics/skills` | Official Anthropic skill collection | docx, pdf, pptx, xlsx, skill-creator symlinked into `.claude/skills/` (document skills are symlink-only for license reasons) | Vendor (Anthropic) |
| `.submodules/anthropics-plugins/` | `anthropics/claude-plugins-official` | hookify plugin engine, security-guidance hooks, pr-review-toolkit agents, several skills | Hook scripts referenced by absolute path from `hooks.json`; selected skills symlinked into `.claude/skills/` and agents into `.claude/agents/` | Vendor (Anthropic) |
| `.submodules/one-skill-to-rule-them-all/` | `rebelytics/one-skill-to-rule-them-all` | Upstream source of the task-observer meta-skill | Not in the load path directly: `scripts/apply-task-observer-patches.sh` builds `.claude/skills/task-observer/SKILL.md` from it | Third-party, reviewed at admission (2026-04-28, pin `b6b6954`); full integration design in [task-observer design](../superpowers/specs/2026-04-28-task-observer-design.md) |
| `.submodules/jeffallan-claude-skills/` | `Jeffallan/claude-skills` | Community skill collection (66 skills at the reviewed pin); only `fastapi-expert` is consumed | One skill symlinked: `.claude/skills/fastapi-expert`; local delta in first-party `.claude/skills/fastapi-expert-extras/` | Third-party, reviewed at pin `5e8b6b8` (2026-07-06); see adjudication below |
| `.submodules/agents-observe/` | `simple10/agents-observe` | Per-subagent token attribution dashboard (Claude Code plugin) | Directory-source marketplace plugin in `settings.json` (`extraKnownMarketplaces` plus `enabledPlugins`); queried by the `usage-report` skill via REST | Third-party, security-reviewed at v0.9.11, PASS with required guardrails; see [usage monitoring survey](../reference/usage-monitoring-survey.md) and [hooks reference](../reference/hooks.md) |

## Trust Adjudications (2026-07-06)

The three submodules added after the original five-entry table each carry an
explicit trust decision.

### `one-skill-to-rule-them-all`

Adjudicated at admission (2026-04-28, the approved integration design below;
pin `b6b6954` as of 2026-07-06). The approved integration design
([2026-04-28-task-observer-design.md](../superpowers/specs/2026-04-28-task-observer-design.md))
treats the submodule as a tracked upstream source, never loaded directly: a
patch script applies three documented transformations and writes the result to
`~/.claude/skills/task-observer/SKILL.md`. Upstream updates re-run the patch
script, so every content change passes through a diff the maintainer sees.
CC BY 4.0 attribution passes through verbatim.

### `jeffallan-claude-skills`

Adjudicated 2026-07-06 at pin `5e8b6b8` (tag `v0.4.14` plus one docs-site-only
commit that does not touch skill content). Findings:

- `fastapi-expert` (the only wired skill: `SKILL.md` plus six reference files,
  about 1,900 lines total) is benign instructional FastAPI content. No tool
  directives beyond running `pytest`, no network calls, no embedded
  instructions targeting the host session. One quality wart (invalid
  `model_config` usage in the minimal example) noted; quality, not trust.
- `.claude/skills/fastapi-expert-extras/` is first-party: a local delta
  built from this repo's own observations, layered on the vendored skill.
  Verified 2026-07-06.
- The upstream repo carries a `CLAUDE.md` at its root. Folder-scoped
  instruction files inside submodules load into any session that reads a file
  under them, so that file is part of the reviewed surface (see admission bar
  item 3). Reviewed at pin: benign authoring conventions for the upstream
  repo itself.
- Snyk attributes 31 npm vulnerabilities to this submodule's
  `site/package.json`. That is the upstream docs-site build, never executed
  here; tracked as not-owned in the
  [Snyk findings inventory](../security/snyk-findings-inventory-2026-06-28.md).

Verdict: keep the symlink. Re-review the wired skill directory and the
upstream instruction files on every pin bump.

### `agents-observe`

Adjudicated at admission (2026-06-11). The submodule is the install mechanism:
`settings.json` registers it as a directory-source marketplace plugin, so the
checked-out working tree is what runs. The full security review (verdict: PASS
with required guardrails, including unredacted tool-input persistence and an
unauthenticated `0.0.0.0` port bind mitigated by WSL2 NAT, a
host-topology-specific mitigation to re-verify on any non-WSL2 deployment)
lives in the
[usage monitoring survey](../reference/usage-monitoring-survey.md); the
hook-composition analysis (28 events, fire-and-forget wrapper verified unable
to block tool calls at v0.9.11) lives in the
[hooks reference](../reference/hooks.md). Do not run `claude plugin update`
or bump the pin without re-running that security review.

## Submodule Admission Bar

A new submodule (or a pin bump to an existing one) must clear the following
before merge. The bar exists because submodule content wired into
`.claude/skills/`, `hooks.json`, or `settings.json` is executable-instruction
supply chain: it runs inside sessions with the session's full tool access.

1. **Pin to a reviewed commit.** Prefer a release tag; record the commit and
   review date in the inventory table. The gitlink is the pin of record.
2. **Content review at the pin** for everything wired into an instruction or
   execution path: skill bodies and their reference files, hook scripts,
   plugin hook registrations. Look for tool directives, network calls, and
   instructions addressed to the host session rather than the end user.
3. **Instruction-file review.** Read the submodule's `CLAUDE.md`, `AGENTS.md`,
   and `GEMINI.md` (root and nested) at the pin. These load into any session
   that reads a file under the submodule, whether or not the submodule is
   otherwise wired in. For a submodule wired as a plugin (marketplace or
   directory source), the auto-load surface is wider: also review its
   `.mcp.json` (auto-registers MCP servers), the `.claude-plugin/plugin.json`
   marketplace manifest (controls what the plugin discovers and exposes), and
   any `commands/`, `agents/`, or `skills/` content the manifest wires in.
4. **Wiring statement.** The inventory table row must say how the submodule
   reaches `~/.claude/` (symlink, hook path, plugin marketplace, build
   artifact) or state explicitly that it is inert.
5. **Same-PR documentation.** The PR that adds the submodule updates the
   inventory table; `tests/unit/test_submodule_strategy_sync.py` enforces
   coverage of every `.gitmodules` entry.
6. **Re-review on bump.** At minimum, diff the wired paths and instruction
   files between the old and new pins. Submodules with a dedicated security
   review (currently `agents-observe`) require that review to be re-run, not
   only a diff.

`#CRITICAL` Symlinks and directory-source plugins read the submodule working
tree, not the pinned gitlink. A manual checkout inside a submodule silently
floats the reviewed version, and so do uncommitted edits to files inside the
submodule tree, which `git submodule status` cannot see (its `+` prefix
tracks only the checked-out commit). `#VERIFY` after any submodule
operation, both of: `git submodule status` shows no `+` prefix (checked-out
commit matches the gitlink), and `git -C .submodules/<name> status
--porcelain` prints nothing (no modified or untracked content), before
trusting wired content.

## How `setup.sh` Wires Them

Each submodule under `.submodules/` is populated by:

```bash
git submodule update --init --recursive
```

`setup.sh` runs this automatically if the submodules have not been initialized (checked by looking for a sentinel file in `reference-library`).

After initialization, `setup.sh` creates one additional symlink beyond the standard set:

```bash
~/.claude/reference-library/ → ~/dev/.claude/.submodules/reference-library/
```

This makes the reference library accessible at `~/.claude/reference-library/`, which is the path the `{{LIBRARY_PATH}}` placeholder resolves to. Agents in the reference library reference each other using that placeholder; resolving it to `~/.claude/reference-library` lets them work without hardcoded paths.

The skill-collection submodules (`superpowers`, `anthropics-skills`, `anthropics-plugins`, `jeffallan-claude-skills`, and `image-generation` for agents) are reached via per-item symlinks in `.claude/skills/` and `.claude/agents/`: the submodule content itself is not automatically in the skill load path, only what is deliberately symlinked in.

`anthropics-plugins` hook scripts are not symlinked into `~/.claude/`. The hook entries in `hooks.json` reference them directly by absolute path:

```bash
$HOME/dev/.claude/.submodules/anthropics-plugins/plugins/hookify/...
```

This keeps the plugin engine out of the user-visible `~/.claude/` namespace while making it accessible to the hook pipeline.

`one-skill-to-rule-them-all` and `agents-observe` are wired by mechanisms of their own, described in their adjudication sections above (patch-script build artifact and plugin marketplace respectively).

## Upstream Update Flow

To pull upstream changes from any submodule:

```bash
cd ~/dev/.claude
git submodule update --remote --merge .submodules/<name>
git add .submodules/<name>
git commit -m "chore(submodules): update <name> to latest upstream"
```

Run `./setup.sh` afterward if the submodule added new content that needs to be symlinked (e.g., new skills that reference a different path).

To update all submodules at once:

```bash
git submodule update --remote --merge
```

Review diffs carefully before committing, applying admission bar item 6 above. Upstream changes can include breaking changes to hook scripts (in `anthropics-plugins`), new skill triggers (in `superpowers`), or changed instruction files (any submodule) that conflict with existing configuration.

Pay specific attention to any `hooks/hooks.json` file in the diff. Some of these trees exist twice on this machine: `superpowers` is both a submodule here and an installed plugin, and it is the plugin cache copy (`~/.claude/plugins/cache/superpowers-dev/superpowers/<version>/`) that Claude Code actually executes, so reviewing the submodule diff alone does not cover the running copy. The same applies to `hookify`, which is currently wired from both the submodule path (via `hooks.json`) and its enabled plugin cache. After updating a submodule or a plugin (`claude plugin update`), run the hook-source drift check; if a hook event, matcher, or command changed, the check fails until the change is reviewed and `hook-inventory.json` is updated in the same commit. See [Hook Pipeline → Hook Sources](hook-pipeline.md#hook-sources) and [ADR-010](adr/ADR-010-hook-source-allowlist.md).

To verify nothing broke after an update:

```bash
./setup.sh --doctor       # includes scripts/check-hook-sources.sh
uv run pytest
uv run mkdocs build
```

## The `{{LIBRARY_PATH}}` Convention

Agent templates in `reference-library` use `{{LIBRARY_PATH}}` as a placeholder for the path where the library is installed. When using these templates, substitute `~/.claude/reference-library`:

```text
{{LIBRARY_PATH}} → ~/.claude/reference-library
```

`setup.sh` prints a reminder about this at the end of every run. Automated substitution tooling is a candidate for a future improvement.

## See Also

- [ADR-005 Submodule Extension Model](adr/ADR-005-submodule-extension-model.md): why submodules over vendoring or packaging
- [Install Model](install-model.md): how `setup.sh` creates the symlink topology
- [Hook Pipeline](hook-pipeline.md): how `anthropics-plugins/hookify` is used by the hook system
- [Task Observer Integration Design](../superpowers/specs/2026-04-28-task-observer-design.md): the `one-skill-to-rule-them-all` adjudication
- [Usage Monitoring Survey](../reference/usage-monitoring-survey.md): the `agents-observe` security review
- [Skills Deep Dive 2026-06](../tool-evals/skills-deep-dive-2026-06.md): per-repo verdicts on the skill-collection submodules
- `.gitmodules`: the authoritative submodule list with upstream URLs
