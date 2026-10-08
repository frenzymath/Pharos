"""Run the pharos CLI: ``python -m pharos.orchestration <verb> …`` (the `pharos` command)."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
