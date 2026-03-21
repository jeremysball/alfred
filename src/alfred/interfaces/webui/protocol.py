"""WebSocket protocol definitions for Alfred Web UI.

This module defines the message types used for communication between
the Web UI frontend and the FastAPI backend via WebSocket.
"""

from typing import Literal, NotRequired, TypedDict

JsonObject = dict[str, object]

# Client -> Server Messages


class ChatSendPayload(TypedDict):
    """Payload for chat.send message."""

    content: str
    queue: NotRequired[bool]


class ChatSendMessage(TypedDict):
    """Client sends a chat message."""

    type: Literal["chat.send"]
    payload: ChatSendPayload


class CommandExecutePayload(TypedDict):
    """Payload for command.execute message."""

    command: str


class CommandExecuteMessage(TypedDict):
    """Client executes a command (e.g., /new, /resume)."""

    type: Literal["command.execute"]
    payload: CommandExecutePayload


class CompletionRequestPayload(TypedDict):
    """Payload for completion.request message."""

    text: str
    cursor: int


class CompletionRequestMessage(TypedDict):
    """Client requests completion suggestions."""

    type: Literal["completion.request"]
    payload: CompletionRequestPayload


class AckPayload(TypedDict):
    """Payload for ack message."""

    messageId: str


class AckMessage(TypedDict):
    """Client acknowledges receipt of a message."""

    type: Literal["ack"]
    payload: AckPayload


ClientMessage = ChatSendMessage | CommandExecuteMessage | CompletionRequestMessage | AckMessage


# Server -> Client Messages


class ChatStartedPayload(TypedDict):
    """Payload for chat.started message."""

    messageId: str
    role: Literal["assistant"]


class ChatStartedMessage(TypedDict):
    """Server notifies that a chat response has started."""

    type: Literal["chat.started"]
    payload: ChatStartedPayload


class ChatChunkPayload(TypedDict):
    """Payload for chat.chunk message."""

    messageId: str
    content: str


class ChatChunkMessage(TypedDict):
    """Server streams a token chunk."""

    type: Literal["chat.chunk"]
    payload: ChatChunkPayload


class UsageInfo(TypedDict):
    """Token usage information."""

    inputTokens: int
    outputTokens: int
    cacheReadTokens: int
    reasoningTokens: int


class ChatCompletePayload(TypedDict):
    """Payload for chat.complete message."""

    messageId: str
    finalContent: str
    usage: UsageInfo


class ChatCompleteMessage(TypedDict):
    """Server notifies that chat response is complete."""

    type: Literal["chat.complete"]
    payload: ChatCompletePayload


class ChatErrorPayload(TypedDict):
    """Payload for chat.error message."""

    messageId: str
    error: str


class ChatErrorMessage(TypedDict):
    """Server notifies of a chat error."""

    type: Literal["chat.error"]
    payload: ChatErrorPayload


class ToolStartPayload(TypedDict):
    """Payload for tool.start message."""

    toolCallId: str
    toolName: str
    arguments: JsonObject
    messageId: str


class ToolStartMessage(TypedDict):
    """Server notifies that tool execution started."""

    type: Literal["tool.start"]
    payload: ToolStartPayload


class ToolOutputPayload(TypedDict):
    """Payload for tool.output message."""

    toolCallId: str
    chunk: str


class ToolOutputMessage(TypedDict):
    """Server streams tool output."""

    type: Literal["tool.output"]
    payload: ToolOutputPayload


class ToolEndPayload(TypedDict):
    """Payload for tool.end message."""

    toolCallId: str
    success: bool
    output: NotRequired[str]


class ToolEndMessage(TypedDict):
    """Server notifies that tool execution completed."""

    type: Literal["tool.end"]
    payload: ToolEndPayload


class CompletionSuggestion(TypedDict):
    """A single completion suggestion."""

    value: str
    description: NotRequired[str]


class CompletionSuggestionsPayload(TypedDict):
    """Payload for completion.suggestions message."""

    suggestions: list[CompletionSuggestion]


class CompletionSuggestionsMessage(TypedDict):
    """Server sends completion suggestions."""

    type: Literal["completion.suggestions"]
    payload: CompletionSuggestionsPayload


class StatusUpdatePayload(TypedDict):
    """Payload for status.update message."""

    model: str
    contextTokens: int
    inputTokens: int
    outputTokens: int
    cacheReadTokens: int
    reasoningTokens: int
    queueLength: int
    isStreaming: bool


class StatusUpdateMessage(TypedDict):
    """Server sends status update."""

    type: Literal["status.update"]
    payload: StatusUpdatePayload


class ToastPayload(TypedDict):
    """Payload for toast message."""

    message: str
    level: Literal["info", "success", "warning", "error"]
    duration: NotRequired[int]


class ToastMessage(TypedDict):
    """Server sends toast notification."""

    type: Literal["toast"]
    payload: ToastPayload


class SessionMessage(TypedDict):
    """A message in a session."""

    id: str
    role: Literal["user", "assistant", "system"]
    content: str


class SessionLoadedPayload(TypedDict):
    """Payload for session.loaded message."""

    sessionId: str
    messages: list[SessionMessage]


class SessionLoadedMessage(TypedDict):
    """Server notifies that session was loaded."""

    type: Literal["session.loaded"]
    payload: SessionLoadedPayload


ServerMessage = (
    ChatStartedMessage
    | ChatChunkMessage
    | ChatCompleteMessage
    | ChatErrorMessage
    | ToolStartMessage
    | ToolOutputMessage
    | ToolEndMessage
    | CompletionSuggestionsMessage
    | StatusUpdateMessage
    | ToastMessage
    | SessionLoadedMessage
)
