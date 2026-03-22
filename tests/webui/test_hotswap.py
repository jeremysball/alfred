from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

import click
from typer.main import get_command

from alfred.cli import main as cli_main
from alfred.cli.webui_hotswap import run_webui_hotswap


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
            "debug": False,
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
