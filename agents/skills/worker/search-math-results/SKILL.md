---
name: search-math-results
description: The default literature workflow — find theorems, constructions, examples, counterexamples, and background for the step you are stuck on, and actually read what you find.
---

# Search Math Results

Search is conditioned on the route you are pursuing and the specific missing
step: know what mechanism you are looking for before you type a query.

## How to search

1. **Check shared memory first** (`gm_search`) — a sibling may already have
   found and used the result.
2. **`search_arxiv_theorems` is the primary tool.** Phrase queries as complete
   mathematical statements when possible, but also query by mechanism ("a
   compactness argument that survives losing X") when that targets the gap
   better. Each hit returns the verbatim theorem text plus `arxiv_id` and
   `theorem_id` — those identifiers are how you pull the exact paper.
3. **Search wide.** Do not restrict yourself to the surface vocabulary of the
   problem: nearby variants, other fields, and proof-level or theory-level
   analogies are all fair game whenever they plausibly transfer to the same
   missing mechanism — say what the transfer idea is.
4. **Fall back to the built-in web search** when the theorem search comes up
   weak — for specific results, terminology, standard references, canonical
   constructions.
5. **An errored search is an outage, not absence.** The search tool returns an
   explicit `error` with empty results when the service is down; never turn
   that into "nothing in the literature". Retry or use the fallback.

**Obstruction/impossibility search is gated.** Do not open with "is the whole
goal impossible" — that search is allowed only when the run has narrowed to a
mature, repeatedly-failed subproblem (and targets THAT subproblem), or when the
assignment explicitly asks for negative results.

## Read what you find — this is where the value is

- **A useful hit is a paper to read, not a snippet to quote.** Download the
  exact paper into `downloads/`, extract its text **once** (keep the `.txt`
  beside the PDF), and read the relevant part before relying on the result.
  Later rounds read the saved text — do not re-run extraction on the same
  paper every round. Note in local memory which papers and pages you have read. Look in
  the project's `../../literature/papers/` first (the main agent's survey
  keeps one copy of every paper read, PDF and `.txt`) and read that exact
  path if it is there; never grep a folder recursively as a substitute for
  search.
- **Check the project's do-not-cite list first** — the "Do not cite /
  superseded" section of `../../expert_guidance/GUIDANCE.md` (two levels up
  from your home). A source listed there is off limits whatever the search
  returns.
- **Cite the current version.** Check the latest arXiv version and any
  corrigendum before relying on a stated range or constant. Record the version you used with the reference.
- **Read the proof, not just the statement**, and extract the techniques,
  reductions, and constructions that could carry over to your target.
- **Expand the definitions from the paper's own context** and check the result
  actually applies in your setting — the same words often mean different
  things in different subfields.
- **A partial result gets a failure analysis**: which extra hypotheses its
  method needs, where the proof breaks without them, and what obstruction that
  reveals. Do not just force your object to satisfy the extra hypotheses.
- **A new direction earns at least one exact paper** before you reject it:
  when a branch opens a genuinely new class of objects or body of machinery,
  read one or a few exact relevant papers — not zero, and not a pile.

## Record

- The search itself is process: note it in local memory (`events`) — queries,
  what came back, why it was or wasn't useful; on a dead end, note the
  attempted queries and why the results failed you.
- A reference you actually **use** goes into the proof step that cites it, with
  its complete statement and identifiers (`title`, `authors`, `arxiv_id`,
  `theorem_id`, year) — and into `external_refs` when that proof is submitted
  via `fact_submit`.
