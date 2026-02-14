"""Dispatcher entry point."""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Dispatcher starting...")
    # TODO: Implement


if __name__ == "__main__":
    asyncio.run(main())
