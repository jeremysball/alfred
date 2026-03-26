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
3. **Fast Startup**: Warm browser pool for ~50ms session start
4. **Single Shared Browser**: One browser context for all agent sessions
5. **Future Interaction**: Foundation for user interaction (click/type) in later PRD

---

## Success Criteria

- [ ] Agent can create browser session (returns page_id)
- [ ] Agent can continue session using page_id (multi-turn)
- [ ] Agent can navigate to URLs with 30s timeout
- [ ] Agent can click/fill/extract with 5s timeout
- [ ] Clear error messages on element not found/timeout
- [ ] Real-time screenshot preview via existing WebSocket (2 FPS)
- [ ] Screenshot encoding uses thread pool (non-blocking)
- [ ] Browser startup <100ms via warm pool
- [ ] Pages auto-close after 1 hour (TTL cleanup)
- [ ] Graceful degradation if Playwright not installed
- [ ] Security warning documented for shared context

---

## Milestones

### Milestone 1: Browser Pool Infrastructure

**Goal**: Fast browser startup with warm pool.

**Changes**:
- Create `BrowserPool` class in `src/alfred/browser/pool.py`
- Pre-launch Chromium on Alfred startup
- Maintain 1 warm browser context
- Provide `new_page()` method for fast page creation

**Validation**:
- Browser pool starts in <3s at Alfred startup
- `new_page()` returns in <100ms
- Pages share cookies/storage (single context)

---

### Milestone 2: Browser Control Tools

**Goal**: Agent can control browser via semantic actions.

**Changes**:
- Create `BrowserTool` in `src/alfred/tools/browser.py`
- Actions: `goto`, `click`, `fill`, `extract`, `screenshot`
- Use CSS selectors (not coordinates)
- Return structured results for LLM consumption

**Validation**:
- Agent can navigate to URL and extract page title
- Agent can click button by selector
- Agent can fill form and submit
- Screenshots saved to temp path

---

### Milestone 3: Real-Time Preview (Web UI)

**Goal**: Users see browser session live in Web UI.

**Changes**:
- Use existing WebSocket (not new endpoint)
- Message type: `browser.screenshot` with hex-encoded JPEG
- Screenshot capture in thread pool (non-blocking)
- `<img>` element in Web UI for preview
- Subscribe/unsubscribe messages to control stream

**Validation**:
- Preview updates every 500ms
- Low latency (<1s from action to visual update)
- Screenshot encoding doesn't block chat messaging
- Works with single shared browser

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
# src/alfred/browser/pool.py
from playwright.async_api import async_playwright, Browser, BrowserContext

