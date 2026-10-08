#!/usr/bin/env bash
# Install the Pharos runtime and register the user-level computation slice.
# Usage: bash scripts/bootstrap.sh
# Downloads Node, a Python environment, Codex, and MathJax under runtime/.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHAROS_ROOT="$(cd "$HERE/.." && pwd)"
RT="$PHAROS_ROOT/runtime"
NODE_VERSION="${NODE_VERSION:-v22.14.0}"
CODEX_NPM_VERSION="${PHAROS_CODEX_SOURCE_VERSION:-0.153.4}"
ARCH="$(uname -m)"; case "$ARCH" in x86_64) NARCH=x64;; aarch64|arm64) NARCH=arm64;; *) NARCH=x64;; esac
mkdir -p "$RT/logs"
log(){ printf '[bootstrap] %s\n' "$*"; }

# Be polite about IO/CPU (do not saturate a shared host).
NICE="nice -n19"; command -v ionice >/dev/null 2>&1 && NICE="ionice -c3 $NICE"

# Node 22
NODE_DIR="$RT/node22"
if [ -x "$NODE_DIR/bin/node" ]; then
  log "node present: $("$NODE_DIR/bin/node" --version)"
else
  log "installing Node $NODE_VERSION ($NARCH) -> $NODE_DIR"
  TARBALL="node-$NODE_VERSION-linux-$NARCH.tar.xz"
  $NICE curl -fsSL "https://nodejs.org/dist/$NODE_VERSION/$TARBALL" -o "$RT/$TARBALL" || true
  [ -s "$RT/$TARBALL" ] || { log "FATAL: could not download node (set NODE_VERSION / check network)"; exit 1; }
  mkdir -p "$NODE_DIR"
  tar -xJf "$RT/$TARBALL" -C "$NODE_DIR" --strip-components=1
  rm -f "$RT/$TARBALL"
  log "node installed: $("$NODE_DIR/bin/node" --version)"
fi
export PATH="$NODE_DIR/bin:$PATH"

# Python venv + deps
# Check the interpreter and dependencies before reusing an environment.
VENV="$RT/venv"
export PIP_DISABLE_PIP_VERSION_CHECK=1
DEPS='import mcp,fastapi,uvicorn,pydantic,openai,pytest,markdown_it,mdit_py_plugins'
if "$VENV/bin/python" -c "$DEPS" 2>/dev/null; then
  log "venv present + healthy"
else
  [ -e "$VENV" ] && { log "venv missing/broken (dangling base interpreter?) — rebuilding"; rm -rf "$VENV"; }
  PYBASE="$(command -v python3)"; [ -n "$PYBASE" ] || { log "FATAL: no python3 on PATH to build the venv"; exit 1; }
  log "creating venv ($PYBASE) -> $VENV"
  "$PYBASE" -m venv "$VENV"
  log "installing python deps (mcp/fastapi/uvicorn/pydantic/openai/pytest)"
  $NICE "$VENV/bin/pip" install --quiet --no-cache-dir --upgrade pip >/dev/null 2>&1 || true
  $NICE "$VENV/bin/pip" install --quiet --no-cache-dir \
    "mcp>=1.0.0" "fastapi>=0.110.0" "uvicorn>=0.30.0" "pydantic>=2.0" "openai>=1.0.0" "pytest>=8.0.0" \
    "markdown-it-py>=3.0" "mdit-py-plugins>=0.4" \
    "numpy" "scipy" "sympy" "mpmath" \
    || { log "FATAL: pip install failed"; exit 1; }
  "$VENV/bin/python" -c "$DEPS" || { log "FATAL: venv still missing deps after install"; exit 1; }
fi

# the pharos package itself (editable install)
# Actors run from project subdirectories. Check imports from a neutral cwd.
if (cd / && "$VENV/bin/python" -c 'from pharos._mcp import FastMCP' 2>/dev/null); then
  log "pharos package present in venv"
else
  log "installing the pharos package (editable) into the venv"
  $NICE "$VENV/bin/pip" install --quiet --no-cache-dir -e "$PHAROS_ROOT" \
    || { log "FATAL: pip install -e failed (the pharos package)"; exit 1; }
  (cd / && "$VENV/bin/python" -c 'from pharos._mcp import FastMCP') \
    || { log "FATAL: pharos still not importable after editable install"; exit 1; }
fi

# codex CLI (npm @openai/codex)
CODEX_NPM="$RT/codex-npm"
CODEX_JS="$(find "$CODEX_NPM" -path '*/@openai/codex/bin/codex.js' 2>/dev/null | head -1 || true)"
CODEX_PACKAGE_JSON="$CODEX_NPM/lib/node_modules/@openai/codex/package.json"
CODEX_INSTALLED_VERSION=""
if [ -f "$CODEX_PACKAGE_JSON" ]; then
  CODEX_INSTALLED_VERSION="$("$NODE_DIR/bin/node" -p \
    'JSON.parse(require("fs").readFileSync(process.argv[1], "utf8")).version' \
    "$CODEX_PACKAGE_JSON" 2>/dev/null || true)"
fi
if [ -n "$CODEX_JS" ] && [ "$CODEX_INSTALLED_VERSION" = "$CODEX_NPM_VERSION" ]; then
  log "matching codex $CODEX_INSTALLED_VERSION present: $CODEX_JS"
