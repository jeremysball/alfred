"""Core Alfred engine - orchestrates memory, context, and LLM with agent loop."""

import logging
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

from telegram import Bot

from src.agent import Agent, ToolEvent
from src.config import Config
from src.context import ContextLoader
from src.cron.notifier import CLINotifier, Notifier, TelegramNotifier
from src.cron.scheduler import CronScheduler
from src.cron.store import CronStore
from src.embeddings import EmbeddingClient
from src.llm import ChatMessage, LLMFactory
from src.memory import MemoryStore
from src.search import MemorySearcher
from src.session import SessionManager
from src.token_tracker import TokenTracker
from src.tools import get_registry, register_builtin_tools

# Default prompt sections loaded by ContextLoader
DEFAULT_PROMPT_SECTIONS = ["AGENTS", "SOUL", "USER", "TOOLS"]


class ContextSummary:
    """Summary of loaded context for status display."""

    def __init__(self) -> None:
        self.memories_count: int = 0
        self.session_messages: int = 0
        self.prompt_sections: list[str] = DEFAULT_PROMPT_SECTIONS.copy()

    def update(self, memories_count: int, session_messages: int) -> None:
        """Update context summary values."""
        self.memories_count = memories_count
        self.session_messages = session_messages


logger = logging.getLogger(__name__)


