#!/usr/bin/env bash
# Source this file to load deployment settings and the installed toolchain.

PHAROS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
export PHAROS_ROOT

# 1) your config (account, models, any override) — gitignored, one file
if [ -f "$PHAROS_ROOT/config/pharos.env" ]; then
  set -a; . "$PHAROS_ROOT/config/pharos.env"; set +a
fi

# 2) machine paths written by bootstrap.sh (node, codex.js, venv)
if [ -f "$PHAROS_ROOT/runtime/runtime.env" ]; then
  set -a; . "$PHAROS_ROOT/runtime/runtime.env"; set +a
fi

# 3) where things live + the backend account
export PHAROS_RUNTIME="${PHAROS_RUNTIME:-$PHAROS_ROOT/runtime}"
export PHAROS_AGENTS_ROOT="${PHAROS_AGENTS_ROOT:-$PHAROS_RUNTIME/projects}"
export CODEX_BACKEND="${CODEX_BACKEND:-api}"            # api (BYO key) | chatgpt (your login)
export CODEX_API_BASE_URL="${CODEX_API_BASE_URL:-}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export PHAROS_CODEX_MODEL="${PHAROS_CODEX_MODEL:-gpt-6-astra}"   # shared backend default
export PHAROS_CODEX_EFFORT="${PHAROS_CODEX_EFFORT:-max}"

# 4) PATH: the venv's bin (which holds `pharos` and `codex`) + the provisioned node
_pharos_path=""
[ -n "${PHAROS_VENV:-}" ]     && [ -d "$PHAROS_VENV/bin" ]  && _pharos_path="$PHAROS_VENV/bin"
[ -n "${PHAROS_NODE_BIN:-}" ] && [ -d "$PHAROS_NODE_BIN" ]  && _pharos_path="${_pharos_path:+$_pharos_path:}$PHAROS_NODE_BIN"
if [ -n "$_pharos_path" ]; then
  case ":$PATH:" in *":$_pharos_path:"*) : ;; *) export PATH="$_pharos_path:$PATH" ;; esac
fi

# 5) the python the engine runs on (venv if bootstrapped, else system python3)
if [ -n "${PHAROS_VENV:-}" ] && [ -x "$PHAROS_VENV/bin/python" ]; then
  export PHAROS_PY="$PHAROS_VENV/bin/python"
else
  export PHAROS_PY="${PHAROS_PY:-$(command -v python3 || true)}"
fi

# silent unless PHAROS_ENV_VERBOSE=1
if [ "${PHAROS_ENV_VERBOSE:-0}" = "1" ]; then
  echo "PHAROS_ROOT=$PHAROS_ROOT"
  echo "PHAROS_PY=$PHAROS_PY"
  echo "PHAROS_AGENTS_ROOT=$PHAROS_AGENTS_ROOT"
  echo "CODEX_API_BASE_URL=$CODEX_API_BASE_URL"
fi
