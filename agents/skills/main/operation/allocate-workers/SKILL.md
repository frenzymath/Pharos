---
name: allocate-workers
description: Driving the worker swarm — the commands, what a TASK.md must contain (the picture, the question, the materials), the assignment principles, and what gets delegated (computation included).
---

# Allocate workers

## Commands (run from your project directory; project implicit)

```bash
pharos assign <worker> --file <path>  # overwrite that worker's TASK.md from a file you wrote (replaces, never appends)
pharos assign <worker> --task "…"     # the same, inline — only for a short redirect
pharos start [<worker>]               # (re)launch loop(s) — resumes from memory, cheap
pharos status                         # liveness + round + last fact per worker
pharos stop [<worker>] [--force]      # graceful at the round boundary / kill now
pharos sub "question…"                # exploratory subagent — advice, never facts
pharos monitor up · pharos usage       # keep the sampler running; read the numbers
```

## What a TASK.md is

Before replacing an existing assignment, read the worker's latest completed report at `<project>/worker_report/<worker>/<timestamp>.md`; reassignment is forbidden until its route reasoning has been considered.

`TASK.md` is the worker's **only** steering input: there is no strategy
channel beside it, workers never read your checkpoints, and each round is a
fresh session that starts by reading it. Everything the worker needs in order
to understand its statement *in context* is in this file or reachable from a
path in it. Write it as you would brief a strong colleague who
just walked in: the picture, the question, the materials.

Draft it as a file (`tasks/<worker>_<stamp>.md` in your project directory
is a fine habit — the drafts are your own record), then `pharos assign
<worker> --file …`.

```
# <worker> — <date>

## Where the project stands
The goal, quoted. The routes in play in a few lines, and which one this task
serves and why it matters now. What is established that bears on this task —
each as `fact_id` + its statement in one line (never a bare id). The current
central obstacle, in one sentence.

## Your question
One framed question with a clear deliverable — normally a precise statement
to prove, to disprove, or to construct, exactly what a `fact_submit` (or a
counterexample, or a computed table) would settle. When the definite result
or the precise shape of the deliverable is not yet clear, enumerate the
possible outcomes and ask the worker to fill in one or some of them. The
mechanism you expect to work, and why. What "done" looks like. The boundary:
what is *not* yours (a sibling's lane, a route the expert closed).

## Materials
Internal — facts to build on (`fact_id` + one-line statement); findings and
dead ends in global memory worth reading (`gm_get` ids, one line each on why);
verifier rejections of similar claims and their lesson; the expert's
direction if it binds this task (`expert_guidance/GUIDANCE.md`, a named
paper, the do-not-cite section).
External — papers already in `literature/papers/<arxiv_id>.txt` with the
theorem or section that matters, and any further arXiv ids you know are
relevant; say what each is for.

## What already failed here
Every attempt on this statement or route, with why it failed — so it is not
repeated. Include your own earlier assignments on it and what came back.

## Why this task (on reassignment)
One paragraph: why the previous task ended — proved, dead, superseded, or
redirected by evidence — and what carries over.
```

Every section is present; a section that is honestly empty says so ("nothing
has been tried on this statement"). A task that could not fill "Where the
project stands" is not ready to be assigned.

## Assignment principles

- **One worker, one framed question, one clear deliverable.** "Think about X"
  is not an assignment; a statement the worker can prove and submit is. If
  you are not sure of the definite result of a question, or are uncertain
  about the precise shape of the possible deliverable for it, you shall try
  to explain or enumerate all the possible outcomes and ask the worker to
  fill in one or some of them.
- **A general statement, never an instance table.** "Prove it for each
  $n \le 17$" or "close the column at arity 12 for $g \ge 15$" turns
  mathematics into a production line. Ask for the statement quantified
  over the parameter; the instances are corollaries inside its proof. And
  never judge a worker by how many facts it produced — by whether its
  frontier statement moved.
- **The context is in the file.** Facts by id *and* statement; papers by path
  *and* the theorem that matters; the route by name *and* mechanism. A worker
  should never have to guess what its statement is for or search to find out
  what you already know.
- **Give a task the time a real proof takes.** A substantial statement is
  expected to take many rounds; a worker deep in an argument with nothing
  submitted yet is working, not stuck. Judge it by the findings it publishes
  and its verification traces (never its private memory, never its fact
  count), and redirect on evidence, never because a beat came around.
- **Materially distinct subgoals across workers.** Each worker shall have a
  distinct task to work on. You shall not assign two identical tasks to two
  different workers. If you have only a limited number of subgoals in mind,
  not enough to dispatch to all idle workers, try to decompose the subgoals
  further, or propose different approaches to the same subgoals. Letting two
  workers work on the same subgoal, with different proposed approaches, is
  acceptable. A greater diversity of tasks among workers can make
  mathematical exploration more efficient.
- **Redirect on evidence** — a verified fact, a route decision, a dead end —
  and say in the new TASK.md why the old task ended.
- **Allocation across strategies follows the expert's rules** in
  `$evaluating-all-proof-strategies-and-allocating-workers`: unexplored
  strategies get an initial exploration first; evaluation by
  `$assessing-genuine-mathematical-progress`; favour the most promising while
  keeping minimal diversity; after two hours without progress reduce a
  strategy's workers but not to zero unless it is demonstrably unworkable;
  never spread workers evenly; push findings from one strategy into a
  stalled one.
- **Expert-recommended strategies get workers first** and keep them until
  the expert closes the route or the evidence against it is decisive; a
  route the expert closed is named as off-limits in every task it could
  tempt.
- When the expert's guidance lists sources not to cite, point the task at
  that section of `expert_guidance/GUIDANCE.md`.

## Computation goes to workers

You direct computation; **workers run and host it**. When a computation is
warranted (their `compute` skill has the doctrine: reason first, machine for
the framed question), put it in the task: what to compute, why the route
needs it, and what outcome would settle the question. The worker writes the
script, runs `pharos compute`, and reports the evidence. The pool — 4 CPUs /
16G for the whole project — is shared, so at most one `--heavy` job at a time,
and only for a named need.
