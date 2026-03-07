import asyncio
from unittest.mock import MagicMock
from alfred.interfaces.pypitui_cli import AlfredTUI
from alfred.alfred import Alfred
from alfred.config import Config
from pathlib import Path
import logging
import sys
import termios
import tty

logging.basicConfig(level=logging.DEBUG, filename="/tmp/test_run.log")

async def test_tui():
    print("Starting TUI test...")
    try:
        config = Config(
            telegram_bot_token="test",
            openai_api_key="test",
            data_dir=Path("/tmp/alfred_test_data")
        )
        config.data_dir.mkdir(parents=True, exist_ok=True)
        
        alfred = Alfred(config)
        print("Alfred engine initialized")
        
        tui = AlfredTUI(alfred)
        print("TUI initialized, calling run()")
        
        # Don't actually run, just check if we get this far
        print("Test complete.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_tui())
