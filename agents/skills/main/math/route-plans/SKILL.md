---
name: route-plans
description: The route-level loop — propose several materially different decomposition plans for the goal, enter them on the route board, probe each through a worker, and when plans fail synthesize the common stuck points before planning again. Use at the opening once the survey exists, whenever the board has fewer than two credible live routes, and whenever the current plans have failed.
---

# Route plans

The main-agent form of the worker skill `propose-subgoal-decomposition-plans`:
the same procedure, one level up. A worker decomposes its assigned statement
into subgoals; you decompose the **goal** into **routes**, and a route's
subgoals are what you hand to workers as tasks. Workers keep their own local
multi-plan thinking inside a route; this skill is about the portfolio.

You do high-level mathematics here — mechanisms, what a route would need,
why it could work, what would kill it. Everything finer is a worker's: the
direct consequences of the goal, the screening of a plan by attempting its
subgoals, the counterexample that would refute a claim. Those are worker
skills (`obtain-immediate-conclusions`, `direct-proving`,
`construct-counterexamples`), and a worker's result can become a fact; a
helper's cannot. **A helper never substitutes for a worker on a statement.**

## Input

- the goal, quoted from `PROBLEM.md`, and the expert's direction
  (`expert_guidance/GUIDANCE.md` — its recommended strategies are routes
  before anything else is);
- `literature/SURVEY.md` — the technique inventory and the candidate routes
  the survey produced (`$prior-work`);
- the workers' findings: `conclusion`, `example`, `counterexample`,
  `dead_end`, `obstacle` (`gm_search`, then `gm_get` the ones that matter)
  and the verified facts that constrain the problem (`fact_search`). If the
  goal's shape is still unclear — its equivalent forms, what any proof must
  respect — assign a worker to derive the immediate conclusions first (its
  `obtain-immediate-conclusions` skill) rather than deriving them yourself;
- the route board, `ROUTES.md`: what is live, parked, dead, and why.

## Procedure

1. Gather the current information that materially constrains the problem:
   useful examples, failed claims, known obstructions, counterexamples,
   relevant results from the survey, and the verified facts and also human expert guidance.
2. Propose **materially different** decomposition plans — Two or three credible plans beat six variants of one. Two plans are materially different when they rest on different key ingredients, a different mechanism or a different critical input, so that the obstruction or counterexample that kills one does not kill the other. Same mechanism with different bookkeeping, the same subgoals in another order, or different notation is one plan.
3. For each plan, state:
   - the main idea of the plan — the mechanism, in a paragraph;
   - the ordered subgoals, each as a task a worker could be assigned, with
     clear deliverables (general statements, never instance tables);
   - why this plan is plausible given the current information — which
     facts, examples, and results it rests on;
   - which earlier failures, counterexamples, or obstructions it tries to
     avoid, and how;
   - the first statement that would show it is working, and the decisive
     obstacle you expect.
4. Choose each plan's **probe**: the one statement whose outcome would tell
   the most — usually the first load-bearing subgoal, or the claim the whole
   mechanism rests on — and assign it to a worker as a full task
   (`$allocate-workers`). The worker screens the plan the way its skills
   say: attempt it directly, hunt for a counterexample when it blocks,
   report the stuck points. You read the outcome; you do not attempt the
   subgoal yourself and you do not have a helper attempt it.
5. A claim a plan rests on that feels fragile is tested the same way: a
   worker's task to construct a counterexample (its
   `construct-counterexamples` skill), before anything stands on the claim.
   A counterexample that kills a route is worth a fact.

## Output

Publish one `plan` finding per decomposition (`gm_add`, kind `plan`, a
judgment): `claim` = the plan's goal + summary, `evidence` = its motivation,
carrying these fields:

```json
{
  "plan_id": "...",
  "record_type": "decomposition_plan",
  "goal": "...",
  "plan_summary": "...",
  "subgoals": ["..."],
  "motivation": ["..."],
  "uses_information_from": {
    "examples": ["..."],
    "counterexamples": ["..."],
    "key_failures": ["..."],
    "search_results": ["..."]
  },
  "status": "proposed|screening|screened|selected|failed|solved",
  "route": "the route board name"
}
```

Then enter each plan on `ROUTES.md` (its format: the `checkpoint` skill) with its
origin — expert-recommended, from the survey, or your own — its status, and
its probe (which worker, which statement). A plan that is never entered on
the board does not exist for the project.

## Reading a probe

The probe comes back as the worker's findings and facts: a `proof_attempt`
or fact (the statement went through — the plan is **selected**, give it a
standing allocation and its next subgoals), a `counterexample` (the claim is
false as stated — the plan is dead or must be restated), an `obstacle` /
`dead_end` with concrete stuck points (the plan is **failed** at this probe —
its stuck points go to the synthesis below). Grade the plan by what the probe
produced, in the plan's history on the board; never by how the attempt
felt.

## When plans fail — synthesize before planning again

The main-agent form of the worker skill `identify-key-failures`, across the
whole portfolio, because the pattern that matters is usually only visible
from above. Inputs: the failed plans and the routes parked or dead on the
board; the probes' stuck points (workers' `proof_attempt` findings with
status `stuck`, their `obstacle` findings); the swarm's `dead_end` findings
and the `verification` rejections (`gm_search(kinds=["verification"])` —
what the verifier keeps refusing is a failure pattern too); the relevant
`counterexample` and `example` findings.

1. Gather the reports from all failed plans; if only the probes have run so
   far, work directly from the probe failures.
2. List the key stuck points for each plan.
3. Identify what is common across those failures: recurring obstructions or
   counterexamples; decomposition patterns that keep breaking; search gaps
   or missing background (`$prior-work`, narrowly, at the obstruction); the
   verifier's recurring objections (a hypothesis everyone forgets, a case
   nobody covers).
4. Summarize what the failures suggest for the next generation of plans:
   what any new plan must avoid, what it must first establish.
5. When every plan has failed and no pattern leads anywhere, reason at the
   level of mechanisms — helpers may think with you on orthogonal questions
   — before planning again; never re-issue the same routes in new words
   without any updates or reflections drawn from the previous mistakes.

Publish the synthesis (`gm_add`, kind `dead_end`): `claim` = the common
stuck points, `evidence` = the per-plan failures, carrying:

```json
{
  "record_type": "key_failures_summary",
  "failed_plan_ids": ["..."],
  "plan_failures": [{"plan_id": "...", "stuck_points": ["..."]}],
  "common_failures": ["..."],
  "implications_for_next_plans": ["..."]
}
```

Close the plans on the route board (dead, with what killed each — a plan is
abandoned only under the conditions of
`$determining-when-to-abandon-a-proof-strategy`, and never while its recent
work directly aids the main proof) and carry
the common failures into the checkpoint's **What is dangerous** — where a
future session, and every task you write, will meet them. If the reports
are too weak for a real synthesis, say so on the board and name what is
missing; one targeted worker task usually settles it. Then plan again.

## Not ready?

If you cannot yet propose meaningful plans, say so on the board (an
"untried" entry naming the missing information and the blockers) and get the
information: a worker on the immediate conclusions or on a toy example, or
`$prior-work` at the obstruction.

## Tools

- `gm_add` (publish the plan findings) · `gm_search` / `gm_get` (recall the
  examples, counterexamples, and dead ends the plans build on) ·
  `fact_search` / `fact_get` · `search_arxiv_theorems`
- `pharos assign` (the probe, and every subgoal, as a worker's task)
- `pharos sub` only for a digest you need first (what do the dead ends on
  route X have in common; what does paper Y's method require) — reading,
  never the mathematics
