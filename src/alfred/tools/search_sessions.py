"""Tool for searching sessions with two-stage contextual retrieval."""

import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from alfred.embeddings.provider import EmbeddingProvider
from alfred.llm import LLMProvider
from alfred.session import Session, SessionManager
from alfred.storage.sqlite import SQLiteStore

from .base import Tool

logger = logging.getLogger(__name__)


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
    after: str | None = Field(
        None,
        description="Filter sessions after this date/time (ISO 8601 format)"
    )
    before: str | None = Field(
        None,
        description="Filter sessions before this date/time (ISO 8601 format)"
    )


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
        """Call LLM to generate session summary.

        Uses the injected LLM client to generate a concise summary
        of the conversation topics and outcomes.
        """
        if not self.llm_client:
            # Fallback if no LLM available
            lines = conversation_preview.strip().split("\n")
            for line in lines:
                if line.lower().startswith("user:"):
                    user_msg = line[5:].strip()
                    if len(user_msg) > 50:
                        return f"Discussion about: {user_msg[:100]}..."
                    return f"Discussion about: {user_msg}"
            return "Session with general conversation"

        # Import here to avoid circular imports
        from alfred.llm import ChatMessage

        messages = [
            ChatMessage(
                role="system",
                content=(
                    "You are a helpful assistant that summarizes conversations. "
                    "Create a concise 1-2 sentence summary of the main topic(s) discussed. "
                    "Focus on what was accomplished or decided, not every detail. "
                    "Be specific about the subject matter (e.g., 'Fixed Python import error in search module' "
                    "rather than just 'Worked on code')."
                ),
            ),
            ChatMessage(
                role="user",
                content=f"Summarize this conversation:\n\n{conversation_preview}",
            ),
        ]

        try:
            response = await self.llm_client.chat(messages)
            summary = response.content.strip()
            # Limit length for embedding efficiency
            if len(summary) > 200:
                summary = summary[:197] + "..."
            return summary
        except Exception as e:
            # Fallback on LLM error
            logger = logging.getLogger(__name__)
            logger.warning(f"LLM summary generation failed: {e}, using fallback")
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
            created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]

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
        summarizer: SessionSummarizer | None = None,
        min_similarity: float = 0.5,
    ) -> None:
        super().__init__()
        self.session_manager = session_manager
        self.embedder = embedder
        self.llm_client = llm_client
        self.min_similarity = min_similarity
        self.summarizer = summarizer

    async def _find_relevant_sessions(
        self,
        query_embedding: list[float],
        top_k: int = 3,
        after: datetime | None = None,
        before: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Stage 1: Find relevant sessions via summary search.

        Args:
            query_embedding: Pre-computed query embedding vector
            top_k: Maximum sessions to return
            after: Only return sessions created after this datetime
            before: Only return sessions created before this datetime

        Returns:
            List of {summary_id, session_id, summary_text, similarity}
        """
        if not self.summarizer or not self.summarizer.store:
            raise RuntimeError("SQLiteStore not configured for search")

        # Search summaries with optional date filtering
        return await self.summarizer.store.search_summaries(
            query_embedding, top_k, after=after, before=before
        )

    async def _search_session_messages(self, session_id: str, query_embedding: list[float], top_k: int = 3) -> list[dict[str, Any]]:
        """Stage 2: Search messages within a session.

        Args:
            session_id: Session to search
            query_embedding: Query embedding
            top_k: Maximum messages to return

        Returns:
            List of {message_idx, role, content_snippet, similarity}
        """
        if not self.summarizer or not self.summarizer.store:
            return []

        return await self.summarizer.store.search_session_messages(session_id, query_embedding, top_k)

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Execute two-stage session search."""
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 3)
        messages_per_session = kwargs.get("messages_per_session", 3)
        after_str = kwargs.get("after")
        before_str = kwargs.get("before")

        # Check for wildcard query to list all sessions
        is_wildcard = query in ("*", "*.*", "all", "ALL")

        if not query:
            yield "Error: Please provide a search query"
            return

        if not self.summarizer or not self.summarizer.store:
            yield "Error: Session search not configured"
            return

        # Parse date filters
        after: datetime | None = None
        before: datetime | None = None

        if after_str:
            try:
                after = datetime.fromisoformat(after_str.replace("Z", "+00:00"))
            except ValueError as e:
                yield f"Error: Invalid 'after' date format. Use ISO 8601 (e.g., '2024-01-01' or '2024-01-01T10:00:00'): {e}"
                return

        if before_str:
            try:
                before = datetime.fromisoformat(before_str.replace("Z", "+00:00"))
            except ValueError as e:
                yield f"Error: Invalid 'before' date format. Use ISO 8601 (e.g., '2024-12-31' or '2024-12-31T23:59:59'): {e}"
                return

        try:
            logger.debug(f"Session search: query='{query}', top_k={top_k}, min_similarity={self.min_similarity}")

            if is_wildcard:
                # Wildcard mode: list all sessions (filtered by date if provided)
                sessions = await self.summarizer.store.list_sessions(limit=top_k * 2)

                # Apply date filters manually
                filtered_sessions = []
                for session in sessions:
                    created_at_str = session.get("created_at")
                    if not created_at_str:
                        continue
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    except ValueError:
                        continue

                    if after and created_at < after:
                        continue
                    if before and created_at > before:
                        continue
                    filtered_sessions.append(session)

                # Limit results
                filtered_sessions = filtered_sessions[:top_k]

                if not filtered_sessions:
                    yield "No sessions found."
                    return

                yield f"Found {len(filtered_sessions)} session(s):\n"
                for session in filtered_sessions:
                    session_id = session["session_id"]
                    created_at = session.get("created_at", "unknown")
                    messages = session.get("messages", [])
                    yield f"\n## Session: {session_id}\n"
                    yield f"Created: {created_at}\n"
                    yield f"Messages: {len(messages)}\n"

                    # Show first few messages
                    if messages:
                        yield "Preview:\n"
                        for msg in messages[:messages_per_session]:
                            role = msg.get("role", "unknown")
                            content = msg.get("content", "")[:100]
                            yield f"  [{role}]: {content}...\n"
                return

            # Semantic search mode
            if not self.embedder:
                yield "Error: Embedder not configured"
                return

            # Stage 1: Find relevant sessions via summary search
            query_embedding = await self.embedder.embed(query)
            logger.debug(f"Query embedded, dim={len(query_embedding)}")

            relevant_summaries = await self._find_relevant_sessions(
                query_embedding, top_k, after=after, before=before
            )
            logger.debug(f"Found {len(relevant_summaries)} summaries")
            for s in relevant_summaries:
                sid = s.get('session_id', '')
                sim = s.get('similarity', 0)
                logger.debug(f"  Summary: {sid[:8]}... sim={sim:.3f}")

            # If no summaries found, fall back to direct message search
            if not relevant_summaries:
                # Fallback: search messages directly across all sessions
                all_messages = await self.summarizer.store.search_all_session_messages(
                    query_embedding, top_k=top_k * 2, after=after, before=before
                )
                logger.debug(f"Fallback message search found {len(all_messages) if all_messages else 0} messages")

                if not all_messages:
                    yield "No relevant sessions or messages found."
                    return

                # Group messages by session_id
                sessions_by_id: dict[str, list[dict[str, Any]]] = {}
                for msg in all_messages:
                    if msg["similarity"] < self.min_similarity:
                        continue
                    sid = msg["session_id"]
                    if sid not in sessions_by_id:
                        sessions_by_id[sid] = []
                    sessions_by_id[sid].append(msg)

                if not sessions_by_id:
                    yield "No relevant messages found above similarity threshold."
                    return

                # Yield results grouped by session
                for session_id, messages in list(sessions_by_id.items())[:top_k]:
                    yield f"\n## Session: {session_id}\n"
                    yield "Found relevant messages (no summary available):\n"

                    for msg in messages[:messages_per_session]:
                        role = msg["role"]
                        content = msg["content_snippet"]
                        msg_sim = msg.get("similarity", 0)
                        yield f"  [{role}]: {content} ({msg_sim:.2f})\n"
                return

            # Filter summaries by similarity threshold
            filtered_summaries = [
                s for s in relevant_summaries
                if s.get("similarity", 0) >= self.min_similarity
            ]

            # If summaries found but all below threshold, fall back to message search
            if not filtered_summaries:
                all_messages = await self.summarizer.store.search_all_session_messages(
                    query_embedding, top_k=top_k * 2, after=after, before=before
                )

                if all_messages:
                    # Group messages by session_id
                    fallback_sessions: dict[str, list[dict[str, Any]]] = {}
                    for msg in all_messages:
                        if msg["similarity"] < self.min_similarity:
                            continue
                        sid = msg["session_id"]
                        if sid not in fallback_sessions:
                            fallback_sessions[sid] = []
                        fallback_sessions[sid].append(msg)

                    if fallback_sessions:
                        yield "\n(Found summaries but below threshold; showing message matches instead)\n"
                        for session_id, messages in list(fallback_sessions.items())[:top_k]:
                            yield f"\n## Session: {session_id}\n"
                            for msg in messages[:messages_per_session]:
                                role = msg["role"]
                                content = msg["content_snippet"]
                                msg_sim = msg.get("similarity", 0)
                                yield f"  [{role}]: {content} ({msg_sim:.2f})\n"
                        return

                yield "No relevant sessions found above similarity threshold."
                return

            # Stage 2: For each relevant session, search messages
            for summary in filtered_summaries:
                session_id = summary["session_id"]
                similarity = summary["similarity"]

                # Format session header; relevance is already normalized similarity
                yield f"\n## Session: {session_id}\n"
                yield f"Summary: {summary['summary_text']}\n"
                yield f"Relevance: {similarity:.2f}\n"

                # Search messages within session
                messages = await self.summarizer.store.search_session_messages(session_id, query_embedding, messages_per_session)

                if messages:
                    yield "Relevant messages:\n"
                    for msg in messages:
                        role = msg["role"]
                        content = msg["content_snippet"]
                        msg_sim = msg.get("similarity", 0)
                        # Message relevance is also normalized similarity.
                        yield f"  [{role}]: {content} ({msg_sim:.2f})\n"
                else:
                    yield "No specific messages found.\n"

        except Exception as e:
            yield f"Error searching sessions: {e}"
