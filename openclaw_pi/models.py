"""Data models for threads and messages."""
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Optional


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Message(BaseModel):
    """A single message in a thread."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=utcnow)


class Thread(BaseModel):
    """A conversation thread with message history."""
    thread_id: str
    chat_id: int
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    messages: list[Message] = []
    active_subagent: Optional[str] = None
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the thread."""
        self.messages.append(Message(role=role, content=content))
        self.updated_at = utcnow()
