# Alfred WebSocket Protocol

This document describes the WebSocket protocol used by Alfred's Web UI for real-time communication between the client and server.

## Overview

The WebSocket protocol enables bidirectional, real-time communication for:
- **Streaming chat responses** — Token-by-token delivery as the LLM generates
- **Tool execution** — Live tool call progress and output streaming
- **Session management** — Create, list, resume, and inspect sessions
- **Status updates** — Token usage, model info, and streaming state

## Connection

### Endpoint

```
ws://localhost:8080/ws
```

The WebSocket endpoint accepts connections at `/ws` on the Alfred Web UI server.

### Connection Lifecycle

1. **Client connects** to `/ws`
2. **Server accepts** connection and sends `connected` message
3. **Server loads** current session (if available) and sends `session.loaded`
4. **Bidirectional communication** begins
5. **Either party** can close the connection

### Initial Connection Example

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message.type, message.payload);
};

ws.onclose = () => {
  console.log('WebSocket disconnected');
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

## Message Format

All messages are JSON objects with the following structure:

```json
{
  "type": "message.type",
  "payload": { /* message-specific data */ }
}
```

### Common Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | `string` | Message type identifier (namespaced with dots) |
| `payload` | `object` | Message-specific data payload |

## Client → Server Messages

These messages are sent by the client (browser) to the server.

### `ping`

Keepalive ping to maintain connection and verify server responsiveness.

```json
{
  "type": "ping",
  "payload": {}
}
```

**Server Response:** `pong`

---

### `chat.send`

Send a chat message to Alfred. The server responds with a streaming sequence of `chat.started`, `chat.chunk`/`reasoning.chunk`, and `chat.complete` messages.

```json
{
  "type": "chat.send",
  "payload": {
    "content": "What is the weather today?"
  }
}
```

**Payload Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | `string` | Yes | The user's message content |

**Server Response Sequence:**
1. `chat.started` — Streaming begins
2. `status.update` — Initial status (streaming started)
3. `reasoning.chunk` (optional) — Reasoning tokens if model supports it
4. `chat.chunk` — Content tokens
5. `tool.start`/`tool.output`/`tool.end` (optional) — If tools are called
6. `status.update` — Final token counts
7. `chat.complete` — Streaming complete

**Error Response:** `chat.error`

---

### `chat.cancel`

Cancel the active assistant response for the current connection.

```json
{
  "type": "chat.cancel"
}
```

**Payload Fields:** None. This message has no payload.

**Server Response:** `chat.cancelled`

---

### `chat.edit`

Update the last completed user message and restart the conversation from that edited text.

```json
{
  "type": "chat.edit",
  "payload": {
    "messageId": "msg-123",
    "content": "Please rewrite this."
  }
}
```

**Payload Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messageId` | `string` | Yes | ID of the user message to update |
| `content` | `string` | Yes | Replacement message content |

**Server Response:** The server updates the session, removes the trailing assistant turn, and starts a new `chat.started` streaming sequence.

---

### `command.execute`

Execute a slash command. Commands are prefixed with `/` and control session management.

```json
{
  "type": "command.execute",
  "payload": {
    "command": "/new"
  }
}
```

**Available Commands:**

| Command | Description | Response |
|---------|-------------|----------|
| `/new` | Create a new session | `session.new` |
| `/sessions` | List recent sessions | `session.list` |
| `/session` | Show current session info | `session.info` |
| `/resume <id>` | Resume a specific session | `session.loaded` |
| `/context` | Show system context | `context.info` |

**Payload Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | `string` | Yes | The command string including `/` prefix |

**Error Response:** `chat.error`

## Server → Client Messages

These messages are sent by the server to the client.

### `connected`

Sent immediately upon successful WebSocket connection.

```json
{
  "type": "connected",
  "payload": {}
}
```

This message indicates the connection is ready for communication.

---

### `pong`

Response to a client `ping` message.

```json
{
  "type": "pong",
  "payload": {}
}
```

---

### `session.loaded`

Sent after connection to load the current or resumed session's messages.

```json
{
  "type": "session.loaded",
  "payload": {
    "sessionId": "550e8400-e29b-41d4-a716-446655440000",
    "messages": [
      {
        "id": "msg-123",
        "role": "user",
        "content": "Hello Alfred",
        "reasoningContent": ""
      },
      {
        "id": "msg-124",
        "role": "assistant",
        "content": "Hello! How can I help you today?",
        "reasoningContent": ""
      }
    ]
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `sessionId` | `string` | Unique session identifier (UUID) |
| `messages` | `array` | Array of message objects |

**Message Object:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Unique message identifier |
| `role` | `string` | One of: `user`, `assistant`, `system` |
| `content` | `string` | Message content |
| `reasoningContent` | `string` | Reasoning/thinking content (if any) |

---

### `session.new`

Sent after successfully creating a new session via `/new` command.

```json
{
  "type": "session.new",
  "payload": {
    "sessionId": "550e8400-e29b-41d4-a716-446655440001",
    "message": "New session created"
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `sessionId` | `string` | The new session's unique identifier |
| `message` | `string` | Human-readable confirmation message |

---

### `session.list`

Sent in response to `/sessions` command.

```json
{
  "type": "session.list",
  "payload": {
    "sessions": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "created": "2026-03-20T10:30:00",
        "messageCount": 42,
        "summary": "Discussion about Python async patterns"
      }
    ]
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `sessions` | `array` | Array of session summary objects |

**Session Summary Object:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Session identifier |
| `created` | `string` | ISO 8601 timestamp of session creation |
| `messageCount` | `number` | Number of messages in the session |
| `summary` | `string` | Auto-generated session summary |

---

### `session.info`

Sent in response to `/session` command.

```json
{
  "type": "session.info",
  "payload": {
    "sessionId": "550e8400-e29b-41d4-a716-446655440000",
    "messageCount": 42,
    "created": "2026-03-20T10:30:00"
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `sessionId` | `string` | Current session identifier |
| `messageCount` | `number` | Number of messages in current session |
| `created` | `string` | ISO 8601 timestamp of session creation |

---

### `context.info`

Sent in response to `/context` command.

```json
{
  "type": "context.info",
  "payload": {
    "cwd": "/home/user/projects/myapp",
    "files": ["README.md", "src/main.py", "pyproject.toml"],
    "systemInfo": {
      "platform": "linux",
      "python_version": "3.12.0"
    }
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `cwd` | `string` | Current working directory |
| `files` | `array` | List of files in current context |
| `systemInfo` | `object` | System information dictionary |

---

### `chat.started`

Sent when Alfred begins processing a chat message. This is the first message in the streaming sequence.

```json
{
  "type": "chat.started",
  "payload": {
    "messageId": "msg-550e8400-e29b-41d4-a716-446655440000",
    "role": "assistant"
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `messageId` | `string` | Unique identifier for this response message |
| `role` | `string` | Always `"assistant"` for AI responses |

The `messageId` is used to correlate all subsequent chunks and the completion message.

---

### `chat.chunk`

Streaming content chunk from the LLM response.

```json
{
  "type": "chat.chunk",
  "payload": {
    "messageId": "msg-550e8400-e29b-41d4-a716-446655440000",
    "content": "Hello! "
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `messageId` | `string` | Matches `chat.started` message ID |
| `content` | `string` | A fragment of the response text |

**Note:** Chunks may arrive rapidly. The client should buffer and concatenate them for display. Markdown rendering should be applied to the accumulated content.

---

### `reasoning.chunk`

Streaming reasoning/thinking content from models that support explicit reasoning (e.g., Kimi K2.5).

```json
{
  "type": "reasoning.chunk",
  "payload": {
    "messageId": "msg-550e8400-e29b-41d4-a716-446655440000",
    "content": "Let me analyze this step by step..."
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `messageId` | `string` | Matches `chat.started` message ID |
| `content` | `string` | A fragment of the reasoning text |

**Note:** Reasoning chunks are separate from content chunks. The UI may choose to display them differently (e.g., collapsed by default, different styling).

---

### `chat.complete`

Sent when the LLM has finished generating the complete response.

```json
{
  "type": "chat.complete",
  "payload": {
    "messageId": "msg-550e8400-e29b-41d4-a716-446655440000",
    "finalContent": "Hello! How can I help you today?",
    "usage": {
      "inputTokens": 12,
      "outputTokens": 8,
      "cacheReadTokens": 0,
      "reasoningTokens": 0
    }
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `messageId` | `string` | Matches `chat.started` message ID |
| `finalContent` | `string` | The complete accumulated response |
| `usage` | `object` | Token usage statistics |

**Usage Object:**

| Field | Type | Description |
|-------|------|-------------|
| `inputTokens` | `number` | Tokens in the input message |
| `outputTokens` | `number` | Tokens in the output response |
| `cacheReadTokens` | `number` | Tokens read from cache (if applicable) |
| `reasoningTokens` | `number` | Tokens used for reasoning (if applicable) |

---

### `chat.error`

Sent when an error occurs during chat processing.

```json
{
  "type": "chat.error",
  "payload": {
    "messageId": "msg-550e8400-e29b-41d4-a716-446655440000",
    "error": "Alfred instance not available"
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `messageId` | `string` | Message ID if available (may be null) |
| `error` | `string` | Human-readable error message |

Common error messages:
- `"Alfred instance not available"` — Server not properly initialized
- `"Message content cannot be empty"` — Empty or whitespace-only message
- `"Session ID required: /resume <session_id>"` — Missing argument for `/resume`

---

### `chat.cancelled`

Sent when the active assistant response has been canceled and the partial turn has been cleaned up.

```json
{
  "type": "chat.cancelled",
  "payload": {
    "messageId": "msg-550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `messageId` | `string` | The assistant message that was canceled |

---

### `status.update`

Sent periodically during streaming to report current status.

```json
{
  "type": "status.update",
  "payload": {
    "model": "kimi-k2-5",
    "contextTokens": 2048,
    "inputTokens": 12,
    "outputTokens": 8,
    "cacheReadTokens": 0,
    "reasoningTokens": 0,
    "queueLength": 0,
    "isStreaming": true
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `model` | `string` | Current model name (e.g., `"kimi-k2-5"`, `"claude-3-opus"`) |
| `contextTokens` | `number` | Total tokens in context window |
| `inputTokens` | `number` | Tokens in user input |
| `outputTokens` | `number` | Tokens generated so far |
| `cacheReadTokens` | `number` | Tokens read from cache |
| `reasoningTokens` | `number` | Tokens used for reasoning |
| `queueLength` | `number` | Number of queued messages |
| `isStreaming` | `boolean` | Whether LLM is currently streaming |

**Usage:** This message is used to update the status bar in the UI with real-time token counts and streaming state.

---

### `tool.start`

Sent when Alfred begins executing a tool.

```json
{
  "type": "tool.start",
  "payload": {
    "toolCallId": "call-550e8400-e29b-41d4-a716-446655440000",
    "toolName": "read",
    "arguments": {
      "path": "/home/user/projects/myapp/README.md"
    },
    "messageId": "msg-550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `toolCallId` | `string` | Unique identifier for this tool call |
| `toolName` | `string` | Name of the tool being executed |
| `arguments` | `object` | Arguments passed to the tool |
| `messageId` | `string` | Parent message ID |

---

### `tool.output`

Streaming output from a tool during execution.

```json
{
  "type": "tool.output",
  "payload": {
    "toolCallId": "call-550e8400-e29b-41d4-a716-446655440000",
    "chunk": "File contents chunk..."
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `toolCallId` | `string` | Matches `tool.start` call ID |
| `chunk` | `string` | A fragment of tool output |

---

### `tool.end`

Sent when tool execution completes.

```json
{
  "type": "tool.end",
  "payload": {
    "toolCallId": "call-550e8400-e29b-41d4-a716-446655440000",
    "success": true,
    "output": "Complete tool output"
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `toolCallId` | `string` | Matches `tool.start` call ID |
| `success` | `boolean` | Whether tool execution succeeded |
| `output` | `string\|null` | Final output (null if error) |

---

### `error`

General protocol error (not chat-specific).

```json
{
  "type": "error",
  "payload": {
    "error": "Invalid JSON"
  }
}
```

**Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `error` | `string` | Error description |

Common errors:
- `"Invalid JSON"` — Malformed message received
- `"Unknown message type: <type>"` — Unrecognized message type

## Message Flow Examples

### Simple Chat Flow

```
Client                                      Server
  |                                           |
  |----------- chat.send {content: "Hi"} ----->|
  |                                           |
  |<-- chat.started {messageId: "msg-1"} ------|
  |<-- status.update {isStreaming: true} -----|
  |<-- chat.chunk {content: "Hello"} ---------|
  |<-- chat.chunk {content: "!"} -------------|
  |<-- chat.chunk {content: " How"} ----------|
  |<-- chat.chunk {content: " can"} ----------|
  |<-- chat.chunk {content: " I"} ------------|
  |<-- chat.chunk {content: " help?"} --------|
  |<-- status.update {isStreaming: false} ---|
  |<-- chat.complete {finalContent: "..."} ---|
```

### Streaming Control Flow

```
Client                                      Server
  |                                           |
  |--- chat.send {content: "Draft this"} --->|
  |<-- chat.started {messageId: "msg-1"} ----|
  |<-- chat.chunk {content: "Draft"} --------|
  |--- chat.cancel -------------------------->|
  |<-- chat.cancelled {messageId: "msg-1"} --|
  |                                           |
  |--- chat.edit {messageId: "msg-0",        |
  |              content: "Rewrite this"} --->|
  |<-- chat.started {messageId: "msg-2"} ----|
```

### Chat with Tool Execution

```
Client                                      Server
  |                                           |
  |--- chat.send {content: "Read README"} --->|
  |                                           |
  |<-- chat.started {messageId: "msg-1"} -----|
  |<-- tool.start {toolName: "read"} --------|
  |<-- tool.output {chunk: "# MyApp..."} ----|
  |<-- tool.end {success: true} -------------|
  |<-- chat.chunk {content: "The README..."} |
  |<-- chat.complete {finalContent: "..."} ---|
```

### Session Management Flow

```
Client                                      Server
  |                                           |
  |--- command.execute {command: "/new"} ---->|
  |<-- session.new {sessionId: "..."} --------|
  |                                           |
  |--- command.execute {command: "/sessions"}>|
  |<-- session.list {sessions: [...]} -------|
  |                                           |
  |-- command.execute {command: "/resume X"}->|
  |<-- session.loaded {messages: [...]} -----|
```

## Error Handling

### Client-Side Errors

The client should handle these scenarios:

1. **Connection failure** — Retry with exponential backoff
2. **Unexpected disconnection** — Attempt to reconnect, restore session
3. **Invalid message format** — Log error, continue operating
4. **Timeout** — Send `ping`, expect `pong` within 30 seconds

### Server-Side Errors

The server handles these scenarios:

1. **Invalid JSON** — Returns `error` message, keeps connection open
2. **Unknown message type** — Returns `echo` or `error`, keeps connection open
3. **Missing Alfred instance** — Returns `chat.error`, keeps connection open
4. **Chat errors** — Returns `chat.error`, keeps connection open

All errors are recoverable; the connection remains open for subsequent messages.

## Implementation Notes

### Reconnection Strategy

When implementing reconnection logic:

1. Detect disconnection via `onclose` or `onerror` handlers
2. Wait 1 second before first retry (exponential backoff: 1s, 2s, 4s, 8s, max 30s)
3. Reconnect and re-establish session state
4. Replay any pending messages from client-side queue

### Message Buffering

For streaming display:

1. Buffer `chat.chunk` messages in a string builder
2. Render markdown from accumulated content periodically (throttle to 30fps)
3. Handle `reasoning.chunk` separately with distinct UI treatment

### Token Counting

Token counts in `status.update` are approximate (4 characters ≈ 1 token for English text). Exact counts are provided in `chat.complete`.

## Debugging and Troubleshooting

### Enabling Debug Logging

The Web UI supports structured debug logging to help diagnose connection issues. Enable debug mode by starting the Web UI with the `--log debug` flag:

```bash
# Enable Web UI client debug logs only
alfred webui --log debug

# Enable both Alfred server logs and Web UI client logs
alfred --log debug webui --log debug
```

**Note:** The root `--log` flag (before `webui`) controls server-side logging. The `webui --log` flag (after `webui`) controls browser/client debug instrumentation.

### Understanding `[websocket]` Logs

When debug logging is enabled, the browser console shows structured lifecycle events with the `[websocket]` prefix:

| Log Message | Description |
|-------------|-------------|
| `[websocket] Connecting to: ws://...` | Connection attempt initiated |
| `[websocket] WebSocket connected` | Connection established successfully |
| `[websocket] WebSocket closed: code=..., reason="...", clean=...` | Connection closed with details |
| `[websocket] Reconnecting in ${delay}ms (attempt ${n}/${max})` | Reconnect scheduled with backoff |
| `[websocket] Flushing ${n} queued message(s)` | Queued messages being sent |
| `[websocket] Pong received, latency: ${ms}ms` | Keepalive round-trip time |

### Common Connection Scenarios

**Normal startup sequence:**
```
[websocket] Connecting to: ws://localhost:8080/ws
[websocket] WebSocket connected
[websocket] Pong received, latency: 45ms
```

**Transient disconnect and recovery:**
```
[websocket] WebSocket closed: code=1006, reason="", clean=false
[websocket] Reconnecting in 1000ms (attempt 1/10)
[websocket] Connecting to: ws://localhost:8080/ws
[websocket] WebSocket connected
[websocket] Pong received, latency: 52ms
```

**Message queue during disconnect:**
```
[websocket] Queueing message until connection is ready
[websocket] Reconnecting in 2000ms (attempt 2/10)
[websocket] Connecting to: ws://localhost:8080/ws
[websocket] WebSocket connected
[websocket] Flushing 1 queued message(s)
```

### Health Endpoint vs Live State

The `/health` endpoint is for ops/readiness checks only. Do not use it for live UI state:

```bash
# Use for monitoring/ops (returns 200 when server is ready)
curl http://localhost:8080/health

# Do NOT poll for live connection status — use WebSocket state instead
```

The Web UI derives all live connection status from the WebSocket itself:
- Connection state: WebSocket `readyState`
- Daemon status: `daemon.status` message payload
- Reconnect state: Client-side reconnect attempt counter

### Troubleshooting Guide

**Connection immediately closes:**
- Check server is running: `curl http://localhost:8080/health`
- Verify port is correct in WebSocket URL
- Check browser console for `[websocket]` connection logs

**Frequent reconnects:**
- Look for `[websocket] WebSocket closed` log — check close code
- Code `1006` (abnormal closure): Often proxy/firewall timeout
- Code `1001` (going away): Page refresh or navigation
- Check `[websocket] Pong received` latency — high latency may trigger timeouts

**Messages not sending:**
- Verify `[websocket] WebSocket connected` appears in logs
- Check for `[websocket] Queueing message` — indicates disconnect
- Look for `[websocket] Flushing` — queued messages should send on reconnect

**No debug logs appearing:**
- Confirm `alfred webui --log debug` was used
- Check browser console filter is not hiding `[websocket]` prefixed logs
- Verify `window.__ALFRED_WEBUI_CONFIG__.debug` is `true` in console

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.2 | 2026-03-27 | Added debugging and troubleshooting section |
| 0.1.1 | 2026-03-23 | Added `chat.cancel`, `chat.edit`, `chat.cancelled`, and streaming control flow examples |
| 0.1.0 | 2026-03-20 | Initial protocol specification |

## See Also

- [Web UI Architecture](architecture.md) — System design and components
- [API Reference](API.md) — Python module documentation
- [Deployment Guide](DEPLOYMENT.md) — Production setup instructions
