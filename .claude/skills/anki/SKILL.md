---
name: anki
description: Turn a distilled lecture summary into 10-15 Anki cards and push them into the live collection over AnkiConnect. Writes a reviewable markdown card file first, pushes only after it is marked approved, and checks for near-duplicates before adding. Triggers on anki, anki cards, make cards, flashcards, lecture notes to cards, push cards, card batch, apkg backup.
user-invocable: true
tools: ["Read", "Write", "Edit", "Bash", "Glob"]
---

# Anki Card Pipeline

Picks up where the note-distillation step leaves off: a half-page distilled
lecture summary goes in, cards come out in the right course deck.

**Operator: Ariannah.** She runs this herself on her own laptop. See
`context/operating-model.md` before proposing any change to who runs what.

## Invocation

```text
/anki <path-or-pasted-summary>     # draft cards from a distilled summary
/anki push <card-file>             # push an approved card file
/anki backup                       # write an .apkg snapshot
```

## The two-stage gate

Card generation and card pushing are deliberately separate steps, with a human
read in between.

1. **Draft.** Cards are written to a markdown file with `status: draft`.
2. **Review.** Ariannah reads them, fixes anything wrong or vague, and changes
   the status line to `approved`.
3. **Push.** `anki-cards push` refuses any file still marked `draft`.

Never edit `status` to `approved` on her behalf, and never push a file you
drafted in the same turn without her having read it. The editing pass is where
the learning happens; skipping it defeats the point of the pipeline.

## Drafting cards

Read the distilled summary, then create the file:

```bash
anki-cards new <course-slug> <term-slug> "<Lecture Title>"
```

This creates `<course>/<term>/<YYYY-MM-DD>-<lecture-slug>.md` under the
card-source root with correct frontmatter and an empty card list. Fill in the
cards with Edit, following the rules below, then run:

```bash
anki-cards validate <card-file>
```

### Card rules

- **10-15 cards per lecture.** Not more. The push command refuses a batch over
  15 because daily review has to stay inside 20-30 minutes; FSRS handles the
  scheduling but it cannot rescue an over-stuffed deck.
- **One fact per card.** If a card needs the word "and", it is probably two
  cards.
- **No walls of text.** A question should be one line. An answer should be a
  term, a number, or one short sentence.
- **Cloze deletions for processes, pathways and sequences.** Anything with an
  order or a set of coupled parts belongs in a cloze, not a Q/A pair.
- **Q/A for discrete facts.** Definitions, values, one-to-one mappings.
- **Images for structures.** Anatomy, histology, and organic structures do not
  survive as text. Note where an image is needed in the `Extra` field and let
  her paste it in Anki; this pipeline does not fetch or embed images.
- **Her vocabulary, not the textbook's.** Cards phrased the way the lecture
  phrased it recall better than cards phrased the way a summary generator would.

Card file format, including both card kinds, is in
`context/card-file-format.md`.

## Pushing

```bash
anki-cards check                  # confirm Anki is running first
anki-cards push <card-file> --dry-run
anki-cards push <card-file>
```

`check` must pass before a push is attempted. Anki Desktop has to be open with
the AnkiConnect add-on installed (code `2055492159`); there is no headless mode
and AnkiWeb is a sync service, not an API. If `check` fails, print its message
and stop; do not retry or work around it.

`push` checks each card against the destination deck and against the rest of
the batch, and skips near-duplicates rather than adding them. It reports every
skip with a similarity score. Only pass `--force-duplicates` if she looks at
the reported matches and says they are genuinely different cards.

`--allow-overflow` is separate from `--force-duplicates` on purpose. Waving
through a duplicate must not quietly raise the card cap.

A successful push triggers an AnkiWeb sync so the cards reach her phone.

## Backup

Two layers, already decided; do not redesign them:

- **AnkiWeb** handles live multi-device sync.
- **The card-source git repo** is the durable, human-readable history. Every
  batch is a commit. It is a separate private repo, never this one: this repo
  is public and her course list and study record are not for publishing.

The `.apkg` export is a third restore path that depends on neither:

```bash
anki-cards export --dest "$ANKI_EXPORT_DIR"
```

## Committing a batch

After a successful push, commit the card file in the card-source repo so the
run is recorded:

```bash
cd "$ANKI_SOURCE_ROOT"
git add <card-file>
git commit -S -m "cards(<course>): <lecture title>"
```

One pipeline run, one commit. Do not batch several lectures into one commit;
the per-lecture history is what makes a bad batch easy to find and revert.

## Setup

First-run configuration, including the three environment variables and how to
create the card-source repo, is in `context/setup.md`.
