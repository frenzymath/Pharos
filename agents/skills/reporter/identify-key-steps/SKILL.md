---
name: identify-key-steps
description: For each route, find where the real mathematical work is — the main theorem it has actually achieved, the few lemmas and propositions that carry its mechanism, which of their proofs are nontrivial, and the exact step inside each nontrivial proof that is not routine. Use when writing the Routes section of the human report, before identify-key-ingredients; every claim grounded in a fact_id, nothing from a route's expectations presented as achieved.
---

# Identify Key Steps

Paths below are relative to `<project>/reporter/`. When using this skill
from the project main session for a paper, resolve them from the current
project root by dropping the leading `../`.

You are the reporter. Use this skill to read a route the way a referee reads a paper: past the 
bookkeeping, to the handful of results that carry the idea, and inside those
proofs to the one step where the argument carries most novelty, hard work and is non-routine. The
reader of the report is an expert with little time; what they need from you is
not the list of facts but the location of the work.

Run it once per live route — a route `../ROUTES.md` (the live board; the
checkpoint's copy may be behind it) marks primary or secondary, and a parked
route the checkpoint grades; a dead, human-closed, or ungraded parked route
gets one paragraph from the board, not a block — and once for the project if
the established key theorems span routes. Its output is the input of `$identify-key-ingredients`.

## Input Contract

Read, for the route under examination:

- the latest checkpoint (the last file by name in `../checkpoints/`): its
  **Key theorems** section — established, with the `fact_id`s that together
  support each, and expected, per route — and the route's entry on
  `../ROUTES.md` (mechanism, frontier, history, what killed or parked it);
- the route's verified facts: start from the `fact_id`s the checkpoint names,
  `fact_get` each, and walk `predecessors` down to the leaves — that walk is
  the route's **support closure**; add what `fact_search` finds under the
  route's own vocabulary that the checkpoint did not name;
- the proofs of the candidates for key results: `fact_get(fact_id,
  with_proof=True)` — you cannot classify a proof you have not read;
- the swarm's record of producing them: `gm_search(kinds=["verification"])`
  for rejections and repairs of these statements before they passed;
  `dead_end`, `obstacle`, and `proof_attempt` findings on the route
  (`gm_search`, then `gm_get` the few that matter);
- `../literature/SURVEY.md` — what the field already had, so that "standard"
  is judged against the field, not against your own familiarity.

## Procedure

1. **Fix the main theorem the route has actually achieved.** The strongest verified statement on the route, at the granularity a paper would state it or best presents the current progress.
2. **Extract the verified skeleton.** (The checkpoint's "proof skeleton" is the planned architecture; this is the verified one — keep the names apart in the report.) Inside the support closure, find the results an expert would state as numbered propositions: the facts most cited by other facts in the closure, the facts on the chain from the leaves to the main theorem, and the facts whose statement *is* the route's mechanism (the reduction, the construction, the essential supporting/technical lemma).
3. **Classify each skeleton proof as routine or nontrivial**, by reading it
   against the criteria below. Do this per proof, not per statement: a deep
   statement can have a routine proof once its predecessors exist, and a
   modest statement can hide the only real work on the route.
4. **Locate the nontrivial step.** In each nontrivial proof, find the claim or paragraph where the work happens — the step a referee would check hardest — and describe it: what the step does, which criterion makes it non-routine, and what it depends on (the hypothesis it uses, the object it constructs, the result it cites). That dependency is the hand-off to `$identify-key-ingredients`.
5. **Corroborate with the process record.** A statement the verifier rejected and the worker repaired, a sibling's dead end on the same statement, a key-failures summary that names this step — these support "nontrivial".  Read the rejection before counting it: a rejection for hygiene (an undefined symbol, a missing citation format) says nothing about the mathematics, and a proof that passed first time can still be the hard one. A statement whose `verification` entries show several rejection–repair rounds before it passed may be nontrivial; you have no view of a worker's time, so infer effort from the record only.
6. **Draw the line between verified and expected.** For the route as a whole,
   state where the facts end and the route's claims begin. Nothing from the
   checkpoint's *expected* theorems is presented as achieved.

### Criteria for a nontrivial step

These are the criteria `$paper-structure-planning` applies to statements when
it picks a paper's key theorems; here they are applied to proofs and steps.
A step is nontrivial when at least one of these holds:

1. It makes a **choice the statement does not determine** — an auxiliary object, a construction, a decomposition — that had to be found, and the proof does not work for the obvious alternatives.
2. It uses a **hypothesis in an essential, specific way**: the step fails without it, and this is the place where the naive argument breaks. (A hypothesis that is merely restated is not being used.)
3. It carries the argument **from a good case to the general case**, when that passage is where the difficulty of the problem lives.
4. It establishes an **estimate, bound, identity, or property that is not a direct consequence of definitions or routine computations**, or a **case analysis whose completeness is genuinely at issue** — the kind of enumeration that has been wrong before.
5. It cites a nontrivial result from literature and uses it critically. In particular, a step which cites results from famous journals (Duke Math. J., Annals, JAMS, Inventiones, Publ. IHES, Advances, Algebra & Number Theory, J. Differential Geom., Compositio Math., etc.) or famous people (professors at top universities, researchers who have published in Annals/JAMS/Inventiones/Acta/IHES, or PhD students of such people) or new results of the last two years discussed at seminars in top universities (if your session has web search, look for seminar talks by the authors; otherwise use `search_arxiv_theorems` and `../literature/notes/<arxiv_id>.md`, and say the check was not made).
6. It is a step **earlier attempts got wrong or could not close**, on the
   record (`dead_end` and `verification` findings; the main agent's key-failures synthesis is a `dead_end` finding).

### What is routine, and is not listed

- unfolding definitions, substitutions, bookkeeping identities, immediate corollaries by specialization of previous results in the route;
- a standard argument applied with its hypotheses trivially met — a textbook lemma cited and used as it stands;
- formal or categorical manipulation carrying no content, and reformulations equivalent to the statement;
- a finite check or a computation that confirms something: a computation is evidence, never a key step; at most the reasoning that framed it is.
- a toy example that cannot be generalized or does not indicate general methods.

### Signals that should not be overweighted

- **Proof length, fact count, case count.** A long proof is often long
  because it is routine.
- **A fact's position in the DAG.** A leaf can be the key step and the root
  can be glue.
- **Rejections that were hygiene**, not mathematics; and the absence of
  rejections, which proves nothing.

## Output Contract

One block per route, written into the Routes section of the report under
that route's heading; `$identify-key-ingredients` reads it next:

```
### <route> — key steps
Main theorem achieved: <the statement as the facts prove it> — supported by
  <fact_id, …>; covers <all | this part> of the route's target; differs from
  the checkpoint's statement in <…> | matches it.
Major results (the verified skeleton):
  - <statement, one line> (<fact_id>) — its role in the mechanism — proof: routine | nontrivial
  - …
Nontrivial steps:
  - in <fact_id>, at <the claim / paragraph>: <what the step does>; not routine
    because <criterion>; depends on <hypothesis | construction | cited result>;
    corroborated by <rejection / dead end / key-failures entry> | uncorroborated.
Verified vs expected: <where the facts end and the route's claims begin>
```

Rules: every `fact_id` you cite exists (one invented id makes the whole report
untrustworthy to the reader who needs it most); a route with no verified fact
gets the honest block — "no key step yet; the route's furthest point is a
lead" — never a manufactured one; no numerical distance estimates; no process
telemetry inside these blocks (elapsed time, spend, and worker deaths have
their own lines at the end of the Brief). When the checkpoint's key theorem and the facts disagree, the report
carries the facts' version and names the discrepancy — that discrepancy is
itself something the operator should see.

## Tools

- `fact_get` (`with_proof=True` for every skeleton candidate — the proof is what you classify; it returns `predecessors`, which is the closure walk), `fact_search` (facts on the route the checkpoint did not name)
- `gm_search` / `gm_get` (kinds `verification`, `dead_end`, `obstacle`, `proof_attempt` — the process record)
- the latest checkpoint in `../checkpoints/`, and `../literature/SURVEY.md` (what counts as standard in this field)
