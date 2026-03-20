# PRD: Web-based UI for Alfred

**Status**: Draft  
**Issue**: #136  
**Priority**: High  
**Created**: 2026-03-18

---

## Problem Statement

The current TUI implementation (PyPiTUI) creates significant friction:

1. **High complexity**: ANSI escape sequences, terminal resize handling, scrollback management, and overlay systems require deep terminal knowledge
2. **Difficult debugging**: Visual bugs require terminal capture, escape code analysis, and complex tmux-based testing
3. **Slow iteration**: Changes require full TUI restart, visual verification is manual, and test automation is brittle
4. **Maintenance burden**: Every new feature must handle terminal edge cases (screen corruption, focus issues, rendering glitches)

The TUI works, but it's a velocity killer. We need an alternative interface that prioritizes developer productivity.

---

## Solution Overview

Create a **web-based UI** that coexists with the TUI:

- **Backend**: FastAPI with native WebSocket for bidirectional streaming
- **Frontend**: Vanilla JavaScript + Web Components (zero build step)
- **Packaging**: Single Python package, launched via `alfred webui`
- **Deployment**: Local-only (Tailscale handles network security)

The web UI provides:
- Full feature parity with TUI (streaming, tool calls, completions, etc.)
- Modern browser developer tools for debugging
- Hot reload for frontend development
- Easier visual testing and automation

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Browser                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Chat Panel │  │  Tool Calls │  │   Status Bar        │  │
│  │  (messages) │  │  (expand)   │  │  (tokens/queue)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Input Area (multiline, completion, history, queue)     ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                            │
                            │ WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  WebSocket  │  │   Alfred    │  │   Static Files      │  │
│  │  Handler    │◄─┤   Core      │  │   (HTML/JS/CSS)     │  │
│  │             │  │             │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | FastAPI + WebSocket | Native async, Python-only, excellent LLM streaming support |
| Frontend | Vanilla JS + Web Components | Zero build step, native browser APIs, component encapsulation |
| Real-time | WebSocket | Bidirectional streaming, natural fit for token streaming |
| Styling | CSS Custom Properties | Theming support, no preprocessor needed |
| Icons | SVG sprites | Lightweight, scalable, no icon font dependencies |

---

## User Experience

### Launching the Web UI

```bash
# Start server (does not open browser)
$ alfred webui
🚀 Alfred Web UI running at http://localhost:8080

# With custom port
$ alfred webui --port 3000

# Start server and open browser
$ alfred webui --open
```

### Core Interactions

| Action | Behavior |
|--------|----------|
| Type message | Input expands for multiline, syntax highlighting for code |
| Press Enter | Send message |
| Shift+Enter | Queue message (appears in status bar queue counter) |
| Press `/` | Command completion menu appears |
| Type `/resume ` | Session ID completion with fuzzy search |
| Press Ctrl+T | Toggle all tool calls expanded/collapsed |
| Press Escape | Clear message queue |
| Tool call appears | Collapsible panel, click to expand |
| Token streaming | Smooth word-by-word appearance (not character) |

### Visual Design

- **Dark theme by default** (matches developer expectations)
- **Message bubbles** for user/assistant distinction
- **Collapsible tool panels** with status indicators (running/success/error)
- **Fixed status bar** showing: model name, context tokens, input/output tokens, cache hits, reasoning tokens, queue count, throbber when streaming
- **Toast notifications** slide in from bottom-right for cron events

---

## Milestones

### Milestone 1: Foundation
**Goal**: Basic WebSocket server with health endpoint

- [ ] FastAPI app with WebSocket endpoint (`/ws`)
- [ ] Connection handshake and session management
- [ ] Static file serving (HTML entry point)
- [ ] Health check endpoint (`/health`)
- [ ] CLI command `alfred webui` with `--port` and `--open` flags
- [ ] Graceful shutdown handling

**Success Criteria**:
- `alfred webui --port 8080` starts server on port 8080
- Browser can connect to WebSocket and receive "connected" message
- Server responds to health check
- Ctrl+C shuts down cleanly

---

### Milestone 2: Message Streaming
**Goal**: Send/receive messages with LLM streaming

- [ ] WebSocket protocol for messages (`chat.send`, `chat.chunk`, `chat.complete`, `chat.error`)
- [ ] Integrate with Alfred's `chat_stream()` method
- [ ] Frontend message display component
- [ ] Token streaming with word-level updates (not character)
- [ ] Auto-scroll to newest message
- [ ] Connection status indicator

**Success Criteria**:
- User can type message and receive streaming response
- Messages appear in correct order
- Streaming is smooth (no jank)
- Connection loss is detected and shown

---

### Milestone 3: Tool Call Display
**Goal**: Visual tool call panels with expand/collapse

