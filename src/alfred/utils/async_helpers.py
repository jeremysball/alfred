"""Async utilities for running coroutines from sync code."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, TypeVar

T = TypeVar("T")


def run_async(coro: Any) -> Any:
    """Run async coroutine from sync code safely.

    Handles all cases:
    - No event loop running: uses asyncio.run()
    - Event loop running: runs in a separate thread to avoid blocking

    WARNING: This blocks the calling thread until completion. If called from
    an async context (e.g., TUI command handler), the event loop is paused.
    For UI responsiveness, consider using asyncio.create_task() instead.

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
    except RuntimeError:
        # No event loop running - safe to use asyncio.run
        return asyncio.run(coro)

    # There's a running event loop in this thread
    # We need to run the coroutine in a separate thread to avoid blocking
    def run_in_new_loop(coroutine):
        """Run coroutine in a new event loop in the current thread."""
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(coroutine)
        finally:
            new_loop.close()
            asyncio.set_event_loop(loop)  # Restore original loop

    # Run in a thread pool to avoid blocking the current loop
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run_in_new_loop, coro)
        return future.result(timeout=30)
