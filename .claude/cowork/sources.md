# Cowork Content Sources

Traceability between Cowork paste-in files and their source rules. When a source file changes, find the affected target rows below and re-compress the corresponding sections.

## Mapping

| Target file | Section | Source |
|---|---|---|
| profile.md | Punctuation | `.claude/rules/writing.md` § Punctuation |
| profile.md | Grammar | `.claude/rules/writing.md` § Grammar Authority |
| profile.md | Banned terms | `.claude/rules/writing.md` § AI Pattern Avoidance |
| profile.md | Structural tells to avoid | `.claude/rules/writing.md` § Structural Tells to Avoid |
| profile.md | Quantification | `.claude/rules/writing.md` § Quantification Over Vagueness |
| profile.md | Communication | `~/.claude/CLAUDE.md` global + session-level style guidance |
| cowork.md | File safety | Anthropic Cowork research (external) |
| cowork.md | Task framing | Anthropic Cowork research (external) |
| cowork.md | Word documents | `.claude/rules/writing.md` § Structural Tells + Anthropic Cowork research |
| cowork.md | Excel workbooks | Anthropic Cowork research + general best practice |
| cowork.md | Citations | `.claude/standards/writing-quality.md` § Stage 2 factual accuracy |

## Update workflow

1. Edit source file in `.claude/rules/` or `.claude/standards/`
2. Look up the target rows in the table above
3. Re-compress the affected sections in `profile.md` or `cowork.md`
4. Paste the updated file content into the matching Cowork settings field
5. Commit the updated files in `.claude/cowork/`

## External sources

Sections marked "Anthropic Cowork research" are not drawn from this repo. They come from Anthropic's Cowork documentation and community guides. When Anthropic updates Cowork guidance, review these sections separately. Primary references:

- [Get started with Claude Cowork — Anthropic Help Center](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork)
- [Use Skills in Claude — Anthropic Help Center](https://support.claude.com/en/articles/12512180-use-skills-in-claude)
- [Claude Cowork product page — Anthropic](https://www.anthropic.com/product/claude-cowork)
