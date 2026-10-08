---
name: statement-writing
description: How a theorem-like statement is written, for whoever states one — the outline's shared statements, a section's own lemmas, a verifier reading either. Which facts fold into one statement and which stay apart; how the statement is phrased — hypotheses, connective, conclusion — in the paper's notation, with no argument inside.
---

# Writing a statement

A statement is a `theorem`, `proposition`, `lemma`, `corollary`, or
`conjecture` of the paper. Facts are its raw material, but a fact is a unit
of verification and a statement is a unit of reading: the two rarely
coincide. This skill answers two questions, in order — which facts become
one statement, and how that statement is written — and the answers are the
same for whoever writes one: the main agent stating the outline's shared
statements, a section writer stating its own internal results, a verifier
judging either.

## From facts to statements

One statement rests on one or several facts; one fact never mechanically
becomes one statement. Which statements are the key theorems is
`$paper-structure-planning`'s question; this is about the cut below that.

**Fold facts together when**

- a fact exists only to feed one other fact — its sole use is as a step
  toward that one: it becomes part of that fact's proof and is not stated
  on its own;
- several facts are tightly linked, with involved intermediate hypotheses
  and conclusions, and together yield one clean, relatively independent
  conclusion: state that conclusion once and let the chain be its proof;
- a fact is a reformulation, a specialization, or an unfolding of
  definitions of another — `$paper-structure-planning`'s signs of a
  statement that is not a key theorem: it folds into the statement that
  uses it;
- facts differ only by a case split — a parameter value, a finite list of
  configurations — and are proved by the same argument: one statement, the
  cases enumerated inside it or handled in the proof;
- a fact records a technical estimate or an auxiliary construction used
  exactly once, by the statement it serves: it lives in that proof.

**Keep facts apart when**

- the arguments proving them use markedly different tools: a reader wants
  to see where one kind of argument ends and another begins;
- a fact has several consumers whose uses are unrelated: it stays a
  statement of its own and is cited, never absorbed into one of its
  consequences;
- the fact behind the final target theorem: the target is stated by itself,
  merged with nothing;
- a statement crosses sections — proved in one, used in another: it stands
  under its own label whatever its size, because the outline's statements
  are how sections refer to each other;
- an external result: it stays a `cited` theorem of its own, in the source's
  hypotheses, never fused with what the paper derives from it;
- a fact that introduces a concept the paper names: it becomes a definition
  and a statement, not one block.

Whatever is merged, the merged statement assumes exactly what the facts
jointly assume and concludes exactly what they jointly certify: merging
never strengthens a conclusion, never drops a hypothesis, and never adds a
claim no fact covers. Every fact behind a statement is listed in its comment
block (`$outline-file-writing`), so the merge can be checked against the
facts.

## How a statement is phrased

A statement names its hypotheses, then a connective, then its conclusion.
It is a claim, not a narrative.

```
[hypotheses]   Let X be …, let f : X → Y be …, and assume that ….
[connective]   Then …  |  Then the following hold:  |  The following are equivalent:
[conclusion]   one clause, or an enumerated list (i), (ii), …
```

- **Hypotheses first, in full.** Every property the conclusion needs is
  assumed here, even one that repeats a standing assumption from the
  notation section: a statement is read on its own. This is about
  hypotheses, not symbols — see the next two points.
- **Nothing is defined after it is used.** Every symbol in the conclusion is
  either global notation, or introduced in the hypotheses, or bound by an
  explicit quantifier in the conclusion itself ("there exists $c>0$,
  depending only on $n$, such that …"). A conclusion never ends with
  "where $c$ is …": the object is introduced on the hypothesis side, or
  quantified where it first appears. Introduced means earlier in the text:
  a term or an object that a later statement or proof constructs is not
  available here, however natural its name. An object one result introduces
  and another needs is either given a `definition` of its own before both,
  or named, where it is used, together with the place that introduced it
  ("the map $\phi$ defined in Lemma~\ref{…}").
- **Local versus global notation.** Objects specific to this statement are
  introduced in its hypotheses ("Let $K \subset X$ be compact"). Global
  notation — the outline's macro block and its notation section — is used
  as it stands, never re-explained in a statement and never given a local
  meaning. When a statement translates a fact, the fact's own symbols are
  replaced by the paper's macros wherever they mean the same thing; a
  fact-private symbol the statement still needs becomes a local symbol
  introduced here.
- **Every variable is bound.** "For every", "there exists", or "Let …": no
  free variable whose range the reader must guess, no "for $n$ large"
  without what it depends on. Where a conclusion mixes "for every" and
  "there exists", its wording leaves one reading of which quantifier governs
  which claim — a plural, or a bare noun phrase, where one chosen object is
  meant reads as "every" — and a claim that could be read either way is
  rewritten, most simply by enumerating (below).
- **The conclusion is a claim, not a process.** No "we show", "we now
  prove", "one checks", "it follows that", "since … we have …". A
  hypothesis phrased as a reason ("since $X$ is compact, $f$ is bounded")
  becomes an assumption and a claim ("Assume $X$ is compact. Then $f$ is
  bounded."). Nothing of the proof — no reduction, no computation, no word
  on how it is shown — appears in the statement; all of that is the proof's.
- **Several conclusions are enumerated** — (i), (ii), … or (1), (2), … or
  (a), (b), …, whichever the style file or the surrounding text uses — each
  item a complete claim under the shared hypotheses; an equivalence uses
  "the following are equivalent". Enumerate above all when the claims
  differ in what is fixed and what is chosen — one holds for every value of
  a parameter, another for some value, a third for all large values or for
  all but finitely many: one item per scope keeps each quantifier where the
  reader sees it, whereas a paragraph that runs such claims together is
  where a quantifier gets lost. A conclusion that needs an extra hypothesis
  of its own is a separate statement.
- **Length.** A statement runs long for two curable reasons. It inlines
  something that deserves a name — an object, a class of objects, a
  construction: give it one before the statement, in a `definition` (the
  natural choice), or in a `construction` or `setup` environment when it is
  a procedure or a standing arrangement rather than a concept, and let the
  statement refer to it by name. Or it carries quantities only the proof
  needs — auxiliary constants, intermediate objects from the facts: leave
  them to the proof unless the conclusion is about them. A bundle of
  hypotheses that recurs across statements is a candidate for a named
  concept (`$paper-structure-planning`); a bundle used once is written out.
- **Nothing internal.** No `fact_id`, worker name, or route name inside a
  statement; the comment block above it carries the facts.
- **Environment and name.** `theorem` for a key theorem; `proposition` for a
  substantial result that is not one; `lemma` for a step serving a nearby
  result; `corollary` for what follows from a stated result with little
  work; `conjecture` only for what the paper does not prove. Labels take
  the form `$outline-file-writing` fixes: `<kind>:<slug>` for a shared
  statement, `<kind>:<section-slug>-<slug>` for a section's internal one.

## Before leaving a statement

- Are the hypotheses complete — would the conclusion be false without any
  assumption not written here?
- Is every symbol global, introduced in the hypotheses, or quantified where
  it first appears?
- Does every quantified claim read one way only, and is each scope its own
  item when there are several?
- Is the conclusion a claim in the paper's notation, with nothing of the
  proof in it?
- Does the statement say exactly what its facts certify — no more, no less?
- Is it as short as the previous four answers allow?
