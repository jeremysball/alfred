"""Alfred entry point - run with `python -m src` or `alfred` after install."""

import argparse
import asyncio
import logging
import sys

from src.alfred import Alfred
from src.config import load_config

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="alfred",
        description="Alfred - The Rememberer: A persistent memory-augmented LLM assistant",
    )
    parser.add_argument(
        "--telegram",
        action="store_true",
        help="Run as Telegram bot (default: run as CLI)",
    )
    parser.add_argument(
        "--debug",
        choices=["info", "debug"],
        default=None,
        help=(
            "Set debug level: 'info' for INFO messages, 'debug' for DEBUG messages. "
            "Default: warnings/errors only"
        ),
    )
    parser.add_argument(
        "--notrunc",
        action="store_true",
        help="Disable log message truncation (default: truncate to 512 chars)",
    )
    return parser.parse_args()


async def run_cli(alfred: Alfred) -> None:
    """Run interactive CLI."""
    from src.interfaces.cli import CLIInterface

    interface = CLIInterface(alfred)
    await alfred.start()
    try:
        await interface.run()
    finally:
        logger.info("CLI interface exited, shutting down Alfred...")
        await alfred.stop()


async def run_telegram(alfred: Alfred) -> None:
    """Run Telegram bot."""
    from src.interfaces.telegram import TelegramInterface

    interface = TelegramInterface(alfred.config, alfred)
    await alfred.start()
    try:
        await interface.run()
    finally:
        logger.info("Telegram interface exited, shutting down Alfred...")
        await alfred.stop()


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


async def async_main() -> None:
    """Main async entry point."""
    args = parse_args()

    # Set log level based on --debug flag
    if args.debug == "debug":
        log_level = logging.DEBUG
    elif args.debug == "info":
        log_level = logging.INFO
    else:
        log_level = logging.WARNING  # Default: only warnings and errors

    # Configure logging with optional truncation and colors
    use_colors = sys.stdout.isatty()
    handler = logging.StreamHandler()
    if args.notrunc:
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

    config = load_config()
    alfred = Alfred(config)

    if args.telegram:
        logger.info("Starting Alfred in Telegram mode")
        await run_telegram(alfred)
    else:
        await run_cli(alfred)


def main() -> None:
    """Synchronous entry point for script wrapper."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
