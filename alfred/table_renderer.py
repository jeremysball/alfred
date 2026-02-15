"""Table rendering: Markdown tables as images."""
import asyncio
import logging
from io import BytesIO
from pathlib import Path

try:
    import markdown
    from playwright.async_api import async_playwright
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

logger = logging.getLogger(__name__)

DEFAULT_CSS = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        padding: 20px;
        background: white;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        font-size: 14px;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 8px 12px;
        text-align: left;
    }
    th {
        background-color: #f5f5f5;
        font-weight: 600;
    }
    tr:nth-child(even) {
        background-color: #fafafa;
    }
</style>
"""


class TableRenderer:
    """Renders markdown tables as images using Playwright."""
    
    def __init__(self):
        self._playwright = None
        self._browser = None
        self._initialized = False
    
    async def setup(self) -> bool:
        """Initialize Playwright browser. Returns True if ready."""
        if not HAS_DEPS:
            logger.error("[TABLE] markdown and playwright required. Run: uv pip install markdown playwright")
            return False
        
        if self._initialized:
            return True
        
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch()
            self._initialized = True
            logger.info("[TABLE] Playwright browser initialized")
            return True
        except Exception as e:
            logger.error(f"[TABLE] Failed to initialize browser: {e}")
            logger.info("[TABLE] Try running: uv run playwright install chromium")
            return False
    
    async def render_table(self, table_md: str, width: int = 800) -> BytesIO | None:
        """Render markdown table to PNG image."""
        if not await self.setup():
            return None
        
        try:
            # Convert markdown to HTML
            html_table = markdown.markdown(table_md, extensions=['tables'])
            full_html = f"{DEFAULT_CSS}{html_table}"
            
            # Render page
            page = await self._browser.new_page(viewport={'width': width, 'height': 600})
            await page.set_content(full_html)
            
            # Get table dimensions
            table_elem = await page.query_selector('table')
            if not table_elem:
                logger.warning("[TABLE] No table found in markdown")
                await page.close()
                return None
            
            bbox = await table_elem.bounding_box()
            if bbox:
                # Screenshot just the table
                await page.set_viewport_size({'width': int(bbox['width']) + 40, 'height': int(bbox['height']) + 40})
            
            screenshot = await page.screenshot(full_page=True)
            await page.close()
            
            return BytesIO(screenshot)
            
        except Exception as e:
            logger.exception(f"[TABLE] Render failed: {e}")
            return None
    
    async def close(self):
        """Cleanup browser resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._initialized = False


async def ensure_playwright_installed():
    """Check and auto-install Playwright browsers if needed."""
    try:
        from playwright.async_api import async_playwright
        
        # Try to launch browser
        p = await async_playwright().start()
        try:
            browser = await p.chromium.launch()
            await browser.close()
            logger.info("[TABLE] Playwright browser already installed")
            await p.stop()
            return True
        except Exception:
            await p.stop()
            logger.info("[TABLE] Browser not found, installing...")
            
            # Install chromium
            import subprocess
            result = subprocess.run(
                ["uv", "run", "playwright", "install", "chromium"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info("[TABLE] Playwright chromium installed")
                return True
            else:
                logger.error(f"[TABLE] Install failed: {result.stderr}")
                return False
                
    except ImportError:
        logger.error("[TABLE] playwright not installed. Run: uv pip install playwright")
        return False
