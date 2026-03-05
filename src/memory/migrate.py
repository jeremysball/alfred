"""Migration script: JSONL to FAISS.

Converts existing JSONL memory store to FAISS-backed store.
Preserves all metadata, creates backup, handles errors gracefully.
"""

import asyncio
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from src.embeddings.provider import EmbeddingProvider
from src.memory.faiss_store import FAISSMemoryStore, MemoryEntry

logger = logging.getLogger(__name__)


async def migrate_jsonl_to_faiss(
    jsonl_path: Path,
    faiss_path: Path,
    provider: EmbeddingProvider,
    backup: bool = True,
    batch_size: int = 100,
) -> dict[str, Any]:
    """Migrate memories from JSONL to FAISS.

    Args:
        jsonl_path: Path to memories.jsonl file
        faiss_path: Directory for FAISS index
        provider: Embedding provider for generating vectors
        backup: Create backup of original file
        batch_size: Number of entries to process per batch

    Returns:
        Dict with migration stats:
        - migrated: Number of entries migrated
        - failed: Number of entries that failed
        - skipped: Number of entries skipped (no content)
        - duration_seconds: Total migration time
    """
    import time

    start_time = time.time()
    stats = {
        "migrated": 0,
        "failed": 0,
        "skipped": 0,
        "duration_seconds": 0,
    }

    # Check if source exists
    if not jsonl_path.exists():
        logger.warning(f"Source file not found: {jsonl_path}")
        stats["error"] = "Source file not found"
        return stats

    # Create backup
    if backup:
        backup_path = jsonl_path.with_suffix(".jsonl.bak")
        if not backup_path.exists():
            shutil.copy2(jsonl_path, backup_path)
            logger.info(f"Created backup: {backup_path}")

    # Create FAISS store
    faiss_path.mkdir(parents=True, exist_ok=True)
    store = FAISSMemoryStore(
        index_path=faiss_path,
        provider=provider,
    )

    # Load entries from JSONL
    entries_to_migrate: list[dict] = []
    with open(jsonl_path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
                entries_to_migrate.append(entry)
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping invalid JSON at line {line_num}: {e}")
                stats["failed"] += 1

    logger.info(f"Found {len(entries_to_migrate)} entries to migrate")

    # Migrate in batches
    for i in range(0, len(entries_to_migrate), batch_size):
        batch = entries_to_migrate[i : i + batch_size]
        await _migrate_batch(batch, store, provider, stats)

        # Log progress
        if (i + batch_size) % 500 == 0 or i + batch_size >= len(entries_to_migrate):
            logger.info(f"Migrated {stats['migrated']}/{len(entries_to_migrate)} entries")

    # Save the FAISS index
    await store.save()

    stats["duration_seconds"] = round(time.time() - start_time, 2)
    logger.info(
        f"Migration complete: {stats['migrated']} migrated, "
        f"{stats['failed']} failed, {stats['skipped']} skipped "
        f"in {stats['duration_seconds']}s"
    )

    return stats


async def _migrate_batch(
    batch: list[dict],
    store: FAISSMemoryStore,
    provider: EmbeddingProvider,
    stats: dict[str, int],
) -> None:
    """Migrate a batch of entries."""
    for entry_data in batch:
        try:
            # Skip entries without content
            if not entry_data.get("content"):
                stats["skipped"] += 1
                continue

            # Create MemoryEntry
            entry = MemoryEntry(
                entry_id=entry_data.get("entry_id"),
                timestamp=datetime.fromisoformat(entry_data["timestamp"])
                if entry_data.get("timestamp")
                else None,
                role=entry_data.get("role", "user"),
                content=entry_data["content"],
                tags=entry_data.get("tags", []),
                permanent=entry_data.get("permanent", False),
                # Note: old embeddings are different dimension, need to re-embed
                embedding=None,
            )

            # Add to store (will generate new embedding)
            await store.add(entry)
            stats["migrated"] += 1

        except Exception as e:
            logger.error(f"Failed to migrate entry {entry_data.get('entry_id', 'unknown')}: {e}")
            stats["failed"] += 1


async def migrate_command(
    jsonl_path: Path | None = None,
    faiss_path: Path | None = None,
    provider_type: str = "local",
    backup: bool = True,
) -> dict[str, Any]:
    """CLI command for migration.

    Args:
        jsonl_path: Path to JSONL file (default: XDG data dir)
        faiss_path: Path for FAISS index (default: XDG data dir /faiss)
        provider_type: "local" or "openai"
        backup: Create backup

    Returns:
        Migration stats
    """
    from src.config import load_config
    from src.embeddings import create_provider
    from src.data_manager import get_memory_dir

    # Default paths
    if jsonl_path is None:
        jsonl_path = get_memory_dir() / "memories.jsonl"
    if faiss_path is None:
        faiss_path = get_memory_dir() / "faiss"

    # Load config and create provider
    config = load_config()
    config.embedding_provider = provider_type
    provider = create_provider(config)

    # Run migration
    return await migrate_jsonl_to_faiss(
        jsonl_path=jsonl_path,
        faiss_path=faiss_path,
        provider=provider,
        backup=backup,
    )


def main() -> None:
    """Entry point for CLI migration command."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate JSONL memories to FAISS")
    parser.add_argument(
        "--jsonl-path",
        type=Path,
        help="Path to memories.jsonl (default: XDG data dir)",
    )
    parser.add_argument(
        "--faiss-path",
        type=Path,
        help="Path for FAISS index (default: XDG data dir /faiss)",
    )
    parser.add_argument(
        "--provider",
        choices=["local", "openai"],
        default="local",
        help="Embedding provider (default: local)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup of JSONL file",
    )

    args = parser.parse_args()

    # Run migration
    stats = asyncio.run(
        migrate_command(
            jsonl_path=args.jsonl_path,
            faiss_path=args.faiss_path,
            provider_type=args.provider,
            backup=not args.no_backup,
        )
    )

    # Print results
    print(f"\nMigration complete:")
    print(f"  Migrated: {stats['migrated']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Duration: {stats['duration_seconds']}s")


if __name__ == "__main__":
    main()
