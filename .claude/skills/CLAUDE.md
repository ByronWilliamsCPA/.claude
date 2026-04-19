# Skills Authoring Conventions

> Folder-level override: applies when editing files under `.claude/skills/`.
> Last scope wins: these rules take precedence over the global CLAUDE.md.

## Structure

Every skill lives in `.claude/skills/<skill-name>/SKILL.md`. Optional subdirectories:
`workflows/`, `context/`, `evals/`, `scripts/`.

Keep `SKILL.md` under 200 lines. Move detail into `workflows/` or `context/` files.

## Key rules

- Skills do not invoke agents. Agents invoke skills. (ADR-004)
- Stateless design: same input produces same output, no cross-invocation state.
- Pattern A (agent-preloaded) vs Pattern B (tool-invoked): see `.claude/rules/supervisor.md`.
- Set `user-invocable: false` for Pattern A skills to prevent accidental slash-command use.
- Workflow files named `<verb>-<noun>.md`; context files are read-only reference material.

## Registration

After creating a skill: add it to `AGENTS-AND-SKILLS.md` and run `pre-commit run --all-files`.
