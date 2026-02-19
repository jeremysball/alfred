"""Alfred CLI entry point with Typer."""

import asyncio
import logging
import sys
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from src.alfred import Alfred
from src.cli.cron import app as cron_app
from src.config import load_config

app = typer.Typer(
    name="alfred",
    help="Alfred - Persistent memory-augmented LLM assistant",
    no_args_is_help=False,  # We'll handle default behavior ourselves
)
console = Console()
logger = logging.getLogger(__name__)


class ColoredFormatter(logging.Formatter):
    """Formatter with colored log levels."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",   # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def __init__(self, fmt: str | None = None, datefmt: str | None = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        # Get color for this level
        levelname = record.levelname
        if self.use_colors and levelname in self.COLORS:
            color = self.COLORS[levelname]
            reset = self.COLORS["RESET"]
            record.levelname = f"{color}{levelname}{reset}"

        return super().format(record)


class TruncatingFormatter(ColoredFormatter):
    """Formatter that truncates long log messages with colors."""

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        max_length: int = 512,
        use_colors: bool = True,
    ):
        super().__init__(fmt, datefmt, use_colors)
        self.max_length = max_length

    def format(self, record: logging.LogRecord) -> str:
        # Store original levelname since ColoredFormatter modifies it
        original_levelname = record.levelname
        result = super().format(record)

        # Restore original for other formatters
        record.levelname = original_levelname

        if len(result) > self.max_length:
            truncated = len(result) - self.max_length
            result = result[:self.max_length - 3] + f"... [trunc {truncated} chars]"
        return result

# Register cron subcommands
app.add_typer(cron_app, name="cron", help="Manage cron jobs")

# Global state for callback
_run_telegram = False
_debug_level: str | None = None
_no_trunc = False


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
    no_trunc: bool = typer.Option(
        False,
        "--notrunc",
        help="Disable log message truncation (default: truncate to 512 chars)",
    ),
) -> None:
    """Alfred - Persistent memory-augmented LLM assistant.

    Run without arguments to start interactive chat.
    Use 'alfred cron' for cron job management.
    """
    global _run_telegram, _debug_level, _no_trunc
    _run_telegram = telegram
    _debug_level = debug
    _no_trunc = no_trunc

    # If no subcommand, run interactive chat
    if ctx.invoked_subcommand is None:
        asyncio.run(_run_interactive())


async def _run_interactive() -> None:
    """Run interactive CLI or Telegram bot."""
    _setup_logging()

    config = load_config()
    alfred = Alfred(config, telegram_mode=_run_telegram)

    try:
        if _run_telegram:
            await _run_telegram_bot(alfred)
        else:
            await _run_chat(alfred)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down Alfred...")
    finally:
        logger.info("CLI/Bot run complete, shutting down Alfred...")
        await alfred.stop()


async def _run_chat(alfred: Alfred) -> None:
    """Run interactive CLI chat."""
    from src.interfaces.cli import CLIInterface

    interface = CLIInterface(alfred)
    await alfred.start()
    await interface.run()


async def _run_telegram_bot(alfred: Alfred) -> None:
    """Run Telegram bot."""
    from src.interfaces.telegram import TelegramInterface

    data_dir = getattr(alfred.config, "data_dir", Path("data"))
    interface = TelegramInterface(alfred.config, alfred, data_dir)
    await alfred.start()
    await interface.run()


def _setup_logging() -> None:
    """Configure logging based on debug level."""
    if _debug_level == "debug":
        log_level = logging.DEBUG
    elif _debug_level == "info":
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    use_colors = sys.stdout.isatty()
    handler = logging.StreamHandler()
    if _no_trunc:
        formatter = ColoredFormatter(
            "%(levelname)s:%(name)s:%(message)s",
            use_colors=use_colors,
        )
    else:
        formatter = TruncatingFormatter(
            "%(levelname)s:%(name)s:%(message)s",
            max_length=512,
            use_colors=use_colors,
        )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)


def run_async(coro_factory: Callable[[], Coroutine[Any, Any, None]]) -> None:
    """Run an async function from sync context.

    Args:
        coro_factory: Function that returns a coroutine
    """
    asyncio.run(coro_factory())


if __name__ == "__main__":
    app()
