# CLI and tools

Use `pharos --help` or `pharos <command> --help` for arguments. Outside project
folders, name the project explicitly; its root makes the project implicit.
Worker and helper directories permit only `compute`, `usage`, and `render`.
The parser and scope rules are in [cli.py](../pharos/orchestration/cli.py) and
[scope.py](../pharos/orchestration/scope.py).

## CLI

| Commands | Purpose |
| --- | --- |
| `new`, `list` | Create projects and inspect the deployment |
| `main start`, `main status` | Manage resident main sessions from outside project folders |
| `assign`, `start`, `status`, `stop` | Set worker tasks and control their loops |
| `verify`, `index`, `monitor` | Start, stop, and inspect project services |
| `sub` | Run a main-agent helper |
| `chat` | Open a separate discussion session |
| `report`, `render` | Write progress reports and render Markdown to PDF |
| `paper` | Assign sections, run and inspect writing loops, verify, and build papers |
| `compute` | Run a script from the project's computation folder under configured limits |
| `usage` | Read recorded token and runtime statistics |
| `doctor`, `check-codex` | Check deployment health and backend access |
| `mcp-call` | Make one MCP call in a fresh session |

For example, assignment uses `pharos assign <project>/<worker> --file <task.md>`
from the repository root. Paper commands use
`pharos paper --project <project> <subcommand>` there; inside a project, omit
`--project`. By default, the installed `codex` command selects the actor's
session home from its working directory; an explicit custom `CODEX_HOME` wins.

## MCP tools

| Tools | Purpose |
| --- | --- |
| `gm_add` | Publish a shared finding |
| `gm_search`, `gm_get` | Search finding summaries and retrieve complete entries |
| `fact_submit` | Submit a proof for verification and write it only if accepted |
| `fact_search`, `fact_get` | Search accepted facts and retrieve statements or proofs |
| `fact_revoke` | Preview, then confirm a dependent-fact revocation cascade |
| `search_arxiv_theorems` | Retrieve published theorem statements |

Tools are exposed according to [role permissions](../pharos/gateway/roles.py);
argument and response definitions are in [server.py](../pharos/gateway/server.py).
The gateway provides these eight tools; paper and report workflows use the CLI
and skills.

## Skill entry points

| Location | Purpose |
| --- | --- |
| [Deployment skills](../.agents/skills/) | Initialize and operate the installation |
| [Main-agent skills](../agents/skills/main/) | Survey, plan routes, assess progress, assign work, and coordinate writing |
| [Worker skills](../agents/skills/worker/) | Proving, memory, literature, and computation |
| [Verification skills](../agents/skills/verify/) | Check a submitted argument and its sources |
| [Reporter skills](../agents/skills/reporter/) | Identify the results and ingredients supporting a report |
| [Section-writing skills](../agents/skills/section/) | Apply the paper's statement and style conventions |
| [Writing-verifier skills](../agents/skills/paper-verify/) | Check paper statements and their proofs |

[Role contracts](../agents/contracts/) and these skills are runtime resources;
keep them with the source checkout.

## Development checks

In a separate Python virtual environment:

```bash
python -m pip install -e '.[dev]'
python -m pytest pharos/ -q
```

Model calls use stubs; service tests use loopback connections. The PDF test uses
Chromium when available, with local MathJax or its CDN fallback.
