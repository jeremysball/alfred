"""Browser regression coverage for memory recall semantics."""

from __future__ import annotations

import asyncio
import re
import socket
import time
import urllib.request
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from threading import Thread
from types import SimpleNamespace
from typing import Any, cast

import pytest
import uvicorn
from playwright.async_api import Page, async_playwright, expect

from alfred.embeddings.provider import EmbeddingProvider
from alfred.interfaces.webui import create_app
from alfred.memory.sqlite_store import SQLiteMemoryStore
from alfred.tools.remember import RememberTool
from alfred.tools.search_memories import SearchMemoriesTool
from tests.webui.fakes import FakeAlfred, make_message


class KeywordEmbeddingProvider(EmbeddingProvider):
    """Deterministic 2D embeddings for memory recall tests."""

    @property
    def dimension(self) -> int:
        return 2

    def _vector_for(self, text: str) -> list[float]:
        normalized = re.sub(r"[^a-z0-9\s]", " ", text.lower())
        if "favorite color" in normalized or "color" in normalized or "blue" in normalized:
            return [1.0, 0.0]
        if "favorite food" in normalized or "food" in normalized or "pizza" in normalized:
            return [0.0, 1.0]
        return [0.70710678, 0.70710678]

    async def embed(self, text: str) -> list[float]:
        return self._vector_for(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for(text) for text in texts]


class MemoryRecallFakeAlfred(FakeAlfred):
    """Alfred fake that uses a real SQLite memory store for recall flows."""

    def __init__(self, memory_store: SQLiteMemoryStore, *, recall_threshold: float = 0.75) -> None:
        super().__init__()
        self._memory_store = memory_store
        self._recall_threshold = recall_threshold
        self._remember_tool = RememberTool(memory_store)
        self._search_tool = SearchMemoriesTool(memory_store)

    @staticmethod
    def _extract_saved_content(message: str) -> str | None:
        match = re.match(r"(?i)^remember(?:\s+that)?\s+(.*)$", message.strip())
        if match is None:
            return None

        content = match.group(1).strip().rstrip(".?!")
        return content or None

    async def _collect_tool_output(self, tool: Any, **kwargs: Any) -> str:
        chunks: list[str] = []
        async for chunk in tool.execute_stream(**kwargs):
            chunks.append(chunk)
        return "".join(chunks)

    async def _render_memory_response(self, message: str) -> str:
        save_content = self._extract_saved_content(message)
        if save_content is not None:
            return await self._collect_tool_output(
                self._remember_tool,
                content=save_content,
            )

        results, similarities, _ = await self._memory_store.search(message, top_k=1)
        if results:
            top_similarity = similarities.get(results[0].entry_id, 0.0)
            if top_similarity >= self._recall_threshold:
                return await self._collect_tool_output(
                    self._search_tool,
                    query=message,
                    top_k=1,
                )

        return "I don't remember that yet."

    async def chat_stream(
        self,
        message: str,
        tool_callback: Callable[[Any], None] | None = None,
        session_id: str | None = None,
        persist_partial: bool = False,
        assistant_message_id: str | None = None,
        reuse_user_message: bool = False,
    ) -> AsyncIterator[str]:
        """Yield a memory-aware assistant response while preserving session state."""

        del tool_callback, session_id

        self.chat_called = True
        self.chat_messages.append(message)
        self.last_message = message
        self.token_tracker.add({"prompt_tokens": max(len(message) // 4, 1), "completion_tokens": 0})

        session_manager = self.core.session_manager
        session = session_manager.get_current_cli_session()
        if session is None:
            session = session_manager.start_session()

        assistant_msg = None
        if persist_partial:
            if not (reuse_user_message and session.messages and session.messages[-1].role.value == "user"):
                session.messages.append(
                    make_message(
                        "user",
                        message,
                        idx=len(session.messages),
                        id=f"user-{len(session.messages)}",
                    )
                )
            assistant_msg = make_message(
                "assistant",
                "",
                idx=len(session.messages),
                id=assistant_message_id or f"assistant-{len(session.messages)}",
                streaming=True,
            )
            session.messages.append(assistant_msg)
            session.meta.message_count = len(session.messages)
            session.meta.last_active = datetime.now(UTC)

        response_text = await self._render_memory_response(message)
        if assistant_msg is not None:
            assistant_msg.content += response_text

        if response_text:
            yield response_text

        if assistant_msg is not None:
            assistant_msg.streaming = False
            session.meta.last_active = datetime.now(UTC)
            session.meta.message_count = len(session.messages)

        self.token_tracker.add(
            {
                "prompt_tokens": 0,
                "completion_tokens": max(len(response_text) // 4, 1),
            }
        )

    async def stop(self) -> None:
        return None


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return cast(int, sock.getsockname()[1])


async def _wait_for_server(port: int, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/health"
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        await asyncio.sleep(0.25)
    raise RuntimeError(f"server did not start: {last_error}")


async def _wait_for_composer_ready(page: Page) -> None:
    await page.wait_for_function(
        """
        () => {
          const input = document.querySelector('#message-input');
          return Boolean(input && !input.disabled);
        }
        """
    )


async def _send_message_and_wait_for_assistant(
    page: Page,
    message: str,
    expected_assistant_count: int,
    *expected_substrings: str,
) -> None:
    await page.fill("#message-input", message)
    await page.click("#send-button")

    assistant_messages = page.locator('chat-message[role="assistant"]')
    await expect(assistant_messages).to_have_count(expected_assistant_count)

    latest_assistant_content = assistant_messages.last.locator(".text-block").last
    for substring in expected_substrings:
        await expect(latest_assistant_content).to_contain_text(substring)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_webui_memory_recall_survives_reload_with_correct_similarity_semantics(
    tmp_path,
) -> None:
    port = _find_free_port()
    memory_store = SQLiteMemoryStore(
        SimpleNamespace(data_dir=tmp_path),
        KeywordEmbeddingProvider(),
    )
    fake_alfred = MemoryRecallFakeAlfred(memory_store)

    config = uvicorn.Config(
        create_app(alfred_instance=fake_alfred),
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="networkidle")
            await _wait_for_composer_ready(page)

            await _send_message_and_wait_for_assistant(
                page,
                "remember that my favorite color is blue",
                1,
                "Remembered: my favorite color is blue",
            )
            await _send_message_and_wait_for_assistant(
                page,
                "what is my favorite color?",
                2,
                "my favorite color is blue",
                "sim: 100%",
            )

            await page.reload(wait_until="networkidle")
            await _wait_for_composer_ready(page)

            restored_assistant_messages = page.locator('chat-message[role="assistant"]')
            await expect(restored_assistant_messages).to_have_count(2)
            restored_recall_content = restored_assistant_messages.last.locator(".text-block").last
            await expect(restored_recall_content).to_contain_text("my favorite color is blue")
            await expect(restored_recall_content).to_contain_text("sim: 100%")

            await _send_message_and_wait_for_assistant(
                page,
                "what is my favorite color?",
                3,
                "my favorite color is blue",
                "sim: 100%",
            )

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
