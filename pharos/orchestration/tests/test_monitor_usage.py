"""Tests for cumulative token usage, monitor history, and run timestamps."""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

from pharos.execution import layout as L
from pharos.execution.scaffold import do_new
from pharos.orchestration import usage, workers
from pharos.orchestration.monitor import record, sample
from pharos.tests.util import env


@contextmanager
def _project_env(root: Path):
    with env(PHAROS_AGENTS_ROOT=str(root), PHAROS_VERIFY_URL=None, VERIFY_PORT=None):
        yield


def _write_session(codex_home: Path, totals):
    """Write session events containing cumulative token counts."""
    d = codex_home / "sessions" / "2026" / "09"
    d.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"type": "event_msg", "payload": {
        "type": "token_count", "info": {"total_token_usage": t}}}) for t in totals]
    (d / f"rollout-{len(list(d.iterdir()))}.jsonl").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


def _tok(i, c, o):
    return {"input_tokens": i, "cached_input_tokens": c, "output_tokens": o,
            "total_tokens": i + o}


def test_usage_last_cumulative_wins_and_groups_sum(tmp: Path):
    with _project_env(tmp):
        do_new("P", roles="xhigh:2")
        # two cumulative snapshots: only the LAST counts (it already includes the first)
        _write_session(L.main_codex_home("P"), [_tok(100, 0, 10), _tok(1000, 200, 50)])
        _write_session(L.WorkerLayout(L.worker_dir("P", "xhigh")).codex_home,
                       [_tok(500, 0, 20)])
        _write_session(L.verifier_codex_home("P"), [_tok(300, 100, 30)])
        u = usage.project_usage("P")
        assert u["tokens"]["main"]["input_tokens"] == 1000
        assert u["tokens"]["main"]["sessions"] == 1
        assert u["tokens"]["workers"]["input_tokens"] == 500
        assert u["tokens"]["total"]["input_tokens"] == 1800
        assert u["tokens"]["total"]["output_tokens"] == 100
        assert u["created_at"] is not None and u["age_days"] is not None
        assert u["cost_usd"] is None                    # no PHAROS_PRICE_* set
        os.environ["PHAROS_PRICE_OUTPUT"] = "10"         # $10 / 1M output tokens
        try:
            assert usage.project_usage("P")["cost_usd"] == pytest.approx(0.001)
        finally:
            os.environ.pop("PHAROS_PRICE_OUTPUT")


def test_monitor_records_history_and_usage_counts_deaths(tmp: Path):
    with _project_env(tmp):
        do_new("P", roles="xhigh:1")
        row = sample("P")
        assert row["workers"][0]["worker"] == "xhigh" and row["workers"][0]["alive"] is False
        assert set(row) >= {"ts", "main_up", "verify", "load1", "io60", "cpu60",
                            "io_read_mbps", "io_write_mbps",
                            "disk_free_gb", "api_errors"}
        assert row["api_errors"] == 0                   # fresh project, no logs yet
        # liveness history: alive -> dead is one death; dead -> dead is not
        path = L.project_dir("P") / "monitor.jsonl"
        for alive in (True, False, False):
            fake = dict(row, ts=int(time.time()),
                        workers=[dict(row["workers"][0], alive=alive)])
            path.open("a").write(json.dumps(fake) + "\n")
        record("P")                                     # a real appended sample
        m = usage.project_usage("P")["monitor"]
        assert m["samples"] == 4
        assert m["worker_deaths"] == {"xhigh": 1}
        assert m["load1_max"] is not None               # peaks survive into the summary
        assert "io60_max" in m and "api_errors" in m


def test_start_records_timestamp(tmp: Path, monkeypatch):
    monkeypatch.setattr(workers, "spawn_loop", lambda _: os.getpid())
    with _project_env(tmp):
        do_new("P", roles="xhigh:1")
        from pharos.orchestration import cli
        meta = json.loads((L.project_dir("P") / "project.json").read_text())
        assert isinstance(meta["created_at"], int)
        assert "last_started_at" not in meta
        cli.do_start("P", stagger=0)
        meta = json.loads((L.project_dir("P") / "project.json").read_text())
        assert isinstance(meta["last_started_at"], int)
