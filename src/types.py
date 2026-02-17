"""Shared type definitions for Alfred."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """A single memory entry with metadata."""

    timestamp: datetime
    role: Literal["user", "assistant", "system"]
    content: str
    embedding: list[float] | None = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


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
