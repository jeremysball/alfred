"""Streaming agent loop for Alfred."""

import json
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field

from src.llm import ChatMessage, LLMProvider
from src.tools import ToolRegistry
from src.type_defs import JsonObject, ToolArguments, UsageData, ensure_json_object

logger = logging.getLogger(__name__)


def _parse_usage_data(raw: JsonObject) -> UsageData:
    usage: UsageData = {}

    prompt_tokens = raw.get("prompt_tokens")
    if isinstance(prompt_tokens, int):
        usage["prompt_tokens"] = prompt_tokens

    completion_tokens = raw.get("completion_tokens")
    if isinstance(completion_tokens, int):
        usage["completion_tokens"] = completion_tokens

    prompt_details = raw.get("prompt_tokens_details")
    if isinstance(prompt_details, dict):
        cached_tokens = prompt_details.get("cached_tokens")
        if isinstance(cached_tokens, int):
            usage["prompt_tokens_details"] = {"cached_tokens": cached_tokens}

    completion_details = raw.get("completion_tokens_details")
    if isinstance(completion_details, dict):
        reasoning_tokens = completion_details.get("reasoning_tokens")
        if isinstance(reasoning_tokens, int):
            usage["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}

    return usage


def _parse_tool_call(data: JsonObject, index: int) -> "ToolCall":
    call_id_value = data.get("id")
    call_id = call_id_value if isinstance(call_id_value, str) else f"call_{index}"

    function_value = data.get("function")
    if not isinstance(function_value, dict):
        raise ValueError("Tool call missing function")
    function_data = ensure_json_object(function_value)

    name_value = function_data.get("name")
    if not isinstance(name_value, str):
        raise ValueError("Tool call missing function name")

    arguments_value = function_data.get("arguments")
    if not isinstance(arguments_value, str):
        raise ValueError("Tool call arguments must be a JSON string")

    arguments = ensure_json_object(json.loads(arguments_value))

    return ToolCall(id=call_id, name=name_value, arguments=arguments)


@dataclass
class ToolCall:
    """A parsed tool call from LLM."""

    id: str
    name: str
    arguments: ToolArguments


# Tool event types for callback-based rendering


@dataclass
class ToolEvent:
    """Base event for tool execution."""

    tool_call_id: str
    tool_name: str


@dataclass
class ToolStart(ToolEvent):
    """Tool started executing."""

    arguments: ToolArguments = field(default_factory=dict)


@dataclass
class ToolOutput(ToolEvent):
    """Chunk of tool output."""

    chunk: str = ""


@dataclass
class ToolEnd(ToolEvent):
    """Tool finished."""

    result: str = ""
    is_error: bool = False


class Agent:
    """Streaming agent - coordinates LLM and tool execution."""

    def __init__(
        self,
        llm: LLMProvider,
        tools: ToolRegistry,
        max_iterations: int = 10,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.max_iterations = max_iterations

    async def run_stream(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
        usage_callback: Callable[[UsageData], None] | None = None,
        tool_callback: Callable[[ToolEvent], None] | None = None,
    ) -> AsyncIterator[str]:
        """Run agent loop with full streaming.

        Args:
            messages: Conversation messages
            system_prompt: Optional system prompt
            usage_callback: Optional callback for token usage updates
            tool_callback: Optional callback for tool execution events

        Yields:
            - LLM response tokens as they arrive
        """
        if system_prompt:
            messages = [ChatMessage(role="system", content=system_prompt)] + messages

        iteration = 0

        while self.max_iterations == -1 or iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"Agent iteration {iteration}")

            # Get tool schemas
            tool_schemas = self.tools.get_schemas()

            # Stream LLM response
            full_content = ""
            tool_calls_data: list[JsonObject] = []
            in_tool_call = False
            reasoning_content = None

            async for chunk in self.llm.stream_chat_with_tools(
                messages,
                tools=tool_schemas if tool_schemas else None,
            ):
                # Check for usage marker
                if chunk.startswith("[USAGE]"):
                    try:
                        usage_raw = ensure_json_object(json.loads(chunk[7:]))
                        usage_data = _parse_usage_data(usage_raw)
                        if usage_callback:
                            usage_callback(usage_data)
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse usage data: {chunk}")
                    continue

                # Check for tool call markers in stream
                if chunk.startswith("[TOOL_CALLS]"):
                    # Parse tool calls from marker
                    try:
                        tc_data = json.loads(chunk[12:])  # Remove prefix
                        if isinstance(tc_data, list):
                            tool_calls_data = [
                                ensure_json_object(item)
                                for item in tc_data
                                if isinstance(item, dict)
                            ]
                            in_tool_call = True
                    except (json.JSONDecodeError, TypeError):
                        pass
                    continue

                # Check for reasoning content marker
                if chunk.startswith("[REASONING]"):
                    chunk_reasoning = chunk[11:]  # Remove prefix
                    reasoning_content = (reasoning_content or "") + chunk_reasoning
                    continue

                # Regular content
                if not in_tool_call:
                    full_content += chunk
                    yield chunk

            # Check if we have tool calls
            if not tool_calls_data:
                # No tool calls, we're done
                return

            # Parse tool calls
            tool_calls: list[ToolCall] = []
            for i, tc in enumerate(tool_calls_data):
                try:
                    tool_calls.append(_parse_tool_call(tc, i))
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    logger.warning("Failed to parse tool call: %s", exc)

            if not tool_calls:
                return

            # Add assistant message with tool calls and reasoning
            assistant_msg = ChatMessage(
                role="assistant",
                content=full_content,
                tool_calls=[
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in tool_calls
                ],
            )
            if reasoning_content:
                assistant_msg.reasoning_content = reasoning_content
            messages.append(assistant_msg)

            # Execute tools with streaming
            for call in tool_calls:
                tool = self.tools.get(call.name)

                if not tool:
                    error_msg = f"Error: Tool '{call.name}' not found"
                    if tool_callback:
                        tool_callback(
                            ToolStart(
                                tool_call_id=call.id,
                                tool_name=call.name,
                                arguments={},
                            )
                        )
                        tool_callback(
                            ToolEnd(
                                tool_call_id=call.id,
                                tool_name=call.name,
                                result=error_msg,
                                is_error=True,
                            )
                        )
                    messages.append(
                        ChatMessage(
                            role="tool",
                            content=error_msg,
                            tool_call_id=call.id,
                        )
                    )
                    continue

                # Emit tool start event
                if tool_callback:
                    tool_callback(
                        ToolStart(
                            tool_call_id=call.id,
                            tool_name=call.name,
                            arguments=call.arguments,
                        )
                    )

                tool_output = ""
                try:
                    async for chunk in tool.validate_and_run_stream(call.arguments):
                        tool_output += chunk
                        # Emit output event
                        if tool_callback:
                            tool_callback(
                                ToolOutput(
                                    tool_call_id=call.id,
                                    tool_name=call.name,
                                    chunk=chunk,
                                )
                            )
                except Exception as e:
                    error_msg = f"Error executing {call.name}: {e}"
                    tool_output += error_msg
                    if tool_callback:
                        tool_callback(
                            ToolOutput(
                                tool_call_id=call.id,
                                tool_name=call.name,
                                chunk=error_msg,
                            )
                        )

                # Emit tool end event
                if tool_callback:
                    tool_callback(
                        ToolEnd(
                            tool_call_id=call.id,
                            tool_name=call.name,
                            result=tool_output,
                            is_error=self._is_error(tool_output),
                        )
                    )

                # Add tool result to messages
                messages.append(
                    ChatMessage(
                        role="tool",
                        content=tool_output,
                        tool_call_id=call.id,
                    )
                )

        # Max iterations reached (only if limit is set)
        if self.max_iterations != -1:
            logger.warning(f"Agent reached max iterations ({self.max_iterations})")

    def _is_error(self, output: str) -> bool:
        """Detect if tool output indicates an error."""
        error_indicators = [
            "Error:",
            "Exception:",
            "Traceback",
            "Failed",
            "❌",
        ]
        return any(indicator in output for indicator in error_indicators)

    async def run(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
        tool_callback: Callable[[ToolEvent], None] | None = None,
    ) -> str:
        """Run agent loop (non-streaming, collects full response).

        Returns:
            Complete response as string
        """
        result = ""
        async for chunk in self.run_stream(messages, system_prompt, tool_callback=tool_callback):
            result += chunk
        return result
