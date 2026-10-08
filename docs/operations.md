# Operations

These commands are a manual reference; the repository-root ops session normally
runs them for you. Load `scripts/env.sh` first. The [operating guide](operating-guide.md)
covers research interaction, and [CLI and tools](cli-and-tools.md) lists commands.

## Services and activity

From the repository root, name the project explicitly:

| Command | Purpose |
| --- | --- |
| `pharos verify up <project>` | Start the required proof-verification service |
| `pharos index up <project>` | Start shared search caches |
| `pharos monitor up <project>` | Start process and resource sampling |
| `pharos main start <project> --tag <tag>` | Start the main session in tmux `pharos-v3-<tag>` |
| `pharos start <project>` | Resume workers from their assignments and saved memory |

Use `status` in place of `up` to inspect the services, `pharos main status` for
main sessions, and `pharos status <project>` for workers. The main agent writes
assignments before starting workers. Attach to its tmux session for instructions.
`pharos chat <project>` is for discussion; its messages do not automatically
become research instructions and decisions must be given to the main session.

Worker logs are in `<project>/workers/<name>/logs/`, verification logs in
`<project>/verifier/`, and monitoring records in `<project>/monitor.jsonl`.
Index logs are under `runtime/logs/index-<project>.log`.

## Stop and recover

For a complete stop, tell the root ops session which project to stop and keep
stopped. `pharos stop`, including `--force`, stops only workers; ops must also
end that project's main session, helpers, paper loops, identified model and
computation tasks, and project services, then check for remaining local work.
Other projects and saved research data must remain intact.

```bash
pharos stop <project>                 # finish current worker rounds, then stop
pharos stop <project> --force         # stop worker process groups immediately
```

Services have `down` commands, and active paper sections have
`pharos paper --project <project> stop <section>`. Ending the main tmux session
also prevents `keep-mains.sh` from resuming that session.

After a host restart, load the environment, run `pharos doctor`, and restart
the services and main session for each project you intend to resume.
`pharos start <project>` resumes workers from saved assignments and memory.
Preserve project folders and deployment logs when retiring a run.

## Diagnostics

| Symptom | Check |
| --- | --- |
| No facts appearing | `pharos verify status <project>` and its service log |
| Worker errors or inactivity | Worker round logs and `pharos check-codex` |
| A service reports `foreign` | Another process answered on its port; verify ownership before changing it |
| Rendering or literature retrieval fails | `pharos doctor --probe` and the returned error |

With API authentication, `doctor` and `check-codex` make live backend requests.
To change a verify port, stop that service first and use
`pharos verify port <project> <port>`.
The optional `scripts/keep-mains.sh` requires `jq` and tmux; it detects the
`Goal stalled` footer and sends `/goal resume` to existing main sessions.
There is no bundled web dashboard.
