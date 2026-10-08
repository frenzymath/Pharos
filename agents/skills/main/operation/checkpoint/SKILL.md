---
name: checkpoint
description: The four-hour strategy audit and its write-once record — a fresh, complete snapshot of where the problem stands (key theorems, the route board as it stands, what you are thinking), drafted privately and published atomically for a future you and as the upstream of the human report and paper outline. Every four hours or on a big change; on resume, read ROUTES.md and the latest one first. Also defines ROUTES.md, the live route board.
---

# checkpoint — the strategy audit and its record

Your session will end: killed, host restarted, context exhausted. What survives
is the stores, and rebuilding "where does this problem actually stand" from
hundreds of facts and findings is expensive and error-prone. The checkpoint is
the machine archive that makes resuming cheap — **written by you, in your own
session, for a future you**, as the record of the deliberate macro-level audit
you owe the project every four hours.

Two things follow from what it is:

- **The audit and the checkpoint are one action.** Thinking about the global
  road to the theorem, deciding routes and allocation, and writing it down are
  not separate duties; the checkpoint *is* the audit's record. Do not audit
  without writing, and do not write without auditing.
- **It is the upstream of the other outputs.** The human report is written from
  the latest checkpoint (it does not re-derive the position from facts); the
  paper outline is seeded from it; the concept of "key theorems", which is
  inherited across the whole project, lives here and nowhere else. This is
  guidance about what those readers will lean on, not a rule that binds them —
  but write so that they can.

