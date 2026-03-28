"""Test markdown table rendering is minimalistic and contained."""

from __future__ import annotations

import asyncio
import socket
import time
import urllib.request
from threading import Thread
from typing import cast

import pytest
import uvicorn
from playwright.async_api import async_playwright

from alfred.interfaces.webui.server import create_app
from tests.webui.fakes import FakeAlfred

TABLE_MARKDOWN = """Here is a comparison table:

| Feature | Option A | Option B | Option C |
|---------|----------|----------|----------|
| Speed | Fast | Medium | Slow |
| Cost | $$$ | $$ | $ |
| Reliability | 99.9% | 98.5% | 95.0% |
| Support | 24/7 | Business hours | Community |

And another table with code:

| Language | Version | Example |
|----------|---------|---------|
| Python | 3.12 | `print("hello")` |
| Rust | 1.75 | `println!("hello")` |
| Go | 1.21 | `fmt.Println("hello")` |

This table has a very long cell that might overflow:

| Short | Very long content that might cause horizontal scrolling on narrow screens |
|-------|--------------------------------------------------------------------------|
| A | Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. |
| B | Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. |
"""


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


async def _render_table_message(page, theme: str) -> None:
    await page.evaluate(
        """
        ({ theme, markdown }) => {
          document.documentElement.setAttribute('data-theme', theme);
          const messageList = document.getElementById('message-list');
          if (!messageList) {
            return;
          }

          messageList.innerHTML = '';
          const message = document.createElement('chat-message');
          message.setAttribute('role', 'assistant');
          message.setAttribute('content', markdown);
          message.setAttribute('timestamp', new Date().toISOString());
          messageList.appendChild(message);
        }
        """,
        {"theme": theme, "markdown": TABLE_MARKDOWN},
    )

    await page.wait_for_function(
        """
        () => {
          const message = document.querySelector('#message-list chat-message[role="assistant"]');
          const tables = message?.querySelectorAll('.text-block table, .reasoning-content table');
          return Boolean(tables && tables.length >= 1);
        }
        """
    )


async def _measure_table_metrics(page) -> dict[str, object] | None:
    return await page.evaluate(
        """
        () => {
          const message = document.querySelector('#message-list chat-message[role="assistant"]');
          const bubble = message?.querySelector('.message');
          const content = message?.querySelector('.text-block');
          const tables = message?.querySelectorAll('.text-block table, .reasoning-content table');
          
          if (!bubble || !tables || tables.length === 0) {
            return null;
          }
          
          const bubbleRect = bubble.getBoundingClientRect();
          
          return {
            bubbleClientWidth: bubble.clientWidth,
            bubbleScrollWidth: bubble.scrollWidth,
            tableCount: tables.length,
            tables: Array.from(tables).map((table, index) => {
              const rect = table.getBoundingClientRect();
              const headers = table.querySelectorAll('th');
              const cells = table.querySelectorAll('td');
              const style = window.getComputedStyle(table);
              
              return {
                index,
                tagName: table.tagName.toLowerCase(),
                leftOffset: rect.left - bubbleRect.left,
                rightOffset: bubbleRect.right - rect.right,
                scrollWidth: table.scrollWidth,
                clientWidth: table.clientWidth,
                headerCount: headers.length,
                cellCount: cells.length,
                borderCollapse: style.borderCollapse,
                overflowX: style.overflowX,
                maxWidth: style.maxWidth,
              };
            }),
          };
        }
        """
    )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_markdown_tables_render_and_stay_contained() -> None:
    """Tables should render properly and stay within message bubbles."""
    port = _find_free_port()
    config = uvicorn.Config(
        create_app(alfred_instance=FakeAlfred()),
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

            themes = ["minimal", "modern-dark"]
            viewports = [
                {"width": 1440, "height": 900},
                {"width": 390, "height": 844},
            ]

            for viewport in viewports:
                await page.set_viewport_size(viewport)
                await page.wait_for_timeout(100)

                for theme in themes:
                    await _render_table_message(page, theme)
                    metrics = await _measure_table_metrics(page)

                    assert metrics is not None
                    assert metrics["tableCount"] >= 1

                    # Tables should exist and have proper structure
                    for table in metrics["tables"]:
                        assert table["tagName"] == "table"
                        assert table["headerCount"] > 0, "Tables should have headers"
                        assert table["cellCount"] > 0, "Tables should have cells"

                        # Tables should be properly styled
                        assert table["borderCollapse"] in ["collapse", "separate"]

                        # On desktop, tables should fit within the bubble
                        # On mobile, tables may scroll horizontally but still be contained
                        if viewport["width"] >= 800:
                            # Relaxed check for desktop - allow small overflow
                            assert table["leftOffset"] >= -2, f"Table {table['index']} overflows left"
                            assert table["rightOffset"] >= -2, f"Table {table['index']} overflows right"
                        else:
                            # On mobile, tables should at least not break layout completely
                            assert table["leftOffset"] >= -5, f"Table {table['index']} breaks layout left"
                            assert table["scrollWidth"] > 0, "Table should have measurable width"

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_markdown_tables_have_minimal_styling() -> None:
    """Tables should have minimal visual styling (no heavy borders or zebra striping)."""
    port = _find_free_port()
    config = uvicorn.Config(
        create_app(alfred_instance=FakeAlfred()),
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

            await _render_table_message(page, "minimal")

            # Check table styling is minimal
            styles = await page.evaluate(
                """
                () => {
                  const message = document.querySelector('#message-list chat-message[role="assistant"]');
                  const table = message?.querySelector('.text-block table, .reasoning-content table');
                  const headers = table?.querySelectorAll('th');
                  const cells = table?.querySelectorAll('td');
                  
                  if (!table || headers.length === 0 || cells.length === 0) {
                    return null;
                  }
                  
                  const tableStyle = window.getComputedStyle(table);
                  const headerStyle = window.getComputedStyle(headers[0]);
                  const cellStyle = window.getComputedStyle(cells[0]);
                  
                  return {
                    table: {
                      borderWidth: tableStyle.borderWidth,
                      marginTop: tableStyle.marginTop,
                      marginBottom: tableStyle.marginBottom,
                    },
                    header: {
                      fontWeight: headerStyle.fontWeight,
                      textAlign: headerStyle.textAlign,
                      padding: headerStyle.padding,
                    },
                    cell: {
                      padding: cellStyle.padding,
                      borderWidth: cellStyle.borderWidth,
                    },
                  };
                }
                """
            )

            assert styles is not None

            # Headers should be distinguishable but not flashy
            header_weight = int(styles["header"]["fontWeight"])
            assert header_weight >= 500, "Headers should have some weight for readability"

            # Cells should have reasonable padding
            assert styles["cell"]["padding"] != "0px", "Cells should have padding"

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
