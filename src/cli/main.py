"""Alfred CLI entry point with Typer."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
from rich.console import Console

from src.alfred import Alfred
from src.cli.cron import app as cron_app
from src.config import load_config
from src.data_manager import get_log_file, init_xdg_directories

if TYPE_CHECKING:
    from src.interfaces.pypitui.toast import ToastManager

app = typer.Typer(
    name="alfred",
    help="Alfred - Persistent memory-augmented LLM assistant",
    no_args_is_help=False,  # We'll handle default behavior ourselves
)
console = Console()

# Register cron subcommands
app.add_typer(cron_app, name="cron", help="Manage cron jobs")

# Global state for callback
_run_telegram = False
_debug_level: str | None = None


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    telegram: bool = typer.Option(
        False,
        "--telegram",
        "-t",
        help="Run as Telegram bot (default: run as CLI)",
    ),
    debug: str | None = typer.Option(
        None,
        "--debug",
        "-d",
        help="Set debug level: 'info' or 'debug'. Default: warnings only",
    ),
) -> None:
    """Alfred - Persistent memory-augmented LLM assistant.

    Run without arguments to start interactive chat.
    Use 'alfred cron' for cron job management.
    """
    global _run_telegram, _debug_level
    _run_telegram = telegram
    _debug_level = debug

    # If no subcommand, run interactive chat
    if ctx.invoked_subcommand is None:
        asyncio.run(_run_interactive())


async def _run_interactive() -> None:
    """Run interactive CLI or Telegram bot."""
    from src.interfaces.pypitui.toast import ToastManager

    # Initialize XDG directories first (needed for log file path)
    init_xdg_directories()

    # Create toast manager for TUI mode
    toast_manager: ToastManager | None = None
    if not _run_telegram:
        toast_manager = ToastManager()

    # Set up logging to file only (never pollute stdout/stderr in TUI)
    _setup_logging(toast_manager)

    # Load config (lightweight)
    config = load_config()

    try:
        if _run_telegram:
            # Telegram mode: create Alfred synchronously (no TUI to show loading)
            alfred = Alfred(config, telegram_mode=True)
            await _run_telegram_bot(alfred)
        else:
            # TUI mode: create Alfred in background while TUI shows loading
            await _run_chat_deferred(config, toast_manager)
    except KeyboardInterrupt:
        pass


async def _run_chat_deferred(
    config: Any, toast_manager: "ToastManager | None"
) -> None:
    """Run TUI with deferred Alfred initialization."""
    from src.interfaces.pypitui_cli import AlfredTUI

    # Create TUI without alfred first (shows loading state)
    interface = AlfredTUI(alfred=None, toast_manager=toast_manager)

    # Initialize Alfred in background
    async def init_alfred() -> None:
        try:
            alfred = Alfred(config, telegram_mode=False)
            await alfred.start()
            # Mark TUI as ready once alfred is initialized
            interface.set_ready(alfred)
        except Exception:
            logging.exception("Failed to initialize Alfred")
            # Show error toast and exit
            if toast_manager:
                toast_manager.add("Startup failed - check logs", level="error")
            interface.running = False

    # Start initialization task
    asyncio.create_task(init_alfred())

    # Run TUI immediately (shows loading state until ready)
    await interface.run()


async def _run_chat(alfred: Alfred, toast_manager: "ToastManager | None") -> None:
    """Run interactive CLI chat."""
    from src.interfaces.pypitui_cli import AlfredTUI

    # Create TUI without alfred first (shows loading state)
    interface = AlfredTUI(alfred=None, toast_manager=toast_manager)

    # Start alfred in background
    async def init_and_start() -> None:
        try:
            await alfred.start()
            # Mark TUI as ready once alfred is initialized
            interface.set_ready(alfred)
        except Exception as e:
            logging.exception("Failed to initialize Alfred")
            # Show error toast and exit
            if toast_manager:
                toast_manager.add(f"Startup failed: {e}", level="error")
            interface.running = False

    # Start initialization task
    asyncio.create_task(init_and_start())

    # Run TUI immediately (shows loading state until ready)
    await interface.run()


async def _run_telegram_bot(alfred: Alfred) -> None:
    """Run Telegram bot."""
    from src.interfaces.telegram import TelegramInterface

    data_dir = getattr(alfred.config, "data_dir", Path("data"))
    interface = TelegramInterface(alfred.config, alfred, data_dir)
    try:
        await alfred.start()
        await interface.run()
    finally:
        await alfred.stop()


# Third-party loggers that are too verbose at DEBUG level
_NOISY_LOGGERS = [
    "markdown_it",  # Extremely verbose markdown parsing logs
    "httpcore",  # HTTP request/response details
    "httpx",  # HTTP client logs
    "urllib3",  # URL handling
    "asyncio",  # Async internals
]


def _suppress_noisy_loggers() -> None:
    """Suppress verbose third-party loggers to WARNING level."""
    for logger_name in _NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def _setup_logging(toast_manager: "ToastManager | None" = None) -> None:
    """Configure logging to file only (never stdout/stderr in TUI mode).

    Logs always go to $XDG_CACHE_HOME/alfred/alfred.log.
    In TUI mode, warnings/errors also appear as toasts.

    Args:
        toast_manager: If provided, show warnings/errors as toast notifications.
    """
    if _debug_level == "debug":
        log_level = logging.DEBUG
    elif _debug_level == "info":
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    # Ensure cache directory exists
    log_file = get_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Always log to file
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s")
    )

    handlers: list[logging.Handler] = [file_handler]

    # In TUI mode, also show warnings/errors as toasts
    if toast_manager is not None:
        from src.interfaces.pypitui.toast import ToastHandler

        toast_handler = ToastHandler(toast_manager)
        toast_handler.setLevel(logging.WARNING)  # Only warnings and above
        handlers.append(toast_handler)

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
    )

    # Suppress verbose third-party loggers
    _suppress_noisy_loggers()


def run_async(coro_factory: Callable[[], Coroutine[Any, Any, None]]) -> None:
    """Run an async function from sync context.

    Args:
        coro_factory: Function that returns a coroutine
    """
    asyncio.run(coro_factory())


if __name__ == "__main__":
    app()
