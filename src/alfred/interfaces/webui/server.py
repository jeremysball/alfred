"""FastAPI server for Alfred Web UI."""

import asyncio
import json
import logging
import uuid
from collections import Counter
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, WebSocket
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect

from alfred.agent import ToolEvent
from alfred.interfaces.webui.contracts import WebUIAlfred, WebUISessionManager
from alfred.interfaces.webui.daemon_status import build_daemon_status_snapshot, build_health_payload
from alfred.observability import event_message

logger = logging.getLogger(__name__)


def _emit_webui_debug(event: str, **fields: object) -> None:
    """Emit a debug-only diagnostic line through the Web UI server surface."""
    logger.debug(event_message(event, **fields))


StatusField = str | int | bool | None
CHUNK_BATCH_FLUSH_INTERVAL_SECONDS = 0.05
CHUNK_BATCH_MAX_CHARS = 256


@dataclass
class _WebSocketDebugStats:
    """Debug-only stats for diagnosing websocket disconnects on long turns."""

    connection_id: str
    enabled: bool = False
    outgoing_counts: Counter[str] = field(default_factory=Counter)
    total_bytes_sent: int = 0
    max_frame_bytes: int = 0
    max_frame_type: str = ""
    last_outgoing_type: str = ""
    last_outgoing_phase: str = ""
    last_incoming_type: str = ""
    largest_incoming_bytes: int = 0
    incoming_counts: Counter[str] = field(default_factory=Counter)
    control_messages_during_stream: Counter[str] = field(default_factory=Counter)
    stream_duration_ms_total: int = 0
    stream_started_at: float | None = None
    pings_during_stream: int = 0
    pongs_during_stream: int = 0
    content_batches_sent: int = 0
    content_chars_sent: int = 0
    reasoning_batches_sent: int = 0
    reasoning_chars_sent: int = 0
    tool_output_batches_sent: int = 0
    tool_output_chars_sent: int = 0

    def start_stream(self) -> None:
        if not self.enabled:
            return
        self.stream_started_at = asyncio.get_running_loop().time()

    def finish_stream(self) -> None:
        if not self.enabled or self.stream_started_at is None:
            return
        elapsed_ms = int((asyncio.get_running_loop().time() - self.stream_started_at) * 1000)
        self.stream_duration_ms_total += max(elapsed_ms, 0)
        self.stream_started_at = None

    def stream_is_active(self) -> bool:
        return self.enabled and self.stream_started_at is not None

    def record_control_message_during_stream(self, message_type: str) -> None:
        if not self.stream_is_active():
            return
        self.control_messages_during_stream[message_type] += 1
        if message_type == "ping":
            self.pings_during_stream += 1

    def record_incoming(self, message_type: str, raw_text: str) -> None:
        if not self.enabled:
            return
        self.last_incoming_type = message_type
        self.incoming_counts[message_type] += 1
        incoming_bytes = len(raw_text.encode("utf-8"))
        if incoming_bytes > self.largest_incoming_bytes:
            self.largest_incoming_bytes = incoming_bytes

    def _record_stream_payload(self, message_type: str, payload: dict[str, object]) -> None:
        if message_type == "chat.chunk":
            content = payload.get("content")
            if isinstance(content, str):
                self.content_batches_sent += 1
                self.content_chars_sent += len(content)
        elif message_type == "reasoning.chunk":
            content = payload.get("content")
            if isinstance(content, str):
                self.reasoning_batches_sent += 1
                self.reasoning_chars_sent += len(content)
        elif message_type == "tool.output":
            chunk = payload.get("chunk")
            if isinstance(chunk, str):
                self.tool_output_batches_sent += 1
                self.tool_output_chars_sent += len(chunk)

    def record_outgoing(self, message: dict[str, object], phase: str | None = None) -> None:
        if not self.enabled:
            return
        message_type = str(message.get("type", "unknown"))
        frame_bytes = len(json.dumps(message).encode("utf-8"))
        self.last_outgoing_type = message_type
        self.last_outgoing_phase = phase or message_type
        self.outgoing_counts[message_type] += 1
        self.total_bytes_sent += frame_bytes
        if frame_bytes > self.max_frame_bytes:
            self.max_frame_bytes = frame_bytes
            self.max_frame_type = message_type

        payload = message.get("payload")
        if isinstance(payload, dict):
            self._record_stream_payload(message_type, payload)

        if message_type == "pong" and self.stream_is_active():
            self.pongs_during_stream += 1

    def merge(self, other: "_WebSocketDebugStats") -> None:
        if not self.enabled or not other.enabled:
            return
        self.outgoing_counts.update(other.outgoing_counts)
        self.incoming_counts.update(other.incoming_counts)
        self.control_messages_during_stream.update(other.control_messages_during_stream)
        self.total_bytes_sent += other.total_bytes_sent
        self.stream_duration_ms_total += other.stream_duration_ms_total
        self.pings_during_stream += other.pings_during_stream
        self.pongs_during_stream += other.pongs_during_stream
        self.content_batches_sent += other.content_batches_sent
        self.content_chars_sent += other.content_chars_sent
        self.reasoning_batches_sent += other.reasoning_batches_sent
        self.reasoning_chars_sent += other.reasoning_chars_sent
        self.tool_output_batches_sent += other.tool_output_batches_sent
        self.tool_output_chars_sent += other.tool_output_chars_sent
        if other.max_frame_bytes > self.max_frame_bytes:
            self.max_frame_bytes = other.max_frame_bytes
            self.max_frame_type = other.max_frame_type
        self.last_incoming_type = other.last_incoming_type or self.last_incoming_type
        self.last_outgoing_type = other.last_outgoing_type or self.last_outgoing_type
        self.last_outgoing_phase = other.last_outgoing_phase or self.last_outgoing_phase
        self.largest_incoming_bytes = max(self.largest_incoming_bytes, other.largest_incoming_bytes)

    def _format_counts(self, counts: Counter[str]) -> str:
        return ",".join(f"{message_type}:{count}" for message_type, count in sorted(counts.items())) or "none"

    def summary(self) -> str:
        return (
            f"connection_id={self.connection_id} "
            f"last_incoming={self.last_incoming_type or 'none'} "
            f"last_outgoing={self.last_outgoing_type or 'none'} "
            f"last_phase={self.last_outgoing_phase or 'none'} "
            f"incoming_counts={self._format_counts(self.incoming_counts)} "
            f"outgoing_counts={self._format_counts(self.outgoing_counts)} "
            f"control_during_stream={self._format_counts(self.control_messages_during_stream)} "
            f"pings_during_stream={self.pings_during_stream} "
            f"pongs_during_stream={self.pongs_during_stream} "
            f"stream_duration_ms={self.stream_duration_ms_total} "
            f"content_batches_sent={self.content_batches_sent} "
            f"content_chars_sent={self.content_chars_sent} "
            f"reasoning_batches_sent={self.reasoning_batches_sent} "
            f"reasoning_chars_sent={self.reasoning_chars_sent} "
            f"tool_output_batches_sent={self.tool_output_batches_sent} "
            f"tool_output_chars_sent={self.tool_output_chars_sent} "
            f"largest_incoming_bytes={self.largest_incoming_bytes} "
            f"total_bytes_sent={self.total_bytes_sent} "
            f"max_frame_bytes={self.max_frame_bytes} "
            f"max_frame_type={self.max_frame_type or 'none'}"
        )


