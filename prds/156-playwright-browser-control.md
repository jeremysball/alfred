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

- [ ] Agent can start a browser session via tool call
- [ ] Agent can navigate to URLs programmatically
- [ ] Agent can click elements using CSS selectors
- [ ] Agent can fill forms and extract data
- [ ] Real-time screenshot preview in Web UI (2 FPS)
- [ ] Browser startup <100ms via warm pool
- [ ] Single shared browser context across sessions

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
- WebSocket endpoint `/ws/browser-stream`
- Screenshot capture every 500ms (JPEG, quality 70)
- Binary WebSocket messages for images
- `<img>` element in Web UI for preview

**Validation**:
- Preview updates every 500ms
- Low latency (<1s from action to visual update)
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
    """Warm browser pool for fast session startup."""
    
    _instance: BrowserPool | None = None
    
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._pages: list[Page] = []
    
    @classmethod
    async def get_instance(cls) -> BrowserPool:
        if cls._instance is None:
            cls._instance = BrowserPool()
            await cls._instance._warmup()
        return cls._instance
    
    async def _warmup(self):
        """Pre-launch browser at startup."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=False,  # Visible for now
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
    
    async def new_page(self) -> Page:
        """Fast page creation from warm context."""
        page = await self._context.new_page()
        self._pages.append(page)
        return page
    
    async def close_page(self, page: Page):
        """Close a page and remove from tracking."""
        if page in self._pages:
            self._pages.remove(page)
        await page.close()
```

### Browser Tool

```python
# src/alfred/tools/browser.py
from alfred.tools.base import Tool

class BrowserTool(Tool):
    """Tool for browser automation via Playwright."""
    
    name = "browser_control"
    description = "Control a web browser programmatically"
    
    async def execute(self, action: str, **params) -> str:
        pool = await BrowserPool.get_instance()
        
        # Get or create agent's page
        page = await self._get_agent_page()
        
        match action:
            case "goto":
                await page.goto(params["url"])
                return f"Navigated to {page.url}, title: {await page.title()}"
            
            case "click":
                await page.click(params["selector"])
                return f"Clicked element: {params['selector']}"
            
            case "fill":
                await page.fill(params["selector"], params["text"])
                return f"Filled {params['selector']} with '{params['text']}'"
            
            case "extract":
                text = await page.text_content(params["selector"])
                return text or "No text found"
            
            case "screenshot":
                path = f"/tmp/alfred_screenshot_{uuid4()}.png"
                await page.screenshot(path=path)
                return f"Screenshot saved: {path}"
            
            case _:
                return f"Unknown action: {action}"
```

### WebSocket Stream Handler

```python
# src/alfred/interfaces/webui/browser_stream.py
from fastapi import WebSocket

class BrowserStreamHandler:
    """Handle real-time browser preview via WebSocket."""
    
    def __init__(self, page: Page, websocket: WebSocket):
        self.page = page
        self.ws = websocket
        self._streaming = False
        self._last_screenshot: bytes | None = None
    
    async def start_stream(self):
        """Start screenshot streaming loop."""
        self._streaming = True
        while self._streaming:
            try:
                screenshot = await self.page.screenshot(
                    type="jpeg",
                    quality=70,
                    full_page=False
                )
                # Only send if changed (simple diff)
                if screenshot != self._last_screenshot:
                    await self.ws.send_bytes(screenshot)
                    self._last_screenshot = screenshot
            except Exception as e:
                logger.error(f"Screenshot failed: {e}")
            
            await asyncio.sleep(0.5)  # 2 FPS
    
    async def stop_stream(self):
        self._streaming = False
```

### Web UI Integration

```javascript
// Web UI JavaScript
class BrowserPreview {
    constructor() {
        this.ws = null;
        this.img = document.getElementById('browser-preview');
        this.connect();
    }
    
    connect() {
        this.ws = new WebSocket('ws://localhost:8888/ws/browser-stream');
        
        this.ws.onmessage = (event) => {
            if (event.data instanceof Blob) {
                const url = URL.createObjectURL(event.data);
                this.img.src = url;
            }
        };
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
