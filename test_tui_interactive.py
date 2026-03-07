import asyncio
from unittest.mock import MagicMock
from alfred.interfaces.pypitui_cli import AlfredTUI
from alfred.alfred import Alfred
from alfred.config import Config
from pathlib import Path
import logging
import sys

logging.basicConfig(level=logging.DEBUG, filename="/tmp/tui_interactive.log")

async def test_tui():
    config = Config(
        telegram_bot_token="test",
        openai_api_key="test",
        data_dir=Path("/tmp/alfred_test_data")
    )
    config.data_dir.mkdir(parents=True, exist_ok=True)
    
    alfred = Alfred(config)
    tui = AlfredTUI(alfred)
    
    async def simulate_input():
        await asyncio.sleep(1)
        logging.debug("Sending first Ctrl-C")
        # In pypitui, we mock the terminal
        if hasattr(tui.terminal, "_input_buffer"):
            tui.terminal._input_buffer = "\x03"
        elif hasattr(tui.terminal, "read"):
            # Mock read
            original_read = tui.terminal.read
            tui.terminal.read = lambda *a, **k: "\x03"
        await asyncio.sleep(1)
        logging.debug("Sending second Ctrl-C")
        if hasattr(tui.terminal, "_input_buffer"):
            tui.terminal._input_buffer = "\x03"
        elif hasattr(tui.terminal, "read"):
            # Stop returning it so it processes
            pass
            
    asyncio.create_task(simulate_input())
    
    # Run the real run loop but break it if it takes too long
    try:
        await asyncio.wait_for(tui.run(), timeout=5.0)
        print("TUI exited gracefully")
    except asyncio.TimeoutError:
        print("TUI timed out - input handling is probably broken")

asyncio.run(test_tui())
