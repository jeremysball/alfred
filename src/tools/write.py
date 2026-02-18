"""Write file tool."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.tools.base import Tool


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

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Write content to file, creating parent directories if needed."""
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")

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
                "lines_written": content.count("\n") + (1 if content and not content.endswith("\n") else 0),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": path,
            }
