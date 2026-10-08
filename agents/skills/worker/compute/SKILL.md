---
name: compute
description: When and how to run a computation — pharos compute only; numerics supplement mathematical reasoning, never replace it.
---

# Compute

**The principle: computation supplements reasoning, it never substitutes for
it.** Reason first — understand the structure, frame a precise question — and
only then compute that question. If you are reaching for the machine to avoid
doing mathematics, stop and reason. And the converse discipline: once
reasoning HAS framed a genuinely computational question, do not grind it by
hand for pages — that is what the machine is for.

## When a computation is warranted (hints, not an exhaustive list)

- **Counterexample search** — after reasoning has narrowed where to look:
  which parameter range, which family of objects, what failure would look
  like. A blind sweep over an unframed space is the laziness this skill
  forbids.
- **Symbolic computation too tedious to trust by hand** — high-order
  expansions/variations, large polynomial or determinant manipulation. Check
  the structure by hand on the smallest case first, then let the machine do
  the swell.
- **Sharpening a constant or estimate** — when the route genuinely needs a
  better value, use the machine to search; only then.
- **Sanity-checking a conjecture on small cases** before investing proof
  effort in it.

## When to reason instead (the default)

Anything not yet framed precisely; any claim about infinitely many cases or
asymptotics (a computation probes finitely many — it can refute, it cannot
prove); anywhere a structural argument is in reach. A surprising computational
result is a prompt to find the reason, not a conclusion.

## How

- Write the script into `<project>/computation/` and run it with
  `pharos compute computation/<name>.py` — **never bare python**; the wrapper's
  cgroup caps keep the shared host alive.
- The default tier (2G · 1 CPU · 10 min) is for exploration and is usually
  enough. `--heavy` needs a justified, named reason. The pool — 4 CPUs / 16G —
  is **shared by the whole project**, so schedule heavy runs deliberately.
- Outputs land in `computation/` (20G cap — delete what is no longer needed).
  `numpy`/`scipy`/`sympy`/`mpmath` are installed; `.sage` runs under Sage when
  present.
- Record honestly: a meaningful outcome goes to global memory as a finding
  **labeled as computational evidence**. Evidence is not proof — a fact that
  leans on a computation must present the check in written, verifiable form,
  and the verifier judges that text without rerunning anything.
