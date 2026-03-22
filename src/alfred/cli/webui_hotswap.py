"""WebUI server startup and hotswap supervision."""

from __future__ import annotations

import asyncio
import threading
import time
import webbrowser
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Protocol, cast

from alfred.interfaces.webui.daemon_bootstrap import bootstrap_daemon

DEFAULT_WEBUI_STATIC_ROOT = Path(__file__).resolve().parents[1] / "interfaces" / "webui" / "static"
WEBUI_HOTSWAP_EXTENSIONS = {".css", ".html", ".js"}
WEBUI_HOTSWAP_DEBOUNCE_MS = 250
WEBUI_STARTUP_TIMEOUT_SECONDS = 15.0
WEBUI_BROWSER_OPEN_DELAY_SECONDS = 1.0


class _ServerController(Protocol):
    """Minimal lifecycle contract for a WebUI server controller."""

    @property
    def started(self) -> bool:
        """Whether the server has fully started."""

    @property
    def alive(self) -> bool:
        """Whether the server thread is still running."""

    def start(self) -> None:
        """Start the server."""

    def stop(self) -> None:
        """Request server shutdown."""

    def join(self) -> None:
        """Wait for server shutdown."""


class _UvicornServerController:
    """Thin wrapper around a Uvicorn server running in a background thread."""

    def __init__(self, server: Any) -> None:
        self._server = server
        self._thread = threading.Thread(target=server.run, daemon=True)

    @property
    def started(self) -> bool:
        return bool(getattr(self._server, "started", False))

    @property
    def alive(self) -> bool:
        return self._thread.is_alive()

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.should_exit = True

    def join(self) -> None:
        self._thread.join()


def _wait_for_started(controller: _ServerController, timeout: float = WEBUI_STARTUP_TIMEOUT_SECONDS) -> None:
    """Wait for a server controller to report that it has started."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if controller.started:
            return
        if not controller.alive:
            raise RuntimeError("Web UI server exited before startup completed")
        time.sleep(0.05)
    raise TimeoutError("Web UI server did not start in time")


def _open_browser_delayed(host: str, port: int) -> None:
    """Open the Web UI in a browser after a short delay."""

    def _open() -> None:
        time.sleep(WEBUI_BROWSER_OPEN_DELAY_SECONDS)
        webbrowser.open(f"http://{host}:{port}")

    threading.Thread(target=_open, daemon=True).start()


def _is_relevant_webui_asset(path: object) -> bool:
    """Return True when a watched file should trigger a restart."""
    return Path(str(path)).suffix.lower() in WEBUI_HOTSWAP_EXTENSIONS


def _has_relevant_webui_change(changes: Iterable[tuple[object, str]]) -> bool:
    """Return True if a batch of file changes includes a WebUI asset."""
    return any(_is_relevant_webui_asset(path) for _change, path in changes)


def _build_server_controller(host: str, port: int, debug: bool) -> _ServerController:
    """Create a new Uvicorn-backed WebUI server controller."""
    import uvicorn

    from alfred.alfred import Alfred
    from alfred.config import load_config
    from alfred.data_manager import init_xdg_directories
    from alfred.interfaces.webui.server import create_app

    init_xdg_directories()
    config = load_config()
    alfred = Alfred(config, telegram_mode=False)
    bootstrap_result = bootstrap_daemon()

    async def _start_alfred() -> None:
        await alfred.start()

    asyncio.run(_start_alfred())

    app = create_app(alfred_instance=cast(Any, alfred), debug=debug)
    app.state.webui_bootstrap_result = bootstrap_result

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="debug" if debug else "info",
        )
    )
    return _UvicornServerController(server)


def run_webui_server(*, host: str, port: int, open_browser: bool, debug: bool) -> None:
    """Run the Web UI server once until it exits."""
    controller = _build_server_controller(host=host, port=port, debug=debug)
    controller.start()
    _wait_for_started(controller)

    if open_browser:
        _open_browser_delayed(host, port)

    try:
        controller.join()
    except KeyboardInterrupt:
        controller.stop()
        controller.join()


def run_webui_hotswap(
    *,
    host: str,
    port: int,
    open_browser: bool,
    debug: bool,
    watch_root: Path | None = None,
    stop_event: threading.Event | None = None,
    server_factory: Callable[[], _ServerController] | None = None,
) -> None:
    """Run the Web UI server and restart it when static assets change."""
    from watchfiles import watch

    watch_path = watch_root or DEFAULT_WEBUI_STATIC_ROOT
    local_stop_event = stop_event or threading.Event()
    create_server = server_factory or (lambda: _build_server_controller(host=host, port=port, debug=debug))
    browser_opened = False

    while not local_stop_event.is_set():
        controller = create_server()
        controller.start()
        _wait_for_started(controller)

        if open_browser and not browser_opened:
            _open_browser_delayed(host, port)
            browser_opened = True

        restart_requested = False
        try:
            for changes in watch(
                watch_path,
                stop_event=local_stop_event,
                debounce=WEBUI_HOTSWAP_DEBOUNCE_MS,
                step=100,
                yield_on_timeout=True,
            ):
                if not controller.alive:
                    raise RuntimeError("Web UI server exited unexpectedly")

                if not changes:
                    continue

                if not _has_relevant_webui_change(changes):
                    continue

                restart_requested = True
                controller.stop()
                break
        except KeyboardInterrupt:
            controller.stop()
        finally:
            controller.join()

        if not restart_requested:
            break