- [ ] WebSocket protocol for tool events (`tool.start`, `tool.output`, `tool.end`)
- [ ] Tool call panel Web Component (`<tool-call>`)
- [ ] Collapsed state: icon + tool name + spinner
- [ ] Expanded state: full arguments and output
- [ ] Ctrl+T global shortcut to expand/collapse all
- [ ] Status indicators (running/success/error)

**Success Criteria**:
- Tool calls appear inline with assistant messages
- Expand/collapse works smoothly
- Ctrl+T toggles all tool calls
- Success/error states are visually distinct

---

### Milestone 4: Input System
**Goal**: Rich input with completion and history

- [ ] Multiline textarea with auto-resize
- [ ] Command completion (`/new`, `/resume`, `/sessions`, etc.)
- [ ] Fuzzy session completion for `/resume `
- [ ] Message queue (Shift+Enter to queue, visual indicator)
- [ ] Per-directory message history (UP/DOWN navigation)
- [ ] Keyboard shortcuts (Ctrl+U clear line, Ctrl+A start, Ctrl+E end)

**Success Criteria**:
- All TUI keyboard shortcuts work
- Completion menu appears and filters correctly
- Queue system functional with visual feedback
- History persists per directory

---

### Milestone 5: Session Management
**Goal**: Full session command support

- [ ] `/new` command implementation
- [ ] `/resume <id>` command with session loading
- [ ] `/sessions` command with session list
- [ ] `/session` command for current session info
- [ ] `/context` command for system context display
- [ ] Session state synchronization on resume

**Success Criteria**:
- All session commands work via WebSocket
- Session loading restores conversation history
- Session list shows correct metadata
- Context display matches TUI format

---

### Milestone 6: Status and Notifications
**Goal**: Status bar and toast system

- [ ] Fixed status bar component
- [ ] Real-time token usage display
- [ ] Model name display
- [ ] Queue counter with badge
- [ ] Animated throbber during streaming
- [ ] Toast notification system for cron events
- [ ] WebSocket protocol for server→client notifications

**Success Criteria**:
- Status bar shows accurate token counts
- Throbber animates smoothly during streaming
- Toasts appear for cron job events
- Queue counter updates in real-time

---

### Milestone 7: Markdown Rendering
**Goal**: Rich markdown with code highlighting

- [ ] Markdown parsing (marked.js or similar)
- [ ] Code block syntax highlighting
- [ ] Copy button on code blocks
- [ ] Inline code styling
- [ ] Link handling (open in new tab)
- [ ] Table rendering

**Success Criteria**:
- Markdown renders correctly (bold, italic, lists, links)
- Code blocks have syntax highlighting
- Copy button works
- Tables render cleanly

---

### Milestone 8: Testing and Documentation
**Goal**: Production-ready with tests and docs

- [ ] Unit tests for WebSocket protocol
- [ ] Component tests for Web Components
- [ ] Integration tests for full flow
- [ ] Update README with `alfred webui` usage
- [ ] Document WebSocket protocol for future extensions
- [ ] Add to ROADMAP.md

**Success Criteria**:
- Test coverage >80% for new code
- All tests pass
- Documentation is complete
- No regression in TUI functionality

---

## WebSocket Protocol

### Client → Server Messages

```typescript
// Send a chat message
{
  type: "chat.send",
  payload: {
    content: string,
    queue?: boolean  // If true, queue instead of sending immediately
  }
}

// Execute a command
{
  type: "command.execute",
  payload: {
    command: string,  // e.g., "/new", "/resume abc123"
  }
}

// Request completion suggestions
{
  type: "completion.request",
  payload: {
    text: string,     // Current input text
    cursor: number,   // Cursor position
  }
}

// Acknowledge receipt (for flow control)
{
  type: "ack",
  payload: {
    messageId: string,
  }
}
```

### Server → Client Messages