@dataclass
class _WebSocketConnectionState:
    """Mutable per-connection state shared by the receive loop and stream task."""

    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    active_chat_task: asyncio.Task[None] | None = None
    active_chat_message_id: str | None = None
    cancel_requested_message_id: str | None = None
    active_turn_debug_stats: _WebSocketDebugStats | None = None

    def has_active_chat(self) -> bool:
        task = self.active_chat_task
        return task is not None and not task.done()

    def set_active_chat(self, task: asyncio.Task[None], message_id: str) -> None:
        self.active_chat_task = task
        self.active_chat_message_id = message_id
        self.cancel_requested_message_id = None

    def clear_active_chat(self) -> None:
        self.active_chat_task = None
        self.active_chat_message_id = None
        self.cancel_requested_message_id = None

    def request_chat_cancel(self) -> str | None:
        task = self.active_chat_task
        message_id = self.active_chat_message_id
        if task is None or task.done() or message_id is None:
            return None
        self.cancel_requested_message_id = message_id
        return message_id

    def start_turn(self, debug_stats: _WebSocketDebugStats) -> None:
        self.active_turn_debug_stats = debug_stats

    def finish_turn(self, debug_stats: _WebSocketDebugStats) -> None:
        if self.active_turn_debug_stats is debug_stats:
            self.active_turn_debug_stats = None

    def record_control_message_during_stream(self, message_type: str) -> None:
        active_turn = self.active_turn_debug_stats
        if active_turn is None:
            return
        active_turn.record_control_message_during_stream(message_type)


class _ChunkBatcher:
    """Batch websocket stream chunks to avoid flooding the client."""

    def __init__(
        self,
        websocket: WebSocket,
        message_type: str,
        payload_key: str,
        extra_payload: dict[str, object] | None = None,
        debug_stats: _WebSocketDebugStats | None = None,
        send_lock: asyncio.Lock | None = None,
    ) -> None:
        self._websocket = websocket
        self._message_type = message_type
        self._payload_key = payload_key
        self._extra_payload = extra_payload or {}
        self._debug_stats = debug_stats
        self._send_lock = send_lock
        self._buffer = ""
        self._buffer_started_at: float | None = None
        self._lock = asyncio.Lock()

    async def add(self, content: str) -> None:
        """Append content and flush immediately if the size threshold is hit."""
        async with self._lock:
            if not self._buffer:
                self._buffer_started_at = asyncio.get_running_loop().time()
            self._buffer += content
            should_flush = len(self._buffer) >= CHUNK_BATCH_MAX_CHARS

        if should_flush:
            await self.flush(force=True)

    async def flush_if_due(self) -> None:
        """Flush buffered content once the time threshold has elapsed."""
        async with self._lock:
            if not self._buffer or self._buffer_started_at is None:
                return
            if asyncio.get_running_loop().time() - self._buffer_started_at < CHUNK_BATCH_FLUSH_INTERVAL_SECONDS:
                return

        await self.flush(force=True)

    async def flush(self, force: bool = False) -> None:
        """Flush the current buffer to the websocket."""
        async with self._lock:
            if not self._buffer:
                return
            if not force and len(self._buffer) < CHUNK_BATCH_MAX_CHARS:
                return
            content = self._buffer
            self._buffer = ""
            self._buffer_started_at = None

        payload = dict(self._extra_payload)
        payload[self._payload_key] = content

        await _send_json(
            self._websocket,
            {
                "type": self._message_type,
                "payload": payload,
            },
            phase=f"batch:{self._message_type}",
            debug_stats=self._debug_stats,
            send_lock=self._send_lock,
        )


class _BroadcastChunkBatcher:
    """Batch websocket stream chunks and broadcast to all active connections."""

    def __init__(
        self,
        message_type: str,
        payload_key: str,
        extra_payload: dict[str, object] | None = None,
        debug_stats: _WebSocketDebugStats | None = None,
    ) -> None:
        self._message_type = message_type
        self._payload_key = payload_key
        self._extra_payload = extra_payload or {}
        self._debug_stats = debug_stats
        self._buffer = ""
        self._buffer_started_at: float | None = None
        self._lock = asyncio.Lock()

    async def add(self, content: str) -> None:
        """Append content and flush immediately if the size threshold is hit."""
        async with self._lock:
            if not self._buffer:
                self._buffer_started_at = asyncio.get_running_loop().time()
            self._buffer += content
            should_flush = len(self._buffer) >= CHUNK_BATCH_MAX_CHARS

        if should_flush:
            await self.flush(force=True)

    async def flush_if_due(self) -> None:
        """Flush buffered content once the time threshold has elapsed."""
        async with self._lock:
            if not self._buffer or self._buffer_started_at is None:
                return
            if asyncio.get_running_loop().time() - self._buffer_started_at < CHUNK_BATCH_FLUSH_INTERVAL_SECONDS:
                return

        await self.flush(force=True)

    async def flush(self, force: bool = False) -> None:
        """Flush the current buffer to all active websockets."""
        async with self._lock:
            if not self._buffer:
                return
            if not force and len(self._buffer) < CHUNK_BATCH_MAX_CHARS:
                return
            content = self._buffer
            self._buffer = ""
            self._buffer_started_at = None

        payload = dict(self._extra_payload)
        payload[self._payload_key] = content

        await _broadcast_json(
            {
                "type": self._message_type,
                "payload": payload,
            },
            phase=f"batch:{self._message_type}",
            debug_stats=self._debug_stats,
        )


async def _send_json(
    websocket: WebSocket,
    message: dict[str, object],
    *,
    phase: str | None = None,
    debug_stats: _WebSocketDebugStats | None = None,
    send_lock: asyncio.Lock | None = None,
) -> bool:
    """Send a websocket JSON message with optional debug instrumentation.

    Returns True if sent successfully, False if client disconnected.
    """
    if debug_stats is not None:
        debug_stats.record_outgoing(message, phase=phase)
    try:
        if send_lock is None:
            await websocket.send_json(message)
        else:
            async with send_lock:
                await websocket.send_json(message)
        return True
    except WebSocketDisconnect:
        # Client disconnected - don't raise, just return False
        # This allows background tasks to continue without crashing
        return False
    except RuntimeError as e:
        # WebSocket already closed (e.g., websocket.close() was called)
        # ASGI raises RuntimeError: "Unexpected ASGI message 'websocket.send'..."
        if "websocket.send" in str(e) or "websocket.close" in str(e):
            return False
        raise


