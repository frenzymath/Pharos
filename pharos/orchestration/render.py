"""Render Markdown reports with TeX math to PDF using headless Chromium.

MathJax uses a local copy from ``runtime/render/`` when available, or a CDN
fallback. Reports in ``human_report/md/`` render to ``human_report/pdf/``.
"""

from __future__ import annotations

import html
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

_MATHJAX_CDN = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"

_CSS_FILE = Path(__file__).with_name("paper.css")

_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>{css}</style>
<script>
MathJax = {{ tex: {{ inlineMath: [["\\\\(", "\\\\)"]],
                     displayMath: [["\\\\[", "\\\\]"]] }},
             svg: {{ fontCache: "local" }} }};
</script>
<script src="{mathjax}"></script>
</head><body>
{body}
</body></html>
"""


def _md():
    from markdown_it import MarkdownIt
    from mdit_py_plugins.dollarmath import dollarmath_plugin

    # Accept display math immediately after prose without a blank line.
    md = (MarkdownIt("commonmark")
          .use(dollarmath_plugin, double_inline=True).enable(["table"]))

    # Preserve TeX underscores and asterisks for MathJax.
    def inline(self, tokens, idx, options, env):
        return r"\(" + html.escape(tokens[idx].content) + r"\)"

    def block(self, tokens, idx, options, env):
        return ('<div class="math-display">\\['
                + html.escape(tokens[idx].content) + "\\]</div>\n")

    md.add_render_rule("math_inline", inline)
    md.add_render_rule("math_inline_double", block)
    md.add_render_rule("math_block", block)
    return md


def _title(md, text: str) -> str:
    tokens = md.parse(text)
    for i, t in enumerate(tokens):
        if t.type == "heading_open" and t.tag == "h1":
            return tokens[i + 1].content
    return "report"


def mathjax_src() -> str:
    env = os.environ.get("PHAROS_MATHJAX_JS")
    if env:
        return Path(env).resolve().as_uri() if Path(env).exists() else env
    from pharos.execution.layout import repo_root
    vendored = repo_root() / "runtime" / "render" / "tex-svg.js"
    return vendored.as_uri() if vendored.is_file() else _MATHJAX_CDN


def build_html(md_text: str) -> str:
    md = _md()
    return _PAGE.format(title=html.escape(_title(md, md_text)),
                        css=_CSS_FILE.read_text(encoding="utf-8"),
                        mathjax=mathjax_src(), body=md.render(md_text))


def chrome_bin() -> Optional[str]:
    env = os.environ.get("PHAROS_CHROME_BIN")
    if env:
        return env
    for c in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        if shutil.which(c):
            return c
    return None


def default_pdf_path(md_path: Path) -> Path:
    """``…/human_report/md/X.md → …/human_report/pdf/X.pdf``; else alongside."""
    if md_path.parent.name == "md":
        return md_path.parent.parent / "pdf" / (md_path.stem + ".pdf")
    return md_path.with_suffix(".pdf")


def render(md_path: Path, pdf_path: Optional[Path] = None) -> Path:
    """Markdown file → PDF file. Raises SystemExit with a clear message when
    the input or chrome is missing, or chrome fails."""
    md_path = Path(md_path)
    if not md_path.is_file():
        raise SystemExit(f"no such markdown file: {md_path}")
    out = Path(pdf_path) if pdf_path else default_pdf_path(md_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    chrome = chrome_bin()
    if not chrome:
        raise SystemExit("no chromium/chrome found (set PHAROS_CHROME_BIN)")

    html_text = build_html(md_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        page = Path(td) / "report.html"
        page.write_text(html_text, encoding="utf-8")
        cmd = [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
               "--virtual-time-budget=20000",     # let MathJax finish typesetting
               f"--print-to-pdf={out}", page.resolve().as_uri()]
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if done.returncode != 0 or not out.is_file():
        raise SystemExit(f"chrome render failed (rc={done.returncode}): "
                         f"{(done.stderr or '').strip()[-400:]}")
    return out
