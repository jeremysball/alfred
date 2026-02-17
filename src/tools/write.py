"""Write file tool."""

import os
from pathlib import Path

from pydantic import Field

from src.tools.base import Tool


class WriteTool(Tool):
    """Create or overwrite a file."""

    name = "write"
    description = "Create or overwrite a file. Automatically creates parent directories if needed."

    def execute(
        self,
        path: str,
        content: str,
    ) -> dict:
        """Write content to file, creating parent directories if needed."""
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