async def _broadcast_json(
    message: dict[str, object],
    *,
    phase: str | None = None,
    debug_stats: _WebSocketDebugStats | None = None,
) -> None:
    """Broadcast a message to all active WebSocket connections.

    Used for streaming chunks so new clients can receive ongoing streams.
    """
    if not _active_connections:
        return

    # Send to all active connections
    disconnected: list[WebSocket] = []
    for ws in list(_active_connections):
        try:
            await ws.send_json(message)
        except WebSocketDisconnect:
            disconnected.append(ws)
        except Exception:
            disconnected.append(ws)

    # Clean up disconnected clients
    for ws in disconnected:
        _active_connections.discard(ws)


async def _send_daemon_status(
    websocket: WebSocket,
    alfred_instance: WebUIAlfred | None,
    *,
    startup_error: str | None = None,
    debug_stats: _WebSocketDebugStats | None = None,
    phase: str | None = None,
    send_lock: asyncio.Lock | None = None,
) -> None:
    """Send the daemon.status message to the client."""
    await _send_json(
        websocket,
        {
            "type": "daemon.status",
            "payload": build_daemon_status_snapshot(
                alfred_instance,
                startup_error=startup_error,
            ),
        },
        phase=phase or "daemon.status",
        debug_stats=debug_stats,
        send_lock=send_lock,
    )


def _get_bootstrap_startup_error(app_state: object | None) -> str | None:
    """Return the Web UI bootstrap error if startup failed."""
    if app_state is None:
        return None

    bootstrap_result = getattr(app_state, "webui_bootstrap_result", None)
    if bootstrap_result is None:
        return None

    startup_error = getattr(bootstrap_result, "startup_error", None)
    return str(startup_error) if startup_error is not None else None


# Module-level set to track active WebSocket connections
_active_connections: set[WebSocket] = set()


async def _register_connection(websocket: WebSocket) -> None:
    """Register an active WebSocket connection."""
    _active_connections.add(websocket)


async def _unregister_connection(websocket: WebSocket) -> None:
    """Unregister a WebSocket connection."""
    _active_connections.discard(websocket)


async def _close_all_connections() -> None:
    """Close all active WebSocket connections."""
    for ws in list(_active_connections):
        with suppress(Exception):
            await ws.close()
        _active_connections.discard(ws)


def _serialize_tool_call(tool_call: object) -> dict[str, object]:
    """Serialize a persisted tool call for WebSocket transport."""
    arguments = getattr(tool_call, "arguments", {})
    if not isinstance(arguments, dict):
        arguments = {}

    return {
        "toolCallId": str(getattr(tool_call, "tool_call_id", "")),
        "toolName": str(getattr(tool_call, "tool_name", "")),
        "arguments": arguments,
        "output": str(getattr(tool_call, "output", "")),
        "status": str(getattr(tool_call, "status", "success")),
        "insertPosition": int(getattr(tool_call, "insert_position", 0)),
        "sequence": int(getattr(tool_call, "sequence", 0)),
    }


def _serialize_message(message: object) -> dict[str, object]:
    """Serialize a session message for WebSocket transport."""
    role = getattr(message, "role", "")
    role_value = role.value if hasattr(role, "value") else str(role)
    timestamp = getattr(message, "timestamp", None)
    message_id = getattr(message, "id", None)
    # Generate UUID if missing (backward compatibility)
    if not message_id:
        message_id = str(uuid.uuid4())
    payload: dict[str, object] = {
        "id": str(message_id),
        "role": role_value,
        "content": str(getattr(message, "content", "")),
        "timestamp": (timestamp.isoformat() if isinstance(timestamp, datetime) else datetime.now(UTC).isoformat()),
        "reasoningContent": str(getattr(message, "reasoning_content", "")),
        "streaming": bool(getattr(message, "streaming", False)),
    }

    tool_calls = getattr(message, "tool_calls", None)
    if isinstance(tool_calls, (list, tuple)) and tool_calls:
        payload["toolCalls"] = [_serialize_tool_call(tool_call) for tool_call in tool_calls]

    return payload


def _serialize_session_messages(session: object) -> list[dict[str, object]]:
    """Serialize all messages from a session."""
    messages = getattr(session, "messages", [])
    if not isinstance(messages, (list, tuple)):
        return []

    return [_serialize_message(message) for message in messages]


def _session_identifier(session: object | None) -> str:
    """Get a stable string session identifier from a session-like object."""
    if session is None:
        return ""

    meta = getattr(session, "meta", None)
    session_id = getattr(meta, "session_id", getattr(session, "session_id", ""))
    return str(session_id)


def _coerce_int(value: object, default: int = 0) -> int:
    """Safely coerce a value to int for JSON payloads."""
    try:
        return int(cast(int | str | float | bytes, value))
    except (TypeError, ValueError):
        return default


def _get_session_manager(alfred_instance: WebUIAlfred | None) -> WebUISessionManager | None:
    """Return the core session manager when available."""
    if alfred_instance is None:
        return None

    return alfred_instance.core.session_manager


async def _call_async_method(target: object | None, method_names: tuple[str, ...], *args: object) -> object:
    """Call the first available async method from a target or raise if none exist."""
    if target is None:
        raise AttributeError("Target not available")

    for method_name in method_names:
        method = getattr(target, method_name, None)
        if callable(method):
            return await method(*args)

    raise AttributeError(f"Missing async method(s): {', '.join(method_names)}")


async def _create_session(alfred_instance: WebUIAlfred) -> object:
    """Create a new session using the modern Alfred API."""
    session_manager = _get_session_manager(alfred_instance)
    if session_manager is None:
        raise AttributeError("Missing session manager")
    return await _call_async_method(session_manager, ("new_session_async",))


async def _resume_session(alfred_instance: WebUIAlfred, session_id: str) -> object:
    """Resume a session using the modern Alfred API."""
    session_manager = _get_session_manager(alfred_instance)
    if session_manager is None:
        raise AttributeError("Missing session manager")
    return await _call_async_method(session_manager, ("resume_session_async",), session_id)


async def _list_sessions(alfred_instance: WebUIAlfred) -> list[object]:
    """List sessions using the modern Alfred API."""
    session_manager = _get_session_manager(alfred_instance)
    if session_manager is None:
        raise AttributeError("Missing session manager")
    sessions = await _call_async_method(session_manager, ("list_sessions_async",))
    if isinstance(sessions, list):
        return sessions
    if isinstance(sessions, tuple):
        return list(sessions)
    return list(cast(Iterable[object], sessions)) if sessions is not None else []


def _get_current_session(alfred_instance: WebUIAlfred | None) -> object | None:
    """Return the current session from the modern API."""
    session_manager = _get_session_manager(alfred_instance)
    if session_manager is None:
        return None

    getter = getattr(session_manager, "get_current_cli_session", None)
    if callable(getter):
        return cast(object | None, getter())
    return None


