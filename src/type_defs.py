from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Literal, Protocol, TypedDict, TypeGuard, runtime_checkable

type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
type JsonObject = dict[str, JsonValue]
type JsonList = list[JsonValue]

type MemoryRole = Literal["user", "assistant", "system"]
type ChatRole = Literal["system", "user", "assistant", "tool"]


@runtime_checkable
class MemoryEntryLike(Protocol):
    entry_id: str | None
    timestamp: datetime
    role: MemoryRole
    content: str
    embedding: list[float] | None
    tags: list[str]
    permanent: bool


type ToolArguments = dict[str, JsonValue]
type ToolOutput = str | JsonObject
type AsyncHandler = Callable[[], Awaitable[None]]


class ToolCallFunction(TypedDict):
    name: str
    arguments: str


class ToolCall(TypedDict):
    id: str
    type: Literal["function"]
    function: ToolCallFunction


class ToolSchemaFunction(TypedDict):
    name: str
    description: str
    parameters: JsonObject


class ToolSchema(TypedDict):
    type: Literal["function"]
    function: ToolSchemaFunction


class PromptTokensDetails(TypedDict, total=False):
    cached_tokens: int


class CompletionTokensDetails(TypedDict, total=False):
    reasoning_tokens: int


class UsageData(TypedDict, total=False):
    prompt_tokens: int
    completion_tokens: int
    prompt_tokens_details: PromptTokensDetails
    completion_tokens_details: CompletionTokensDetails


type ToolCallStatus = Literal["success", "error"]


class ContextSection(TypedDict):
    name: str
    tokens: int


class ContextSystemPrompt(TypedDict):
    sections: list[ContextSection]
    total_tokens: int


class ContextMemoryItem(TypedDict):
    content: str
    role: MemoryRole
    timestamp: str


class ContextMemories(TypedDict):
    displayed: int
    total: int
    items: list[ContextMemoryItem]
    tokens: int


class ContextMessageItem(TypedDict):
    role: str
    content: str


class ContextSessionHistory(TypedDict):
    count: int
    messages: list[ContextMessageItem]
    tokens: int


class ContextToolCallItem(TypedDict):
    tool_name: str
    arguments: ToolArguments
    output: str
    status: ToolCallStatus


class ContextToolCalls(TypedDict):
    count: int
    items: list[ContextToolCallItem]
    tokens: int


class ContextDisplay(TypedDict):
    system_prompt: ContextSystemPrompt
    memories: ContextMemories
    session_history: ContextSessionHistory
    tool_calls: ContextToolCalls
    total_tokens: int


def is_json_value(value: object) -> TypeGuard[JsonValue]:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and is_json_value(val) for key, val in value.items())
    return False


def ensure_json_object(value: object) -> JsonObject:
    if not isinstance(value, dict):
        raise TypeError(f"Expected JSON object, got {type(value).__name__}")

    for key, val in value.items():
        if not isinstance(key, str):
            raise TypeError("JSON object keys must be strings")
        if not is_json_value(val):
            raise TypeError("JSON object values must be JSON-compatible")

    return value
