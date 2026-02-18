"""Streaming agent loop for Alfred."""

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from src.llm import ChatMessage, LLMProvider
from src.tools import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """A parsed tool call from LLM."""
    id: str
    name: str
    arguments: dict[str, Any]


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
    ) -> AsyncIterator[str]:
        """Run agent loop with full streaming.
        
        Yields:
            - LLM response tokens as they arrive
            - Tool execution status markers
            - Tool output chunks in real-time
            - Final response after tool results
        """
        if system_prompt:
            messages = [ChatMessage(role="system", content=system_prompt)] + messages

        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"Agent iteration {iteration}")

            # Get tool schemas
            tool_schemas = self.tools.get_schemas()

            # Stream LLM response
            full_content = ""
            tool_calls_data = []
            in_tool_call = False
            reasoning_content = None

            async for chunk in self.llm.stream_chat_with_tools(
                messages,
                tools=tool_schemas if tool_schemas else None,
            ):
                # Check for tool call markers in stream
                if chunk.startswith("[TOOL_CALLS]"):
                    # Parse tool calls from marker
                    try:
                        tc_data = json.loads(chunk[12:])  # Remove prefix
                        tool_calls_data = tc_data
                        in_tool_call = True
                    except json.JSONDecodeError:
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
            tool_calls = [
                ToolCall(
                    id=tc.get("id", f"call_{i}"),
                    name=tc["function"]["name"],
                    arguments=json.loads(tc["function"]["arguments"]),
                )
                for i, tc in enumerate(tool_calls_data)
            ]

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
                    yield f"\n[Tool '{call.name}' not found]\n"
                    messages.append(ChatMessage(
                        role="tool",
                        content=f"Error: Tool '{call.name}' not found",
                        tool_call_id=call.id,
                    ))
                    continue

                # Stream tool execution
                yield f"\n[Executing: {call.name}]\n"

                tool_output = ""
                try:
                    async for chunk in tool.validate_and_run_stream(call.arguments):
                        tool_output += chunk
                        yield chunk  # Stream tool output in real-time!
                except Exception as e:
                    error_msg = f"Error executing {call.name}: {e}"
                    yield f"\n{error_msg}\n"
                    tool_output += error_msg

                # Add tool result to messages
                messages.append(ChatMessage(
                    role="tool",
                    content=tool_output,
                    tool_call_id=call.id,
                ))

                yield f"\n[{call.name} complete]\n"

        # Max iterations reached
        yield "\n[Max iterations reached]\n"

    async def run(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> str:
        """Run agent loop (non-streaming, collects full response).
        
        Returns:
            Complete response as string
        """
        result = ""
        async for chunk in self.run_stream(messages, system_prompt):
            result += chunk
        return result
