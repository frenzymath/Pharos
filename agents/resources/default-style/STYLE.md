---
name: default-style
description: The default house style of a Pharos paper — its voice, the shape of its introduction and of its technical sections, and its format through the template. A project replaces it by providing its own style/STYLE.md.
---

# The default style

A reader of the finished PDF sees a paper — not an assembly of verified
facts. This file describes how such a paper reads and how it is shaped. The
format is whatever the template fixes; the default template, `TEMPLATE.tex`
beside this file, uses `article` at 11pt, Latin Modern with microtype,
one theorem counter per section (`Theorem 2.1`,
`Definition 2.2`, `Remark 2.3`), equations numbered by section, a table of
contents, an appendix, and a bibliography with alphabetic labels.

## Structure

```
abstract          what is proved, then the mechanism
1  introduction   background · previous study · what we achieve (the main
                  theorems, in full) · key contributions · roadmap
2  setting        standing notation and assumptions stated once (when the
                  paper needs it)
3… technical      one or two results each, in dependency order; the main
                  theorem's proof last among them; a mechanism-revealing
                  section (a second proof, the geometry behind the
                  statement) when the paper has one
```

The abstract says what is proved, in two to four sentences a non-specialist
in the subfield can follow, then the mechanism in one sentence. When the
paper has a setting section, the standing notation and assumptions are
stated there once and the technical sections refer to it; a short paper
states them in the introduction instead. The acknowledgements close the
introduction as an unnumbered section, and the appendix follows the body, as
the template provides.

## The introduction

Five parts, in this order, then the acknowledgements.

1. **Background.** The objects, notations and the problem, defined precisely
   enough that the main theorem can be stated with them — in the field's own
   terms, with the originating references. Why the problem matters, in a
   sentence or two, not a paragraph.
2. **Previous study.** What is known: the results and conjectures this paper
   touches, who proved what and for which families or cases, each with its
   citation. It ends where the literature stopped: the barrier — what the
   known methods could not do, and why. Every paper that passes the bar for
   citable work is mentioned here, so that previous work is fully respected.
   The bar: a paper that has appeared in a mathematics journal, or an arXiv
   preprint of the last three years whose authors have journal publications
   within the last four years, are PhD students of such authors, or have
   presented the work at a research seminar.
3. **What we achieve.** "We show that …" in one sentence. Then the minimal
   setup the statement needs, and the main theorems stated in full and
   numbered. After each theorem, one paragraph reading its hypothesis. Then
   the corollaries; and when the result is constructive or existential, a
   concrete instance with the actual numbers.
4. **Key contributions.** What is new here and what made the result possible —
   the key observation, the result from the literature used in an essential way, the
   method imported and adapted; why the previous approaches could not do it,
   and how this one gets past the barrier named in part 2; and how the result
   compares with the literature — sharper, more general, the first over every
   field, the first counterexample. The paragraph names inputs and
   mechanisms, never routes, workers, or the process.
5. **Roadmap.** One paragraph: what each section does, by reference.

## Technical sections

- A section opens by fixing the notation it inherits ("We retain the
  notation of the introduction") and by stating what it proves or achieves.
- A definition marks the defined term with `\emph{}`. A characterization is
  an `enumerate` with roman labels, `\begin{enumerate}[label=(\roman*)]`.
- Lemmas and propositions build to the section's result; the proof of a
  theorem stated in the introduction is `\begin{proof}[Proof of
  Theorem~\ref{thm:main}]`. A `remark` holds an alternative proof, a
  generalization not pursued, or a known special case.

## Voice

- Short declarative sentences, in the first person plural, present tense
  for mathematics ("We show that", "The hypothesis says that"). One idea per
  sentence; a paragraph opens with what it establishes.
- A theorem, then its reading: after every stated result, a sentence or a
  paragraph in words — what the hypothesis means, what the conclusion buys.
- Displayed is what has a sum, a fraction, or a quantifier chain; inline,
  only what fits a line without strain. An equation gets a number only if
  something refers to it.
- The bracketed name of a theorem (`\begin{theorem}[…]`) holds an
  attribution or a short conventional name, never a summary of the content.
