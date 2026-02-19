"""CLI interface for Alfred using prompt_toolkit for async input."""

import sys
from contextlib import redirect_stdout
from typing import TextIO

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from src.alfred import Alfred


class _StdoutTee:
    """Tee stdout to both original stdout and a buffer."""

    def __init__(self, original: TextIO) -> None:
        self.original = original
        self.buffer: list[str] = []

    def write(self, s: str) -> int:
        self.buffer.append(s)
        result: int = self.original.write(s)
        return result

    def flush(self) -> None:
        self.original.flush()

    def isatty(self) -> bool:
        result: bool = self.original.isatty()
        return result


class CLIInterface:
    """CLI interface with async prompt and streaming output capture."""

    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred
        self.session: PromptSession[str] = PromptSession("You: ")

    async def run(self) -> None:
        """Run interactive CLI with async input and streaming output."""
        print("Alfred CLI. Type 'exit' to quit, 'compact' to compact.\n")

        while True:
            try:
                # Use patch_stdout to allow streaming output during prompt
                with patch_stdout():
                    user_input = await self.session.prompt_async()
                user_input = user_input.strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() == "exit":
                print("Goodbye!")
                break

            if user_input.lower() == "compact":
                result = await self.alfred.compact()
                print(f"Alfred: {result}\n")
                continue

            # Stream response with stdout capture
            print("Alfred: ", end="", flush=True)

            # Tee stdout to both display and buffer
            original_stdout = sys.stdout
            tee = _StdoutTee(original_stdout)

            try:
                with redirect_stdout(tee):
                    async for chunk in self.alfred.chat_stream(user_input):
                        print(chunk, end="", flush=True)
                print("\n")  # New line after response
            except Exception as e:
                print(f"\n[Error: {e}]\n")
            finally:
                sys.stdout = original_stdout
