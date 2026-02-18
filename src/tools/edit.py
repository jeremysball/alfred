"""Edit file tool."""

from typing import Any

from pydantic import BaseModel, Field

from src.tools.base import Tool


class EditToolParams(BaseModel):
    """Parameters for EditTool."""
    
    path: str = Field(..., description="Path to the file to edit")
    old_text: str = Field(..., description="Exact text to replace (including whitespace)")
    new_text: str = Field(..., description="New text to insert")
    
    class Config:
        extra = "forbid"


class EditTool(Tool):
    """Make precise edits to a file by replacing text."""

    name = "edit"
    description = "Make precise edit to a file by replacing old_text with new_text. The old_text must match exactly (including whitespace)."
    param_model = EditToolParams

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Replace old_text with new_text in file."""
        path = kwargs.get("path", "")
        old_text = kwargs.get("old_text", "")
        new_text = kwargs.get("new_text", "")
        
        try:
            # Read file
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except FileNotFoundError:
                return {
                    "success": False,
                    "error": f"File not found: {path}",
                    "path": path,
                }

            # Check if old_text exists
            if old_text not in content:
                # Provide context about what was searched
                snippet = content[:200].replace("\n", " ") if len(content) > 200 else content.replace("\n", " ")
                return {
                    "success": False,
                    "edited": False,
                    "error": f"old_text not found in file. File starts with: {snippet}...",
                    "path": path,
                }

            # Replace (only first occurrence)
            new_content = content.replace(old_text, new_text, 1)

            # Check if replacement happened
            if new_content == content:
                return {
                    "success": False,
                    "edited": False,
                    "error": "Replacement failed - old_text may have been found but not replaced",
                    "path": path,
                }

            # Write back
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {
                "success": True,
                "edited": True,
                "path": path,
                "replacements": 1,
                "bytes_changed": len(new_content) - len(content),
            }

        except Exception as e:
            return {
                "success": False,
                "edited": False,
                "error": str(e),
                "path": path,
            }
