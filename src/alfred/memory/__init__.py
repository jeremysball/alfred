"""Memory storage backends for Alfred.

Uses SQLite + sqlite-vec for unified storage with vector search.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alfred.config import Config
from alfred.embeddings.provider import EmbeddingProvider
from alfred.memory.base import MemoryEntry, MemoryStore
from alfred.memory.support_memory import (
    ArcBlocker,
    ArcDecision,
    ArcOpenLoop,
    ArcSituation,
    ArcSnapshot,
    ArcTask,
    EvidenceRef,
    GlobalSituation,
    LifeDomain,
    OperationalArc,
    SupportEpisode,
    SupportIntervention,
    SupportInterventionMessageRef,
)
from alfred.memory.support_profile import (
    DEFAULT_SUPPORT_PROFILE_REGISTRY_CATALOG,
    RELATIONAL_REGISTRY_DIMENSIONS,
    SUPPORT_PROFILE_SCHEMA_VERSION,
    SUPPORT_REGISTRY_DIMENSIONS,
    V1_INTERACTION_CONTEXT_IDS,
    SupportProfileDimensionDefinition,
    SupportProfileRegistryCatalog,
    SupportProfileRegistryFamily,
    SupportProfileScope,
    SupportProfileValue,
    get_registry_dimension,
    validate_registry_value,
)

if TYPE_CHECKING:
    from alfred.memory.sqlite_store import SQLiteMemoryStore

# Re-export for compatibility
__all__ = [
    "ArcBlocker",
    "ArcDecision",
    "ArcOpenLoop",
    "ArcSituation",
    "ArcSnapshot",
    "ArcTask",
    "EvidenceRef",
    "GlobalSituation",
    "LifeDomain",
    "MemoryEntry",
    "MemoryStore",
    "OperationalArc",
    "RELATIONAL_REGISTRY_DIMENSIONS",
    "SQLiteMemoryStore",
    "SUPPORT_PROFILE_SCHEMA_VERSION",
    "SUPPORT_REGISTRY_DIMENSIONS",
    "SupportEpisode",
    "SupportIntervention",
    "SupportInterventionMessageRef",
    "SupportProfileDimensionDefinition",
    "SupportProfileRegistryCatalog",
    "SupportProfileRegistryFamily",
    "SupportProfileScope",
    "SupportProfileValue",
    "V1_INTERACTION_CONTEXT_IDS",
    "DEFAULT_SUPPORT_PROFILE_REGISTRY_CATALOG",
    "create_memory_store",
    "get_registry_dimension",
    "validate_registry_value",
]


def __getattr__(name: str) -> object:
    """Lazily expose heavy exports to avoid package-init import cycles."""
    if name == "SQLiteMemoryStore":
        from alfred.memory.sqlite_store import SQLiteMemoryStore

        return SQLiteMemoryStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def create_memory_store(config: Config, embedder: EmbeddingProvider) -> SQLiteMemoryStore:
    """Create SQLite memory store.

    Args:
        config: Application configuration
        embedder: Embedding provider instance

    Returns:
        SQLiteMemoryStore instance
    """
    from alfred.memory.sqlite_store import SQLiteMemoryStore

    return SQLiteMemoryStore(
        config=config,
        embedder=embedder,
    )
