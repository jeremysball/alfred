"""Core Alfred engine - orchestrates memory, context, and LLM with agent loop."""

import logging
from collections.abc import AsyncIterator
from typing import Optional

from src.agent import Agent
from src.config import Config
from src.context import ContextLoader
from src.embeddings import EmbeddingClient
from src.llm import ChatMessage, ChatResponse, LLMFactory
from src.memory import MemoryStore
from src.search import MemorySearcher
from src.tools import get_registry, register_builtin_tools

logger = logging.getLogger(__name__)


class Alfred:
    """Core Alfred engine - handles memory, context, LLM, and agent loop."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.llm = LLMFactory.create(config)

        # Initialize memory system
        self.embedder = EmbeddingClient(config)
        self.memory_store = MemoryStore(config, self.embedder)
        self.searcher = MemorySearcher(
            context_limit=config.memory_context_limit,
            min_similarity=0.7,
        )
        self.context_loader = ContextLoader(config, searcher=self.searcher)

        # Register built-in tools
        register_builtin_tools()
        self.tools = get_registry()

        # Create agent
        self.agent = Agent(self.llm, self.tools, max_iterations=10)

    async def chat(self, message: str) -> str:
        """Process a message with full agent loop (non-streaming).
        
        Returns:
            Complete response as string
        """
        # Load context
        context = await self.context_loader.assemble()

        # Build system prompt with tool descriptions
        system_prompt = self._build_system_prompt(context.system_prompt)

        # Run agent loop
        messages = [ChatMessage(role="user", content=message)]

        response = await self.agent.run(messages, system_prompt)

        return response

    async def chat_stream(self, message: str) -> AsyncIterator[str]:
        """Process a message with streaming.

        Yields:
            - LLM response tokens
            - Tool execution status
            - Tool output in real-time
        """
        logger.info(f"Processing message: {message[:50]}...")

        # Get query embedding for memory search
        logger.debug("Generating query embedding...")
        query_embedding = await self.embedder.embed(message)

        # Load all memories
        logger.debug("Loading memories...")
        all_memories = await self.memory_store.get_all_entries()
        logger.info(f"Loaded {len(all_memories)} memories from store")

        # Build context with memory search
        logger.debug("Assembling context with memory search...")
        system_prompt = self.context_loader.assemble_with_search(
            query_embedding=query_embedding,
            memories=all_memories,
        )
        system_prompt = self._build_system_prompt(system_prompt)

        messages = [ChatMessage(role="user", content=message)]

        logger.debug("Starting agent loop...")
        async for chunk in self.agent.run_stream(messages, system_prompt):
            yield chunk

    def _build_system_prompt(self, base_prompt: str) -> str:
        """Build system prompt with tool descriptions."""
        tool_descriptions = []
        for tool in self.tools.list_tools():
            # Get parameter summary
            params = tool._param_model
            if params:
                param_list = []
                for name, field in params.model_fields.items():
                    param_type = "any"
                    if hasattr(field, "annotation") and field.annotation:
                        ann = field.annotation
                        if hasattr(ann, "__name__"):
                            param_type = ann.__name__.lower()
                        else:
                            param_type = str(ann).lower()
                    param_list.append(f"{name}: {param_type}")
                
                params_str = ", ".join(param_list)
                tool_descriptions.append(f"- {tool.name}({params_str}): {tool.description}")
            else:
                tool_descriptions.append(f"- {tool.name}: {tool.description}")

        tools_section = "\n".join(tool_descriptions)

        return f"""{base_prompt}

## Available Tools

You have access to the following tools. Use them when needed to accomplish the user's request.

{tools_section}

To use a tool, respond with a tool call. The system will execute the tool and return the results to you.
You can then continue the conversation with the tool results.
"""

    async def compact(self) -> str:
        """Trigger conversation compaction."""
        # TODO: Implement in M9
        return "Compaction not yet implemented"
