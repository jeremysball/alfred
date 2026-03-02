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
from src.data_manager import init_xdg_directories

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
    from src.interfaces.pypitui_cli import AlfredTUI

    interface = AlfredTUI(alfred, toast_manager=toast_manager)
    await alfred.start()
    await interface.run()


async def _run_telegram_bot(alfred: Alfred) -> None:
    """Run Telegram bot."""
    from src.interfaces.telegram import TelegramInterface

    data_dir = getattr(alfred.config, "data_dir", Path("data"))
    interface = TelegramInterface(alfred.config, alfred, data_dir)
    await alfred.start()
    await interface.run()


def _setup_logging(toast_manager: "ToastManager | None" = None) -> None:
    """Configure logging based on debug level.

    Args:
        toast_manager: If provided, use ToastHandler to display logs as
            toast notifications (TUI mode). Otherwise logs go to stderr.
    """
    if _debug_level == "debug":
        log_level = logging.DEBUG
    elif _debug_level == "info":
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    if toast_manager is not None:
        # TUI mode: warnings/errors go to toast, info/debug to stderr
        from src.interfaces.pypitui.toast import ToastHandler

        toast_handler = ToastHandler(toast_manager)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(log_level)

        logging.basicConfig(
            level=log_level,
            format="%(levelname)s:%(name)s:%(message)s",
            handlers=[toast_handler, stream_handler],
        )
    else:
        # Normal mode: log to stderr
        logging.basicConfig(
            level=log_level,
            format="%(levelname)s:%(name)s:%(message)s",
        )


def run_async(coro_factory: Callable[[], Coroutine[Any, Any, None]]) -> None:
    """Run an async function from sync context.

    Args:
        coro_factory: Function that returns a coroutine
    """
    asyncio.run(coro_factory())


if __name__ == "__main__":
    app()