def _reset_token_tracker(alfred_instance: object | None) -> None:
    """Reset token tracking when the instance exposes a tracker."""
    if alfred_instance is None:
        return

    token_tracker = getattr(alfred_instance, "token_tracker", None)
    reset = getattr(token_tracker, "reset", None)
    if callable(reset):
        reset()


def _sync_token_tracker_from_session(alfred_instance: object | None, session_id: str | None = None) -> None:
    """Synchronize token tracking when the instance exposes the helper."""
    if alfred_instance is None:
        return

    sync = getattr(alfred_instance, "sync_token_tracker_from_session", None)
    if not callable(sync):
        return

    try:
        if session_id is None:
            sync()
        else:
            sync(session_id)
    except TypeError:
        sync()


def _build_context_payload(context_data: dict[str, object]) -> dict[str, object]:
    """Convert shared context display data to WebSocket-friendly camelCase."""
    system_prompt = cast(dict[str, object], context_data["system_prompt"])

    return {
        "systemPrompt": {
            "sections": system_prompt["sections"],
            "totalTokens": system_prompt["total_tokens"],
        },
        "blockedContextFiles": context_data.get("blocked_context_files", []),
        "warnings": context_data.get("warnings", []),
        "memories": context_data["memories"],
        "sessionHistory": context_data["session_history"],
        "toolCalls": context_data["tool_calls"],
        "totalTokens": context_data["total_tokens"],
    }


async def _load_current_session(
    websocket: WebSocket,
    alfred_instance: WebUIAlfred,
    debug_stats: _WebSocketDebugStats | None = None,
    send_lock: asyncio.Lock | None = None,
) -> None:
    """Load and send current session messages on connection.

    Args:
        websocket: The WebSocket connection
        alfred_instance: The Alfred instance
    """
    try:
        session = _get_current_session(alfred_instance)
        if session is None:
            session_manager = _get_session_manager(alfred_instance)
            starter = getattr(session_manager, "start_session", None)
            if callable(starter):
                session = starter()

        _sync_token_tracker_from_session(alfred_instance)

        if session is None:
            return

        await _send_json(
            websocket,
            {
                "type": "session.loaded",
                "payload": {
                    "sessionId": _session_identifier(session),
                    "messages": _serialize_session_messages(session),
                },
            },
            phase="session.loaded",
            debug_stats=debug_stats,
            send_lock=send_lock,
        )
    except Exception as e:
        # Silently ignore - session loading is optional
        print(f"Failed to load session: {e}")


async def _send_status_update(
    websocket: WebSocket,
    alfred_instance: WebUIAlfred | None,
    extra_status: dict[str, StatusField] | None = None,
    debug_stats: _WebSocketDebugStats | None = None,
    phase: str | None = None,
    send_lock: asyncio.Lock | None = None,
) -> None:
    """Send current status to the client."""
    status: dict[str, StatusField] = {
        "model": "",
        "contextTokens": 0,
        "inputTokens": 0,
        "outputTokens": 0,
        "cacheReadTokens": 0,
        "reasoningTokens": 0,
        "queueLength": 0,
        "isStreaming": False,
    }

    if alfred_instance is not None:
        token_tracker = getattr(alfred_instance, "token_tracker", None)
        usage = getattr(token_tracker, "usage", None)
        status.update(
            {
                "model": str(getattr(alfred_instance, "model_name", "")),
                "contextTokens": _coerce_int(getattr(token_tracker, "context_tokens", 0)),
                "inputTokens": _coerce_int(getattr(usage, "input_tokens", 0)),
                "outputTokens": _coerce_int(getattr(usage, "output_tokens", 0)),
                "cacheReadTokens": _coerce_int(getattr(usage, "cache_read_tokens", 0)),
                "reasoningTokens": _coerce_int(getattr(usage, "reasoning_tokens", 0)),
            }
        )

    if extra_status:
        status.update(extra_status)

    await _send_json(
        websocket,
        {
            "type": "status.update",
            "payload": status,
        },
        phase=phase or "status.update",
        debug_stats=debug_stats,
        send_lock=send_lock,
    )


def _find_last_user_message(session: object | None) -> object | None:
    """Return the last user message from a session-like object."""
    if session is None:
        return None

    messages = getattr(session, "messages", [])
    if not isinstance(messages, (list, tuple)):
        return None

    for message in reversed(messages):
        role = getattr(message, "role", "")
        role_value = role.value if hasattr(role, "value") else str(role)
        if role_value == "user":
            return cast(object, message)

    return None


async def _cleanup_cancelled_turn(
    alfred_instance: WebUIAlfred,
    message_id: str,
) -> None:
    """Remove the persisted partial assistant message for a canceled turn."""
    session_manager = _get_session_manager(alfred_instance)
    if session_manager is None:
        return

    session = _get_current_session(alfred_instance)
    if session is None:
        return

    messages = getattr(session, "messages", [])
    if not isinstance(messages, (list, tuple)) or not messages:
        return

    last_message = messages[-1]
    last_role = getattr(last_message, "role", "")
    last_role_value = last_role.value if hasattr(last_role, "value") else str(last_role)
    last_message_id = str(getattr(last_message, "id", "") or "")

    if last_role_value != "assistant" or last_message_id != message_id:
        return

    user_message = _find_last_user_message(session)
    if user_message is None:
        return

    user_message_id = str(getattr(user_message, "id", "") or "")
    if not user_message_id:
        return

    truncate_after_message_async = getattr(session_manager, "truncate_after_message_async", None)
    if not callable(truncate_after_message_async):
        return

    await truncate_after_message_async(user_message_id, session_id=_session_identifier(session))
    _sync_token_tracker_from_session(alfred_instance, _session_identifier(session))


