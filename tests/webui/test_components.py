from __future__ import annotations

import asyncio
import json
import os
import socket
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return cast(int, sock.getsockname()[1])


def _build_launch_env(
    tmp_path: Path,
    *,
    bootstrap_failure_message: str | None = None,
) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_DATA_HOME": str(tmp_path / "data"),
        }
    )

    if bootstrap_failure_message is not None:
        sitecustomize_dir = tmp_path / "sitecustomize"
        sitecustomize_dir.mkdir(parents=True, exist_ok=True)
        sitecustomize_path = sitecustomize_dir / "sitecustomize.py"
        sitecustomize_path.write_text(
            f'''import os

if os.environ.get("ALFRED_TEST_WEBUI_BOOTSTRAP_FAILURE"):
    from alfred.interfaces.webui.daemon_bootstrap import DaemonBootstrapResult
    import alfred.cli.webui_hotswap as webui_hotswap
    import alfred.interfaces.webui.daemon_bootstrap as daemon_bootstrap

    def _bootstrap_daemon() -> DaemonBootstrapResult:
        return DaemonBootstrapResult(
            daemon_was_running=False,
            daemon_started=False,
            startup_error={json.dumps(bootstrap_failure_message)},
        )

    webui_hotswap.bootstrap_daemon = _bootstrap_daemon
    daemon_bootstrap.bootstrap_daemon = _bootstrap_daemon
'''
        )
        pythonpath_parts = [str(sitecustomize_dir)]
        if env.get("PYTHONPATH"):
            pythonpath_parts.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
        env["ALFRED_TEST_WEBUI_BOOTSTRAP_FAILURE"] = bootstrap_failure_message

    return env


async def _wait_for_server(port: int, timeout: float = 20.0) -> None:
    await _wait_for_health(port, timeout=timeout)


async def _wait_for_health(
    port: int,
    *,
    timeout: float = 20.0,
    predicate: Callable[[dict[str, object]], bool] | None = None,
) -> dict[str, object]:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/health"
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status != 200:
                    continue
                data = json.loads(response.read().decode("utf-8"))
                if predicate is None or predicate(data):
                    return data
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        await asyncio.sleep(0.25)
    raise RuntimeError(f"server did not start: {last_error}")


async def _launch_webui(port: int, *, env: dict[str, str] | None = None) -> asyncio.subprocess.Process:
    process = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "alfred",
        "webui",
        "--port",
        str(port),
        cwd=PROJECT_ROOT,
        env=env,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await _wait_for_server(port)
    return process


async def _stop_daemon(env: dict[str, str]) -> None:
    process = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "alfred",
        "daemon",
        "stop",
        cwd=PROJECT_ROOT,
        env=env,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        await asyncio.wait_for(process.wait(), timeout=10)
    except TimeoutError:
        process.kill()
        await process.wait()


