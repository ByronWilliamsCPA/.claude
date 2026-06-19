---
name: systematic-debugging-extras
description: Local delta on top of the vendored systematic-debugging skill. Adds numeric premise-probing, sibling-consumer falsification for shared components, data-semantics verification before applying a prescribed transform, proxy-input discipline, and newly-reachable-path testing after a guard is removed. Use alongside systematic-debugging when investigating any bug, all-zero/constant metric, a "shared component is broken" diagnosis, a brief that prescribes a transform or fix mechanism, a finding built on stand-in data, or a fix that removes a guard. Triggers on: debug, root cause, all-zeros metric, shared workflow broken, difference the cumulative, proxy data, removed a guard.
---

# systematic-debugging-extras

Extends the vendored `systematic-debugging` skill (read-only, in `.submodules`). Contains only the delta: the bug premise and the prescribed fix are both hypotheses, and several cheap probes discriminate truth from plausible-but-wrong before any code is written.

## The brief's diagnosis and its prescribed fix are two separate claims; verify both

systematic-debugging already says verify the root cause before fixing. Extend that to the fix mechanism. When a task brief or reviewer prescribes a transformation over a data structure (difference, cumsum, normalize, invert), verify the structure's actual semantics empirically (print a sample, check monotonicity, sum, sign) before applying it, even when the brief sounds authoritative. A confident instruction like "ta_distributions returns a cumulative curve, so difference it" can be wrong about the data model: the curve was bell-shaped per-year, and differencing it would have produced negative distributions that pass shape/sign tests but corrupt the economics. One cheap empirical probe of the actual values discriminates between the two mental models.

Likewise verify a lever's DIRECTION before committing the value a brief assumes. When a step says "change X to move metric Y toward Z," sweep X across a small grid and confirm the sign of dY/dX matches the brief first. A brief can assume growing benefits lower funded status when they raise it; committing the assumed value bakes in a wrong-signed change and masks the real driver (an asset-scope mismatch). If the sign is wrong, surface it as a finding rather than tuning X to fit.

## A constant or all-zero metric is a scale mismatch in disguise

When a metric reads as a constant (all-zeros, all-same across inputs), it is almost never "low signal": one operand of a min/max/threshold is on the wrong scale (aggregate-vs-summed, per-unit-vs-total, rate-vs-level). Instrument BOTH sides of the binding comparison and print them per-input. A short numeric probe both confirms the premise (aggregate stressed share 0.48 vs summed ceiling 0.625, so over=0) and reveals the correctly-scaled operand to switch to (the single most-overweight sleeve vs its own max). The instrumentation that proves the bug usually designs the fix in the same step.

## Falsify "the shared component is broken" by sampling siblings first

When the suspect is a shared or centralized component (a reusable workflow, a shared library version, an org config), sample three to five other consumers of the same version before concluding the component is broken. One green consumer on the same version immediately falsifies the global-breakage hypothesis and redirects the investigation to the caller/consumer side. A workflow that startup-failed for one caller was caused by a caller-side missing `actions: read` grant (GitHub validates this at compile time with only a generic `startup_failure` message), not an org-wide break; five sibling repos ran the same reusable green that day. Run this cheapest falsification test before building any workaround.

## A proxy is a placeholder for evidence, not evidence

When an analysis rests on a proxy, sample, or stand-in for a blocked real input, any conclusion carries an obligation to recompute against the real input. (a) Label the finding provisional and name the proxy explicitly in any broadcast; (b) record the specific upstream artifact whose arrival resolves it; (c) treat "real input now available" as a high-priority trigger to recompute and correct the record before the proxy finding ossifies into accepted fact. A stale-CMA proxy implied a 116 bps miss; the real 2026 inputs reversed it to within tolerance. Correcting a broadcast finding is a deliverable, not an embarrassment.

## Removing a guard makes downstream code reachable for the first time

A bug-causing condition can double as accidental protection for code downstream of it. When a fix removes a guard or makes a previously-unreachable path reachable, run the end-to-end scenario in the exact trigger condition, not just unit tests. Fixing a `max([])` crash on an empty-survivor set let scoring proceed over the full field, which then KeyError'd in a downstream function on a candidate missing from a stale artifact; unit tests passed and only the real trigger condition exposed the second failure. Verify the whole newly-live path, not just the line you changed.
