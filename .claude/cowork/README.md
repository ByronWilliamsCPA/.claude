# Cowork Instructions

This directory holds paste-in instructions for Claude Cowork and related Claude surfaces, compressed from the rules files under `.claude/rules/` and `.claude/standards/`.

## Files

- `profile.md`: paste into Settings → Profile. Applies to all Claude surfaces (chat, Cowork, Desktop).
- `cowork.md`: paste into Settings → Cowork → Instructions. Applies only to Cowork sessions, stacks on Profile.
- `folder-template.md`: copy into each Cowork work folder as `CLAUDE-FOLDER.md` and fill in placeholders. Applies only when that folder is the active context.
- `sources.md`: traceability table mapping each section of profile.md and cowork.md back to its source rule file.

## Why three layers

Profile applies everywhere at token cost on every turn. Keep it lean and universal. Cowork adds operational rules (file safety, done framing, Word and Excel conventions) that only matter in Cowork. Folder adds project-specific context that only applies when that folder is active. This keeps per-turn token cost proportional to what each scope actually needs.

## Updating

When you edit a source file in `.claude/rules/`, consult `sources.md` to find which target sections depend on it. Re-compress the affected sections, paste the updated content into the matching Cowork settings field, and commit the updated files here so the repo stays authoritative.

## Future migration (v2)

Dense content (writing rules, Word and Excel conventions) will eventually move into Cowork Skills, which auto-load only when relevant file types are touched. The paste-in fields then shrink to just communication posture and safety rules. For now, the paste-in approach ships working instructions with a clear maintenance story.

## Word count budget

Profile and Cowork target under 500 words per field, per Anthropic best practice for custom instructions. Current targets:

- profile.md: about 300 words
- cowork.md: about 350 words
- folder-template.md: about 220 words (most of which are placeholders)

## Scope of this v1

Covers Word and Excel document work. Browser research lives in Claude for Chrome. Coding lives in Claude Code. If Cowork expands into browser or code work, add a new section or skill rather than stretching these files.
