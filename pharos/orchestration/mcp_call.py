"""One-shot client for recovering a closed main-agent MCP transport.

This keeps the normal Pharos permission boundary: every invocation starts the
configured role-gated stdio gateway and calls one registered MCP tool.  It is
intended for an already-running Codex session whose long-lived MCP pipe cannot
be reconnected by the host.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import anyio
from mcp import ClientSession, StdioServerParameters, stdio_client


async def _call(tool: str, arguments: dict[str, Any]) -> int:
    root = Path(os.environ.get("PHAROS_ROOT", Path(__file__).resolve().parents[2]))
    env = {key: value for key, value in os.environ.items() if key.startswith("PHAROS_")}
    # This recovery client belongs to the main-agent surface. Do not let an
    # inherited shell environment widen its gateway permissions.
    env["PHAROS_ROLE"] = "main"
    env["PHAROS_AUTHOR"] = "main_agent"
    # Use this interpreter to keep the gateway in the same installation.
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "pharos.gateway"],
        cwd=root,
        env=env,
    )
    async with stdio_client(server) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            await session.list_tools()
            result = await session.call_tool(tool, arguments)
    payload = result.model_dump(mode="json", by_alias=True, exclude_none=True)
    print(json.dumps(payload, ensure_ascii=False))
    return 1 if payload.get("isError") else 0


def run(tool: str, json_args: Optional[str] = None, use_stdin: bool = False) -> int:
    """Call one MCP tool in a fresh session. Used by ``pharos mcp-call``."""
    try:
        if use_stdin:
            raw = sys.stdin.read()
        else:
            raw = json_args or "{}"
        arguments = json.loads(raw) if raw.strip() else {}
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be a JSON object")
        return anyio.run(_call, tool, arguments)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"invalid arguments: {exc}", file=sys.stderr)
        return 2
