"""Pytest configuration and fixtures."""

import asyncio
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Provide temporary path for test isolation."""
    return tmp_path_factory.mktemp("test_")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Playwright fixtures for integration tests
# ============================================================================
