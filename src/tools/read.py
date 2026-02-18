"""Read file contents tool."""

import os
from typing import Any

from pydantic import BaseModel, Field

from src.tools.base import Tool


class ReadToolParams(BaseModel):
    """Parameters for ReadTool."""
    
    path: str = Field(..., description="Path to the file to read")
    offset: int | None = Field(None, description="Line number to start reading from (1-indexed)")
    limit: int | None = Field(None, description="Maximum number of lines to read")
    
    class Config:
        extra = "forbid"


class ReadTool(Tool):
    """Read file contents. Supports text files and images."""
    
    name = "read"
    description = "Read file contents. Supports text files (with optional line offset/limit) and images (jpg, png, gif, webp)."
    param_model = ReadToolParams
    
    def execute(self, **kwargs: Any) -> str:
        """Read file contents with optional pagination."""
        path = kwargs.get("path", "")
        offset = kwargs.get("offset")
        limit = kwargs.get("limit")
        
        # Validate path exists
        if not os.path.exists(path):
            return f"Error: File not found: {path}"
        
        # Check if image
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'):
            # For now, return marker indicating it's an image
            # In future, could return base64 or send directly to LLM
            file_size = os.path.getsize(path)
            return f"[Image file: {path}, size: {file_size} bytes, type: {ext[1:]}]"
        
        # Read text file
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Binary file
            return f"Error: File appears to be binary: {path}"
        except Exception as e:
            return f"Error reading file: {e}"
        
        # Apply offset
        if offset:
            if offset < 1:
                return "Error: offset must be >= 1"
            lines = lines[offset - 1:]
        
        # Apply limit
        if limit:
            lines = lines[:limit]
        
        result = "".join(lines)
        
        # Truncate if too long (50KB / 2000 lines)
        max_bytes = 50000
        max_lines = 2000
        
        if len(result) > max_bytes or len(lines) > max_lines:
            # Truncate to safe limits
            result_lines = result.split('\n')[:max_lines]
            result = '\n'.join(result_lines)
            if len(result) > max_bytes:
                result = result[:max_bytes]
            result += "\n\n[Output truncated: file too large. Use offset/limit to read specific sections.]"
        
        # If empty result, mention it
        if not result.strip():
            return "[File is empty]"
        
        return result
