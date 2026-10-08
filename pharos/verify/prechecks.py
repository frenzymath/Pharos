"""Reject empty or insubstantial inputs before launching the verifier.

These checks cannot accept a proof. Mathematical judgments belong to the
verifier contract in ``agents/contracts/verifier.md``.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

MIN_STATEMENT_CHARS = 10
MIN_PROOF_CHARS = 30
MIN_PROOF_WORDS = 5

_VACUOUS_PROOF_MARKERS = (
    "todo", "fixme", "tbd", "to be done", "see above", "see below", "obvious",
    "obviously true", "trivial", "trivially true", "left as exercise",
    "left to the reader", "exercise for the reader", "by inspection",
    "by definition", "clear", "clearly", "qed",
)


def _strip_markdown_noise(text: str) -> str:
    """Remove code fences / inline code / quote & hr / header markers and collapse
    whitespace, so markdown wrappers can't make a vacuous proof look substantive."""
    no_fences = re.sub(r"```[\s\S]*?```", "", text)
    no_inline_code = re.sub(r"`[^`\n]*`", "", no_fences)
    no_quotes = re.sub(r"^\s*>\s?", "", no_inline_code, flags=re.MULTILINE)
    no_hr = re.sub(r"^\s*[-*_]{3,}\s*$", "", no_quotes, flags=re.MULTILINE)
    no_headers = re.sub(r"^\s*#+\s*", "", no_hr, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", no_headers).strip()


def is_vacuous_proof(proof: str) -> Tuple[bool, str]:
    """Return whether a proof is too short or reduces to a vacuous marker, and why."""
    cleaned = _strip_markdown_noise(proof)
    if len(cleaned) < MIN_PROOF_CHARS:
        return True, (
            f"proof has only {len(cleaned)} substantive characters after stripping "
            f"markdown noise (minimum {MIN_PROOF_CHARS}). A vacuous or near-empty "
            "proof cannot be passed by the verifier."
        )
    word_count = len(re.findall(r"\b\w+\b", cleaned))
    if word_count < MIN_PROOF_WORDS:
        return True, f"proof has only {word_count} substantive words (minimum {MIN_PROOF_WORDS})."
    stripped_lowered = re.sub(r"[^\w\s]", "", cleaned.lower()).strip()
    for marker in _VACUOUS_PROOF_MARKERS:
        if stripped_lowered == marker:
            return True, (
                f'proof body reduces to the vacuous marker "{marker}" after '
                "stripping punctuation and markdown noise."
            )
    return False, ""


def is_vacuous_statement(statement: str) -> Tuple[bool, str]:
    """(is_vacuous, reason). Only refuses statements too short to be real."""
    cleaned = _strip_markdown_noise(statement)
    if len(cleaned) < MIN_STATEMENT_CHARS:
        return True, (
            f"statement has only {len(cleaned)} substantive characters after "
            f"stripping markdown noise (minimum {MIN_STATEMENT_CHARS}). Refusing to "
            "verify against an essentially empty statement."
        )
    return False, ""


def run_prechecks(statement: str, proof: str) -> Optional[Tuple[int, str]]:
    """Run the vacuousness pre-checks. Returns ``(http_status, detail)`` for the
    first rejection, or ``None`` if both pass."""
    vac, reason = is_vacuous_statement(statement)
    if vac:
        return 400, f"vacuous statement: {reason}"
    vac, reason = is_vacuous_proof(proof)
    if vac:
        return 400, f"vacuous proof: {reason}"
    return None
