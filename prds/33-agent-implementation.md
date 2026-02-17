# PRD: Agent Implementation - Tool Loop & Execution

## Overview

**Issue**: #33
**Parent**: #10 (Alfred - The Rememberer)
**Depends On**: #14 (M5: Telegram Bot), #32 (Skill System + API)
**Status**: Planning
**Priority**: High
**Created**: 2026-02-17

Implement the core agent loop: tool registration, tool call parsing from LLM responses, execution, and streaming. This is the "brain" that makes Alfred an agent rather than a simple chatbot.

---

## Problem Statement

Current `Alfred.chat()` is a simple pass-through:
1. Load context
2. Send to LLM
3. Return response

The LLM cannot act. It can only respond with text. To make Alfred an agent, we need:
- Tools the LLM can invoke
- Parsing of tool calls from LLM responses
- Execution of those tools
- Feeding results back to the LLM
- Loop until the LLM stops calling tools

---

## Solution

### Architecture

```
User Message
    │
    ▼
┌─────────────────┐
│  Agent Loop     │
│                 │
│  1. Assemble    │◄──┐
│     context     │   │
│                 │   │
│  2. Send to     │   │
│     LLM         │   │
│                 │   │
│  3. Parse       │   │
│     response    │   │
│                 │   │
│  4. Has tool    │   │
│     calls?      │───┴──► Return final response
│       │         │        to user
│      Yes        │
│       │         │
│       ▼         │
│  5. Execute     │
│     tools       │
│                 │
│  6. Add results │
│     to context  │
│                 │
└─────────────────┘
```

### Tool Definition (Decorator Pattern)

```python
from src.tools import tool, ToolRegistry
from typing import Optional

@tool
def read(path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> str:
    """Read file contents.
    
    Args:
        path: Path to the file to read
        offset: Line number to start from (1-indexed)
        limit: Maximum number of lines to read
    
    Returns:
        File contents as string
    """
    with open(path) as f:
        lines = f.readlines()
    
    if offset:
        lines = lines[offset - 1:]
    if limit:
        lines = lines[:limit]
    
    return "".join(lines)


@tool
def write(path: str, content: str) -> dict:
    """Create or overwrite a file.
    
    Args:
        path: Path where to write the file
        content: Content to write
    
    Returns:
        Status dict with path and bytes written
    """
    with open(path, "w") as f:
        f.write(content)
    
    return {"path": path, "bytes_written": len(content.encode())}


@tool
def edit(path: str, old_text: str, new_text: str) -> dict:
    """Make precise edit to a file by replacing old_text with new_text.
    
    Args:
        path: Path to the file to edit
        old_text: Exact text to find and replace
        new_text: Text to replace with
    
    Returns:
        Status dict with path and whether edit was made
    """
    with open(path) as f:
        content = f.read()
    
    if old_text not in content:
        return {"path": path, "edited": False, "error": "old_text not found"}
    
    new_content = content.replace(old_text, new_text, 1)
    
    with open(path, "w") as f:
        f.write(new_content)
    
    return {"path": path, "edited": True}


@tool
def bash(command: str, timeout: Optional[int] = None) -> dict:
    """Execute a bash command.
    
    Args:
        command: Shell command to execute
        timeout: Timeout in seconds (default: 60)
    
    Returns:
        Dict with stdout, stderr, exit_code
    """
    import subprocess
    
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout or 60,
    )
    
    # Truncate output if too long
    stdout = result.stdout
    stderr = result.stderr
    max_lines = 2000
    max_bytes = 50000
    
    if len(stdout) > max_bytes or stdout.count('\n') > max_lines:
        lines = stdout.split('\n')[:max_lines]
        stdout = '\n'.join(lines)[:max_bytes]
        stdout += "\n[Output truncated...]"
    
    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": result.returncode,
    }
```

### Tool Registration

