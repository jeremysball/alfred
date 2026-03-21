"""Pydantic validation models for WebSocket protocol messages.

This module provides validation functions and Pydantic models for ensuring
WebSocket messages conform to the expected protocol structure.
"""

from typing import Literal

from pydantic import BaseModel, Field, ValidationError

JsonObject = dict[str, object]

# =============================================================================
# Client -> Server Messages (Incoming)
# =============================================================================


class ChatSendPayload(BaseModel):
    """Payload for chat.send message."""

    content: str = Field(..., min_length=1, description="The message content")
    queue: bool = Field(default=False, description="Whether to queue the message")


class ChatSendMessage(BaseModel):
    """Client sends a chat message."""

    type: Literal["chat.send"]
    payload: ChatSendPayload


class CommandExecutePayload(BaseModel):
    """Payload for command.execute message."""

    command: str = Field(..., min_length=1, description="The command to execute")


class CommandExecuteMessage(BaseModel):
    """Client executes a command (e.g., /new, /resume)."""

    type: Literal["command.execute"]
    payload: CommandExecutePayload


class CompletionRequestPayload(BaseModel):
    """Payload for completion.request message."""

    text: str = Field(..., description="The text to complete")
    cursor: int = Field(..., ge=0, description="Cursor position in text")


class CompletionRequestMessage(BaseModel):
    """Client requests completion suggestions."""

    type: Literal["completion.request"]
    payload: CompletionRequestPayload


class AckPayload(BaseModel):
    """Payload for ack message."""

    message_id: str = Field(..., alias="messageId", description="ID of message being acknowledged")

    model_config = {"populate_by_name": True}


class AckMessage(BaseModel):
    """Client acknowledges receipt of a message."""

    type: Literal["ack"]
    payload: AckPayload


# Union type for all client messages
ClientMessage = ChatSendMessage | CommandExecuteMessage | CompletionRequestMessage | AckMessage


# =============================================================================
# Server -> Client Messages (Outgoing)
# =============================================================================


class ChatStartedPayload(BaseModel):
    """Payload for chat.started message."""

    message_id: str = Field(..., alias="messageId", description="Unique message ID")
    role: Literal["assistant"] = Field(default="assistant", description="Message role")

    model_config = {"populate_by_name": True}


class ChatStartedMessage(BaseModel):
    """Server notifies that a chat response has started."""

    type: Literal["chat.started"]
    payload: ChatStartedPayload


class ChatChunkPayload(BaseModel):
    """Payload for chat.chunk message."""

    message_id: str = Field(..., alias="messageId", description="Unique message ID")
    content: str = Field(..., description="Token chunk content")

    model_config = {"populate_by_name": True}


class ChatChunkMessage(BaseModel):
    """Server streams a token chunk."""

    type: Literal["chat.chunk"]
    payload: ChatChunkPayload


class UsageInfo(BaseModel):
    """Token usage information."""

    input_tokens: int = Field(..., alias="inputTokens", ge=0)
    output_tokens: int = Field(..., alias="outputTokens", ge=0)
    cache_read_tokens: int = Field(..., alias="cacheReadTokens", ge=0)
    reasoning_tokens: int = Field(..., alias="reasoningTokens", ge=0)

    model_config = {"populate_by_name": True}


class ChatCompletePayload(BaseModel):
    """Payload for chat.complete message."""

    message_id: str = Field(..., alias="messageId", description="Unique message ID")
    final_content: str = Field(..., alias="finalContent", description="Complete response")
    usage: UsageInfo = Field(..., description="Token usage info")

    model_config = {"populate_by_name": True}


class ChatCompleteMessage(BaseModel):
    """Server notifies that chat response is complete."""

    type: Literal["chat.complete"]
    payload: ChatCompletePayload


class ChatErrorPayload(BaseModel):
    """Payload for chat.error message."""

    message_id: str = Field(..., alias="messageId", description="Unique message ID")
    error: str = Field(..., description="Error message")

    model_config = {"populate_by_name": True}


class ChatErrorMessage(BaseModel):
    """Server notifies of a chat error."""

    type: Literal["chat.error"]
    payload: ChatErrorPayload


class ToolStartPayload(BaseModel):
    """Payload for tool.start message."""

    tool_call_id: str = Field(..., alias="toolCallId", description="Tool call ID")
    tool_name: str = Field(..., alias="toolName", description="Tool name")
    arguments: JsonObject = Field(default_factory=dict, description="Tool arguments")
    message_id: str = Field(..., alias="messageId", description="Parent message ID")

    model_config = {"populate_by_name": True}


class ToolStartMessage(BaseModel):
    """Server notifies that tool execution started."""

    type: Literal["tool.start"]
    payload: ToolStartPayload


