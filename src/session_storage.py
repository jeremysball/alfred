"""Session persistence layer (PRD #53).

Handles file I/O for session storage:
    $XDG_DATA_HOME/alfred/sessions/
    ├── current.json             # CLI current session_id
    └── {session_id}/
        ├── meta.json            # Session metadata
        ├── current.jsonl        # Recent messages
        ├── tokens.jsonl         # Token count deltas (append-only)
        └── archive.jsonl        # Older messages (post-compaction)

Token counts are stored as deltas in tokens.jsonl to avoid rewriting
the entire message file on every token update.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import aiofiles

from src import llm
from src.data_manager import get_data_dir
from src.embeddings.provider import EmbeddingProvider
from src.session import Message, Role, Session, SessionMeta, SessionSummary, ToolCallRecord

logger = logging.getLogger(__name__)


class SessionStorage:
    """Handles file I/O for session persistence."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        data_dir: Path | None = None,
    ) -> None:
        self.embedder = embedder
        self.sessions_dir = (data_dir or get_data_dir()) / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_path = self.sessions_dir / "current.json"
        # Session metadata cache
        self._session_cache: dict[str, SessionMeta] | None = None
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 5.0  # seconds

    # === Session Discovery ===

    def session_exists(self, session_id: str) -> bool:
        """Check if session folder exists."""
        return (self.sessions_dir / session_id).is_dir()

    def list_sessions(self) -> list[str]:
        """List all session IDs by scanning folders."""
        sessions = []
        for item in self.sessions_dir.iterdir():
            if item.is_dir() and item.name not in (".", ".."):
                sessions.append(item.name)
        return sorted(sessions, reverse=True)  # Most recent first

    def list_sessions_cached(self) -> list[SessionMeta]:
        """List all session metadata, using cache if fresh."""
        now = time.time()
        if self._session_cache is not None and (now - self._cache_timestamp) < self._cache_ttl:
            return sorted(self._session_cache.values(), key=lambda m: m.last_active, reverse=True)

        # Cache miss or expired - refresh
        sessions = self.list_sessions()
        cache = {}
        result = []

        for sid in sessions:
            meta = self.get_meta(sid)
            if meta:
                cache[sid] = meta
                result.append(meta)

        self._session_cache = cache
        self._cache_timestamp = now

        return sorted(result, key=lambda m: m.last_active, reverse=True)

    def invalidate_session_cache(self) -> None:
        """Clear the session metadata cache."""
        self._session_cache = None

    def get_meta_cached(self, session_id: str) -> SessionMeta | None:
        """Get session metadata, preferably from cache."""
        if self._session_cache is not None and session_id in self._session_cache:
            return self._session_cache[session_id]
        return self.get_meta(session_id)

    # === CLI Current Session ===

    def get_cli_current(self) -> str | None:
        """Get CLI current session_id from current.json."""
        if not self.current_path.exists():
            return None
        try:
            data: dict[str, str] = json.loads(self.current_path.read_text())
            return data.get("session_id")
        except (json.JSONDecodeError, KeyError):
            return None

    def set_cli_current(self, session_id: str) -> None:
        """Save CLI current session_id to current.json."""
        self.current_path.write_text(json.dumps({"session_id": session_id}))

    # === Session Metadata ===

    def get_meta(self, session_id: str) -> SessionMeta | None:
        """Load session metadata from meta.json."""
        meta_path = self.sessions_dir / session_id / "meta.json"
        logger.debug(f"get_meta called for session {session_id}: checking {meta_path}")

        if not meta_path.exists():
            logger.debug(f"No metadata found for session {session_id}")
            return None

        try:
            data = json.loads(meta_path.read_text())
            meta = SessionMeta(
                session_id=data["session_id"],
                created_at=datetime.fromisoformat(data["created_at"]),
                last_active=datetime.fromisoformat(data["last_active"]),
                status=data["status"],
                current_count=data.get("current_count", 0),
                archive_count=data.get("archive_count", 0),
                first_message_time=(
                    datetime.fromisoformat(data["first_message_time"])
                    if data.get("first_message_time")
                    else None
                ),
                last_summarized_count=data.get("last_summarized_count", 0),
                summary_version=data.get("summary_version", 0),
            )
            logger.debug(
                "Metadata loaded for session %s: status=%s, msgs=%s, last_summary_v=%s",
                session_id,
                meta.status,
                meta.message_count,
                meta.summary_version,
            )
            return meta
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse meta.json for session {session_id}: {e}")
            raise ValueError(f"Invalid meta.json for session {session_id}: {e}") from e

    def save_meta(self, meta: SessionMeta) -> None:
        """Save session metadata to meta.json."""
        logger.debug(
            "save_meta called for session %s: status=%s, msgs=%s",
            meta.session_id,
            meta.status,
            meta.message_count,
        )

        session_dir = self.sessions_dir / meta.session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        meta_path = session_dir / "meta.json"
        meta_path.write_text(
            json.dumps(
                {
                    "session_id": meta.session_id,
                    "created_at": meta.created_at.isoformat(),
                    "last_active": meta.last_active.isoformat(),
                    "status": meta.status,
                    "current_count": meta.current_count,
                    "archive_count": meta.archive_count,
                    "first_message_time": (
                        meta.first_message_time.isoformat()
                        if meta.first_message_time
                        else None
                    ),
                    "last_summarized_count": meta.last_summarized_count,
                    "summary_version": meta.summary_version,
                },
                indent=2,
            )
        )
        logger.debug(f"Metadata saved for session {meta.session_id}")

    # === Session Creation ===

    def create_session(self, session_id: str | None = None) -> SessionMeta:
        """Create a new session folder with metadata."""
        now = datetime.now(UTC)
        sid = session_id or self._generate_session_id()

        meta = SessionMeta(
            session_id=sid,
            created_at=now,
            last_active=now,
            status="active",
        )
        self.save_meta(meta)

        # Create empty current.jsonl
        session_dir = self.sessions_dir / sid
        (session_dir / "current.jsonl").touch()

        return meta

    def _generate_session_id(self) -> str:
        """Generate a new session ID (UUID without dashes, prefixed)."""
        return f"sess_{uuid4().hex[:12]}"

    # === Messages ===

    def _load_token_deltas(self, session_id: str) -> dict[int, dict[str, int]]:
        """Load token count deltas from tokens.jsonl.

        Returns a dict mapping message idx to token counts.
        Later entries override earlier ones for the same idx.
        """
        tokens_path = self.sessions_dir / session_id / "tokens.jsonl"
        if not tokens_path.exists():
            return {}

        deltas: dict[int, dict[str, int]] = {}
        with open(tokens_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                idx = data["idx"]
                # Merge deltas - later entries take precedence
                if idx not in deltas:
                    deltas[idx] = {}
                for key in ["input_tokens", "output_tokens", "cached_tokens", "reasoning_tokens"]:
                    if key in data:
                        deltas[idx][key] = data[key]
        return deltas

    def _load_tool_calls(self, data: dict) -> list[ToolCallRecord] | None:
        """Load tool calls from message data.

        Returns None if no tool_calls field (backward compatibility).
        """
        tool_calls_data = data.get("tool_calls")
        if not tool_calls_data:
            return None

        return [
            ToolCallRecord(
                tool_call_id=tc["tool_call_id"],
                tool_name=tc["tool_name"],
                arguments=tc["arguments"],
                output=tc["output"],
                status=tc["status"],
                insert_position=tc.get("insert_position", 0),
                sequence=tc.get("sequence", 0),
            )
            for tc in tool_calls_data
        ]

    def load_messages(self, session_id: str) -> list[Message]:
        """Load messages from current.jsonl and merge token deltas."""
        messages_path = self.sessions_dir / session_id / "current.jsonl"
        if not messages_path.exists():
            return []

        # Load token deltas from sidecar file
        token_deltas = self._load_token_deltas(session_id)

        messages = []
        with open(messages_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                idx = data["idx"]

                # Get token deltas for this message (if any)
                deltas = token_deltas.get(idx, {})

                # Load tool calls (handles backward compatibility)
                tool_calls = self._load_tool_calls(data)

                messages.append(
                    Message(
                        idx=idx,
                        role=Role(data["role"]),
                        content=data["content"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        embedding=data.get("embedding"),
                        input_tokens=deltas.get("input_tokens", data.get("input_tokens", 0)),
                        output_tokens=deltas.get("output_tokens", data.get("output_tokens", 0)),
                        cached_tokens=deltas.get("cached_tokens", data.get("cached_tokens", 0)),
                        reasoning_tokens=deltas.get(
                            "reasoning_tokens", data.get("reasoning_tokens", 0)
                        ),
                        tool_calls=tool_calls,
                    )
                )
        return messages

    def _serialize_tool_calls(self, tool_calls: list[ToolCallRecord] | None) -> list[dict] | None:
        """Serialize tool calls to JSON-compatible format.

        Returns None if tool_calls is None or empty.
        """
        if not tool_calls:
            return None

        return [
            {
                "tool_call_id": tc.tool_call_id,
                "tool_name": tc.tool_name,
                "arguments": tc.arguments,
                "output": tc.output,
                "status": tc.status,
                "insert_position": tc.insert_position,
                "sequence": tc.sequence,
            }
            for tc in tool_calls
        ]

    async def append_message(self, session_id: str, message: Message) -> None:
        """Append message to current.jsonl."""
        messages_path = self.sessions_dir / session_id / "current.jsonl"

        # Build message data
        data: dict = {
            "idx": message.idx,
            "role": message.role.value,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "embedding": message.embedding,
            "input_tokens": message.input_tokens,
            "output_tokens": message.output_tokens,
            "cached_tokens": message.cached_tokens,
            "reasoning_tokens": message.reasoning_tokens,
        }

        # Add tool_calls if present
        tool_calls_data = self._serialize_tool_calls(message.tool_calls)
        if tool_calls_data:
            data["tool_calls"] = tool_calls_data

        line = json.dumps(data)
        async with aiofiles.open(messages_path, "a") as f:
            await f.write(line + "\n")

    async def update_message_embedding(
        self, session_id: str, idx: int, embedding: list[float]
    ) -> None:
        """Update embedding for a specific message.

        Rewrites the message line with the new embedding.
        """
        messages_path = self.sessions_dir / session_id / "current.jsonl"

        # Read all messages
        messages = self.load_messages(session_id)

        # Update the specific message
        for msg in messages:
            if msg.idx == idx:
                msg.embedding = embedding
                break

        # Rewrite the file
        async with aiofiles.open(messages_path, "w") as f:
            for msg in messages:
                # Build message data
                data: dict = {
                    "idx": msg.idx,
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "embedding": msg.embedding,
                    "input_tokens": msg.input_tokens,
                    "output_tokens": msg.output_tokens,
                    "cached_tokens": msg.cached_tokens,
                    "reasoning_tokens": msg.reasoning_tokens,
                }

                # Add tool_calls if present
                tool_calls_data = self._serialize_tool_calls(msg.tool_calls)
                if tool_calls_data:
                    data["tool_calls"] = tool_calls_data

                line = json.dumps(data)
                await f.write(line + "\n")

    async def update_message_tokens(
        self,
        session_id: str,
        idx: int,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
        messages: list[Message] | None = None,
    ) -> None:
        """Update token counts for a specific message.

        Appends a delta entry to tokens.jsonl (append-only, no rewrite).
        This avoids race conditions with concurrent message appends.
        """
        tokens_path = self.sessions_dir / session_id / "tokens.jsonl"

        # Build delta entry with only non-zero values
        delta: dict[str, int | str] = {"idx": idx}
        if input_tokens:
            delta["input_tokens"] = input_tokens
        if output_tokens:
            delta["output_tokens"] = output_tokens
        if cached_tokens:
            delta["cached_tokens"] = cached_tokens
        if reasoning_tokens:
            delta["reasoning_tokens"] = reasoning_tokens

        # Append delta to sidecar file (no rewrite, no race condition)
        async with aiofiles.open(tokens_path, "a") as f:
            await f.write(json.dumps(delta) + "\n")

    # === Full Session Load ===

    def load_session(self, session_id: str) -> Session | None:
        """Load full session (meta + messages)."""
        meta = self.get_meta(session_id)
        if meta is None:
            return None

        messages = self.load_messages(session_id)
        return Session(meta=meta, messages=messages)

    # === Summary Storage (PRD #76) ===

    async def store_summary(self, summary: SessionSummary) -> None:
        """Store summary to {session_id}/summary.json.

        Overwrites existing summary and auto-increments version if
        a previous summary exists.

        Args:
            summary: SessionSummary to persist (version will be updated)
        """
        logger.debug(
            "store_summary called for session %s: id=%s, msg_count=%s",
            summary.session_id,
            summary.id,
            summary.message_count,
        )

        # Check for existing summary to increment version
        try:
            existing = await self.get_summary(summary.session_id)
            if existing is not None:
                summary.version = existing.version + 1
                logger.debug(
                    "Found existing summary v%s, incrementing to v%s",
                    existing.version,
                    summary.version,
                )
            else:
                logger.debug("No existing summary found, using version %s", summary.version)
        except ValueError as e:
            logger.warning(f"Error reading existing summary for version check: {e}")
            # Corrupt file - start fresh with caller's version

        session_dir = self.sessions_dir / summary.session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        summary_path = session_dir / "summary.json"
        logger.debug(f"Writing summary to {summary_path}")

        # Serialize to JSON
        data = summary.to_dict()
        content = json.dumps(data, indent=2)

        # Atomic write: temp file + rename
        temp_path = summary_path.with_suffix(".tmp")
        async with aiofiles.open(temp_path, "w") as f:
            await f.write(content)
        temp_path.rename(summary_path)
        logger.debug(
            "Summary stored successfully: v%s, %s bytes",
            summary.version,
            len(content),
        )

    async def get_summary(self, session_id: str) -> SessionSummary | None:
        """Load summary from {session_id}/summary.json.

        Args:
            session_id: Session ID to load summary for

        Returns:
            SessionSummary if exists, None otherwise

        Raises:
            ValueError: If summary.json is corrupted
        """
        summary_path = self.sessions_dir / session_id / "summary.json"
        logger.debug(
            "get_summary called for session %s: checking %s",
            session_id,
            summary_path,
        )

        if not summary_path.exists():
            logger.debug(f"No summary found for session {session_id}")
            return None

        try:
            async with aiofiles.open(summary_path) as f:
                content = await f.read()
            data = json.loads(content)
            summary = SessionSummary.from_dict(data)
            logger.debug(
                "Summary loaded successfully: id=%s, v%s, msg_count=%s",
                summary.id,
                summary.version,
                summary.message_count,
            )
            return summary
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse summary.json for session {session_id}: {e}")
            raise ValueError(f"Invalid summary.json for session {session_id}: {e}") from e

    # === Async Embedding Task ===

    async def embed_and_update(self, session_id: str, idx: int, content: str) -> None:
        """Generate embedding and update message (fire-and-forget task)."""
        try:
            embedding = await self.embedder.embed(content)
            await self.update_message_embedding(session_id, idx, embedding)
        except Exception:
            # Log but don't raise - this is a background task
            # TODO: Add proper logging
            pass

    def spawn_embed_task(self, session_id: str, idx: int, content: str) -> None:
        """Spawn background task to embed message."""
        asyncio.create_task(self.embed_and_update(session_id, idx, content))


async def generate_session_summary(
    session_id: str,
    storage: SessionStorage,
    embedder: EmbeddingProvider,
) -> SessionSummary:
    """Generate and store summary for a session.

    Orchestrates the full pipeline: fetch messages → summarize → embed → store.

    Args:
        session_id: Session ID to summarize
        storage: SessionStorage instance for loading/storing
        embedder: Embedding provider for creating summary embedding

    Returns:
        SessionSummary with embedding created and stored

    Raises:
        Exception: If any step fails (messages fail to load, LLM fails, etc.)
    """
    logger.debug(f"generate_session_summary called for session {session_id}")

    # 1. Load messages
    messages = storage.load_messages(session_id)
    logger.debug(f"Loaded {len(messages)} messages for session {session_id}")

    # 2. Check for existing summary to reuse ID
    existing = await storage.get_summary(session_id)
    if existing:
        summary_id = existing.id
        logger.debug(f"Found existing summary {summary_id}, will reuse ID")
    else:
        summary_id = f"sum_{uuid4().hex[:12]}"
        logger.debug(f"No existing summary, creating new ID: {summary_id}")

    # 3. Generate summary text via LLM
    summary_text = await llm.summarize_conversation(messages)
    logger.debug(f"Generated summary text: {len(summary_text)} chars")

    # 4. Create embedding
    embedding = await embedder.embed(summary_text)
    logger.debug(f"Created embedding: {len(embedding)} dimensions")

    # 5. Create SessionSummary
    summary = SessionSummary(
        id=summary_id,
        session_id=session_id,
        timestamp=datetime.now(UTC),
        message_range=(0, len(messages)),
        message_count=len(messages),
        summary_text=summary_text,
        embedding=embedding,
        version=1,  # store_summary will auto-increment if existing
    )
    logger.debug(f"Created SessionSummary: {summary.id}, msgs {summary.message_range}")

    # 6. Store summary
    await storage.store_summary(summary)
    logger.debug(f"Stored summary for session {session_id}")

    return summary
