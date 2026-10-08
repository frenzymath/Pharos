"""Behavioral tests for write-once checkpoint publication."""

from __future__ import annotations

import stat
import subprocess
import sys
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "agents/skills/main/operation/checkpoint/scripts/publish_checkpoint.py"
)
AT = "2026-09-05T07:08Z"


def _project(tmp: Path) -> tuple[Path, Path]:
    project = tmp / "demo"
    drafts = project / ".checkpoint-drafts"
    drafts.mkdir(parents=True)
    (project / "project.json").write_text("{}\n", encoding="utf-8")
    draft = drafts / "current.md"
    return project, draft


def _run(project: Path, draft: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(draft), "--at", AT],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )


def test_publish_is_atomic_timestamped_and_read_only(tmp: Path):
    project, draft = _project(tmp)
    draft.write_text(
        "# Checkpoint - project demo\n\nTimestamp: DRAFT\n\ncomplete body\n",
        encoding="utf-8",
    )

    result = _run(project, draft)

    destination = project / "checkpoints" / "demo_2609050708.md"
    assert result.returncode == 0
    assert result.stdout.strip() == "checkpoints/demo_2609050708.md"
    assert not draft.exists()
    assert destination.read_text(encoding="utf-8") == (
        "# Checkpoint - project demo\n\n"
        "Timestamp: 2026-09-05 07:08 UTC\n\ncomplete body\n"
    )
    assert stat.S_IMODE(destination.stat().st_mode) == 0o444


def test_publish_refuses_to_overwrite_existing_checkpoint(tmp: Path):
    project, draft = _project(tmp)
    draft.write_text("Timestamp: DRAFT\n\nfirst\n", encoding="utf-8")
    assert _run(project, draft).returncode == 0
    destination = project / "checkpoints" / "demo_2609050708.md"
    original = destination.read_bytes()

    draft.write_text("Timestamp: DRAFT\n\nsecond\n", encoding="utf-8")
    result = _run(project, draft)

    assert result.returncode == 1
    assert "refusing to overwrite" in result.stderr
    assert destination.read_bytes() == original
    assert draft.exists()


def test_publish_rejects_symlink_without_changing_draft(tmp: Path):
    project, draft = _project(tmp)
    original = "Timestamp: DRAFT\n\nkeep this draft\n"
    draft.write_text(original, encoding="utf-8")
    link = draft.with_name("linked.md")
    link.symlink_to(draft.name)

    result = _run(project, link)

    assert result.returncode == 1
    assert "non-symlink" in result.stderr
    assert draft.read_text(encoding="utf-8") == original
    assert link.is_symlink() and link.exists()
    assert not (project / "checkpoints").exists()


def test_publish_rejects_draft_outside_staging_directory(tmp: Path):
    project, _ = _project(tmp)
    outside = project / "notes.md"
    original = "Timestamp: DRAFT\n\nresearch notes\n"
    outside.write_text(original, encoding="utf-8")

    result = _run(project, outside)

    assert result.returncode == 1
    assert "must be inside" in result.stderr
    assert outside.read_text(encoding="utf-8") == original
    assert not (project / "checkpoints").exists()
