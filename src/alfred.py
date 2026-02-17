"""Core Alfred engine - orchestrates memory, context, and LLM."""

import logging

from src.config import Config
from src.context import ContextLoader
from src.llm import ChatMessage, ChatResponse, LLMFactory

logger = logging.getLogger(__name__)


class Alfred:
    """Core Alfred engine - handles memory, context, and LLM."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.llm = LLMFactory.create(config)
        self.context_loader = ContextLoader(config)

    async def chat(self, message: str) -> ChatResponse:
        """Process a message and return response.

        This is the main entry point for any interface.
        Handles: load context → build prompt → call LLM → return response
        """
        # 1. Load context (agents, soul, user, tools)
        context = await self.context_loader.assemble()

        # 2. Build messages
        messages = [
            ChatMessage(role="system", content=context.system_prompt),
            ChatMessage(role="user", content=message),
        ]

        # 3. Call LLM
        response = await self.llm.chat(messages)

        logger.info(f"Chat completed: {response.usage}")
        return response

    async def compact(self) -> str:
        """Trigger conversation compaction."""
        # TODO: Implement in M9
        return "Compaction not yet implemented"
