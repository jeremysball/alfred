"""MemoryStore implementation using SQLite backend.

Replaces JSONLMemoryStore and FAISSMemoryStore with a unified SQLite solution.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime
from typing import Any

from alfred.config import Config
from alfred.embeddings.provider import EmbeddingProvider
from alfred.memory.base import MemoryEntry, MemoryStore
from alfred.storage.sqlite import SQLiteStore

logger = logging.getLogger(__name__)


def _parse_timestamp(ts: str | datetime) -> datetime:
    """Parse timestamp from string or return datetime object.

    SQLite returns timestamps as strings, so we need to parse them.
    """
    if isinstance(ts, str):
        return datetime.fromisoformat(ts)
    return ts


class SQLiteMemoryStore(MemoryStore):
    """Memory store backed by SQLite with vector search.

    Uses sqlite-vec for efficient vector similarity search when available,
    falling back to brute-force search if not.
    """

    def __init__(self, config: Config, embedder: EmbeddingProvider) -> None:
        """Initialize SQLite memory store.

        Args:
            config: Application configuration
            embedder: Embedding provider for generating vectors
        """
        self.config = config
        self.embedder = embedder
        self._schema_rebuild_lock = asyncio.Lock()

        # Use data_dir from config.
        # Keep SQLiteStore generic: memory-specific rebuild logic lives here.
        db_path = config.data_dir / "memories.db"
        self._store = SQLiteStore(
            db_path,
            embedding_dim=embedder.dimension,
        )

        logger.info(
            "SQLite memory store initialized: %s (dim=%s)",
            db_path,
            embedder.dimension,
        )

    @staticmethod
    def _is_memory_schema_mismatch(exc: RuntimeError) -> bool:
        """Return True when SQLiteStore failed because memory_embeddings drifted."""
        message = str(exc).lower()
        return "memory_embeddings" in message and "schema mismatch" in message

    async def _ensure_store_ready(self) -> None:
        """Initialize the backing store, rebuilding stale memory vectors if needed."""
        if self._store._initialized:
            return

        async with self._schema_rebuild_lock:
            if self._store._initialized:
                return

            try:
                await self._store._init()
                return
            except RuntimeError as exc:
                if not self._is_memory_schema_mismatch(exc):
                    raise

            logger.warning(
                "SQLiteMemoryStore detected stale memory_embeddings vec0 schema; rebuilding automatically."
            )
            await self._rebuild_memory_embeddings()
            await self._store._init()

    async def _rebuild_memory_embeddings(self) -> None:
        """Rebuild the memory_embeddings vec0 table from canonical memory rows."""
        import aiosqlite

        async with aiosqlite.connect(self._store.db_path) as db:
            await self._store._load_extensions(db)
            db.row_factory = aiosqlite.Row

            await db.execute("DROP TABLE IF EXISTS memory_embeddings")
            await db.execute(
                f"""
                CREATE VIRTUAL TABLE memory_embeddings USING vec0(
                    entry_id TEXT PRIMARY KEY,
                    embedding FLOAT[{self.embedder.dimension}] distance_metric=cosine
                )
                """
            )

            async with db.execute("SELECT entry_id, content FROM memories") as cursor:
                memories = await cursor.fetchall()

            for memory in memories:
                embedding = await self.embedder.embed(memory["content"])
                await db.execute(
                    """
                    INSERT INTO memory_embeddings (entry_id, embedding)
                    VALUES (?, ?)
                    """,
                    (memory["entry_id"], json.dumps(embedding)),
                )

            await db.commit()

    async def add(self, entry: MemoryEntry) -> None:
        """Add a memory entry.

        Args:
            entry: MemoryEntry to add
        """
        await self._ensure_store_ready()

        # Generate embedding if not provided.
        if entry.embedding is None:
            entry.embedding = await self.embedder.embed(entry.content)

        await self._store.add_memory(
            entry_id=entry.entry_id,
            role=entry.role,
            content=entry.content,
            embedding=entry.embedding,
            tags=entry.tags,
            permanent=entry.permanent,
            timestamp=entry.timestamp,
        )

    async def search(
        self,
        query: str,
        top_k: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> tuple[list[MemoryEntry], dict[str, float], dict[str, float]]:
        """Search memories by semantic similarity.

        Args:
            query: Search query text
            top_k: Number of results to return
            start_date: Optional filter for entries on or after this date
            end_date: Optional filter for entries on or before this date

        Returns:
            Tuple of (results, similarities, scores)
        """
        await self._ensure_store_ready()

        # Generate query embedding.
        query_embedding = await self.embedder.embed(query)

        # Search via SQLite store.
        results = await self._store.search_memories(
            query_embedding=query_embedding,
            top_k=top_k,
        )

        # Filter by date if specified.
        if start_date or end_date:
            filtered: list[dict[str, Any]] = []
            for row in results:
                ts = row["timestamp"]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                entry_date = ts.date() if isinstance(ts, datetime) else ts
                if start_date and entry_date < start_date:
                    continue
                if end_date and entry_date > end_date:
                    continue
                filtered.append(row)
            results = filtered

        entries: list[MemoryEntry] = []
        similarities: dict[str, float] = {}
        scores: dict[str, float] = {}

        for row in results:
            entry = MemoryEntry(
                entry_id=row["entry_id"],
                timestamp=_parse_timestamp(row["timestamp"]),
                role=row["role"],
                content=row["content"],
                tags=row["tags"],
                permanent=row["permanent"],
            )
            entries.append(entry)
            similarity = float(row.get("similarity", 0.0))
            similarities[row["entry_id"]] = similarity
            scores[row["entry_id"]] = similarity

        return entries, similarities, scores

    async def get_by_id(self, entry_id: str) -> MemoryEntry | None:
        """Get memory by ID.

        Args:
            entry_id: Unique memory ID

        Returns:
            Memory entry or None
        """
        await self._ensure_store_ready()

        data = await self._store.get_memory(entry_id)
        if data is None:
            return None

        return MemoryEntry(
            entry_id=data["entry_id"],
            timestamp=_parse_timestamp(data["timestamp"]),
            role=data["role"],
            content=data["content"],
            tags=data["tags"],
            permanent=data["permanent"],
        )

    async def get_all_entries(self) -> list[MemoryEntry]:
        """Get all memory entries.

        Returns:
            List of all entries
        """
        await self._ensure_store_ready()

        results = await self._store.get_all_memories()

        return [
            MemoryEntry(
                entry_id=row["entry_id"],
                timestamp=_parse_timestamp(row["timestamp"]),
                role=row["role"],
                content=row["content"],
                tags=row["tags"],
                permanent=row["permanent"],
            )
            for row in results
        ]

    async def delete_by_id(self, entry_id: str) -> tuple[bool, str]:
        """Delete memory by ID.

        Args:
            entry_id: Unique memory ID

        Returns:
            Tuple of (success, message)
        """
        await self._ensure_store_ready()

        deleted = await self._store.delete_memory(entry_id)
        if deleted:
            return True, f"Deleted memory {entry_id}"
        return False, f"Memory {entry_id} not found"

    async def add_entries(self, entries: list[MemoryEntry]) -> None:
        """Add multiple entries at once.

        Args:
            entries: List of MemoryEntry objects
        """
        await self._ensure_store_ready()

        # Generate embeddings for entries that don't have them.
        entries_to_embed = [entry for entry in entries if entry.embedding is None]
        if entries_to_embed:
            embeddings = await self.embedder.embed_batch([entry.content for entry in entries_to_embed])
            for entry, embedding in zip(entries_to_embed, embeddings, strict=True):
                entry.embedding = embedding

        # Add all entries.
        for entry in entries:
            await self.add(entry)

    async def prune_expired_memories(self, ttl_days: int = 90, dry_run: bool = False) -> int:
        """Remove non-permanent memories older than TTL.

        Args:
            ttl_days: Number of days after which non-permanent memories expire
            dry_run: If True, return count without deleting

        Returns:
            Number of memories pruned
        """
        await self._ensure_store_ready()
        return await self._store.prune_memories(ttl_days=ttl_days, dry_run=dry_run)

    async def update_entry(
        self,
        search_query: str,
        new_content: str | None = None,
    ) -> tuple[bool, str]:
        """Update an existing memory entry.

        Args:
            search_query: Query to find the memory to update
            new_content: New content (None = don't change)

        Returns:
            Tuple of (success, message)
        """
        await self._ensure_store_ready()

        # Find best matching memory.
        entries = await self.get_all_entries()
        if not entries:
            return False, "No memories to update"

        best_match = None
        for entry in entries:
            if search_query.lower() in entry.content.lower():
                best_match = entry
                break

        if best_match is None:
            return False, f"No matching memory found for query: {search_query}"

        updated = await self._store.update_memory(
            entry_id=best_match.entry_id,
            content=new_content,
        )

        if updated:
            return True, f"Updated memory {best_match.entry_id}"
        return False, f"Failed to update memory {best_match.entry_id}"

    async def delete_entries(self, query: str) -> tuple[int, str]:
        """Delete memories matching a semantic query.

        Args:
            query: Semantic query to find memories to delete

        Returns:
            Tuple of (count_deleted, message)
        """
        await self._ensure_store_ready()

        # Find matching memories.
        entries = await self.get_all_entries()
        if not entries:
            return 0, "No memories to delete"

        # Use simple text search.
        to_delete = [entry for entry in entries if query.lower() in entry.content.lower()]

        if not to_delete:
            return 0, f"No memories matching query: {query}"

        deleted_count = 0
        for entry in to_delete:
            if await self._store.delete_memory(entry.entry_id):
                deleted_count += 1

        return deleted_count, f"Deleted {deleted_count} memories"

    def check_memory_threshold(self, threshold: int = 1000) -> tuple[bool, int]:
        """Check if memory count exceeds threshold.

        Args:
            threshold: Maximum allowed memories before warning

        Returns:
            Tuple of (exceeded, count)
        """
        # This is synchronous - run in executor or cache.
        import asyncio

        try:
            count = asyncio.get_event_loop().run_until_complete(self._get_memory_count())
        except Exception:
            # Fallback: assume under threshold.
            return False, 0

        return count > threshold, count

    async def _get_memory_count(self) -> int:
        """Get memory count asynchronously."""
        await self._ensure_store_ready()
        entries = await self._store.get_all_memories()
        return len(entries)
