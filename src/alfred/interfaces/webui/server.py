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
    message_id = str(uuid.uuid4())

    try:
        # Send chat.started message
        await websocket.send_json({
            "type": "chat.started",
            "payload": {
                "messageId": message_id,
                "role": "assistant",
            },
        })

        # Stream response from Alfred
        full_content = ""
        async for chunk in alfred_instance.chat_stream(content):
            full_content += chunk
            await websocket.send_json({
                "type": "chat.chunk",
                "payload": {
                    "messageId": message_id,
                    "content": chunk,
                },
            })

        # Send chat.complete message
        await websocket.send_json({
            "type": "chat.complete",
            "payload": {
                "messageId": message_id,
                "finalContent": full_content,
                "usage": {
                    "inputTokens": 0,  # TODO: Get actual token counts
                    "outputTokens": 0,
                    "cacheReadTokens": 0,
                    "reasoningTokens": 0,
                },
            },
        })

    except Exception as e:
        # Send chat.error message
        await websocket.send_json({
            "type": "chat.error",
            "payload": {
                "messageId": message_id,
                "error": str(e),
            },
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

                if msg_type == "chat.send":
                    if alfred_instance is None:
                        await websocket.send_json({
                            "type": "chat.error",
                            "payload": {
                                "error": "Alfred instance not available",
                            },
                        })
                        continue

                    content = payload.get("content", "")
                    await _handle_chat_message(
                        websocket,
                        alfred_instance,
                        content,
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

    return app


class WebUIServer:
    """Web UI server using FastAPI and WebSocket."""

    def __init__(self, port: int = 8080) -> None:
        """Initialize the Web UI server.

        Args:
            port: Port to run the server on.
        """
        self.port = port
