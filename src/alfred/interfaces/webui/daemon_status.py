"""Daemon status snapshot helpers for the Web UI."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

import alfred
from alfred.cron.daemon import DaemonManager
from alfred.cron.socket_protocol import SOCKET_NAME


class _SocketClientLike(Protocol):
    is_connected: bool


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _format_datetime(value: datetime | None) -> str | None:
    normalized = _normalize_datetime(value)
    if normalized is None:
        return None
    return normalized.isoformat().replace("+00:00", "Z")


def _get_daemon_manager(daemon_manager: DaemonManager | None = None) -> DaemonManager:
    return daemon_manager or DaemonManager()


def _get_socket_client(alfred_instance: object | None) -> object | None:
    if alfred_instance is None:
        return None
    socket_client = cast(object | None, getattr(alfred_instance, "socket_client", None))
    if socket_client is not None:
        return socket_client
    return cast(object | None, getattr(alfred_instance, "_socket_client", None))


def _get_socket_path(daemon_manager: DaemonManager, socket_client: object | None) -> Path:
    socket_path = getattr(socket_client, "socket_path", None)
    if isinstance(socket_path, Path):
        return socket_path
    if isinstance(socket_path, str):
        return Path(socket_path)
    return daemon_manager.pid_file.parent / SOCKET_NAME


def _socket_is_healthy(socket_client: object | None, socket_path: Path) -> bool:
    if socket_client is not None and hasattr(socket_client, "is_connected"):
        return bool(cast(_SocketClientLike, socket_client).is_connected)
    return socket_path.exists()


def _get_file_timestamp(path: Path) -> datetime | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def build_daemon_status_snapshot(
    alfred_instance: object | None = None,
    *,
    daemon_manager: DaemonManager | None = None,
    startup_error: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Build the nested daemon payload used by the Web UI."""
    manager = _get_daemon_manager(daemon_manager)
    current_time = _normalize_datetime(now) or datetime.now(UTC)
    socket_client = _get_socket_client(alfred_instance)
    socket_path = _get_socket_path(manager, socket_client)
    pid = manager.read_pid()
    pid_file = manager.pid_file

    socket_healthy = _socket_is_healthy(socket_client, socket_path)
    started_at = _get_file_timestamp(pid_file) if pid is not None else None
    if started_at is None and socket_path.exists():
        started_at = _get_file_timestamp(socket_path)
    heartbeat_at = _get_file_timestamp(socket_path) if socket_path.exists() else None

    if startup_error is not None:
        state = "failed"
    elif pid is not None:
        state = "running"
    elif socket_healthy:
        state = "starting"
    else:
        state = "stopped"

    uptime_seconds: int | None = None
    if started_at is not None:
        uptime_seconds = max(int((current_time - started_at).total_seconds()), 0)

    daemon_status = {
        "state": state,
        "pid": pid,
        "socketPath": str(socket_path),
        "socketHealthy": socket_healthy,
        "startedAt": _format_datetime(started_at),
        "uptimeSeconds": uptime_seconds,
        "lastHeartbeatAt": _format_datetime(heartbeat_at),
        "lastReloadAt": None,
        "lastError": startup_error,
    }

    return {"daemon": daemon_status}


def build_health_payload(
    alfred_instance: object | None = None,
    *,
    daemon_manager: DaemonManager | None = None,
    startup_error: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Build the HTTP health payload while preserving legacy fields."""
    snapshot = build_daemon_status_snapshot(
        alfred_instance,
        daemon_manager=daemon_manager,
        startup_error=startup_error,
        now=now,
    )
    daemon_status = snapshot["daemon"]
    assert isinstance(daemon_status, dict)

    return {
        "status": "ok",
        "version": alfred.__version__,
        "daemon": daemon_status,
        "daemonStatus": daemon_status.get("state"),
        "daemonPid": daemon_status.get("pid"),
    }
