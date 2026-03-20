"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page


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


@pytest_asyncio.fixture(scope="session")
async def browser() -> AsyncGenerator["Browser", None]:
    """Launch browser for integration tests."""
    pytest.importorskip("playwright")
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def context(browser: "Browser") -> AsyncGenerator["BrowserContext", None]:
    """Create browser context for each test."""
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
    )
    yield context
    await context.close()


@pytest_asyncio.fixture
async def page(context: "BrowserContext") -> AsyncGenerator["Page", None]:
    """Create page for each test."""
    page = await context.new_page()
    yield page
    await page.close()
