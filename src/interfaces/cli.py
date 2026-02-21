"""CLI interface for Alfred using prompt_toolkit for async input."""

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.alfred import Alfred
from src.utils.markdown import MarkdownRenderer

# Styling for prompt_toolkit input
PROMPT_STYLE = Style.from_dict({
    "prompt": "ansicyan bold",
    "cursor": "ansigreen",
})


class CLIInterface:
    """CLI interface with async prompt and streaming output capture."""

    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred
        self.console = Console()
        self.markdown_renderer = MarkdownRenderer(self.console)
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

            # Buffer for markdown rendering
            response_buffer = ""

            try:
                async for chunk in self.alfred.chat_stream(user_input):
                    # Print chunk for streaming feel
                    print(chunk, end="", flush=True)
                    response_buffer += chunk

                # Render complete response as markdown
                if response_buffer:
                    rendered = self.markdown_renderer.render(response_buffer)
                    # Clear current line and print rendered markdown
                    print("\r\033[K", end="")  # Carriage return + clear line
                    print(rendered, end="")
                print("\n")  # New line after response
            except Exception as e:
                self.console.print(f"\n[bold red][Error: {e}][/bold red]\n")
