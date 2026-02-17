"""CLI interface for Alfred."""

import asyncio
import logging

from src.alfred import Alfred
from src.config import Config

logger = logging.getLogger(__name__)


class CLIInterface:
    """CLI interface - delegates to Alfred engine."""

    def __init__(self, config: Config, alfred: Alfred) -> None:
        self.config = config
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


async def main() -> None:
    """Entry point."""
    from src.config import load_config

    logging.basicConfig(level=logging.INFO)

    config = load_config()
    alfred = Alfred(config)
    interface = CLIInterface(config, alfred)

    await interface.run()


if __name__ == "__main__":
    asyncio.run(main())
