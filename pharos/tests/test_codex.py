"""Launcher resolution, subprocess environment, and session-home tests."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from pharos import codex
from pharos.tests.util import env

_ALL = dict(PHAROS_CODEX_BIN=None,
            PHAROS_CODEX_MODEL=None, PHAROS_CODEX_EFFORT=None,
            PHAROS_VERIFY_MODEL=None, PHAROS_VERIFY_EFFORT=None)


def test_resolve_bin_precedence(tmp: Path, monkeypatch):
    monkeypatch.setattr(codex.shutil, "which", lambda _: "/x/on-path")
    with env(**{**_ALL, "PHAROS_CODEX_BIN": "/x/primary"}):
        assert codex.resolve_bin() == "/x/primary"
    with env(**_ALL):
        assert codex.resolve_bin() == "/x/on-path"
        monkeypatch.setattr(codex.shutil, "which", lambda _: None)
        monkeypatch.setattr(codex.sys, "executable", str(tmp / "python"))
        assert codex.resolve_bin() == "codex"
        sibling = tmp / "codex"
        sibling.write_text("#!/bin/sh\n", encoding="utf-8")
        sibling.chmod(0o755)
        assert codex.resolve_bin() == str(sibling)


def test_npm_prefix_follows_pinned_codex_install(tmp: Path):
    entry = tmp / "codex-npm" / "lib" / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    entry.parent.mkdir(parents=True)
    entry.write_text("", encoding="utf-8")
    assert codex.npm_prefix(str(entry)) == str(tmp / "codex-npm")
    assert codex.npm_prefix(str(tmp / "other" / "codex.js")) is None


def test_model_and_effort_precedence():
    with env(**{**_ALL, "PHAROS_VERIFY_MODEL": "override", "PHAROS_CODEX_MODEL": "neutral"}):
        assert codex.model("PHAROS_VERIFY_MODEL") == "override"
    with env(**{**_ALL, "PHAROS_CODEX_MODEL": "neutral", "PHAROS_CODEX_EFFORT": "e"}):
        assert codex.model("PHAROS_VERIFY_MODEL") == "neutral"
        assert codex.effort("PHAROS_VERIFY_EFFORT") == "e"
    with env(**_ALL):
        assert codex.model("PHAROS_VERIFY_MODEL") == codex.DEFAULT_MODEL == "gpt-6-astra"
        assert codex.effort("PHAROS_VERIFY_EFFORT") == codex.DEFAULT_EFFORT == "max"
    with env(**{**_ALL, "PHAROS_VERIFY_MODEL": "primary", "PHAROS_OTHER_MODEL": "other"}):
        assert codex.model("PHAROS_VERIFY_MODEL", "PHAROS_OTHER_MODEL") == "primary"


def test_subprocess_env_pins_the_projects_root():
    """A child codex session inherits PHAROS_AGENTS_ROOT even when the launching
    shell never sourced env.sh, so `pharos usage` works from a side actor's home."""
    from pharos.execution import layout as L
    with env(PHAROS_AGENTS_ROOT=None, PHAROS_RUNTIME=None):
        assert codex.subprocess_env("codex")["PHAROS_AGENTS_ROOT"] == str(L.agents_root())
    with env(PHAROS_AGENTS_ROOT="/srv/projects"):
        assert codex.subprocess_env("codex")["PHAROS_AGENTS_ROOT"] == "/srv/projects"


def test_subprocess_env_path_and_codex_home():
    with env(**{**_ALL, "PATH": "/usr/bin:/bin"}):
        # a concrete binary path gets its dir prepended (for the node shebang) —
        # idempotently; the bare fallback never injects the CWD
        assert codex.subprocess_env("/opt/cx/codex")["PATH"].startswith("/opt/cx")
        with env(PATH="/opt/cx:/usr/bin"):
            assert codex.subprocess_env("/opt/cx/codex")["PATH"] == "/opt/cx:/usr/bin"
        bare = codex.subprocess_env("codex")
        assert bare["PATH"] == "/usr/bin:/bin"
        assert "" not in bare["PATH"].split(os.pathsep)
        # codex_home= pins the child's session store; omitted -> untouched
        assert codex.subprocess_env("codex", codex_home="/w/.codex-home")["CODEX_HOME"] \
            == "/w/.codex-home"
        assert codex.subprocess_env("codex").get("CODEX_HOME") == os.environ.get("CODEX_HOME")


