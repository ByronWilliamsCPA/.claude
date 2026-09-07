# Operating Model

> Decided 2026-09-02. Recorded here so it is not re-litigated each session.

## Who runs what

| Layer | Tool | Who | Why |
| --- | --- | --- | --- |
| Tutoring, quizzing, PREview, practice sets | Claude.ai chat ("Tutor" Project) | Ariannah | Mobile access. She needs it live, on her phone, between classes. |
| Lecture capture | Genio, or handwritten iPad notes | Ariannah | Existing step, unchanged. |
| Distillation to a half-page summary | Manual, within 48 hours | Ariannah | The 48-hour rule is the existing cadence. |
| Cards from summary, and push to Anki | Claude Code + `anki-cards` | Ariannah | This pipeline. |
| Daily review | Anki (desktop and phone), FSRS on | Ariannah | Unchanged. |

**Operator: Ariannah (option B).** She runs the pipeline herself on her own
laptop. This was chosen over Dad-as-operator so the person who has to learn the
material is the person who reads and edits the cards, with no handoff in
between.

What that decision costs, and what it buys:

- Anki Desktop plus the AnkiConnect add-on has to be installed on **her**
  machine, not Dad's. AnkiConnect only talks to a running local Anki.
- The CLI surface is deliberately small, and every error message says what to
  do next. Keep it that way. Any change that assumes developer knowledge is a
  regression for this operator.
- It keeps the review gate honest: the same person drafts, reads, edits and
  pushes, so the editing pass cannot be skipped by someone who does not need it.

## Do not reopen

These were settled before this pipeline was built:

- **Tutoring stays in Claude.ai chat.** Do not propose moving it to Claude
  Code. Mobile access is the whole reason.
- **AnkiWeb, free tier, for live sync.** Not a self-hosted sync server.
- **One tool per job.** Do not introduce a second card-generation path
  alongside this one.
- **Card source lives in a separate private repo,** never in the public
  `.claude` config repo.

## If the operator changes

If Ariannah stops running it and Dad takes over, the only changes needed are
which machine has Anki installed and where the three environment variables are
set. Update the table above, and keep the draft-then-approve gate: under a
Dad-as-operator model the gate is what keeps her in the loop at all, so it
matters more, not less.
