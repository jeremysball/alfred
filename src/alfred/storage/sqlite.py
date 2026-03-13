"""Unified SQLite storage with sqlite-vec for vector search.

Replaces CASStore, JSONLMemoryStore, FAISSMemoryStore, SessionStorage, and CronStore
with a single ACID-compliant SQLite solution.
"""

import contextlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

# sqlite-vec is required for vector search
try:
    import sqlite_vec  # noqa: F401
except ImportError as e:
    raise ImportError(
        "sqlite-vec is required. Install with: uv add sqlite-vec"
    ) from e

logger = logging.getLogger(__name__)


class SQLiteStore:
    """Unified SQLite storage for sessions, cron jobs, and memories.

    Uses sqlite-vec for vector similarity search on memories.
    All operations are ACID-compliant via SQLite transactions.
    """

    def __init__(self, db_path: Path | str) -> None:
        """Initialize SQLite store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    async def _load_extensions(self, db) -> None:
        """Load sqlite-vec extension for vector search.

        Must be called on every new connection before using vec0 virtual tables.
        """
        await db.enable_load_extension(True)
        import sqlite_vec
        await db.load_extension(sqlite_vec.loadable_path())

    async def _init(self) -> None:
        """Lazy initialization of database connection and tables."""
        if self._initialized:
            return

        try:
            import aiosqlite
        except ImportError as e:
            raise ImportError("aiosqlite required. Install with: uv add aiosqlite") from e

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension
            await self._load_extensions(db)

            # Enable WAL mode for better concurrency
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA foreign_keys=ON")

            # Create tables
            await self._create_sessions_table(db)
            await self._create_session_summaries_table(db)
            await self._create_message_embeddings_table(db)
            await self._create_cron_tables(db)
            await self._create_memories_table(db)

            await db.commit()

        self._initialized = True
        logger.info(f"SQLite store initialized: {self.db_path}")

    async def _create_sessions_table(self, db: Any) -> None:
        """Create sessions table."""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                messages JSON NOT NULL DEFAULT '[]',
                message_count INTEGER DEFAULT 0,
                metadata JSON DEFAULT '{}'
            )
        """)

        # Index for session lookups
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_updated
            ON sessions(updated_at)
        """)

    async def _create_session_summaries_table(self, db: Any) -> None:
        """Create session_summaries table with FK to sessions."""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS session_summaries (
                summary_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER NOT NULL,
                first_message_idx INTEGER NOT NULL,
                last_message_idx INTEGER NOT NULL,
                summary_text TEXT NOT NULL,
                embedding JSON,
                version INTEGER DEFAULT 1,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)

        # Indexes
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_summaries_session
            ON session_summaries(session_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_summaries_created
            ON session_summaries(created_at)
        """)

    async def _create_message_embeddings_table(self, db: Any) -> None:
        """Create message_embeddings table with FK to sessions."""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_embeddings (
                message_embedding_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                message_idx INTEGER NOT NULL,
                role TEXT NOT NULL,
                content_snippet TEXT,
                embedding JSON NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)

        # Index for session-based lookups
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_message_embeddings_session
            ON message_embeddings(session_id)
        """)

        # Create sqlite-vec virtual table for message embeddings
        await db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS message_embeddings_vec USING vec0(
                message_embedding_id TEXT PRIMARY KEY,
                embedding FLOAT[768]
            )
        """)

    async def _create_cron_tables(self, db: Any) -> None:
        """Create cron jobs and history tables."""
        # Jobs table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cron_jobs (
                job_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                schedule TEXT NOT NULL,
                command TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_run_at TIMESTAMP,
                next_run_at TIMESTAMP,
                metadata JSON DEFAULT '{}'
            )
        """)

        # Execution history table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cron_history (
                execution_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT NOT NULL,
                output TEXT,
                error TEXT,
                FOREIGN KEY (job_id) REFERENCES cron_jobs(job_id) ON DELETE CASCADE
            )
        """)

        # Indexes
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_cron_jobs_next_run
            ON cron_jobs(next_run_at) WHERE enabled = 1
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_cron_history_job
            ON cron_history(job_id, started_at DESC)
        """)

    async def _create_memories_table(self, db: Any) -> None:
        """Create memories table with vector support via sqlite-vec."""
        # Use sqlite-vec virtual table for embeddings
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                entry_id TEXT PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tags JSON DEFAULT '[]',
                permanent BOOLEAN DEFAULT 0
            )
        """)

        # Virtual table for vector search
        await db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_embeddings USING vec0(
                entry_id TEXT PRIMARY KEY,
                embedding FLOAT[768]  -- Adjustable dimension
            )
        """)

        # Index for timestamp queries
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_timestamp
            ON memories(timestamp)
        """)

        # Index for permanent flag
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_permanent
            ON memories(permanent) WHERE permanent = 0
        """)

    # === Session Operations ===

    async def save_session(
        self, session_id: str, messages: list[dict], metadata: dict | None = None
    ) -> None:
        """Save or update a session.

        Args:
            session_id: Unique session identifier
            messages: List of message dicts
            metadata: Optional session metadata
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            await db.execute(
                """
                INSERT INTO sessions (session_id, messages, metadata, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    messages = excluded.messages,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session_id, json.dumps(messages), json.dumps(metadata or {})),
            )
            await db.commit()

            # Index message embeddings for vector search (new sessions only)
            await self._index_message_embeddings(db, session_id, messages)

    async def _index_message_embeddings(
        self, db: Any, session_id: str, messages: list[dict]
    ) -> None:
        """Index message embeddings for vector search using sqlite-vec.

        Only indexes messages with embeddings. Skips if already indexed.
        """
        for msg in messages:
            embedding = msg.get("embedding")
            if not embedding:
                continue  # Skip messages without embeddings

            message_idx = msg.get("idx", 0)
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]  # Snippet

            # Generate unique ID
            me_id = f"{session_id}_{message_idx}"

            try:
                # Insert into message_embeddings
                await db.execute(
                    """
                    INSERT INTO message_embeddings (
                        message_embedding_id, session_id, message_idx,
                        role, content_snippet, embedding
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(message_embedding_id) DO NOTHING
                    """,
                    (me_id, session_id, message_idx, role, content, json.dumps(embedding)),
                )

                # Insert into sqlite-vec virtual table
                await db.execute(
                    """
                    INSERT INTO message_embeddings_vec (message_embedding_id, embedding)
                    VALUES (?, ?)
                    ON CONFLICT(message_embedding_id) DO NOTHING
                    """,
                    (me_id, json.dumps(embedding)),
                )

            except Exception as e:
                logger.warning(
                    f"Failed to index message {message_idx} for session {session_id}: {e}"
                )

        await db.commit()

    async def load_session(self, session_id: str) -> dict | None:
        """Load a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session dict or None if not found
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()

                if row is None:
                    return None

                return {
                    "session_id": row["session_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "messages": json.loads(row["messages"]),
                    "metadata": json.loads(row["metadata"]),
                }

    async def list_sessions(self, limit: int = 100) -> list[dict]:
        """List recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session dicts
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "session_id": row["session_id"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "messages": json.loads(row["messages"]),
                        "metadata": json.loads(row["metadata"]),
                    }
                    for row in rows
                ]

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session to delete

        Returns:
            True if deleted, False if not found
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            cursor = await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            await db.commit()
            return cursor.rowcount > 0

    # === Cron Operations ===

    async def save_job(self, job: dict) -> None:
        """Save or update a cron job.

        Args:
            job: Job dict with job_id, name, schedule, command, etc.
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            await db.execute(
                """
                INSERT INTO cron_jobs (
                    job_id, name, schedule, command, enabled,
                    last_run_at, next_run_at, metadata, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(job_id) DO UPDATE SET
                    name = excluded.name,
                    schedule = excluded.schedule,
                    command = excluded.command,
                    enabled = excluded.enabled,
                    last_run_at = excluded.last_run_at,
                    next_run_at = excluded.next_run_at,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    job["job_id"],
                    job["name"],
                    job["schedule"],
                    job["command"],
                    job.get("enabled", True),
                    job.get("last_run_at"),
                    job.get("next_run_at"),
                    json.dumps(job.get("metadata", {})),
                ),
            )
            await db.commit()

    async def load_jobs(self) -> list[dict]:
        """Load all cron jobs.

        Returns:
            List of job dicts
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM cron_jobs") as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "job_id": row["job_id"],
                        "name": row["name"],
                        "schedule": row["schedule"],
                        "command": row["command"],
                        "enabled": bool(row["enabled"]),
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "last_run_at": row["last_run_at"],
                        "next_run_at": row["next_run_at"],
                        "metadata": json.loads(row["metadata"]),
                    }
                    for row in rows
                ]

    async def delete_job(self, job_id: str) -> bool:
        """Delete a cron job.

        Args:
            job_id: Job to delete

        Returns:
            True if deleted, False if not found
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            cursor = await db.execute("DELETE FROM cron_jobs WHERE job_id = ?", (job_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def record_execution(self, record: dict) -> None:
        """Record a job execution.

        Args:
            record: Execution record dict
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            await db.execute(
                """
                INSERT INTO cron_history (
                    execution_id, job_id, started_at, completed_at,
                    status, output, error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["execution_id"],
                    record["job_id"],
                    record.get("started_at"),
                    record.get("completed_at"),
                    record["status"],
                    record.get("output"),
                    record.get("error"),
                ),
            )
            await db.commit()

    async def get_job_history(self, job_id: str, limit: int | None = None) -> list[dict]:
        """Get execution history for a job.

        Args:
            job_id: Job ID to query
            limit: Maximum records to return

        Returns:
            List of execution records
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            db.row_factory = aiosqlite.Row

            if limit:
                async with db.execute(
                    """
                    SELECT * FROM cron_history
                    WHERE job_id = ?
                    ORDER BY started_at DESC
                    LIMIT ?
                    """,
                    (job_id, limit),
                ) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute(
                    """
                    SELECT * FROM cron_history
                    WHERE job_id = ?
                    ORDER BY started_at DESC
                    """,
                    (job_id,),
                ) as cursor:
                    rows = await cursor.fetchall()

            return [
                {
                    "execution_id": row["execution_id"],
                    "job_id": row["job_id"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "status": row["status"],
                    "output": row["output"],
                    "error": row["error"],
                }
                for row in rows
            ]

    # === Memory Operations ===

    async def add_memory(
        self,
        entry_id: str,
        role: str,
        content: str,
        embedding: list[float] | None = None,
        tags: list[str] | None = None,
        permanent: bool = False,
        timestamp: datetime | None = None,
    ) -> None:
        """Add a memory entry.

        Args:
            entry_id: Unique memory ID
            role: "user", "assistant", or "system"
            content: Memory content
            embedding: Optional vector embedding
            tags: Optional list of tags
            permanent: If True, never expire
            timestamp: Optional timestamp (default: now)
        """
        await self._init()

        import aiosqlite

        ts = timestamp or datetime.now()

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            # Insert memory record
            await db.execute(
                """
                INSERT INTO memories (entry_id, timestamp, role, content, tags, permanent)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(entry_id) DO UPDATE SET
                    role = excluded.role,
                    content = excluded.content,
                    tags = excluded.tags,
                    permanent = excluded.permanent
                """,
                (entry_id, ts, role, content, json.dumps(tags or []), permanent),
            )

            # Insert embedding if provided and sqlite-vec available
            if embedding:
                try:
                    await db.execute(
                        """
                        INSERT INTO memory_embeddings (entry_id, embedding)
                        VALUES (?, ?)
                        ON CONFLICT(entry_id) DO UPDATE SET
                            embedding = excluded.embedding
                        """,
                        (entry_id, json.dumps(embedding)),
                    )
                except Exception:
                    # sqlite-vec not available, store in main table
                    await db.execute(
                        """
                        UPDATE memories SET embedding = ? WHERE entry_id = ?
                        """,
                        (json.dumps(embedding), entry_id),
                    )

            await db.commit()

    async def search_memories(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        role: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict]:
        """Search memories by vector similarity using sqlite-vec.

        Args:
            query_embedding: Query vector
            top_k: Number of results
            role: Optional role filter
            tags: Optional tags filter

        Returns:
            List of memory dicts with similarity scores
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            db.row_factory = aiosqlite.Row

            # Use sqlite-vec for vector search
            query = """
                SELECT m.*, e.distance
                FROM memory_embeddings e
                JOIN memories m ON e.entry_id = m.entry_id
                WHERE e.embedding MATCH ?
            """
            params: list[Any] = [json.dumps(query_embedding)]

            if role:
                query += " AND m.role = ?"
                params.append(role)

            if tags:
                # Simple tag filtering - check if any tag matches
                for tag in tags:
                    query += " AND json_extract(m.tags, '$') LIKE ?"
                    params.append(f'%"{tag}"%')

            query += " ORDER BY e.distance LIMIT ?"
            params.append(top_k)

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

            result = []
            for row in rows:
                entry = {
                    "entry_id": row["entry_id"],
                    "timestamp": row["timestamp"],
                    "role": row["role"],
                    "content": row["content"],
                    "tags": json.loads(row["tags"]),
                    "permanent": bool(row["permanent"]),
                    "similarity": row["distance"],
                }
                result.append(entry)
            return result

    async def get_memory(self, entry_id: str) -> dict | None:
        """Get a memory by ID.

        Args:
            entry_id: Memory ID

        Returns:
            Memory dict or None
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM memories WHERE entry_id = ?", (entry_id,)
            ) as cursor:
                row = await cursor.fetchone()

                if row is None:
                    return None

                return {
                    "entry_id": row["entry_id"],
                    "timestamp": row["timestamp"],
                    "role": row["role"],
                    "content": row["content"],
                    "tags": json.loads(row["tags"]),
                    "permanent": bool(row["permanent"]),
                }

    async def get_all_memories(
        self,
        role: str | None = None,
        tags: list[str] | None = None,
        permanent_only: bool = False,
    ) -> list[dict]:
        """Get all memories with optional filtering.

        Args:
            role: Optional role filter
            tags: Optional tags filter
            permanent_only: If True, only return permanent memories

        Returns:
            List of memory dicts
        """
        await self._init()

        import aiosqlite

        query = "SELECT * FROM memories WHERE 1=1"
        params: list[Any] = []

        if role:
            query += " AND role = ?"
            params.append(role)

        if permanent_only:
            query += " AND permanent = 1"

        if tags:
            for tag in tags:
                query += " AND json_extract(tags, '$') LIKE ?"
                params.append(f'%"{tag}"%')

        query += " ORDER BY timestamp DESC"

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "entry_id": row["entry_id"],
                        "timestamp": row["timestamp"],
                        "role": row["role"],
                        "content": row["content"],
                        "tags": json.loads(row["tags"]),
                        "permanent": bool(row["permanent"]),
                    }
                    for row in rows
                ]

    async def delete_memory(self, entry_id: str) -> bool:
        """Delete a memory by ID.

        Args:
            entry_id: Memory to delete

        Returns:
            True if deleted, False if not found
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            # Delete from embeddings first (if exists)
            with contextlib.suppress(Exception):
                await db.execute("DELETE FROM memory_embeddings WHERE entry_id = ?", (entry_id,))

            # Delete from memories
            cursor = await db.execute("DELETE FROM memories WHERE entry_id = ?", (entry_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def prune_memories(
        self,
        ttl_days: int = 90,
        dry_run: bool = False,
    ) -> int:
        """Remove non-permanent memories older than TTL.

        Args:
            ttl_days: Age threshold in days
            dry_run: If True, return count without deleting

        Returns:
            Number of memories pruned (or would be pruned)
        """
        await self._init()

        from datetime import timedelta

        import aiosqlite

        cutoff = datetime.now() - timedelta(days=ttl_days)

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            # Count matching records
            async with db.execute(
                """
                SELECT COUNT(*) FROM memories
                WHERE permanent = 0 AND timestamp < ?
                """,
                (cutoff,),
            ) as cursor:
                row = await cursor.fetchone()
                count = row[0] if row else 0

            if not dry_run and count > 0:
                # Get IDs to delete
                async with db.execute(
                    """
                    SELECT entry_id FROM memories
                    WHERE permanent = 0 AND timestamp < ?
                    """,
                    (cutoff,),
                ) as cursor:
                    ids = [r[0] for r in await cursor.fetchall()]

                # Delete from embeddings
                for entry_id in ids:
                    with contextlib.suppress(Exception):
                        await db.execute(
                            "DELETE FROM memory_embeddings WHERE entry_id = ?", (entry_id,)
                        )

                # Delete from memories
                await db.execute(
                    """
                    DELETE FROM memories
                    WHERE permanent = 0 AND timestamp < ?
                    """,
                    (cutoff,),
                )
                await db.commit()

            return count

    async def update_memory(
        self,
        entry_id: str,
        content: str | None = None,
        embedding: list[float] | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        """Update a memory entry.

        Args:
            entry_id: Memory to update
            content: New content (None = no change)
            embedding: New embedding (None = no change)
            tags: New tags (None = no change)

        Returns:
            True if updated, False if not found
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            # Check if exists
            async with db.execute(
                "SELECT 1 FROM memories WHERE entry_id = ?", (entry_id,)
            ) as cursor:
                if await cursor.fetchone() is None:
                    return False

            # Update content/tags
            if content is not None or tags is not None:
                updates = []
                params: list[Any] = []

                if content is not None:
                    updates.append("content = ?")
                    params.append(content)

                if tags is not None:
                    updates.append("tags = ?")
                    params.append(json.dumps(tags))

                params.append(entry_id)

                await db.execute(
                    f"UPDATE memories SET {', '.join(updates)} WHERE entry_id = ?", params
                )

            # Update embedding
            if embedding:
                try:
                    await db.execute(
                        """
                        INSERT INTO memory_embeddings (entry_id, embedding)
                        VALUES (?, ?)
                        ON CONFLICT(entry_id) DO UPDATE SET
                            embedding = excluded.embedding
                        """,
                        (entry_id, json.dumps(embedding)),
                    )
                except Exception:
                    # sqlite-vec not available
                    await db.execute(
                        "UPDATE memories SET embedding = ? WHERE entry_id = ?",
                        (json.dumps(embedding), entry_id),
                    )

            await db.commit()
            return True

    # Session Summary methods (PRD #76)
    async def save_summary(self, summary: dict) -> None:
        """Save or update a session summary.

        Args:
            summary: Summary dict with summary_id, session_id, message_count,
                     first_message_idx, last_message_idx, summary_text,
                     embedding (optional), version (optional)
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            # Serialize embedding to JSON if present
            embedding = summary.get("embedding")
            embedding_json = json.dumps(embedding) if embedding is not None else None

            await db.execute(
                """
                INSERT INTO session_summaries (
                    summary_id, session_id, message_count,
                    first_message_idx, last_message_idx, summary_text,
                    embedding, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary["summary_id"],
                    summary["session_id"],
                    summary["message_count"],
                    summary["first_message_idx"],
                    summary["last_message_idx"],
                    summary["summary_text"],
                    embedding_json,
                    summary.get("version", 1),
                ),
            )
            await db.commit()

    async def get_latest_summary(self, session_id: str) -> dict | None:
        """Get the latest summary for a session.

        Args:
            session_id: Session ID to query

        Returns:
            Summary dict or None if not found
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            db.row_factory = aiosqlite.Row

            async with db.execute(
                """
                SELECT * FROM session_summaries
                WHERE session_id = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                (session_id,),
            ) as cursor:
                row = await cursor.fetchone()

                if row is None:
                    return None

                result = dict(row)

                # Deserialize embedding from JSON
                if result.get("embedding"):
                    result["embedding"] = json.loads(result["embedding"])

                return result

    async def find_sessions_needing_summary(self, threshold: int = 20) -> list[str]:
        """Find sessions with threshold+ new messages since last summary.

        Args:
            threshold: Minimum number of new messages to trigger summary

        Returns:
            List of session_ids needing summary
        """
        await self._init()

        import aiosqlite

        async with (
            aiosqlite.connect(self.db_path) as db,
            db.execute(
                """
                SELECT s.session_id
                FROM sessions s
                LEFT JOIN session_summaries sm ON s.session_id = sm.session_id
                WHERE s.message_count - COALESCE(sm.message_count, 0) >= ?
                """,
                (threshold,),
            ) as cursor,
        ):
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    # Two-stage search methods (PRD #76 Phase 4)
    async def search_summaries(
        self,
        query_embedding: list[float],
        top_k: int = 3,
    ) -> list[dict]:
        """Search session summaries by vector similarity.

        Uses sqlite-vec for efficient vector similarity search.

        Args:
            query_embedding: Query vector
            top_k: Maximum results to return

        Returns:
            List of {summary_id, session_id, summary_text, similarity}

        Raises:
            RuntimeError: If sqlite-vec not available
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            # Check if sqlite-vec is available
            try:
                await db.execute("SELECT vec_version()")
            except Exception as e:
                raise RuntimeError("sqlite-vec required for summary search") from e

            # Use sqlite-vec for vector similarity search
            results = []
            try:
                async with db.execute(
                    """
                    SELECT
                        s.summary_id,
                        s.session_id,
                        s.summary_text,
                        v.distance as similarity
                    FROM session_summaries_vec v
                    JOIN session_summaries s ON v.summary_id = s.summary_id
                    WHERE v.embedding MATCH ?
                    ORDER BY v.distance
                    LIMIT ?
                    """,
                    (json.dumps(query_embedding), top_k),
                ) as cursor:
                    async for row in cursor:
                        results.append(
                            {
                                "summary_id": row[0],
                                "session_id": row[1],
                                "summary_text": row[2],
                                "similarity": row[3],
                            }
                        )
            except Exception as e:
                logger.error(f"Error searching summaries: {e}")
                raise RuntimeError("Failed to search summaries") from e

            return results

    async def search_session_messages(
        self,
        session_id: str,
        query_embedding: list[float],
        top_k: int = 3,
    ) -> list[dict]:
        """Search messages within a session by vector similarity.

        Uses sqlite-vec for efficient vector similarity search.

        Args:
            session_id: Session to search within
            query_embedding: Query vector
            top_k: Maximum results to return

        Returns:
            List of {message_idx, role, content_snippet, similarity}

        Raises:
            RuntimeError: If sqlite-vec not available
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Load sqlite-vec extension for vector search
            await self._load_extensions(db)
            # Check if sqlite-vec is available
            try:
                await db.execute("SELECT vec_version()")
            except Exception as e:
                raise RuntimeError("sqlite-vec required for message search") from e

            # Use sqlite-vec for vector similarity search
            results = []
            try:
                async with db.execute(
                    """
                    SELECT
                        m.message_idx,
                        m.role,
                        m.content_snippet,
                        v.distance as similarity
                    FROM message_embeddings_vec v
                    JOIN message_embeddings m ON v.message_embedding_id = m.message_embedding_id
                    WHERE v.embedding MATCH ?
                        AND m.session_id = ?
                    ORDER BY v.distance
                    LIMIT ?
                    """,
                    (json.dumps(query_embedding), session_id, top_k),
                ) as cursor:
                    async for row in cursor:
                        results.append(
                            {
                                "message_idx": row[0],
                                "role": row[1],
                                "content_snippet": row[2],
                                "similarity": row[3],
                            }
                        )
            except Exception as e:
                logger.error(f"Error searching messages for session {session_id}: {e}")
                raise RuntimeError("Failed to search messages") from e

            return results
