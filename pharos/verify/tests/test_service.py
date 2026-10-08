"""Verification HTTP contract with a mocked launcher and server entry point."""

from __future__ import annotations

import os
from contextlib import contextmanager

from fastapi import HTTPException
from fastapi.testclient import TestClient

from pharos.verify import service

_STMT = "For every integer n, n + 0 equals n."
_PROOF = (
    "Zero is the additive identity of the integers, so adding zero to any integer n "
    "leaves the value unchanged. Hence n + 0 = n for every integer n, as required."
)

_CANNED_OK = {
    "verification_report": {"summary": "fake accept", "critical_errors": [], "gaps": []},
    "verdict": "correct",
    "repair_hints": "",
}


@contextmanager
def _fake_run(fn):
    """Replace the launcher's codex-run (imported into service) with a fake."""
    orig_run = service.run_codex_verification
    orig_alloc = service._allocate_run_id
    service.run_codex_verification = fn
    service._allocate_run_id = lambda statement: "RID-fake"
    try:
        yield
    finally:
        service.run_codex_verification = orig_run
        service._allocate_run_id = orig_alloc


def _client():
    return TestClient(service.app)


def test_health_ok():
    resp = _client().get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # The PID identifies the service instance for lifecycle checks.
    assert isinstance(body["pid"], int) and body["pid"] > 0


def test_verify_accept_contract():
    def fake(run_id, statement, proof):
        assert run_id == "RID-fake"  # allocator was used
        return _CANNED_OK

    with _fake_run(fake):
        resp = _client().post("/verify", json={"statement": _STMT, "proof": _PROOF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "correct"
    assert body["verification_report"]["critical_errors"] == []
    assert "repair_hints" in body


def test_verify_reject_verdict_still_200():
    # a "wrong" verdict is a normal 200 response (the verdict is the payload).
    canned = dict(_CANNED_OK, verdict="wrong", repair_hints="fix the gap")
    with _fake_run(lambda run_id, statement, proof: canned):
        resp = _client().post("/verify", json={"statement": _STMT, "proof": _PROOF})
    assert resp.status_code == 200 and resp.json()["verdict"] == "wrong"


def _must_not_run(*a, **k):
    raise AssertionError("codex must not run when a precheck rejects")


def test_verify_vacuous_proof_400():
    with _fake_run(_must_not_run):
        resp = _client().post("/verify", json={"statement": _STMT, "proof": "QED"})
    assert resp.status_code == 400 and "vacuous proof" in resp.json()["detail"]


def _raiser(status, detail):
    def fn(run_id, statement, proof):
        raise HTTPException(status_code=status, detail=detail)
    return fn


def test_verify_timeout_504():
    with _fake_run(_raiser(504, "codex exec timed out after 86400s")):
        resp = _client().post("/verify", json={"statement": _STMT, "proof": _PROOF})
    assert resp.status_code == 504 and "timed out" in resp.json()["detail"]


def test_verify_empty_field_422():
    with _fake_run(_must_not_run):
        resp = _client().post("/verify", json={"statement": "", "proof": _PROOF})
    assert resp.status_code == 422


def test_main_entry_sets_defaults_and_calls_uvicorn(monkeypatch):
    # the entrypoint must default CODEX_TIMEOUT_SECONDS (unbounded in-process
    # default -> bounded per-call default) and hand the app to uvicorn on the
    # configured host/port; uvicorn.run is mocked so no server ever binds.
    import runpy

    import uvicorn

    calls = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, host=None, port=None: calls.update(host=host, port=port))
    monkeypatch.delenv("CODEX_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("VERIFY_HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setenv("VERIFY_PORT", "18099")

    runpy.run_module("pharos.verify.__main__", run_name="__main__")

    assert calls == {"host": "127.0.0.1", "port": 18099}
    assert os.environ["CODEX_TIMEOUT_SECONDS"] == "86400"
