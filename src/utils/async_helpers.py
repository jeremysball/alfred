"""Async utilities for running coroutines from sync code."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, TypeVar

T = TypeVar("T")


def run_async(coro: Any) -> Any:
    """Run async coroutine from sync code safely.

    Handles both cases:
    - No event loop running: uses asyncio.run()
    - Event loop running: uses run_coroutine_threadsafe()

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine

    Raises:
        TimeoutError: If the coroutine takes longer than 30 seconds
        Exception: Any exception raised by the coroutine
    """
    try:
        loop = asyncio.get_running_loop()
        if loop is None:
            # No running loop - safe to use asyncio.run
            return asyncio.run(coro)
        # We're in an async context - use thread pool to avoid blocking
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=30)
    except RuntimeError:
        # No event loop running - safe to use asyncio.run
        return asyncio.run(coro)
