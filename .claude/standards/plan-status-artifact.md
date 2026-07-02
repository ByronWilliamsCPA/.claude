# Plan-Status Artifact Standard

**Version:** 1.0
**Effective:** 2026-07-02
**Applies to:** Project-plan status visuals rendered as HTML Artifacts (claude.ai/code
artifact pages) for any repository with a phased project plan

> This document is the full specification for the "thread timeline" plan-status
> artifact: a single self-contained HTML page that shows what is complete, where the
> project currently stands, and what remains, at phase granularity. The
> `diagram-specialist` agent authors the HTML; the supervisor session publishes it
> with the Artifact tool. First produced for the CYO Adventure (Ariadne) plan on
> 2026-07-02 and generalized here.

---

## 1. Purpose and when to use

Use this artifact when the user asks for a visual depiction of a project plan's
progress: "where are we", "what's done and what's left", a status map for a phased
roadmap. It is a **status instrument, not a Gantt chart**: it encodes sequence and
state, not calendar dates or resource allocation.

Do not use it for: dependency graphs (use PlantUML/Mermaid), burndown metrics, or
task-level tracking (too granular; this reads at phase level with detail for the
current phase only).

## 2. Data contract

Derive every fact on the page from the target repo's planning documents. Typical
sources, in priority order:

1. `docs/planning/PROJECT-PLAN.md` (or equivalent synthesized plan): phase list,
   status table, release cuts, risk register.
