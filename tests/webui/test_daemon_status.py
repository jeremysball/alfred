from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alfred.interfaces.webui.daemon_status import build_daemon_status_snapshot
from tests.webui.fakes import FakeAlfred


class FakeDaemonManager:
    def __init__(self, pid_file: Path, pid: int | None) -> None:
        self.pid_file = pid_file
        self._pid = pid

    def read_pid(self) -> int | None:
        return self._pid


def _touch(path: Path, timestamp: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("test")
    epoch = timestamp.timestamp()
    os.utime(path, (epoch, epoch))


def test_build_daemon_status_reports_running_daemon_and_socket_health(tmp_path: Path) -> None:
    started_at = datetime(2026, 3, 21, 12, 0, tzinfo=UTC)
    now = started_at + timedelta(seconds=183)
    pid_file = tmp_path / "cron-runner.pid"
    socket_path = tmp_path / "notify.sock"
    _touch(pid_file, started_at)
    _touch(socket_path, started_at)

    fake_alfred = FakeAlfred()
    fake_alfred.socket_client.socket_path = socket_path
    fake_alfred.socket_client.is_connected = True

    snapshot = build_daemon_status_snapshot(
        alfred_instance=fake_alfred,
        daemon_manager=FakeDaemonManager(pid_file, 12345),
        now=now,
    )

    assert snapshot["daemon"] == {
        "state": "running",
        "pid": 12345,
        "socketPath": str(socket_path),
        "socketHealthy": True,
        "startedAt": "2026-03-21T12:00:00Z",
        "uptimeSeconds": 183,
        "lastHeartbeatAt": "2026-03-21T12:00:00Z",
        "lastReloadAt": None,
        "lastError": None,
    }


def test_build_daemon_status_handles_stopped_daemon(tmp_path: Path) -> None:
    pid_file = tmp_path / "cron-runner.pid"
    fake_alfred = FakeAlfred()
    fake_alfred.socket_client.socket_path = tmp_path / "notify.sock"
    fake_alfred.socket_client.is_connected = False

    snapshot = build_daemon_status_snapshot(
        alfred_instance=fake_alfred,
        daemon_manager=FakeDaemonManager(pid_file, None),
        now=datetime(2026, 3, 21, 12, 0, tzinfo=UTC),
    )

    assert snapshot["daemon"] == {
        "state": "stopped",
        "pid": None,
        "socketPath": str(tmp_path / "notify.sock"),
        "socketHealthy": False,
        "startedAt": None,
        "uptimeSeconds": None,
        "lastHeartbeatAt": None,
        "lastReloadAt": None,
        "lastError": None,
    }


def test_build_daemon_status_marks_failed_daemon_with_last_error(tmp_path: Path) -> None:
    pid_file = tmp_path / "cron-runner.pid"

    snapshot = build_daemon_status_snapshot(
        alfred_instance=None,
        daemon_manager=FakeDaemonManager(pid_file, None),
        startup_error="daemon failed to start",
        now=datetime(2026, 3, 21, 12, 0, tzinfo=UTC),
    )

    assert snapshot["daemon"]["state"] == "failed"
    assert snapshot["daemon"]["pid"] is None
    assert snapshot["daemon"]["lastError"] == "daemon failed to start"