class BrowserPool:
    """Warm browser pool for fast session startup.
    
    SECURITY NOTE: Single shared context means all sessions share cookies
    and localStorage. Do not use for sensitive sites with multiple users.
    """
    
    _instance: BrowserPool | None = None
    PAGE_TTL_SECONDS = 3600  # 1 hour max page lifetime
    
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._pages: dict[str, tuple[Page, datetime]] = {}  # page_id -> (page, created_at)
        self._cleanup_task: asyncio.Task | None = None
    
    @classmethod
    async def get_instance(cls) -> BrowserPool:
        if cls._instance is None:
            cls._instance = BrowserPool()
            await cls._instance._warmup()
        return cls._instance
    
    async def _warmup(self):
        """Pre-launch browser at startup."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("Playwright not installed. Run: uv pip install playwright && playwright install chromium")
        
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def new_page(self) -> Page:
        """Fast page creation from warm context."""
        page = await self._context.new_page()
        page_id = f"page_{uuid4().hex[:8]}"
        self._pages[page_id] = (page, datetime.now())
        return page_id, page
    
    async def get_page(self, page_id: str) -> Page:
        """Get existing page by ID."""
        if page_id not in self._pages:
            raise ValueError(f"Page {page_id} not found")
        page, _ = self._pages[page_id]
        return page
    
    async def close_page(self, page_id: str):
        """Close a page and remove from tracking."""
        if page_id in self._pages:
            page, _ = self._pages.pop(page_id)
            await page.close()
    
    async def _cleanup_loop(self):
        """Periodic cleanup of stale pages."""
        while True:
            await asyncio.sleep(300)  # Check every 5 minutes
            await self._cleanup_stale_pages()
    
    async def _cleanup_stale_pages(self):
        """Close pages older than TTL."""
        now = datetime.now()
        stale = [
            page_id for page_id, (_, created_at) in self._pages.items()
            if (now - created_at).total_seconds() > self.PAGE_TTL_SECONDS
        ]
        for page_id in stale:
            logger.info(f"Closing stale browser page: {page_id}")
            await self.close_page(page_id)
```

### Browser Tool

```python
# src/alfred/tools/browser.py
from alfred.tools.base import Tool

class BrowserTool(Tool):
    """Tool for browser automation via Playwright.
    
    Multi-turn usage:
    - First call: create new page, returns page_id
    - Subsequent calls: pass same page_id to continue session
    - Logged-in state persists across calls (shared context)
    """
    
    name = "browser_control"
    description = "Control a web browser programmatically"
    
    async def execute(self, action: str, page_id: str | None = None, **params) -> str:
        pool = await BrowserPool.get_instance()
        
        # Get existing page or create new one
        if page_id:
            page = await pool.get_page(page_id)
        else:
            page = await pool.new_page()
            page_id = pool.get_page_id(page)
        
        try:
            match action:
                case "new_session":
                    return f"Created new browser session: {page_id}"
                
                case "goto":
                    await page.goto(params["url"], timeout=30000)
                    return f"Navigated to {page.url}, title: {await page.title()}"
                
                case "click":
                    await page.click(params["selector"], timeout=5000)
                    return f"Clicked element: {params['selector']}"
                
                case "fill":
                    await page.fill(params["selector"], params["text"])
                    return f"Filled {params['selector']} with '{params['text']}'"
                
                case "extract":
                    text = await page.text_content(params["selector"], timeout=5000)
                    return text or "No text found"
                
                case "screenshot":
                    path = f"/tmp/alfred_screenshot_{uuid4()}.png"
                    await page.screenshot(path=path)
                    return f"Screenshot saved: {path}"
                
                case "close":
                    await pool.close_page(page_id)
                    return f"Closed session: {page_id}"
                
                case _:
                    return f"Unknown action: {action}"
        except TimeoutError:
            return f"ERROR: Timeout - element '{params.get('selector', 'unknown')}' not found or operation took too long"
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {str(e)[:100]}"
```

### Screenshot Streaming (Thread Pool)

```python
# src/alfred/tools/browser_stream.py
import asyncio
from concurrent.futures import ThreadPoolExecutor

class BrowserStreamManager:
    """Handle real-time browser preview via WebSocket.
    
    Uses thread pool to avoid blocking event loop during screenshot encoding.
    """
    
    def __init__(self):
        self._streaming_pages: dict[str, tuple[Page, WebSocket]] = {}
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._stream_tasks: dict[str, asyncio.Task] = {}
    
    async def start_stream(self, page_id: str, page: Page, websocket: WebSocket):
        """Start screenshot streaming for a page."""
        self._streaming_pages[page_id] = (page, websocket)
        task = asyncio.create_task(self._stream_loop(page_id, page, websocket))
        self._stream_tasks[page_id] = task
    
    async def _stream_loop(self, page_id: str, page: Page, websocket: WebSocket):
        """Screenshot loop with offloaded encoding."""
        last_screenshot: bytes | None = None
        
        while page_id in self._streaming_pages:
            try:
                # Offload CPU-intensive screenshot to thread pool
                screenshot = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: sync_screenshot(page)
                )
                
                # Only send if changed
                if screenshot != last_screenshot:
                    await websocket.send_json({
                        "type": "browser.screenshot",
                        "payload": {"image": screenshot.hex(), "page_id": page_id}
                    })
                    last_screenshot = screenshot
                    
            except Exception as e:
                logger.error(f"Screenshot failed for {page_id}: {e}")
            
            await asyncio.sleep(0.5)  # 2 FPS
    
    def sync_screenshot(page: Page) -> bytes:
        """Synchronous screenshot (runs in thread pool)."""
        import playwright.sync_api
        # Convert async page to sync for thread safety
        return page.screenshot(type="jpeg", quality=70, full_page=False)
    
    async def stop_stream(self, page_id: str):
        """Stop streaming for a page."""
        if page_id in self._streaming_pages:
            del self._streaming_pages[page_id]
        if page_id in self._stream_tasks:
            self._stream_tasks[page_id].cancel()
            del self._stream_tasks[page_id]
```

### Web UI Integration

```javascript
// src/alfred/interfaces/webui/static/js/browser-preview.js
class BrowserPreview {
    constructor() {
        this.ws = null;
        this.img = document.getElementById('browser-preview');
        this.currentPageId = null;
    }
    
    connect(existingWebSocket) {
        // Use existing Alfred WebSocket, not a new one
        this.ws = existingWebSocket;
        
        this.ws.addEventListener('message', (event) => {
            const msg = JSON.parse(event.data);
            
            if (msg.type === 'browser.screenshot' && msg.payload.page_id === this.currentPageId) {
                // Convert hex string back to bytes
                const hex = msg.payload.image;
                const bytes = new Uint8Array(hex.match(/.{2}/g).map(b => parseInt(b, 16)));
                const blob = new Blob([bytes], {type: 'image/jpeg'});
                const url = URL.createObjectURL(blob);
                this.img.src = url;
            }
        });
    }
    
    subscribe(pageId) {
        this.currentPageId = pageId;
        this.ws.send(JSON.stringify({
            type: 'browser.subscribe',
            payload: {page_id: pageId}
        }));
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
src/alfred/
├── tools/
│   ├── browser.py              # BrowserTool (stateless, receives page_id)
│   ├── browser_pool.py         # BrowserPool with TTL cleanup
│   └── browser_stream.py       # StreamManager with thread pool
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

**⚠️ Shared Browser Context Warning:**

All agent sessions share the same browser context (cookies, localStorage, sessionStorage). This means:
- If Agent A logs into Gmail, Agent B is also logged in
- Session data persists across Alfred restarts (until page TTL expires)
- **Do not use for sensitive multi-user scenarios**

**Mitigations:**
- Pages auto-close after 1 hour (TTL)
- `browser close` action to manually end session
- Future: Per-session contexts (out of scope for MVP)

---

## Open Questions

1. **Persistence**: Should browser cookies persist across Alfred restarts?
2. **Multi-page**: Should agent manage multiple tabs?
3. **Downloads**: How to handle file downloads?
4. **Auth**: How to handle login sessions securely?
5. **Headless**: Default to headless in production?

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-25 | Single shared browser | Simpler, faster, no isolation needed for MVP |
| 2026-03-25 | Screenshot streaming (not CDP) | Works across all browsers, simpler implementation |
| 2026-03-25 | No sandboxing | User request, trust environment |
| 2026-03-25 | Semantic selectors (not coordinates) | Robust, maintainable, LLM-friendly |
| 2026-03-25 | 2 FPS screenshot rate | Balance between real-time and performance |
| 2026-03-25 | Tool receives page_id explicitly | Aligns with stateless tool pattern, enables multi-turn |
| 2026-03-25 | Use existing WebSocket with message types | Consistent with Alfred's unified WS pattern |
| 2026-03-25 | Thread pool for screenshot encoding | Prevents blocking event loop |
| 2026-03-25 | Page TTL = 1 hour | Prevents resource leaks, documented security tradeoff |
| 2026-03-25 | Graceful degradation for missing Playwright | Alfred works without browser optional dep |

---

## Out of Scope

- User interaction (click/type) - Future PRD
- Browser session persistence across restarts
- Multiple concurrent browser contexts
- Mobile browser emulation
- Video recording of sessions

---

## Notes

- Playwright requires system dependencies (will document)
- Screenshots may contain sensitive data (warn users)
- Consider rate limiting for screenshot capture
- Future: Allow user to "take control" of browser
