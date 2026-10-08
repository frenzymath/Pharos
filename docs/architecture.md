# Architecture

![Pharos architecture](assets/architecture.svg)

## Roles

| Role | Responsibility |
| --- | --- |
| Operations session | Configure the deployment, launch projects, and inspect their processes from the repository root |
| Project main agent | Organize research routes, assign work, record progress, and coordinate writing |
| Workers | Develop proofs and submit results for verification |
| Helpers | Return literature summaries and other advice to the main agent |
| Proof verifier | Review each submission in a fresh session |
| Reporter and writing roles | Produce progress reports, paper sections, and paper reviews |

Each project has its own main agent. Workers receive direction through `TASK.md`
and carry unfinished arguments across rounds in their private local memory.
Helpers' advice can inform research but does not create a verified fact.

## Routes and checkpoints

The main agent keeps `ROUTES.md` as the live record of each approach: its origin,
status, evidence, obstruction, next question, and worker allocation. Routes from
expert guidance and the literature survey remain visible alongside the main
agent's own proposals, including routes that are parked or closed.

A checkpoint is a complete, dated audit that includes the route board and the
established results, missing steps, and next decisions. It is published once;
later changes go into a new checkpoint. The main agent reads the current board,
latest checkpoint, and expert guidance when resuming. The running main session
carries out these reviews according to its contract.

## Verification and memory

A worker submits a statement, proof, and predecessor fact IDs through
`fact_submit`. The gateway calls the verify service, which starts a fresh
verifier session. On acceptance, the gateway writes the fact; otherwise the
worker receives feedback and can revise its proof. Outcomes, including service
errors, are recorded in global memory.

| Store | Contents |
| --- | --- |
| Worker-local memory | Private notes and unfinished attempts |
| Global memory | Shared findings, failed approaches, and verification records |
| Fact graph | Accepted statements and proofs, identified by content and linked by dependencies |

Only accepted facts serve as verified premises. The index service caches
searches over shared stores, with local indexing as a fallback. Revocation
first previews dependent facts, then archives the confirmed cascade.

MCP permissions govern store tools: main agents may add findings and revoke
facts but cannot submit facts; workers may submit; readers cannot write;
verifiers have literature search and read predecessor files directly. Unknown
roles receive the verifier's tool set. See [CLI and tools](cli-and-tools.md).

## Reports and papers

Reports read the latest checkpoint and the project's facts while research
continues. Once a target is a fact, the main agent prepares `paper/OUTLINE.tex`
and assigns sections. Each section writer revises against its own verifier's
feedback; both sessions resume between rounds. A whole-paper verifier checks
the assembled argument before final polishing and building the PDF.

Research files, actor homes, session records, and outputs live in
`runtime/projects/<name>/`; deployment logs and process IDs live separately in
`runtime/logs/` and `runtime/run/`. Implementation is in `pharos/`, with runtime
contracts and skills in `agents/` and deployment skills in `.agents/skills/`.

## Trust boundary

The verifier is a language model, so acceptance is not a formal proof
certificate. Autonomous research sessions bypass Codex approval and sandbox
checks and use the host account's permissions; use a dedicated environment.
MCP role permissions do not restrict those processes' direct filesystem access.
Verify and index services bind to loopback by default and have no authentication
layer for public network access. Credential storage is described in
[Configuration](configuration.md).
