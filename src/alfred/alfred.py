"""Core Alfred engine - orchestrates memory, context, and LLM with agent loop."""

import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from telegram import Bot

from alfred.agent import Agent, ToolEnd, ToolEvent, ToolOutput, ToolStart
from alfred.config import Config
from alfred.container import ServiceLocator
from alfred.context import ContextLoader
from alfred.cron.scheduler import CronScheduler
from alfred.cron.store import CronStore
from alfred.embeddings import create_provider
from alfred.llm import ChatMessage, LLMFactory
from alfred.memory import create_memory_store
from alfred.session import Session, SessionManager, ToolCallRecord
from alfred.storage.sqlite import SQLiteStore
from alfred.token_tracker import TokenTracker
from alfred.tools import get_registry, register_builtin_tools
from alfred.tools.factories import SummarizerFactory
from alfred.tools.search_sessions import SessionSummarizer

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
        self.embedder = create_provider(config)
        self.memory_store = create_memory_store(config, self.embedder)

        # Initialize SQLiteStore for context loading
        self.sqlite_store = SQLiteStore(config.data_dir / "alfred.db")
        self.context_loader = ContextLoader(config, store=self.sqlite_store)

        # Initialize data directory
        data_dir = config.data_dir

        # Initialize Telegram bot if in telegram mode
        self._telegram_bot: Bot | None = None
        if telegram_mode:
            try:
                self._telegram_bot = Bot(token=config.telegram_bot_token)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Telegram bot: {e}")

        # Initialize cron scheduler (uses socket for TUI communication)
        self.cron_scheduler = CronScheduler(
            store=CronStore(data_dir),
            data_dir=data_dir,
        )

        # Initialize session manager FIRST (before tools that need it)
        SessionManager.initialize(data_dir=data_dir)
        self.session_manager = SessionManager.get_instance()

        # Create summarizer via factory
        self.summarizer_factory = SummarizerFactory(
            store=self.sqlite_store,
            llm_client=self.llm,
            embedder=self.embedder,
        )
        self.summarizer = self.summarizer_factory.create()

        # Register services in ServiceLocator for cron jobs
        ServiceLocator.register(SessionSummarizer, self.summarizer)
        ServiceLocator.register(SessionManager, self.session_manager)
        ServiceLocator.register(SQLiteStore, self.sqlite_store)

        # Register built-in tools (inject memory store, scheduler, and config)
        register_builtin_tools(
            memory_store=self.memory_store,
            scheduler=self.cron_scheduler,
            config=self.config,
            session_manager=self.session_manager,
            embedder=self.embedder,
            llm_client=self.llm,
            summarizer=self.summarizer,
        )
        self.tools = get_registry()

        # Create agent
        self.agent = Agent(self.llm, self.tools, max_iterations=-1)

        # Token tracking for usage display
        self.token_tracker = TokenTracker()
        self._last_usage: dict[str, Any] | None = None

        # Context summary for status display
        self.context_summary = ContextSummary()

    @property
    def model_name(self) -> str:
        """Get full model display name (provider/model)."""
        return f"{self.config.default_llm_provider}/{self.config.chat_model}"

    def _on_usage(self, usage: dict[str, Any]) -> None:
        """Callback for LLM usage updates."""
        self.token_tracker.add(usage)
        # Store the last usage for message token tracking
        self._last_usage = usage

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count from character count.

        Uses 4 chars per token as rough approximation.
        """
        return len(text) // 4

    def sync_token_tracker_from_session(self, session_id: str | None = None) -> None:
        """Sync token tracker with historical session messages.

        Uses stored token counts from messages. Legacy messages without
        stored counts contribute 0 (no estimation). Called when resuming
        a session so the status line shows the total accumulated usage.

        Args:
            session_id: Optional session ID. If None, uses current CLI session.
        """
        from alfred.session import Role

        messages = self.session_manager.get_session_messages(session_id)
        if not messages:
            return

        input_tokens = 0
        output_tokens = 0
        cached_tokens = 0
        reasoning_tokens = 0

        for msg in messages:
            # Use stored count if available (> 0), otherwise 0 (no estimation)
            if msg.role == Role.USER and msg.input_tokens > 0:
                input_tokens += msg.input_tokens
            elif msg.role == Role.ASSISTANT and msg.output_tokens > 0:
                output_tokens += msg.output_tokens
            # Accumulate cached and reasoning tokens from all messages that have them
            cached_tokens += getattr(msg, "cached_tokens", 0)
            reasoning_tokens += getattr(msg, "reasoning_tokens", 0)

        # Reset and set total tokens for the session
        self.token_tracker.reset()
        self.token_tracker.add(
            {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "prompt_tokens_details": {"cached_tokens": cached_tokens},
                "completion_tokens_details": {"reasoning_tokens": reasoning_tokens},
            }
        )

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
        session_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Process a message with streaming.

        Args:
            message: User message
            tool_callback: Optional callback for tool execution events
            session_id: Optional session ID (for Telegram chat_id). If None, uses CLI session.

        Yields:
            LLM response tokens
        """
        logger.info(f"Processing message: {message[:50]}...")

        # Handle session based on mode
        if session_id:
            # Telegram mode - use provided session_id (chat_id)
            self.session_manager.get_or_create_session(session_id)
        else:
            # CLI mode - use singleton session
            if not self.session_manager.has_active_session():
                logger.debug("Starting new session...")
                self.session_manager.start_session()

        # Add user message to session and get its index
        self.session_manager.add_message("user", message, session_id=session_id)
        messages_list = self.session_manager.get_session_messages(session_id)
        user_msg_idx = messages_list[-1].idx if messages_list else 0
        msg_count = len(messages_list)
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
        session_messages = self.session_manager.get_messages_for_context(session_id)
        # Get full messages with tool_calls for context
        session_messages_with_tools = self.session_manager.get_messages_with_tools_for_context(
            session_id
        )
        system_prompt, memories_count = self.context_loader.assemble_with_search(
            query_embedding=query_embedding,
            memories=all_memories,
            session_messages=session_messages,
            session_messages_with_tools=session_messages_with_tools,
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

        # Accumulator for tool calls during this turn
        tool_calls_accumulator: list[dict[str, Any]] = []
        full_response: list[str] = []

        def _tool_callback_wrapper(event: ToolEvent) -> None:
            """Wrapper to capture tool calls while still calling external callback."""
            nonlocal full_response

            # Call external callback if provided
            if tool_callback:
                tool_callback(event)

            # Capture tool call data
            if isinstance(event, ToolStart):
                # Calculate insert position based on current response length
                insert_position = len("".join(full_response))

                # Find sequence number for tools at same position
                sequence = sum(
                    1
                    for tc in tool_calls_accumulator
                    if tc.get("insert_position") == insert_position
                )

                tool_calls_accumulator.append(
                    {
                        "tool_call_id": event.tool_call_id,
                        "tool_name": event.tool_name,
                        "arguments": event.arguments,
                        "output_chunks": [],
                        "insert_position": insert_position,
                        "sequence": sequence,
                        "is_error": False,
                    }
                )

            elif isinstance(event, ToolOutput):
                # Find matching tool call and append output
                for tc in tool_calls_accumulator:
                    if tc["tool_call_id"] == event.tool_call_id:
                        tc["output_chunks"].append(event.chunk)
                        break

            elif isinstance(event, ToolEnd):
                # Finalize tool call with status
                for tc in tool_calls_accumulator:
                    if tc["tool_call_id"] == event.tool_call_id:
                        tc["is_error"] = event.is_error
                        break

        async for chunk in self.agent.run_stream(
            messages,
            system_prompt,
            usage_callback=self._on_usage,
            tool_callback=_tool_callback_wrapper,
        ):
            full_response.append(chunk)
            yield chunk

        # Build ToolCallRecord objects from accumulated data
        tool_calls: list[ToolCallRecord] | None = None
        if tool_calls_accumulator:
            tool_calls = [
                ToolCallRecord(
                    tool_call_id=tc["tool_call_id"],
                    tool_name=tc["tool_name"],
                    arguments=tc["arguments"],
                    output="".join(tc["output_chunks"]),
                    status="error" if tc["is_error"] else "success",
                    insert_position=tc["insert_position"],
                    sequence=tc["sequence"],
                )
                for tc in tool_calls_accumulator
            ]

        # Add assistant response to session with tool calls
        assistant_message = "".join(full_response)

        # Create message manually to include tool_calls
        from datetime import UTC, datetime

        from alfred.session import Message, Role

        messages_list = self.session_manager.get_session_messages(session_id)
        idx = messages_list[-1].idx + 1 if messages_list else 0

        assistant_msg_obj = Message(
            idx=idx,
            role=Role.ASSISTANT,
            content=assistant_message,
            timestamp=datetime.now(UTC),
            tool_calls=tool_calls,
        )

        # Get session and append message
        session: Session
        if session_id:
            session = self.session_manager.get_or_create_session(session_id)
        else:
            maybe_session = self.session_manager.get_current_cli_session()
            if maybe_session is None:
                raise RuntimeError("No active session")
            session = maybe_session

        session.messages.append(assistant_msg_obj)
        session.meta.last_active = datetime.now(UTC)
        session.meta.message_count = len(session.messages)

        # Persist to storage
        self.session_manager._spawn_persist_task(session.meta.session_id, session.messages)

        assistant_msg_idx = assistant_msg_obj.idx
        msg_count = len(session.messages)
        logger.debug(f"Added assistant message. Session now has {msg_count} messages")

        # Store actual token counts with the messages
        if self._last_usage:
            prompt_tokens = self._last_usage.get("prompt_tokens", 0)
            completion_tokens = self._last_usage.get("completion_tokens", 0)

            # Extract cached tokens from prompt_tokens_details
            prompt_details = self._last_usage.get("prompt_tokens_details") or {}
            cached_tokens = 0
            if isinstance(prompt_details, dict):
                cached_tokens = prompt_details.get("cached_tokens", 0)

            # Extract reasoning tokens from completion_tokens_details
            completion_details = self._last_usage.get("completion_tokens_details") or {}
            reasoning_tokens = 0
            if isinstance(completion_details, dict):
                reasoning_tokens = completion_details.get("reasoning_tokens", 0)

            # Update user message with input tokens (and cached)
            self.session_manager.update_message_tokens(
                user_msg_idx,
                input_tokens=prompt_tokens,
                cached_tokens=cached_tokens,
                session_id=session_id,
            )

            # Update assistant message with output tokens (and reasoning)
            self.session_manager.update_message_tokens(
                assistant_msg_idx,
                output_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
                session_id=session_id,
            )

            # Clear last usage for next turn
            self._last_usage = None

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
        return "Compaction not yet implemented"

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