async def _handle_chat_message(
    websocket: WebSocket,
    alfred_instance: WebUIAlfred,
    content: str,
    connection_state: _WebSocketConnectionState | None = None,
    debug_stats: _WebSocketDebugStats | None = None,
    message_id: str | None = None,
    reuse_user_message: bool = False,
) -> None:
    """Handle a chat message by streaming through Alfred.

    Args:
        websocket: The WebSocket connection
        alfred_instance: The Alfred instance
        content: The user message content
    """
    from alfred.agent import ToolEnd, ToolOutput, ToolStart

    if connection_state is None:
        connection_state = _WebSocketConnectionState()

    message_id = message_id or str(uuid.uuid4())
    connection_debug_stats = debug_stats
    turn_debug_stats = _WebSocketDebugStats(
        connection_id=message_id,
        enabled=bool(connection_debug_stats.enabled if connection_debug_stats is not None else False),
    )
    debug_stats = turn_debug_stats
    connection_state.start_turn(turn_debug_stats)
    turn_debug_stats.start_stream()
    turn_phase = "chat.cancelled"

    tool_event_lock = asyncio.Lock()
    pending_tool_tasks: set[asyncio.Task[None]] = set()
    tool_output_batchers: dict[str, _ChunkBatcher] = {}

    async def _handle_tool_event(event: "ToolEvent") -> None:
        async with tool_event_lock:
            if isinstance(event, ToolStart):
                await _send_json(
                    websocket,
                    {
                        "type": "tool.start",
                        "payload": {
                            "toolCallId": event.tool_call_id,
                            "toolName": event.tool_name,
                            "arguments": event.arguments,
                            "messageId": message_id,
                        },
                    },
                    phase="tool.start",
                    debug_stats=debug_stats,
                    send_lock=connection_state.send_lock,
                )
            elif isinstance(event, ToolOutput):
                batcher = tool_output_batchers.setdefault(
                    event.tool_call_id,
                    _ChunkBatcher(
                        websocket,
                        "tool.output",
                        "chunk",
                        {"toolCallId": event.tool_call_id},
                        debug_stats=debug_stats,
                        send_lock=connection_state.send_lock,
                    ),
                )
                await batcher.add(event.chunk)
            elif isinstance(event, ToolEnd):
                tool_end_batcher: _ChunkBatcher | None = tool_output_batchers.get(event.tool_call_id)
                if tool_end_batcher is not None:
                    await tool_end_batcher.flush(force=True)
                await _send_json(
                    websocket,
                    {
                        "type": "tool.end",
                        "payload": {
                            "toolCallId": event.tool_call_id,
                            "success": not event.is_error,
                            "output": event.result if not event.is_error else None,
                        },
                    },
                    phase="tool.end",
                    debug_stats=debug_stats,
                    send_lock=connection_state.send_lock,
                )

    def _tool_callback(event: "ToolEvent") -> None:
        """Send tool events via WebSocket (sync wrapper for async send)."""
        task = asyncio.create_task(_handle_tool_event(event))
        pending_tool_tasks.add(task)
        task.add_done_callback(pending_tool_tasks.discard)

    token_usage = {
        "inputTokens": 0,
        "outputTokens": 0,
        "cacheReadTokens": 0,
        "reasoningTokens": 0,
    }

    try:
        await _send_json(
            websocket,
            {
                "type": "chat.started",
                "payload": {
                    "messageId": message_id,
                    "role": "assistant",
                },
            },
            phase="chat.started",
            debug_stats=debug_stats,
            send_lock=connection_state.send_lock,
        )
        await _send_status_update(
            websocket,
            alfred_instance,
            {"isStreaming": True},
            debug_stats=debug_stats,
            phase="status.update.streaming_start",
            send_lock=connection_state.send_lock,
        )

        full_content = ""
        full_reasoning = ""
        in_reasoning = False
        # Use broadcast batchers so new clients can receive ongoing streams
        content_batcher = _BroadcastChunkBatcher(
            "chat.chunk",
            "content",
            {"messageId": message_id},
            debug_stats=debug_stats,
        )
        reasoning_batcher = _BroadcastChunkBatcher(
            "reasoning.chunk",
            "content",
            {"messageId": message_id},
            debug_stats=debug_stats,
        )
        stop_flush_loop = asyncio.Event()

        async def _flush_loop() -> None:
            while not stop_flush_loop.is_set():
                await asyncio.sleep(CHUNK_BATCH_FLUSH_INTERVAL_SECONDS)
                await content_batcher.flush_if_due()
                await reasoning_batcher.flush_if_due()
                for batcher in list(tool_output_batchers.values()):
                    await batcher.flush_if_due()

        flush_task = asyncio.create_task(_flush_loop())

        try:
            try:
                stream = alfred_instance.chat_stream(
                    content,
                    tool_callback=_tool_callback,
                    persist_partial=True,
                    assistant_message_id=message_id,
                    reuse_user_message=reuse_user_message,
                )
            except TypeError:
                try:
                    stream = alfred_instance.chat_stream(
                        content,
                        tool_callback=_tool_callback,
                        persist_partial=True,
                        assistant_message_id=message_id,
                    )
                except TypeError:
                    stream = alfred_instance.chat_stream(content, tool_callback=_tool_callback)

            async for chunk in stream:
                if chunk.startswith("[REASONING]"):
                    in_reasoning = True
                    reasoning_content = chunk[11:]
                    full_reasoning += reasoning_content
                    if reasoning_content:
                        await reasoning_batcher.add(reasoning_content)
                elif in_reasoning:
                    if chunk.startswith("[/REASONING]"):
                        in_reasoning = False
                        await reasoning_batcher.flush(force=True)
                    else:
                        full_reasoning += chunk
                        await reasoning_batcher.add(chunk)
                else:
                    full_content += chunk
                    await content_batcher.add(chunk)
        finally:
            stop_flush_loop.set()
            flush_task.cancel()
            with suppress(asyncio.CancelledError):
                await flush_task
            if pending_tool_tasks:
                await asyncio.gather(*pending_tool_tasks)
            await reasoning_batcher.flush(force=True)
            await content_batcher.flush(force=True)
            for batcher in tool_output_batchers.values():
                await batcher.flush(force=True)

        token_usage["outputTokens"] = len(full_content) // 4
        token_usage["reasoningTokens"] = len(full_reasoning) // 4

        await _send_json(
            websocket,
            {
                "type": "chat.complete",
                "payload": {
                    "messageId": message_id,
                    "finalContent": full_content,
                    "usage": token_usage,
                },
            },
            phase="chat.complete",
            debug_stats=debug_stats,
            send_lock=connection_state.send_lock,
        )
        await _send_status_update(
            websocket,
            alfred_instance,
            {"isStreaming": False},
            debug_stats=debug_stats,
            phase="status.update.streaming_end",
            send_lock=connection_state.send_lock,
        )
        turn_phase = "chat.complete"
    except asyncio.CancelledError:
        turn_phase = "chat.cancelled"
        if connection_state.cancel_requested_message_id == message_id:
            with suppress(Exception):
                await _cleanup_cancelled_turn(alfred_instance, message_id)
            connection_state.clear_active_chat()
            with suppress(Exception):
                await _send_status_update(
                    websocket,
                    alfred_instance,
                    {"isStreaming": False},
                    debug_stats=debug_stats,
                    phase="status.update.cancelled",
                    send_lock=connection_state.send_lock,
                )
            with suppress(Exception):
                await _send_json(
                    websocket,
                    {
                        "type": "chat.cancelled",
                        "payload": {
                            "messageId": message_id,
                        },
                    },
                    phase="chat.cancelled",
                    debug_stats=debug_stats,
                    send_lock=connection_state.send_lock,
                )
        raise
    except WebSocketDisconnect:
        turn_phase = "chat.disconnect"
        # Client disconnected but we DON'T stop the stream
        # The stream continues in background and broadcasts to any new connections
        # Just swallow the exception and continue streaming
        pass
    except Exception as exc:
        turn_phase = "chat.error"
        with suppress(Exception):
            await _send_json(
                websocket,
                {
                    "type": "chat.error",
                    "payload": {
                        "messageId": message_id,
                        "error": str(exc),
                    },
                },
                phase="chat.error",
                debug_stats=debug_stats,
                send_lock=connection_state.send_lock,
            )
            await _send_status_update(
                websocket,
                alfred_instance,
                {"isStreaming": False},
                debug_stats=debug_stats,
                phase="status.update.streaming_error",
                send_lock=connection_state.send_lock,
            )
    finally:
        turn_debug_stats.finish_stream()
        connection_state.finish_turn(turn_debug_stats)
        if connection_debug_stats is not None:
            connection_debug_stats.merge(turn_debug_stats)
        if turn_debug_stats.enabled:
            _emit_webui_debug(
                "webui.websocket.turn_summary",
                phase=turn_phase,
                summary=turn_debug_stats.summary(),
            )


