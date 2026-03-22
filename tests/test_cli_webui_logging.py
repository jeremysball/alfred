"""CLI tests for separate root and Web UI log scoping."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from alfred.cli import main as cli_main

runner = CliRunner()


def _invoke_webui(args: list[str]) -> tuple[object, list[str | None], object]:
    """Invoke the CLI with logging/server hooks patched."""

    setup_log_levels: list[str | None] = []

    def capture_setup_logging(*_args, **_kwargs) -> None:
        setup_log_levels.append(cli_main._log_level)

    original_root_log_level = cli_main._log_level
    original_run_telegram = cli_main._run_telegram
    cli_main._log_level = None
    cli_main._run_telegram = False

    try:
        with (
            patch("alfred.cli.main._setup_logging", side_effect=capture_setup_logging),
            patch("alfred.cli.webui_hotswap.run_webui_server") as run_webui_server,
            patch("alfred.cli.webui_hotswap.run_webui_hotswap") as run_webui_hotswap,
        ):
            result = runner.invoke(cli_main.app, args)
    finally:
        cli_main._log_level = original_root_log_level
        cli_main._run_telegram = original_run_telegram

    run_webui_hotswap.assert_not_called()
    return result, setup_log_levels, run_webui_server


def test_root_log_debug_does_not_enable_webui_debug() -> None:
    """Root --log should not turn on Web UI-specific debug instrumentation."""

    result, setup_log_levels, run_webui_server = _invoke_webui(["--log", "debug", "webui"])

    assert result.exit_code == 0
    assert setup_log_levels == ["debug"]
    run_webui_server.assert_called_once_with(
        host="127.0.0.1",
        port=8080,
        open_browser=False,
        debug=False,
    )


def test_webui_log_debug_enables_webui_debug_without_root_debug() -> None:
    """webui --log should enable Web UI debug without changing root logging."""

    result, setup_log_levels, run_webui_server = _invoke_webui(["webui", "--log", "debug"])

    assert result.exit_code == 0
    assert setup_log_levels == [None]
    run_webui_server.assert_called_once_with(
        host="127.0.0.1",
        port=8080,
        open_browser=False,
        debug=True,
    )


def test_root_and_webui_log_debug_can_be_enabled_together() -> None:
    """Root and Web UI logging should be independently configurable."""

    result, setup_log_levels, run_webui_server = _invoke_webui(["--log", "debug", "webui", "--log", "debug"])

    assert result.exit_code == 0
    assert setup_log_levels == ["debug"]
    run_webui_server.assert_called_once_with(
        host="127.0.0.1",
        port=8080,
        open_browser=False,
        debug=True,
    )
