"""FastAPI server for Alfred Web UI."""

from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

import alfred

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


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Alfred Web UI",
        description="Web-based interface for Alfred",
        version="0.1.0",
    )

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok", "version": alfred.__version__}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time communication."""
        await websocket.accept()
        await _register_connection(websocket)
        await websocket.send_text("connected")
        try:
            while True:
                data = await websocket.receive_text()
                await websocket.send_text(f"echo: {data}")
        except Exception:
            pass  # Connection closed
        finally:
            await _unregister_connection(websocket)

    @app.on_event("shutdown")
    async def shutdown_event():
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