async def _handle_command(
    websocket: WebSocket,
    alfred_instance: WebUIAlfred | None,
    command: str,
) -> None:
    """Handle a command message.

    Args:
        websocket: The WebSocket connection
        alfred_instance: The Alfred instance (optional)
        command: The command string
    """
    cmd_parts = command.strip().split()
    if not cmd_parts:
        return

    cmd = cmd_parts[0].lower()
    args = cmd_parts[1:] if len(cmd_parts) > 1 else []

    if cmd == "/new":
        await _handle_new_command(websocket, alfred_instance)
    elif cmd == "/resume":
        await _handle_resume_command(websocket, alfred_instance, args)
    elif cmd == "/sessions":
        await _handle_sessions_command(websocket, alfred_instance)
    elif cmd == "/session":
        await _handle_session_command(websocket, alfred_instance)
    elif cmd == "/context":
        await _handle_context_command(websocket, alfred_instance)
    elif cmd == "/debug":
        await _handle_debug_command(websocket, alfred_instance, args)
    else:
        await websocket.send_json(
            {
                "type": "chat.error",
                "payload": {"error": f"Unknown command: {cmd}"},
            }
        )


async def _handle_new_command(
    websocket: WebSocket,
    alfred_instance: WebUIAlfred | None,
) -> None:
    """Handle /new command to create a new session."""
    if alfred_instance is None:
        await websocket.send_json(
            {
                "type": "chat.error",
                "payload": {"error": "Alfred instance not available"},
            }
        )
        return

    try:
        # Match TUI behavior: reset token totals before switching to a fresh session.
        _reset_token_tracker(alfred_instance)
        new_session = await _create_session(alfred_instance)

        await websocket.send_json(
            {
                "type": "session.new",
                "payload": {
                    "sessionId": _session_identifier(new_session),
                    "message": "New session created",
                },
            }
        )
        await _send_status_update(websocket, alfred_instance)
    except Exception as e:
        await websocket.send_json(
            {
                "type": "chat.error",
                "payload": {"error": f"Failed to create session: {str(e)}"},
            }
        )


async def _handle_resume_command(
    websocket: WebSocket,
    alfred_instance: WebUIAlfred | None,
    args: list[str],
) -> None:
    """Handle /resume command to resume a session."""
    if alfred_instance is None:
        await websocket.send_json(
            {
                "type": "chat.error",
                "payload": {"error": "Alfred instance not available"},
            }
        )
        return

    if not args:
        await websocket.send_json(
            {
                "type": "chat.error",
                "payload": {"error": "Session ID required: /resume <session_id>"},
            }
        )
        return

    session_id = args[0]

    try:
        session = await _resume_session(alfred_instance, session_id)
        _sync_token_tracker_from_session(alfred_instance, session_id)

        await websocket.send_json(
            {
                "type": "session.loaded",
                "payload": {
                    "sessionId": _session_identifier(session),
                    "messages": _serialize_session_messages(session),
                },
            }
        )
        await _send_status_update(websocket, alfred_instance)
    except Exception as e:
        await websocket.send_json(
            {
                "type": "chat.error",
                "payload": {"error": f"Failed to resume session: {str(e)}"},
            }
        )


async def _handle_sessions_command(
    websocket: WebSocket,
    alfred_instance: WebUIAlfred | None,
) -> None:
    """Handle /sessions command to list recent sessions."""
    if alfred_instance is None:
        await websocket.send_json(
            {
                "type": "chat.error",
                "payload": {"error": "Alfred instance not available"},
            }
        )
        return

    try:
        sessions = await _list_sessions(alfred_instance)
        current_session = _get_current_session(alfred_instance)
        current_session_id = _session_identifier(current_session) if current_session is not None else None

        session_list = []
        for session in list(sessions)[:20]:
            meta = getattr(session, "meta", None)
            created_at = getattr(session, "created_at", getattr(meta, "created_at", datetime.now(UTC)))
            last_active = getattr(session, "last_active", getattr(meta, "last_active", created_at))
            messages = getattr(session, "messages", [])
            message_count = getattr(session, "message_count", getattr(meta, "message_count", len(messages)))
            status = getattr(session, "status", getattr(meta, "status", "active"))
            session_id = _session_identifier(session)

            session_list.append(
                {
                    "id": session_id,
                    "created": created_at.isoformat() if isinstance(created_at, datetime) else datetime.now(UTC).isoformat(),
                    "lastActive": last_active.isoformat() if isinstance(last_active, datetime) else datetime.now(UTC).isoformat(),
                    "messageCount": message_count,
                    "status": status,
                    "isCurrent": session_id == current_session_id,
                    "summary": str(getattr(session, "summary", "")),
                }
            )

        await websocket.send_json(
            {
                "type": "session.list",
                "payload": {"sessions": session_list},
            }
        )
    except Exception as e:
        await websocket.send_json(
            {
                "type": "chat.error",
                "payload": {"error": f"Failed to list sessions: {str(e)}"},
            }
        )


async def _handle_session_command(
    websocket: WebSocket,
    alfred_instance: WebUIAlfred | None,
) -> None:
    """Handle /session command to show current session info."""
    if alfred_instance is None:
        await websocket.send_json(
            {
                "type": "chat.error",
                "payload": {"error": "Alfred instance not available"},
            }
        )
        return

    try:
        current_session = _get_current_session(alfred_instance)

        if current_session is None:
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "payload": {"error": "No active session"},
                }
            )
            return

        meta = getattr(current_session, "meta", None)
        created_at = getattr(current_session, "created_at", getattr(meta, "created_at", datetime.now(UTC)))
        last_active = getattr(current_session, "last_active", getattr(meta, "last_active", created_at))
        messages = getattr(current_session, "messages", [])
        message_count = getattr(current_session, "message_count", getattr(meta, "message_count", len(messages)))
        status = getattr(current_session, "status", getattr(meta, "status", "active"))
        session_id = _session_identifier(current_session)

        # Try to get session summary if available
        summary_text = None
        summarizer = getattr(alfred_instance.core, "summarizer", None)
        if summarizer is not None:
            try:
                summary = await summarizer.load_summary(session_id)
                if summary is not None:
                    summary_text = summary.text
            except Exception:
                # Summary not available, continue without it
                pass

        payload = {
            "sessionId": session_id,
            "messageCount": message_count,
            "created": created_at.isoformat() if isinstance(created_at, datetime) else datetime.now(UTC).isoformat(),
            "lastActive": last_active.isoformat() if isinstance(last_active, datetime) else datetime.now(UTC).isoformat(),
            "status": status,
        }
        if summary_text is not None:
            payload["summary"] = summary_text

        await websocket.send_json(
            {
                "type": "session.info",
                "payload": payload,
            }
        )
    except Exception as e:
        await websocket.send_json(
            {
                "type": "chat.error",
                "payload": {"error": f"Failed to get session info: {str(e)}"},
            }
        )


