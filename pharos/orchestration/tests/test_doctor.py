"""Health-check tests using stub tools and a closed loopback port."""

from __future__ import annotations

import socket
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from pharos.orchestration import health, paper
from pharos.tests.util import env as _env


def test_tex_engine_override_must_resolve(tmp: Path):
    with _env(PHAROS_TEX_ENGINE=str(tmp / "no-such-latex")):
        assert paper.tex_engine() is None
    fake = tmp / "pdflatex"
    fake.write_text("#!/bin/sh\nexit 0\n"); fake.chmod(0o755)
    with _env(PHAROS_TEX_ENGINE=str(fake)):
        assert paper.tex_engine() == str(fake)


def test_probes_fail_loudly_when_the_tools_are_absent(tmp: Path):
    # a closed loopback port stands in for an unreachable literature service
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    import importlib
    from pharos.integrations import matlas
    try:
        with _env(MATLAS_URL=f"http://127.0.0.1:{port}/thm/search"):
            importlib.reload(matlas)  # The endpoint is read at import time.
            rows = health.probes(chrome=None, engine=None)
    finally:
        importlib.reload(matlas)
    by = {r["label"]: r for r in rows}
    assert by["probe: render a report PDF"]["state"] == "FAIL"
    assert by["probe: compile the paper template"]["state"] == "FAIL"
    assert by["probe: theorem search (matlas)"]["state"] == "FAIL"
    assert "127.0.0.1" in by["probe: theorem search (matlas)"]["detail"]


def test_tex_compile_reports_the_engines_last_lines(tmp: Path):
    fake = tmp / "pdflatex"
    fake.write_text("#!/bin/sh\necho 'boom line 1'\necho '! Undefined control sequence.'\nexit 1\n")
    fake.chmod(0o755)
    (tmp / "main.tex").write_text("x")
    err = paper.tex_compile(str(fake), tmp, "main.tex")
    assert err and "Undefined control sequence" in err
    ok = tmp / "ok-latex"
    ok.write_text("#!/bin/sh\nexit 0\n"); ok.chmod(0o755)
    assert paper.tex_compile(str(ok), tmp, "main.tex") is None


def test_tex_probe_includes_the_sample_body(monkeypatch):
    from pharos.integrations import matlas

    def compile_sample(engine, directory, filename):
        source = (directory / filename).read_text()
        assert "\\section{Doctor}" in source
        assert r"\int_0^1 x\,dx = \tfrac12" in source
        assert "\n%%SECTIONS%%\n" not in source
        (directory / "main.pdf").write_bytes(b"%PDF-stub")

    monkeypatch.setattr(paper, "tex_compile", compile_sample)
    monkeypatch.setattr(matlas, "search", lambda *a, **kw: {"endpoint": "stub"})
    rows = health.probes(chrome=None, engine="stub")
    assert next(r for r in rows if r["label"] == "probe: compile the paper template")["state"] == "ok"


@pytest.mark.parametrize("provider", ["openai-compatible", "azure"])
def test_api_ping_uses_the_configured_credentials(provider, monkeypatch):
    from urllib.parse import parse_qs, urlsplit

    requests = []

    class Endpoint(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((urlsplit(self.path), self.headers, body))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"id":"probe","object":"response","status":"completed","output":[]}')

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Endpoint)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("CODEX_API_BASE_URL", f"http://127.0.0.1:{server.server_port}/api")
    monkeypatch.setenv("CODEX_API_PROVIDER", provider)
    monkeypatch.setenv("PHAROS_CODEX_MODEL", "test-model")
    monkeypatch.setenv("CODEX_API_VERSION", "test-version")
    monkeypatch.delenv("AZURE_OPENAI_AD_TOKEN", raising=False)
    if provider == "azure":
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-azure-key")
    else:
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    try:
        assert health._ping()["ok"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert len(requests) == 1
    url, headers, body = requests[0]
    assert url.path == "/api/responses"
    assert body["model"] == "test-model" and body["input"] == "ping"
    if provider == "azure":
        assert headers["api-key"] == "test-azure-key"
        assert parse_qs(url.query) == {"api-version": ["test-version"]}
    else:
        assert headers["Authorization"] == "Bearer test-openai-key"
        assert not url.query


def test_azure_ping_requires_its_api_version(monkeypatch):
    monkeypatch.setenv("CODEX_API_PROVIDER", "azure")
    monkeypatch.setenv("CODEX_API_BASE_URL", "http://127.0.0.1:1/api")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("CODEX_API_VERSION", raising=False)
    result = health._ping()
    assert not result["ok"] and "CODEX_API_VERSION" in result["err"]