```python
# src/tools.py

import inspect
import json
from dataclasses import dataclass, field
from typing import Callable, Any, Optional
from functools import wraps


@dataclass
class Tool:
    """A registered tool."""
    name: str
    description: str
    parameters: dict  # JSON Schema
    execute: Callable[..., Any]
    func: Callable[..., Any]  # Original function


class ToolRegistry:
    """Registry of available tools."""
    
    def __init__(self):
        self._tools: dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def get_schemas(self) -> list[dict]:
        """Get JSON schemas for all tools (for LLM)."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()


# Global registry instance
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _registry


def python_type_to_json_schema(py_type: type) -> dict:
    """Convert Python type to JSON Schema type."""
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }
    
    # Handle Optional[T]
    origin = getattr(py_type, "__origin__", None)
    if origin is not None:
        args = getattr(py_type, "__args__", ())
        if origin is Optional or type(None) in args:
            # Get the non-None type
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                schema = python_type_to_json_schema(non_none[0])
                return schema
    
    return type_map.get(py_type, {"type": "string"})


def parse_docstring_params(docstring: str) -> dict[str, str]:
    """Parse Args section from docstring."""
    if not docstring:
        return {}
    
    params = {}
    lines = docstring.split("\n")
    in_args = False
    current_param = None
    
    for line in lines:
        stripped = line.strip()
        
        if stripped == "Args:" or stripped.startswith("Args:"):
            in_args = True
            continue
        
        if in_args:
            # Check for new section
            if stripped.endswith(":") and not stripped.startswith(" "):
                break
            
            # Parse param: "name: description"
            if ":" in stripped and not stripped.startswith(" "):
                parts = stripped.split(":", 1)
                current_param = parts[0].strip()
                params[current_param] = parts[1].strip()
            elif current_param and stripped:
                # Continuation of previous param description
                params[current_param] += " " + stripped
    
    return params


def tool(func: Callable) -> Callable:
    """Decorator to register a function as a tool.
    
    Extracts name, description, and parameters from the function
    signature and docstring.
    """
    # Get function metadata
    name = func.__name__
    docstring = inspect.getdoc(func) or ""
    
    # First line of docstring is description
    description = docstring.split("\n")[0].strip() if docstring else ""
    
    # Parse parameter descriptions from docstring
    param_docs = parse_docstring_params(docstring)
    
    # Get signature
    sig = inspect.signature(func)
    
    # Build JSON Schema parameters
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        # Get type annotation
        py_type = param.annotation if param.annotation != inspect.Parameter.empty else str
        
        # Build property
        prop = python_type_to_json_schema(py_type)
        if param_name in param_docs:
            prop["description"] = param_docs[param_name]
        
        properties[param_name] = prop
        
        # Check if required
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
    
    parameters_schema = {
        "type": "object",
        "properties": properties,
        "required": required,
    }
    
    # Create Tool instance
    tool_instance = Tool(
        name=name,
        description=description,
        parameters=parameters_schema,
        execute=func,
        func=func,
    )
    
    # Register
    _registry.register(tool_instance)
    
    # Return original function unchanged
    return func
```

### Tool Call Format (Kimi/OpenAI Compatible)

```python
# LLM sends tool calls in this format:
{
    "tool_calls": [
        {
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "read",
                "arguments": '{"path": "/app/README.md", "limit": 50}'
            }
        }
    ]
}

# Tool results sent back:
{
    "tool_call_id": "call_abc123",
    "role": "tool",
    "content": "...file contents..."
}
```

### Agent Loop Implementation

