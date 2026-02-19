"""Regression tests for CLI threading/buffering issues.

These tests verify that the CLI correctly handles output when input() runs
in a separate thread via run_in_executor(). This addresses a known Python
bug where print() can deadlock or silently drop output in threaded scenarios.

References:
    - https://github.com/python/cpython/issues/85711
    - https://bugs.python.org/issue41539
"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestCLIThreadingRegression:
    """Test that CLI output works correctly with threaded input."""

    @pytest.mark.timeout(30)
    def test_piped_input_produces_output(self) -> None:
        """Regression test: CLI should produce visible output with piped input.

        Bug: When input() runs in a thread via run_in_executor(), Python's
        print() can deadlock or silently drop output due to stdout buffer
        lock contention with C stdio.

        This test verifies the fix using os.write(1, ...) instead of print().
        """
        # Run alfred with piped input
        result = subprocess.run(
            [sys.executable, "-m", "src", "--debug", "info"],
            input="hello\nexit\n",
            capture_output=True,
            text=True,
            timeout=20,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Should get response output (not just exit)
        # async_print uses os.write(1, ...) which goes to stdout (fd 1)
        output = result.stdout + result.stderr
        assert "ALFRED:" in output, (
            "CLI should produce ALFRED: output. "
            f"stdout was: {result.stdout[:500]}, stderr was: {result.stderr[:500]}"
        )
        assert result.returncode == 0

    @pytest.mark.timeout(30)
    def test_streaming_output_not_buffered(self) -> None:
        """Test that response streams immediately, not batched at end.

        Bug: If output is buffered, all chunks arrive at once after the
        full response is received. With proper streaming, output appears
        progressively.
        """
        # This is harder to test definitively, but we can at least verify
        # that the output contains the expected response content
        result = subprocess.run(
            [sys.executable, "-m", "src", "--debug", "info"],
            input="say hi\nexit\n",
            capture_output=True,
            text=True,
            timeout=20,
            cwd=Path(__file__).parent.parent.parent,
        )

        # async_print uses os.write(1, ...) which goes to stdout
        output = result.stdout

        # Should see ALFRED: prefix
        assert "ALFRED:" in output

        # Should see actual response content (not empty)
        alfred_lines = [line for line in output.split("\n") if "ALFRED:" in line]
        assert len(alfred_lines) > 0

        # Response should have content after ALFRED:
        for line in alfred_lines:
            content = line.split("ALFRED:", 1)[1].strip()
            # Should have actual text, not just empty
            assert len(content) > 0 or "YOU:" in line

    @pytest.mark.timeout(30)
    def test_multiple_inputs_all_produce_output(self) -> None:
        """Test that multiple piped inputs each get responses.

        Bug: EOFError occurs on second input when print() corrupts stdout state.
        """
        result = subprocess.run(
            [sys.executable, "-m", "src", "--debug", "info"],
            input="hello\nhow are you\nexit\n",
            capture_output=True,
            text=True,
            timeout=25,
            cwd=Path(__file__).parent.parent.parent,
        )

        # async_print uses os.write(1, ...) which goes to stdout
        output = result.stdout

        # Count ALFRED: occurrences - should be at least 2
        alfred_count = output.count("ALFRED:")
        assert alfred_count >= 2, (
            f"Expected at least 2 ALFRED: responses, got {alfred_count}. "
            f"stdout: {output[:1000]}"
        )

    def test_async_print_uses_direct_fd_write(self) -> None:
        """Unit test: Verify async_print uses os.write, not print().

        This tests the implementation directly to ensure the fix is in place.
        """
        import os

        from src.interfaces.cli import async_print

        # Mock os.write to capture what's being written
        written = []
        original_write = os.write

        def mock_write(fd: int, data: bytes) -> int:
            written.append((fd, data))
            return len(data)

        os.write = mock_write  # type: ignore

        try:
            async_print("test message\n")

            # Should have written to fd 1 (stdout)
            assert len(written) == 1
            assert written[0][0] == 1  # stdout fd
            assert written[0][1] == b"test message\n"
        finally:
            os.write = original_write  # type: ignore


class TestAsyncInputFunction:
    """Tests for the async_input helper function."""

    @pytest.mark.asyncio
    async def test_async_input_reads_from_stdin(self, monkeypatch) -> None:
        """Test that async_input correctly reads input."""
        from src.interfaces.cli import async_input

        # Mock input() to return test value
        monkeypatch.setattr("builtins.input", lambda: "test input")

        result = await async_input("prompt: ")
        assert result == "test input"

    @pytest.mark.asyncio
    async def test_async_input_raises_eof_on_empty_stdin(self, monkeypatch) -> None:
        """Test that async_input properly raises EOFError."""
        from src.interfaces.cli import async_input

        # Mock input() to raise EOFError (simulates piped EOF)
        def raise_eof():
            raise EOFError()

        monkeypatch.setattr("builtins.input", raise_eof)

        with pytest.raises(EOFError):
            await async_input("prompt: ")
