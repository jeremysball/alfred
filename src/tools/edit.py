"""Edit file tool."""

from pydantic import Field

from src.tools.base import Tool


class EditTool(Tool):
    """Make precise edits to a file by replacing text."""

    name = "edit"
    description = "Make precise edit to a file by replacing old_text with new_text. The old_text must match exactly (including whitespace)."

    def execute(
        self,
        path: str,
        old_text: str,
        new_text: str,
    ) -> dict:
        """Replace old_text with new_text in file."""
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
