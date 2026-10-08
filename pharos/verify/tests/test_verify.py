"""Verification request tests using a local Codex stub."""

from __future__ import annotations

import stat
import tempfile
from pathlib import Path

from fastapi import HTTPException

from pharos.tests.util import env as _env
from pharos.verify.service import VerifyRequest, verify

FAKE = Path(__file__).resolve().parent / "fake_codex.py"

_GOOD_STATEMENT = "For every integer n, n + 0 equals n."
_GOOD_PROOF = (
    "Zero is the additive identity of the integers, so adding zero to any integer n "
    "leaves the value unchanged. Hence n + 0 = n for every integer n, as required."
)


def _ensure_fake_executable():
    FAKE.chmod(FAKE.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _call(statement, proof, tmp):
    with _env(PHAROS_CODEX_BIN=str(FAKE)), \
            _env(VERIFIER_RESULTS_DIR=str(Path(tmp) / "runs"), VERIFY_AGENT_HOME=str(tmp)):
        return verify(VerifyRequest(statement=statement, proof=proof))


def test_verify_accept_via_fake_codex():
    _ensure_fake_executable()
    with tempfile.TemporaryDirectory() as tmp:
        out = _call(_GOOD_STATEMENT, _GOOD_PROOF, tmp)
        assert out["verdict"] == "correct" and out["verification_report"]["critical_errors"] == []


def test_verify_reject_via_fake_codex():
    _ensure_fake_executable()
    with tempfile.TemporaryDirectory() as tmp:
        out = _call(_GOOD_STATEMENT, _GOOD_PROOF + " [[FAKE:wrong]]", tmp)
        assert out["verdict"] == "wrong" and out["repair_hints"]


def test_verify_vacuous_rejected_400():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _call("Trivial lemma about integers.", "QED", tmp)
            assert False, "vacuous proof should be rejected"
        except HTTPException as e:
            assert e.status_code == 400
