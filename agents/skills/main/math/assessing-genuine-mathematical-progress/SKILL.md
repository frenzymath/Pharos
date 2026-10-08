---
name: assessing-genuine-mathematical-progress
description: Evaluate the genuine mathematical progress of one proof approach over its last two hours — new understanding, reduction in difficulty, essential reduction of a key lemma, comparison with prior exploration — with the negative signals and the signals not to overweight; classify as substantial progress, modest but real progress, or lack of progress. Use in every checkpoint and before any allocation decision.
---

# Assessing Genuine Mathematical Progress

Use this skill to evaluate the mathematical progress of one proof approach — a route on the board, pursued by workers. Consider only content produced in the last two hours along this specific approach.

## Input Contract

Read, for the one approach under evaluation:

- the route's entry on `ROUTES.md` — its frontier statement before and its history;
- what its workers produced in the last two hours: verified facts (`fact_search` / `fact_get`), their findings and rejections (`gm_search`, then `gm_get`), their reports;
- for criterion 4, what earlier explorations of the same approach ran into: the survey (`literature/SURVEY.md`), the swarm's `dead_end` findings, the board's history.

## Procedure

### Criteria for Progress

1. New mathematical understanding. 
  Examples include: discovering previously unknown phenomena within a structure; identifying new mathematical structures that advance the problem; finding new techniques, or recognizing that techniques from other fields can be applied; establishing new dictionaries (correspondences between different areas).
2. Reduction in difficulty of the remaining problem.
  Assess whether the remaining problem is now substantially simpler than the original, or whether it remains essentially equivalent with the core difficulty merely repackaged. For instance, extracting a purely technical lemma in commutative algebra or sheaf theory from an algebraic geometry problem may count as progress if the setup is simpler and the difficulty is significantly lower. Conversely, decomposing a known hard problem into exercises only slightly harder than textbook problems would count. Distinguish whether the remaining problem is technical or still requires essentially new ideas.
3. Essential reduction or significant progress on a key technical lemma. 
   Examples include reducing a general algebraic geometry problem to one over \(\mathbb{A}^1\), or achieving a breakthrough on a previously identified key unresolved lemma. Partial progress—such as solving the problem under mild extra assumptions or identifying the core of the proof while leaving technical details incomplete—also counts. However, the location of the main difficulty matters: if the key obstacle is precisely the passage from a good case to the general case, then solving only the good case is not progress. If the good case was previously unknown or its generalizability was unrecognized, proving it is meaningful progress. This process typically involves finding a key inferential step rather than merely finding equivalent condition of the original problem.
4. Comparison with prior exploration of this approach.
   If this proof strategy has been explored before by others, first search for and summarize the main obstacles encountered by previous attempts. Identify why the approach failed to solve the main problem and where it stalled. Then compare the current progress against those historical sticking points to determine whether meaningful advancement has occurred.

To obtain a more objective assessment, the main agent should invoke one or more subagents to independently evaluate the difficulty of the remaining problem and assess each of the above criteria. The final judgment should classify the work as: substantial progress, modest but real progress, or lack of progress.

### Negative Signals

The following indicate a lack of effective mathematical progress:

1. Merely performing equivalent reformulations of the problem statement without substantive advancement.
2. Adding only new examples for special cases without general understanding; beyond 3–5 examples this ceases to be meaningful.
3. Newly discovered lemmas that do not contribute to the main proof—e.g., simple implications among known properties, or results applicable only to unrepresentative special cases that cannot advance the proof.

### Signals That Should Not Be Overweighted

The following should not be treated as evidence of mathematical progress:

1. Reduction in the number of remaining subproblems or cases after decomposing the original problem. 
  What matters is the difficulty of the remaining cases. A remaining case may be nearly equivalent to the original problem or may be the only nontrivial case; leaving only such cases does not make the problem easier. Progress can be claimed only if each remaining case is genuinely simpler than the original problem.
2. The number of newly discovered results or checked examples. 
  Discovering many simple theorems is not useful. The key question is whether a crucial result has been found that substantially lowers the difficulty. Understanding the first 1–2 examples is meaningful; beyond that, what matters is whether a sufficiently representative example has been identified whose proofs can generalize.

A proof approach may show significant progress and then stall, or it may encounter initial obstacles before gradually finding a breakthrough. The evaluation should focus on the progress made within the most recent two hours.

## Output Contract

One classification per approach — **substantial progress**, **modest but real progress**, or **lack of progress** — with the criterion it rests on and the evidence (the fact, the reduction, the obstacle passed), written into the route's history on `ROUTES.md` and carried into the progress section of the next checkpoint (`$checkpoint`). The classification is what `$evaluating-all-proof-strategies-and-allocating-workers` allocates on.

## Tools

- `fact_search` / `fact_get`, `gm_search` / `gm_get` (the last two hours of the route's facts, findings, and rejections)
- `pharos sub` (the independent evaluation of the remaining difficulty)
- `search_arxiv_theorems` (prior explorations of the same approach)
