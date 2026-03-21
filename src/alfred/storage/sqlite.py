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
    import sqlite_vec  # type: ignore[import-untyped]  # noqa: F401
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

    def __init__(
        self,
        db_path: Path | str,
        embedding_dim: int = 768,
        embedder: Any | None = None
    ) -> None:
        """Initialize SQLite store.

        Args:
            db_path: Path to SQLite database file
            embedding_dim: Dimension of embeddings (768 for BGE, 1536 for OpenAI)
            embedder: Optional embedder for automatic re-embedding on dimension change
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._embedding_dim = embedding_dim
        self._embedder = embedder
        self._initialized = False

    async def _load_extensions(self, db: Any) -> None:
        """Load sqlite-vec extension for vector search.

        Must be called on every new connection before using vec0 virtual tables.
        """
        await db.enable_load_extension(True)
        import sqlite_vec
        await db.load_extension(sqlite_vec.loadable_path())

    @staticmethod
    def _distance_to_similarity(distance: float) -> float:
        """Convert backend distance into Alfred-facing similarity."""
        return 1.0 - distance

    async def _get_vec0_dimension(self, db: Any, table_name: str) -> int | None:
        """Extract embedding dimension from existing vec0 table schema.

        Queries sqlite_master to find the table's CREATE statement and
        extracts the FLOAT[N] dimension using regex.

        Args:
            db: Database connection
            table_name: Name of the vec0 table

        Returns:
            Dimension as int (e.g., 768, 1536) or None if table doesn't exist
        """
        import re

        async with db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or not row[0]:
                return None

            schema = row[0]
            # Extract FLOAT[N] dimension from schema like:
            # CREATE VIRTUAL TABLE x USING vec0(..., embedding FLOAT[768])
            match = re.search(r'FLOAT\[(\d+)\]', schema)
            if match:
                return int(match.group(1))

            return None

    async def _check_dimension_mismatch(self, db: Any, table_name: str) -> tuple[int, int] | None:
        """Check if vec0 table dimension differs from expected dimension.

        Args:
            db: Database connection
            table_name: Name of the vec0 table

        Returns:
            Tuple of (old_dim, new_dim) if mismatch detected, None otherwise
        """
        actual_dim = await self._get_vec0_dimension(db, table_name)

        # If table doesn't exist, no mismatch (will be created with correct dimension)
        if actual_dim is None:
            return None

        # If dimensions match, no mismatch
        if actual_dim == self._embedding_dim:
            return None

        # Mismatch detected
        return (actual_dim, self._embedding_dim)

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

        # Virtual table for vector search on summaries
        await self._ensure_vec0_dimension(db, "session_summaries_vec", "summary_id")

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

        # Check if vec0 table exists with different dimension
        await self._ensure_vec0_dimension(db, "message_embeddings_vec", "message_embedding_id")

    async def _ensure_vec0_dimension(self, db: Any, table_name: str, id_column: str) -> None:
        """Ensure vec0 table exists with correct dimension.

        Drops and recreates the table if dimension mismatch is detected.
        """
        import re

        dim = self._embedding_dim

        # Check if table exists
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ) as cursor:
            row = await cursor.fetchone()
            table_exists = row is not None

        if table_exists:
            # Get the table schema to check dimension
            async with db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    schema = row[0]
                    # Extract dimension from FLOAT[N]
                    match = re.search(r'FLOAT\[(\d+)\]', schema)
                    if match:
                        existing_dim = int(match.group(1))
                        if existing_dim != dim:
                            if self._embedder is not None:
                                # Use reembedder to preserve data
                                logger.warning(
                                    f"Embedding dimension changed: {table_name} has {existing_dim}, "
                                    f"expected {dim}. Starting automatic re-embedding..."
                                )
                                reembedder = EmbeddingReembedder(self, self._embedder)
                                await reembedder.reembed_all(existing_dim, dim)
                                # Table was recreated by reembedder
                                return
                            else:
                                # No embedder available, just drop and warn
                                logger.warning(
                                    f"Embedding dimension mismatch: {table_name} has {existing_dim}, "
                                    f"expected {dim}. Dropping and recreating (vec0 data will be lost)."
                                )
                                await db.execute(f"DROP TABLE {table_name}")
                                table_exists = False

        # Create table with correct dimension
        if not table_exists:
            await db.execute(f"""
                CREATE VIRTUAL TABLE {table_name} USING vec0(
                    {id_column} TEXT PRIMARY KEY,
                    embedding FLOAT[{dim}]
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

        # Virtual table for vector search - dimension handled dynamically
        await self._ensure_vec0_dimension(db, "memory_embeddings", "entry_id")

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
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
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
        self, db: Any, session_id: str, messages: list[dict[str, Any]]
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

    async def load_session(self, session_id: str) -> dict[str, Any] | None:
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

    async def list_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
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

    async def save_job(self, job: dict[str, Any]) -> None:
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

    async def load_jobs(self) -> list[dict[str, Any]]:
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

    async def record_execution(self, record: dict[str, Any]) -> None:
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

    async def get_job_history(self, job_id: str, limit: int | None = None) -> list[dict[str, Any]]:
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
    ) -> list[dict[str, Any]]:
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
            # Note: sqlite-vec requires k constraint for KNN queries
            query = """
                SELECT m.*, e.distance
                FROM memory_embeddings e
                JOIN memories m ON e.entry_id = m.entry_id
                WHERE e.embedding MATCH ? AND k = ?
            """
            params: list[Any] = [json.dumps(query_embedding), top_k]

            if role:
                query += " AND m.role = ?"
                params.append(role)

            if tags:
                # Simple tag filtering - check if any tag matches
                for tag in tags:
                    query += " AND json_extract(m.tags, '$') LIKE ?"
                    params.append(f'%"{tag}"%')

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
                    "similarity": self._distance_to_similarity(float(row["distance"])),
                }
                result.append(entry)
            return result

    async def get_memory(self, entry_id: str) -> dict[str, Any] | None:
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
    ) -> list[dict[str, Any]]:
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
    async def save_summary(self, summary: dict[str, Any]) -> None:
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

    async def get_latest_summary(self, session_id: str) -> dict[str, Any] | None:
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
    ) -> list[dict[str, Any]]:
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
            # Note: sqlite-vec requires k constraint for KNN queries
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
                    WHERE v.embedding MATCH ? AND k = ?
                    ORDER BY v.distance
                    """,
                    (json.dumps(query_embedding), top_k),
                ) as cursor:
                    async for row in cursor:
                        results.append(
                            {
                                "summary_id": row[0],
                                "session_id": row[1],
                                "summary_text": row[2],
                                "similarity": self._distance_to_similarity(float(row[3])),
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
    ) -> list[dict[str, Any]]:
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
            # Note: sqlite-vec requires k constraint for KNN queries
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
                    WHERE v.embedding MATCH ? AND k = ?
                        AND m.session_id = ?
                    ORDER BY v.distance
                    """,
                    (json.dumps(query_embedding), top_k, session_id),
                ) as cursor:
                    async for row in cursor:
                        results.append(
                            {
                                "message_idx": row[0],
                                "role": row[1],
                                "content_snippet": row[2],
                                "similarity": self._distance_to_similarity(float(row[3])),
                            }
                        )
            except Exception as e:
                logger.error(f"Error searching messages for session {session_id}: {e}")
                raise RuntimeError("Failed to search messages") from e

            return results

    async def count_sessions(self) -> int:
        """Count total sessions in database.

        Returns:
            Number of sessions
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await self._load_extensions(db)
            async with db.execute("SELECT COUNT(*) FROM sessions") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def count_memories(self) -> int:
        """Count total memories in database.

        Returns:
            Number of memories
        """
        await self._init()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await self._load_extensions(db)
            async with db.execute("SELECT COUNT(*) FROM memories") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0


class ReembedResult:
    """Result of a re-embedding operation."""

    def __init__(self, success: bool, message: str, stats: dict[str, Any] | None = None) -> None:
        """Initialize result.

        Args:
            success: Whether the operation succeeded
            message: Human-readable status message
            stats: Optional statistics about the operation
        """
        self.success = success
        self.message = message
        self.stats = stats or {}


class EmbeddingReembedder:
    """Handles re-embedding of all vector data when dimensions change.

    This class orchestrates the safe migration of vec0 tables from one
    embedding dimension to another, preserving all content.
    """

    def __init__(self, store: "SQLiteStore", embedder: Any) -> None:
        """Initialize reembedder.

        Args:
            store: SQLiteStore instance with database connection
            embedder: Embedder instance for generating new embeddings
        """
        self._store = store
        self._embedder = embedder

    async def reembed_all(self, old_dim: int, new_dim: int) -> ReembedResult:
        """Re-embed all vector data with new dimension.

        Args:
            old_dim: Previous embedding dimension
            new_dim: New embedding dimension

        Returns:
            ReembedResult with success status and statistics
        """
        logger.info(f"Starting re-embedding: {old_dim} -> {new_dim}")

        try:
            # Re-embed each table type
            memory_count = await self._reembed_memories()
            summary_count = await self._reembed_session_summaries()
            message_count = await self._reembed_message_embeddings()

            stats = {
                "memories_reembedded": memory_count,
                "summaries_reembedded": summary_count,
                "messages_reembedded": message_count,
                "old_dimension": old_dim,
                "new_dimension": new_dim,
            }

            msg = (
                f"Re-embedding complete ({old_dim} -> {new_dim}): "
                f"{memory_count} memories, {summary_count} summaries, "
                f"{message_count} messages"
            )
            logger.info(msg)

            return ReembedResult(success=True, message=msg, stats=stats)

        except Exception as e:
            logger.error(f"Re-embedding failed: {e}")
            return ReembedResult(
                success=False,
                message=f"Re-embedding failed: {e}",
                stats={"error": str(e)}
            )

    async def _reembed_memories(self) -> int:
        """Re-embed all memories with current embedder dimension.

        Returns:
            Number of memories re-embedded
        """
        import aiosqlite

        count = 0
        db_path = self._store.db_path

        async with aiosqlite.connect(db_path) as db:
            await self._store._load_extensions(db)

            # Fetch all memories from base table
            async with db.execute(
                "SELECT entry_id, content FROM memories"
            ) as cursor:
                memories = list(await cursor.fetchall())

            total = len(memories)
            logger.info(f"Re-embedding {total} memories...")

            for i, (entry_id, content) in enumerate(memories, 1):
                # Generate new embedding
                embedding = await self._embedder.embed(content)

                # Update in database
                await db.execute(
                    """
                    UPDATE memory_embeddings
                    SET embedding = ?
                    WHERE entry_id = ?
                    """,
                    (json.dumps(embedding), entry_id)
                )

                count += 1
                if i % 10 == 0 or i == total:
                    logger.info(f"  Re-embedded memory {i}/{total}")

            await db.commit()

        return count

    async def _reembed_session_summaries(self) -> int:
        """Re-embed all session summaries with current embedder dimension.

        Returns:
            Number of summaries re-embedded
        """
        import aiosqlite

        count = 0
        db_path = self._store.db_path

        async with aiosqlite.connect(db_path) as db:
            await self._store._load_extensions(db)

            # Fetch all summaries from base table
            async with db.execute(
                "SELECT summary_id, summary_text FROM session_summaries"
            ) as cursor:
                summaries = list(await cursor.fetchall())

            total = len(summaries)
            logger.info(f"Re-embedding {total} session summaries...")

            for i, (summary_id, summary_text) in enumerate(summaries, 1):
                # Generate new embedding
                embedding = await self._embedder.embed(summary_text)

                # Update in database
                await db.execute(
                    """
                    UPDATE session_summaries_vec
                    SET embedding = ?
                    WHERE summary_id = ?
                    """,
                    (json.dumps(embedding), summary_id)
                )

                count += 1
                if i % 10 == 0 or i == total:
                    logger.info(f"  Re-embedded summary {i}/{total}")

            await db.commit()

        return count

    async def _reembed_message_embeddings(self) -> int:
        """Re-embed all message embeddings with current embedder dimension.

        Returns:
            Number of messages re-embedded
        """
        import aiosqlite

        count = 0
        db_path = self._store.db_path

        async with aiosqlite.connect(db_path) as db:
            await self._store._load_extensions(db)

            # Fetch all message embeddings from base table
            async with db.execute(
                "SELECT message_embedding_id, content_snippet FROM message_embeddings"
            ) as cursor:
                messages = list(await cursor.fetchall())

            total = len(messages)
            logger.info(f"Re-embedding {total} message embeddings...")

            for i, (msg_id, content_snippet) in enumerate(messages, 1):
                # Generate new embedding
                embedding = await self._embedder.embed(content_snippet)

                # Update in database
                await db.execute(
                    """
                    UPDATE message_embeddings_vec
                    SET embedding = ?
                    WHERE message_embedding_id = ?
                    """,
                    (json.dumps(embedding), msg_id)
                )

                count += 1
                if i % 10 == 0 or i == total:
                    logger.info(f"  Re-embedded message {i}/{total}")

            await db.commit()

        return count
