"""Tests for Web UI daemon bootstrap helper."""

from __future__ import annotations

import alfred.interfaces.webui.daemon_bootstrap as daemon_bootstrap
from alfred.interfaces.webui.daemon_bootstrap import DaemonBootstrapResult


def test_bootstrap_daemon_starts_when_daemon_is_missing(monkeypatch) -> None:
    """The helper should start the daemon when nothing is running."""

    calls = {"checked": 0, "started": 0}

    def fake_is_daemon_running() -> bool:
        calls["checked"] += 1
        return False

    def fake_start_daemon_if_needed() -> bool:
        calls["started"] += 1
        return True

    monkeypatch.setattr(daemon_bootstrap, "is_daemon_running", fake_is_daemon_running)
    monkeypatch.setattr(daemon_bootstrap, "start_daemon_if_needed", fake_start_daemon_if_needed)

    result = daemon_bootstrap.bootstrap_daemon()

    assert result == DaemonBootstrapResult(
        daemon_was_running=False,
        daemon_started=True,
        startup_error=None,
    )
    assert result.success is True
    assert calls == {"checked": 1, "started": 1}


def test_bootstrap_daemon_noops_when_daemon_is_already_running(monkeypatch) -> None:
    """The helper should be a no-op when the daemon is already running."""

    calls = {"checked": 0, "started": 0}

    def fake_is_daemon_running() -> bool:
        calls["checked"] += 1
        return True

    def fake_start_daemon_if_needed() -> bool:
        calls["started"] += 1
        return True

    monkeypatch.setattr(daemon_bootstrap, "is_daemon_running", fake_is_daemon_running)
    monkeypatch.setattr(daemon_bootstrap, "start_daemon_if_needed", fake_start_daemon_if_needed)

    result = daemon_bootstrap.bootstrap_daemon()

    assert result == DaemonBootstrapResult(
        daemon_was_running=True,
        daemon_started=False,
        startup_error=None,
    )
    assert result.success is True
    assert calls == {"checked": 1, "started": 0}


def test_bootstrap_daemon_reports_failure_when_startup_fails(monkeypatch) -> None:
    """The helper should surface startup failure without raising."""

    calls = {"checked": 0, "started": 0}

    def fake_is_daemon_running() -> bool:
        calls["checked"] += 1
        return False

    def fake_start_daemon_if_needed() -> bool:
        calls["started"] += 1
        return False

    monkeypatch.setattr(daemon_bootstrap, "is_daemon_running", fake_is_daemon_running)
    monkeypatch.setattr(daemon_bootstrap, "start_daemon_if_needed", fake_start_daemon_if_needed)

    result = daemon_bootstrap.bootstrap_daemon()

    assert result == DaemonBootstrapResult(
        daemon_was_running=False,
        daemon_started=False,
        startup_error="Failed to start daemon",
    )
    assert result.success is False
    assert calls == {"checked": 1, "started": 1}
