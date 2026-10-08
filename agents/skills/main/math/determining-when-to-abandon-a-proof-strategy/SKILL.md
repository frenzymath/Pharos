---
name: determining-when-to-abandon-a-proof-strategy
description: Decide when a proof strategy should be fully abandoned: a definitive counterexample that repair attempts could not overcome, or no progress on the central problem with activity only on trivial cases and lemmas; the warning signs, and the override when recent work directly aids the main proof. Use before killing or parking any route on the board.
---

# Determining When to Abandon a Proof Strategy

Use this skill to decide when a proof strategy — a route on the board, pursued by workers — should be fully abandoned.

## Input Contract

Read, for the route in question:

- its recent assessment (`$assessing-genuine-mathematical-progress`) and its history on the board;
- its workers' `counterexample`, `dead_end`, and `obstacle` findings, and what the repair attempts after a counterexample produced;
- what its workers have submitted recently — facts, and the rejections in the `verification` traces.

## Procedure

### Conditions for Clear Abandonment

Abandon a strategy when either of the following holds:

1. A counterexample has been found that definitively refutes the approach, and devoted attempts to repair the route have failed. The strategy cannot be repaired into a meaningful way.

2. No progress is being made on the central problem. Work has stalled on the key problem, and progress occurs only under over-simplified special cases or trivial deductions with no progress on the main line. This includes producing numerous trivial lemmas or resolving many trivial cases. Such activity consumes resources without advancing the proof.

### Warning Signs

The following patterns are potential indicators that a strategy should be abandoned, but each still requires checking whether the work actually helps the main proof:

1. Generating too many trivial cases and trivial lemmas. Solving many simple cases or discovering many simple lemmas is not progress by itself. It is a warning sign that no real progress has been made. Evaluate whether these results advance the main line.

2. Circular or equivalent reformulations. Newly derived conclusions merely restate the original conditions of a key problem or move in circles without yielding genuinely new results.

### Override Condition

Do not abandon the strategy if recent work contains content that directly aids the proof of the main theorem.

## Output Contract

The decision on `ROUTES.md` (its format: `$checkpoint`): **dead**, with the condition that applied and what killed it (the counterexample's finding or fact, or the stalled key problem), its workers re-tasked; or **kept**, with the override evidence named. A warning sign alone changes nothing on the board — it triggers the check.

## Tools

- `gm_search` / `gm_get` (the counterexamples, dead ends, and rejections on the route)
- `fact_search` / `fact_get` (what the route has actually established)
- `pharos assign` (re-task the route's workers when it is abandoned — `$allocate-workers`)
