"""Session persistence layer (PRD #53).

Handles file I/O for session storage:
    data/sessions/
    ├── current.json             # CLI current session_id
    └── {session_id}/
        ├── meta.json            # Session metadata
        ├── current.jsonl        # Recent messages
        └── archive.jsonl        # Older messages (post-compaction)
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import aiofiles

from src.embeddings import EmbeddingClient
from src.session import Message, Role, Session, SessionMeta


class SessionStorage:
    """Handles file I/O for session persistence."""

    def __init__(
        self,
        embedder: EmbeddingClient,
        data_dir: Path | None = None,
    ) -> None:
        self.embedder = embedder
        self.sessions_dir = (data_dir or Path("data")) / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_path = self.sessions_dir / "current.json"

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
        if not meta_path.exists():
            return None
        try:
            data = json.loads(meta_path.read_text())
            return SessionMeta(
                session_id=data["session_id"],
                created_at=datetime.fromisoformat(data["created_at"]),
                last_active=datetime.fromisoformat(data["last_active"]),
                status=data["status"],
                current_count=data.get("current_count", 0),
                archive_count=data.get("archive_count", 0),
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid meta.json for session {session_id}: {e}") from e

    def save_meta(self, meta: SessionMeta) -> None:
        """Save session metadata to meta.json."""
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
                },
                indent=2,
            )
        )

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
        from uuid import uuid4

        return f"sess_{uuid4().hex[:12]}"

    # === Messages ===

    def load_messages(self, session_id: str) -> list[Message]:
        """Load messages from current.jsonl."""
        messages_path = self.sessions_dir / session_id / "current.jsonl"
        if not messages_path.exists():
            return []

        messages = []
        with open(messages_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                messages.append(
                    Message(
                        idx=data["idx"],
                        role=Role(data["role"]),
                        content=data["content"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        embedding=data.get("embedding"),
                    )
                )
        return messages

    async def append_message(self, session_id: str, message: Message) -> None:
        """Append message to current.jsonl."""
        messages_path = self.sessions_dir / session_id / "current.jsonl"
        line = json.dumps(
            {
                "idx": message.idx,
                "role": message.role.value,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "embedding": message.embedding,
            }
        )
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
                line = json.dumps(
                    {
                        "idx": msg.idx,
                        "role": msg.role.value,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "embedding": msg.embedding,
                    }
                )
                await f.write(line + "\n")

    # === Full Session Load ===

    def load_session(self, session_id: str) -> Session | None:
        """Load full session (meta + messages)."""
        meta = self.get_meta(session_id)
        if meta is None:
            return None

        messages = self.load_messages(session_id)
        return Session(meta=meta, messages=messages)

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
