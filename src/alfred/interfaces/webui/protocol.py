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


class ChatCancelMessage(TypedDict):
    """Client cancels the active assistant response."""

    type: Literal["chat.cancel"]


class ChatEditPayload(TypedDict):
    """Payload for chat.edit message."""

    messageId: str
    content: str


class ChatEditMessage(TypedDict):
    """Client edits the last completed user message."""

    type: Literal["chat.edit"]
    payload: ChatEditPayload


ClientMessage = ChatSendMessage | CommandExecuteMessage | CompletionRequestMessage | AckMessage | ChatCancelMessage | ChatEditMessage


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


class ChatCancelledPayload(TypedDict):
    """Payload for chat.cancelled message."""

    messageId: str


class ChatCancelledMessage(TypedDict):
    """Server confirms that the active response was canceled."""

    type: Literal["chat.cancelled"]
    payload: ChatCancelledPayload


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


class DaemonStatusInfo(TypedDict):
    """Details about the cron daemon runtime state."""

    state: Literal["running", "stopped", "starting", "failed", "unknown"]
    pid: int | None
    socketPath: str | None
    socketHealthy: bool | None
    startedAt: str | None
    uptimeSeconds: int | None
    lastHeartbeatAt: str | None
    lastReloadAt: str | None
    lastError: str | None


class DaemonStatusPayload(TypedDict):
    """Payload for daemon.status message."""

    daemon: DaemonStatusInfo


class DaemonStatusMessage(TypedDict):
    """Server sends daemon runtime status."""

    type: Literal["daemon.status"]
    payload: DaemonStatusPayload


class ContextConflictPayload(TypedDict):
    """Structured conflict record for a blocked context file."""

    id: str
    name: str
    label: str
    reason: str


class ContextStatusPayload(TypedDict):
    """Lightweight context-health snapshot used for persistent Web UI warnings."""

    blockedContextFiles: list[str]
    conflictedContextFiles: list[ContextConflictPayload]
    warnings: list[str]


class StatusUpdatePayload(TypedDict):
    """Payload for status.update message."""

    model: str
    contextTokens: int
    contextWindowTokens: NotRequired[int | None]
    inputTokens: int
    outputTokens: int
    cacheReadTokens: int
    reasoningTokens: int
    queueLength: int
    isStreaming: bool
    contextStatus: NotRequired[ContextStatusPayload | None]


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
    reasoningContent: NotRequired[str]
    textBlocks: NotRequired[list[JsonObject]]
    toolCalls: NotRequired[list[JsonObject]]
    streaming: NotRequired[bool]


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
    | ChatCancelledMessage
    | ToolStartMessage
    | ToolOutputMessage
    | ToolEndMessage
    | CompletionSuggestionsMessage
    | DaemonStatusMessage
    | StatusUpdateMessage
    | ToastMessage
    | SessionLoadedMessage
)
