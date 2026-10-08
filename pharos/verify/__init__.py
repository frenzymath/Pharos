"""pharos.verify — the cold-start proof-verifier HTTP service (the sole write-gate).

``service.app`` is the FastAPI app (POST /verify, GET /health). Run as
``python -m pharos.verify`` (or ``uvicorn pharos.verify.service:app``).

The request schema is in ``service.py``; correctness policy lives in
``agents/contracts/verifier.md``.
"""

from __future__ import annotations

from .service import VerifyRequest, app
from .launcher import run_codex_verification
from .prechecks import run_prechecks

__all__ = ["app", "VerifyRequest", "run_codex_verification", "run_prechecks"]