async def _handle_context_command(
    websocket: WebSocket,
    alfred_instance: WebUIAlfred | None,
) -> None:
    """Handle /context command to show system context."""
    if alfred_instance is None:
        await websocket.send_json(
            {
                "type": "chat.error",
                "payload": {"error": "Alfred instance not available"},
            }
        )
        return

    try:
        from alfred.context_display import get_context_display

        context_data = await get_context_display(cast(Any, alfred_instance))
        await websocket.send_json(
            {
                "type": "context.info",
                "payload": _build_context_payload(context_data),
            }
        )
    except Exception as e:
        await websocket.send_json(
            {
                "type": "chat.error",
                "payload": {"error": f"Failed to get context: {str(e)}"},
            }
        )


async def _handle_debug_command(
    websocket: WebSocket,
    alfred_instance: WebUIAlfred | None,
    args: list[str],
) -> None:
    """Handle /debug command to dump diagnostics."""
    debug_type = args[0] if args else "all"

    payload: dict[str, object] = {"debug_type": debug_type}

    if debug_type in ("all", "session"):
        # Session info
        session = _get_current_session(alfred_instance)
        payload["session"] = {
            "id": _session_identifier(session),
            "has_messages": bool(getattr(session, "messages", [])),
            "message_count": len(getattr(session, "messages", [])),
        }

    if debug_type in ("all", "messages"):
        # Message details
        session = _get_current_session(alfred_instance)
        messages = getattr(session, "messages", [])
        payload["messages"] = [
            {
                "index": i,
                "id": str(getattr(msg, "id", "") or getattr(msg, "idx", "") or f"idx_{i}"),
                "role": str(getattr(msg, "role", "unknown")),
                "content_preview": str(getattr(msg, "content", ""))[:100],
                "has_tool_calls": bool(getattr(msg, "tool_calls", None)),
            }
            for i, msg in enumerate(messages)
        ]

    if debug_type in ("all", "websocket"):
        # WebSocket connection stats
        payload["websocket"] = {
            "active_connections": len(_active_connections),
        }

    await websocket.send_json(
        {
            "type": "debug.info",
            "payload": payload,
        }
    )


def _render_webui_config_script(debug: bool) -> str:
    """Render a tiny JS config payload for the browser."""
    return f"window.__ALFRED_WEBUI_CONFIG__ = {json.dumps({'debug': debug})};"


