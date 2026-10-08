"""Pharos index service — one process per project that holds the search caches.

    GET  /health                                   -> {status: "ok", pid, project}
    POST /fact_search {query, limit?}              -> {results: [{fact_id, score, statement} …]}
    POST /gm_search   {query, kinds?, limit_per_kind?} -> GlobalMemory.search(...) verbatim
    POST /gm_get      {entry_id}                   -> {entry: <entry> | null}

Gateways forward searches here and fall back to their own index if unavailable.
The service shares one cache per project. Writes go directly to the stores;
searches discover changed fact files and appended memory entries on each call.
The server binds to loopback by default.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from pharos.core import FactGraph, GlobalMemory

_LOCK = threading.Lock()          # the core indexes are plain dicts: one call at a time


def _handle(project_dir: Path, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if path == "/fact_search":
        query = str(payload.get("query", ""))
        limit = int(payload.get("limit", 10))
        with _LOCK:
            return {"results": FactGraph(project_dir).search(query, limit=limit)}
    if path == "/gm_search":
        query = str(payload.get("query", ""))
        kinds = payload.get("kinds")
        limit_per_kind = int(payload.get("limit_per_kind", 10))
        with _LOCK:
            return GlobalMemory(project_dir).search(query, kinds=kinds, limit_per_kind=limit_per_kind)
    if path == "/gm_get":
        entry_id = str(payload.get("entry_id", ""))
        with _LOCK:
            return {"entry": GlobalMemory(project_dir).get(entry_id)}
    raise KeyError(path)


def build_server(project_dir: Path, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    """An HTTP server bound to ``host:port`` (``0`` = ephemeral) serving one project."""
    project_dir = Path(project_dir)

    class Handler(BaseHTTPRequestHandler):
        server_version = "pharos-index/3.1"

        def log_message(self, fmt, *args):   # Errors are logged separately.
            return

        def _send(self, code: int, body: Dict[str, Any]) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # noqa: N802 (http.server API)
            if self.path == "/health":
                self._send(200, {"status": "ok", "pid": os.getpid(), "project": project_dir.name})
            else:
                self._send(404, {"error": f"no such path {self.path!r}"})

        def do_POST(self):  # noqa: N802
            try:
                length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("body must be a JSON object")
            except (ValueError, UnicodeDecodeError) as exc:
                self._send(400, {"error": f"bad request: {exc}"})
                return
            try:
                self._send(200, _handle(project_dir, self.path, payload))
            except KeyError:
                self._send(404, {"error": f"no such path {self.path!r}"})
            except Exception as exc:  # noqa: BLE001
                print(f"pharos index: {self.path} failed: {exc!r}", file=sys.stderr, flush=True)
                self._send(500, {"error": repr(exc)})

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    return httpd


def serve(project_dir: Path, host: str, port: int) -> None:
    httpd = build_server(project_dir, host, port)
    print(f"pharos index: serving {Path(project_dir).name} on http://{host}:{httpd.server_address[1]} "
          f"(pid {os.getpid()})", file=sys.stderr, flush=True)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
