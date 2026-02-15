"""Alfred - Telegram thread manager with Pi agent support."""
__version__ = "0.1.0"

from alfred.config import Settings
from alfred.dispatcher import Dispatcher
from alfred.pi_manager import PiManager, PiSubprocess
from alfred.telegram_bot import TelegramBot
from alfred.table_renderer import TableRenderer, ensure_playwright_installed

__all__ = ["Settings", "Dispatcher", "PiManager", "PiSubprocess", "TelegramBot", "TableRenderer", "ensure_playwright_installed"]
