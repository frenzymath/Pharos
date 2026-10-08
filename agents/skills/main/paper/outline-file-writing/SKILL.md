---
name: outline-file-writing
description: The content and format of paper/OUTLINE.tex — the compilable LaTeX skeleton every section writer fills in and every verifier judges against: its structure, what it states and what it leaves out, the comment block over every theorem, labels, macros, the reference collation, and how to check that it compiles.
---

# Writing OUTLINE.tex

`paper/OUTLINE.tex` is the **skeleton** of the finished paper. It exists to
give the section writers one uniform frame to fill in, and the verifiers one
text to judge against: every statement the sections share is stated here,
once, in the paper's own notation — and nothing is proved here. A section
writer can look facts up itself; the outline carries only what is listed
below, and is as short as that allows. The thinking behind it — which
theorems are key, which concepts get a name, how the body is cut — is
`$paper-structure-planning`; this skill is about the file.

## The structure of OUTLINE.tex

A bare LaTeX body — no `\documentclass`, no `\usepackage`, only the
environments the template defines (the template's preamble lists them:
`paper/src/template.tex` once it exists, else the project's style template —
`style/TEMPLATE.tex` if the project provides one, else
`style/default/TEMPLATE.tex`) — that compiles when dropped into the project
template (see "It must compile"). In this order:

1. **The macro block.** At the very top, one `\providecommand` per piece of
   global notation, each with a one-line comment saying what it denotes.
   `\providecommand`, not `\newcommand`: the same block is copied into the
   preamble of `paper/src/template.tex` at stage 2, and the outline must
   still compile through that template afterwards.
2. **Introduction** — a placeholder: the `\section` line, its label, and
   one comment line per part of the introduction the style file prescribes
   (`$paper-style`), so that its shape is visible; no prose. It is written
   for real at polish (stage 3), not here.
3. **Notation and terminologies** — written for real, here: the definitions
   and notation that do not depend on a theorem holding. The standing
   setting (a `setup` environment), the global notation in words, and every
   concept or setting the paper uses in a sense that could be ambiguous —
   even a well-known one — explained once.
4. **The body sections** — one `\section` per section home, each carrying
   the statements listed under "What the outline should contain", every
   theorem under its comment block, no proofs.
5. **The reference collation** — the last part of the file: a
   `thebibliography` block holding every citation the paper will use, each
   entry audited in the comments above it (see "Comment format").

**Section names.** Give every section, the introduction included, a name of
the form `NN-slug` (`01-introduction`, `02-notation`, `03-…`), numbered from
`01` in the order of the paper. The name is the section's directory under
`paper/src/sections/` — `pharos paper assign <name>` creates it, and
`pharos paper build` assembles sections in sorted name order — and its label
`sec:<name>` carries it (see "Labels and macros").

## What the outline should contain

Each statement below is written as `$statement-writing` prescribes — which
facts fold into one statement and which stay apart, and how hypotheses,
connective, and conclusion are phrased in the paper's notation.

- **Every key theorem**, as `$paper-structure-planning` identifies them —
  stated exactly, with no proof.
- **Every other cross-section statement and definition** — a result one
  section proves and another uses — stated exactly, with no proof.
- **Every external result the paper depends on**, stated as a theorem in the
  section that first uses it, marked `cited` in its comment block with its
  source (see "Comment format"); later sections cite it by label.
- Any **new concept or setting** the paper introduces, defined once, in the
  body section where it belongs.
- Every concept or setting that could be ambiguous, even a well-known one,
  in the notation and terminologies section, explained once.
- **Notation aligned globally** — one symbol, one meaning, across every
  section; a later section may not silently redefine it.
- The **last part of the file is the reference collation** — a
  `thebibliography` block, not a `\section` and with no section home — every
  citation the paper will use, gathered and audited right there: does the reference exist, and is the
  conclusion attributed to it actually what that source states. Start from
  the `external_refs` of the facts the outline rests on and from the papers
  the introduction will discuss (`literature/SURVEY.md` when the project has
  one; otherwise the facts' `external_refs` and `materials/` are the whole
  list — do not run the `prior-work` survey for this).

