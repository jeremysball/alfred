"""Write file tool."""

from pathlib import Path

from pydantic import BaseModel, Field

from src.tools.base import Tool
from src.type_defs import JsonObject, JsonValue


class WriteToolParams(BaseModel):
    """Parameters for WriteTool."""

    path: str = Field(..., description="Path to the file to write")
    content: str = Field(..., description="Content to write to the file")

    class Config:
        extra = "forbid"


class WriteTool(Tool):
    """Create or overwrite a file."""

    name = "write"
    description = "Create or overwrite a file. Automatically creates parent directories if needed."
    param_model = WriteToolParams

    def execute(self, **kwargs: JsonValue) -> JsonObject:
        """Write content to file, creating parent directories if needed."""
        path_value = kwargs.get("path")
        content_value = kwargs.get("content")

        if not isinstance(path_value, str) or not isinstance(content_value, str):
            return {
                "success": False,
                "error": "Invalid parameters for write",
                "path": path_value if isinstance(path_value, str) else "",
            }

        path = path_value
        content = content_value

        try:
            # Create parent directories if needed
            parent = Path(path).parent
            if parent and not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "path": path,
                "bytes_written": len(content.encode("utf-8")),
                "lines_written": content.count("\n")
                + (1 if content and not content.endswith("\n") else 0),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": path,
            }
