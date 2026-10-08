---
name: verify-proof
description: Verify a result and, on acceptance, write it as a fact — via the fact_submit tool. Use for the full target theorem AND for every sharply-delimited intermediate result, lemma, construction, or formula you intend to build on. The verifier is the sole authority on mathematical correctness.
---

# Verify Proof

The verifier is the **canonical and sole authority on mathematical correctness**.
Mathematics requires 100% accuracy; even though this verifier is not a formal
proof assistant, it is the strongest correctness check in the system. No LLM
consultation, panel, or self-critique substitutes for it.

**You verify and write a fact through one tool: `fact_submit`.** It calls the
verifier and writes the fact to the fact graph
**iff the verifier accepts** — there is no other way a fact enters the graph.

## When to submit

- **The full target theorem** — when you have assembled a complete proof of the
  whole problem (as a self-contained statement + proof, citing its predecessors by
  `fact_id`).
- **Every intermediate result you intend to USE downstream** — a lemma, a
  candidate construction, an arithmetic/closed-form claim, a saturation or
  local-to-global claim, any sharply-delimited step. **Adopting an unverified
  partial result as a building block is the single biggest correctness risk.** When
  in doubt, submit.

Choose a substantive mathematical boundary, not the smallest checkable line.
Routine calculations, substitutions, and bookkeeping identities should normally
remain internal steps in the proof of a deeper fact. The submitted fact should
state one mathematically significant conclusion; depth must not be simulated by
bundling several shallow or unrelated claims. Split supporting claims only when
they have independent downstream uses, separate proof obligations, or need
isolated verifier repair.

Do **not** build on an unverified finding from global memory. A `conclusion` /
`example` / `counterexample` there is awareness, not a brick — re-derive it as a
self-contained statement+proof and submit it before relying on it.

## Before you submit — write an "ugly-proof" fact

A fact in the fact graph is written in **"ugly-but-rigorous"** form (the operator
may call it an **"ugly-proof"**). The one goal of
this form is that the fact is **mechanically checkable for correctness** by a
reader with no memory and no math intuition (an agent with no recall, a human, the
verifier). It is allowed — encouraged — to be **ugly**: redundant, machine-flavored,
verbose. It is **not allowed** to be ambiguous, vague, or context-dependent.
"Ugly" is the deliberate contrast with a polished write-up, which is a
downstream concern; here, only mechanical correctness matters.

Concretely, before you submit:

- **Self-contained.** A reader using only this fact + its declared predecessors +
  the project glossary can decide whether the math is correct. No appeal to chart
  positions, parse status, project history, or "as we know".
- **Define every symbol — local ones in the statement.** "Let $X$ be …" inside
  the statement is the definition of $X$ for this fact; that is what the
  verifier reads. `glossary_introduces` is only for a *standing* project
  symbol (an object the whole project keeps using — rare; most facts introduce
  nothing), one sentence each, never an instance of a family, never universal
  notation. A symbol already in the project glossary keeps its meaning: reuse
  it, never redefine it. The verifier rejects an undefined symbol (P6).
- **Cite every dependency by `fact_id`** — never "by the result above", never the
  problem statement as a math source.
- **Every quantifier explicit; every introduced parameter (epsilon, k, …) carries
  an explicit range.**
- **No handwave** ("obviously", "easy to see", "routine", "analogously",
  "by some classical argument") and **no chart-position references** ("as above").
- **Avoid duplicates.** Use `fact_search` to find an existing fact with the
  same statement, and `fact_get` to read it; if one exists, cite its `fact_id`
  instead of re-proving it.

## Submit and repair

Call `fact_submit(statement, proof, predecessors=[...], glossary_introduces={...})`.
Read the result:

- `accepted: true, fact_id` — the fact is written. **Cite `fact_id`** downstream.
- `accepted: false, repair_hints` — revise: resolve
  critical errors first, then all remaining gaps; do not assume the fix is local —
  change strategy or backtrack if needed; then resubmit. Treat any `wrong` verdict,
  any critical error, or any gap as failure.
- `verdict: "error"` — the verify service was unavailable; retry.
- `accepted: true, write_error` (e.g. a predecessor was revoked) — the fact was not
  written; re-prove or avoid that predecessor.

Every outcome is auto-logged to global memory (kind `verification`), so the
feedback is shared — `gm_search` it to learn from others' rejections.

## The verifier is the only correctness authority

If your own reasoning, the main agent's `TASK.md`, or any other LLM calls
a result correct but `fact_submit` rejects it, the verifier wins. Always. Note the
disagreement (a `dead_end` finding) and treat the "looks correct" opinion as the
unreliable signal it was. A non-verifier opinion (including the main agent's) is
for ideas and directions, never for correctness.

## Tools

- `fact_submit` (the only path to verify a result and write a fact)
- `fact_search` / `fact_get` (check for an existing fact before submitting)
- `gm_search` (read others' findings and verification outcomes)
- the project glossary may be read directly for a known symbol
