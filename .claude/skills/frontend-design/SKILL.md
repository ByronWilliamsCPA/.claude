---
name: frontend-design
description: >
  Create distinctive, production-grade frontend interfaces with high design quality
  and strong UX foundations. Use when building web components, pages, dashboards,
  landing pages, or applications. Covers creative direction, accessibility, interaction
  design, performance optimization, and visual polish. Supports React, Next.js, Vue,
  Svelte, and HTML/CSS.
version: 1.0.0
sources:
  - anthropics/skills/frontend-design (creative direction, anti-slop aesthetics)
  - vercel-labs/agent-skills/react-best-practices (69 React/Next.js perf rules)
  - nextlevelbuilder/ui-ux-pro-max (99 UX guidelines, accessibility, interaction)
---

# Frontend Design Skill

Create distinctive, production-grade frontend interfaces that avoid generic AI aesthetics.
Implement real working code with exceptional attention to aesthetic details, accessibility,
performance, and creative choices.

## Activation

Trigger on: build UI, create component, design page, frontend, landing page, dashboard,
web app, React component, HTML/CSS layout, style UI, beautify, improve UI, review UI,
check accessibility, audit design, review UX

## Design Thinking (REQUIRED Before Coding)

Before writing any code, commit to a clear aesthetic direction:

- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick a bold direction: brutally minimal, maximalist chaos, retro-futuristic,
  organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw,
  art deco/geometric, soft/pastel, industrial/utilitarian, etc.
- **Constraints**: Framework, performance budget, accessibility requirements
- **Differentiation**: What makes this UNFORGETTABLE? What will someone remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision.
Bold maximalism and refined minimalism both work -- the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, Svelte, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Arguments

- (none) -- Design thinking + full implementation
- `review` -- Review existing UI against UX checklist and aesthetics guidelines
- `a11y` -- Focused accessibility audit (WCAG AA compliance)
- `perf` -- Performance optimization pass (React/Next.js focus)
- `fix <file>` -- Fix UI/UX issues in a specific file

---

## Part 1: Aesthetics Guidelines

Source: Anthropic frontend-design skill (adapted)

### Typography

Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like
Arial, Inter, Roboto, and system defaults. Opt for distinctive choices that elevate the
interface. Pair a distinctive display font with a refined body font.

### Color & Theme

Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with
sharp accents outperform timid, evenly-distributed palettes. Design light and dark
variants together to keep brand, contrast, and style consistent.

### Motion

Use animations for effects and micro-interactions. Focus on high-impact moments: one
well-orchestrated page load with staggered reveals (animation-delay) creates more
delight than scattered micro-interactions. Use scroll-triggering and hover states that
surprise.

- Prioritize CSS-only solutions for HTML
- Use Motion (framer-motion) for React when available
- Duration 150-300ms for micro-interactions; complex transitions <=400ms
- Use ease-out for entering, ease-in for exiting; avoid linear for UI transitions
- Prefer spring/physics-based curves for natural feel
- Exit animations shorter than enter (~60-70% of enter duration)
- Stagger list/grid item entrance by 30-50ms per item
- ALL animations must respect `prefers-reduced-motion`

### Spatial Composition

Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous
negative space OR controlled density. Use 4pt/8dp incremental spacing system.

### Backgrounds & Visual Details

Create atmosphere and depth rather than defaulting to solid colors. Gradient meshes,
noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative
borders, custom cursors, grain overlays.

### Anti-Patterns (NEVER Use)

- Overused fonts: Inter, Roboto, Arial, Space Grotesk, system fonts
- Cliched color schemes: purple gradients on white backgrounds
- Predictable layouts and cookie-cutter component patterns
- Generic AI-generated aesthetics ("AI slop")
- Emoji as structural icons -- use SVG icons (Heroicons, Lucide)
- Mixing filled and outline icon styles at the same hierarchy level
- Raw hex colors in components -- use semantic color tokens

### Implementation Complexity Rule

Match code complexity to the aesthetic vision:
- **Maximalist designs**: Elaborate code with extensive animations, effects, layered visuals
- **Minimalist designs**: Restraint, precision, careful spacing/typography/subtle details
- Elegance comes from executing the vision well, not from adding more

---

## Part 2: UX & Accessibility Checklist

Source: nextlevelbuilder/ui-ux-pro-max (adapted, generalized from React Native)

### Priority 1: Accessibility (CRITICAL)

