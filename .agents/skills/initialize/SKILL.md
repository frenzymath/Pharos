---
name: initialize
description: Bring a fresh Pharos checkout to a healthy, ready-to-run deployment — toolchain, codex backend, operator profile. Use once per deployment (or after moving the checkout to a new host); day-to-day running of projects and services is the operate skill.
---

# Initialize a Pharos deployment

You are the ops agent (see `AGENTS.md`). This is the one-time bring-up. It ends
with a host that can create projects, not with a project.

1. **See what is already true** — `bash scripts/bootstrap.sh` (idempotent:
   Node, the venv, the pinned npm codex, `runtime/runtime.env`; it ends by
   naming any system tool the host lacks), then `pharos doctor`. Inspect the
   current branch and whether `config/pharos.env` exists.
   **Three host tools are not optional**, because three deliverables depend
   on them: `tmux` (the main agent lives in a tmux session), a Chromium
   (`chromium` / `google-chrome` — every human report is rendered through it),
   and a TeX engine (`pdflatex` from TeX Live, or `tectonic` — the paper).
   Bootstrap installs nothing system-wide, so when `doctor` marks one of them
   FAIL, tell the operator the exact package to install (Debian/Ubuntu:
   `tmux chromium texlive-latex-extra texlive-fonts-extra`; Fedora:
   `tmux chromium texlive-scheme-medium`) and either install it with their
   permission or wait until they have. A deployment without them is not ready,
   whatever else works.
2. **Interview the operator, briefly.** Ask only for what you cannot read:
   how to address them and in which language, the codex backend, the working
   branch, the default worker roster, and — when this host is shared with
   another Pharos deployment — which port range is this deployment's. Do not
   re-ask anything already in `OPERATOR.md`.
3. **Configure.** Copy `config/pharos.env.example` to `config/pharos.env` if it is
   missing, and fill it. Put operator-supplied credentials in that gitignored
   file; Codex authentication stays in its ignored runtime home. Never commit
   credentials or echo a key back. On a shared host set `VERIFY_PORT` there:
   it is the base `pharos new` allocates verify ports from, and two deployments
   allocating from the same base collide (`pharos new` skips ports the host
   already holds, but only a distinct base keeps them apart for good).
4. **Record durable operator preferences** in `OPERATOR.md` — how they want to
   be addressed, language, and any standing instruction. This is what every
   later session reads.
5. **Wire the codex backend** — `bash scripts/setup-codex.sh api` (or `login`
   for a ChatGPT subscription), then `pharos check-codex` to confirm
   the endpoint actually answers. This writes the ONE shared codex home whose
   config + credential every agent symlinks to.
6. **Confirm health for real, then mark it** — run `pharos doctor --probe`.
   Beyond the presence checks it renders a PDF through Chromium, compiles the
   default paper template through the TeX engine (so every package the paper
   needs is proven installed), and queries the literature service; in this
   mode a missing config, backend or node is a FAIL too. Write
   `runtime/.pharos-initialized` only when the probe run shows **no FAIL**, and
   every remaining `warn` has been either fixed or explicitly accepted by the
   operator (a `warn` on the MathJax bundle or the compute slice is a real
   limitation — say what it costs). Paste the doctor output into your report.
7. **Hand off to `operate`.** Creating a project, starting its verify service,
   and launching its main agent belong to that skill — do not do them here
   unless the operator asks in the same breath.

Report what you actually ran and what it returned. If a step failed, say so with
the output rather than moving on. Never push or publish automatically.
