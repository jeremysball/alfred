"""Shared type definitions for Alfred."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """A single memory entry with metadata."""

    timestamp: datetime
    role: Literal["user", "assistant", "system"]
    content: str
    embedding: list[float] | None = None
    tags: list[str] = Field(default_factory=list)
    entry_id: str | None = None  # Hash of timestamp + content

    def generate_id(self) -> str:
        """Generate unique ID from timestamp and content."""
        import hashlib

        content = f"{self.timestamp.isoformat()}:{self.content}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def model_post_init(self, __context: Any) -> None:
        """Auto-generate ID if not set."""
        if self.entry_id is None:
            self.entry_id = self.generate_id()


class DailyMemory(BaseModel):
    """All memories for a single day."""

    date: date  # YYYY-MM-DD as actual date type
    entries: list[MemoryEntry] = Field(default_factory=list)


class ContextFile(BaseModel):
    """A loaded context file with metadata."""

    name: str
    path: str
    content: str
    last_modified: datetime


class AssembledContext(BaseModel):
    """Complete assembled context for LLM prompt."""

    agents: str
    soul: str
    user: str
    tools: str
    memories: list[MemoryEntry]
    system_prompt: str  # Combined