```python
# src/agent.py

import json
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from src.config import Config
from src.llm import ChatMessage, ChatResponse, LLMProvider
from src.tools import ToolRegistry, Tool, get_registry

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """A parsed tool call from LLM."""
    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    """Result of a tool execution."""
    call_id: str
    name: str
    content: str
    error: Optional[str] = None


class Agent:
    """Core agent - handles tool loop and execution."""
    
    def __init__(
        self,
        llm: LLMProvider,
        tools: ToolRegistry,
        config: Config,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.config = config
        self.max_iterations = 10  # Prevent infinite loops
    
    async def run(
        self,
        messages: list[ChatMessage],
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        """Run agent loop until completion.
        
        Returns final response (no tool calls).
        """
        # Add system prompt if provided
        if system_prompt:
            messages = [ChatMessage(role="system", content=system_prompt)] + messages
        
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"Agent iteration {iteration}")
            
            # Get tool schemas
            tool_schemas = self.tools.get_schemas()
            
            # Call LLM
            response = await self.llm.chat_with_tools(
                messages,
                tools=tool_schemas if tool_schemas else None,
            )
            
            # Check for tool calls
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                # No tool calls, we're done
                return response
            
            # Add assistant message with tool calls
            messages.append(ChatMessage(
                role="assistant",
                content=response.content or "",
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
            ))
            
            # Execute tools
            results = await self._execute_tools(tool_calls)
            
            # Add tool results to messages
            for result in results:
                messages.append(ChatMessage(
                    role="tool",
                    content=result.content if not result.error else f"Error: {result.error}",
                    tool_call_id=result.call_id,
                ))
        
        # Max iterations reached
        logger.warning(f"Max iterations ({self.max_iterations}) reached")
        return ChatResponse(
            content="I apologize, but I needed too many steps to complete this task. Please try breaking it down.",
            model="agent",
        )
    
    async def run_stream(
        self,
        messages: list[ChatMessage],
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Run agent loop with streaming output.
        
        Yields text chunks. When tools are called, yields
        tool execution status.
        """
        if system_prompt:
            messages = [ChatMessage(role="system", content=system_prompt)] + messages
        
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            
            tool_schemas = self.tools.get_schemas()
            
            # Stream the response
            full_response = ""
            tool_calls_buffer = ""
            
            async for chunk in self.llm.stream_chat_with_tools(
                messages,
                tools=tool_schemas if tool_schemas else None,
            ):
                # Check if chunk contains tool call info
                if chunk.startswith("[TOOL_CALLS]"):
                    tool_calls_buffer = chunk[12:]  # Remove prefix
                    continue
                
                full_response += chunk
                yield chunk
            
            # Parse any tool calls from buffer
            if tool_calls_buffer:
                tool_calls = self._parse_tool_calls_from_buffer(tool_calls_buffer)
            else:
                # Check if response contains tool calls
                response_obj = ChatResponse(
                    content=full_response,
                    model="streaming",
                )
                tool_calls = self._parse_tool_calls(response_obj)
            
            if not tool_calls:
                return
            
            # Execute tools
            yield f"\n[Executing {len(tool_calls)} tool(s)...]\n"
            
            results = await self._execute_tools(tool_calls)
            
            # Add to messages for next iteration
            messages.append(ChatMessage(
                role="assistant",
                content=full_response,
            ))
            
            for result in results:
                messages.append(ChatMessage(
                    role="tool",
                    content=result.content if not result.error else f"Error: {result.error}",
                    tool_call_id=result.call_id,
                ))
                
                yield f"[{result.name}] ✓\n"
        
        yield "\n[Max iterations reached]\n"
    
    def _parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]:
        """Parse tool calls from LLM response."""
        # OpenAI/Kimi format: response has tool_calls attribute
        if hasattr(response, "tool_calls") and response.tool_calls:
            return [
                ToolCall(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=json.loads(tc["function"]["arguments"]),
                )
                for tc in response.tool_calls
            ]
        
        # Check if content contains JSON tool calls (fallback)
        if response.content and "```json" in response.content:
            try:
                # Extract JSON from markdown
                json_str = response.content.split("```json")[1].split("```")[0]
                data = json.loads(json_str)
                
                if "tool_calls" in data:
                    return [
                        ToolCall(
                            id=tc.get("id", f"call_{i}"),
                            name=tc["function"]["name"],
                            arguments=json.loads(tc["function"]["arguments"]),
                        )
                        for i, tc in enumerate(data["tool_calls"])
                    ]
            except (json.JSONDecodeError, KeyError, IndexError):
                pass
        
        return []
    
    def _parse_tool_calls_from_buffer(self, buffer: str) -> list[ToolCall]:
        """Parse tool calls from streaming buffer."""
        try:
            data = json.loads(buffer)
            return [
                ToolCall(
                    id=tc["id"],
                    name=tc["name"],
                    arguments=tc["arguments"],
                )
                for tc in data
            ]
        except json.JSONDecodeError:
            return []
    
    async def _execute_tools(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Execute a list of tool calls."""
        results = []
        
        for call in tool_calls:
            tool = self.tools.get(call.name)
            
            if not tool:
                results.append(ToolResult(
                    call_id=call.id,
                    name=call.name,
                    content="",
                    error=f"Tool '{call.name}' not found",
                ))
                continue
            
            try:
                # Execute the tool
                import asyncio
                
                # Check if coroutine
                if asyncio.iscoroutinefunction(tool.execute):
                    result = await tool.execute(**call.arguments)
                else:
                    result = tool.execute(**call.arguments)
                
                # Convert result to string
                if isinstance(result, str):
                    content = result
                else:
                    content = json.dumps(result, indent=2)
                
                results.append(ToolResult(
                    call_id=call.id,
                    name=call.name,
                    content=content,
                ))
                
                logger.debug(f"Tool {call.name} executed successfully")
                
            except Exception as e:
                logger.exception(f"Error executing tool {call.name}")
                results.append(ToolResult(
                    call_id=call.id,
                    name=call.name,
                    content="",
                    error=str(e),
                ))
        
        return results
```

### Updated LLM Provider with Tool Support

```python
# src/llm.py additions

class KimiProvider(LLMProvider):
    # ... existing methods ...
    
    async def chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[dict]] = None,
    ) -> ChatResponse:
        """Send chat with tool definitions."""
        import openai
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                tools=tools,
                temperature=0.7,
                max_tokens=4000,
            )
            
            content = response.choices[0].message.content or ""
            tool_calls = None
            
            # Check for tool calls
            if response.choices[0].message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response.choices[0].message.tool_calls
                ]
            
            return ChatResponse(
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                } if response.usage else None,
                tool_calls=tool_calls,
            )
            
        except Exception as e:
            logger.error(f"Error in chat_with_tools: {e}")
            raise
    
    async def stream_chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[dict]] = None,
    ) -> AsyncIterator[str]:
        """Stream chat with tool support."""
        import openai
        
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            tools=tools,
            temperature=0.7,
            max_tokens=4000,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


@dataclass
class ChatResponse:
    content: str
    model: str
    usage: Optional[dict] = None
    tool_calls: Optional[list[dict]] = None  # New field
```

### Integration with Alfred

```python
# src/alfred.py (updated)

from src.agent import Agent
from src.tools import get_registry, tool  # Import tools

class Alfred:
    """Core Alfred engine with agent loop."""
    
    def __init__(self, config: Config) -> None:
        self.config = config
        self.llm = LLMFactory.create(config)
        self.context_loader = ContextLoader(config)
        self.tools = get_registry()
        self.agent = Agent(self.llm, self.tools, config)
        
        # Auto-load built-in tools
        self._load_builtin_tools()
    
    def _load_builtin_tools(self) -> None:
        """Register the four built-in tools."""
        # These are defined in src/tools/builtin.py
        from src.tools.builtin import read, write, edit, bash
        # Already registered by @tool decorator
    
    async def chat(self, message: str) -> ChatResponse:
        """Process a message with full agent loop."""
        # Load context
        context = await self.context_loader.assemble()
        
        # Add tool descriptions to system prompt
        system_prompt = self._build_system_prompt(context)
        
        # Run agent loop
        messages = [ChatMessage(role="user", content=message)]
        
        response = await self.agent.run(messages, system_prompt)
        
        return response
    
    async def chat_stream(self, message: str) -> AsyncIterator[str]:
        """Process a message with streaming."""
        context = await self.context_loader.assemble()
        system_prompt = self._build_system_prompt(context)
        
        messages = [ChatMessage(role="user", content=message)]
        
        async for chunk in self.agent.run_stream(messages, system_prompt):
            yield chunk
    
    def _build_system_prompt(self, context) -> str:
        """Build system prompt with tool descriptions."""
        tool_descriptions = []
        for tool in self.tools.list_tools():
            params_desc = ", ".join(
                f"{name}: {info.get('type', 'any')}"
                for name, info in tool.parameters.get("properties", {}).items()
            )
            tool_descriptions.append(
                f"- {tool.name}({params_desc}): {tool.description}"
            )
        
        return f"""{context.system_prompt}

## Available Tools

You have access to the following tools:

{chr(10).join(tool_descriptions)}

To use a tool, respond with a tool call in the format specified by the LLM.
"""
```

### Built-in Tools Module

```python
# src/tools/builtin.py

from src.tools import tool
from typing import Optional
import subprocess


@tool
def read(path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> str:
    """Read file contents. Supports text and images (jpg, png, gif, webp).
    
    Args:
        path: Path to the file to read
        offset: Line number to start from (1-indexed)
        limit: Maximum number of lines to read (max 2000)
    
    Returns:
        File contents as string, or image as attachment
    """
    import os
    
    # Check if image
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
        # Return marker for image handling
        return f"[Image: {path}]"
    
    with open(path) as f:
        lines = f.readlines()
    
    if offset:
        lines = lines[offset - 1:]
    if limit:
        lines = lines[:limit]
    
    result = "".join(lines)
    
    # Truncate if too long
    max_chars = 50000
    if len(result) > max_chars:
        result = result[:max_chars] + "\n[Content truncated...]"
    
    return result


@tool
def write(path: str, content: str) -> dict:
    """Create or overwrite a file.
    
    Args:
        path: Path where to write the file
        content: Content to write
    
    Returns:
        Status dict with path and bytes written
    """
    import os
    
    # Ensure parent directory exists
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    
    with open(path, "w") as f:
        f.write(content)
    
    return {
        "path": path,
        "bytes_written": len(content.encode()),
        "status": "written"
    }


@tool
def edit(path: str, old_text: str, new_text: str) -> dict:
    """Make precise edit to a file by replacing old_text with new_text.
    
    The old_text must match exactly (including whitespace).
    
    Args:
        path: Path to the file to edit
        old_text: Exact text to find and replace
        new_text: Text to replace with
    
    Returns:
        Status dict with path and whether edit was made
    """
    with open(path) as f:
        content = f.read()
    
    if old_text not in content:
        return {
            "path": path,
            "edited": False,
            "error": "old_text not found in file"
        }
    
    new_content = content.replace(old_text, new_text, 1)
    
    with open(path, "w") as f:
        f.write(new_content)
    
    return {
        "path": path,
        "edited": True,
        "bytes_changed": len(new_text) - len(old_text)
    }


@tool
def bash(command: str, timeout: Optional[int] = None) -> dict:
    """Execute a bash command in the current working directory.
    
    Args:
        command: Shell command to execute
        timeout: Timeout in seconds (default: 60, max: 300)
    
    Returns:
        Dict with stdout, stderr, exit_code, and truncated flag
    """
    timeout = min(timeout or 60, 300)  # Max 5 minutes
    
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    
    # Truncate output
    stdout = result.stdout
    stderr = result.stderr
    max_lines = 2000
    max_bytes = 50000
    truncated = False
    
    if len(stdout) > max_bytes or stdout.count('\n') > max_lines:
        lines = stdout.split('\n')[:max_lines]
        stdout = '\n'.join(lines)[:max_bytes]
        stdout += "\n[Output truncated: use file redirection or grep for large outputs]"
        truncated = True
    
    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": result.returncode,
        "truncated": truncated,
    }
```

---

## Milestones

| # | Milestone | Description |
|---|-----------|-------------|
| **1** | Tool Registry | `@tool` decorator, `ToolRegistry`, schema generation |
| **2** | Built-in Tools | Implement `read`, `write`, `edit`, `bash` with truncation |
| **3** | Tool Call Parsing | Parse OpenAI/Kimi tool call format |
| **4** | Agent Loop | `Agent.run()` with iteration limit, error handling |
| **5** | Streaming | `Agent.run_stream()` for CLI/Telegram |
| **6** | Integration | Wire into `Alfred.chat()`, update interfaces |
| **7** | Tests | Unit tests for tools, integration tests for agent loop |

---

## Acceptance Criteria

- [ ] `@tool` decorator registers functions with correct schemas
- [ ] `read` tool handles text files and images
- [ ] `write` tool creates parent directories automatically
- [ ] `edit` tool requires exact match (whitespace-sensitive)
- [ ] `bash` tool truncates output at 50KB/2000 lines
- [ ] Agent loop handles multiple tool calls per iteration
- [ ] Agent loop stops when LLM returns no tool calls
- [ ] Agent loop has max iteration limit (10)
- [ ] Tool errors are caught and returned to LLM
- [ ] Streaming works in both CLI and Telegram
- [ ] Tool schemas included in system prompt
- [ ] All existing tests still pass

---

## Streaming for Interfaces

### Telegram

```python
async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages with streaming."""
    if not update.message or not update.message.text:
        return

    # Send "typing" indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    # Stream response
    full_response = ""
    last_update = 0
    
    async for chunk in self.alfred.chat_stream(update.message.text):
        full_response += chunk
        
        # Update message every 50 chars or on tool execution markers
        if len(full_response) - last_update > 50 or "[Executing" in chunk:
            if update.message.text:  # Only edit if we have a message
                await update.message.edit_text(full_response[:4000])
            last_update = len(full_response)
    
    # Final message
    await update.message.reply_text(full_response[:4000])
```

### CLI

```python
async def run(self) -> None:
    """Run interactive CLI with streaming."""
    print("Alfred CLI. Type 'exit' to quit.\n")
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() == "exit":
            break
        
        print("Alfred: ", end="", flush=True)
        
        async for chunk in self.alfred.chat_stream(user_input):
            print(chunk, end="", flush=True)
        
        print("\n")
```

---

## Tests

```python
# tests/test_tools.py

import pytest
from src.tools import tool, get_registry, ToolRegistry


def test_tool_decorator_registers():
    registry = ToolRegistry()
    
    @tool
    def test_func(name: str, count: int = 5) -> str:
        """Test function."""
        return f"Hello {name}"
    
    assert "test_func" in [t.name for t in registry.list_tools()]


def test_tool_schema_generation():
    registry = ToolRegistry()
    
    @tool
    def test_func(name: str, count: int = 5) -> str:
        """Test function."""
        return f"Hello {name}"
    
    t = registry.get("test_func")
    assert t.parameters["type"] == "object"
    assert "name" in t.parameters["properties"]
    assert t.parameters["properties"]["name"]["type"] == "string"
    assert t.parameters["properties"]["count"]["type"] == "integer"
    assert "name" in t.parameters["required"]
    assert "count" not in t.parameters["required"]


# tests/test_agent.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agent import Agent
from src.tools import ToolRegistry, Tool


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat_with_tools = AsyncMock()
    return llm


@pytest.fixture
def mock_tool_registry():
    registry = ToolRegistry()
    
    # Add a mock tool
    async def mock_execute(x: int) -> dict:
        return {"result": x * 2}
    
    registry.register(Tool(
        name="double",
        description="Double a number",
        parameters={
            "type": "object",
            "properties": {"x": {"type": "integer"}},
            "required": ["x"],
        },
        execute=mock_execute,
        func=mock_execute,
    ))
    
    return registry


@pytest.mark.asyncio
async def test_agent_executes_tools(mock_llm, mock_tool_registry):
    from src.agent import ChatResponse
    
    agent = Agent(mock_llm, mock_tool_registry, MagicMock())
    
    # First response has tool call
    mock_llm.chat_with_tools.side_effect = [
        ChatResponse(
            content="",
            model="test",
            tool_calls=[{
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "double",
                    "arguments": '{"x": 5}',
                },
            }],
        ),
        # Second response is final
        ChatResponse(content="Result is 10", model="test"),
    ]
    
    from src.llm import ChatMessage
    response = await agent.run([ChatMessage(role="user", content="Double 5")])
    
    assert response.content == "Result is 10"
    assert mock_llm.chat_with_tools.call_count == 2
