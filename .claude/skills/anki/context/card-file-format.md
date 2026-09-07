# Card File Format

One markdown file per lecture, stored under the card-source repo's `cards/`
folder as `cards/<course>/<term>/<YYYY-MM-DD>-<lecture>.md`. YAML frontmatter,
then `## Card N` blocks.

```markdown
---
course: bisc-220
term: fall-2026
lecture: Glycolysis Regulation
date: 2026-09-02
deck: Ariannah::bisc-220::fall-2026
tags: [bisc-220, metabolism]
status: draft
---

<!-- Read every card. Fix anything that is wrong or vague.
     When you are happy with them, change status above to: approved -->

## Card 1
**Q:** Which enzyme catalyzes the rate-limiting step of glycolysis?
**A:** Phosphofructokinase-1

## Card 2
**Cloze:** PFK-1 is activated by {{c1::AMP}} and inhibited by {{c2::ATP}}.
**Extra:** Allosteric regulation, not covalent modification.

## Card 3
**Q:** Which structure is labelled here?
**A:** Loop of Henle
**Extra:** NEEDS IMAGE: nephron diagram, lecture 4 slide 12.
```

## Frontmatter keys

| Key | Required | Notes |
| --- | --- | --- |
| `course` | yes | Slug. Becomes the first path segment. |
| `term` | yes | Slug. Becomes the second path segment. |
| `lecture` | yes | Human title. Slugified into the filename. |
| `date` | yes | ISO `YYYY-MM-DD`. Prefixes the filename and orders the term. |
| `deck` | yes | Full Anki deck path, `::` separated. Created if missing. |
| `tags` | no | Applied to every card in the batch. |
| `status` | no | `draft` (default) or `approved`. Push refuses `draft`. |

## Card blocks

- A heading starting `##` opens a new card. Text before the first heading is
  ignored, so notes-to-self at the top of the file are safe.
- Fields are `**Label:** value`. A value may run onto following lines; it ends
  at the next `**Label:**` or at the end of the block.
- `**Q:**` / `**A:**` (or `**Question:**` / `**Answer:**`) make a Basic note.
- `**Cloze:**` (or `**Text:**`) makes a Cloze note.
- A `**Q:**` containing a `{{c1::...}}` marker and no answer is treated as a
  cloze, so a card rewritten in place does not need its label changed.
- `**Extra:**` is optional. On a Basic card it is appended to the answer in
  italics; on a Cloze card it becomes `Back Extra`.

## Images

The pipeline does not fetch or embed images. Write
`NEEDS IMAGE: <what and where>` in the `Extra` field and paste the image into
the note in Anki after the push. Structures (anatomy, histology, organic
chemistry) do not survive as text, so a text-only card for one of those is
worse than no card.

## What the tooling checks

- 10-15 cards. Over 15 is refused; under 10 warns and proceeds.
- Every block parses into a complete card.
- No card closely repeats another card in the same batch.
- No card closely repeats a note already in the destination deck.
