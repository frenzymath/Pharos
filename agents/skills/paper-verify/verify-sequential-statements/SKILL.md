---
name: verify-sequential-statements
description: How to read a written proof for correctness, statement by statement in the order the text presents them — what to check at each step, how to compare a cited statement with the use a proof makes of it, and the ways a wrong proof usually gets past a reader. For a text-only reviewer of a LaTeX section or a whole paper; yields anchored findings for the verdict the governing contract prescribes.
---

# Verify sequential statements

Technique only. What is given and never re-litigated, what counts as a
blocking finding, and how the verdict is written are the governing contract's;
this is how to read so that the verdict is right.

## Order and anchors

- Read in the order written: a statement, then its proof, then the next. An
  internal lemma is judged where it stands, before its first use. A term or
  an object is available to the text from the point that defines it, not
  before: one that a later statement introduces is undefined at an earlier
  use.
- Before reading a proof, fix its statement: write down the hypotheses and the
  exact claim (hypotheses, connective, conclusion — `$statement-writing`).
  Everything the proof concludes is measured against that list, not against
  what the proof says it is proving along the way.
- When the intended argument is available (a source proof the text was written
  from), read it first: the steps the source has and the text lacks are the
  first suspects. The text is still judged as written — a step the source would
  supply and the text does not is missing.
- Give every place you may refer to an anchor as you go — the label, or the
  first words of the passage — so a finding can be written without rereading.

## At each step of a proof

1. **Inference.** Does the step's conclusion follow from what stands above it
   plus what the step cites? Name to yourself the rule or the cited statement
   that carries it. "Clearly", "it follows that", "one checks", and just as
   much "reduces to", "by the standard argument", "similarly", "the same
   argument gives" mark the steps to slow down on: could a reader carry the
   step out with routine work from what the text gives, or does the phrase
   hide an obligation — a hypothesis of the invoked argument that these
   objects do not visibly meet, a parameter that varies with another so that
   the standard version does not apply as it stands, a uniformity the
   conclusion needs, a difference between two cases said to be alike? A step
   that cannot be reconstructed from the text is a defect, whatever the
   source argument does there.
2. **Hypotheses of what is applied.** Where a statement is applied — an earlier
   result, an internal lemma, an external theorem the paper carries — every one
   of its hypotheses is established at this point, for these objects. A
   hypothesis met "obviously" is one to check.
3. **Objects.** An object the proof uses exists and has the property claimed:
   constructed here, or given by a cited statement, or bound in the hypotheses.
   "Let $x$ be such that …" with no source is a gap; so is an object that
   exists but whose claimed property was never shown; so is a symbol that
   names, at this step, another object than the one it was introduced for.
4. **Quantifiers and dependence.** A constant or threshold depends on exactly
   what the text says; "for $n$ large" has a stated dependence; the order of
   quantifiers is the same in the statement, the proof, and the conclusion.
5. **Case splits.** "The cases are", "the only remaining case", "exhaustive":
   never taken on the proof's word. Enumerate the cases yourself and look for
   the one that is missing before accepting — an incomplete enumeration is the
   commonest way a wrong proof passes a reader.
6. **Cited statements as used** — the next section.

## Comparing a cited statement with its use

- Put the cited statement, as the paper states it, beside the step that uses
  it. Compare hypothesis by hypothesis, then the exact conclusion — formulas,
  quantifiers, parameter ranges — never the names of the results.
- Same word, different meaning. A term may not mean in the source what it means
  in the paper (another field, a source written in other notation). Expand both
  to their defining formulas before deciding they agree; do not collapse two
  definitions because their names or formulas look alike.
- A restatement or compression of a cited statement says what the original
  says: not stronger, no hypothesis dropped, no specialization the original does
  not license. A hand-wavy instantiation is itself a step to check.
- What the proof deduces from the cited statement is a further step, checked
  like any other; a property deduced from another property is checked on their
  defining formulas.

## Unused hypotheses

A hypothesis the proof never uses is not passed over: either it is redundant —
a remark — or the proof silently skipped the step that needs it — find that
step. When the statement's text is fixed outside the section under review (a
shared statement), an unnecessary hypothesis is a note for the main agent —
the outline's author — in the verdict's notes, not a finding against the proof.

## Keep, for the verdict

For each defect, at its anchor: what is claimed, why it does not follow (the
invalid inference, the unmet hypothesis, the missing case, the changed
meaning), and what would satisfy you. Findings in the order of the text; their
classification is the contract's.

## Tools

None — reading and reasoning. Cited statements and the source arguments are
where the contract says they are.