```

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | Decorator-based tools | Clean, Pythonic, auto-extracts schema | `@tool def read(...)` |
| 2026-02-17 | Global registry | Simple, works at import time | Tools auto-register |
| 2026-02-17 | OpenAI tool format | Standard, supported by Kimi | Interoperable |
| 2026-02-17 | Max 10 iterations | Prevent infinite loops | Safety guard |
| 2026-02-17 | Synchronous tool execution | Tools are fast, async adds complexity | Sequential execution |
| 2026-02-17 | Truncate bash output | Protect context window | 50KB/2000 lines |

---

## Dependencies

- `inspect` — For signature introspection (built-in)
- `typing` — For type annotations (built-in)
- OpenAI client — For tool-enabled chat completions

---

## File Structure

```
src/
├── tools/
│   ├── __init__.py      # Tool registry, @tool decorator
│   ├── builtin.py       # read, write, edit, bash
│   └── registry.py      # ToolRegistry class
├── agent.py             # Agent loop implementation
├── alfred.py            # Updated with Agent integration
└── llm.py               # Updated with tool support
```

---

## Notes

- Tools are registered at import time via `@tool` decorator
- Tool schemas are generated from type hints and docstrings
- The agent loop is separate from the LLM provider (clean separation)
- Streaming requires special handling for tool call detection
- Error handling: tool errors are caught and returned to LLM as error messages
