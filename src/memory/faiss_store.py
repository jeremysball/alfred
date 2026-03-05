"""FAISS-backed memory store for fast semantic search.

Provides O(log n) search vs O(n) for JSONL.
Uses FAISS IndexFlatIP for small stores, IndexIVFFlat for large.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np

from src.embeddings.provider import EmbeddingProvider
from src.memory.base import MemoryStore

logger = logging.getLogger(__name__)

# Default thresholds
DEFAULT_IVF_THRESHOLD = 10000  # Switch to IVF at 10K memories
DEFAULT_REBUILD_THRESHOLD = 0.2  # Rebuild when 20% deleted (not used with rebuild-on-delete)


class MemoryEntry:
    """Memory entry for FAISS store."""

    def __init__(
        self,
        content: str,
        role: Literal["user", "assistant", "system"] = "user",
        timestamp: datetime | None = None,
        tags: list[str] | None = None,
        entry_id: str | None = None,
        permanent: bool = False,
        embedding: list[float] | None = None,
    ) -> None:
        import hashlib

        self.timestamp = timestamp or datetime.now()
        self.role = role
        self.content = content
        self.tags = tags or []
        self.permanent = permanent
        self.embedding = embedding

        # Generate ID if not provided
        if entry_id:
            self.entry_id = entry_id
        else:
            hash_input = f"{self.timestamp.isoformat()}:{content}"
            self.entry_id = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "role": self.role,
            "content": self.content,
            "tags": self.tags,
            "permanent": self.permanent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        """Deserialize from dict."""
        return cls(
            entry_id=data["entry_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            role=data["role"],
            content=data["content"],
            tags=data.get("tags", []),
            permanent=data.get("permanent", False),
        )


class FAISSMemoryStore(MemoryStore):
    """FAISS-backed memory store with fast semantic search.

    Features:
    - O(log n) search via FAISS ANN index
    - Auto-switches from Flat to IVF at threshold
    - Persistence (save/load to disk)
    - Rebuild-on-delete for simplicity
    """

    def __init__(
        self,
        index_path: Path,
        provider: EmbeddingProvider,
        index_type: Literal["flat", "ivf", "auto"] = "auto",
        ivf_threshold: int = DEFAULT_IVF_THRESHOLD,
        rebuild_threshold: float = DEFAULT_REBUILD_THRESHOLD,
    ) -> None:
        """Initialize FAISS memory store.

        Args:
            index_path: Directory to store index and metadata
            provider: Embedding provider for generating vectors
            index_type: "flat" (exact), "ivf" (approximate), or "auto"
            ivf_threshold: Memory count to switch from flat to IVF (when auto)
            rebuild_threshold: Ratio of deleted entries before rebuild (unused)
        """
        import faiss

        self._index_path = Path(index_path)
        self._index_path.mkdir(parents=True, exist_ok=True)
        self._provider = provider
        self._dimension = provider.dimension
        self._index_type_setting = index_type
        self._ivf_threshold = ivf_threshold
        self._rebuild_threshold = rebuild_threshold

        # Internal state
        self._metadata: dict[str, MemoryEntry] = {}  # id -> entry
        self._id_to_idx: dict[str, int] = {}  # id -> FAISS index position
        self._idx_to_id: dict[int, str] = {}  # FAISS index position -> id
        self._next_idx: int = 0
        self._deleted_ids: set[str] = set()

        # Initialize FAISS index
        self._index_type = self._determine_index_type(index_type)
        self._index = self._create_index(self._index_type)

        # Try to load existing index
        self._load_sync()

    def _determine_index_type(self, setting: str) -> str:
        """Determine actual index type to use."""
        if setting == "auto":
            # Will be re-evaluated as entries are added
            return "flat"
        return setting

    def _create_index(self, index_type: str) -> Any:
        """Create FAISS index of specified type."""
        import faiss

        if index_type == "ivf":
            # IVF requires nlist (number of clusters)
            # Rule of thumb: sqrt(n) clusters, but we need minimum
            nlist = max(4, int(np.sqrt(self._ivf_threshold)))
            quantizer = faiss.IndexFlatIP(self._dimension)
            index = faiss.IndexIVFFlat(quantizer, self._dimension, nlist)
            return index
        else:
            # Flat index for exact search
            return faiss.IndexFlatIP(self._dimension)

    def _maybe_upgrade_to_ivf(self) -> None:
        """Upgrade from Flat to IVF if threshold exceeded."""
        if self._index_type_setting != "auto":
            return
        if self._index_type == "ivf":
            return

        if self._next_idx >= self._ivf_threshold:
            logger.info(f"Upgrading to IVF index at {self._next_idx} entries")
            self._upgrade_to_ivf()

    def _upgrade_to_ivf(self) -> None:
        """Upgrade Flat index to IVF."""
        import faiss

        if self._index.ntotal == 0:
            # Just create new IVF index
            self._index = self._create_index("ivf")
            self._index_type = "ivf"
            return

        # Extract all vectors from flat index
        vectors = self._index.xb.reshape(-1, self._dimension).copy()

        # Create IVF index
        nlist = max(4, int(np.sqrt(len(vectors))))
        quantizer = faiss.IndexFlatIP(self._dimension)
        ivf_index = faiss.IndexIVFFlat(quantizer, self._dimension, nlist)

        # Train on existing vectors
        ivf_index.train(vectors)
        ivf_index.add(vectors)

        self._index = ivf_index
        self._index_type = "ivf"
        logger.info(f"Upgraded to IVF index with {nlist} clusters")

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimension

    async def add(self, entry: MemoryEntry) -> None:
        """Add memory entry to store.

        Args:
            entry: Memory entry to add
        """
        # Generate embedding if not provided
        if entry.embedding is None:
            entry.embedding = await self._provider.embed(entry.content)

        # Add to FAISS index
        vector = np.array([entry.embedding], dtype=np.float32)
        self._index.add(vector)

        # Track mapping
        idx = self._next_idx
        self._id_to_idx[entry.entry_id] = idx
        self._idx_to_id[idx] = entry.entry_id
        self._metadata[entry.entry_id] = entry
        self._next_idx += 1

        # Maybe upgrade to IVF
        self._maybe_upgrade_to_ivf()

        logger.debug(f"Added memory {entry.entry_id} at index {idx}")

    async def search(
        self,
        query: str,
        top_k: int = 10,
        **kwargs,
    ) -> tuple[list[MemoryEntry], dict[str, float], dict[str, float]]:
        """Search memories by semantic similarity.

        Args:
            query: Search query text
            top_k: Number of results to return

        Returns:
            Tuple of (results, similarities, scores)
        """
        if self._index.ntotal == 0:
            return [], {}, {}

        # Embed query
        query_embedding = await self._provider.embed(query)
        query_vector = np.array([query_embedding], dtype=np.float32)

        # Search FAISS
        k = min(top_k, self._index.ntotal)
        distances, indices = self._index.search(query_vector, k)

        # Build results
        results: list[MemoryEntry] = []
        similarities: dict[str, float] = {}
        scores: dict[str, float] = {}

        for i, idx in enumerate(indices[0]):
            if idx < 0:  # FAISS returns -1 for not found
                continue

            entry_id = self._idx_to_id.get(int(idx))
            if entry_id is None:
                continue

            # Skip deleted entries
            if entry_id in self._deleted_ids:
                continue

            entry = self._metadata.get(entry_id)
            if entry is None:
                continue

            results.append(entry)

            # FAISS returns inner product (cosine sim for normalized vectors)
            sim = float(distances[0][i])
            similarities[entry_id] = sim
            scores[entry_id] = sim  # Same as similarity for FAISS

        return results, similarities, scores

    async def get_by_id(self, entry_id: str) -> MemoryEntry | None:
        """Get memory by ID.

        Args:
            entry_id: Unique memory ID

        Returns:
            Memory entry or None if not found/deleted
        """
        if entry_id in self._deleted_ids:
            return None
        return self._metadata.get(entry_id)

    async def get_all_entries(self) -> list[MemoryEntry]:
        """Get all non-deleted memory entries.

        Returns:
            List of all entries
        """
        return [
            entry
            for entry_id, entry in self._metadata.items()
            if entry_id not in self._deleted_ids
        ]

    async def delete_by_id(self, entry_id: str) -> tuple[bool, str]:
        """Delete memory by ID (rebuilds index).

        Args:
            entry_id: Unique memory ID

        Returns:
            Tuple of (success, message)
        """
        if entry_id not in self._metadata:
            return False, f"Memory {entry_id} not found"

        # Mark as deleted
        self._deleted_ids.add(entry_id)

        # Rebuild index without deleted entries
        await self._rebuild_index()

        return True, f"Deleted memory {entry_id}"

    async def _rebuild_index(self) -> None:
        """Rebuild FAISS index without deleted entries."""
        import faiss

        # Get all non-deleted entries with embeddings
        entries_to_keep = [
            (entry, idx)
            for entry_id, entry in self._metadata.items()
            if entry_id not in self._deleted_ids
            for idx in [self._id_to_idx.get(entry_id)]
            if idx is not None and entry.embedding is not None
        ]

        if not entries_to_keep:
            # Empty store - reset
            self._index = self._create_index(self._index_type)
            self._id_to_idx.clear()
            self._idx_to_id.clear()
            self._metadata.clear()
            self._deleted_ids.clear()
            self._next_idx = 0
            return

        # Build new vectors array
        vectors = np.array(
            [entry.embedding for entry, _ in entries_to_keep],
            dtype=np.float32,
        )

        # Create new index
        self._index = self._create_index(self._index_type)
        if self._index_type == "ivf" and len(vectors) > 0:
            # IVF needs training
            self._index.train(vectors)
        self._index.add(vectors)

        # Rebuild mappings
        new_id_to_idx: dict[str, int] = {}
        new_idx_to_id: dict[int, str] = {}
        new_metadata: dict[str, MemoryEntry] = {}

        for new_idx, (entry, _) in enumerate(entries_to_keep):
            new_id_to_idx[entry.entry_id] = new_idx
            new_idx_to_id[new_idx] = entry.entry_id
            new_metadata[entry.entry_id] = entry

        self._id_to_idx = new_id_to_idx
        self._idx_to_id = new_idx_to_id
        self._metadata = new_metadata
        self._deleted_ids.clear()
        self._next_idx = len(entries_to_keep)

        logger.debug(f"Rebuilt index with {len(entries_to_keep)} entries")

    async def save(self) -> None:
        """Persist index and metadata to disk."""
        import faiss

        # Save FAISS index
        index_file = self._index_path / "index.faiss"
        faiss.write_index(self._index, str(index_file))

        # Save metadata
        metadata_file = self._index_path / "metadata.json"
        metadata = {
            "dimension": self._dimension,
            "index_type": self._index_type,
            "entries": [entry.to_dict() for entry in self._metadata.values()],
            "id_to_idx": self._id_to_idx,
            "next_idx": self._next_idx,
            "deleted_ids": list(self._deleted_ids),
        }
        metadata_file.write_text(json.dumps(metadata, indent=2))

        # Save embeddings separately (for rebuild)
        embeddings_file = self._index_path / "embeddings.npy"
        if self._metadata:
            embeddings = [
                entry.embedding
                for entry in self._metadata.values()
                if entry.embedding is not None
            ]
            if embeddings:
                np.save(embeddings_file, np.array(embeddings, dtype=np.float32))
            elif embeddings_file.exists():
                embeddings_file.unlink()

        logger.info(f"Saved FAISS index with {len(self._metadata)} entries")

    async def load(self) -> None:
        """Load index and metadata from disk."""
        self._load_sync()

    def _load_sync(self) -> None:
        """Synchronous load (called from __init__)."""
        import faiss

        index_file = self._index_path / "index.faiss"
        metadata_file = self._index_path / "metadata.json"
        embeddings_file = self._index_path / "embeddings.npy"

        if not index_file.exists() or not metadata_file.exists():
            logger.debug("No existing FAISS index found, starting fresh")
            return

        # Load FAISS index
        self._index = faiss.read_index(str(index_file))

        # Load metadata
        data = json.loads(metadata_file.read_text())
        self._index_type = data.get("index_type", "flat")
        self._id_to_idx = {k: int(v) for k, v in data.get("id_to_idx", {}).items()}
        self._idx_to_id = {int(v): k for k, v in self._id_to_idx.items()}
        self._next_idx = data.get("next_idx", 0)
        self._deleted_ids = set(data.get("deleted_ids", []))

        # Load entries
        self._metadata = {
            entry_data["entry_id"]: MemoryEntry.from_dict(entry_data)
            for entry_data in data.get("entries", [])
        }

        # Load embeddings
        if embeddings_file.exists():
            embeddings = np.load(embeddings_file)
            # Re-attach embeddings to entries
            entries = list(self._metadata.values())
            for i, entry in enumerate(entries):
                if i < len(embeddings):
                    entry.embedding = embeddings[i].tolist()

        logger.info(f"Loaded FAISS index with {len(self._metadata)} entries")
