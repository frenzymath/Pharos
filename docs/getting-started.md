# Getting started

If Codex is already available, open a session in this checkout's root and ask
it to set up Pharos; the commands below are the manual installation reference.

## Install

Use a dedicated Linux environment with Python 3.10+, Git, Bash, curl, tar,
and tmux. Install Chromium or Chrome for reports and `pdflatex` or `tectonic`
for papers through your host's package manager.

```bash
git clone https://github.com/frenzymath/Pharos.git
cd Pharos
bash scripts/bootstrap.sh
cp config/pharos.env.example config/pharos.env
```

Bootstrap installs Node, a Python environment, the Codex CLI, and MathJax under
`runtime/`; it also registers the computation slice with user systemd and links
`pharos` into `~/.local/bin`. Keep the source tree in place for runtime resources.

## Configure the backend

Edit `config/pharos.env` with one of these choices:

| Backend | Required settings | Setup |
| --- | --- | --- |
| Responses-compatible API | `CODEX_API_BASE_URL`, `OPENAI_API_KEY` | `bash scripts/setup-codex.sh api` |
| Azure OpenAI | `CODEX_API_PROVIDER=azure`, `CODEX_API_BASE_URL`, `CODEX_API_VERSION`, `AZURE_OPENAI_API_KEY` | `bash scripts/setup-codex.sh api` |
| Subscription login | `CODEX_BACKEND=chatgpt` | `bash scripts/setup-codex.sh login` |

The default model is GPT-6 Astra (`gpt-6-astra`). Select a backend that supports the
configured model and reasoning tiers: shared defaults use `max`, the project
main uses `ultra`, and worker tiers default to `xhigh` and `max`. Model overrides
and saved project settings are explained in [Configuration](configuration.md).

Load the settings and check the installation:

```bash
source scripts/env.sh
pharos doctor
```

In API mode this makes a live request; subscription mode checks login status.
`pharos doctor --probe` additionally tests PDF rendering, TeX compilation, and
literature retrieval. Resolve reported failures before starting research.

## Open the operations session

From the repository root, run:

```bash
codex
```

Codex reads the root `AGENTS.md` and loads the operations role. Use natural
language to provide a problem, paths to your materials, and your requirements;
the ops agent configures the deployment, creates the project, and launches it.
It shows you the problem statement and initial guidance before research starts.

You can also select the Pharos repository folder as a project in the Codex
desktop app. That session needs access to the configured Linux deployment and
its tools; selecting a folder does not perform the installation above.

After launch, give research instructions to the project's main session and
machine or deployment requests to the root ops session. The
[operating guide](operating-guide.md) covers that workflow; [Operations](operations.md)
is the manual reference for services and recovery.
