---
name: operate
description: Run the Pharos deployment day to day — start or stop a project, check what is running, recover after a host restart, and diagnose a stalled or unhealthy deployment. Use when the operator asks to start/stop/check something, when a project produces no facts, or after a reboot. NOT for mathematics or proof strategy (that is each project's own main agent).
---

# operate — run the deployment

You are the ops agent (see `AGENTS.md`). This skill covers starting and stopping
projects, checking what is running, recovery, and diagnosis.

Every command below names its project. Each project has its own verify port,
main agent, and session records.

## Start an experiment

An experiment is one project: one problem, its own workers, verifier, and
resident main agent. Do these in order — each step depends on the one before.

**1. Name it.** Pick a **short lowercase tag** abbreviating the experiment
(2–8 characters, conventionally 3–4), and confirm it with the operator if it
is not obvious:

| experiment | tag | tmux session |
|---|---|---|
| `Mbar15` | `mb15` | `pharos-v3-mb15` |
| `p4-octic` | `p4` | `pharos-v3-p4` |

**2. Scaffold and record the problem.**

```bash
pharos new <project> --roles xhigh:3,max:4     # workers + verify port + main-agent wiring
```

Then get `PROBLEM.md` in place. There are two cases, and they differ in **when
you may start the main agent**:

- **The operator states the problem.** Write it **verbatim** into
  `runtime/projects/<project>/PROBLEM.md`. Do not paraphrase, tidy, or
  "clarify" it — that file is the fixed goal every agent works against, and an
  edited goal is a silently different experiment. If it is genuinely ambiguous,
  record it as given and raise the ambiguity with the operator.

- **The operator has materials** — papers, references, known partial results,
  a prior write-up — and wants the problem stated *from* them. Then:

  1. `pharos new` has already created `runtime/projects/<project>/materials/`.
     Finish everything else (step 4 below), tell the operator that exact path,
     and **wait** until they say the materials are in. Do not proceed on a
     half-filled directory.
  2. **Read every item** — all of them, not a skim. A source is supplied
     because its exact shape matters; re-deriving its content in your own words
     defeats the point of supplying it.
  3. **Write `PROBLEM.md` yourself**, stating the problem from the materials and
     **citing them by path**, so any later reader — a worker, the main agent —
     can reach the same context.
  4. **Show it to the operator and get their confirmation before starting the
     main agent.** From that moment the statement is the fixed goal and stops
     moving; everything downstream is measured against it, so it is worth one
     round-trip to get right.

  The goal is set by you and the operator, never by the agent that will pursue
  it. A main agent must always find a finished `PROBLEM.md` waiting for it.

**3. Record the operator's direction.** Everything the operator says at launch
that is direction rather than the problem itself — a technique or paper to
try, a route to avoid, a source not to cite — goes **verbatim** into
`runtime/projects/<project>/expert_guidance/INSTRUCTIONS.md`: one entry per
instruction, with the date,
channel `launch`, and the operator's exact words;
the one-line reading is the id and local path of any paper it names, else
"launch-time instruction".

Then write `expert_guidance/GUIDANCE.md`: the current instructions organized
as a digest, plus its "Do not cite / superseded" section (one line
per ruled-out source; "none yet" if empty). If the operator gave no direction,
leave the digest as it is.

Fetch any paper the operator names (arXiv) into `literature/papers/`. List it,
and any paper they supplied as direction, under "Papers the expert named" in
`GUIDANCE.md`: id · what the operator wants from it · its path.

If the operator wants the eventual paper written in a house style of their
own, their `STYLE.md` (how the paper reads) and/or `TEMPLATE.tex` (the
format) go into `runtime/projects/<project>/style/`, before the paper stage;
`style/README.md` there says how. Without them the default style is used.

Show both files to the operator together with `PROBLEM.md` and get their
confirmation before starting the main agent; tell them that from then on
instructions go to the main agent directly (attach its tmux session). After
`pharos main start`, this folder is the main agent's; you never edit it again.

**4. Bring up its verifier.** Required before any fact can exist:

```bash
pharos verify up <project>
```

If it fails because the port is held by another process, another Pharos
deployment on this host owns that port (`pharos new` allocates from the same
base in every deployment; `pharos verify status` says `foreign` for a live one).
That is routine, not a decision to bring to the operator: move the project to
a free port and bring it up again —

```bash
pharos verify port <project> <N>        # service down; rewrites project.json
pharos verify up <project>
```

— and, so it does not recur, set `VERIFY_PORT` in `config/pharos.env` to a
base this deployment owns (say 8101 when the other holds 8091–8099); tell the
operator which. Workers pick the new URL up at their next start.

**5. Start the main agent** in tmux, tagged:

```bash
pharos main start <project> --tag <tag>     # tmux session pharos-v3-<tag>
```

The tag is recorded in `project.json` on first use, so later commands and the
attach hint resolve the same session. This runs `codex` in the project
directory with approvals and sandbox bypassed (colloquially "yolo" — the flag
is `--dangerously-bypass-approvals-and-sandbox`) at the **`ultra`** reasoning
tier, which the project's generated `.codex/config.toml` sets. The main agent
is the strategy brain and is the only session at that tier; workers and the
verifier keep their own.

**6. Hand off and report.** The main agent creates its Goal, assigns workers,
and starts the swarm — *you do not assign work*. Tell the operator: the project
directory, the verify port, and

```bash
tmux attach -t pharos-v3-<tag>
```

If a step fails, stop there and say so with the output. A half-started
experiment (workers running with no verifier, say) produces nothing and looks
like a hard problem.

## See what is running

```bash
pharos list                     # projects + live worker counts
pharos status <project>         # per-worker liveness, round, last fact
pharos verify status            # verify services (per project, with health)
pharos main status              # which experiments have a live main agent
tmux ls                        # the sessions themselves (pharos-v3-*)
```

A healthy experiment has: its verify service `ok`, a live `pharos-v3-<tag>`
session, and workers running. Any one missing is worth reporting.

## Stop a project

`pharos stop <project>`, including `--force`, stops workers only. For a full
project shutdown, preserve its research files and work in this order:

1. Identify the deployment and project directory. Before stopping anything,
   record its process IDs and groups, using tmux panes and `/proc` to check
   working directories, command lines, and project-specific `CODEX_HOME` paths.
   A tag or PID file alone is not proof of ownership; leave ambiguous processes
   untouched and report them. Recheck ownership before each stop/down command
   or signal; signal a whole group only if all members belong to this project.
2. Disable any external restarter for this project, then end the confirmed main
   session with `tmux kill-session -t =pharos-v3-<tag>` and terminate any surviving
   main process, so it cannot restart workers or services. The bundled
   `keep-mains.sh` does not recreate an ended session; leave it running for
   other projects.
3. Run `pharos stop <project> --force` for immediate worker shutdown, or omit
   `--force` and wait for current rounds to finish if requested. Use
   `pharos paper --project <project> status` to enumerate section loops and
   `pharos paper --project <project> stop <section>` for each active loop.
   Stop remaining helpers, reporter/chat sessions, standalone paper verifiers,
   and their model and compute tasks after confirming project ownership.
4. Stop this project's services with `pharos verify down <project>`,
   `pharos index down <project>`, and `pharos monitor down <project>`.
5. Recheck main, worker, paper, and service status, the recorded process groups
   and descendants, and project ports; repeat to detect restarts. Check group
   members even if the leader exited or a command reported `stopped`. For
   confirmed residual processes/groups, send TERM, wait, and use KILL only if
   still alive. Stop only this project's compute scopes, never the shared
   `pharos-compute.slice`, tmux server, or another project's processes.

Report what stopped and anything still running or unverified. Local shutdown
does not confirm cancellation of requests already sent to a remote provider.

## Recover after a host restart

Nothing survives a reboot except the files, which is enough — all mathematical
state lives in each project's stores. Bring the machine back in this order:

```bash
bash scripts/bootstrap.sh                      # rebuilds a dangling venv, re-checks node/codex
pharos doctor                         # confirm the stack before starting anything
rm -f runtime/run/*.pid                        # stale pidfiles from the dead processes
```

Then, **for every project that should be running** (`pharos list`):

```bash
pharos verify up <project>
pharos main start <project>          # the tag is already in project.json
pharos start <project>               # worker loops resume from persisted memory
```

Enumerate the projects rather than trusting a saved list; ask the operator which
projects should come back if it is not obvious. Finish with `pharos verify status`
and report what is up.

## Diagnose a stall

Work outward from the cheapest check.

| symptom | check, in order |
|---|---|
| no facts appearing | is this project's verify up (`pharos verify status`)? then `pharos doctor` |
| workers erroring each round | `pharos check-codex` (backend + recent API-error scan); the worker's `runtime/projects/<p>/workers/<w>/logs/round_*.log` |
| a verification looks wrong | `runtime/projects/<p>/verifier/runs/<run_id>/log.md` |
| main agent unresponsive | `tmux attach -t pharos-v3-<tag>`; if the session is gone, `pharos main start <p>` |
| everything looks up, nothing progresses | attach to the main agent and ask — the blockage is mathematical, not operational |

A running project fixes itself: its main agent restarts its own verifier and
workers as part of its control beat. So a project that is *down* usually means
its **main agent** is down — check that before restarting services under a live
agent, which only duplicates its work.

**An outage must not look like absence.** A backend that is down, rate-limited,
or misconfigured produces empty results and quiet logs, which reads exactly like
"the mathematics is hard". Whenever a project goes quiet, run `pharos check-codex`
before concluding anything about the mathematics, and tell the operator plainly
which of the two you established.

## Reporting

Say what you ran, what it returned, and what you did not check. "verify up on
:8092, main agent running, 4/4 workers alive, backend ping ok" is a report;
"everything looks fine" is not.
