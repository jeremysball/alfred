"""Dispatcher entry point."""
import asyncio
import logging

from dispatcher.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    settings = Settings()
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    logger.info("Dispatcher starting...")
    logger.info(f"Workspace: {settings.workspace_dir}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    # TODO: Implement dispatcher


if __name__ == "__main__":
    asyncio.run(main())
