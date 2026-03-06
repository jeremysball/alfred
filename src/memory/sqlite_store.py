"""MemoryStore implementation using SQLite backend.

Replaces JSONLMemoryStore and FAISSMemoryStore with a unified SQLite solution.
"""

import logging
from datetime import date, datetime
from typing import Any

from src.config import Config
from src.embeddings.provider import EmbeddingProvider
from src.memory.base import MemoryStore
from src.storage.sqlite import SQLiteStore

logger = logging.getLogger(__name__)


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

        # Use data_dir from config
        db_path = config.data_dir / "memories.db"
        self._store = SQLiteStore(db_path)

        logger.info(f"SQLite memory store initialized: {db_path}")

    async def add(self, entry: Any) -> None:
        """Add a memory entry.
        
        Args:
            entry: MemoryEntry to add
        """
        # Generate embedding if not provided
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
    ) -> tuple[list[Any], dict[str, float], dict[str, float]]:
        """Search memories by semantic similarity.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            start_date: Optional filter for entries on or after this date
            end_date: Optional filter for entries on or before this date
            
        Returns:
            Tuple of (results, similarities, scores)
        """
        # Generate query embedding
        query_embedding = await self.embedder.embed(query)

        # Search via SQLite store
        results = await self._store.search_memories(
            query_embedding=query_embedding,
            top_k=top_k,
        )

        # Filter by date if specified
        if start_date or end_date:
            filtered = []
            for r in results:
                entry_date = r["timestamp"].date() if isinstance(r["timestamp"], datetime) else r["timestamp"]
                if start_date and entry_date < start_date:
                    continue
                if end_date and entry_date > end_date:
                    continue
                filtered.append(r)
            results = filtered

        # Convert to MemoryEntry objects
        from src.memory.jsonl_store import MemoryEntry

        entries = []
        similarities = {}
        scores = {}

        for r in results:
            entry = MemoryEntry(
                entry_id=r["entry_id"],
                timestamp=r["timestamp"],
                role=r["role"],
                content=r["content"],
                tags=r["tags"],
                permanent=r["permanent"],
            )
            entries.append(entry)
            sim = r.get("similarity", 0.0)
            similarities[r["entry_id"]] = sim
            scores[r["entry_id"]] = sim

        return entries, similarities, scores

    async def get_by_id(self, entry_id: str) -> Any | None:
        """Get memory by ID.
        
        Args:
            entry_id: Unique memory ID
            
        Returns:
            Memory entry or None
        """
        from src.memory.jsonl_store import MemoryEntry

        data = await self._store.get_memory(entry_id)
        if data is None:
            return None

        return MemoryEntry(
            entry_id=data["entry_id"],
            timestamp=data["timestamp"],
            role=data["role"],
            content=data["content"],
            tags=data["tags"],
            permanent=data["permanent"],
        )

    async def get_all_entries(self) -> list[Any]:
        """Get all memory entries.
        
        Returns:
            List of all entries
        """
        from src.memory.jsonl_store import MemoryEntry

        results = await self._store.get_all_memories()

        return [
            MemoryEntry(
                entry_id=r["entry_id"],
                timestamp=r["timestamp"],
                role=r["role"],
                content=r["content"],
                tags=r["tags"],
                permanent=r["permanent"],
            )
            for r in results
        ]

    async def delete_by_id(self, entry_id: str) -> tuple[bool, str]:
        """Delete memory by ID.
        
        Args:
            entry_id: Unique memory ID
            
        Returns:
            Tuple of (success, message)
        """
        deleted = await self._store.delete_memory(entry_id)
        if deleted:
            return True, f"Deleted memory {entry_id}"
        return False, f"Memory {entry_id} not found"

    async def add_entries(self, entries: list[Any]) -> None:
        """Add multiple entries at once.
        
        Args:
            entries: List of MemoryEntry objects
        """
        # Generate embeddings for entries that don't have them
        entries_to_embed = [e for e in entries if e.embedding is None]
        if entries_to_embed:
            embeddings = await self.embedder.embed_batch([e.content for e in entries_to_embed])
            for entry, embedding in zip(entries_to_embed, embeddings):
                entry.embedding = embedding

        # Add all entries
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
        return await self._store.prune_memories(ttl_days=ttl_days, dry_run=dry_run)

    async def update_entry(self, search_query: str, new_content: str | None = None) -> tuple[bool, str]:
        """Update an existing memory entry.
        
        Args:
            search_query: Query to find the memory to update
            new_content: New content (None = don't change)
            
        Returns:
            Tuple of (success, message)
        """
        # Find best matching memory
        entries = await self.get_all_entries()
        if not entries:
            return False, "No memories to update"

        # Use simple text search for now
        best_match = None
        for entry in entries:
            if search_query.lower() in entry.content.lower():
                best_match = entry
                break

        if best_match is None:
            return False, f"No matching memory found for query: {search_query}"

        # Update the entry
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
        # Find matching memories
        entries = await self.get_all_entries()
        if not entries:
            return 0, "No memories to delete"

        # Use simple text search
        to_delete = [e for e in entries if query.lower() in e.content.lower()]

        if not to_delete:
            return 0, f"No memories matching query: {query}"

        # Delete them
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
        # This is synchronous - run in executor or cache
        import asyncio

        try:
            count = asyncio.get_event_loop().run_until_complete(
                self._get_memory_count()
            )
        except Exception:
            # Fallback: assume under threshold
            return False, 0

        return count > threshold, count

    async def _get_memory_count(self) -> int:
        """Get memory count asynchronously."""
        entries = await self._store.get_all_memories()
        return len(entries)
