"""CLI interface for Alfred using prompt_toolkit for async input."""

import sys
from contextlib import redirect_stdout
from typing import TextIO

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.alfred import Alfred

# Styling for prompt_toolkit input
PROMPT_STYLE = Style.from_dict({
    "prompt": "ansicyan bold",
    "cursor": "ansigreen",
})


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
        self.console = Console()
        self.session: PromptSession[str] = PromptSession(
            message=[("class:prompt", "You: ")],
            style=PROMPT_STYLE,
        )

    def _print_banner(self) -> None:
        """Print a welcoming banner."""
        banner = Panel(
            Text(
                "🎩 Alfred - Your Persistent Memory Assistant",
                style="bold cyan",
                justify="center",
            ),
            subtitle="Type 'exit' to quit • 'compact' to compact memory",
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(banner)
        self.console.print()

    async def run(self) -> None:
        """Run interactive CLI with async input and streaming output."""
        self._print_banner()

        while True:
            try:
                # Use patch_stdout to allow streaming output during prompt
                with patch_stdout():
                    user_input = await self.session.prompt_async()
                user_input = user_input.strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                self.console.print("\n[bold yellow]Goodbye! 👋[/bold yellow]")
                break

            if not user_input:
                continue

            if user_input.lower() == "exit":
                self.console.print("[bold yellow]Goodbye! 👋[/bold yellow]")
                break

            if user_input.lower() == "compact":
                result = await self.alfred.compact()
                self.console.print(f"[bold green]Alfred:[/bold green] {result}\n")
                continue

            # Stream response with stdout capture
            self.console.print("[bold magenta]Alfred:[/bold magenta] ", end="")

            # Tee stdout to both display and buffer
            original_stdout = sys.stdout
            tee = _StdoutTee(original_stdout)

            try:
                with redirect_stdout(tee):
                    async for chunk in self.alfred.chat_stream(user_input):
                        print(chunk, end="", flush=True)
                print("\n")  # New line after response
            except Exception as e:
                self.console.print(f"\n[bold red][Error: {e}][/bold red]\n")
            finally:
                sys.stdout = original_stdout
