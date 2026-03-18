"""Tests for Web UI server."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from alfred.interfaces.webui import WebUIServer, create_app


def test_webui_module_exists():
    """Verify webui module is importable and WebUIServer can be instantiated."""
    server = WebUIServer(port=8080)
    assert server is not None
    assert server.port == 8080


def test_webui_server_default_port():
    """Verify WebUIServer uses default port 8080."""
    server = WebUIServer()
    assert server.port == 8080


def test_webui_server_custom_port():
    """Verify WebUIServer accepts custom port."""
    server = WebUIServer(port=3000)
    assert server.port == 3000


def test_fastapi_app_factory():
    """Verify create_app returns a valid FastAPI application."""
    app = create_app()
    assert app is not None
    assert isinstance(app, FastAPI)
    assert app.title == "Alfred Web UI"
