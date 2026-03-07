import asyncio
from unittest.mock import MagicMock
from alfred.interfaces.pypitui_cli import AlfredTUI
from alfred.alfred import Alfred
from alfred.config import Config
from pathlib import Path
import logging
import sys
import os

logging.basicConfig(level=logging.DEBUG, filename="/tmp/run_timeout.log")

async def test_tui():
    print("Starting TUI...")
    try:
        config = Config(
            telegram_bot_token="test",
            openai_api_key="test",
            data_dir=Path("/tmp/alfred_test_data")
        )
        config.data_dir.mkdir(parents=True, exist_ok=True)
        
        alfred = Alfred(config)
        tui = AlfredTUI(alfred)
        
        # Override running to True initially, but schedule it to stop
        async def stop_soon():
            await asyncio.sleep(2)
            print("Stopping TUI...")
            tui.running = False
            
        asyncio.create_task(stop_soon())
        
        await tui.run()
        print("TUI run finished naturally")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_tui())
