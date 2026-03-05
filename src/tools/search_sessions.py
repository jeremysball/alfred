"""Tool for searching sessions with two-stage contextual retrieval."""

import json
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.embeddings import cosine_similarity
from src.session import Session
from src.session_storage import SessionStorage

from .base import Tool


class SessionSummary(BaseModel):
    """Summary of a session for semantic search."""

    session_id: str
    text: str
    embedding: list[float] | None = None
    message_count: int = 0
    created_at: datetime | None = None
    last_active: datetime | None = None

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

    def __init__(self, llm_client: Any, embedder: Any) -> None:
        self.llm_client = llm_client
        self.embedder = embedder

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

    async def save_summary(self, summary: SessionSummary, session_dir: Path) -> None:
        """Save summary to summary.json in session directory."""
        summary_path = session_dir / "summary.json"

        data = {
            "session_id": summary.session_id,
            "text": summary.text,
            "embedding": summary.embedding,
            "message_count": summary.message_count,
            "created_at": summary.created_at.isoformat() if summary.created_at else None,
            "last_active": summary.last_active.isoformat() if summary.last_active else None,
        }

        summary_path.write_text(json.dumps(data, indent=2))

    async def load_summary(self, session_dir: Path) -> SessionSummary | None:
        """Load summary from summary.json if it exists."""
        summary_path = session_dir / "summary.json"
        if not summary_path.exists():
            return None

        try:
            data = json.loads(summary_path.read_text())
            return SessionSummary(
                session_id=data["session_id"],
                text=data["text"],
                embedding=data.get("embedding"),
                message_count=data.get("message_count", 0),
                created_at=datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else None,  # noqa: E501
                last_active=datetime.fromisoformat(data["last_active"])
                if data.get("last_active")
                else None,  # noqa: E501
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None


class SearchSessionsTool(Tool):
    """Search through session archive with two-stage contextual retrieval."""

    name = "search_sessions"
    description = "Search through your conversation history for past discussions"
    param_model = SearchSessionsToolParams

    def __init__(
        self,
        storage: SessionStorage,
        embedder: Any,
        llm_client: Any | None = None,
        min_similarity: float = 0.6,
    ) -> None:
        super().__init__()
        self.storage = storage
        self.embedder = embedder
        self.llm_client = llm_client
        self.min_similarity = min_similarity
        self.summarizer = SessionSummarizer(llm_client, embedder) if llm_client else None

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Execute two-stage session search.

        Stage 1: Find relevant sessions by searching summaries
        Stage 2: Search messages within those sessions

        Yields:
            Formatted hierarchical results
        """
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 3)
        messages_per_session = kwargs.get("messages_per_session", 3)

        if not query:
            yield "Error: Please provide a search query"
            return

        # Stage 1: Find relevant sessions
        sessions = await self._find_relevant_sessions(query, top_k)

        if not sessions:
            yield "No relevant sessions found."
            return

        # Stage 2: Search within each session
        results_found = False
        for session_info in sessions:
            session_id = session_info["session_id"]
            summary_text = session_info.get("summary", "")
            meta = session_info.get("meta")

            # Search messages in this session
            messages = await self._search_session_messages(session_id, query, messages_per_session)

            if messages:
                results_found = True

                # Format session header
                date_str = "Unknown date"
                message_count_str = ""
                if meta:
                    if hasattr(meta, "created_at") and meta.created_at:
                        date_str = meta.created_at.strftime("%Y-%m-%d")
                    if hasattr(meta, "message_count"):
                        message_count_str = f" ({meta.message_count} messages)"

                yield f"\nSession: {session_id} ({date_str}){message_count_str}\n"

                if summary_text:
                    yield f"Summary: {summary_text}\n"

                # Format messages
                for msg in messages:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    # Truncate long messages
                    if len(content) > 200:
                        content = content[:200] + "..."
                    yield f"  [{role}] {content}\n"

        if not results_found:
            yield "Found sessions but no matching messages within them."

    async def _find_relevant_sessions(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Stage 1: Find relevant sessions by searching summaries.

        Returns list of session info dicts with session_id, summary, meta, similarity.
        """
        # Get query embedding
        query_embedding = await self.embedder.embed(query)

        # Load all session summaries
        session_scores: list[tuple[float, dict[str, Any]]] = []

        session_ids = self.storage.list_sessions()

        for session_id in session_ids:
            session_dir = self.storage.sessions_dir / session_id

            # Try to load summary
            summary = None
            if self.summarizer:
                summary = await self.summarizer.load_summary(session_dir)

            # Load metadata
            meta = self.storage.get_meta(session_id)

            if summary and summary.embedding:
                # Use summary embedding for search
                similarity = cosine_similarity(query_embedding, summary.embedding)
                if similarity >= self.min_similarity:
                    session_scores.append(
                        (
                            similarity,
                            {
                                "session_id": session_id,
                                "summary": summary.text,
                                "meta": meta,
                                "similarity": similarity,
                            },
                        )
                    )
            else:
                # Fallback: use a simple heuristic based on message count and recency
                if meta:
                    # Score based on recency (simplistic fallback)
                    session_scores.append(
                        (
                            0.5,  # Default similarity for sessions without summaries
                            {
                                "session_id": session_id,
                                "summary": "",
                                "meta": meta,
                                "similarity": 0.5,
                            },
                        )
                    )

        # Sort by similarity and return top_k
        session_scores.sort(key=lambda x: x[0], reverse=True)
        return [info for _, info in session_scores[:top_k]]

    async def _search_session_messages(
        self, session_id: str, query: str, top_k: int
    ) -> list[dict[str, Any]]:
        """Stage 2: Search messages within a specific session.

        Returns list of message dicts with role, content, similarity.
        """
        # Get query embedding
        query_embedding = await self.embedder.embed(query)

        # Load messages from session
        messages_with_scores: list[tuple[float, dict[str, Any]]] = []

        session_dir = self.storage.sessions_dir / session_id
        current_path = session_dir / "current.jsonl"
        archive_path = session_dir / "archive.jsonl"

        # Search current.jsonl
        if current_path.exists():
            async for msg in self._iter_messages(current_path):
                if msg.get("embedding"):
                    similarity = cosine_similarity(query_embedding, msg["embedding"])
                    if similarity >= self.min_similarity:
                        messages_with_scores.append((similarity, msg))

        # Search archive.jsonl
        if archive_path.exists():
            async for msg in self._iter_messages(archive_path):
                if msg.get("embedding"):
                    similarity = cosine_similarity(query_embedding, msg["embedding"])
                    if similarity >= self.min_similarity:
                        messages_with_scores.append((similarity, msg))

        # Sort by similarity and return top_k
        messages_with_scores.sort(key=lambda x: x[0], reverse=True)
        return [msg for _, msg in messages_with_scores[:top_k]]

    async def _iter_messages(self, path: Path) -> AsyncIterator[dict[str, Any]]:
        """Iterate over messages in a JSONL file."""
        import aiofiles

        if not path.exists():
            return

        async with aiofiles.open(path) as f:
            async for line in f:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