```typescript
// Chat message started (empty assistant message created)
{
  type: "chat.started",
  payload: {
    messageId: string,
    role: "assistant",
  }
}

// Token chunk received
{
  type: "chat.chunk",
  payload: {
    messageId: string,
    content: string,  // This chunk only
  }
}

// Chat completed
{
  type: "chat.complete",
  payload: {
    messageId: string,
    finalContent: string,
    usage: {
      inputTokens: number,
      outputTokens: number,
      cacheReadTokens: number,
      reasoningTokens: number,
    }
  }
}

// Chat error
{
  type: "chat.error",
  payload: {
    messageId: string,
    error: string,
  }
}

// Tool execution started
{
  type: "tool.start",
  payload: {
    toolCallId: string,
    toolName: string,
    arguments: object,
    messageId: string,  // Parent assistant message
  }
}

// Tool output chunk
{
  type: "tool.output",
  payload: {
    toolCallId: string,
    chunk: string,
  }
}

// Tool execution completed
{
  type: "tool.end",
  payload: {
    toolCallId: string,
    success: boolean,
    output?: string,
  }
}

// Completion suggestions
{
  type: "completion.suggestions",
  payload: {
    suggestions: Array<{
      value: string,
      description?: string,
    }>,
  }
}

// Status update (tokens, queue, etc.)
{
  type: "status.update",
  payload: {
    model: string,
    contextTokens: number,
    inputTokens: number,
    outputTokens: number,
    cacheReadTokens: number,
    reasoningTokens: number,
    queueLength: number,
    isStreaming: boolean,
  }
}

// Toast notification
{
  type: "toast",
  payload: {
    message: string,
    level: "info" | "success" | "warning" | "error",
    duration?: number,  // ms, default 5000
  }
}

// Session loaded (after /resume)
{
  type: "session.loaded",
  payload: {
    sessionId: string,
    messages: Array<{
      id: string,
      role: "user" | "assistant" | "system",
      content: string,
      toolCalls?: Array<{
        id: string,
        name: string,
        arguments: object,
        output?: string,
        status: "running" | "success" | "error",
      }>,
    }>,
  }
}
```

---

## Web Components

### Component Hierarchy

```
<alfred-app>
  ├── <chat-panel>
  │     └── <chat-message> × N
  │           ├── <message-header>
  │           ├── <message-content>
  │           └── <tool-call> × N
  │                 ├── <tool-header>
  │                 └── <tool-output>
  ├── <status-bar>
  │     ├── <model-badge>
  │     ├── <token-counter>
  │     ├── <queue-badge>
  │     └── <streaming-indicator>
  ├── <input-area>
  │     ├── <textarea>
  │     └── <completion-menu>
  └── <toast-container>
        └── <toast-notification> × N
```

### Component API Examples

```html
<!-- Chat message -->
<chat-message 
  role="assistant" 
  content="Hello! How can I help?"
  timestamp="2026-03-18T10:30:00Z">
</chat-message>

<!-- Tool call -->
<tool-call
  id="call_abc123"
  name="read_file"
  args='{"path": "/docs/readme.md"}'
  output="File contents here..."
  status="success"
  expanded="false">
</tool-call>

<!-- Status bar -->
<status-bar
  model="kimi-latest"
  context="2450"
  input="1200"
  output="850"
  cached="2000"
  reasoning="150"
  queued="2"
  streaming="true">
</status-bar>
```

---

## File Structure

```
alfred/
├── src/
│   └── alfred/
│       ├── cli/
│       │   └── main.py              # Add `alfred webui` command
│       ├── interfaces/
│       │   ├── pypitui/             # Existing TUI (unchanged)
│       │   └── webui/               # NEW: Web UI
│       │       ├── __init__.py
│       │       ├── server.py        # FastAPI app, WebSocket handler
│       │       ├── static/
│       │       │   ├── index.html   # Entry point
│       │       │   ├── css/
│       │       │   │   ├── base.css
│       │       │   │   ├── components.css
│       │       │   │   └── themes.css
│       │       │   └── js/
│       │       │       ├── main.js           # App initialization
│       │       │       ├── websocket.js      # WebSocket client
│       │       │       ├── components/       # Web Components
│       │       │       │   ├── chat-message.js
│       │       │       │   ├── tool-call.js
│       │       │       │   ├── status-bar.js
│       │       │       │   ├── input-area.js
│       │       │       │   ├── completion-menu.js
│       │       │       │   └── toast-container.js
│       │       │       └── utils/
│       │       │           ├── markdown.js
│       │       │           └── keyboard.js
│       │       └── protocol.py      # Message type definitions
└── tests/
    └── webui/                       # Web UI specific tests
        ├── test_websocket.py
        └── test_components.py
```

---

## Configuration

### New Config Options

```toml
[webui]
enabled = true          # Enable web UI endpoints
port = 8080             # Default port
host = "127.0.0.1"      # Bind address (127.0.0.1 for local-only)
hot_reload = false      # Auto-reload frontend in dev mode
```

### Environment Variables

```bash
ALFRED_WEBUI_PORT=8080        # Override port
ALFRED_WEBUI_HOST=0.0.0.0     # Override host (use with caution)
```

---

## Security Considerations

Since this is **local-only with Tailscale**:

1. **Bind to localhost by default** (`127.0.0.1`)
2. **No authentication required** (Tailscale provides network-level security)
3. **CORS disabled** (same-origin only)
4. **No HTTPS** (Tailscale handles encryption)
5. **Input validation** on all WebSocket messages (prevent injection)
6. **Rate limiting** on message sending (prevent accidental flooding)

---

## Success Criteria

