---
name: paper
description: The writing workflow you drive once the target is a fact — outline, autonomous section jobs, polish, build — and exactly how you interact with each side actor.
---

# Paper — the writing workflow

You drive it and write the frame — the outline's statements, the
introduction, the front matter; the proofs are the section writers'. Three
stages, three kinds of side actor, one channel: **files**. Nothing here needs
a chat with anyone.

The style every writer — and you — write to is `$paper-style`: it resolves
to the project's `style/STYLE.md` when the project provides one, else the
default. Read it at stage 1 and at stage 3; the verifiers do not read it.

Read the operator's paper disclosure choices in
`expert_guidance/INSTRUCTIONS.md`. The template's system disclosure, team
acknowledgements, Rethlas reference and AI appendix remain the default;
apply any explicit changes or omissions to `paper/src/template.tex` when
the copy exists, and check them again at polish (`$paper-polish`).

```
stage 1  OUTLINE.tex           you, with $paper-structure-planning then $outline-file-writing (seeded from the checkpoint)
stage 2  sections/<name>/      one autonomous job per section: writer ⇄ its verifier
stage 3  polish → build        you, with $paper-polish; then pharos paper build
```

## Who does what, and how you talk to them

| actor | lives in | you send | you receive |
|---|---|---|---|
| section writer | `paper/src/sections/<name>/` | `TASK.md` (via `pharos paper assign`) | `REPORT.md` — `status: done \| escalate \| failed` |
| that section's verifier | `<name>/verifier/` | nothing — the section loop runs it | `VERDICT.md` — `status: pass \| fail` (also in `pharos paper status`) |
| whole-paper verifier | `paper/verifier/` | `pharos paper verify --global` | its `VERDICT.md` |

Writers and verifiers **resume their own session** between rounds, so they
remember their section and their earlier verdicts; you never re-explain.

## Stage 1 — the outline, and why you keep coming back to it

Two skills, in order. `$paper-structure-planning` is the thinking: from the
latest checkpoint, which statements are the key theorems, which concepts
deserve a name and a definition, how the body is cut into sections.
`$outline-file-writing` is the file: `paper/OUTLINE.tex`, a bare LaTeX body
that compiles through the project template — the macro block for the global
notation, a placeholder introduction, the notation-and-terminologies section
written for real, the body sections with every shared statement and every
external result stated under its comment block (facts · owner · depends ·
source) and no proofs, and, as its last part, the reference collation as a
`thebibliography` block with its citation audit. **OUTLINE.tex is the
instrument you steer with for the whole job**: every section writes against
it, every verifier judges against it, and every escalation is a request to
change it. Expect it to be sent back repeatedly; that is the design, not a
failure.

## Stage 2 — sections as autonomous jobs

```bash
pharos paper assign <name> --task "…"   # names the section to fill from the outline (+ your instructions)
pharos paper start --all                # every section whose TASK.md is new
pharos paper wait                       # sleep until one finishes; prints name: state
pharos paper status                     # state · round · last verdict, per section
pharos paper stop <name>                # stop a running section, e.g. before re-assigning it
```

### Assigning a section: TASK.md

For each body section, `pharos paper assign <name> --task "…"` — `<name>` is
the section's name from the outline, which is also its directory under
`paper/src/sections/` (sorted name order is the order of the paper). The
writer fills in its section of the outline directly — the statements, their
labels and comment blocks, `depends:`, and the macros it reads from
`OUTLINE.tex` itself — so TASK.md copies none of that. Its first line names
the section: `Fill section sec:<name> as OUTLINE.tex states it.` Anything
after that line is an instruction of yours to this one writer: none at the
first assignment, normally; later, what a `failed` or a long loop taught you
— where the verifier keeps failing, which facts carry the intended argument,
how to treat a computation, the level of detail. TASK.md is also the switch:
a section starts, or restarts after `escalate` or `failed`, only with a
TASK.md newer than its last round, so rewrite it even when its text does not
change.

Two sections have no writer. The notation-and-terminologies section is
finished in the outline: copy it yourself, verbatim, to
`paper/src/sections/<name>/section.tex` — by line range with a tool
(`sed -n 'A,Bp' paper/OUTLINE.tex`), never retyped: the whole-paper
verifier compares the two byte for byte, and a stray space costs a round.
The introduction stays a
placeholder until polish: its `section.tex` holds just the `\section` line
and its label for now. Neither gets a `TASK.md`. Create their directories
yourself (`mkdir -p paper/src/sections/<name>`): only `assign` creates a
section home, and it refuses an empty task. `status` lists these two as
`unassigned` for the whole run — that is right; "every section is `done`"
below means every section that has a `TASK.md`.

