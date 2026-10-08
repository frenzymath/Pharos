---
name: paper-structure-planning
description: Stage-1 planning of the paper — read the checkpoint, locate the key theorems, extract the new concepts, design the sections; then write paper/OUTLINE.tex with $outline-file-writing and revise it on every escalation.
---

# Paper structure planning

Stage 1 is your own work: you plan the paper that the section writers will
fill in. The plan becomes `paper/OUTLINE.tex` — its content and format are
the subject of `$outline-file-writing`; this skill is about what goes into
it: which statements the paper rests on, which concepts get a name, and how
the body is cut into sections.

## How to plan the paper

1. Understand the thread of the paper — "Seed it from the checkpoint".
2. Decide which statements are the key theorems — "How to locate the key
   theorems" — and, around them, which concepts deserve a name and a
   definition — "Tips on extracting new concepts and writing definitions".
3. Design the section structure — "How to organize sections".
4. Write `paper/OUTLINE.tex`, following `$outline-file-writing`.
5. Revise it whenever a section sends it back — "Handling escalations".

## Seed it from the checkpoint

Start from the latest checkpoint (the last file by name in `checkpoints/`) —
its verdict, key theorems, and route board are the seed. Mark whatever you draw from it as
**provisional**: a checkpoint is a synthesis for steering proof work, not a
vetted paper structure, and the outline stage is where it gets scrutinized as
one. This project's records are the only seed: another project's paper or
outline, however similar its problem, is neither a source nor a model.

## How to locate the key theorems

The key theorems are what the outline is built around: each body section
exists to prove one of them, or a few tightly connected ones, and every
other statement in the outline is there because a key theorem needs it. The
checkpoint's key-theorem section is the first list; check it against the
facts (`fact_get` the ids it cites) before you build on it.

Signs that a statement is a key theorem:

- First, the final target theorem is a key theorem.
- It makes a **choice the statement does not determine** — an auxiliary
  object, a construction, a decomposition — that had to be found, and the
  proof does not work for the obvious alternatives.
- It uses a **hypothesis of the original paper in an essential, specific
  way**: the paper fails without it, and this is the place where the naive
  argument breaks. (A hypothesis that is merely restated is not being used.)
- It carries the argument **from a good case to the general case**, when that
  passage is where the difficulty of the problem lives.
- It establishes an **estimate, bound, identity, or property that is not a
  direct consequence of definitions or routine computations**, or a **case
  analysis whose completeness is genuinely at issue** — the kind of
  enumeration that has been wrong before.

Signs that a statement is not a key theorem:

- unfolding definitions, substitutions, bookkeeping identities, immediate
  corollaries by specialization of previous results in the route;
- a standard argument applied with its hypotheses trivially met — a textbook
  lemma cited and used as it stands;
- formal or categorical manipulation carrying no content, and reformulations
  equivalent to the statement;
- a finite check or a computation that confirms something: a computation is
  evidence, never a key step; at most the reasoning that framed it is;
- a toy example that cannot be generalized or does not indicate general
  methods.

Every key theorem enters the outline, even one used only inside its own
section. A statement that is not a key theorem enters only when a section
other than the one proving it needs it (`$outline-file-writing` lists what
the outline must carry); it does not organize a section of its own.

## Tips on extracting new concepts and writing definitions

A concept here means a specific set of settings, or some mathematical
structures, that the argument keeps referring to. Consider abstracting one
into a named concept with a definition when:

- it is repeatedly used as a whole, as hypothesis or as conclusion, in
  several theorems;
- it is never used independently in any theorem: every mention uses it as a
  whole.

The raw material is the facts themselves: the project glossary
(`fact_graph/glossary.json`) and each fact's `glossary_introduces` hold the
standing notation the facts were verified against, and the statements show
which bundles of hypotheses recur. That is the workers' notation, not yet
the paper's: merge what is the same, rename what collides, drop what no
statement in the paper uses. The outline's notation is the one the paper
speaks; section writers translate the facts into it.

Where a definition goes: a new concept is defined once, in the body section
where it belongs — normally the first section that uses it. The notation
and terminologies section holds the standing setting, the global notation,
and every known concept the paper uses in a sense that could be ambiguous;
a new concept may sit there too when its definition depends on no theorem
and every section uses it. A concept whose well-definedness is itself a
result belongs in the body, next to that result.

## How to organize sections

Three kinds of section:

- **Introduction.** A placeholder at stage 1; written for real at polish
  (stage 3), when it can describe a paper that exists.
- **Notation and terminologies.** Written for real at stage 1, by you: the
  standing setting, the global notation, and the known concepts in the
  sense the paper uses them — everything a section may use without defining
  it.
- **Body sections.** Each is organized around one key conclusion, or
  several tightly connected ones.

The shape of the paper as a whole — which sections a reader expects, the
parts of the introduction, an optional section that reveals the mechanism
behind the main result — is described by the style file (`$paper-style`).
The three kinds above and the rule of one key conclusion per section stay
as they are whatever the style file says: the pipeline depends on them. A
mechanism-revealing section, when the paper has one, is a body section like
any other — its own home, its own key conclusion (the second proof, the
geometric reading).

How the body splits: sections should be as independent as possible, cite
other sections as little as possible, and each focus on one key conclusion
or a few tightly connected key conclusions. Organizing ideas worth
considering, one per section:

- the proof of one key lemma or theorem;
- the well-definedness of one key concept or equivalence relation — a
  section whose point is that one object may be seen as another is a
  legitimate section on its own;
- a relatively independent technical module, unrelated to the rest of the
  paper.

Order the body so that citations point backwards; the section that proves
the final target comes last, citing what precedes it. Sorted section-name
order is the order of the paper (`$outline-file-writing` fixes the naming),
so settle the order here, before any section home exists.

## Handling escalations

A section writer's `status: escalate` means the outline is wrong for that
section, not that the section failed. Revise `OUTLINE.tex` immediately, then
propagate: every section the change touches — shared notation, a statement
another section cites — gets a fresh `TASK.md` (stop it first if it is still
running), and `pharos paper start --all` restarts exactly those. You never
relay verifier findings yourself: each section's loop feeds its verifier's
verdict back to its writer; you see only `done`, `escalate`, or `failed`.
