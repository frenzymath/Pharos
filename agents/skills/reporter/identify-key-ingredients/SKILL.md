---
name: identify-key-ingredients
description: For each route, name the critical inputs the current progress stands on — the key observation, the key citation (which result in the literature is used essentially, and whether it applies), the key method or theory imported, and the expert's inputs used or not yet used — each located at the fact and step where it enters, tested by removal, and ranked by load. Use after identify-key-steps when writing the Routes section of the human report; a route with progress but no identifiable nontrivial input is itself a finding.
---

# Identify Key Ingredients

Paths below are relative to `<project>/reporter/`. When using this skill
from the project main session for a paper, resolve them from the current
project root by dropping the leading `../`.

Frontier mathematics is not solved by routine checks, routine computation, or
abstract nonsense. Wherever a route has made genuine progress there is a hard
input somewhere — a novel idea, a theorem from the literature, a method brought in
from elsewhere, a hint from the expert — and the report owes the reader its
name and its location. This skill finds that input for each route, tests that
it really is the input, and says what stands on it. 

Run it after `$identify-key-steps`: the nontrivial steps found there are where
the ingredients enter.

## Input Contract

Read, for the route under examination:

- the route's key-steps block: the main theorem, the skeleton, and every
  nontrivial step with what it depends on;
- the facts named there, with proof (`fact_get(fact_id, with_proof=True)`),
  and for any fact that cites the literature its `external_refs` line — read
  `../fact_graph/facts/<fact_id>.md` directly (one known file) — which carries
  key, authors, title, arXiv id, year, and what it was cited for;
- `../literature/SURVEY.md` and `../literature/notes/<arxiv_id>.md` — what the
  field already had, and how the key papers do it, so that an imported method
  is recognized as imported and a "new" observation is checked against the
  survey;
- `../expert_guidance/INSTRUCTIONS.md` and `../expert_guidance/GUIDANCE.md` —
  every instruction and hint the expert gave, dated, and the do-not-cite
  list; the ledger is in the expert's own language — quote an entry
  verbatim, then gloss it;
- the route's origin on `../ROUTES.md`, the live board (expert-recommended ·
  from the literature · the main agent's own), and the technique-inventory findings in
  global memory (`gm_search`, kinds `direction` and `plan`);
- `search_arxiv_theorems`, to check that a cited statement is what the proof
  says it is and that the version cited is current.

## Procedure

1. **Trace each nontrivial step to what it consumes.** For every step in the key-steps block ask: what does this step use that a routine argument would not have had? Follow the answer to its source and classify it:
   - **Key observation** (internal to the project): a reformulation, an invariant, an auxiliary construction, a coincidence noticed, a choice of object or parameter that makes the argument go, a technical supporting lemma. 
   Locate its first appearance — a `fact_id`, a finding id, a route-board entry — and attribute it: a worker (the fact's `author`), a helper's lead as the checkpoint records it, the main agent's route plan (a `plan` finding), or the expert.
   - **Key citation** (external): the exact result — authors, title, arXiv
     id, theorem number, version — from the fact's `external_refs` and the
     citation in the proof. State the hypotheses the cited theorem needs and
     where in the proof they are matched to the actual object; if the
     matching is itself a nontrivial step, say so. Confirm the statement with
     `search_arxiv_theorems`; check the do-not-cite list. Note that a key citation should be a result from literature that is nontrivial itself and critically used in the argument. A strong indicator of a nontrivial cited result: it is from famous top math journals (Duke Math. J., Annals, JAMS, Inventiones, Publ. IHES, Advances, Algebra & Number Theory, J. Differential Geom., Compositio Math., etc.) or famous people (professors at top universities, researchers who have published in Annals/JAMS/Inventiones/Acta/IHES, prize winners such as Fields medalists, or PhD students or collaborators of such people) or new results of the last three years discussed at seminars in top universities (if your session has web search, look for seminar talks by the authors; otherwise say the check was not made).

   - **Key method or theory** (imported technique): the technique, where it comes from (the survey, a note, a paper), what was changed to make it work here, and what it delivers on this route.
   - **Expert input** (human): the instruction or hint in `INSTRUCTIONS.md`
     the step traces back to, by date. Record equally the expert inputs that
     appear in *no* step yet — the reader must see what became of their
     advice, used or not.
2. **Prepare what the expert can settle.** A citation that carries the route
   is a question for the expert — does that theorem apply under these
   hypotheses, is this the right version, is there a sharper result — because
   an expert answers that in a minute and an agent gets it wrong. A method
   whose adaptation is untested and an observation that is still a lead are
   the same kind of question. Phrase each so that it can be answered, and repeat it in the report's closing
   section (questions for the expert, items parked for the operator).

### Criteria for "key"

- **Without it the step does not close**, and no routine substitute exists.
- **It would appear in the paper's introduction** as the main new idea or the
  main tool: the sentence "the key input is …" can be written truthfully.
- It alone can interest an expert, or give an expert confidence in the significance or correctness of the route.

### What is not an ingredient

- standard background: definitions, textbook facts, tools used with their
  hypotheses trivially met;
- a computation that confirms; the reasoning that framed it may be an
  observation, the computation is not;
- reformulations equivalent to the statement, and the problem statement
  itself;
- anything in the do-not-cite list — that is a defect, reported as one.

### Signals that should not be overweighted

- **The number of citations.** One theorem used essentially outweighs ten
  cited in passing; count load, not references.
- **The length of an adaptation.** A method changed in one decisive line can
  be the whole ingredient; a method rewritten at length may deliver nothing.

## Output Contract

One block per route, written into the Routes section directly after the
route's key-steps block; and one project-level box, written into the Brief
at the top of the report:

```
### <route> — key ingredients (in order of load)
1. [observation | citation | method | expert] <what it is, one sentence>
   source: <fact_id + step | finding id | arXiv id · theorem · version | INSTRUCTIONS.md, date>
   enters at: <fact_id, step>; enables: <the key step or result it unlocks>
   status: verified in the fact | lead, unverified | the expert's claim
   why not routine: <one line>
   load: <what fails without it>
   for the expert: <the question it raises, if any — else omit the line>
Expert inputs not yet used: <date · one line each> | none on record
Diagnostic: <no concern | progress looks routine because … | possible hidden input at <fact_id>, <step>: …>
```

```
What the current progress stands on (project-level)
- the <few> inputs every live route depends on, one line each with where they enter
- load-bearing citations for the expert to check: <arXiv id · theorem · used at fact_id>
- routes with no identifiable nontrivial input: <names> | none
```

Rules: every `fact_id`, finding id, and arXiv id you cite exists and says what
you say it says; an ingredient is never invented to fill a section; status is
stated honestly — a lead is a lead even when it is the best idea on the route;
no numerical distance estimates; no process telemetry inside these blocks. The
expert's inputs are
reported whether or not they helped.

## Tools

- `fact_get` (`with_proof=True`), and `../fact_graph/facts/<fact_id>.md` for a known fact's `external_refs`
- `search_arxiv_theorems` (confirm a cited statement and its version)
- `gm_search` / `gm_get` (the technique inventory — kinds `direction`, `plan` — and the finding where an observation first appeared)
- `../literature/SURVEY.md`, `../literature/notes/`, `../expert_guidance/INSTRUCTIONS.md`, `../expert_guidance/GUIDANCE.md`, the latest checkpoint's route board
