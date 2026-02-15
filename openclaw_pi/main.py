"""Dispatcher entry point."""
import asyncio
import logging
import signal

from openclaw_pi.config import Settings
from openclaw_pi.dispatcher import Dispatcher
from openclaw_pi.telegram_bot import TelegramBot
from openclaw_pi.pi_manager import PiManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point."""
    settings = Settings()
    logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))
    
    # Create pi manager with LLM provider config
    pi_manager = PiManager(
        timeout=settings.pi_timeout,
        llm_provider=settings.llm_provider,
        llm_api_key=settings.llm_api_key,
        llm_model=settings.llm_model
    )
    
    # Create dispatcher
    dispatcher = Dispatcher(
        workspace_dir=settings.workspace_dir,
        threads_dir=settings.threads_dir,
        pi_manager=pi_manager
    )
    
    # Create bot
    bot = TelegramBot(settings.telegram_bot_token, dispatcher)
    
    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        raise asyncio.CancelledError()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.run()
    except asyncio.CancelledError:
        logger.info("Shutting down...")
    finally:
        await dispatcher.shutdown()
        logger.info("Shutdown complete")


def cli() -> None:
    """CLI entry point for console script."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli()