else
  log "installing matching @openai/codex@$CODEX_NPM_VERSION -> $CODEX_NPM"
  mkdir -p "$CODEX_NPM"
  $NICE "$NODE_DIR/bin/npm" install -g --prefix "$CODEX_NPM" \
    "@openai/codex@$CODEX_NPM_VERSION" >/dev/null 2>&1 \
    || { log "FATAL: npm install @openai/codex failed"; exit 1; }
  CODEX_JS="$(find "$CODEX_NPM" -path '*/@openai/codex/bin/codex.js' 2>/dev/null | head -1 || true)"
  [ -n "$CODEX_JS" ] || { log "FATAL: codex.js not found after install"; exit 1; }
  CODEX_INSTALLED_VERSION="$("$NODE_DIR/bin/node" -p \
    'JSON.parse(require("fs").readFileSync(process.argv[1], "utf8")).version' \
    "$CODEX_PACKAGE_JSON")"
  [ "$CODEX_INSTALLED_VERSION" = "$CODEX_NPM_VERSION" ] \
    || { log "FATAL: installed npm Codex $CODEX_INSTALLED_VERSION, expected $CODEX_NPM_VERSION"; exit 1; }
fi

# the computation cgroup slice (collective 4-CPU/16G cap)
# Without the user slice, computation has per-job limits only.
SLICE_SRC="$PHAROS_ROOT/config/pharos-compute.slice"
SLICE_DST="$HOME/.config/systemd/user/pharos-compute.slice"
if command -v systemctl >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/systemd/user"
  cp "$SLICE_SRC" "$SLICE_DST"
  systemctl --user daemon-reload 2>/dev/null \
    && log "installed compute cap slice -> $SLICE_DST" \
    || log "WARN: systemd user session unavailable (compute falls back to rlimits)"
else
  log "WARN: no systemctl — pharos compute will use per-job rlimits only"
fi

# pharos on PATH for bare shells (human + agent convenience)
# Expose the CLI to shells that include ~/.local/bin on PATH.
LOCALBIN="$HOME/.local/bin"
mkdir -p "$LOCALBIN"
ln -sfn "$VENV/bin/pharos" "$LOCALBIN/pharos"
log "linked pharos -> $LOCALBIN/pharos"

# MathJax for pharos render (soft — CDN fallback at render time)
MJ="$RT/render/tex-svg.js"
if [ ! -s "$MJ" ]; then
  mkdir -p "$RT/render"
  curl -fsSL --max-time 60 "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js" \
    -o "$MJ" 2>/dev/null && log "vendored MathJax -> $MJ" \
    || log "WARN: MathJax download failed (pharos render will use the CDN)"
fi

# write runtime/runtime.env (machine paths for scripts/env.sh)
cat > "$RT/runtime.env" <<ENV
# Generated by bootstrap.sh; sourced by scripts/env.sh.
export PHAROS_NODE=$NODE_DIR/bin/node
export PHAROS_NODE_BIN=$NODE_DIR/bin
export PHAROS_CODEX_JS=$CODEX_JS
export PHAROS_CODEX_NPM_PREFIX=$CODEX_NPM
export PHAROS_VENV=$VENV
ENV
log "wrote $RT/runtime.env"

# codex backend = your BYO API key (config/pharos.env)
# Configure API authentication when endpoint and credentials are present.
. "$PHAROS_ROOT/scripts/env.sh" >/dev/null 2>&1 || true
PHAROS_SETUP_KEY="${OPENAI_API_KEY:-}"
if [ "${CODEX_API_PROVIDER:-openai-compatible}" = "azure" ]; then
  PHAROS_SETUP_KEY="${AZURE_OPENAI_API_KEY:-}"
fi
if [ "${CODEX_BACKEND:-api}" = "api" ] \
   && [ -n "$PHAROS_SETUP_KEY" ] && [ -n "${CODEX_API_BASE_URL:-}" ] \
   && case "$PHAROS_SETUP_KEY" in *"<"*|*"your"*) false;; *) true;; esac; then
  bash "$PHAROS_ROOT/scripts/setup-codex.sh" api 2>&1 | sed 's/^/[bootstrap] /' \
    || log "WARN: could not write the codex api provider config"
else
  log "codex api provider NOT written — fill config/pharos.env (cp config/pharos.env.example)"
  log "  with your BYO endpoint + key, then re-run bootstrap (or: scripts/setup-codex.sh api)"
fi

# system tools bootstrap cannot install (report, never install)
MISSING=""
command -v tmux >/dev/null 2>&1 || MISSING="$MISSING tmux"
{ command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1 \
  || command -v google-chrome >/dev/null 2>&1 || command -v google-chrome-stable >/dev/null 2>&1; } \
  || MISSING="$MISSING chromium"
{ command -v pdflatex >/dev/null 2>&1 || command -v tectonic >/dev/null 2>&1; } \
  || MISSING="$MISSING texlive(pdflatex)|tectonic"
if [ -n "$MISSING" ]; then
  log "MISSING system tools:$MISSING"
  log "  install them with the host's package manager (Debian/Ubuntu: tmux chromium texlive-latex-extra"
  log "  texlive-fonts-extra; Fedora: tmux chromium texlive-scheme-medium); pharos doctor FAILs until then"
else
  log "system tools present: tmux, chromium, TeX engine"
fi

log "done. Next:"
log "  1) cp config/pharos.env.example config/pharos.env   # fill your endpoint + key"
log "  2) pharos check-codex                              # confirm the backend is reachable"
log "  3) pharos doctor --probe                           # full health check: renders, compiles, queries"
