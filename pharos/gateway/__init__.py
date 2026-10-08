"""Role-gated MCP server. Run with ``python -m pharos.gateway``."""

from __future__ import annotations

from .roles import ALL_TOOLS, ROLE_TOOLS, tools_for
from .server import build_app

__all__ = ["build_app", "tools_for", "ROLE_TOOLS", "ALL_TOOLS"]
