#!/usr/bin/env python3
"""Atomically publish one completed checkpoint draft without overwrite."""

from __future__ import annotations

import argparse
import os
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


HEADER_DRAFT = "Timestamp: DRAFT"
INPUT_FORMAT = "%Y-%m-%dT%H:%MZ"


def _fail(message: str) -> int:
    print(f"publish_checkpoint: {message}", file=sys.stderr)
    return 1


def _fsync_dir(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _publication_time(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(second=0, microsecond=0)
    try:
        return datetime.strptime(value, INPUT_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"--at must use YYYY-MM-DDTHH:MMZ: {value!r}") from exc


def _rewrite_timestamp(draft: Path, expected: str) -> None:
    text = draft.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines) if line.startswith("Timestamp:")]
    if len(indices) != 1:
        raise ValueError("draft must contain exactly one Timestamp: line")

    index = indices[0]
    current = lines[index].rstrip("\r\n ")
    if current not in (HEADER_DRAFT, expected):
        raise ValueError(
            f"timestamp line must be {HEADER_DRAFT!r} or {expected!r}, got {current!r}"
        )
    ending = "\r\n" if lines[index].endswith("\r\n") else "\n"
    lines[index] = expected + ending

    fd, temporary = tempfile.mkstemp(prefix=".publish-", dir=draft.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.writelines(lines)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, draft)
        _fsync_dir(draft.parent)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish a completed .checkpoint-drafts file atomically."
    )
    parser.add_argument("draft", type=Path)
    parser.add_argument(
        "--at", metavar="YYYY-MM-DDTHH:MMZ",
        help="fixed UTC publication minute (primarily for deterministic recovery/tests)",
    )
    args = parser.parse_args(argv)

    project = Path.cwd().resolve()
    if not (project / "project.json").is_file():
        return _fail("run from a project root containing project.json")

    draft_root = (project / ".checkpoint-drafts").resolve()
    draft = project / args.draft
    try:
        draft_stat = draft.lstat()
    except OSError as exc:
        return _fail(f"cannot read draft: {exc}")
    if not stat.S_ISREG(draft_stat.st_mode):
        return _fail("draft must be a regular, non-symlink file")
    draft = draft.resolve()
    try:
        draft.relative_to(draft_root)
    except ValueError:
        return _fail(f"draft must be inside {draft_root}")

    try:
        published_at = _publication_time(args.at)
    except ValueError as exc:
        return _fail(str(exc))
    header = f"Timestamp: {published_at:%Y-%m-%d %H:%M} UTC"
    filename = f"{project.name}_{published_at:%y%m%d%H%M}.md"
    checkpoints = project / "checkpoints"
    checkpoints.mkdir(exist_ok=True)
    destination = checkpoints / filename
    if os.path.lexists(destination):
        return _fail(f"refusing to overwrite existing checkpoint: {destination}")
    if draft.stat().st_dev != checkpoints.stat().st_dev:
        return _fail("draft and checkpoints directory must be on the same filesystem")

    try:
        _rewrite_timestamp(draft, header)
    except (OSError, UnicodeError, ValueError) as exc:
        return _fail(str(exc))

    original_mode = stat.S_IMODE(draft.stat().st_mode)
    os.chmod(draft, 0o444)
    try:
        # link(2) creates the complete destination atomically and never clobbers.
        os.link(draft, destination, follow_symlinks=False)
    except OSError as exc:
        os.chmod(draft, original_mode)
        return _fail(f"atomic publish failed: {exc}")

    _fsync_dir(checkpoints)
    draft.unlink()
    _fsync_dir(draft_root)
    print(destination.relative_to(project))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