2. `docs/planning/roadmap.md`: phase objectives and acceptance criteria.
3. `docs/planning/completion-plan.md` (or the current phase's slice breakdown):
   item-level detail for the in-progress phase.
4. `git log` on the default branch: confirms what has actually merged; when the
   plan doc and git history disagree, git wins and the discrepancy is noted in
   the summary you return to the supervisor.

Map plan-document statuses onto exactly four states:

| State | Meaning | Marker |
|-------|---------|--------|
| `done` | Delivered and merged | Solid green knot |
| `partial` | Delivered with an explicit scope carve-out (e.g. "backend only") | Solid green knot + dashed-outline pill labeled with the carve-out |
| `active` | The current phase (there should be exactly one) | Hollow amber knot with pulse + "You are here" tag |
| `pending` | Not started | Hollow grey knot on a dashed thread |

## 3. Design tokens

The palette is fixed so successive status artifacts across repos read as one
system. Semantic status colors are deliberately separate from the single accent.

```css
:root {
  --paper: #F7F6F2;      /* page ground: warm-neutral, not cream */
  --card: #FFFFFF;       /* panel ground */
  --ink: #262A3E;        /* primary text: indigo-biased near-black */
  --ink-soft: #5C5F70;   /* secondary text */
  --thread: #A93226;     /* THE accent: madder red; thread, cut lines, eyebrow */
  --done: #2E7D4F;   --done-bg: #E8F2EC;     /* semantic: delivered */
  --active: #B45309; --active-bg: #FBF0E1;   /* semantic: in progress */
  --pending: #8B8D99; --pending-bg: #EEEEEA; /* semantic: planned */
  --line: #DDDCD4;       /* hairlines and borders */
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", "Cascadia Mono", Consolas, monospace;
}
```

Type roles: serif for display (h1, phase names, summary values, cut-line labels),
sans for body and labels, mono for phase IDs, slice IDs, and PR numbers. Uppercase
labels get `letter-spacing: 0.09em` to `0.14em`. Body copy maxes at `66ch`.

Artifact CSP blocks all external requests: system font stacks only, no webfont
URLs, no CDN assets. Everything inline.

## 4. Page structure (top to bottom)

1. **Header**: accent eyebrow (`PROJECT NAME · CODENAME`), serif h1, one-sentence
   subtitle stating the as-of date and what the page answers.
2. **Summary strip**: 3 cards in a hairline grid: (a) track progress count with a
   segmented meter (one segment per phase, filled by state), (b) what the next
   release still needs, (c) the next track or horizon with its estimate.
3. **Thread timeline, one per track**: a vertical 2px line in the accent color
   with one knot per phase. Solid line for the reached portion; `repeating-linear-gradient`
   dashes with reduced opacity for future portions. Each phase row: mono phase ID,
   serif phase name, status pill, and a one-line description (strong-tag the single
   most load-bearing fact, e.g. a measured yield or an enforced invariant).
4. **Current-phase card**: the only place with item-level detail. A left-accent
   card inside the active phase row listing that phase's slices as a 3-column grid
   (state glyph / mono slice ID / description). Glyphs: `✓` done, `▶` next up,
   `○` remaining.
5. **Cut lines**: release boundaries drawn as dashed horizontal rules in the
   accent color with a centered serif label and a small sans subtitle stating the
   acceptance meaning of the cut ("concept to child's tablet, end to end").
6. **Carried-risks panel**: 2-4 bullets max, each a bolded risk name plus one
   sentence. Only risks that survive into the remaining work.
7. **Footer**: source documents and "status reflects main as of DATE (through PR #N)".

## 5. Accessibility and correctness rules

- Encode state in **form, not only color**: solid vs hollow knots, solid vs dashed
  thread, pill text labels. The page must read correctly in grayscale.
- Pulse animation on the active knot only, wrapped in
  `@media (prefers-reduced-motion: no-preference)`.
- No em-dash characters anywhere, including in HTML entities (`&mdash;`); use
  colons, middle dots (`&middot;`), or restructured sentences.
- Wide content scrolls inside its own `overflow-x: auto` container; the body
  never scrolls horizontally. Summary grid uses `auto-fit, minmax(230px, 1fr)`.
- `font-variant-numeric: tabular-nums` wherever digits align.
- Every count on the page must be derivable from the source documents; never
  invent progress percentages. Phase counts, PR numbers, and measured metrics
  (yields, coverage) are quoted from the plan verbatim.

## 6. Component markup patterns

Compose the page from these patterns; the CSS class names below are the contract.

**Phase row (thread node):**

```html
<div class="phase done|active|">          <!-- no class = pending -->
  <span class="knot" aria-hidden="true"></span>
  <div class="phase-head">
    <span class="phase-id">PHASE N</span>
    <span class="phase-name">Name</span>
    <span class="pill done|active|pending|partial">Label</span>
    <!-- active phase only: --> <span class="here-tag">You are here</span>
  </div>
  <p class="phase-desc">One line; <strong>bold the load-bearing fact</strong>.</p>
  <!-- active phase only: current-phase card goes here -->
</div>
```

**Cut line:**

```html
<div class="cutline" role="separator">
  <span>RELEASE NAME<small>what the cut means, in acceptance terms</small></span>
</div>
```

**Current-phase slice list:**

```html
<ul class="slices">
  <li class="s-done"><span class="tick">&#10003;</span><code>ID-1</code><span>Done item <span class="why">(evidence, PR #)</span></span></li>
  <li class="s-next"><span class="tick">&#9654;</span><code>ID-2</code><span>Next item</span></li>
  <li class="s-todo"><span class="tick">&#9675;</span><code>ID-3</code><span>Remaining item</span></li>
</ul>
```

The full reference stylesheet implementing these classes is embedded in the
template section of this standard's companion file
`plan-status-artifact.template.html` (same directory). Copy it verbatim and
adjust content, not the token values.

## 7. Authoring and publishing workflow

Subagents do not hold the Artifact tool, so the split is:

1. **diagram-specialist** (or the main session acting directly): read the planning
   docs per the data contract, write the complete HTML file to the session
   scratchpad (or a path the supervisor names), and return the file path plus a
   short list of any plan-vs-git discrepancies found.
2. **Supervisor session**: publish with the Artifact tool. Favicon `🧵` (constant
   for this artifact family). Title `<title>PROJECT: Plan Status</title>`. Redeploy
   to the same file path so status refreshes keep the same URL; label each deploy
   with a short version note (e.g. `post-pr-58`).

Refreshing an existing status artifact is an update, not a new page: same file
path, same favicon, same URL.

## 8. Content voice

Write from the reader's side: "a child sees only their approved books", not
"the library API filters by profile". One line per phase; the current phase gets
the only expansion. Bold at most one fact per phase description. The risks panel
admits the honest caveats behind the green checkmarks; a status page that hides
carried risk is decoration, not an instrument.