## What the outline should not contain

- the proof of any theorem — not a sketch, not a hint; the writer gets the
  argument from the facts named in the comment block;
- auxiliary lemmas internal to one section;
- prose: no motivation, no remarks, no examples — the statements, their
  comment blocks, and the definitions are the whole file.

## Comment format

These comments are for the section writer that will expand the statement;
they never reach the paper. One fixed block, immediately above every
theorem-like statement (`theorem`, `proposition`, `lemma`, `corollary`,
`conjecture`) and every definition in a body section:

```latex
% facts:   3f2a9c1b7e5d0a44, 8c1d2e3f4a5b6c7d
% owner:   sec:04-reduction
% depends: prop:finiteness
```

- `facts:` — the `fact_id`s this statement rests on. When the statement is
  the combination of several facts, list them all here, in one block. For a
  definition: the fact whose statement or `glossary_introduces` introduced
  the concept. `none` when no fact stands behind it — an external result,
  or a definition no fact introduced.
- `owner:` — the label of the section that proves it (and, for a
  definition, the section that states it). `cited` when no section proves
  it: an external result.
- `depends:` — the labels of the outline's statements and definitions its
  proof is expected to draw on, outside the notation section; `none` when it
  uses only the notation section. The writer reads it here (TASK.md carries
  none of it) and may cite an earlier outline statement beyond it, reporting
  the addition.

An external result adds a fourth line — its source, and what that source
actually states, in the source's own hypotheses:

```latex
% facts:   none
% owner:   cited
% depends: none
% source:  \cite{smith2023}, Theorem 4.2 — for a projective X with …, it gives …
```

A statement with neither facts nor a source is a gap in the proof, not an
outline entry: a worker proves it first.

In the reference collation, every `\bibitem` carries its audit above it:

```latex
% exists:  yes — arXiv:2301.01234v2; J. Algebra 600 (2023) 1--20 (search_arxiv_theorems, 2026-09-03)
% used by: thm:smith, for its Theorem 4.2
% matches: yes — Theorem 4.2 there assumes exactly … and concludes …
```

`matches: no` is a finding, not a note: the statement that cites it is
wrong as stated, and the outline changes before any section is assigned.

## Labels and macros

- **Every section and every statement carries a `\label`.** The forms,
  fixed here for the whole pipeline:
  - a section: `sec:<name>`, `<name>` its `NN-slug` name
    (`\label{sec:04-reduction}`);
  - a shared statement or definition — one the outline states:
    `<kind>:<slug>`, `<slug>` lowercase and hyphenated, named for the
    content (`thm:main`, `lem:contraction`, `def:admissible-pair`), never
    for a position or an order, and unique across the paper. The outline
    fixes these labels and every section keeps them, so that `\ref`s from
    other sections resolve at build;
  - a section's internal statement — one its writer adds:
    `<kind>:<section-slug>-<slug>`, `<section-slug>` the section's name
    without its `NN-` prefix (`lem:reduction-contraction` in section
    `04-reduction`), so that sections written in parallel never collide;
  - an equation: `eq:<slug>`; an appendix: `app:<slug>`;
  - `<kind>` is one of `thm prop lem cor conj def ex not constr setup rem`
    — one per template environment (`theorem proposition lemma corollary
    conjecture definition example notation construction setup remark`; the
    template lists the kind beside each `\newtheorem`) — plus `sec`, `eq`,
    `app`.
- **Notation is macros.** Every recurring symbol is a macro from the macro
  block, and every global symbol has exactly one meaning across the paper.
  A section defines no macros of its own: when it needs one, that is a
  change to the outline (an escalation), so the whole paper gets it.
  Two TeX habits keep the macros from breaking at their boundaries: a body
  that ends in a superscript or subscript is braced as a whole
  (`\providecommand{\Lamreg}{{\Lambda_N^{\mathrm{reg}}}}`, so that
  `\Lamreg^2` compiles), and a macro is never run into a letter — `\KN{}x`
  or `\KN\, x`, never `\KNx`, which is another, undefined macro.

