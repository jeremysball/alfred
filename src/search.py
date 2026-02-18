"""Vector search and context building for semantic memory retrieval."""

import logging
import math
from datetime import datetime

from src.embeddings import cosine_similarity
from src.types import MemoryEntry

logger = logging.getLogger(__name__)


def approximate_tokens(text: str) -> int:
    """Approximate token count (4 chars ≈ 1 token)."""
    return len(text) // 4


class MemorySearcher:
    """Search and rank memories by semantic similarity with hybrid scoring."""

    def __init__(
        self,
        context_limit: int = 20,
        min_similarity: float = 0.7,
        recency_half_life: int = 30,  # days
    ) -> None:
        self.context_limit = context_limit
        self.min_similarity = min_similarity
        self.recency_half_life = recency_half_life

    def search(
        self,
        query_embedding: list[float],
        memories: list[MemoryEntry],
    ) -> list[MemoryEntry]:
        """Search memories by semantic similarity with hybrid scoring.

        Args:
            query_embedding: Pre-computed embedding for the query
            memories: List of memories to search (caller loads these)

        Returns:
            Top memories ranked by hybrid score (similarity + recency + importance)
        """
        logger.debug(
            f"Searching {len(memories)} memories with min_similarity={self.min_similarity}"
        )

        scored: list[tuple[float, MemoryEntry]] = []

        for memory in memories:
            if not memory.embedding:
                continue

            similarity = cosine_similarity(query_embedding, memory.embedding)
            if similarity < self.min_similarity:
                continue

            score = self._hybrid_score(memory, similarity)
            scored.append((score, memory))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results = [memory for _, memory in scored[: self.context_limit]]
        logger.info(
            f"Memory search: {len(memories)} total, {len(scored)} scored, {len(results)} returned"
        )
        return results

    def _hybrid_score(
        self,
        memory: MemoryEntry,
        similarity: float,
    ) -> float:
        """Combine similarity, recency, and importance into a single score.

        Weights:
            - Similarity: 0.5 (semantic relevance to query)
            - Recency: 0.3 (newer memories score higher)
            - Importance: 0.2 (user/marked importance)
        """
        # Recency decay: exp(-age / half_life)
        age_days = (datetime.now() - memory.timestamp).days
        recency = math.exp(-age_days / self.recency_half_life)

        return similarity * 0.5 + recency * 0.3 + memory.importance * 0.2

    def deduplicate(
        self,
        memories: list[MemoryEntry],
        threshold: float = 0.95,
    ) -> list[MemoryEntry]:
        """Remove near-duplicate memories by embedding similarity.

        Args:
            memories: Ranked list of memories
            threshold: Cosine similarity threshold for duplicates (default 0.95)

        Returns:
            List with duplicates removed, preserving order
        """
        if not memories:
            return []

        logger.debug(f"Deduplicating {len(memories)} memories with threshold={threshold}")

        unique: list[MemoryEntry] = []

        for memory in memories:
            if not memory.embedding:
                # Keep memories without embeddings (can't compare)
                unique.append(memory)
                continue

            # Check if similar to any already-kept memory
            is_duplicate = False
            for kept in unique:
                if not kept.embedding:
                    continue

                sim = cosine_similarity(memory.embedding, kept.embedding)
                if sim > threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(memory)

        removed = len(memories) - len(unique)
        if removed > 0:
            logger.info(f"Deduplication removed {removed} memories ({len(unique)} remaining)")
        return unique


class ContextBuilder:
    """Build prompt context with relevant memories injected."""

    def __init__(
        self,
        searcher: MemorySearcher,
        token_budget: int = 8000,
    ) -> None:
        self.searcher = searcher
        self.token_budget = token_budget

    def build_context(
        self,
        query_embedding: list[float],
        memories: list[MemoryEntry],
        system_prompt: str,
    ) -> str:
        """Build full context with relevant memories injected.

        Args:
            query_embedding: Pre-computed query embedding
            memories: All available memories (caller loads these)
            system_prompt: Base system prompt from context files

        Returns:
            Combined context string ready for LLM
        """
        logger.debug(f"Building context with {len(memories)} memories available")

        # Search and deduplicate
        relevant = self.searcher.search(query_embedding, memories)
        relevant = self.searcher.deduplicate(relevant)

        # Build memory section
        memory_section = self._format_memories(relevant)

        # Combine parts
        parts = [
            system_prompt,
            memory_section,
            "## CURRENT CONVERSATION\n",
        ]

        context = "\n\n".join(parts)

        # Verify token budget (log warning if exceeded)
        token_count = approximate_tokens(context)
        logger.info(f"Context built: {token_count} tokens ({len(relevant)} memories injected)")

        if token_count > self.token_budget:
            logger.warning(
                f"Context exceeds budget: {token_count} > {self.token_budget} tokens, truncating"
            )
            # Simple truncation: limit memories included
            # More sophisticated: could trim oldest or least relevant
            truncated = self._truncate_to_budget(system_prompt, relevant, self.token_budget)
            return truncated

        return context

    def _format_memories(self, memories: list[MemoryEntry]) -> str:
        """Format memories section for prompt."""
        if not memories:
            return "## RELEVANT MEMORIES\n\n_No relevant memories found._"

        lines = ["## RELEVANT MEMORIES\n"]

        for memory in memories:
            prefix = "User" if memory.role == "user" else "Assistant"
            date = memory.timestamp.strftime("%Y-%m-%d")
            # Truncate long content for prompt efficiency
            content = memory.content[:200]
            if len(memory.content) > 200:
                content += "..."
            lines.append(f"- [{date}] {prefix}: {content}")

        return "\n".join(lines)

    def _truncate_to_budget(
        self,
        system_prompt: str,
        memories: list[MemoryEntry],
        budget: int,
    ) -> str:
        """Truncate memories to fit within token budget."""
        # Reserve tokens for system prompt, headers, and conversation
        reserved = approximate_tokens(system_prompt) + 200
        available = budget - reserved

        if available <= 0:
            # No room for memories at all
            return "\n\n".join(
                [
                    system_prompt,
                    "## CURRENT CONVERSATION\n",
                ]
            )

        # Include memories until budget exhausted
        lines = ["## RELEVANT MEMORIES\n"]
        current_tokens = approximate_tokens("\n".join(lines))

        for memory in memories:
            prefix = "User" if memory.role == "user" else "Assistant"
            date = memory.timestamp.strftime("%Y-%m-%d")
            content = memory.content[:200]
            if len(memory.content) > 200:
                content += "..."

            line = f"- [{date}] {prefix}: {content}"
            line_tokens = approximate_tokens(line)

            if current_tokens + line_tokens > available:
                break

            lines.append(line)
            current_tokens += line_tokens

        if len(lines) == 1:
            lines.append("_No memories fit in context window._")

        return "\n\n".join(
            [
                system_prompt,
                "\n".join(lines),
                "## CURRENT CONVERSATION\n",
            ]
        )