It is not a dispatch order (that is each worker's `TASK.md`), not a
report for the operator (that is the human report, coarser than
this), and not the route board (that is `ROUTES.md`, live, which the
checkpoint copies). Finer than both: the reader is you.

## When

- **Every four hours of wall-clock time** while the project runs — normally
  every eighth thirty-minute control beat — even if facts are still arriving
  and the current route feels close. Missed the boundary during downtime? One
  substantive catch-up, then the next future boundary; never a ceremonial
  duplicate.
- **On a big change, without waiting for the boundary:** a route closes or
  dies; the central obstacle changes; the proof architecture changes; the
  expert gives an instruction that touches strategy; a revocation cascade; a
  target is proved (the checkpoint written when the last target closes is the
  one the paper outline seeds from — make its key-theorem section complete).
- **Not** on a thirty-minute beat that found nothing new. A beat refreshes
  assignments; an unchanged snapshot republished only
  makes the latest checkpoint less trustworthy.
- **Not** merely because the board moved. A route entered, graded, killed, or
  reallocated is written on `ROUTES.md` as it happens; the next checkpoint
  copies the board.
- **On resume, read before you write.** A fresh session reads `ROUTES.md`,
  the latest checkpoint, and `expert_guidance/GUIDANCE.md`, verifies anything
  load-bearing against the fact graph, and writes its own only after a real
  audit.

## Reading rule: the latest, only

All checkpoints are kept; **every reader takes only the latest** — you, the
report writer, the outline — and `ROUTES.md` for the board as it stands now.
Older ones exist for a human who asks for history.
Consequently a checkpoint is never a delta on the previous one: **write each as
a fresh, complete report as if none existed**, with the previous one open as a
reference, and put the delta in its own section inside it. A reader of the
latest must never need the one before.

## The audit, then the record

1. **Read** — `expert_guidance/GUIDANCE.md` first; `ROUTES.md`; the latest
   checkpoint; what entered the fact graph since it (`fact_search`, or the
   recent `fact_graph/facts/`); recent findings and `verification` traces
   (`gm_search`, summaries, then `gm_get` the few that matter); each worker's
   current task; every subagent result that came back.
   Never a worker's local memory. Subagents may compile raw digests for you
   (facts added on route X since T, what the rejections on route Y have in
   common); the judgment and the writing are yours.
2. **Think at the level of the whole road to the theorem**, not local
   activity: for every credible route, how far its mechanism has actually been
   carried, the decisive obstacle that remains, what evidence strengthened or
   weakened it, whether its worker allocation is still justified, and whether
   the primary should continue, be complemented, or yield to a parked route.
   Fact volume and activity inside the primary route are not macro progress.
3. **Decide** — route status changes, the missing bridges to hand out, the
   allocation — checking the plan against GUIDANCE.md. A deviation from an
   expert instruction is the operator's decision, declared and parked, never
   quietly made.
4. **Record the decisions on `ROUTES.md`, compose and publish the checkpoint**
   by the write-once procedure below, then act on it: assignments via
   `pharos assign` (each `TASK.md` carrying the route context its worker needs —
   workers never read checkpoints), helpers via `pharos sub`.

## Draft privately, publish once

Checkpoint files are write-once artifacts. Never create a timestamped file in
`checkpoints/` while the audit is still in progress, and never patch, append to,
or replace one after publication. A file in that directory is a published
snapshot: readers may consume it immediately and use its timestamp as the
boundary for later facts.

1. Compose the whole checkpoint in `<project>/.checkpoint-drafts/current.md`.
   Create the private draft directory when needed; readers do not inspect it.
   The header's timestamp line must initially be exactly `Timestamp: DRAFT`.
   Revise this draft as often as the audit requires.
2. Before publishing, complete the audit and do one final consistency pass:
   refresh material facts and findings, settle `ROUTES.md`, verify every cited
   `fact_id`, confirm all nine sections are complete, and ensure no late result
   still needs to be folded into this snapshot.
3. Publish with the bundled helper, from the project root:

   ```bash
   python .agents/skills/operation/checkpoint/scripts/publish_checkpoint.py \
     .checkpoint-drafts/current.md
   ```

   The helper chooses one UTC minute, writes the matching header and filename,
   then atomically publishes the complete draft as
   `checkpoints/<project>_<YYMMDDHHMM>.md`. It refuses to overwrite an existing
   path and makes the published file read-only. Draft and destination must be
   on the same filesystem.
4. Treat success from the helper as the publication boundary. A fact or change
   discovered afterwards belongs to a later checkpoint when the next real
   trigger occurs; it never justifies reopening this one. If composition is
   interrupted before publication, resume the private draft. `ROUTES.md`
   remains the live exception and continues to be updated in place.

## What it contains

Every section is present every time. An empty one is written honestly ("no
route has died yet") — a reader must be able to tell "nothing here" from "not
considered".

1. **Header.** Timestamp; trigger (four-hour audit, or the event); the project
   goal quoted verbatim from `PROBLEM.md`.
2. **Verdict.** Is the goal proved? If not, the single thing blocking it, the
   current best proof skeleton, and the central missing lemma.
3. **Key theorems — inherited.** The human-granularity statements this project
   is about, in two lists:
   - *Established*: each stated precisely, with the `fact_id`s that together
     support it. Key theorems rarely coincide with single fact-graph nodes —
     one may rest on a chain of a dozen facts, or be only partly covered; say
     which part is verified and which is not. Alignment is your judgment, not a
     mechanical check.
   - *Expected*: for each live route, the theorem(s) it is trying to prove,
     stated as precisely as the route currently allows, with what stands
     between here and there.
   Every entry from the previous checkpoint is carried forward. An entry leaves
   only by being proved (moves up), killed (moves to the dead routes, with the
   reason), or restated (say what changed and why).
4. **The route board — `ROUTES.md`, copied as it stands.** `ROUTES.md` is the
   project's global strategy record: live, in the project directory next to
   `PROBLEM.md`, yours alone to write. Every route decision — entering,
   grading, killing, reallocating — lands there when it is made; the
   checkpoint carries a copy so that each one is self-contained. One entry
   for every route ever considered, including dead ones:
   - name; mechanism in a paragraph; **origin**: expert-recommended (with the
     instruction's date), from the literature (which paper — the `prior-work`
     survey is where most routes are born), or your own;
   - **status**: primary · secondary · parked (with explicit revisit
     conditions) · dead (what killed it — a `fact_id`, a counterexample, an
     obstruction; decided by `$determining-when-to-abandon-a-proof-strategy`)
     · human-closed (the instruction's date and words; never reopened
     without the human);
   - **history**: how many rounds of work it has had, how many assignments to
     which workers, what each returned, the cumulative conclusion;
   - **frontier**: the exact statement the next piece must deliver —
     hypotheses, the object, the form of the conclusion — so a future you or a
     worker can resume the route without re-deriving its contract;
   - the decisive obstruction, and the evidence for and against the route;
   - **allocation**: who is on it, why, what each is expected to deliver,
     and what would make you redirect them — intent, not liveness (whether a
     process is alive belongs to the monitor, never here).

   **Expert-recommended strategies sit at the top of the board and stay
   there.** The moment the expert explicitly recommends a strategy — at
   launch or in dialogue later — it is entered as a route marked
   expert-recommended, it gets worker allocation ahead of your own routes, and
   it is pushed continuously until it is proved, the expert closes it, or the
   evidence against it is decisive — and even then parking it is declared to
   the expert, not decided by you. A route the expert closed stays closed.
5. **Progress since the last checkpoint — graded, and accurate.** The
   baseline is the previous checkpoint file, never `ROUTES.md`. The operator
   reads this section to learn one thing: did the project move, or spin? It is
   the one place you grade yourself, so grade with evidence only.
   - *Last time's decisions, and what each produced.* Every decision the
     previous checkpoint recorded — a route change, an assignment, a probe —
     with its outcome by now: a verified statement (`fact_id`), a route dead
     for a verified reason, a narrower frontier, or nothing yet.
   - *Movement, stated in statements.* Per route, the frontier statement
     before and after, and the assessments recorded in its history on
     `ROUTES.md` since the previous checkpoint
     (`$assessing-genuine-mathematical-progress`).
   - *One plain closing sentence per route and for the project*, in that
     skill's vocabulary: **substantial progress** (name what was understood
     or reduced, and the fact), **modest but real progress** (say what
     advanced and what did not), or **lack of progress** (say which pattern
     repeats and what you will change). Write the true one: the operator
     acts on it, and a flattering grade costs them more than a bad one.
   - *Grade decisions by outcome, not by size.* "The Sigma2 re-plan now targets
     statement S through the resolvent cover; it has produced one dead probe
     and nothing verified" is a grade. "A major architectural sharpening, not
     closure" is not: it names no statement and no outcome. A re-plan that has
     produced nothing yet is *untested*, whatever it felt like.
   Also here: instructions received since the last checkpoint, and routes
   whose status changed.
6. **What is dangerous.** Heuristics that look right and are not; statements
   false as stated; arguments that quietly assume the conclusion; the
   rejections whose lesson generalizes. This section saves the most time,
   because these are the mistakes a fresh session makes again.
7. **The missing bridges.** The smallest statements which, if proved, would
   close the gap — each phrased precisely enough to hand to a worker as-is,
   and tagged with the route it serves.
8. **What I am thinking now.** The plan for the next four hours; hypotheses
   under consideration and what you believe about them; what evidence would
   change the plan; questions you have sent to subagents and what each is for.
9. **Parked for the operator.** Decisions that are theirs — confirming the
   answer, a revocation, a deviation from an instruction, anything leaving
   the machine — each stated once, with what you are doing meanwhile.

## Discipline

- **The goal is fixed.** Quote it; never redefine, weaken, restrict to a
  special case, or substitute a proxy. If the evidence says it may be false or
  unreachable, say so plainly while keeping the goal as stated.
- **Only `fact_id`s are truth.** A claim without one is awareness; every id
  you cite must exist. One invented id makes the whole checkpoint untrustworthy
  to the reader who needs it most.
- **No numerical distance estimates** ("≈ 8–12 facts", "80% done"). Distance
  is qualitative. **No process telemetry** — cost, uptime, worker deaths,
  pressure are the monitor's and `pharos usage`'s, reported in the human
  report, not here.
- **Honest, not reassuring.** Surface hidden assumptions and the places your
  own summary could mislead; do not round "substantial progress" up to "almost
  done" — you are the one who will be misled.
- **Global, not locally captive.** Judge the whole portfolio against the fixed
  goal; never let the route that occupied the recent context erase a reliable
  parked one.
- Before presenting a route as novel, search the literature broadly
  (`search_arxiv_theorems`, varied formulations and technique names); record
  what you learn as findings. Literature notes are leads, never facts.

## Where it lives

```
<project>/ROUTES.md                                 # the route board — live, rewritten in place
<project>/.checkpoint-drafts/current.md              # private mutable draft; never read as a checkpoint
<project>/checkpoints/<project>_<YYMMDDHHMM>.md     # one file per checkpoint; the latest is the last by name
```

Publish the file with the bundled helper; that is the whole output. The report
writer and the outline read the latest file in this folder; the previous ones
stay immutable for history.
