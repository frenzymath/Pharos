---
name: evaluating-all-proof-strategies-and-allocating-workers
description: Assess the status of every current proof strategy and allocate the workers pursuing them: unexplored strategies first, evaluation by the progress criteria, favour the most promising while keeping diversity, reduce after two hours without progress but not to zero, never spread evenly, and push cross-approach findings into stalled strategies. Use at every four-hour audit and whenever workers are reallocated.
---

# Evaluating All Proof Strategies and Allocating Workers

Use this skill to assess the status of all current proof strategies — the routes on the board — and allocate the workers pursuing them accordingly (`pharos assign`, `$allocate-workers`).

## Input Contract

Read:

- the route board, `ROUTES.md` — every strategy, its status, its allocation;
- each strategy's assessment by `$assessing-genuine-mathematical-progress` (its last two hours);
- the current worker roster and assignments (`pharos status`, each worker's `TASK.md`).

## Procedure

### General Principles

1. Unexplored strategies receive priority.  
   If a proof strategy has not yet been explored, allocate resources to conduct an initial exploration before making comparative judgments.

2. Ground evaluations in established criteria.
   Before deciding, apply `$assessing-genuine-mathematical-progress` to evaluate all current proof strategies.

3. Favor the most promising strategy while maintaining diversity.
   Actively direct resources toward the strategy most likely to yield new genuine progress and those already yield genuine progress recently, while preserving minimal exploration effort (maybe paused until later) of less promising approaches.

### Resource Adjustment Rules

- If a strategy has been pursued for at least two hours without progress, reduce its worker allocation—but not to zero—unless the approach is demonstrably unworkable (e.g., a clear counterexample exists and cannot be repaired into a viable route after genuine effort). In that case (i.e., when the approach is demonstrably unworkable), terminate it.

- If a strategy shows significant progress, increase its worker allocation and correspondingly reduce resources for other strategies.

- Avoid overly even distribution after first explorations (e.g. same number of agents for each strategy). When facing obstacles, shift focus appropriately rather than spreading resources uniformly across all strategies.

### Cross-Approach Progress

Facts or methods discovered in one strategy may substantially help another strategy that is currently stalled. Actively instruct workers to draw on all accumulated findings and revisit previously blocked strategies with fresh progress when no approach with more promising progress exists.

## Output Contract

A new allocation: which workers move to which strategy, issued as tasks (`pharos assign`, each a full TASK.md carrying the strategy's context and the cross-approach findings it should draw on), and the allocation with its reasons recorded on `ROUTES.md` (its format: `$checkpoint`). A strategy terminated here is terminated under `$determining-when-to-abandon-a-proof-strategy`.

## Tools

- `pharos status`, `pharos assign` (the roster and the reallocation — `$allocate-workers`)
- `gm_search` / `gm_get`, `fact_search` / `fact_get` (the findings a stalled strategy should draw on)
- `pharos sub` (an independent evaluation when a judgment is close)