The first `assign` creates `paper/src/template.tex`, the project's own copy
of the style template (`style/TEMPLATE.tex` if the project provides one,
else `style/default/TEMPLATE.tex`). Right then, and again whenever they
change: copy the outline's macro block into its preamble, before
`\begin{document}`, and
merge the outline's `thebibliography` entries into the template's
bibliography (keeping the default Rethlas entry unless the operator changes
or omits it; every remaining citation must resolve). Section writers use the
macros and `\cite` the keys, and `pharos paper build` compiles from this
file, never from the outline — an entry left out shows as `[?]` and fails
the whole-paper verifier.

### The loop

`start` launches a small loop per section: the writer works → if it reports
`done`, its own verifier judges → `fail` sends the writer another round (it
reads `verifier/VERDICT.md` itself and revises) → until `pass`, `escalate`, or
the writer itself reports `failed`. There is no round cap: a section takes the
rounds it takes. **A long loop is your cue, not a failure**: from round 5
(`PHAROS_PAPER_ATTENTION_ROUNDS`) the section carries a note in `status` and
`wait` returns once for it while it keeps running. Then you look — its
`REPORT.md` and `verifier/VERDICT.md` trail — and decide what is wrong:
usually the outline (the section's statement, the notation, the sectioning) →
fix `OUTLINE.tex` and re-`assign` the touched sections; sometimes the task →
sharpen `TASK.md` and re-`assign`; and reflect on whether the neighbouring
sections carry the same flaw. A re-assigned writer resumes with its history.
**The
writer/verifier back-and-forth never crosses your desk.** Your loop is:

1. `wait` → a section reports.
2. `done` → nothing to do; it will be part of the build.
3. `escalate` → read its `REPORT.md`: the outline is wrong for that section
   (a statement, the notation, the sectioning). **Fix `OUTLINE.tex` at once**,
   then propagate: re-`assign` every section the change touches — including
   ones still running (`stop` them first) — and `start --all`; if the macro
   block or the notation section changed, update the template's copy and the
   notation section's `section.tex` too. A writer that
   is re-assigned resumes with its history intact, so a revised task costs one
   round, not a restart from zero.
4. `failed` → read the last verdict; usually the task was under-specified.
   Sharpen `TASK.md` (or fix the outline if the verdict blames it) and `start`
   again.

Until polish, a section is its writer's the same way: you do not edit its
`section.tex`, write its `REPORT.md`, or run `pharos paper verify <name>` on
it — a proof you write has had no writer's rounds and no verifier round of
its own behind it. A writer that looks idle is not stuck: its log stays
quiet while it reads the facts and thinks, and a failing `apply_patch` shows
there only as the same patch tried again. Judge a writer by `wait` and
`status`, never by probing its process or its log; `wait` returns when its
round ends. The one stall you may see is a writer failing the same
`apply_patch` again and again for a long time: then `stop` it, tell it in
`TASK.md` to rewrite `section.tex` whole instead of patching it, and `start`
it again — it resumes with its history.

A change confined to the outline's comment blocks — a `depends:` line
brought up to date with a citation a writer reported, a `facts:` line — is
bookkeeping: edit the outline and move on. No re-assign and no new round; the
statements the section was written against did not change.

Run sections in parallel; the loop makes that free. Run them in dependency
order only when a later section's task genuinely needs an earlier section's
final text (rare: the outline's statements are what they cite).

## Between the stages — the whole-paper verifier

When every section is `done`: `pharos paper build` (assemble + compile), then
`pharos paper verify --global`. It catches what no section can — notation
drift, a hypothesis not discharged where a lemma is used, a reference that
does not resolve. A `fail` here maps to sections: re-assign those, `start
--all`, repeat.

## Stage 3 — polish, introduction, build

`$paper-polish`: readability only, no mathematical change, seams between
sections harmonized, **then** the introduction written for real, in the
shape the style prescribes (it describes a paper that now exists), **then
the front matter** in the project's own `paper/src/template.tex` — title,
authors, the abstract — the retained acknowledgements moved to the end of
the introduction, the retained AI appendix filled from the project's
records, the bibliography checked against the outline's block once more
(it was merged at stage 2). Finish
with `pharos paper build` → `paper/<project>_<YYMMDDHHMM>.pdf`. Compiling is a format check at the very
end; correctness was the verifiers' job.
