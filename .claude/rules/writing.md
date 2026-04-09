# Writing Rules

> Applies to all text Claude generates: responses, documents, comments, PR descriptions,
> commit messages, emails, and any other prose output.

## Punctuation

**No em-dashes.** This is a confirmed user preference (Tier 3 override over CMS §6.85–6.87).
Use commas, colons, semicolons, or parentheses instead.

Bad: "The system — which runs nightly — processes 40K records."
Good: "The system runs nightly and processes 40K records."
Good: "The system (which runs nightly) processes 40K records."

## AI Pattern Avoidance

Never use these terms in any output. They signal unrevised AI-generated text and carry no
information.

**Vague qualifiers** — replace with a specific number or remove:
`significantly`, `substantially`, `considerably`, `greatly`, `highly`, `markedly`

**Corporate buzzwords** — replace with what you actually mean:
`leverage`, `synergies`, `optimize`, `streamline`, `empower`, `enable` (when used as filler)

**Hype words** — describe the specific capability instead:
`best-in-class`, `cutting-edge`, `game-changer`, `innovative`, `revolutionary`,
`transformative`, `state-of-the-art`, `groundbreaking`

**AI filler phrases** — delete or restate directly:
`delve into`, `it's important to note`, `in conclusion`, `in summary`, `to summarize`,
`moving forward`, `in today's landscape`, `at the end of the day`

**Puffery** — replace with specific evidence:
`crucial`, `robust`, `seamless`, `holistic`, `comprehensive`, `pivotal`, `vital`,
`testament`, `unwavering`, `unparalleled`, `exemplary`

**Empty gerund phrases** — name the mechanism or quantify:
"ensuring reliability," "fostering collaboration," "driving growth," "delivering value,"
"enabling success," "enhancing performance"

## Structural Tells to Avoid

These patterns appear in AI output and make text look unreviewed:

- Bullet points always in groups of 3 (list what's actually there)
- Every section the same length (let content determine length)
- Analytical prose broken into bullets when it should be prose
- Multiple consecutive sentences starting with "This," "The," or "Additionally"
- "Additionally," "Furthermore," "Moreover" used more than once per page
- Excessive bolding: more than one bolded phrase per section, or entire bolded sentences
- Emoji used as formatting decorators in professional documents

## Quantification Over Vagueness

When writing professionally, state measurable outcomes. If you cannot measure it, say so
explicitly rather than using a vague qualifier.

| Vague | Better |
| --- | --- |
| "Significantly improve efficiency" | "Reduce processing time from 40 to 5 hours per month" |
| "Better data quality" | "Increase accuracy from 85% to 99%" |
| "Lower costs" | "Eliminate $50K in annual manual workaround costs" |

When a number is not available, use a range and state the basis:
"Estimated 20–30% reduction based on comparable implementations."

## Grammar Authority (Professional Documents)

When producing professional documents, follow this hierarchy:

| Operation | Authority |
| --- | --- |
| Drafting (writing first draft) | Elements of Style (Tier 1 baseline) |
| Editing (reviewing any draft) | Chicago Manual of Style, 17th ed. (Tier 2) |
| User-confirmed preference deviations | PromptCraft Pro defaults (Tier 3) |

**Active Tier 3 overrides**: No em-dashes (see above). See
`.submodules/reference-library/writing-style/grammar-style/cross-reference.md` for the
full list of EoS/CMS/PCP divergences.

## Writing Pipeline

For document editing tasks, use the three-stage pipeline:

1. `grammar-composition-editor` (Stage 1) — grammar, composition, plain language
2. `document-validator` (Stage 2) — factual accuracy, assumptions, hallucinations, bias
3. `writing-style-editor` (Stage 3) — voice alignment, AI pattern detection, stylometry

Always run in order. See `standards/writing-quality.md` for thresholds and sequencing rules.
