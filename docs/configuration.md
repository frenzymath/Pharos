# Configuration

Copy `config/pharos.env.example` to `config/pharos.env`, use valid shell syntax,
and run `source scripts/env.sh` after editing it. The configuration file and
`runtime/` are ignored by Git; API and subscription login may store credentials
in the shared runtime authentication home.

## Backend and models

The default model is GPT-6 Astra; backend setup steps are in
[Getting started](getting-started.md#configure-the-backend).

| Setting | Default or use |
| --- | --- |
| `CODEX_BACKEND` | `api`; use `chatgpt` for subscription login |
| `CODEX_API_PROVIDER` | `openai-compatible`; use `azure` for Azure OpenAI |
| `CODEX_API_BASE_URL` | Required API base URL; no default endpoint |
| `OPENAI_API_KEY` | Key for a Responses-compatible provider |
| `AZURE_OPENAI_API_KEY`, `CODEX_API_VERSION` | Key and API version for Azure |
| `PHAROS_CODEX_MODEL`, `PHAROS_CODEX_EFFORT` | Shared defaults: `gpt-6-astra`, `max` |
| `PHAROS_WORKER_MODEL` | New project main/worker model: `gpt-6-astra`; `pharos new --model` takes precedence |
| `PHAROS_VERIFY_MODEL`, `PHAROS_VERIFY_EFFORT` | Verifier overrides; otherwise shared defaults |

New projects save their model in `project.json` and workers' `.role` files;
changing environment defaults does not replace those saved choices. The main
agent uses `ultra`, and `pharos new --roles` selects worker reasoning tiers.
Run `scripts/setup-codex.sh api` or `login` again after changing shared settings.

## Paths and services

| Setting | Default or use |
| --- | --- |
| `PHAROS_RUNTIME` | `<checkout>/runtime` |
| `PHAROS_AGENTS_ROOT` | `<runtime>/projects` |
| `PHAROS_CODEX_SHARED_HOME` | `<runtime>/codex-home`: shared configuration and authentication |
| `VERIFY_PORT` | `8091`, the base for allocating each new project's verify port |
| `VERIFY_HOST`, `PHAROS_INDEX_HOST` | `127.0.0.1` |
| `PHAROS_MONITOR_INTERVAL` | `120` seconds |
| `PHAROS_ROUND_HARD_TIMEOUT` | `14400` seconds per worker round |
| `PHAROS_MAX_ROUNDS` | `0`, unlimited |

The project stores its verify and index ports in `project.json`; use the CLI to
manage them. Each actor has its own session home and role contract, while
configuration and authentication link to the shared home. Avoid exporting one
`CODEX_HOME` for all actors.

## Reports and computation

| Setting | Default or use |
| --- | --- |
| `PHAROS_CHROME_BIN` | Auto-detected Chromium/Chrome executable |
| `PHAROS_MATHJAX_JS` | `runtime/render/tex-svg.js`, with CDN fallback |
| `PHAROS_TEX_ENGINE` | Auto-detected `pdflatex` or `tectonic` |
| `PHAROS_PRICE_INPUT`, `PHAROS_PRICE_CACHED`, `PHAROS_PRICE_OUTPUT` | USD per million tokens for cost estimates |

With user systemd available, `config/pharos-compute.slice` limits the deployment's
computation pool to 4 CPUs and 16 GB. Without it, computation has per-job memory
limits and low priority but no collective CPU or memory cap. Scripts run through
`pharos compute` from a project's `computation/` folder.

Less common overrides are documented alongside their implementation in
[execution](../pharos/execution/) and [orchestration](../pharos/orchestration/).
