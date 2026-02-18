"""Unified memory storage system with semantic search."""

import json
from datetime import datetime, date
from pathlib import Path
from typing import AsyncIterator

import aiofiles

from src.config import Config
from src.embeddings import EmbeddingClient, cosine_similarity
from src.types import MemoryEntry


class MemoryStore:
    """Unified memory store with semantic search.

    All memories stored in a single JSONL file with embeddings.
    Date is metadata (timestamp), not structural (file names).
    MEMORY.md holds curated long-term memories separately.
    """

    def __init__(self, config: Config, embedder: EmbeddingClient) -> None:
        self.config = config
        self.embedder = embedder
        self.memory_dir = config.memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memories_path = self.memory_dir / "memories.jsonl"
        self.curated_path = Path("MEMORY.md")

    def _entry_to_jsonl(self, entry: MemoryEntry) -> str:
        """Serialize MemoryEntry to JSONL line."""
        # Ensure ID is generated
        if entry.entry_id is None:
            entry.entry_id = entry.generate_id()
        return json.dumps({
            "timestamp": entry.timestamp.isoformat(),
            "role": entry.role,
            "content": entry.content,
            "embedding": entry.embedding,
            "importance": entry.importance,
            "tags": entry.tags,
            "entry_id": entry.entry_id,
        })

    def _entry_from_jsonl(self, line: str) -> MemoryEntry:
        """Deserialize JSONL line to MemoryEntry."""
        data = json.loads(line)
        return MemoryEntry(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            role=data["role"],
            content=data["content"],
            embedding=data.get("embedding"),
            importance=data.get("importance", 0.5),
            tags=data.get("tags", []),
            entry_id=data.get("entry_id"),  # Auto-generated if None
        )

    async def add_entries(self, entries: list[MemoryEntry]) -> None:
        """Add multiple entries to the unified memory store.

        Called by the distillation process after extracting insights.
        Generates embeddings if not already present.

        Fail-fast behavior: If embedding generation fails (even after retries),
        no entries are written. Memories without embeddings are useless for
        semantic search, so we don't write partial data.
        """
        if not entries:
            return

        # Generate embeddings for entries that don't have them
        entries_to_embed = [e for e in entries if e.embedding is None]
        if entries_to_embed:
            try:
                embeddings = await self.embedder.embed_batch(
                    [e.content for e in entries_to_embed]
                )
                for entry, embedding in zip(entries_to_embed, embeddings):
                    entry.embedding = embedding
            except Exception:
                # Fail fast - don't write anything if embedding fails
                raise

        # Fail fast if any entry still lacks embedding
        entries_without_embeddings = [e for e in entries if e.embedding is None]
        if entries_without_embeddings:
            raise ValueError(
                f"Cannot add {len(entries_without_embeddings)} entries without embeddings"
            )

        # Append to JSONL file (only reached if all embeddings succeeded)
        async with aiofiles.open(self.memories_path, "a") as f:
            for entry in entries:
                await f.write(self._entry_to_jsonl(entry) + "\n")

    async def get_all_entries(self) -> list[MemoryEntry]:
        """Load all memory entries."""
        entries = []
        if not self.memories_path.exists():
            return entries

        async with aiofiles.open(self.memories_path, "r") as f:
            async for line in f:
                line = line.strip()
                if line:
                    entries.append(self._entry_from_jsonl(line))
        return entries

    async def iter_entries(self) -> AsyncIterator[MemoryEntry]:
        """Iterate over all memory entries (memory-efficient)."""
        if not self.memories_path.exists():
            return

        async with aiofiles.open(self.memories_path, "r") as f:
            async for line in f:
                line = line.strip()
                if line:
                    yield self._entry_from_jsonl(line)

    async def filter_by_date(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MemoryEntry]:
        """Filter entries by date range."""
        results = []
        async for entry in self.iter_entries():
            entry_date = entry.timestamp.date()
            if start_date and entry_date < start_date:
                continue
            if end_date and entry_date > end_date:
                continue
            results.append(entry)
        return results

    async def search(
        self,
        query: str,
        top_k: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MemoryEntry]:
        """Search memories by semantic similarity.

        Args:
            query: Search query text
            top_k: Number of results to return
            start_date: Optional filter for entries on or after this date
            end_date: Optional filter for entries on or before this date

        Returns:
            Top-k most relevant entries, ranked by similarity × importance
        """
        query_embedding = await self.embedder.embed(query)

        # Score all entries (with optional date filtering)
        scored: list[tuple[float, MemoryEntry]] = []

        async for entry in self.iter_entries():
            # Date filtering
            if start_date or end_date:
                entry_date = entry.timestamp.date()
                if start_date and entry_date < start_date:
                    continue
                if end_date and entry_date > end_date:
                    continue

            if entry.embedding:
                score = cosine_similarity(query_embedding, entry.embedding)
                # Boost by importance (0.7 base + 0.3 × importance)
                score *= 0.7 + (entry.importance * 0.3)
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]

    async def clear(self) -> None:
        """Clear all memories (useful for testing)."""
        if self.memories_path.exists():
            self.memories_path.unlink()

    async def get_by_id(self, entry_id: str) -> MemoryEntry | None:
        """Get a memory entry by its ID.

        Args:
            entry_id: The unique ID of the memory entry

        Returns:
            The memory entry if found, None otherwise
        """
        async for entry in self.iter_entries():
            if entry.entry_id == entry_id:
                return entry
        return None

    # --- CRUD Operations ---

    async def update_entry(
        self,
        search_query: str,
        new_content: str | None = None,
        new_importance: float | None = None,
    ) -> tuple[bool, str]:
        """Update an existing memory entry.

        Finds the best matching memory by semantic search and updates specified fields.
        If content changes, the embedding is regenerated.

        Args:
            search_query: Query to find the memory to update
            new_content: New content (None = don't change)
            new_importance: New importance value (None = don't change)

        Returns:
            Tuple of (success: bool, message: str)
        """
        if new_content is None and new_importance is None:
            return False, "No changes specified"

        # Load all entries
        entries = await self.get_all_entries()
        if not entries:
            return False, "No memories to update"

        # Find best match
        query_embedding = await self.embedder.embed(search_query)
        best_match: tuple[float, MemoryEntry | None] = (0.0, None)

        for entry in entries:
            if entry.embedding:
                similarity = cosine_similarity(query_embedding, entry.embedding)
                if similarity > best_match[0]:
                    best_match = (similarity, entry)

        if best_match[1] is None or best_match[0] < 0.3:
            return False, f"No matching memory found for query: {search_query}"

        target_entry = best_match[1]

        # Apply updates
        old_content = target_entry.content
        if new_content is not None:
            target_entry.content = new_content
            # Regenerate embedding if content changed
            if new_content != old_content:
                target_entry.embedding = await self.embedder.embed(new_content)

        if new_importance is not None:
            target_entry.importance = new_importance

        # Rewrite all entries
        await self._rewrite_entries(entries)

        return True, f"Updated: {target_entry.content[:100]}{'...' if len(target_entry.content) > 100 else ''}"

    async def delete_entries(
        self,
        query: str,
    ) -> tuple[int, str]:
        """Delete memories matching a semantic query.

        Args:
            query: Semantic query to find memories to delete

        Returns:
            Tuple of (count_deleted: int, message: str)
        """
        # Load all entries
        entries = await self.get_all_entries()
        if not entries:
            return 0, "No memories to delete"

        # Find matches
        query_embedding = await self.embedder.embed(query)
        entries_to_keep: list[MemoryEntry] = []
        deleted_count = 0

        for entry in entries:
            if entry.embedding:
                similarity = cosine_similarity(query_embedding, entry.embedding)
                if similarity >= 0.3:  # Same threshold as retrieval
                    deleted_count += 1
                    continue  # Skip this entry (delete it)
            entries_to_keep.append(entry)

        if deleted_count == 0:
            return 0, f"No memories matching query: {query}"

        # Rewrite with remaining entries
        await self._rewrite_entries(entries_to_keep)

        return deleted_count, f"Deleted {deleted_count} memory{'ies' if deleted_count != 1 else 'y'}"

    async def delete_by_id(self, entry_id: str) -> tuple[bool, str]:
        """Delete a memory entry by its ID.

        Args:
            entry_id: The unique ID of the memory entry to delete

        Returns:
            Tuple of (success: bool, message: str)
        """
        entries = await self.get_all_entries()
        if not entries:
            return False, "No memories to delete"

        original_count = len(entries)
        entries = [e for e in entries if e.entry_id != entry_id]

        if len(entries) == original_count:
            return False, f"No memory found with ID: {entry_id}"

        # Rewrite with remaining entries
        await self._rewrite_entries(entries)

        return True, "Deleted 1 memory"

    async def _rewrite_entries(self, entries: list[MemoryEntry]) -> None:
        """Atomically rewrite all entries to the JSONL file.

        Uses a temp file and atomic replace to prevent corruption.
        """
        temp_path = self.memories_path.with_suffix('.tmp')

        async with aiofiles.open(temp_path, "w") as f:
            for entry in entries:
                await f.write(self._entry_to_jsonl(entry) + "\n")

        # Atomic replace
        temp_path.replace(self.memories_path)

    # --- MEMORY.md (Curated Long-term Memory) ---

    async def read_curated_memory(self) -> str:
        """Read MEMORY.md content."""
        if not self.curated_path.exists():
            return ""
        async with aiofiles.open(self.curated_path, "r") as f:
            return await f.read()

    async def write_curated_memory(self, content: str) -> None:
        """Write to MEMORY.md (overwrites existing content).

        Use this for durable, important memories that should persist
        across sessions and be loaded into every context.
        """
        async with aiofiles.open(self.curated_path, "w") as f:
            await f.write(content)

    async def append_curated_memory(self, content: str) -> None:
        """Append to MEMORY.md."""
        async with aiofiles.open(self.curated_path, "a") as f:
            await f.write(f"\n\n{content}\n")

    async def search_curated(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[MemoryEntry]:
        """Search curated memories by semantic similarity."""
        content = await self.read_curated_memory()
        if not content:
            return []

        # Split into sections (by headers or paragraphs)
        sections = [s.strip() for s in content.split("\n\n") if s.strip()]

        query_embedding = await self.embedder.embed(query)

        scored = []
        for section in sections:
            section_embedding = await self.embedder.embed(section)
            score = cosine_similarity(query_embedding, section_embedding)
            scored.append((score, section))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Return as MemoryEntry objects
        now = datetime.now()
        return [
            MemoryEntry(
                timestamp=now,
                role="system",
                content=section,
                embedding=None,  # Could cache these later
                importance=1.0,
                tags=["curated"],
            )
            for _, section in scored[:top_k]
        ]
