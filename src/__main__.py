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
    return parser.parse_args()


async def run_cli(alfred: Alfred) -> None:
    """Run interactive CLI."""
    from src.interfaces.cli import CLIInterface

    interface = CLIInterface(alfred)
    await alfred.start()
    try:
        await interface.run()
    finally:
        await alfred.stop()


async def run_telegram(alfred: Alfred) -> None:
    """Run Telegram bot."""
    from src.interfaces.telegram import TelegramInterface

    interface = TelegramInterface(alfred.config, alfred)
    await alfred.start()
    try:
        await interface.run()
    finally:
        await alfred.stop()


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

    logging.basicConfig(
        level=log_level,
        format="%(levelname)s:%(name)s:%(message)s",
    )

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