def create_app(alfred_instance: WebUIAlfred | None = None, debug: bool = False) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        alfred_instance: Optional Alfred instance for chat integration

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Alfred Web UI",
        description="Web-based interface for Alfred",
        version="0.1.0",
    )

    if debug:
        logger.setLevel(logging.DEBUG)

    # Store Alfred instance in app state
    app.state.alfred = alfred_instance
    app.state.webui_debug = debug
    app.state.webui_bootstrap_result = None

    @app.middleware("http")
    async def _no_store_static_assets(request: Any, call_next: Any) -> Response:
        response = cast(Response, await call_next(request))
        if request.url.path.startswith("/static/") or request.url.path == "/app-config.js":
            response.headers["Cache-Control"] = "no-store"
        return response

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    cache_buster = uuid.uuid4().hex

    @app.get("/static/index.html")
    async def static_index_html() -> Response:
        html = (static_dir / "index.html").read_text()
        html = html.replace("?v=3", f"?v={cache_buster}")
        return Response(content=html, media_type="text/html", headers={"Cache-Control": "no-store"})

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def root() -> RedirectResponse:
        """Redirect root to static index.html."""
        return RedirectResponse(url="/static/index.html")

    @app.get("/app-config.js")
    async def app_config() -> Response:
        """Expose browser config for debug-only instrumentation."""
        return Response(
            content=_render_webui_config_script(debug),
            media_type="application/javascript",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/health")
    async def health_check() -> dict[str, object]:
        """Health check endpoint."""
        return build_health_payload(
            app.state.alfred,
            startup_error=_get_bootstrap_startup_error(app.state),
        )

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time communication."""
        await websocket.accept()
        await _register_connection(websocket)

        alfred_instance: WebUIAlfred | None = websocket.app.state.alfred
        connection_debug_stats = _WebSocketDebugStats(
            connection_id=str(uuid.uuid4()),
            enabled=bool(getattr(websocket.app.state, "webui_debug", False)),
        )
        connection_state = _WebSocketConnectionState()
        bootstrap_startup_error = _get_bootstrap_startup_error(websocket.app.state)

        def _clear_chat_task(task: asyncio.Task[None]) -> None:
            if connection_state.active_chat_task is task:
                connection_state.clear_active_chat()
            try:
                exception = task.exception()
            except asyncio.CancelledError:
                return
            if exception is None or isinstance(exception, WebSocketDisconnect):
                return
            if connection_debug_stats.enabled:
                logger.error(
                    "webui websocket chat task failed summary=%s",
                    connection_debug_stats.summary(),
                    exc_info=(type(exception), exception, exception.__traceback__),
                )

        def _start_chat_task(
            content: str,
            *,
            message_id: str | None = None,
            reuse_user_message: bool = False,
        ) -> None:
            chat_message_id = message_id or str(uuid.uuid4())
            alfred = cast(WebUIAlfred, alfred_instance)
            chat_task = asyncio.create_task(
                _handle_chat_message(
                    websocket,
                    alfred,
                    content,
                    connection_state,
                    connection_debug_stats,
                    message_id=chat_message_id,
                    reuse_user_message=reuse_user_message,
                )
            )
            connection_state.set_active_chat(chat_task, chat_message_id)
            chat_task.add_done_callback(_clear_chat_task)

        try:
            await _send_json(
                websocket,
                {
                    "type": "connected",
                    "payload": {},
                },
                phase="connected",
                debug_stats=connection_debug_stats,
                send_lock=connection_state.send_lock,
            )

            if alfred_instance is not None:
                await _load_current_session(
                    websocket,
                    alfred_instance,
                    connection_debug_stats,
                    send_lock=connection_state.send_lock,
                )

            await _send_daemon_status(
                websocket,
                alfred_instance,
                startup_error=bootstrap_startup_error,
                debug_stats=connection_debug_stats,
                phase="daemon.status.connected",
                send_lock=connection_state.send_lock,
            )

            if alfred_instance is not None:
                await _send_status_update(
                    websocket,
                    alfred_instance,
                    debug_stats=connection_debug_stats,
                    phase="status.update.connected",
                    send_lock=connection_state.send_lock,
                )

            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    connection_debug_stats.record_incoming("invalid.json", data)
                    await _send_json(
                        websocket,
                        {
                            "type": "error",
                            "payload": {"error": "Invalid JSON"},
                        },
                        phase="error.invalid_json",
                        debug_stats=connection_debug_stats,
                        send_lock=connection_state.send_lock,
                    )
                    continue

                msg_type = str(message.get("type", "unknown"))
                connection_debug_stats.record_incoming(msg_type, data)
                if connection_state.has_active_chat():
                    connection_state.record_control_message_during_stream(msg_type)
                payload = message.get("payload", {})

                if msg_type == "ping":
                    await _send_json(
                        websocket,
                        {"type": "pong"},
                        phase="pong",
                        debug_stats=connection_debug_stats,
                        send_lock=connection_state.send_lock,
                    )
                    continue

                if msg_type == "chat.cancel":
                    cancel_message_id = connection_state.request_chat_cancel()
                    if cancel_message_id is None:
                        continue
                    active_chat_task = connection_state.active_chat_task
                    if active_chat_task is not None and not active_chat_task.done():
                        active_chat_task.cancel()
                    continue

                if msg_type == "chat.send":
                    if connection_state.has_active_chat():
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {"error": "A response is already streaming"},
                            },
                            phase="chat.error.stream_busy",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue
                    if alfred_instance is None:
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {
                                    "error": "Alfred instance not available",
                                },
                            },
                            phase="chat.error.no_alfred",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue

                    content = str(payload.get("content") or "").strip()
                    if not content:
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {"error": "Message content cannot be empty"},
                            },
                            phase="chat.error.empty_content",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue

                    _start_chat_task(content)
                elif msg_type == "chat.edit":
                    if connection_state.has_active_chat():
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {"error": "A response is already streaming"},
                            },
                            phase="chat.error.stream_busy",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue
                    if alfred_instance is None:
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {
                                    "error": "Alfred instance not available",
                                },
                            },
                            phase="chat.error.no_alfred",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue

                    content = str(payload.get("content") or "").strip()
                    message_id = str(payload.get("messageId") or "").strip()
                    if not content:
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {"error": "Message content cannot be empty"},
                            },
                            phase="chat.error.empty_edit_content",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue
                    if not message_id:
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {"error": "Message ID required for edit"},
                            },
                            phase="chat.error.empty_edit_id",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue

                    session_manager = _get_session_manager(alfred_instance)
                    session = _get_current_session(alfred_instance)
                    if session_manager is None or session is None:
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {"error": "No active session to edit"},
                            },
                            phase="chat.error.no_session_for_edit",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue

                    target_message = _find_last_user_message(session)
                    if target_message is None:
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {"error": "No user message available to edit"},
                            },
                            phase="chat.error.no_edit_target",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue

                    target_message_id = str(getattr(target_message, "id", "") or "")
                    if not target_message_id:
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {"error": "No editable user message ID available"},
                            },
                            phase="chat.error.no_edit_target_id",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue

                    replace_message_and_truncate_after_async = getattr(
                        session_manager,
                        "replace_message_and_truncate_after_async",
                        None,
                    )
                    if not callable(replace_message_and_truncate_after_async):
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {"error": "Session editing is unavailable"},
                            },
                            phase="chat.error.edit_unavailable",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue

                    try:
                        edited_session = await replace_message_and_truncate_after_async(
                            target_message_id,
                            content,
                            session_id=_session_identifier(session),
                        )
                    except Exception as exc:
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {"error": f"Failed to edit message: {exc}"},
                            },
                            phase="chat.error.edit_failed",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue

                    _sync_token_tracker_from_session(alfred_instance, _session_identifier(edited_session))
                    _start_chat_task(content, reuse_user_message=True)
                elif msg_type == "command.execute":
                    if connection_state.has_active_chat():
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {"error": "Commands are unavailable while a response is streaming"},
                            },
                            phase="chat.error.command_while_streaming",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue
                    command = payload.get("command", "").strip()
                    if not command:
                        await _send_json(
                            websocket,
                            {
                                "type": "chat.error",
                                "payload": {"error": "Command cannot be empty"},
                            },
                            phase="chat.error.empty_command",
                            debug_stats=connection_debug_stats,
                            send_lock=connection_state.send_lock,
                        )
                        continue
                    await _handle_command(
                        websocket,
                        alfred_instance,
                        command,
                    )
                else:
                    await _send_json(
                        websocket,
                        {
                            "type": "echo",
                            "payload": {"received": message},
                        },
                        phase="echo",
                        debug_stats=connection_debug_stats,
                        send_lock=connection_state.send_lock,
                    )

        except WebSocketDisconnect as disconnect:
            if connection_debug_stats.enabled:
                _emit_webui_debug(
                    "webui.websocket.disconnect",
                    code=disconnect.code,
                    reason=getattr(disconnect, "reason", ""),
                    summary=connection_debug_stats.summary(),
                )
        except Exception:
            if connection_debug_stats.enabled:
                logger.exception(
                    "webui websocket unexpected error summary=%s",
                    connection_debug_stats.summary(),
                )
        finally:
            # Don't cancel active chat task on disconnect - let it complete in background
            # The task will handle WebSocket errors gracefully and finish streaming to session
            active_chat_task = connection_state.active_chat_task
            # Only cancel if explicitly requested (user clicked stop), not on disconnect
            if (
                active_chat_task is not None
                and not active_chat_task.done()
                and connection_state.cancel_requested_message_id is not None
            ):
                active_chat_task.cancel()
                with suppress(asyncio.CancelledError, WebSocketDisconnect):
                    await active_chat_task
            if connection_debug_stats.enabled:
                _emit_webui_debug(
                    "webui.websocket.closed",
                    summary=connection_debug_stats.summary(),
                )
            await _unregister_connection(websocket)

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """Handle server shutdown by closing all WebSocket connections."""
        await _close_all_connections()
        # Stop Alfred instance if available
        alfred_instance: WebUIAlfred | None = app.state.alfred
        if alfred_instance is not None:
            with suppress(Exception):
                await alfred_instance.stop()

    return app


class WebUIServer:
    """Web UI server using FastAPI and WebSocket."""

    def __init__(self, port: int = 8080) -> None:
        """Initialize the Web UI server.

        Args:
            port: Port to run the server on.
        """
        self.port = port
