"""Alfred CLI entry point with Typer."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

import typer
from rich.console import Console

from src.alfred import Alfred
from src.cli.cron import app as cron_app
from src.cli.memory import app as memory_app
from src.config import load_config
from src.data_manager import init_xdg_directories

if TYPE_CHECKING:
    from src.cron.socket_protocol import (
        JobCompletedMessage,
        JobFailedMessage,
        JobStartedMessage,
        NotifyMessage,
    )
    from src.interfaces.pypitui.toast import ToastManager

app = typer.Typer(
    name="alfred",
    help="Alfred - Persistent memory-augmented LLM assistant",
    no_args_is_help=False,  # We'll handle default behavior ourselves
)
console = Console()

# Register cron subcommands
app.add_typer(cron_app, name="cron", help="Manage cron jobs")
app.add_typer(memory_app, name="memory", help="Manage memory system")

# Global state for callback
_run_telegram = False
_log_level: str | None = None


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    telegram: bool = typer.Option(
        False,
        "--telegram",
        "-t",
        help="Run as Telegram bot (default: run as CLI)",
    ),
    log: str | None = typer.Option(
        None,
        "--log",
        "-l",
        help="Set log level: 'info' or 'debug'. Default: warnings only",
    ),
) -> None:
    """Alfred - Persistent memory-augmented LLM assistant.

    Run without arguments to start interactive chat.
    Use 'alfred cron' for cron job management.
    """
    global _run_telegram, _log_level
    _run_telegram = telegram
    _log_level = log

    # If no subcommand, run interactive chat
    if ctx.invoked_subcommand is None:
        asyncio.run(_run_interactive())


async def _run_interactive() -> None:
    """Run interactive CLI or Telegram bot."""
    from src.interfaces.pypitui.toast import ToastManager

    # Create toast manager for TUI mode
    toast_manager: ToastManager | None = None
    if not _run_telegram:
        toast_manager = ToastManager()

    # Initialize XDG directories and load config
    init_xdg_directories()
    config = load_config()

    # Set up logging with optional toast handler
    _setup_logging(toast_manager)

    alfred = Alfred(config, telegram_mode=_run_telegram)

    try:
        if _run_telegram:
            await _run_telegram_bot(alfred)
        else:
            await _run_chat(alfred, toast_manager)
    except KeyboardInterrupt:
        pass
    finally:
        await alfred.stop()


async def _run_chat(alfred: Alfred, toast_manager: "ToastManager | None") -> None:
    """Run interactive CLI chat."""
    from src.cron.socket_server import SocketServer
    from src.interfaces.pypitui_cli import AlfredTUI

    # Create socket server for cron runner communication
    socket_server = SocketServer(
        on_notify=lambda msg: _handle_notify(toast_manager, msg),
        on_job_started=lambda msg: _handle_job_started(toast_manager, msg),
        on_job_completed=lambda msg: _handle_job_completed(toast_manager, msg),
        on_job_failed=lambda msg: _handle_job_failed(toast_manager, msg),
    )

    # Start socket server
    await socket_server.start()

    try:
        interface = AlfredTUI(alfred, toast_manager=toast_manager)
        await alfred.start()
        await interface.run()
    finally:
        await socket_server.stop()


def _handle_notify(
    toast_manager: "ToastManager | None",
    msg: "NotifyMessage",
) -> None:
    """Handle notify message from cron runner."""
    if toast_manager:
        toast_manager.add(msg.message, msg.level)


def _handle_job_started(
    toast_manager: "ToastManager | None",
    msg: "JobStartedMessage",
) -> None:
    """Handle job started message."""
    if toast_manager:
        toast_manager.add(f"Cron job started: {msg.job_name}", "info")


def _handle_job_completed(
    toast_manager: "ToastManager | None",
    msg: "JobCompletedMessage",
) -> None:
    """Handle job completed message."""
    if toast_manager:
        toast_manager.add(
            f"Cron job completed: {msg.job_name} ({msg.duration_ms}ms)",
            "info",
        )


def _handle_job_failed(
    toast_manager: "ToastManager | None",
    msg: "JobFailedMessage",
) -> None:
    """Handle job failed message."""
    if toast_manager:
        toast_manager.add(
            f"Cron job failed: {msg.job_name} - {msg.error}",
            "error",
        )


async def _run_telegram_bot(alfred: Alfred) -> None:
    """Run Telegram bot."""
    from src.interfaces.telegram import TelegramInterface

    data_dir = alfred.config.data_dir
    interface = TelegramInterface(alfred.config, alfred, data_dir)
    await alfred.start()
    await interface.run()


def _setup_logging(toast_manager: "ToastManager | None" = None) -> None:
    """Configure logging to file (never stdout/stderr in TUI mode).

    Logs go to $XDG_CACHE_HOME/alfred/alfred.log.
    In TUI mode, warnings/errors also appear as toasts.

    Args:
        toast_manager: If provided, show warnings/errors as toast notifications.
    """
    if _log_level == "debug":
        level = logging.DEBUG
    elif _log_level == "info":
        level = logging.INFO
    else:
        level = logging.WARNING

    # Import here to avoid circular import
    from src.data_manager import get_log_file

    # Ensure log directory exists
    log_file = get_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Always log to file
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s")
    )

    handlers: list[logging.Handler] = [file_handler]

    # In TUI mode, also show warnings/errors as toasts
    if toast_manager is not None:
        from src.interfaces.pypitui.toast import ToastHandler

        toast_handler = ToastHandler(toast_manager)
        toast_handler.setLevel(logging.WARNING)
        handlers.append(toast_handler)

    logging.basicConfig(
        level=level,
        handlers=handlers,
    )

    # Suppress noisy third-party loggers
    for logger_name in ["markdown_it", "httpcore", "httpx", "urllib3", "asyncio"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def run_async(coro_factory: Callable[[], Coroutine[Any, Any, None]]) -> None:
    """Run an async function from sync context.

    Args:
        coro_factory: Function that returns a coroutine
    """
    asyncio.run(coro_factory())


if __name__ == "__main__":
    app()