## It must compile

The outline is checked by compiling it through the project template — the
project's own copy `paper/src/template.tex` once it exists (the first
`pharos paper assign` creates it), otherwise the project's style template:
`style/TEMPLATE.tex` if the project provides one, else
`style/default/TEMPLATE.tex`. From the project directory:

```bash
mkdir -p paper/src
tpl=paper/src/template.tex; [ -f "$tpl" ] || tpl=style/TEMPLATE.tex; [ -f "$tpl" ] || tpl=style/default/TEMPLATE.tex
sed -e 's|%%TITLE%%|Outline|' -e 's|%%SECTIONS%%|\\input{../OUTLINE.tex}|' "$tpl" > paper/src/outline_check.tex
(cd paper/src && tectonic outline_check.tex)   # or, with pdflatex: pdflatex -interaction=nonstopmode outline_check.tex — use the engine on PATH
```

A clean run — no undefined environments, no undefined control sequences, no
duplicate labels — is the check; then remove `paper/src/outline_check.*` one
file at a time (`unlink`).
(A second `thebibliography` from the template is expected: the outline's
block is merged into it by the main agent after the first `assign` creates
the project's `paper/src/template.tex`.) `pharos paper build` never reads the
outline: sections compile through the template, which is why the macro
block is copied into it at stage 2 (`$paper`).

## A skeleton, in miniature

```latex
% paper/OUTLINE.tex — the skeleton every section writes against. Bare body: no preamble.

% ---- macros: the global notation (copied into template.tex's preamble at stage 2) ----
\providecommand{\Fol}{\mathcal{F}}          % the foliation
\providecommand{\KF}{K_{\Fol}}              % its canonical class
% ---- end macros ----

\section{Introduction}\label{sec:01-introduction}
% Placeholder: one comment line per part of the introduction, per the style
% file; written for real at polish. It will state thm:main and place the
% paper relative to \cite{smith2023}.

\section{Notation and terminologies}\label{sec:02-notation}

\begin{setup}\label{setup:standing}
Throughout, $X$ is a normal projective variety over $\mathbb{C}$ and $\Fol$ a
foliation on $X$ with canonical class $\KF$; …
\end{setup}

\begin{definition}[admissible pair]\label{def:admissible-pair}
…
\end{definition}

\section{Reduction to the admissible case}\label{sec:03-reduction}

% facts:   none
% owner:   cited
% depends: none
% source:  \cite{smith2023}, Theorem 4.2 — for a projective $X$ with …, it gives …
\begin{theorem}[Smith]\label{thm:smith}
…
\end{theorem}

% facts:   3f2a9c1b7e5d0a44, 8c1d2e3f4a5b6c7d
% owner:   sec:03-reduction
% depends: thm:smith
\begin{proposition}\label{prop:reduction}
…
\end{proposition}

\section{The main theorem}\label{sec:04-main}

% facts:   a1b2c3d4e5f60718
% owner:   sec:04-main
% depends: prop:reduction
\begin{theorem}\label{thm:main}
…
\end{theorem}

% ---- reference collation: every citation the paper will use, audited ----
\begin{thebibliography}{99}

% exists:  yes — arXiv:2301.01234v2; J. Algebra 600 (2023) 1--20 (search_arxiv_theorems, 2026-09-03)
% used by: thm:smith, for its Theorem 4.2
% matches: yes — Theorem 4.2 there assumes exactly … and concludes …
\bibitem[Smi23]{smith2023} A.~Smith, \textit{Foliations and …}, J. Algebra \textbf{600} (2023), 1--20.

\end{thebibliography}
```

The bracketed `\bibitem` label follows the alphabetic form used by the
template's default Rethlas entry.
The key is the first author's surname followed by the four-digit year, all
lowercase, no punctuation (`smith2023`); a letter suffix disambiguates
(`smith2023a`). The template's Rethlas key, `Ju+26`, is the only exception
when that entry is retained under the operator's disclosure choice
(`$paper-style`).
