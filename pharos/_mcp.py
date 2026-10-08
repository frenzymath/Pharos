"""Resolve the MCP server class by import availability across mcp 1.x and 2.x."""

from __future__ import annotations

try:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP
except ImportError:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as FastMCP

__all__ = ["FastMCP"]