class ToolOutputPayload(BaseModel):
    """Payload for tool.output message."""

    tool_call_id: str = Field(..., alias="toolCallId", description="Tool call ID")
    chunk: str = Field(..., description="Output chunk")

    model_config = {"populate_by_name": True}


class ToolOutputMessage(BaseModel):
    """Server streams tool output."""

    type: Literal["tool.output"]
    payload: ToolOutputPayload


class ToolEndPayload(BaseModel):
    """Payload for tool.end message."""

    tool_call_id: str = Field(..., alias="toolCallId", description="Tool call ID")
    success: bool = Field(..., description="Whether tool execution succeeded")
    output: str | None = Field(default=None, description="Final output if success")

    model_config = {"populate_by_name": True}


class ToolEndMessage(BaseModel):
    """Server notifies that tool execution completed."""

    type: Literal["tool.end"]
    payload: ToolEndPayload


class CompletionSuggestion(BaseModel):
    """A single completion suggestion."""

    value: str = Field(..., description="Completion value")
    description: str | None = Field(default=None, description="Optional description")


class CompletionSuggestionsPayload(BaseModel):
    """Payload for completion.suggestions message."""

    suggestions: list[CompletionSuggestion] = Field(..., description="List of suggestions")


class CompletionSuggestionsMessage(BaseModel):
    """Server sends completion suggestions."""

    type: Literal["completion.suggestions"]
    payload: CompletionSuggestionsPayload


class StatusUpdatePayload(BaseModel):
    """Payload for status.update message."""

    model: str = Field(..., description="Current model name")
    context_tokens: int = Field(..., alias="contextTokens", ge=0)
    input_tokens: int = Field(..., alias="inputTokens", ge=0)
    output_tokens: int = Field(..., alias="outputTokens", ge=0)
    cache_read_tokens: int = Field(..., alias="cacheReadTokens", ge=0)
    reasoning_tokens: int = Field(..., alias="reasoningTokens", ge=0)
    queue_length: int = Field(..., alias="queueLength", ge=0)
    is_streaming: bool = Field(..., alias="isStreaming")

    model_config = {"populate_by_name": True}


class StatusUpdateMessage(BaseModel):
    """Server sends status update."""

    type: Literal["status.update"]
    payload: StatusUpdatePayload


class ToastPayload(BaseModel):
    """Payload for toast message."""

    message: str = Field(..., min_length=1, description="Toast message")
    level: Literal["info", "success", "warning", "error"] = Field(default="info")
    duration: int | None = Field(default=None, ge=1000, description="Duration in ms")


class ToastMessage(BaseModel):
    """Server sends toast notification."""

    type: Literal["toast"]
    payload: ToastPayload


class SessionMessage(BaseModel):
    """A message in a session."""

    id: str = Field(..., description="Message ID")
    role: Literal["user", "assistant", "system"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class SessionLoadedPayload(BaseModel):
    """Payload for session.loaded message."""

    session_id: str = Field(..., alias="sessionId", description="Session ID")
    messages: list[SessionMessage] = Field(default_factory=list, description="Session messages")

    model_config = {"populate_by_name": True}


class SessionLoadedMessage(BaseModel):
    """Server notifies that session was loaded."""

    type: Literal["session.loaded"]
    payload: SessionLoadedPayload


# Union type for all server messages
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


# =============================================================================
# Validation Functions
# =============================================================================


def validate_client_message(data: JsonObject) -> tuple[bool, ClientMessage | None, str]:
    """Validate incoming client message.

    Args:
        data: Parsed JSON dict from WebSocket

    Returns:
        Tuple of (is_valid, validated_message_or_none, error_message)
    """
    if not isinstance(data, dict):
        return False, None, "Message must be a JSON object"

    message_type = data.get("type")
    if not message_type:
        return False, None, "Message must have a 'type' field"

    try:
        match message_type:
            case "chat.send":
                return True, ChatSendMessage.model_validate(data), ""
            case "command.execute":
                return True, CommandExecuteMessage.model_validate(data), ""
            case "completion.request":
                return True, CompletionRequestMessage.model_validate(data), ""
            case "ack":
                return True, AckMessage.model_validate(data), ""
            case _:
                return False, None, f"Unknown message type: {message_type}"
    except ValidationError as e:
        errors = "; ".join(
            f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
            for err in e.errors()
        )
        return False, None, f"Validation error: {errors}"


def create_validation_error_response(message_id: str, error: str) -> JsonObject:
    """Create a chat.error response for validation failures.

    Args:
        message_id: The message ID to reference
        error: The error message

    Returns:
        Dict representing a chat.error message
    """
    return {
        "type": "chat.error",
        "payload": {
            "messageId": message_id,
            "error": error
        }
    }