| Rule | Standard |
|------|----------|
| `color-contrast` | Minimum 4.5:1 for normal text, 3:1 for large text (WCAG AA) |
| `focus-states` | Visible focus rings (2-4px) on all interactive elements |
| `alt-text` | Descriptive alt text for meaningful images |
| `aria-labels` | aria-label for icon-only buttons |
| `keyboard-nav` | Tab order matches visual order; full keyboard support |
| `form-labels` | Use `<label>` with `for` attribute; never placeholder-only |
| `skip-links` | Skip to main content for keyboard users |
| `heading-hierarchy` | Sequential h1-h6, no level skipping |
| `color-not-only` | Never convey info by color alone (add icon/text) |
| `reduced-motion` | Respect `prefers-reduced-motion`; reduce/disable animations |
| `screen-reader` | Meaningful labels; logical reading order |
| `escape-routes` | Provide cancel/back in modals and multi-step flows |

### Priority 2: Touch & Interaction (CRITICAL)

| Rule | Standard |
|------|----------|
| `touch-target-size` | Min 44x44px interactive area |
| `touch-spacing` | Minimum 8px gap between touch targets |
| `hover-vs-tap` | Use click/tap for primary interactions; never rely on hover alone |
| `loading-buttons` | Disable button during async; show spinner or progress |
| `error-feedback` | Clear error messages near the problem |
| `cursor-pointer` | Add cursor-pointer to all clickable elements |
| `tap-feedback` | Visual feedback on press within 100ms (ripple, opacity, scale) |
| `disabled-clarity` | Disabled elements: reduced opacity (0.38-0.5) + cursor change + semantic attribute |

### Priority 3: Performance (HIGH)

| Rule | Standard |
|------|----------|
| `image-optimization` | WebP/AVIF, responsive srcset/sizes, lazy load non-critical |
| `image-dimensions` | Declare width/height or aspect-ratio to prevent CLS |
| `font-loading` | font-display: swap/optional; preload critical fonts only |
| `critical-css` | Prioritize above-the-fold CSS |
| `lazy-loading` | Lazy load non-hero components via dynamic import |
| `bundle-splitting` | Split code by route/feature |
| `third-party-scripts` | Load async/defer; audit and remove unnecessary ones |
| `content-jumping` | Reserve space for async content (CLS < 0.1) |
| `virtualize-lists` | Virtualize lists with 50+ items |
| `debounce-throttle` | Debounce/throttle high-frequency events (scroll, resize, input) |

### Priority 4: Style Selection (HIGH)

| Rule | Standard |
|------|----------|
| `style-match` | Match style to product type and audience |
| `consistency` | Same style across all pages |
| `no-emoji-icons` | Use SVG icons (Heroicons, Lucide), not emojis |
| `effects-match-style` | Shadows, blur, radius aligned with chosen style |
| `state-clarity` | Hover/pressed/disabled states visually distinct |
| `elevation-consistent` | Consistent shadow/elevation scale for cards, sheets, modals |
| `dark-mode-pairing` | Design light/dark variants together |
| `icon-style-consistent` | One icon set/visual language across the product |
| `primary-action` | One primary CTA per screen; secondary actions visually subordinate |

### Priority 5: Layout & Responsive (HIGH)

| Rule | Standard |
|------|----------|
| `viewport-meta` | width=device-width initial-scale=1 (never disable zoom) |
| `mobile-first` | Design mobile-first, scale up |
| `breakpoints` | Systematic: 375 / 768 / 1024 / 1440 |
| `readable-font-size` | Minimum 16px body text on mobile |
| `line-length` | 35-60 chars mobile; 60-75 chars desktop |
| `no-horizontal-scroll` | Content fits viewport width |
| `spacing-scale` | 4pt/8dp incremental spacing system |
| `container-width` | Consistent max-width on desktop |
| `z-index-management` | Defined layered scale (0/10/20/40/100/1000) |
| `viewport-units` | Prefer min-h-dvh over 100vh on mobile |

### Priority 6: Typography & Color (MEDIUM)

| Rule | Standard |
|------|----------|
| `line-height` | 1.5-1.75 for body text |
| `font-pairing` | Match heading/body font personalities |
| `font-scale` | Consistent type scale (12/14/16/18/24/32) |
| `weight-hierarchy` | Bold headings (600-700), Regular body (400), Medium labels (500) |
| `color-semantic` | Semantic tokens (primary, secondary, error, surface, on-surface) |
| `color-dark-mode` | Desaturated/lighter tonal variants; never simply inverted |
| `color-accessible-pairs` | Verify all fg/bg pairs meet 4.5:1 (AA) or 7:1 (AAA) |
| `truncation` | Prefer wrapping; when truncating use ellipsis + tooltip |
| `number-tabular` | Tabular/monospaced figures for data columns, prices, timers |

### Priority 7: Animation (MEDIUM)

