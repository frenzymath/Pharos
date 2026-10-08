"""Backend setup against an isolated configuration and a stub login command."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("provider", ["openai-compatible", "azure"])
def test_api_setup_and_subscription_switch(tmp_path, provider):
    root = Path(__file__).resolve().parents[2]
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("setup-codex.sh", "env.sh"):
        shutil.copyfile(root / "scripts" / name, scripts / name)
    shared = tmp_path / "shared"
    login = tmp_path / "login-stub"
    login.write_text(
        '#!/bin/sh\n'
        'printf "%s\\n" "$*" > "$CODEX_HOME/login-command"\n'
        'if [ "$2" = "--with-api-key" ]; then\n'
        '  cat > "$CODEX_HOME/login-input"\n'
        'fi\n'
    )
    login.chmod(0o755)
    settings = {k: v for k, v in os.environ.items()
                if not k.startswith(("PHAROS_", "CODEX_", "OPENAI_", "AZURE_"))}
    settings.update(
        PHAROS_CODEX_SHARED_HOME=str(shared),
        PHAROS_CODEX_BIN=str(login),
        CODEX_API_BASE_URL="https://example.invalid/api",
        CODEX_API_PROVIDER=provider,
        CODEX_API_VERSION="test-version",
        PHAROS_CODEX_MODEL="test-model",
        PHAROS_CODEX_EFFORT="high",
    )
    settings["AZURE_OPENAI_API_KEY" if provider == "azure" else "OPENAI_API_KEY"] = "test-key"

    def setup(mode):
        subprocess.run(["bash", str(scripts / "setup-codex.sh"), mode],
                       cwd=tmp_path, env=settings, check=True, capture_output=True, text=True)
        text = (shared / "config.toml").read_text()
        assert 'project_root_markers = ["AGENTS.md"]' in text
        assert 'goals = true' in text
        assert 'model = "test-model"' in text
        assert 'model_reasoning_effort = "high"' in text
        assert "test-key" not in text
        assert (shared / "config.toml").stat().st_mode & 0o777 == 0o600
        return text

    config = setup("api")
    assert 'model_provider = "OpenAI"' in config
    if provider == "azure":
        assert 'env_http_headers = { "api-key" = "AZURE_OPENAI_API_KEY" }' in config
        assert 'query_params = { api-version = "test-version" }' in config
        assert not (shared / "login-command").exists()
    else:
        assert 'requires_openai_auth = true' in config
        assert (shared / "login-command").read_text().strip() == "login --with-api-key"
        assert (shared / "login-input").read_text() == "test-key"
    config = setup("login")
    assert "model_provider" not in config
    assert (shared / "login-command").read_text().strip() == "login --device-auth"
