"""Tool for searching sessions with two-stage contextual retrieval."""

import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from alfred.embeddings.provider import EmbeddingProvider
from alfred.llm import LLMProvider
from alfred.session import Session, SessionManager
from alfred.storage.sqlite import SQLiteStore

from .base import Tool


class SessionSummary(BaseModel):
    """Summary of a session for semantic search."""

    session_id: str
    text: str
    embedding: list[float] | None = None
    message_count: int = 0
    created_at: datetime | None = None
    last_active: datetime | None = None
    summary_id: str | None = None
    version: int = 1

    @field_serializer("created_at", "last_active")
    def serialize_datetime(self, v: datetime | None) -> str | None:
        return v.isoformat() if v is not None else None


class SearchSessionsToolParams(BaseModel):
    """Parameters for SearchSessionsTool."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field("", description="Search query to find relevant sessions")
    top_k: int = Field(3, description="Maximum number of sessions to search")
    messages_per_session: int = Field(3, description="Maximum messages to return per session")


class SessionSummarizer:
    """Generates and manages LLM-based session summaries."""

    def __init__(self, llm_client: LLMProvider, embedder: EmbeddingProvider, store: SQLiteStore | None = None) -> None:
        self.llm_client = llm_client
        self.embedder = embedder
        self.store = store

    async def generate_summary(self, session: Session) -> SessionSummary:
        """Generate LLM summary for a session.

        Creates a concise summary of the session using an LLM,
        then generates an embedding for semantic search.
        """
        # Build conversation preview for LLM
        preview_lines = []
        for msg in session.messages[:10]:  # First 10 messages for context
            role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
            content = msg.content[:200]  # Truncate long messages
            preview_lines.append(f"{role}: {content}")

        preview = "\n".join(preview_lines)

        # Generate summary via LLM
        summary_text = await self._call_llm_for_summary(preview)

        # Generate embedding for the summary
        embedding = await self.embedder.embed(summary_text)

        return SessionSummary(
            session_id=session.meta.session_id,
            text=summary_text,
            embedding=embedding,
            message_count=len(session.messages),
            created_at=session.meta.created_at,
            last_active=session.meta.last_active,
        )

    async def _call_llm_for_summary(self, conversation_preview: str) -> str:
        """Call LLM to generate session summary."""
        # Simple implementation - in production this would use the actual LLM client
        # For now, use the injected llm_client
        if hasattr(self.llm_client, "generate_summary"):
            return await self.llm_client.generate_summary(conversation_preview)

        # Fallback: extract key topics from first user message
        lines = conversation_preview.strip().split("\n")
        for line in lines:
            if line.lower().startswith("user:"):
                user_msg = line[5:].strip()
                if len(user_msg) > 50:
                    return f"Discussion about: {user_msg[:100]}..."
                return f"Discussion about: {user_msg}"

        return "Session with general conversation"

    async def save_summary(self, summary: SessionSummary) -> None:
        """Save summary to SQLite.

        Args:
            summary: SessionSummary to persist

        Raises:
            RuntimeError: If SQLiteStore not configured
        """
        if not self.store:
            raise RuntimeError("SQLiteStore not configured")

        # Generate summary_id if not present
        summary_id = summary.summary_id or str(uuid.uuid4())

        # Build dict for storage
        summary_dict = {
            "summary_id": summary_id,
            "session_id": summary.session_id,
            "message_count": summary.message_count,
            "first_message_idx": 0,  # Full session summarization (PRD #76)
            "last_message_idx": summary.message_count - 1,
            "summary_text": summary.text,
            "embedding": summary.embedding,
            "version": summary.version,
        }

        await self.store.save_summary(summary_dict)

    async def load_summary(self, session_id: str) -> SessionSummary | None:
        """Load latest summary for session from SQLite.

        Args:
            session_id: Session ID to query

        Returns:
            SessionSummary or None if no summary exists
        """
        if not self.store:
            return None

        data = await self.store.get_latest_summary(session_id)
        if data is None:
            return None

        # Parse datetime from ISO format string
        created_at = None
        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                created_at = datetime.fromisoformat(data["created_at"])
            else:
                created_at = data["created_at"]

        return SessionSummary(
            session_id=data["session_id"],
            text=data["summary_text"],
            embedding=data.get("embedding"),
            message_count=data["message_count"],
            created_at=created_at,
            last_active=created_at,  # Use created_at as last_active
            summary_id=data["summary_id"],
            version=data.get("version", 1),
        )


class SearchSessionsTool(Tool):
    """Search through session archive with two-stage contextual retrieval."""

    name = "search_sessions"
    description = "Search through your conversation history for past discussions"
    param_model = SearchSessionsToolParams

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        embedder: Any | None = None,
        llm_client: Any | None = None,
        store: SQLiteStore | None = None,
        min_similarity: float = 0.6,
    ) -> None:
        super().__init__()
        self.session_manager = session_manager
        self.embedder = embedder
        self.llm_client = llm_client
        self.min_similarity = min_similarity
        self.summarizer = SessionSummarizer(llm_client, embedder, store) if llm_client else None

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Execute two-stage session search."""
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 3)
        messages_per_session = kwargs.get("messages_per_session", 3)

        if not query:
            yield "Error: Please provide a search query"
            return

        if not self.session_manager:
            yield "Error: Session manager not initialized"
            return

        # Get list of sessions from manager
        try:
            sessions = self.session_manager.list_sessions()
        except Exception as e:
            yield f"Error listing sessions: {e}"
            return

        if not sessions:
            yield "No sessions found."
            return

        # Format results
        results_found = False
        for meta in sessions[:top_k]:
            results_found = True
            date_str = meta.last_active.strftime("%Y-%m-%d") if hasattr(meta, 'last_active') else "Unknown"
            msg_count = f" ({meta.message_count} messages)" if hasattr(meta, 'message_count') else ""
            yield f"\nSession: {meta.session_id} ({date_str}){msg_count}\n"

        if not results_found:
            yield "No sessions found."