def test_exec_cmd_shape():
    assert codex.exec_cmd("/x/codex", "m", "max", "-C", "/home", "-") == [
        "/x/codex", "exec", "--model", "m",
        "--config", 'model_reasoning_effort="max"', "-C", "/home", "-"]
    assert codex.exec_cmd("codex", "m", "e") == [
        "codex", "exec", "--model", "m", "--config", 'model_reasoning_effort="e"']


def test_shared_codex_home_resolution():
    with env(PHAROS_CODEX_SHARED_HOME="/x/shared", PHAROS_RUNTIME=None):
        assert codex.shared_codex_home() == Path("/x/shared")
    with env(PHAROS_CODEX_SHARED_HOME=None, PHAROS_RUNTIME="/x/rt"):
        assert codex.shared_codex_home() == Path("/x/rt/codex-home")


def test_human_root_uses_shared_home_instead_of_stale_pharos_home(tmp: Path):
    shared = tmp / "shared"
    agents = tmp / "projects"
    assert codex._human_codex_home(
        codex._REPO_ROOT, shared,
        {"CODEX_HOME": str(agents / "demo" / ".codex-home"),
         "PHAROS_AGENTS_ROOT": str(agents)},
    ) == shared
    assert codex._human_codex_home(
        codex._REPO_ROOT, shared,
        {"CODEX_HOME": str(shared.parent / "projects" / "demo" / ".codex-home")},
    ) == shared
    assert codex._human_codex_home(
        codex._REPO_ROOT, shared,
        {"CODEX_HOME": str(Path.home() / ".codex")},
    ) == shared
    custom = tmp / "custom"
    assert codex._human_codex_home(
        codex._REPO_ROOT, shared, {"CODEX_HOME": str(custom)},
    ) is None


def test_provision_codex_home(tmp: Path):
    shared = tmp / "shared"
    shared.mkdir()
    (shared / "config.toml").write_text("model = 'm'\n")
    (shared / "auth.json").write_text("{}")
    with env(PHAROS_CODEX_SHARED_HOME=str(shared)):
        home = codex.provision_codex_home(tmp / "agent" / ".codex-home")
        assert (home / "config.toml").is_symlink()
        assert (home / "config.toml").resolve() == (shared / "config.toml").resolve()
        assert (home / "auth.json").resolve() == (shared / "auth.json").resolve()
        codex.provision_codex_home(home)                     # idempotent
        codex.provision_codex_home(shared)                   # never self-links
        assert (shared / "config.toml").is_file() and not (shared / "config.toml").is_symlink()


def test_provision_codex_home_skips_missing_shared_files(tmp: Path):
    with env(PHAROS_CODEX_SHARED_HOME=str(tmp / "nowhere")):
        home = codex.provision_codex_home(tmp / "a" / ".codex-home")
        assert home.is_dir() and not (home / "config.toml").exists()


def test_last_activity_reads_the_newest_session_write(tmp: Path):
    assert codex.last_activity(tmp / "nowhere") is None
    home = tmp / ".codex-home"
    old = home / "sessions" / "2026" / "09" / "01"
    new = home / "sessions" / "2026" / "09" / "03"
    old.mkdir(parents=True); new.mkdir(parents=True)
    (old / "rollout-a.jsonl").write_text("x"); (new / "rollout-b.jsonl").write_text("y")
    os.utime(old / "rollout-a.jsonl", (1_700_000_000, 1_700_000_000))
    os.utime(new / "rollout-b.jsonl", (1_800_000_000, 1_800_000_000))
    assert codex.last_activity(home) == 1_800_000_000
    (home / "history.jsonl").write_text("h")
    os.utime(home / "history.jsonl", (1_900_000_000, 1_900_000_000))
    assert codex.last_activity(home) == 1_900_000_000


def test_low_priority_prefixes_when_available():
    out = codex.low_priority(["codex", "exec"])
    assert out[-2:] == ["codex", "exec"]
    if shutil.which("ionice"):
        assert out[:5] == ["ionice", "-c", "2", "-n", "7"]
