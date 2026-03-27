from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from alfred.cli import webui_hotswap
from alfred.interfaces.webui.daemon_bootstrap import DaemonBootstrapResult


def test_run_webui_server_bootstraps_daemon_before_starting_uvicorn(monkeypatch) -> None:
    """The Web UI launch path should bootstrap the daemon before uvicorn starts."""

    bootstrap_result = DaemonBootstrapResult(
        daemon_was_running=False,
        daemon_started=True,
        startup_error=None,
    )
    bootstrap_calls = 0
    configured_apps: list[object] = []

    class FakeAlfred:
        def __init__(self, config, telegram_mode: bool) -> None:
            self.config = config
            self.telegram_mode = telegram_mode
            self.start_called = False

        async def start(self) -> None:
            self.start_called = True

    class FakeServer:
        def __init__(self, config) -> None:
            assert bootstrap_calls == 1
            configured_apps.append(config.app)
            assert config.app.state.webui_bootstrap_result is bootstrap_result
            self.started = False
            self.should_exit = False

        def run(self) -> None:
            self.started = True

    def fake_bootstrap_daemon() -> DaemonBootstrapResult:
        nonlocal bootstrap_calls
        bootstrap_calls += 1
        return bootstrap_result

    def fake_create_app(*, alfred_instance):
        app = SimpleNamespace(state=SimpleNamespace())
        app.state.alfred = alfred_instance
        return app

    monkeypatch.setattr("alfred.data_manager.init_xdg_directories", lambda: None)
    monkeypatch.setattr("alfred.config.load_config", lambda: SimpleNamespace(data_dir=Path("/tmp/alfred-data")))
    monkeypatch.setattr("alfred.alfred.Alfred", FakeAlfred)
    monkeypatch.setattr("alfred.interfaces.webui.server.create_app", fake_create_app)
    monkeypatch.setattr("alfred.cli.webui_hotswap.bootstrap_daemon", fake_bootstrap_daemon)
    monkeypatch.setattr("uvicorn.Server", FakeServer)

    webui_hotswap.run_webui_server(host="127.0.0.1", port=8080, open_browser=False)

    assert bootstrap_calls == 1
    assert len(configured_apps) == 1
