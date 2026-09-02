# First-Run Setup

Done once per machine. All three steps are needed before the first push.

## 1. Anki Desktop and AnkiConnect

1. Install Anki Desktop and sign in to AnkiWeb (free tier).
2. Tools > Add-ons > Get Add-ons, paste code `2055492159`, restart Anki.
3. Turn on FSRS in the deck options if it is not already on.

Anki must be **running** for any push or export. AnkiConnect serves
`127.0.0.1:8765` from inside the running app; there is no headless mode, and
AnkiWeb is a sync service rather than an API, so neither can substitute.

Confirm it works:

```bash
anki-cards check
```

## 2. The card-source repository

The human-readable card source lives in its own **private** repository. It does
not go in the `.claude` config repo, which is public: a course list, lecture
cadence and study record are not things to publish.

```bash
gh repo create ByronWilliamsCPA/premed-anki-source --private --clone \
  --description "Card source for the Anki study pipeline"
cd premed-anki-source
git commit -S --allow-empty -m "chore: initialize card source"
```

Layout, created automatically by `anki-cards new`:

```text
premed-anki-source/
  bisc-220/
    fall-2026/
      2026-09-02-glycolysis-regulation.md
      2026-09-04-gluconeogenesis.md
  chem-322/
    fall-2026/
      2026-09-03-sn1-and-sn2.md
```

Course, then term, then date-prefixed lecture file. The term tier keeps a
repeated or retaken course from colliding with its earlier run, and the date
prefix makes a term read chronologically.

## 3. Environment variables

Add to the shell profile (`~/.zshrc` or `~/.bashrc`):

```bash
export ANKI_SOURCE_ROOT="$HOME/dev/premed-anki-source"
export ANKI_EXPORT_DIR="$HOME/OneDrive/Family/anki-backups"
export ANKI_ROOT_DECK="Ariannah"
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANKI_SOURCE_ROOT` | `~/dev/premed-anki-source` | Card-source repo root. |
| `ANKI_EXPORT_DIR` | unset | Where `.apkg` snapshots are written. Point at the OneDrive folder that already holds the family Excel tracker. |
| `ANKI_ROOT_DECK` | `Ariannah` | Top-level deck. Exporting it includes every subdeck. |
| `ANKI_CONNECT_HOST` | `127.0.0.1` | Only change if Anki runs on another machine. |
| `ANKI_CONNECT_PORT` | `8765` | Only change if the add-on was reconfigured. |
| `ANKI_CONNECT_API_KEY` | unset | Only if the add-on's `apiKey` setting was set. |

## Backup layers

Three, independent on purpose:

| Layer | Covers | Fails if |
| --- | --- | --- |
| AnkiWeb sync | Day-to-day multi-device review | Account or service problem |
| Card-source git repo | Human-readable history, per-batch revert | Local disk and GitHub both lost |
| `.apkg` in OneDrive | Full collection with scheduling state | OneDrive lost |

Run the export on a cadence that suits the term:

```bash
anki-cards export
```

## Verifying the whole setup

One command checks every step above and prints a remedy for anything that
fails:

```bash
anki-cards doctor
```

It exits non-zero if anything would block a push. Warnings (a missing export
folder, a root deck that does not exist yet) do not block, because the export
folder is only needed for backups and course decks are created on demand.

Two failures worth knowing about in advance:

- **Note types missing.** The pipeline creates `Basic` and `Cloze` notes. A
  collection set up in a language other than English carries translated
  note-type names, and every push would fail on an unhelpful add-on error.
  `doctor` catches this and names it.
- **Card source inside the config repo.** If `ANKI_SOURCE_ROOT` points
  anywhere inside the public `.claude` repo, `doctor` fails hard. Card content
  carries a course list, lecture cadence and study record, and must stay in its
  own private repo.
