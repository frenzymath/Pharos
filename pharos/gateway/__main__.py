"""Run the pharos gateway as a stdio MCP server: ``python -m pharos.gateway``.

Role is taken from ``PHAROS_ROLE`` (env). Launched from each agent's generated
``.codex/config.toml`` (main / worker) or the verifier's ``-c`` override.
"""

from .server import build_app

if __name__ == "__main__":
    build_app().run()
