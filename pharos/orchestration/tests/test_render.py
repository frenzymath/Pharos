"""Math rendering, report paths, and optional Chromium PDF tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pharos.orchestration import render as R

_MD = """# The contraction estimate: a progress report

Some prose with math: let $a_{i} \\le b_{j}^{*}$ and consider
$$\\int_0^1 f(x)\\,dx = \\sum_{n \\ge 1} c_n.$$

## Key theorems

| route | status |
|---|---|
| weighted energy | proved |
"""


def test_math_survives_markdown():
    html = R.build_html(_MD)
    # underscores/asterisks inside math must NOT become <em>/<strong>
    assert r"\(a_{i} \le b_{j}^{*}\)" in html
    assert r"\int_0^1" in html and "<em>" not in html.split("math-display")[1][:80]
    assert "<title>The contraction estimate: a progress report</title>" in html
    assert "<table>" in html                        # tables enabled for reports
    assert "MathJax" in html


def test_default_pdf_pairing(tmp_path: Path):
    md = tmp_path / "human_report" / "md" / "2026-09-01T12.md"
    assert R.default_pdf_path(md) == tmp_path / "human_report" / "pdf" / "2026-09-01T12.pdf"
    loose = tmp_path / "note.md"
    assert R.default_pdf_path(loose) == tmp_path / "note.pdf"


@pytest.mark.skipif(not R.chrome_bin(), reason="no chromium/chrome on host")
def test_render_end_to_end(tmp_path: Path):
    md = tmp_path / "human_report" / "md" / "r1.md"
    md.parent.mkdir(parents=True)
    md.write_text(_MD, encoding="utf-8")
    out = R.render(md)
    assert out == tmp_path / "human_report" / "pdf" / "r1.pdf"
    assert out.stat().st_size > 10_000               # a real PDF, not an error page
    assert out.read_bytes()[:5] == b"%PDF-"
