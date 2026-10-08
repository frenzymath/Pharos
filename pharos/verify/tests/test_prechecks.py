"""Offline tests for pharos.verify.prechecks — the vacuousness gate."""

from __future__ import annotations

from pharos.verify import prechecks


def test_vacuous_proof_short_and_markers():
    assert prechecks.is_vacuous_proof("")[0] is True
    assert prechecks.is_vacuous_proof("QED")[0] is True
    assert prechecks.is_vacuous_proof("obvious.")[0] is True
    # markdown wrappers can't dress up an empty proof
    assert prechecks.is_vacuous_proof("```\n\n```\n> \n# \n---\n`x`")[0] is True


def test_real_one_line_proof_passes():
    proof = ("Zero is the additive identity of the integers, so adding zero to "
             "any integer n leaves the value unchanged; hence n + 0 = n.")
    assert prechecks.is_vacuous_proof(proof)[0] is False


def test_vacuous_statement():
    assert prechecks.is_vacuous_statement("x")[0] is True
    assert prechecks.is_vacuous_statement("For every integer n, n + 0 = n.")[0] is False


def test_run_prechecks_status_and_pass():
    status, detail = prechecks.run_prechecks("x", "whatever proof text this is, long enough")
    assert status == 400 and "vacuous statement" in detail
    status, detail = prechecks.run_prechecks("For every integer n, n + 0 = n.", "QED")
    assert status == 400 and "vacuous proof" in detail
    assert prechecks.run_prechecks(
        "For every integer n, n + 0 = n.",
        "Zero is the additive identity, so adding it to n changes nothing; done.",
    ) is None
