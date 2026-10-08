"""Run one project's verify service: ``python -m pharos.verify``.

``pharos verify up <project>`` sets the per-project env (``VERIFY_PORT`` from
project.json, ``VERIFIER_RESULTS_DIR`` + ``CODEX_HOME`` inside the project
dir) so each project's verifier keeps its own run logs and sessions."""

from __future__ import annotations

import os

if __name__ == "__main__":
    import uvicorn

    from pharos import codex
    from .service import app

    # This launcher entrypoint supplies a bounded per-verification codex time
    # unless the operator overrides; the library default (launcher._timeout)
    # stays 0/None (= no timeout) for in-process use.
    os.environ.setdefault("CODEX_TIMEOUT_SECONDS", "86400")
    # Per-project session store: the verifier subprocesses inherit CODEX_HOME
    # from this process; make sure it exists and links the shared config.
    if os.environ.get("CODEX_HOME"):
        codex.provision_codex_home(os.environ["CODEX_HOME"])
    host = os.getenv("VERIFY_HOST", "127.0.0.1")
    port = int(os.getenv("VERIFY_PORT", os.getenv("PORT", "8091")))
    uvicorn.run(app, host=host, port=port)
