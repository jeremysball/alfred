"""Data models for PyPiTUI components."""

from typing import Literal


class ToolCallInfo:
    """Info about a tool call embedded in a message.

    Attributes:
        tool_name: Name of the tool (e.g., "remember", "search")
        tool_call_id: Unique ID for this tool call
        output: Accumulated output from the tool
        status: Current status (running/success/error)
        insert_position: Character position in text where tool box appears
        sequence: Monotonic sequence number to order tools at same position
        arguments: Tool arguments (dict of key=value pairs)
    """

    __slots__ = (
        "tool_name",
        "tool_call_id",
        "output",
        "status",
        "insert_position",
        "sequence",
        "arguments",
    )

    def __init__(
        self,
        tool_name: str,
        tool_call_id: str,
        output: str = "",
        status: Literal["running", "success", "error"] = "running",
        insert_position: int = 0,
        sequence: int = 0,
        arguments: dict[str, object] | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.tool_call_id = tool_call_id
        self.output = output
        self.status = status
        self.insert_position = insert_position
        self.sequence = sequence
        self.arguments = arguments or {}
