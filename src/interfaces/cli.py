"""CLI interface for Alfred."""

from src.alfred import Alfred


class CLIInterface:
    """CLI interface - delegates to Alfred engine."""

    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred

    async def run(self) -> None:
        """Run interactive CLI."""
        print("Alfred CLI. Type 'exit' to quit, 'compact' to compact.\n")

        while True:
            try:
                user_input = input("You: ").strip()
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

            response = await self.alfred.chat(user_input)
            print(f"Alfred: {response.content}\n")