| Rule | Standard |
|------|----------|
| `duration-timing` | 150-300ms micro; <=400ms complex; never >500ms |
| `transform-only` | Animate transform/opacity only; never width/height/top/left |
| `loading-states` | Skeleton/shimmer when loading >300ms |
| `motion-meaning` | Every animation must express cause-effect, not just decoration |
| `state-transition` | State changes animate smoothly, never snap |
| `spring-physics` | Prefer spring curves over cubic-bezier for natural feel |
| `interruptible` | User tap/gesture cancels in-progress animation immediately |
| `no-blocking` | Never block user input during animation |
| `stagger-sequence` | Stagger list entrance 30-50ms per item |
| `layout-shift-avoid` | Animations must not cause reflow or CLS |

### Priority 8: Forms & Feedback (MEDIUM)

| Rule | Standard |
|------|----------|
| `input-labels` | Visible label per input (not placeholder-only) |
| `error-placement` | Error below the related field |
| `submit-feedback` | Loading then success/error state on submit |
| `required-indicators` | Mark required fields (asterisk) |
| `empty-states` | Helpful message and action when no content |
| `toast-dismiss` | Auto-dismiss toasts 3-5s; aria-live="polite" |
| `confirmation-dialogs` | Confirm before destructive actions |
| `inline-validation` | Validate on blur, not keystroke |
| `progressive-disclosure` | Reveal complex options progressively |
| `error-recovery` | Error messages include cause + how to fix + recovery path |
| `multi-step-progress` | Step indicator or progress bar; allow back navigation |
| `focus-management` | After submit error, auto-focus first invalid field |

### Priority 9: Navigation (HIGH)

| Rule | Standard |
|------|----------|
| `bottom-nav-limit` | Max 5 items; labels with icons |
| `back-behavior` | Predictable and consistent; preserve scroll/state |
| `deep-linking` | All key screens reachable via URL |
| `nav-label-icon` | Both icon and text label; icon-only harms discoverability |
| `nav-state-active` | Current location visually highlighted |
| `modal-escape` | Clear close/dismiss affordance |
| `search-accessible` | Easily reachable; provide recent/suggested queries |
| `breadcrumb-web` | Use breadcrumbs for 3+ level deep hierarchies |
| `state-preservation` | Navigating back restores scroll, filters, input |
| `adaptive-nav` | Large screens (>=1024px) prefer sidebar; small use bottom/top |

### Priority 10: Charts & Data (LOW)

| Rule | Standard |
|------|----------|
| `chart-type-match` | Trend=line, comparison=bar, proportion=pie/donut |
| `accessible-colors` | Supplement color with patterns/shapes |
| `data-table` | Provide table alternative for screen readers |
| `legend-visible` | Always show legend near chart |
| `tooltip-on-interact` | Hover (web) or tap (mobile) shows exact values |
| `responsive-chart` | Reflow/simplify on small screens |
| `empty-data-state` | "No data yet" + guidance, not blank chart |
| `no-pie-overuse` | Avoid pie/donut for >5 categories; use bar chart |

---

## Part 3: React & Next.js Performance Patterns

Source: Vercel react-best-practices (vercel-labs/agent-skills)

Apply these when writing, reviewing, or refactoring React/Next.js code.

### Category 1: Eliminating Waterfalls (CRITICAL)

- Check cheap sync conditions before awaiting remote values
- Move `await` into branches where actually used (defer-await)
- Use `Promise.all()` for independent async operations
- Start promises early, await late in API routes
- Use `<Suspense>` boundaries to stream content progressively

### Category 2: Bundle Size (CRITICAL)

- Import directly from modules; avoid barrel files (`index.ts` re-exports)
- Use `next/dynamic` or `React.lazy` for heavy components
- Defer third-party scripts (analytics, logging) until after hydration
- Load modules conditionally only when features are activated
- Preload on hover/focus for perceived speed

### Category 3: Server-Side Performance (HIGH)

- Use `React.cache()` for per-request deduplication
- Use LRU cache for cross-request caching
- Avoid duplicate serialization in RSC props
- Hoist static I/O (fonts, logos) to module level
- Never use module-level mutable state in RSC/SSR
- Minimize data passed to client components
- Restructure components to parallelize server fetches
- Use `after()` for non-blocking post-response operations

### Category 4: Client-Side Data (MEDIUM-HIGH)

- Use SWR or React Query for automatic request deduplication
- Deduplicate global event listeners
- Use passive listeners for scroll events
- Version and minimize localStorage data

### Category 5: Re-render Optimization (MEDIUM)

