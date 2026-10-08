---
name: prior-work
description: The opening literature phase — survey everything already known about this problem, download and read the key papers into literature/, write the detailed SURVEY.md (known results, each key paper's method, the technique inventory), and turn every plausibly transferable technique into a candidate route on the board, each of which gets a real probe. Rerun narrowly at every new obstruction.
---

# prior-work — survey the field before choosing a route

A research problem is never attacked from nothing. Before the first route
decision, this project owes itself a real survey: 
- what is known, exactly and with versions. This inludes similar problems or conjectures or analogues in the same field or related fields, known cases or conditional results of the problem or conjecture, developed techniques or framework for these types of problems in the area, related technical lemmas or theorems.
- how the key papers actually do it; which of their techniques or methology plausibly transfer here; and where each is expected to break.
- The survey is the source of the route board: most routes pursued by a strong project should first appear here. If a potentially useful technique is omitted entirely—not evaluated, attempted, or deliberately deferred—treat that omission as a gap/defect in the route board.

## When

- **At project opening**, after reading `expert_guidance/GUIDANCE.md` and
  **before the first route decision**. The first pass is measured in hours,
  not days: enough to frame the first assignments, then refine while workers
  run. The expert's recommended strategies are already on the board above
  everything the survey adds.
- **Again, narrowly, at every new obstruction** — the same discipline aimed at
  the obstruction, extending `SURVEY.md` rather than starting over.

## Who does what

- **You orchestrate and judge.** Run the first broad `search_arxiv_theorems`
  sweep yourself — it is cheap and shows you the shape of the map — then fan
  out helpers, one per direction, with `pharos sub`. Read the returned notes
  and the decisive parts of the key papers yourself before writing
  `SURVEY.md`: the judgment of what transfers is yours.
- **Helpers run every errand** — search, download, extract, read, note. They
  have `search_arxiv_theorems`, `gm_search`/`gm_get`, `fact_search`, web
  search and a shell. They report; they decide nothing.
- **Workers never.** A worker's task is a piece of mathematics; it searches
  for itself when its own proof needs a reference (its `search-math-results`
  skill), and it reads this folder.

## The folder

```
literature/
  SURVEY.md                    the survey and the candidate routes — you write it
  papers/<arxiv_id>.pdf|.txt   every paper read: the PDF, its text extracted once
  notes/<arxiv_id>.md          one note per paper, in the fixed form below
```

One copy per project: a paper downloaded here is never downloaded again, and
workers read `literature/papers/` too.

## How to search

1. **Check shared memory first** (`gm_search`, then `gm_get` the few that
   matter) — an earlier pass or a worker may already have found and used the
   result.
2. **`search_arxiv_theorems` is the primary tool.** Phrase queries as complete
   mathematical statements when possible, but also query by mechanism ("a
   compactness argument that survives losing X") when that targets the gap
   better. Each hit returns the verbatim theorem text plus `arxiv_id` and
   `theorem_id` — those identifiers are how you pull the exact paper.
3. **Search wide.** Do not restrict yourself to the surface vocabulary of the
   problem: nearby variants, stronger and weaker hypotheses, other fields, and
   proof-level or theory-level analogies are all fair game whenever they
   plausibly transfer to the same missing mechanism — say what the transfer
   idea is. Do not stop after the first plausible hit.
4. **Fall back to the built-in web search** when the theorem search comes up
   weak — for specific results, terminology, standard references, canonical
   constructions, and the papers that cite a key paper.
5. **An errored search is an outage, not absence.** The search tool returns an
   explicit `error` with empty results when the service is down; never turn
   that into "nothing in the literature". Retry or use the fallback.

**Obstruction/impossibility search is gated.** Do not open with "is the whole
goal impossible" — that search is allowed only when the run has narrowed to a
mature, repeatedly-failed subproblem (and targets THAT subproblem), or when the
expert explicitly asks for negative results. Known negative results that the
survey meets on its way are recorded, not hunted.

## Read what you find — this is where the value is

- **A useful hit is a paper to read, not a snippet to quote.** Download the
  exact paper into `literature/papers/`, extract its text **once** (keep the
  `.txt` beside the PDF), and read the relevant part before relying on the
  result. Later passes read the saved text — never re-extract the same paper, and never
  grep the folder recursively as a substitute for search.
- **Check the do-not-cite list first** — the "Do not cite / superseded"
  section of `expert_guidance/GUIDANCE.md`. A source listed there is off
  limits whatever the search returns.
- **Cite the current version.** Check the latest arXiv version and any
  corrigendum before relying on a stated range or constant. Record the version with every reference.
- **Read the proof, not just the statement**, and extract the techniques,
  reductions, and constructions that could carry over to the target.
- **Expand the definitions from the paper's own context** and check the result
  actually applies in this setting — the same words often mean different
  things in different subfields.
- **A partial result gets a failure analysis**: which extra hypotheses its
  method needs, where the proof breaks without them, and what obstruction that
  reveals. Do not just force the object to satisfy the extra hypotheses.
- **A new direction earns at least one exact paper** before you reject it —
  not zero, and not a pile.

## The helper's brief and its note

Hand each helper one direction, the seed hits (ids) you already have, the
folder paths, the do-not-cite section, and this form for every paper it
reads — `literature/notes/<arxiv_id>.md`:

```
title · authors · arxiv id · version read · date
Exact statements used (theorem numbers, hypotheses verbatim)
Mechanism of the proof, in a paragraph
What the method needs (hypotheses, structure, inputs)
How far it gets toward our goal, and where it breaks
Techniques that might transfer, each with the transfer idea
Do-not-cite check · open questions · what was searched and not found
```

## SURVEY.md — the detailed survey

Dated at the top, revised in place with a dated revision note whenever a later
pass changes the picture. It holds the mathematics; route *status* lives on
the board, never here in a second copy.

1. **The problem in the field's terms** — standing definitions, how the goal
   relates to what is known, the precise sense in which it is open.
2. **Known results** — the strongest results toward the goal, each stated
   exactly with hypotheses, `arxiv_id`, theorem number and version; and what
   is known to fail.
3. **Key papers and how they do it** — per paper: the mechanism, what it
   needs, how far it gets, where it breaks for this goal.
4. **Technique inventory** — each technique: what it does, why it works, its
   exact applicability and limits, the identifiers, how it might connect to
   the problem.
5. **Candidate attack routes** — one per plausibly transferable technique or
   combination: name; the transfer idea; the first statement it would need;
   the expected obstacle; the first probe (a framed worker task, or a helper
   investigation when it is not yet a statement).
6. **Obstructions, negative results, near-misses** met on the way; **open
   threads**; the queries tried that found nothing.

## Sync with the board

- **Every candidate route goes onto `ROUTES.md`** (its format: the
  `checkpoint` skill), origin "literature (arxiv id)", below the
  expert-recommended routes and above nothing else yet.
- **Every candidate gets a real probe before it can be parked** — try each
  once: a framed worker assignment or a helper investigation whose outcome
  is recorded in that route's history on the board. A technique nobody tried
  is an *untried* route, and the board says so; it is never quietly dropped.
- The technique inventory also goes to global memory as findings (`gm_add`,
  kind `direction` or `plan`, one per technique with its identifiers), so
  workers meet it through `gm_search`. Literature notes are leads, never
  facts: their mathematical use is verifier-gated like everything else.
- Learn and imitate the successful strategies before claiming that a new
  mechanism is needed — and when the survey shows the goal sits on a known
  cliff, say so on the board rather than in a quieter place.