### Functional
- [ ] All TUI features work in Web UI
- [ ] WebSocket streaming is smooth (< 50ms latency per chunk)
- [ ] Tool calls display correctly with expand/collapse
- [ ] Session commands work identically to TUI
- [ ] Message queue and history work correctly

### Performance
- [ ] First paint < 2 seconds
- [ ] Message streaming at 60fps
- [ ] Memory usage stable over long sessions (> 100 messages)
- [ ] No memory leaks on hot reload

### Quality
- [ ] Test coverage > 80%
- [ ] No console errors in standard usage
- [ ] Works in Chrome, Firefox, Safari (latest 2 versions)
- [ ] Graceful degradation if WebSocket unavailable

### Developer Experience
- [ ] Hot reload for frontend development
- [ ] Clear WebSocket protocol documentation
- [ ] Error messages are actionable
- [ ] Debug logging available

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-18 | Web UI coexists with TUI | User wants both interfaces available |
| 2026-03-18 | Vanilla JS + Web Components | Zero build step, native browser APIs |
| 2026-03-18 | FastAPI + WebSocket | Native async, Python-only stack |
| 2026-03-18 | Local-only (no auth) | Tailscale handles network security |
| 2026-03-18 | Feature parity with TUI | User wants all TUI features |

---

## Open Questions

1. Should we implement session persistence in browser (localStorage) for offline draft messages?
2. Should we add a "mobile" layout breakpoint for phone usage?
3. Should we support multiple concurrent browser tabs (shared connection or separate sessions)?

---

## Related PRDs

- #94 - PyPiTUI CLI (current TUI implementation)
- #95 - TUI enhancements
- #97 - Command completion in TUI

---

## Bug Fixes Post-Milestone 5

### Issue 1: Commands Displayed as User Messages
**Problem**: When typing a command like `/new` or `/sessions`, the command text appears as a user message bubble in the chat before being executed. This creates confusing UX where the command looks like a message to the LLM.

**Expected Behavior**: Commands should either:
- Not appear in chat at all (silent execution), OR
- Appear as a system/notification message styled differently

**Root Cause**: In `main.js`, `sendMessageContent()` adds the content to the UI as a user message before checking if it's a command.

**Fix**: Move the user message creation after the command check, or render commands differently.

---

### Issue 2: Missing Streaming Throbber
**Problem**: When the LLM is generating a response, there's no visual indicator that work is happening. Users can't tell if the system is processing or stuck.

**Expected Behavior**: A throbber/loading indicator should appear:
- In the status bar (animated indicator)
- Next to the assistant message being generated
- Similar to TUI's throbber: `⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏`

**Implementation**: 
- CSS animation or JavaScript-based frame animation
- Display during `chat.started` → `chat.complete` period
- Pause when reasoning blocks are displayed (optional)

---

### Issue 3: Thinking Block Looks Like Code Block
**Problem**: The reasoning/thinking block uses similar styling to code blocks (dark background, monospace font, bordered container), making it hard to distinguish from actual code.

**Current Styling** (from `base.css`):
```css
.reasoning-section {
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 0.5rem;
}

.reasoning-content {
  background: #252525;
  font-size: 0.875rem;
  color: #888;
}
```

**Expected Behavior**: Distinct visual treatment that clearly signals "this is the model's thinking process, not output":
- Different background color (lighter/different hue)
- Italic text styling
- Border-left accent instead of full border
- Collapsed by default with clear "Thinking..." label
- Plus/minus toggle indicator (✓ already implemented)

**Suggested Styling**:
```css
.reasoning-section {
  background: transparent;
  border: none;
  border-left: 3px solid #666;
  border-radius: 0;
  margin: 0.5rem 0;
  padding: 0 0 0 0.75rem;
}

.reasoning-content {
  background: transparent;
  color: #666;
  font-style: italic;
  font-size: 0.875rem;
  padding: 0.5rem 0;
}
```

---

## Appendix: Web Component Lifecycle

```javascript
// Example Web Component structure
class ChatMessage extends HTMLElement {
  static observedAttributes = ['role', 'content'];
  
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }
  
  connectedCallback() {
    // Element added to DOM
    this.render();
  }
  
  attributeChangedCallback(name, oldValue, newValue) {
    // Attribute changed
    if (oldValue !== newValue) {
      this.render();
    }
  }
  
  render() {
    this.shadowRoot.innerHTML = `
      <style>${this.styles()}</style>
      <div class="message ${this.getAttribute('role')}">
        <div class="content">${this.parseMarkdown()}</div>
      </div>
    `;
  }
  
  styles() {
    return `
      :host { display: block; }
      .message { padding: 1rem; }
      .user { background: var(--color-user-bg); }
      .assistant { background: var(--color-assistant-bg); }
    `;
  }
}

customElements.define('chat-message', ChatMessage);
```
