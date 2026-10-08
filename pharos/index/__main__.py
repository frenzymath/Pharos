"""Run one project's index service: ``python -m pharos.index``.

``pharos index up <project>`` sets ``PHAROS_PROJECT_DIR`` and ``PHAROS_INDEX_PORT``
(from project.json) and starts this detached, like the verify service."""

from __future__ import annotations

import os
from pathlib import Path

from .service import serve

if __name__ == "__main__":
    pdir = os.environ.get("PHAROS_PROJECT_DIR")
    if not pdir:
        raise SystemExit("PHAROS_PROJECT_DIR is not set")
    host = os.environ.get("PHAROS_INDEX_HOST", "127.0.0.1")
    port = int(os.environ.get("PHAROS_INDEX_PORT", "0"))
    serve(Path(pdir), host, port)
