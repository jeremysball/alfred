"""Web UI for Alfred using FastAPI and WebSocket."""

from alfred.interfaces.webui.server import WebUIServer, create_app

__all__ = ["WebUIServer", "create_app"]
