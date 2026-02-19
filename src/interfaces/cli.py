"""CLI interface for Alfred."""

from aioconsole import ainput  # type: ignore[import-untyped]

from src.alfred import Alfred


class CLIInterface:
    """CLI interface - delegates to Alfred engine with streaming."""

    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred

    async def run(self) -> None:
        """Run interactive CLI with streaming."""
        print("Alfred CLI. Type 'exit' to quit, 'compact' to compact.\n")

        while True:
            try:
                user_input = (await ainput("You: ")).strip()
            except EOFError:
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

            # Stream response
            print("Alfred: ", end="", flush=True)

            try:
                async for chunk in self.alfred.chat_stream(user_input):
                    print(chunk, end="", flush=True)
                print("\n")  # New line after response
            except Exception as e:
                print(f"\n[Error: {e}]\n")
