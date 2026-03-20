"""FastAPI server for Alfred Web UI."""

import json
import uuid
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

import alfred

if TYPE_CHECKING:
    from alfred.agent import ToolEvent
    from alfred.alfred import Alfred

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


async def _load_current_session(
    websocket: WebSocket,
    alfred_instance: "Alfred",
) -> None:
    """Load and send current session messages on connection.

    Args:
        websocket: The WebSocket connection
        alfred_instance: The Alfred instance
    """
    try:
        # Get current CLI session
        session = alfred_instance.core.session_manager.get_current_cli_session()

        if session is None:
            # No active session, create one
            session = alfred_instance.core.session_manager.start_session()

        # Convert messages to JSON format
        messages = []
        for msg in session.messages:
            messages.append({
                "id": msg.id if hasattr(msg, "id") else str(uuid.uuid4()),
                "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                "content": msg.content,
                "reasoningContent": msg.reasoning_content if hasattr(msg, "reasoning_content") else "",
            })

        await websocket.send_json({
            "type": "session.loaded",
            "payload": {
                "sessionId": session.meta.session_id,
                "messages": messages,
            },
        })
    except Exception as e:
        # Silently ignore - session loading is optional
        print(f"Failed to load session: {e}")


async def _send_status_update(
    websocket: WebSocket,
    alfred_instance: "Alfred | None",
    extra_status: dict | None = None,
) -> None:
    """Send current status to the client.

    Args:
        websocket: The WebSocket connection
        alfred_instance: The Alfred instance (optional)
        extra_status: Additional status fields to include
    """
    status = {
        "model": "",
        "contextTokens": 0,
        "inputTokens": 0,
        "outputTokens": 0,
        "cacheReadTokens": 0,
        "reasoningTokens": 0,
        "queueLength": 0,
        "isStreaming": False,
    }

    if extra_status:
        status.update(extra_status)

    # Try to get model from config
    if alfred_instance is not None and hasattr(alfred_instance, "config"):
        try:
            model = alfred_instance.config.get("model", "")
            if model:
                status["model"] = model
        except Exception:
            pass

    await websocket.send_json({
        "type": "status.update",
        "payload": status,
    })