async def _stop_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return

    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=10)
    except TimeoutError:
        process.kill()
        await process.wait()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_status_bar_renders_live_updates_in_browser() -> None:
    port = _find_free_port()
    process = await _launch_webui(port)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            await page.evaluate(
                """
                () => {
                  const statusBar = document.querySelector('#status-bar');
                  if (!statusBar) return;
                  statusBar.setModel('kimi-k2');
                  statusBar.setTokens(1200, 3456, 78, 9, 4567);
                  statusBar.setQueue(3);
                  statusBar.setStreaming(true);
                }
                """
            )
            await page.wait_for_timeout(160)

            data = await page.evaluate(
                """
                () => {
                  const statusBar = document.querySelector('#status-bar');
                  const streaming = statusBar?.querySelector('.streaming-section');
                  const throbber = statusBar?.querySelector('.throbber');
                  const model = statusBar?.querySelector('.model-name');
                  const tokens = statusBar?.querySelector('.tokens-display');
                  const queue = statusBar?.querySelector('.queue-count');

                  return {
                    model: model?.textContent || '',
                    tokens: tokens?.textContent || '',
                    queue: queue?.textContent || '',
                    streamingActive: streaming?.classList.contains('active') || false,
                    streamingText: streaming?.querySelector('.streaming-text')?.textContent || '',
                    throbber: throbber?.textContent || '',
                  };
                }
                """
            )

            assert data["model"] == "kimi-k2"
            assert data["tokens"] == "In: 1.2k | Out: 3.5k | Cache: 78 | Reason: 9"
            assert data["queue"] == "3"
            assert data["streamingActive"] is True
            assert data["streamingText"] == "Thinking..."
            assert data["throbber"]

            await page.evaluate(
                """
                () => {
                  const statusBar = document.querySelector('#status-bar');
                  statusBar?.setStreaming(false);
                }
                """
            )
            await page.wait_for_timeout(120)

            stopped = await page.evaluate(
                """
                () => {
                  const statusBar = document.querySelector('#status-bar');
                  const streaming = statusBar?.querySelector('.streaming-section');
                  return {
                    streamingActive: streaming?.classList.contains('active') || false,
                    streamingHidden: streaming?.classList.contains('hidden') || false,
                  };
                }
                """
            )

            assert stopped["streamingActive"] is False
            assert stopped["streamingHidden"] is True

            await browser.close()
    finally:
        await _stop_process(process)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_status_bar_compacts_on_mobile_in_browser() -> None:
    port = _find_free_port()
    process = await _launch_webui(port)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 390, "height": 844})
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            await page.evaluate(
                """
                () => {
                  const statusBar = document.querySelector('#status-bar');
                  if (!statusBar) return;
                  statusBar.setModel('kimi-k2-5');
                  statusBar.setTokens(1200, 3456, 78, 9, 68272, 272000);
                  statusBar.setQueue(0);
                }
                """
            )
            await page.wait_for_timeout(120)

            data = await page.evaluate(
                """
                () => {
                  const statusBar = document.querySelector('#status-bar');
                  const modelSection = statusBar?.querySelector('.model-section');
                  const modelName = modelSection?.querySelector('.model-name');
                  const tokensSection = statusBar?.querySelector('.tokens-section');
                  const contextSection = statusBar?.querySelector('.mobile-context-section');
                  const contextDisplay = contextSection?.querySelector('.context-display');
                  const queueSection = statusBar?.querySelector('.queue-section');

                  return {
                    modelDisplay: modelSection ? getComputedStyle(modelSection).display : '',
                    modelText: modelName?.textContent || '',
                    tokensDisplay: tokensSection ? getComputedStyle(tokensSection).display : '',
                    contextDisplay: contextSection ? getComputedStyle(contextSection).display : '',
                    contextText: contextDisplay?.textContent || '',
                    queueExists: Boolean(queueSection),
                  };
                }
                """
            )

            assert data["modelDisplay"] == "flex"
            assert data["modelText"] == "kimi-k2-5"
            assert data["tokensDisplay"] == "none"
            assert data["contextDisplay"] == "flex"
            assert data["contextText"] == "25.1%/272k"
            assert data["queueExists"] is False

            await browser.close()
    finally:
        await _stop_process(process)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_status_bar_uses_local_queue_and_nested_daemon_status_payloads() -> None:
    port = _find_free_port()
    process = await _launch_webui(port)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )
            await page.wait_for_function("() => window.__alfredWebUI?.emitMessage !== undefined")

            await page.evaluate(
                """
                () => {
                  window.__alfredWebUI.emitMessage({
                    type: 'daemon.status',
                    payload: {
                      daemon: {
                        state: 'running',
                        pid: 4242,
                      },
                    },
                  });

                  window.__alfredWebUI.emitMessage({
                    type: 'status.update',
                    payload: {
                      model: 'kimi-k2-5',
                      queueLength: 0,
                      isStreaming: true,
                      contextTokens: 68272,
                      contextWindowTokens: 272000,
                    },
                  });

                  window.__alfredWebUI.emitMessage({
                    type: 'chat.started',
                    payload: { messageId: 'assistant-1', role: 'assistant' },
                  });
                }
                """
            )

            await page.fill("#message-input", "queued follow-up")
            await page.press("#message-input", "Shift+Enter")
            await page.wait_for_timeout(120)

            await page.evaluate(
                """
                () => {
                  window.__alfredWebUI.emitMessage({
                    type: 'status.update',
                    payload: {
                      model: 'kimi-k2-5',
                      queueLength: 0,
                      isStreaming: true,
                    },
                  });
                }
                """
            )
            await page.wait_for_timeout(120)

            data = await page.evaluate(
                """
                () => {
                  const statusBar = document.querySelector('#status-bar');
                  const tooltip = document.getElementById('connection-status-tooltip');
                  return {
                    model: statusBar?.querySelector('.model-name')?.textContent || '',
                    queue: statusBar?.querySelector('.queue-count')?.textContent || '',
                    queueBadge: document.getElementById('queue-badge')?.textContent || '',
                    tooltipText: tooltip?.textContent || '',
                  };
                }
                """
            )

            assert data["model"] == "kimi-k2-5"
            assert data["queue"] == "1"
            assert data["queueBadge"] == "1"
            assert "Daemon: running" in data["tooltipText"]
            assert "PID: 4242" in data["tooltipText"]

            await browser.close()
    finally:
        await _stop_process(process)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_toast_container_shows_and_dismisses_toasts_in_browser() -> None:
    port = _find_free_port()
    process = await _launch_webui(port)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            toast_id = await page.evaluate(
                """
                () => {
                  const container = document.querySelector('#toast-container');
                  if (!container) return null;
                  return container.show('Sparkle parade ready', 'success', 0);
                }
                """
            )

            assert isinstance(toast_id, int)
            await page.wait_for_timeout(120)

            shown = await page.evaluate(
                """
                () => {
                  const toast = document.querySelector('#toast-container .toast-success');
                  return {
                    exists: Boolean(toast),
                    text: toast?.textContent || '',
                    classes: toast?.className || '',
                    toastId: toast?.getAttribute('data-toast-id') || '',
                    enter: toast?.classList.contains('toast-enter') || false,
                  };
                }
                """
            )

            assert shown["exists"] is True
            assert "Sparkle parade ready" in shown["text"]
            assert "toast-success" in shown["classes"]
            assert shown["toastId"] == str(toast_id)
            assert shown["enter"] is True

            await page.evaluate(
                """
                (toastId) => {
                  const container = document.querySelector('#toast-container');
                  container?.dismiss(toastId);
                }
                """,
                toast_id,
            )
            await page.wait_for_timeout(350)

            dismissed = await page.evaluate(
                """
                () => ({
                  count: document.querySelectorAll('#toast-container .toast').length,
                })
                """
            )

            assert dismissed["count"] == 0

            await browser.close()
    finally:
        await _stop_process(process)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_tool_call_component_toggles_and_updates_in_browser() -> None:
    port = _find_free_port()
    process = await _launch_webui(port)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            await page.evaluate(
                """
                () => {
                  const toolCall = document.createElement('tool-call');
                  toolCall.id = 'browser-tool-call';
                  toolCall.setAttribute('tool-call-id', 'call_abc123');
                  toolCall.setAttribute('tool-name', 'read_file');
                  toolCall.setAttribute('arguments', JSON.stringify({ path: '/tmp/demo.txt' }));
                  toolCall.setAttribute('output', 'File contents here');
                  toolCall.setAttribute('status', 'running');
                  toolCall.setAttribute('expanded', 'false');
                  document.body.appendChild(toolCall);
                }
                """
            )
            await page.wait_for_timeout(120)

            collapsed = await page.evaluate(
                """
                () => {
                  const toolCall = document.querySelector('#browser-tool-call');
                  const box = toolCall?.querySelector('.tool-call');
                  return {
                    toolName: toolCall?.querySelector('.tool-name')?.textContent || '',
                    statusIcon: toolCall?.querySelector('.tool-status-icon')?.textContent || '',
                    expanded: toolCall?.getAttribute('expanded') || '',
                    collapsedClass: box?.className || '',
                    toggle: toolCall?.querySelector('.tool-toggle')?.textContent || '',
                  };
                }
                """
            )

            assert collapsed["toolName"] == "read_file"
            assert collapsed["statusIcon"] == ">"  # running status shows ">"
            assert collapsed["expanded"] == "false"
            assert "collapsed" in collapsed["collapsedClass"]
            assert collapsed["toggle"] == "+"

            await page.evaluate(
                """
                () => {
                  const toolCall = document.querySelector('#browser-tool-call');
                  toolCall?.setStatus('success');
                  toolCall?.appendOutput('\\nMore output');
                }
                """
            )
            await page.wait_for_timeout(120)

            updated = await page.evaluate(
                """
                () => {
                  const toolCall = document.querySelector('#browser-tool-call');
                  const box = toolCall?.querySelector('.tool-call');
                  return {
                    statusIcon: toolCall?.querySelector('.tool-status-icon')?.textContent || '',
                    collapsedClass: box?.className || '',
                    toggle: toolCall?.querySelector('.tool-toggle')?.textContent || '',
                  };
                }
                """
            )

            assert updated["statusIcon"] == "ok"  # success status shows "ok"
            assert "success" in updated["collapsedClass"]
            assert updated["toggle"] == "+"  # still collapsed

            # Expand to check output
            await page.click("#browser-tool-call .tool-button")
            await page.wait_for_timeout(80)

            expanded = await page.evaluate(
                """
                () => {
                  const toolCall = document.querySelector('#browser-tool-call');
                  const box = toolCall?.querySelector('.tool-call');
                  return {
                    expanded: toolCall?.getAttribute('expanded') || '',
                    expandedClass: box?.className || '',
                    toggle: toolCall?.querySelector('.tool-toggle')?.textContent || '',
                    outputText: toolCall?.querySelector('.tool-output')?.textContent || '',
                  };
                }
                """
            )

            assert expanded["expanded"] == "true"
            assert "expanded" in expanded["expandedClass"]
            assert expanded["toggle"] == "-"  # expanded shows "-"
            assert "More output" in expanded["outputText"]

            await browser.close()
    finally:
        await _stop_process(process)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_session_loaded_restores_text_blocks_around_tool_calls_in_order() -> None:
    port = _find_free_port()
    process = await _launch_webui(port)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )
            await page.wait_for_function("() => window.__alfredWebUI?.emitMessage !== undefined")

            await page.evaluate(
                """
                () => {
                  window.__alfredWebUI.emitMessage({
                    type: 'session.loaded',
                    payload: {
                      sessionId: 'session-order',
                      messages: [
                        {
                          id: 'assistant-order',
                          role: 'assistant',
                          content: 'Before After',
                          timestamp: '2026-03-21T00:00:01.000Z',
                          reasoningContent: '',
                          textBlocks: [
                            { content: 'Before ', sequence: 0 },
                            { content: 'After', sequence: 2 },
                          ],
                          toolCalls: [
                            {
                              toolCallId: 'tool-1',
                              toolName: 'bash',
                              arguments: { command: 'ls' },
                              output: 'done',
                              status: 'success',
                              insertPosition: 7,
                              sequence: 1,
                            },
                          ],
                          streaming: false,
                        },
                      ],
                    },
                  });
                }
                """
            )
            await page.wait_for_function(
                """
                () => {
                  const assistant = document.querySelector('chat-message[message-id="assistant-order"]');
                  return Boolean(assistant && assistant.querySelectorAll('.content-blocks > *').length === 3);
                }
                """
            )

            blocks = await page.evaluate(
                """
                () => {
                  const assistant = document.querySelector('chat-message[message-id="assistant-order"]');
                  return Array.from(assistant?.querySelectorAll('.content-blocks > *') || []).map((node) => ({
                    tag: node.tagName.toLowerCase(),
                    classes: node.className || '',
                    text: node.textContent || '',
                  }));
                }
                """
            )

            assert len(blocks) == 3
            assert blocks[0]["tag"] == "div"
            assert "text-block" in blocks[0]["classes"]
            assert "Before" in blocks[0]["text"]
            assert blocks[1]["tag"] == "tool-call"
            assert "bash" in blocks[1]["text"]
            assert blocks[2]["tag"] == "div"
            assert "text-block" in blocks[2]["classes"]
            assert "After" in blocks[2]["text"]

            await browser.close()
    finally:
        await _stop_process(process)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_webui_launch_path_starts_daemon_from_cold_state(tmp_path: Path) -> None:
    port = _find_free_port()
    env = _build_launch_env(tmp_path)
    process = await _launch_webui(port, env=env)
    pid_file = Path(env["XDG_CACHE_HOME"]) / "alfred" / "cron-runner.pid"

    try:
        health = await _wait_for_health(
            port,
            timeout=30.0,
            predicate=lambda data: data["daemonStatus"] == "running",
        )

        assert health["status"] == "ok"
        assert health["daemonStatus"] == "running"
        assert health["daemon"]["state"] == "running"
        assert isinstance(health["daemonPid"], int)

        daemon_pid = cast(int, health["daemonPid"])
        assert pid_file.exists()
        assert pid_file.read_text().strip() == str(daemon_pid)
        os.kill(daemon_pid, 0)
    finally:
        await _stop_daemon(env)
        await _stop_process(process)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_webui_launch_path_still_serves_health_after_bootstrap_failure(tmp_path: Path) -> None:
    port = _find_free_port()
    failure_message = "daemon failed to start"
    env = _build_launch_env(tmp_path, bootstrap_failure_message=failure_message)
    process = await _launch_webui(port, env=env)

    try:
        health = await _wait_for_health(
            port,
            timeout=30.0,
            predicate=lambda data: data["daemonStatus"] == "failed",
        )

        assert health["status"] == "ok"
        assert health["daemonStatus"] == "failed"
        assert health["daemonPid"] is None
        assert health["daemon"]["state"] == "failed"
        assert health["daemon"]["lastError"] == failure_message
    finally:
        await _stop_daemon(env)
        await _stop_process(process)