class Alfred:
    """Core Alfred engine - handles memory, context, LLM, and agent loop."""

    def __init__(self, config: Config, telegram_mode: bool = False) -> None:
        self.config = config
        self.llm = LLMFactory.create(config)

        # Initialize memory system
        self.embedder = EmbeddingClient(config)
        self.memory_store = MemoryStore(config, self.embedder)
        self.searcher = MemorySearcher(
            context_limit=config.memory_context_limit,
            min_similarity=0.3,
        )
        self.context_loader = ContextLoader(config, searcher=self.searcher)

        # Initialize data directory
        data_dir = getattr(config, "data_dir", Path("data"))

        # Create notifier based on mode
        notifier: Notifier
        self._telegram_bot: Bot | None = None

        if telegram_mode:
            try:
                self._telegram_bot = Bot(token=config.telegram_bot_token)
                # Read chat_id from telegram state file
                state_file = data_dir / "telegram_state.json"
                chat_id: int | None = None
                if state_file.exists():
                    import json

                    with open(state_file) as f:
                        chat_id = json.load(f).get("chat_id")

                notifier = TelegramNotifier(
                    bot=self._telegram_bot,
                    default_chat_id=chat_id,
                )
                logger.info("TelegramNotifier initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize TelegramNotifier, falling back to CLI: {e}")
                notifier = CLINotifier()
        else:
            notifier = CLINotifier()
            logger.info("CLINotifier initialized")

        # Initialize cron scheduler with notifier
        self.cron_scheduler = CronScheduler(
            store=CronStore(data_dir),
            data_dir=data_dir,
            notifier=notifier,
        )

        # Register built-in tools (inject memory store and scheduler)
        register_builtin_tools(
            memory_store=self.memory_store,
            scheduler=self.cron_scheduler,
        )
        self.tools = get_registry()

        # Create agent
        self.agent = Agent(self.llm, self.tools, max_iterations=10)

        # Session manager for conversation history
        self.session_manager = SessionManager.get_instance()

        # Token tracking for usage display
        self.token_tracker = TokenTracker()

        # Context summary for status display
        self.context_summary = ContextSummary()

    @property
    def model_name(self) -> str:
        """Get full model display name (provider/model)."""
        return f"{self.config.default_llm_provider}/{self.config.chat_model}"

    def _on_usage(self, usage: dict[str, Any]) -> None:
        """Callback for LLM usage updates."""
        self.token_tracker.add(usage)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count from character count.

        Uses 4 chars per token as rough approximation.
        """
        return len(text) // 4

    def _update_context_tokens(self, system_prompt: str, messages: list[ChatMessage]) -> None:
        """Update context token estimate.

        Args:
            system_prompt: Full system prompt text
            messages: Conversation messages
        """
        total_chars = len(system_prompt)
        for msg in messages:
            total_chars += len(msg.content)
            if msg.tool_calls:
                total_chars += len(str(msg.tool_calls))

        self.token_tracker.set_context_tokens(self._estimate_tokens(system_prompt + str(messages)))

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

    async def chat_stream(
        self,
        message: str,
        tool_callback: Callable[[ToolEvent], None] | None = None,
    ) -> AsyncIterator[str]:
        """Process a message with streaming.

        Args:
            message: User message
            tool_callback: Optional callback for tool execution events

        Yields:
            LLM response tokens
        """
        logger.info(f"Processing message: {message[:50]}...")

        # Start session on first message
        if not self.session_manager.has_active_session():
            logger.debug("Starting new session...")
            self.session_manager.start_session()

        # Add user message to session
        self.session_manager.add_message("user", message)
        msg_count = len(self.session_manager.get_messages())
        logger.debug(f"Added user message. Session now has {msg_count} messages")

        # Get query embedding for memory search
        logger.debug("Generating query embedding...")
        query_embedding = await self.embedder.embed(message)

        # Load all memories
        logger.debug("Loading memories...")
        all_memories = await self.memory_store.get_all_entries()
        logger.info(f"Loaded {len(all_memories)} memories from store")

        # Build context with memory search and session history
        logger.debug("Assembling context with memory search...")
        session_messages = self._get_session_messages_for_context()
        system_prompt, memories_count = self.context_loader.assemble_with_search(
            query_embedding=query_embedding,
            memories=all_memories,
            session_messages=session_messages,
        )
        system_prompt = self._build_system_prompt(system_prompt)

        messages = [ChatMessage(role="user", content=message)]

        # Update context token estimate for status display
        self._update_context_tokens(system_prompt, messages)

        # Update context summary for status display
        self.context_summary.update(
            memories_count=memories_count,
            session_messages=len(session_messages),
        )

        logger.debug("Starting agent loop...")
        full_response = []
        async for chunk in self.agent.run_stream(
            messages,
            system_prompt,
            usage_callback=self._on_usage,
            tool_callback=tool_callback,
        ):
            full_response.append(chunk)
            yield chunk

        # Add assistant response to session
        assistant_message = "".join(full_response)
        self.session_manager.add_message("assistant", assistant_message)
        msg_count = len(self.session_manager.get_messages())
        logger.debug(f"Added assistant message. Session now has {msg_count} messages")

    def _build_system_prompt(self, base_prompt: str) -> str:
        """Build system prompt with tool descriptions."""
        tool_descriptions = []
        for tool in self.tools.list_tools():
            # Get parameter summary
            params = tool.param_model
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

To use a tool, respond with a tool call. The system will execute the tool
and return the results to you.
You can then continue the conversation with the tool results.
"""

    async def compact(self) -> str:
        """Trigger conversation compaction."""
        # TODO: Implement in M9
        return "Compaction not yet implemented"

    def _get_session_messages_for_context(self) -> list[tuple[str, str]]:
        """Get session messages formatted for context injection.

        Returns:
            List of (role, content) tuples for session history.
        """
        if not self.session_manager.has_active_session():
            return []

        messages = self.session_manager.get_messages()
        # Convert to (role, content) tuples, excluding the most recent user message
        # (which is the current query being processed)
        result = []
        for msg in messages[:-1] if messages else []:  # Exclude last (current) message
            result.append((msg.role.value, msg.content))
        return result

    async def start(self) -> None:
        """Start Alfred and all subsystems.

        Initializes the cron scheduler and starts background tasks.
        Failures are logged but don't prevent Alfred from starting.
        """
        try:
            await self.cron_scheduler.start()
            logger.info("Cron scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start cron scheduler: {e}")

    async def stop(self) -> None:
        """Graceful shutdown.

        Stops all subsystems cleanly.
        """
        try:
            await self.cron_scheduler.stop()
            logger.info("Cron scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping cron scheduler: {e}")
