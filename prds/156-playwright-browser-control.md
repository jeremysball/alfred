# PRD: Playwright Browser Control for Agent Sessions

## Issue Reference

**GitHub Issue**: [#156](https://github.com/jeremysball/alfred/issues/156)  
**Priority**: Medium  
**Status**: Draft

---

## Problem Statement

Alfred currently cannot interact with web interfaces, limiting its ability to:
- Help with web-based tasks (form filling, data extraction)
- Perform browser automation and testing
- Assist with web app development and debugging
- Navigate websites on behalf of the user

Users need a way for Alfred to control a browser programmatically and view the session in real-time through the Web UI.

---

## Solution Overview

Integrate Playwright to provide browser control capabilities with:
1. **Programmatic Control**: Agent uses semantic selectors (CSS/XPath), not raw mouse coordinates
2. **Real-Time Viewing**: Screenshot streaming via WebSocket to Web UI
3. **Session-Scoped Browser**: Session manager holds browser; tools access via session
4. **Always Headless**: Screenshots work without visible browser window
5. **LLM-Controlled TTL**: Agent specifies session lifetime per request

---

## Success Criteria

- [ ] Agent can navigate to URLs with 30s timeout
- [ ] Agent can click/fill/extract with 5s timeout
- [ ] Agent can specify TTL seconds for browser session lifetime
- [ ] Browser auto-closes after TTL expires
- [ ] Clear error messages on element not found/timeout
- [ ] Real-time screenshot preview via existing WebSocket (2 FPS)
- [ ] Screenshots broadcast to session's WebSocket connections
- [ ] Graceful degradation if Playwright not installed
- [ ] Screenshots work in headless mode

---

## Milestones

### Milestone 1: Browser Pool Infrastructure

**Goal**: Session-scoped browser with TTL management.

**Changes**:
- Create `BrowserPool` class in `src/alfred/tools/browser_pool.py`
- Session manager holds `BrowserPool` instance per session
- Always headless (screenshots work without visible window)
- TTL tracking: auto-close after specified duration
- Lazy initialization on first browser tool call in session

**Validation**:
- First browser tool call creates browser in <3s
- Browser scoped to session (separate sessions = separate browsers)
- Browser auto-closes after TTL expires or session ends
- Screenshots broadcast to WebSocket connections for that session only

---

### Milestone 2: Browser Control Tools

**Goal**: Agent can control browser via semantic actions.

**Changes**:
- Create `BrowserTool` in `src/alfred/tools/browser.py`
- Tool receives `session_id` from Alfred context
- Actions: `goto`, `click`, `fill`, `extract`, `close`
- `goto` accepts `ttl_seconds` parameter (default 3600)
- Session manager holds BrowserPool per session
- Use CSS selectors (not coordinates)
- Return structured results for LLM consumption

**Validation**:
- Agent can navigate to URL and extract page title
- Agent can specify custom TTL
- Agent can click button by selector
- Agent can fill form and submit
- Agent can explicitly close browser
- Screenshots available via WebSocket stream

---

### Milestone 3: Real-Time Preview (Web UI)

**Goal**: Users see browser session live in Web UI.

**Changes**:
- Use existing WebSocket (not new endpoint)
- Message type: `browser.screenshot` with hex-encoded JPEG
- Screenshot capture using async Playwright APIs
- Broadcast to WebSocket connections for the active session
- `<img>` element in Web UI for preview

**Validation**:
- Preview updates every 500ms when browser active
- Screenshots broadcast to session's WebSocket connections
- Screenshot capture doesn't block chat messaging
- Works with session-scoped browser

---

### Milestone 4: Agent Integration

**Goal**: LLM can plan and execute browser tasks.

**Changes**:
- Add browser tool schemas to tool registry
- Prompt engineering for browser action planning
- Error handling (element not found, timeout)
- Action result feedback to LLM

**Validation**:
- Agent can complete simple web task (e.g., check weather)
- Handles errors gracefully
- Provides useful feedback on failures

---

## Technical Design

### Browser Pool

```python
# src/alfred/tools/browser_pool.py
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class BrowserPool:
    """Browser pool for Alfred.
    
    Manages a single browser instance with TTL.
    Session manager creates/holds BrowserPool instances per session.
    """
    
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._created_at: datetime | None = None
        self._ttl_seconds: int = 3600
    
    @classmethod
    async def create(cls, ttl_seconds: int = 3600) -> "BrowserPool":
        """Factory: create a new browser pool instance."""
        pool = BrowserPool()
        await pool._initialize(ttl_seconds)
        return pool
    
    async def _initialize(self, ttl_seconds: int):
        """Initialize browser instance."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("Playwright not installed. Run: uv pip install playwright && playwright install chromium")
        
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        self._page = await self._context.new_page()
        self._created_at = datetime.now()
        self._ttl_seconds = ttl_seconds
        logger.info(f"Browser pool initialized with TTL {ttl_seconds}s")
    
    def is_expired(self) -> bool:
        """Check if pool has exceeded TTL."""
        if self._created_at is None:
            return True
        elapsed = (datetime.now() - self._created_at).total_seconds()
        return elapsed > self._ttl_seconds
    
    @property
    def page(self) -> Page:
        """Get the managed page."""
        if self._page is None:
            raise RuntimeError("Browser pool not initialized")
        return self._page
    
    async def close(self):
        """Close browser and cleanup."""
        if self._page:
            await self._page.close()
            self._page = None
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._created_at = None
        logger.info("Browser pool closed")
```

### Browser Tool

```python
# src/alfred/tools/browser.py
from alfred.tools.base import Tool
from alfred.tools.browser_pool import BrowserPool

class BrowserTool(Tool):
    """Tool for browser automation via Playwright.
    
    Stateless tool - accesses browser through session manager.
    Session manager holds BrowserPool instance per session.
    """
    
    name = "browser_control"
    description = "Control a web browser programmatically"
    
    async def execute(self, action: str, session_id: str, **params) -> str:
        """Execute browser action on session's browser.
        
        Args:
            action: goto, click, fill, extract, close
            session_id: Session ID from Alfred context
            **params: action-specific parameters
        """
        from alfred.core.sessions import get_session_manager
        
        session_manager = get_session_manager()
        pool = await session_manager.get_or_create_browser(session_id, params.get("ttl_seconds", 3600))
        
        try:
            match action:
                case "goto":
                    page = pool.page
                    await page.goto(params["url"], timeout=30000)
                    title = await page.title()
                    return f"Navigated to {page.url}, title: {title}"
                
                case "click":
                    page = pool.page
                    await page.click(params["selector"], timeout=5000)
                    return f"Clicked element: {params['selector']}"
                
                case "fill":
                    page = pool.page
                    await page.fill(params["selector"], params["text"])
                    return f"Filled {params['selector']} with '{params['text']}'"
                
                case "extract":
                    page = pool.page
                    text = await page.text_content(params["selector"], timeout=5000)
                    return text or "No text found"
                
                case "close":
                    await session_manager.close_browser(session_id)
                    return "Browser closed"
                
                case _:
                    return f"Unknown action: {action}"
        except TimeoutError:
            return f"ERROR: Timeout - element '{params.get('selector', 'unknown')}' not found"
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {str(e)[:100]}"
```

### Session Manager Integration

```python
# src/alfred/core/sessions.py (additions)

class SessionManager:
    """Extended to hold browser pools per session."""
    
    def __init__(self):
        # ... existing code ...
        self._session_browsers: dict[str, BrowserPool] = {}  # session_id -> BrowserPool
    
    async def get_or_create_browser(self, session_id: str, ttl_seconds: int = 3600) -> BrowserPool:
        """Get or create browser for session."""
        pool = self._session_browsers.get(session_id)
        if pool is None or pool.is_expired():
            if pool is not None:
                await pool.close()
            pool = await BrowserPool.create(ttl_seconds)
            self._session_browsers[session_id] = pool
        return pool
    
    async def close_browser(self, session_id: str):
        """Close browser for session."""
        pool = self._session_browsers.pop(session_id, None)
        if pool:
            await pool.close()
    
    async def close_session(self, session_id: str):
        """Close session and its browser."""
        await self.close_browser(session_id)
        # ... existing session cleanup ...
```

### Screenshot Streaming

```python
# src/alfred/tools/browser_stream.py
import asyncio
from alfred.interfaces.webui.server import _broadcast_to_session
from alfred.tools.browser_pool import BrowserPool
import logging

logger = logging.getLogger(__name__)


class BrowserStreamManager:
    """Handle real-time browser preview via WebSocket.
    
    Broadcasts screenshots to connections for a specific session.
    Uses async Playwright APIs (no thread pool needed).
    """
    
    def __init__(self, session_id: str):
        self._session_id = session_id
        self._streaming = False
        self._stream_task: asyncio.Task | None = None
        self._last_screenshot: bytes | None = None
    
    async def start_stream(self, page):
        """Start screenshot streaming for given page."""
        if self._streaming:
            return
        
        self._streaming = True
        self._stream_task = asyncio.create_task(self._stream_loop(page))
        logger.info(f"Browser screenshot streaming started for session {self._session_id}")
    
    async def stop_stream(self):
        """Stop streaming."""
        self._streaming = False
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None
        logger.info(f"Browser screenshot streaming stopped for session {self._session_id}")
    
    async def _stream_loop(self, page):
        """Screenshot loop - broadcasts to session's connections."""
        while self._streaming:
            try:
                # Async screenshot (no blocking)
                screenshot = await page.screenshot(
                    type="jpeg", 
                    quality=70, 
                    full_page=False
                )
                
                # Only broadcast if changed (to session's connections)
                if screenshot != self._last_screenshot:
                    await _broadcast_to_session(self._session_id, {
                        "type": "browser.screenshot",
                        "payload": {
                            "image": screenshot.hex(),
                            "url": page.url
                        }
                    })
                    self._last_screenshot = screenshot
                    
            except Exception as e:
                logger.error(f"Screenshot failed: {e}")
                # Stop streaming on error
                break
            
            await asyncio.sleep(0.5)  # 2 FPS
        
        self._streaming = False
```

### Web UI Integration

```javascript
// src/alfred/interfaces/webui/static/js/browser-preview.js
class BrowserPreview {
    constructor() {
        this.ws = null;
        this.img = document.getElementById('browser-preview');
        this.urlDisplay = document.getElementById('browser-url');
    }
    
    connect(existingWebSocket) {
        // Use existing Alfred WebSocket, not a new one
        this.ws = existingWebSocket;
        
        this.ws.addEventListener('message', (event) => {
            const msg = JSON.parse(event.data);
            
            if (msg.type === 'browser.screenshot') {
                // Convert hex string back to bytes
                const hex = msg.payload.image;
                const bytes = new Uint8Array(hex.match(/.{2}/g).map(b => parseInt(b, 16)));
                const blob = new Blob([bytes], {type: 'image/jpeg'});
                const url = URL.createObjectURL(blob);
                this.img.src = url;
                
                // Update URL display
                if (this.urlDisplay && msg.payload.url) {
                    this.urlDisplay.textContent = msg.payload.url;
                }
            }
        });
    }
}
```

---

## UI/UX Specifications

### Web UI Layout

```
┌─ Alfred Web UI ──────────────────────────┐
│                                          │
│  [Messages...]                           │
│                                          │
│  ┌─ Browser Preview ─────────────────┐  │
│  │                                    │  │
│  │  [Live screenshot preview]         │  │
│  │                                    │  │
│  │  URL: https://example.com          │  │
│  └────────────────────────────────────┘  │
│                                          │
│  [Input...]                              │
└──────────────────────────────────────────┘
```

### Preview Panel

- **Position**: Collapsible sidebar or inline below messages
- **Size**: 320x240 (thumbnail) or 1280x720 (expanded)
- **Update**: Every 500ms
- **Controls**: Expand/collapse, pause/resume, manual refresh

---

## File Structure

```
src/alfred/tools/
├── browser.py          # BrowserTool (stateless, uses session manager)
├── browser_pool.py     # BrowserPool with TTL management
└── browser_stream.py   # StreamManager broadcasting per session

src/alfred/core/
└── sessions.py         # Extended: session-scoped browser management
```

## Dependencies

```toml
[project.optional-dependencies]
browser = [
    "playwright>=1.40.0",
]
```

```bash
# Setup script
playwright install chromium
```

## Security Considerations

**⚠️ Browser Data Persistence:**

The singleton browser maintains cookies and localStorage until TTL expires or explicit close. This means:
- Logged-in state persists across agent interactions
- Session data shared across all WebSocket connections
- **Clear sensitive data** by calling `close` action or waiting for TTL

---

## Open Questions

1. **Downloads**: How to handle file downloads?
2. **Auth**: How to handle login sessions securely?

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-26 | Session-scoped browser | Session manager holds browser; tools are stateless, access via session_id |
| 2026-03-26 | Always headless (no headed mode) | Screenshots work in headless, no UI complexity |
| 2026-03-26 | LLM controls TTL via parameter | Flexible session lifetime, similar to bash timeout |
| 2026-03-26 | Stateless tools (no page_id) | Matches Alfred's existing tool architecture |
| 2026-03-26 | Async screenshot (no thread pool) | Playwright has native async APIs, simpler code |
| 2026-03-26 | Broadcast to all WebSockets | One user = one Alfred = show on all connections |
| 2026-03-25 | Screenshot streaming (not CDP) | Works across all browsers, simpler implementation |
| 2026-03-25 | Semantic selectors (not coordinates) | Robust, maintainable, LLM-friendly |
| 2026-03-25 | 2 FPS screenshot rate | Balance between real-time and performance |
| 2026-03-25 | Use existing WebSocket with message types | Consistent with Alfred's unified WS pattern |
| 2026-03-25 | Graceful degradation for missing Playwright | Alfred works without browser optional dep |

---

## Out of Scope

- User interaction (click/type) - Future PRD
- Multiple concurrent browser contexts
- Mobile browser emulation
- Video recording of sessions
- Per-session browser isolation

---

## Notes

- Playwright requires system dependencies (will document)
- Screenshots may contain sensitive data (warn users)
- Uses native async Playwright APIs (no thread pool needed)
- Future: Allow user to "take control" of browser
