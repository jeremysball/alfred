"""Dispatcher entry point."""
import asyncio
import logging
import signal

from alfred.config import Settings
from alfred.dispatcher import Dispatcher
from alfred.telegram_bot import TelegramBot
from alfred.pi_manager import PiManager
from alfred.token_tracker import TokenTracker
from alfred.table_renderer import ensure_playwright_installed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point."""
    settings = Settings()
    logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))
    
    # Auto-install Playwright browsers if needed
    logger.info("[INIT] Checking Playwright installation...")
    playwright_ready = await ensure_playwright_installed()
    if not playwright_ready:
        logger.warning("[INIT] Table rendering unavailable. Install manually: uv run playwright install chromium")
    
    # Create token tracker
    token_tracker = TokenTracker(settings.workspace_dir / "logs")
    
    # Create pi manager with LLM provider config
    pi_manager = PiManager(
        timeout=settings.pi_timeout,
        llm_provider=settings.llm_provider,
        llm_api_key=settings.llm_api_key,
        llm_model=settings.llm_model,
        pi_path=settings.pi_path,
        token_tracker=token_tracker,
        skills_dirs=settings.skills_dirs
    )
    
    # Create dispatcher
    dispatcher = Dispatcher(
        workspace_dir=settings.workspace_dir,
        threads_dir=settings.threads_dir,
        pi_manager=pi_manager,
        token_tracker=token_tracker
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