- Don't subscribe to state only used in callbacks
- Extract expensive work into memoized components
- Hoist default non-primitive props outside components
- Use primitive dependencies in effects/memos
- Subscribe to derived booleans, not raw store values
- Derive state during render, not in effects
- Use functional setState for stable callbacks
- Pass function to useState for expensive initial values
- Don't define components inside other components
- Use `startTransition` for non-urgent updates
- Use `useDeferredValue` for expensive renders
- Use refs for transient high-frequency values

### Category 6: Rendering Performance (MEDIUM)

- Animate wrapper divs, not SVG elements directly
- Use `content-visibility: auto` for long off-screen lists
- Extract static JSX outside component functions
- Reduce SVG coordinate precision
- Use ternary (`? :`) not `&&` for conditional rendering
- Prefer `useTransition` over manual loading state
- Use React DOM resource hints for preloading

### Category 7: JavaScript Performance (LOW-MEDIUM)

- Batch DOM/CSS changes via classes or cssText
- Build Map/Set for repeated lookups (O(1) vs O(n))
- Cache object properties and function results in loops
- Combine multiple filter/map into single loop
- Check array length before expensive operations
- Return early from functions
- Hoist RegExp creation outside loops
- Use `requestIdleCallback` for non-critical deferred work

---

## Workflow

### Mode: Build (default)

1. **Design Thinking**: Establish bold aesthetic direction (see Design Thinking section)
2. **Design System**: Define tokens -- colors, typography, spacing, shadows, radii
3. **Component Architecture**: Plan component hierarchy and data flow
4. **Implementation**: Build with production-grade code following all guidelines
5. **Polish Pass**: Verify against UX Checklist priorities 1-5 (CRITICAL + HIGH)
6. **Accessibility Audit**: Run through Priority 1 checklist completely

### Mode: Review (`review`)

1. Read the target files
2. Check against **Aesthetics Guidelines** -- is the design distinctive or generic?
3. Run through **UX Checklist** priorities 1-5 (CRITICAL and HIGH)
4. Check **Performance Patterns** if React/Next.js
5. Output findings as `file:line - [PRIORITY] rule-name: description`

### Mode: Accessibility (`a11y`)

1. Read the target files
2. Run through Priority 1 (Accessibility) completely
3. Check Priority 2 (Touch & Interaction) for interactive elements
4. Check Priority 8 (Forms & Feedback) for any form elements
5. Verify color contrast, focus states, aria attributes, keyboard navigation
6. Output findings grouped by severity

### Mode: Performance (`perf`)

1. Read the target files
2. Run through Priority 3 (Performance) from UX Checklist
3. Apply React/Next.js Performance Patterns (Part 3) if applicable
4. Check bundle size, waterfall, and rendering patterns
5. Output findings with estimated impact level

### Mode: Fix (`fix <file>`)

1. Read the specified file
2. Identify UX/accessibility/performance issues
3. Apply fixes following the guidelines
4. Run the project's linter to verify no regressions
5. Present summary of changes

## Pre-Delivery Checklist

Before delivering any frontend work:

- [ ] Design direction is clear and intentional (not generic)
- [ ] Color contrast meets WCAG AA (4.5:1 text, 3:1 large text)
- [ ] All interactive elements have visible focus states
- [ ] Touch targets >= 44x44px
- [ ] No horizontal scroll on mobile
- [ ] `prefers-reduced-motion` respected
- [ ] No emoji used as structural icons
- [ ] Semantic color tokens used (no raw hex in components)
- [ ] Images have dimensions/aspect-ratio set (CLS prevention)
- [ ] Forms have visible labels, error placement below fields
- [ ] Tested at 375px width and landscape orientation
- [ ] Dark mode contrast verified independently

## Reference catalogs

Static design catalogs live in [`context/`](context/README.md), extracted from
`ui-ux-pro-max-skill` (MIT). Load the one that fits the task instead of inventing
options: `styles.csv` (84 style families with palettes and prompt keywords),
`typography.csv` (74 font pairings with imports), `charts.csv` (25 chart types
with a11y grades), `ui-reasoning.csv` (161 product-type UX decision rules), and
`app-interface.csv` (30 interface Do/Don't rules with code). See
[`context/README.md`](context/README.md) for the full index and usage.

## Attribution

This skill synthesizes guidance from:
- [Anthropic Skills: frontend-design](https://github.com/anthropics/skills) -- Creative direction, anti-slop aesthetics
- [Vercel Labs: react-best-practices](https://github.com/vercel-labs/agent-skills) -- 69 React/Next.js performance rules (MIT)
- [nextlevelbuilder: ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) -- 99 UX guidelines, accessibility, interaction patterns
