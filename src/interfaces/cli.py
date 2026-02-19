"""CLI interface for Alfred."""

import asyncio
import os

from src.alfred import Alfred


class Colors:
    """ANSI color codes for terminal output."""

    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    RED = "\033[31m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    @classmethod
    def disable_if_not_tty(cls) -> None:
        """Disable colors if stdout is not a TTY."""
        if not os.isatty(1):
            cls.CYAN = ""
            cls.GREEN = ""
            cls.YELLOW = ""
            cls.BLUE = ""
            cls.MAGENTA = ""
            cls.RED = ""
            cls.RESET = ""
            cls.BOLD = ""


Colors.disable_if_not_tty()


def async_print(message: str) -> None:
    """DEPRECATED: Thread-safe print using direct syscall.

    Previously used to avoid deadlocks when input() ran in a thread.
    Kept for reference. Use regular print() instead - the stdout
    corruption issue has been fixed in src/cron/executor.py by
    isolating job output buffers.

    ARCHITECTURE (for historical reference):
        Python's I/O stack is layered:
            Layer 4: print() → acquires threading.RLock on stdout
            Layer 3: io.TextIOWrapper → encoding/decoding buffer
            Layer 2: io.BufferedWriter → internal buffer + GIL interaction
            Layer 1: FileIO → raw fd operations with C stdio lock
            Layer 0: Kernel fd → syscall interface

    THE BUG (fixed):
        Cron jobs used redirect_stdout() which mutated global sys.stdout.
        When jobs ran concurrently, nested redirects corrupted stdout state,
        causing print() to silently fail.

    THE FIX:
        Jobs now get injected stdout/stderr buffers in their namespace.
        No global state mutation. No locks needed.
    """
    import os

    os.write(1, message.encode("utf-8"))


async def async_input(prompt: str) -> str:
    """Async wrapper around input() that properly handles piped stdin."""
    print(prompt, end="")
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input())


class CLIInterface:
    """CLI interface - delegates to Alfred engine with streaming."""

    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred

    async def run(self) -> None:
        """Run interactive CLI with streaming."""
        print("Alfred CLI. Type 'exit' to quit, 'compact' to compact.\n")

        while True:
            try:
                # BOLD and ALL CAPS for prompt
                prompt = f"{Colors.BOLD}{Colors.GREEN}YOU:{Colors.RESET} "
                user_input = (await async_input(prompt)).strip()
            except EOFError:
                break

            if not user_input:
                continue

            if user_input.lower() == "exit":
                print("Goodbye!")
                break

            if user_input.lower() == "compact":
                result = await self.alfred.compact()
                print(f"ALFRED: {result}\n")
                continue

            # Stream response - BOLD and ALL CAPS
            response_prefix = (
                f"{Colors.BOLD}{Colors.CYAN}ALFRED:{Colors.RESET} "
            )

            # Create stream generator - using typing.cast to tell mypy
            # this is an AsyncGenerator which has aclose() method
            from collections.abc import AsyncGenerator
            from typing import cast

            stream = cast(
                AsyncGenerator[str, None], self.alfred.chat_stream(user_input)
            )
            try:
                print(response_prefix, end="")
                async for chunk in stream:
                    print(chunk, end="")
                print()
            except Exception as e:
                print(f"\n[Error: {e}]\n")
            finally:
                # Ensure the stream generator is properly closed
                # This prevents hanging when stdin is redirected
                if hasattr(stream, "aclose"):
                    await stream.aclose()
