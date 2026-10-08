"""Launch a fresh Codex session for each proof verification.

The verifier reads its contract and skills, then writes ``verification.json``
in the run directory. Prompts are sent on stdin to avoid argument size limits.
The injected gateway exposes verifier-role tools. ``pharos.codex`` resolves
the command, model, and effort settings at call time.

Config (env):
  PHAROS_CODEX_BIN,
  PHAROS_VERIFY_MODEL (default gpt-6-astra),
  PHAROS_VERIFY_EFFORT (default max),
  CODEX_TIMEOUT_SECONDS (0 = no timeout),
  VERIFY_AGENT_HOME    the codex `-C` dir — in production <project>/verifier/,
                       holding the contract + skills symlinks and .codex-home,
  VERIFIER_RESULTS_DIR the per-call run dirs — in production <project>/verifier/runs/.
Both are set by `pharos verify up <project>`; the defaults below are a fallback
for direct library use and tests.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from pharos import codex

_HERE = Path(__file__).resolve().parent  # pharos/verify/
_REPO_ROOT = _HERE.parent.parent         # repo root (pharos/verify -> pharos -> root)
VERIFICATION_FILENAME = "verification.json"


def _agent_home() -> Path:
    return Path(os.getenv("VERIFY_AGENT_HOME", str(_HERE / "agent"))).resolve()


def ensure_agent_home() -> Path:
    """Provision the verifier contract and skills for direct library use.

    ``pharos new`` normally creates this home. If source assets are missing,
    return the configured path without creating broken links.
    """
    home = _agent_home()
    contract = _REPO_ROOT / "agents" / "contracts" / "verifier.md"
    skills = _REPO_ROOT / "agents" / "skills" / "verify"
    agents_md = home / "AGENTS.md"
    skills_link = home / ".agents" / "skills"
    if agents_md.exists() and skills_link.exists():
        return home
    if not (contract.exists() and skills.exists()):
        return home  # nothing to link from — do not create broken links
    home.mkdir(parents=True, exist_ok=True)
    (home / ".agents").mkdir(parents=True, exist_ok=True)
    for link, target in ((agents_md, contract), (skills_link, skills)):
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target)
    return home


def _results_root() -> Path:
    return Path(os.getenv("VERIFIER_RESULTS_DIR", str(_HERE / "runs"))).resolve()


def _model() -> str:
    return codex.model("PHAROS_VERIFY_MODEL")


def _effort() -> str:
    return codex.effort("PHAROS_VERIFY_EFFORT")


def _timeout() -> Optional[int]:
    return int(os.getenv("CODEX_TIMEOUT_SECONDS", "0")) or None


def _mcp_config_arg() -> str:
    """Inject the pharos gateway (role=verifier) into the codex agent via `-c`,
    independent of CODEX_HOME. Runs the installed package (``python3 -m
    pharos.gateway``); the verifier role exposes only search_arxiv_theorems."""
    return 'mcp_servers.pharos={command="python3",args=["-m","pharos.gateway"],env={PHAROS_ROLE="verifier"}}'


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def generate_run_id(statement: str) -> str:
    return f"{_utc_timestamp()}_{hashlib.sha256(statement.encode('utf-8')).hexdigest()[:12]}"


def _allocate_run_id(statement: str) -> str:
    """Claim a unique run dir atomically (mkdir exist_ok=False, retry with a
    numeric suffix) so concurrent verifiers sharing RESULTS_ROOT never clobber."""
    root = _results_root()
    root.mkdir(parents=True, exist_ok=True)
    base = generate_run_id(statement)
    run_id, suffix = base, 1
    for _ in range(10000):
        try:
            (root / run_id).mkdir(parents=False, exist_ok=False)
            return run_id
        except FileExistsError:
            suffix += 1
            run_id = f"{base}_{suffix}"
    raise RuntimeError(f"could not allocate a unique run_id under {root} for base={base}")


def _results_dir(run_id: str) -> Path:
    return _results_root() / run_id


def _verification_path(run_id: str) -> Optional[Path]:
    path = _results_dir(run_id) / VERIFICATION_FILENAME
    return path if path.exists() else None


def build_prompt(run_id: str, statement: str, proof: str) -> str:
    output_path = _results_dir(run_id) / VERIFICATION_FILENAME
    return (
        f"Run_id: {run_id}. "
        f"Statement: {statement}. "
        f"Proof:\n{proof}\n\n"
        "Use AGENTS.md to verify the above proof for the statement. "
        f"Write the verification JSON to this exact path: {output_path}."
    )


def build_codex_command() -> List[str]:
    return codex.exec_cmd(
        codex.resolve_bin(), _model(), _effort(),
        "-C", str(_agent_home()),
        # Support source archives without a .git directory.
        "--skip-git-repo-check",
        "-c", _mcp_config_arg(),
        "--dangerously-bypass-approvals-and-sandbox",
        "-",  # read the potentially large prompt from stdin
    )


def run_codex_verification(run_id: str, statement: str, proof: str) -> Dict[str, Any]:
    """Spawn the cold-start codex verifier; read back + return the verification
    JSON. Raises HTTPException 504 (timeout) / 500 (nonzero exit, no output, or
    bad/non-dict JSON) — the callers translate these into the fact_submit
    verify-error path."""
    results_dir = _results_dir(run_id)
    results_dir.mkdir(parents=True, exist_ok=True)
    log_path = results_dir / "log.md"
    ensure_agent_home()  # provision the codex -C home on a fresh checkout (idempotent)
    cmd = build_codex_command()
    prompt = build_prompt(run_id=run_id, statement=statement, proof=proof)
    env = codex.subprocess_env(cmd[0])

    started_at = datetime.now(timezone.utc).isoformat()
    try:
        with log_path.open("w", encoding="utf-8") as log_handle:
            log_handle.write(f"started_at_utc: {started_at}\n")
            log_handle.write(f"command: {shlex.join(cmd)}\n\n")
            log_handle.flush()
            completed = subprocess.run(
                cmd, cwd=_agent_home(), env=env,
                input=prompt, stdout=log_handle, stderr=subprocess.STDOUT,
                text=True, timeout=_timeout(), check=False,
            )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504,
                            detail=f"codex exec timed out after {exc.timeout}s. See log at {log_path}") from exc

    if completed.returncode != 0:
        raise HTTPException(status_code=500,
                            detail=f"codex exec failed with exit code {completed.returncode}. See log at {log_path}")

    verification_path = _verification_path(run_id)
    if verification_path is None:
        expected = results_dir / VERIFICATION_FILENAME
        raise HTTPException(status_code=500,
                            detail=f"verification output was not found at {expected}. See log at {log_path}")
    try:
        payload = json.loads(verification_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500,
                            detail=f"verification output at {verification_path} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500,
                            detail=f"verification output at {verification_path} must be a JSON object")
    return payload
