"""Web UI daemon bootstrap helper."""

from __future__ import annotations

from dataclasses import dataclass

from alfred.cli.cron import is_daemon_running, start_daemon_if_needed


@dataclass(frozen=True, slots=True)
class DaemonBootstrapResult:
    """Result of a Web UI daemon bootstrap attempt."""

    daemon_was_running: bool
    daemon_started: bool
    startup_error: str | None = None

    @property
    def success(self) -> bool:
        """Return True when the daemon is ready for the Web UI."""
        return self.startup_error is None


def bootstrap_daemon() -> DaemonBootstrapResult:
    """Ensure the cron daemon is running for the Web UI.

    This helper is intentionally small: it checks whether the daemon is already
    running, then reuses the existing cron bootstrap logic if not. The helper
    does not raise on expected startup failures so the Web UI can stay usable
    and surface the failure through status UI instead.
    """

    try:
        daemon_was_running = is_daemon_running()
    except Exception as exc:  # pragma: no cover - defensive boundary
        return DaemonBootstrapResult(
            daemon_was_running=False,
            daemon_started=False,
            startup_error=f"Failed to check daemon status: {exc}",
        )

    if daemon_was_running:
        return DaemonBootstrapResult(
            daemon_was_running=True,
            daemon_started=False,
        )

    try:
        daemon_started = start_daemon_if_needed()
    except Exception as exc:  # pragma: no cover - defensive boundary
        return DaemonBootstrapResult(
            daemon_was_running=False,
            daemon_started=False,
            startup_error=f"Failed to start daemon: {exc}",
        )

    if daemon_started:
        return DaemonBootstrapResult(
            daemon_was_running=False,
            daemon_started=True,
        )

    return DaemonBootstrapResult(
        daemon_was_running=False,
        daemon_started=False,
        startup_error="Failed to start daemon",
    )