async def _handle_chat_message(
    websocket: WebSocket,
    alfred_instance: "Alfred",
    content: str,
) -> None:
    """Handle a chat message by streaming through Alfred.

    Args:
        websocket: The WebSocket connection
        alfred_instance: The Alfred instance
        content: The user message content
    """
    from alfred.agent import ToolEnd, ToolOutput, ToolStart

    message_id = str(uuid.uuid4())

    def _tool_callback(event: "ToolEvent") -> None:
        """Send tool events via WebSocket (sync wrapper for async send)."""
        import asyncio

        if isinstance(event, ToolStart):
            asyncio.create_task(websocket.send_json({
                "type": "tool.start",
                "payload": {
                    "toolCallId": event.tool_call_id,
                    "toolName": event.tool_name,
                    "arguments": event.arguments,
                    "messageId": message_id,
                },
            }))
        elif isinstance(event, ToolOutput):
            asyncio.create_task(websocket.send_json({
                "type": "tool.output",
                "payload": {
                    "toolCallId": event.tool_call_id,
                    "chunk": event.chunk,
                },
            }))
        elif isinstance(event, ToolEnd):
            asyncio.create_task(websocket.send_json({
                "type": "tool.end",
                "payload": {
                    "toolCallId": event.tool_call_id,
                    "success": not event.is_error,
                    "output": event.result if not event.is_error else None,
                },
            }))

    # Track token usage
    token_usage = {
        "inputTokens": 0,
        "outputTokens": 0,
        "cacheReadTokens": 0,
        "reasoningTokens": 0,
    }

    try:
        # Send chat.started message and status update
        await websocket.send_json({
            "type": "chat.started",
            "payload": {
                "messageId": message_id,
                "role": "assistant",
            },
        })
        await _send_status_update(
            websocket,
            alfred_instance,
            {"isStreaming": True, "inputTokens": len(content) // 4},  # Rough estimate
        )

        # Stream response from Alfred with tool callback
        full_content = ""
        full_reasoning = ""
        in_reasoning = False
        reasoning_buffer = ""

        async for chunk in alfred_instance.chat_stream(content, tool_callback=_tool_callback):
            # Parse [REASONING] markers
            if chunk.startswith("[REASONING]"):
                in_reasoning = True
                reasoning_content = chunk[11:]  # Remove [REASONING] prefix
                reasoning_buffer += reasoning_content
                full_reasoning += reasoning_content
                await websocket.send_json({
                    "type": "reasoning.chunk",
                    "payload": {
                        "messageId": message_id,
                        "content": reasoning_content,
                    },
                })
            elif in_reasoning:
                # Check if this chunk ends reasoning
                if chunk.startswith("[/REASONING]"):
                    in_reasoning = False
                    reasoning_buffer = ""  # Clear buffer
                else:
                    # Still in reasoning - send chunk and accumulate
                    reasoning_buffer += chunk
                    full_reasoning += chunk
                    await websocket.send_json({
                        "type": "reasoning.chunk",
                        "payload": {
                            "messageId": message_id,
                            "content": chunk,
                        },
                    })
            else:
                # Regular content chunk
                full_content += chunk
                await websocket.send_json({
                    "type": "chat.chunk",
                    "payload": {
                        "messageId": message_id,
                        "content": chunk,
                    },
                })

        # Calculate approximate token counts
        # Rough approximation: 4 chars ≈ 1 token for English text
        token_usage["outputTokens"] = len(full_content) // 4
        token_usage["reasoningTokens"] = len(full_reasoning) // 4

        # Send chat.complete message
        await websocket.send_json({
            "type": "chat.complete",
            "payload": {
                "messageId": message_id,
                "finalContent": full_content,
                "usage": token_usage,
            },
        })

        # Send status update when streaming ends
        await _send_status_update(
            websocket,
            alfred_instance,
            {"isStreaming": False, **token_usage},
        )

    except Exception as e:
        # Send chat.error message
        await websocket.send_json({
            "type": "chat.error",
            "payload": {
                "messageId": message_id,
                "error": str(e),
            },
        })
        # Send status update when streaming ends on error
        await _send_status_update(
            websocket,
            alfred_instance,
            {"isStreaming": False, **token_usage},
        )


async def _handle_command(
    websocket: WebSocket,
    alfred_instance: "Alfred | None",
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
    else:
        await websocket.send_json({
            "type": "chat.error",
            "payload": {"error": f"Unknown command: {cmd}"},
        })


async def _handle_new_command(
    websocket: WebSocket,
    alfred_instance: "Alfred | None",
) -> None:
    """Handle /new command to create a new session."""
    if alfred_instance is None:
        await websocket.send_json({
            "type": "chat.error",
            "payload": {"error": "Alfred instance not available"},
        })
        return

    try:
        # Create new session via Alfred
        new_session = await alfred_instance.new_session()

        await websocket.send_json({
            "type": "session.new",
            "payload": {
                "sessionId": new_session.session_id,
                "message": "New session created",
            },
        })
    except Exception as e:
        await websocket.send_json({
            "type": "chat.error",
            "payload": {"error": f"Failed to create session: {str(e)}"},
        })


async def _handle_resume_command(
    websocket: WebSocket,
    alfred_instance: "Alfred | None",
    args: list[str],
) -> None:
    """Handle /resume command to resume a session."""
    if alfred_instance is None:
        await websocket.send_json({
            "type": "chat.error",
            "payload": {"error": "Alfred instance not available"},
        })
        return

    if not args:
        await websocket.send_json({
            "type": "chat.error",
            "payload": {"error": "Session ID required: /resume <session_id>"},
        })
        return

    session_id = args[0]

    try:
        # Resume session via Alfred
        session = await alfred_instance.resume_session(session_id)

        # Convert messages to serializable format
        messages = []
        for msg in session.messages:
            messages.append({
                "id": msg.id if hasattr(msg, "id") else str(uuid.uuid4()),
                "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                "content": msg.content,
            })

        await websocket.send_json({
            "type": "session.loaded",
            "payload": {
                "sessionId": session.meta.session_id,
                "messages": messages,
            },
        })
    except Exception as e:
        await websocket.send_json({
            "type": "chat.error",
            "payload": {"error": f"Failed to resume session: {str(e)}"},
        })


async def _handle_sessions_command(
    websocket: WebSocket,
    alfred_instance: "Alfred | None",
) -> None:
    """Handle /sessions command to list recent sessions."""
    if alfred_instance is None:
        await websocket.send_json({
            "type": "chat.error",
            "payload": {"error": "Alfred instance not available"},
        })
        return

    try:
        # Get recent sessions
        sessions = await alfred_instance.list_sessions(limit=10)

        session_list = []
        for session in sessions:
            session_list.append({
                "id": session.session_id,
                "created": session.created_at.isoformat() if hasattr(session, "created_at") else "",
                "messageCount": len(session.messages) if hasattr(session, "messages") else 0,
                "summary": session.summary if hasattr(session, "summary") else "",
            })

        await websocket.send_json({
            "type": "session.list",
            "payload": {"sessions": session_list},
        })
    except Exception as e:
        await websocket.send_json({
            "type": "chat.error",
            "payload": {"error": f"Failed to list sessions: {str(e)}"},
        })


async def _handle_session_command(
    websocket: WebSocket,
    alfred_instance: "Alfred | None",
) -> None:
    """Handle /session command to show current session info."""
    if alfred_instance is None:
        await websocket.send_json({
            "type": "chat.error",
            "payload": {"error": "Alfred instance not available"},
        })
        return

    try:
        current_session = alfred_instance.current_session

        await websocket.send_json({
            "type": "session.info",
            "payload": {
                "sessionId": current_session.session_id if hasattr(current_session, "session_id") else "unknown",
                "messageCount": len(current_session.messages) if hasattr(current_session, "messages") else 0,
                "created": current_session.created_at.isoformat() if hasattr(current_session, "created_at") else "",
            },
        })
    except Exception as e:
        await websocket.send_json({
            "type": "chat.error",
            "payload": {"error": f"Failed to get session info: {str(e)}"},
        })


async def _handle_context_command(
    websocket: WebSocket,
    alfred_instance: "Alfred | None",
) -> None:
    """Handle /context command to show system context."""
    if alfred_instance is None:
        await websocket.send_json({
            "type": "chat.error",
            "payload": {"error": "Alfred instance not available"},
        })
        return

    try:
        context = alfred_instance.get_context() if hasattr(alfred_instance, "get_context") else {}

        await websocket.send_json({
            "type": "context.info",
            "payload": {
                "cwd": context.get("cwd", ""),
                "files": context.get("files", []),
                "systemInfo": context.get("system_info", {}),
            },
        })
    except Exception as e:
        await websocket.send_json({
            "type": "chat.error",
            "payload": {"error": f"Failed to get context: {str(e)}"},
        })


def create_app(alfred_instance: "Alfred | None" = None) -> FastAPI:
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

    # Store Alfred instance in app state
    app.state.alfred = alfred_instance

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def root() -> None:
        """Redirect root to static index.html."""
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/static/index.html")

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok", "version": alfred.__version__}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time communication."""
        await websocket.accept()
        await _register_connection(websocket)

        # Get Alfred instance from app state
        alfred_instance: Alfred | None = websocket.app.state.alfred

        try:
            # Send connected message
            await websocket.send_json({
                "type": "connected",
                "payload": {},
            })

            # Load current session if available
            if alfred_instance is not None:
                await _load_current_session(websocket, alfred_instance)

            while True:
                # Receive and parse message
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "payload": {"error": "Invalid JSON"},
                    })
                    continue

                # Handle message based on type
                msg_type = message.get("type")
                payload = message.get("payload", {})

                if msg_type == "ping":
                    # Respond to keepalive ping
                    await websocket.send_json({"type": "pong"})
                    continue

                if msg_type == "chat.send":
                    if alfred_instance is None:
                        await websocket.send_json({
                            "type": "chat.error",
                            "payload": {
                                "error": "Alfred instance not available",
                            },
                        })
                        continue

                    content = payload.get("content", "").strip()
                    if not content:
                        await websocket.send_json({
                            "type": "chat.error",
                            "payload": {"error": "Message content cannot be empty"},
                        })
                        continue

                    await _handle_chat_message(
                        websocket,
                        alfred_instance,
                        content,
                    )
                elif msg_type == "command.execute":
                    command = payload.get("command", "").strip()
                    if not command:
                        await websocket.send_json({
                            "type": "chat.error",
                            "payload": {"error": "Command cannot be empty"},
                        })
                        continue
                    await _handle_command(
                        websocket,
                        alfred_instance,
                        command,
                    )
                else:
                    # Echo for other message types (for testing)
                    await websocket.send_json({
                        "type": "echo",
                        "payload": {"received": message},
                    })

        except Exception:
            pass  # Connection closed
        finally:
            await _unregister_connection(websocket)

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """Handle server shutdown by closing all WebSocket connections."""
        await _close_all_connections()
        # Stop Alfred instance if available
        alfred_instance: Alfred | None = app.state.alfred
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
