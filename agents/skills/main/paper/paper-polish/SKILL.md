---
name: paper-polish
description: Stage-3 readability pass — seams harmonized, the introduction written for real to the style file, the front matter and any retained acknowledgements and AI appendix filled in the project's template copy from the project's records, the bibliography checked, then the build; no mathematical change.
---

# Paper polish

Stage 3 runs once every section has passed its own verifier and the
whole-paper verifier has passed. Its only job is readability.

## No mathematical changes

No mathematical claim, proof, or supporting citation may change here — no
new statements, no rewording that shifts a hypothesis or a conclusion, no
reordering that changes what a proof relies on. If polish surfaces a real
mathematical problem, that is an escalation back to the outline, not
something to fix in place.

## Paper disclosure

Read the operator's choices in `expert_guidance/INSTRUCTIONS.md` and apply
them to the project's template copy and acknowledgements. The default
includes the abstract's system disclosure, system and team
acknowledgements, the Rethlas reference and the AI appendix. The operator
may explicitly modify or omit any of them for this paper; otherwise keep
the defaults. This choice does not waive the mathematical requirements.

Use the operator's information and project records for contributions,
funding, system use and verification. Do not infer human verification or
author contributions from an automated job's completion. If required
information is missing, report it and leave the draft incomplete rather
than inventing a claim or filling a placeholder with a guess.

## Harmonize the seams

Sections were written somewhat independently against a shared outline; read
them consecutively and fix what only shows up at the join: repeated setup,
inconsistent terminology for the same object, a transition that doesn't tell
the reader why the next section is next, notation that is technically
consistent but reads jarringly different section to section. The voice you
harmonize to is the style file's (`$paper-style` says which file that is).

## Write the introduction for real

The outline's introduction was a placeholder. Now that the body exists,
write it: read the style file's section on the introduction and write to
it, part by part, in its order. Two things the style file cannot supply:

- The main theorems are stated exactly as the body proves them — same
  hypotheses, same conclusion — with every symbol they use declared before
  the statement, in the introduction itself. A restated theorem carries the
  introduction's own label (`thm:introduction-<slug>`), never the body's,
  and the paragraph that reads it names the body theorem it restates and
  the section that proves it (`Theorem~\ref{thm:introduction-main} is
  Theorem~\ref{thm:main}, proved in Section~\ref{sec:06-…}`) — which is
  how the whole-paper verifier pairs the two.
- The key-contributions paragraph is drawn from `$identify-key-steps` and
  `$identify-key-ingredients`, run over the final checkpoint. It names
  inputs and mechanisms — the key observation, the result from the
  literature used essentially, how the barrier was passed — never routes,
  workers, or the process by which they were found.

## The front matter — the project's template copy

`paper/src/template.tex` is the project's copy of the paper template; the
build compiles it. Fill in the title (the build otherwise prints the
project's name), the author block, the MSC line if wanted, and the abstract.
Its default closing sentence is "The main result of this paper was
obtained using the Pharos system."; apply the operator's disclosure choice.
Check that every macro of the outline's macro block is in the preamble;
add any still missing.

## The acknowledgements

The template copy carries an unnumbered `Acknowledgements` section after the
sections. If retained, move it to the end of the introduction and fill it.
Three parts, kept apart, in this order: funding; the people who verified or
commented on the paper; the default system sentences the template carries
(Pharos built on Rethlas, `\cite{Ju+26}`, the Pharos developers and feedback
contributors thanked separately, the pointer to Appendix~`\ref{app:ai}`,
the authors responsible for correctness). Apply the operator's changes or
omissions, and remove the appendix pointer if that appendix is omitted.
Funding and personal thanks use only supplied information; omit unfilled
optional lines.

Pharos's developers are Bin Dong, Guoxiong Gao, Jiedong Jiang, Shurui Liu,
Zeming Sun, and Bin Wu, in that order. In the default acknowledgements,
keep the template's separate thanks for feedback and suggestions after the
developer thanks, preserving the name order within each group.

## Appendix A — the use of generative AI

If retained, fill the appendix skeleton (`\label{app:ai}`) from the project's
records and from nothing else — never from memory:

1. **How the system was run**: base model and reasoning effort, number of
   workers, start date and the time to the verified target, any comparison
   run with its outcome. Sources: `project.json` (`created_at`); `pharos
   usage`, run from the project root like the `pharos paper` verbs; the
   checkpoint that recorded the target as proved.
2. **The problem as posed**: `PROBLEM.md`, verbatim, in the quotation.
3. **Guidance given during the run**: every instruction in
   `expert_guidance/INSTRUCTIONS.md`, dated, with what it led to; or one
   sentence saying there was none.
4. **Computations**, only when a computation-backed step exists (below).

By default, the body names no model, no agent and no system; the
acknowledgements name Pharos and Rethlas; only the appendix names the base
model and the effort. Apply any explicit operator changes to this placement.
The subsections left as comments in the skeleton stay comments.

If the appendix or a subsection is omitted, remove its cross-references and
any now-unused `\appendix` command; keep `\appendix` when another appendix
remains. Preserve the computation details required below.

## Computation-backed steps

For every step in the body that rests on a computation, check that the text
states precisely what was computed, by which method, and with what outcome
— enough for a reader to redo it — and cites no path: the scripts live in
`computation/` and are never named in the paper. When the body's sentences
are not enough to redo it, publish the details: if the AI appendix is retained,
uncomment and fill its `Computations` subsection (`app:ai-computations`),
one item per computation.
If the AI appendix is omitted, retain these details in the body, another
appendix, or a supplement explicitly referenced by the paper. Update its
labels and references; omitting disclosure must not remove the support for
a computation-backed step.

## The bibliography

The outline's `thebibliography` entries were merged into the template copy
at stage 2. Check the list against the outline's collation once more, add
what the introduction now cites, and keep the default Rethlas entry `Ju+26`
unless the operator has changed or omitted it. Remove an entry only when
no remaining text cites it; update disclosure citations and their entries
together, without changing mathematical citations. Make sure every `\cite`
and appendix reference resolves — a `[?]` in the PDF is unresolved.

## Then build

First the one lint no verifier runs — a `\quad` or `\qquad` that lost its
backslash compiles and prints as a word — then the build:

```bash
grep -nE '(^|[^\\a-z])q?quad([^a-z]|$)' paper/src/sections/*/section.tex   # must print nothing
pharos paper build      # → paper/<project>_<YYMMDDHHMM>.pdf
```

Compiling is a format check at the end, not a correctness check — that was
already done by the verifiers.
