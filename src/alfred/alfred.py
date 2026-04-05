"""Core Alfred engine - orchestrates memory, context, and LLM with agent loop."""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, cast
from uuid import uuid4

from telegram import Bot

from alfred.agent import Agent, ToolEnd, ToolEvent, ToolOutput, ToolStart
from alfred.config import Config
from alfred.context import ContextLoader
from alfred.core import AlfredCore
from alfred.llm import ChatMessage
from alfred.self_model import RuntimeSelfModel, build_runtime_self_model
from alfred.session import Message, ReasoningBlock, Role, Session, TextBlock, ToolCallRecord
from alfred.support_policy import SupportPolicyRuntime
from alfred.token_tracker import TokenTracker
from alfred.tools import get_registry, register_builtin_tools

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

        # Initialize core services (shared with LittleAlfred)
        self.core = AlfredCore(config)

        # Initialize UI-specific components
        self.context_loader = ContextLoader(config, store=self.core.sqlite_store)

        # Initialize Telegram bot if in telegram mode
        self._telegram_bot: Bot | None = None
        if telegram_mode:
            try:
                self._telegram_bot = Bot(token=config.telegram_bot_token)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Telegram bot: {e}")

        # Create socket client for cron job tools
        from alfred.cron.socket_client import SocketClient

        self._socket_client = SocketClient()

        # Register built-in tools (inject services from core)
        register_builtin_tools(
            memory_store=self.core.memory_store,
            socket_client=self._socket_client,
            config=self.config,
            session_manager=self.core.session_manager,
            embedder=self.core.embedder,
            llm_client=self.core.llm,
            summarizer=self.core.summarizer,
        )
        self.tools = get_registry()

        # Create agent with LLM from core
        self.agent = Agent(self.core.llm, self.tools, max_iterations=-1)

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

    def _log_turn_event(self, event: str, **fields: Any) -> None:
        """Log a structured core turn lifecycle event."""
        details = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
        if details:
            logger.debug("%s %s", event, details)
        else:
            logger.debug(event)

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

        messages = self.core.session_manager.get_session_messages(session_id)
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
        turn_started_at = perf_counter()
        turn_id = str(uuid4())
        self._log_turn_event(
            "core.turn.start",
            turn_id=turn_id,
            session_id="cli",
            message_chars=len(message),
            persist_partial=False,
        )

        assistant_message = ""
        boundary = "context"

        try:
            self._log_turn_event(
                "core.context.start",
                turn_id=turn_id,
                session_id="cli",
            )
            context_started_at = perf_counter()
            context = await self.context_loader.assemble_with_self_model(self)
            system_prompt = self._build_system_prompt(context.system_prompt)
            memories_count = len(getattr(context, "memories", []) or [])
            self._log_turn_event(
                "core.context.completed",
                turn_id=turn_id,
                session_id="cli",
                memories_count=memories_count,
                context_chars=len(system_prompt),
                duration_ms=round((perf_counter() - context_started_at) * 1000, 2),
            )

            messages = [ChatMessage(role="user", content=message)]
            self._update_context_tokens(system_prompt, messages)
            self.context_summary.update(memories_count=memories_count, session_messages=0)

            boundary = "agent"
            agent_started_at = perf_counter()
            self._log_turn_event(
                "core.agent_loop.start",
                turn_id=turn_id,
                session_id="cli",
                system_prompt_chars=len(system_prompt),
            )
            response = await self.agent.run(messages, system_prompt)
            assistant_message = response
            self._log_turn_event(
                "core.agent_loop.completed",
                turn_id=turn_id,
                session_id="cli",
                response_chars=len(response),
                duration_ms=round((perf_counter() - agent_started_at) * 1000, 2),
            )

            self._log_turn_event(
                "core.turn.completed",
                turn_id=turn_id,
                session_id="cli",
                message_chars=len(message),
                response_chars=len(response),
                memories_count=memories_count,
                session_messages=0,
                duration_ms=round((perf_counter() - turn_started_at) * 1000, 2),
            )
            return response
        except asyncio.CancelledError:
            self._log_turn_event(
                "core.turn.cancelled",
                turn_id=turn_id,
                session_id="cli",
                boundary=boundary,
                message_chars=len(message),
                response_chars=len(assistant_message),
                duration_ms=round((perf_counter() - turn_started_at) * 1000, 2),
            )
            raise
        except Exception as exc:
            self._log_turn_event(
                "core.turn.failed",
                turn_id=turn_id,
                session_id="cli",
                boundary=boundary,
                error_type=type(exc).__name__,
                error=str(exc),
                message_chars=len(message),
                response_chars=len(assistant_message),
                duration_ms=round((perf_counter() - turn_started_at) * 1000, 2),
            )
            raise

    async def chat_stream(
        self,
        message: str,
        tool_callback: Callable[[ToolEvent], None] | None = None,
        session_id: str | None = None,
        persist_partial: bool = False,
        assistant_message_id: str | None = None,
        reuse_user_message: bool = False,
        status_callback: Callable[[str], None] | None = None,
    ) -> AsyncIterator[str]:
        """Process a message with streaming.

        Args:
            message: User message
            tool_callback: Optional callback for tool execution events
            session_id: Optional session ID (for Telegram chat_id). If None, uses CLI session.

        Yields:
            LLM response tokens
        """
        turn_started_at = perf_counter()
        turn_id = str(uuid4())
        self._log_turn_event(
            "core.turn.start",
            turn_id=turn_id,
            session_id=session_id or "cli",
            message_chars=len(message),
            persist_partial=persist_partial,
        )

        assistant_message_id = assistant_message_id or str(uuid4())
        boundary = "session"

        assistant_message = ""
        chunk_count = 0
        try:
            # Handle session based on mode
            if session_id:
                # Telegram mode - use provided session_id (chat_id)
                self.core.session_manager.get_or_create_session(session_id)
            else:
                # CLI mode - use singleton session
                if not self.core.session_manager.has_active_session():
                    logger.debug("Starting new session...")
                    self.core.session_manager.start_session()

            session: Session
            if session_id:
                session = self.core.session_manager.get_or_create_session(session_id)
            else:
                maybe_session = self.core.session_manager.get_current_cli_session()
                if maybe_session is None:
                    raise RuntimeError("No active session")
                session = maybe_session

            messages_list = self.core.session_manager.get_session_messages(session_id)
            if reuse_user_message and messages_list:
                last_message = messages_list[-1]
                if last_message.role is Role.USER:
                    user_msg_idx = last_message.idx
                    msg_count = len(messages_list)
                    logger.debug(f"Reusing user message. Session has {msg_count} messages")
                else:
                    self.core.session_manager.add_message("user", message, session_id=session_id)
                    messages_list = self.core.session_manager.get_session_messages(session_id)
                    user_msg_idx = messages_list[-1].idx if messages_list else 0
                    msg_count = len(messages_list)
                    logger.debug(f"Added user message. Session now has {msg_count} messages")
            else:
                self.core.session_manager.add_message("user", message, session_id=session_id)
                messages_list = self.core.session_manager.get_session_messages(session_id)
                user_msg_idx = messages_list[-1].idx if messages_list else 0
                msg_count = len(messages_list)
                logger.debug(f"Added user message. Session now has {msg_count} messages")

            assistant_msg_obj: Message | None = None

            boundary = "embedding"
            if status_callback:
                status_callback("Embedding")
            # Get query embedding for memory search
            logger.debug("Generating query embedding...")
            query_embedding = await self.core.embedder.embed(message)

            if status_callback:
                status_callback("Loading memories")
            # Load all memories
            logger.debug("Loading memories...")
            all_memories = await self.core.memory_store.get_all_entries()
            logger.info(f"Loaded {len(all_memories)} memories from store")

            if status_callback:
                status_callback("Assembling context")
            boundary = "context"

            # Build context with memory search and session history
            session_messages = self.core.session_manager.get_messages_for_context(session_id)
            # Get full messages with tool_calls for context
            session_messages_with_tools = self.core.session_manager.get_messages_with_tools_for_context(session_id)
            self._log_turn_event(
                "core.context.start",
                turn_id=turn_id,
                available_memories=len(all_memories),
                session_messages=len(session_messages),
            )
            context_started_at = perf_counter()
            system_prompt, memories_count = await self.context_loader.assemble_with_search(
                query_embedding=query_embedding,
                memories=all_memories,
                session_messages=session_messages,
                session_messages_with_tools=session_messages_with_tools,
                alfred=self,
            )
            system_prompt = self._build_system_prompt(system_prompt)
            self._log_turn_event(
                "core.context.completed",
                turn_id=turn_id,
                memories_count=memories_count,
                context_chars=len(system_prompt),
                duration_ms=round((perf_counter() - context_started_at) * 1000, 2),
            )

            support_contract_section = await self._build_support_contract_section_for_turn(
                message=message,
                query_embedding=query_embedding,
                session_messages=session_messages,
                session_id=session_id,
            )
            if support_contract_section:
                system_prompt = f"{system_prompt}\n\n{support_contract_section}"

            messages = [ChatMessage(role="user", content=message)]

            # Update context token estimate for status display
            self._update_context_tokens(system_prompt, messages)

            # Update context summary for status display
            self.context_summary.update(
                memories_count=memories_count,
                session_messages=len(session_messages),
            )

            if persist_partial:
                boundary = "persist"
                assistant_msg_obj = Message(
                    idx=(messages_list[-1].idx + 1) if messages_list else 0,
                    role=Role.ASSISTANT,
                    content="",
                    id=assistant_message_id,
                    timestamp=datetime.now(UTC),
                    streaming=True,
                )
                session.messages.append(assistant_msg_obj)
                session.meta.last_active = datetime.now(UTC)
                session.meta.message_count = len(session.messages)
                await self.core.session_manager._persist_messages(session.meta.session_id, session.messages)

            if status_callback:
                status_callback("")
            boundary = "agent"
            agent_started_at = perf_counter()
            self._log_turn_event(
                "core.agent_loop.start",
                turn_id=turn_id,
                system_prompt_chars=len(system_prompt),
            )

            # Accumulator for tool calls and reasoning during this turn
            chunk_count = 0
            tool_calls_accumulator: list[dict[str, Any]] = []
            full_response: list[str] = []
            reasoning_blocks: list[ReasoningBlock] = []  # Interleaved reasoning blocks
            current_reasoning_block: ReasoningBlock | None = None
            text_blocks: list[TextBlock] = []  # Ordered visible text segments
            current_text_block: TextBlock | None = None
            sequence_counter = 0  # Shared sequence counter for interleaving

            def _build_text_blocks_snapshot() -> list[TextBlock] | None:
                if not text_blocks:
                    return None

                return [
                    TextBlock(
                        content=tb.content,
                        sequence=tb.sequence,
                    )
                    for tb in text_blocks
                ]

            def _build_reasoning_blocks_snapshot() -> list[ReasoningBlock] | None:
                snapshot = [
                    ReasoningBlock(
                        content=rb.content,
                        sequence=rb.sequence,
                    )
                    for rb in reasoning_blocks
                ]
                if current_reasoning_block is not None:
                    snapshot.append(
                        ReasoningBlock(
                            content=current_reasoning_block.content,
                            sequence=current_reasoning_block.sequence,
                        )
                    )
                return snapshot or None

            def _build_tool_calls_snapshot() -> list[ToolCallRecord] | None:
                if not tool_calls_accumulator:
                    return None

                return [
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

            def _tool_callback_wrapper(event: ToolEvent) -> None:
                """Wrapper to capture tool calls while still calling external callback."""
                nonlocal full_response, sequence_counter, reasoning_blocks, current_reasoning_block, current_text_block

                # Call external callback if provided
                if tool_callback:
                    tool_callback(event)

                # Capture tool call data
                if isinstance(event, ToolStart):
                    # Finalize any active reasoning block before tool call
                    if current_reasoning_block is not None:
                        reasoning_blocks.append(current_reasoning_block)
                        current_reasoning_block = None

                    # Tool calls break the current text segment so the next text chunk
                    # starts a fresh block after the tool call.
                    current_text_block = None

                    # Calculate insert position based on current response length
                    insert_position = len("".join(full_response))

                    # Assign sequence from shared counter and increment
                    sequence = sequence_counter
                    sequence_counter += 1

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

                if persist_partial and assistant_msg_obj is not None:
                    assistant_msg_obj.tool_calls = _build_tool_calls_snapshot()
                    assistant_msg_obj.reasoning_blocks = _build_reasoning_blocks_snapshot()
                    assistant_msg_obj.text_blocks = _build_text_blocks_snapshot()

            chunk_times: list[float] = []
            last_chunk_time = perf_counter()
            stream_start = perf_counter()

            async for chunk in self.agent.run_stream(
                messages,
                system_prompt,
                usage_callback=self._on_usage,
                tool_callback=_tool_callback_wrapper,
            ):
                now = perf_counter()
                chunk_latency = now - last_chunk_time
                chunk_times.append(chunk_latency)
                last_chunk_time = now

                # Separate reasoning from content for storage
                if chunk.startswith("[REASONING]"):
                    reasoning_chunk = chunk[11:]  # Strip [REASONING] prefix

                    # Start new reasoning block if needed
                    if current_reasoning_block is None:
                        current_reasoning_block = ReasoningBlock(
                            content=reasoning_chunk,
                            sequence=sequence_counter,
                        )
                        sequence_counter += 1
                    else:
                        current_reasoning_block.content += reasoning_chunk

                    # Reasoning boundaries break the current visible text segment.
                    current_text_block = None

                    if assistant_msg_obj is not None:
                        assistant_msg_obj.reasoning_content += reasoning_chunk
                        assistant_msg_obj.reasoning_blocks = _build_reasoning_blocks_snapshot()
                        assistant_msg_obj.text_blocks = _build_text_blocks_snapshot()
                        assistant_msg_obj.streaming = True
                elif chunk.startswith("[/REASONING]"):
                    # End current reasoning block
                    if current_reasoning_block is not None:
                        reasoning_blocks.append(current_reasoning_block)
                        current_reasoning_block = None

                    # Keep the next visible text chunk in a fresh block.
                    current_text_block = None

                    if assistant_msg_obj is not None:
                        assistant_msg_obj.reasoning_blocks = _build_reasoning_blocks_snapshot()
                        assistant_msg_obj.text_blocks = _build_text_blocks_snapshot()
                else:
                    full_response.append(chunk)
                    if current_text_block is None:
                        current_text_block = TextBlock(
                            content=chunk,
                            sequence=sequence_counter,
                        )
                        sequence_counter += 1
                        text_blocks.append(current_text_block)
                    else:
                        current_text_block.content += chunk

                    if assistant_msg_obj is not None:
                        assistant_msg_obj.content = "".join(full_response)
                        assistant_msg_obj.text_blocks = _build_text_blocks_snapshot()
                        assistant_msg_obj.reasoning_blocks = _build_reasoning_blocks_snapshot()
                        assistant_msg_obj.streaming = True
                chunk_count += 1

                # Log slow chunks (>100ms) at debug level
                if chunk_latency > 0.1:
                    logger.debug(f"[STREAM_SLOW_CHUNK] chunk={chunk_count} latency={chunk_latency * 1000:.2f}ms chars={len(chunk)}")

                yield chunk

            # Log streaming performance summary
            if chunk_times:
                total_stream_time = perf_counter() - stream_start
                avg_chunk_latency = sum(chunk_times) / len(chunk_times)
                max_chunk_latency = max(chunk_times)
                min_chunk_latency = min(chunk_times[1:])  # Exclude first chunk (includes request setup)
                logger.debug(
                    f"[STREAM_PERF] chunks={chunk_count} "
                    f"total_time={total_stream_time * 1000:.2f}ms "
                    f"avg_latency={avg_chunk_latency * 1000:.2f}ms "
                    f"min_latency={min_chunk_latency * 1000:.2f}ms "
                    f"max_latency={max_chunk_latency * 1000:.2f}ms"
                )

            # Finalize any pending reasoning block
            if current_reasoning_block is not None:
                reasoning_blocks.append(current_reasoning_block)
                current_reasoning_block = None

            assistant_message = "".join(full_response)
            reasoning_text = "".join(rb.content for rb in reasoning_blocks)
            self._log_turn_event(
                "core.agent_loop.completed",
                turn_id=turn_id,
                chunks=chunk_count,
                response_chars=len(assistant_message),
                reasoning_chars=len(reasoning_text),
                tool_calls=len(tool_calls_accumulator),
                duration_ms=round((perf_counter() - agent_started_at) * 1000, 2),
            )

            # Build ToolCallRecord objects from accumulated data
            tool_calls = _build_tool_calls_snapshot()

            # Add assistant response to session with tool calls

            if assistant_msg_obj is None:
                assistant_msg_obj = Message(
                    idx=(session.messages[-1].idx + 1) if session.messages else 0,
                    role=Role.ASSISTANT,
                    content=assistant_message,
                    id=assistant_message_id,
                    timestamp=datetime.now(UTC),
                    tool_calls=tool_calls,
                    reasoning_content=reasoning_text,
                    reasoning_blocks=reasoning_blocks if reasoning_blocks else None,
                    text_blocks=text_blocks if text_blocks else None,
                )
                session.messages.append(assistant_msg_obj)
            else:
                assistant_msg_obj.content = assistant_message
                assistant_msg_obj.reasoning_content = reasoning_text
                assistant_msg_obj.reasoning_blocks = reasoning_blocks if reasoning_blocks else None
                assistant_msg_obj.text_blocks = text_blocks if text_blocks else None
                assistant_msg_obj.tool_calls = tool_calls
                assistant_msg_obj.streaming = False

            session.meta.last_active = datetime.now(UTC)
            session.meta.message_count = len(session.messages)

            # Persist to storage
            if persist_partial:
                boundary = "persist"
                await self.core.session_manager._persist_messages(session.meta.session_id, session.messages)
            else:
                self.core.session_manager._spawn_persist_task(session.meta.session_id, session.messages)

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
                self.core.session_manager.update_message_tokens(
                    user_msg_idx,
                    input_tokens=prompt_tokens,
                    cached_tokens=cached_tokens,
                    session_id=session_id,
                )

                # Update assistant message with output tokens (and reasoning)
                self.core.session_manager.update_message_tokens(
                    assistant_msg_idx,
                    output_tokens=completion_tokens,
                    reasoning_tokens=reasoning_tokens,
                    session_id=session_id,
                )

                # Clear last usage for next turn
                self._last_usage = None

            self._log_turn_event(
                "core.turn.completed",
                turn_id=turn_id,
                session_id=session.meta.session_id,
                message_chars=len(message),
                response_chars=len(assistant_message),
                memories_count=memories_count,
                session_messages=len(session_messages),
                duration_ms=round((perf_counter() - turn_started_at) * 1000, 2),
            )

        except asyncio.CancelledError:
            self._log_turn_event(
                "core.turn.cancelled",
                turn_id=turn_id,
                session_id=session_id or "cli",
                boundary=boundary,
                message_chars=len(message),
                response_chars=len(assistant_message),
                chunks=chunk_count,
                duration_ms=round((perf_counter() - turn_started_at) * 1000, 2),
            )
            # Clean up streaming flag on cancellation
            if persist_partial and assistant_msg_obj is not None:
                assistant_msg_obj.streaming = False
                await self.core.session_manager._persist_messages(session.meta.session_id, session.messages)
            raise
        except Exception as exc:
            self._log_turn_event(
                "core.turn.failed",
                turn_id=turn_id,
                session_id=session_id or "cli",
                boundary=boundary,
                error_type=type(exc).__name__,
                error=str(exc),
                message_chars=len(message),
                response_chars=len(assistant_message),
                chunks=chunk_count,
                duration_ms=round((perf_counter() - turn_started_at) * 1000, 2),
            )
            # Clean up streaming flag on error
            if persist_partial and assistant_msg_obj is not None:
                assistant_msg_obj.streaming = False
                await self.core.session_manager._persist_messages(session.meta.session_id, session.messages)
            raise

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
                        param_type = ann.__name__.lower() if hasattr(ann, "__name__") else str(ann).lower()
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

    def _get_support_policy_runtime(self) -> SupportPolicyRuntime | None:
        """Return the cached support-policy runtime when the core exposes the required seams."""
        runtime = cast(SupportPolicyRuntime | None, getattr(self, "_support_policy_runtime", None))
        if runtime is not None:
            return runtime

        store = getattr(self.core, "sqlite_store", None)
        embedder = getattr(self.core, "embedder", None)
        if store is None or embedder is None:
            return None

        runtime = SupportPolicyRuntime(store=store, embedder=embedder)
        self._support_policy_runtime = runtime
        return runtime

    async def _build_support_contract_section_for_turn(
        self,
        *,
        message: str,
        query_embedding: list[float] | None,
        session_messages: list[tuple[str, str]],
        session_id: str | None,
    ) -> str | None:
        """Build the runtime support-contract section for one live turn when available."""
        runtime = self._get_support_policy_runtime()
        if runtime is None:
            return None

        return await runtime.build_prompt_section(
            message=message,
            query_embedding=query_embedding,
            session_messages=session_messages,
            session_id=session_id,
        )

    async def compact(self) -> str:
        """Trigger conversation compaction."""
        return "Compaction not yet implemented"

    async def start(self) -> None:
        """Start Alfred and all subsystems.

        Note: Cron scheduler runs in standalone daemon only.
        CLI/Telegram instances do not run cron, but they do connect
        to the daemon's socket for job management.
        """
        # Start socket client for cron job tools
        try:
            await self._socket_client.start()
            logger.debug("Socket client started for cron job tools")
        except Exception as e:
            logger.warning(f"Failed to start socket client: {e}")

    def build_self_model(self) -> RuntimeSelfModel:
        """Build a self-model snapshot from current runtime state.

        This creates a runtime snapshot describing Alfred's current state,
        capabilities, and environment. Used for self-awareness in prompts.

        Returns:
            RuntimeSelfModel populated with current runtime facts
        """
        logger.debug("Alfred.build_self_model: building self-model snapshot")
        model = build_runtime_self_model(self)
        logger.debug(
            "Alfred.build_self_model: self-model ready - interface=%s, tools=%d, memory=%s, search=%s, messages=%d",
            model.runtime.interface.value if model.runtime.interface else None,
            len(model.capabilities.tools_available),
            model.capabilities.memory_enabled,
            model.capabilities.search_enabled,
            model.context_pressure.message_count,
        )
        return model

    async def stop(self) -> None:
        """Graceful shutdown.

        Stops all subsystems cleanly.
        """
        # Stop socket client
        try:
            await self._socket_client.stop()
            logger.debug("Socket client stopped")
        except Exception as e:
            logger.warning(f"Error stopping socket client: {e}")
