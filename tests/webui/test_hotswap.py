from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import click
from typer.main import get_command

from alfred.cli import main as cli_main
from alfred.cli.webui_hotswap import run_webui_hotswap
from alfred.interfaces.webui.daemon_bootstrap import DaemonBootstrapResult


def _wait_for(predicate: Callable[[], bool], timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_webui_help_includes_hotswap_flag() -> None:
    command = get_command(cli_main.webui_app)

    hotswap_option = next(
        option
        for option in command.params
        if isinstance(option, click.Option) and "--hotswap" in option.opts
    )

    assert hotswap_option.help == "Restart the Web UI server when static web assets change"


def test_webui_hotswap_restarts_only_on_webui_assets(tmp_path: Path) -> None:
    static_root = tmp_path / "static"
    static_root.mkdir()

    ignored_file = static_root / "notes.txt"
    ignored_file.write_text("one")

    watched_file = static_root / "index.html"
    watched_file.write_text("<html>one</html>")

    stop_event = threading.Event()
    start_count = 0
    stop_count = 0
    first_start = threading.Event()

    class FakeServerController:
        def __init__(self) -> None:
            self.started = False
            self._alive = True

        @property
        def alive(self) -> bool:
            return self._alive

        def start(self) -> None:
            nonlocal start_count
            start_count += 1
            self.started = True
            self._alive = True
            if start_count == 1:
                first_start.set()

        def stop(self) -> None:
            nonlocal stop_count
            stop_count += 1
            self._alive = False

        def join(self) -> None:
            return None

    def server_factory() -> FakeServerController:
        return FakeServerController()

    supervisor_thread = threading.Thread(
        target=run_webui_hotswap,
        kwargs={
            "host": "127.0.0.1",
            "port": 0,
            "open_browser": False,
            "watch_root": static_root,
            "stop_event": stop_event,
            "server_factory": server_factory,
        },
        daemon=True,
    )
    supervisor_thread.start()

    try:
        assert first_start.wait(timeout=3)
        assert start_count == 1

        ignored_file.write_text("two")
        time.sleep(0.75)
        assert start_count == 1

        watched_file.write_text("<html>two</html>")
        assert _wait_for(lambda: start_count == 2, timeout=5)
        assert stop_count >= 1
    finally:
        stop_event.set()
        supervisor_thread.join(timeout=5)

    assert not supervisor_thread.is_alive()


def test_run_webui_hotswap_uses_the_same_bootstrap_path(monkeypatch, tmp_path: Path) -> None:
    """Hotswap restarts should reuse the same daemon bootstrap helper each cycle."""

    bootstrap_result = DaemonBootstrapResult(
        daemon_was_running=False,
        daemon_started=True,
        startup_error=None,
    )
    bootstrap_calls = 0
    app_bootstrap_results: list[object] = []
    watched_file = tmp_path / "static" / "index.html"
    watched_file.parent.mkdir(parents=True)
    watched_file.write_text("<html>one</html>")
    watch_calls = 0
    stop_event = threading.Event()

    class FakeAlfred:
        def __init__(self, config, telegram_mode: bool) -> None:
            self.config = config
            self.telegram_mode = telegram_mode

        async def start(self) -> None:
            return None

    class FakeServer:
        def __init__(self, config) -> None:
            self.started = False
            self.should_exit = False
            app_bootstrap_results.append(config.app.state.webui_bootstrap_result)
            assert config.app.state.webui_bootstrap_result is bootstrap_result

        def run(self) -> None:
            self.started = True
            while not self.should_exit:
                import time

                time.sleep(0.01)

    def fake_bootstrap_daemon() -> DaemonBootstrapResult:
        nonlocal bootstrap_calls
        bootstrap_calls += 1
        return bootstrap_result

    def fake_create_app(*, alfred_instance):
        app = SimpleNamespace(state=SimpleNamespace())
        app.state.alfred = alfred_instance
        return app

    def fake_watch(*args, **kwargs):
        nonlocal watch_calls
        watch_calls += 1
        if watch_calls == 1:
            yield [("modified", watched_file)]
        else:
            stop_event.set()
            yield [("modified", watched_file)]

    monkeypatch.setattr("alfred.data_manager.init_xdg_directories", lambda: None)
    monkeypatch.setattr("alfred.config.load_config", lambda: SimpleNamespace(data_dir=Path("/tmp/alfred-data")))
    monkeypatch.setattr("alfred.alfred.Alfred", FakeAlfred)
    monkeypatch.setattr("alfred.interfaces.webui.server.create_app", fake_create_app)
    monkeypatch.setattr("alfred.cli.webui_hotswap.bootstrap_daemon", fake_bootstrap_daemon)
    monkeypatch.setattr("uvicorn.Server", FakeServer)
    monkeypatch.setattr("watchfiles.watch", fake_watch)

    run_webui_hotswap(
        host="127.0.0.1",
        port=8080,
        open_browser=False,
        watch_root=watched_file.parent,
        stop_event=stop_event,
    )

    assert bootstrap_calls == 2
    assert app_bootstrap_results == [bootstrap_result, bootstrap_result]
