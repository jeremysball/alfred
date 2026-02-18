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
    ) -> tuple[list[MemoryEntry], dict[str, float], dict[str, float]]:
        """Search memories by semantic similarity with hybrid scoring.

        Args:
            query_embedding: Pre-computed embedding for the query
            memories: List of memories to search (caller loads these)

        Returns:
            Tuple of (results, similarities, scores) where:
            - results: top memories ranked by hybrid score
            - similarities: dict of entry_id -> cosine similarity (0-1)
            - scores: dict of entry_id -> hybrid score (0-1)
        """
        logger.debug(
            f"Searching {len(memories)} memories with min_similarity={self.min_similarity}"
        )

        scored: list[tuple[float, MemoryEntry, float]] = []  # (score, memory, similarity)

        for memory in memories:
            if not memory.embedding:
                continue

            similarity = cosine_similarity(query_embedding, memory.embedding)
            if similarity < self.min_similarity:
                continue

            score = self._hybrid_score(memory, similarity)
            scored.append((score, memory, similarity))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results = [memory for _, memory, _ in scored[: self.context_limit]]
        similarities = {
            memory.entry_id or "": sim for _, memory, sim in scored[: self.context_limit]
        }
        scores = {
            memory.entry_id or "": scr for scr, memory, _ in scored[: self.context_limit]
        }
        logger.info(
            f"Memory search: {len(memories)} total, {len(scored)} scored, {len(results)} returned"
        )
        return results, similarities, scores

    def _hybrid_score(
        self,
        memory: MemoryEntry,
        similarity: float,
    ) -> float:
        """Combine similarity and recency into a single score.

        Weights:
            - Similarity: 0.6 (semantic relevance to query)
            - Recency: 0.4 (newer memories score higher)
        """
        # Recency decay: exp(-age / half_life)
        age_days = (datetime.now() - memory.timestamp).days
        recency = math.exp(-age_days / self.recency_half_life)

        return similarity * 0.6 + recency * 0.4

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
        session_messages: list[tuple[str, str]] | None = None,
    ) -> str:
        """Build full context with relevant memories and session history injected.

        Args:
            query_embedding: Pre-computed query embedding
            memories: All available memories (caller loads these)
            system_prompt: Base system prompt from context files
            session_messages: Optional list of (role, content) tuples from current session

        Returns:
            Combined context string ready for LLM
        """
        logger.debug(f"Building context with {len(memories)} memories available")

        # Search and deduplicate
        relevant, similarities, scores = self.searcher.search(query_embedding, memories)
        relevant = self.searcher.deduplicate(relevant)

        # Build memory section with similarities and scores
        memory_section = self._format_memories(relevant, similarities, scores)

        # Build session history section
        session_section = self._format_session_messages(session_messages or [])

        # Combine parts
        parts = [
            system_prompt,
            memory_section,
            session_section,
            "## CURRENT CONVERSATION\n",
        ]

        context = "\n\n".join(parts)

        # Verify token budget (log warning if exceeded)
        token_count = approximate_tokens(context)
        mem_count = len(relevant)
        sess_count = len(session_messages or [])
        logger.info(
            f"Context: {token_count} tokens ({mem_count} memories, {sess_count} session msg)"
        )

        if token_count > self.token_budget:
            logger.warning(
                f"Context exceeds budget: {token_count} > {self.token_budget} tokens, truncating"
            )
            # Simple truncation: limit memories included
            # More sophisticated: could trim oldest or least relevant
            truncated = self._truncate_to_budget(
                system_prompt, relevant, session_messages or [],
                self.token_budget, similarities, scores
            )
            return truncated

        return context

    def _format_session_messages(self, messages: list[tuple[str, str]]) -> str:
        """Format session messages for context.

        Args:
            messages: List of (role, content) tuples

        Returns:
            Formatted session history section
        """
        if not messages:
            return "## SESSION HISTORY\n\n_No previous messages in this session._"

        lines = ["## SESSION HISTORY\n"]

        for role, content in messages:
            # Capitalize role for display
            display_role = role.capitalize()
            lines.append(f"{display_role}: {content}")

        return "\n".join(lines)

    def _format_memories(
        self,
        memories: list[MemoryEntry],
        similarities: dict[str, float],
        scores: dict[str, float] | None = None,
    ) -> str:
        """Format memories section for prompt with similarity and score."""
        if not memories:
            return "## RELEVANT MEMORIES\n\n_No relevant memories found._"

        lines = ["## RELEVANT MEMORIES\n"]
        scores = scores or {}

        for memory in memories:
            prefix = "User" if memory.role == "user" else "Assistant"
            date = memory.timestamp.strftime("%Y-%m-%d")
            # Truncate long content for prompt efficiency
            content = memory.content[:200]
            if len(memory.content) > 200:
                content += "..."
            # Get similarity and format as percentage
            sim = similarities.get(memory.entry_id or "", 0.0)
            sim_pct = int(sim * 100)
            # Get hybrid score and format as percentage
            scr = scores.get(memory.entry_id or "", 0.0)
            scr_pct = int(scr * 100)
            mid = memory.entry_id
            lines.append(
                f"- [{date}] {prefix}: {content} "
                f"(sim: {sim_pct}%, score: {scr_pct}%, id: {mid})"
            )

        return "\n".join(lines)

    def _truncate_to_budget(
        self,
        system_prompt: str,
        memories: list[MemoryEntry],
        session_messages: list[tuple[str, str]],
        budget: int,
        similarities: dict[str, float] | None = None,
        scores: dict[str, float] | None = None,
    ) -> str:
        """Truncate memories and session messages to fit within token budget."""
        similarities = similarities or {}
        scores = scores or {}
        # Reserve tokens for system prompt, headers, and conversation
        reserved = approximate_tokens(system_prompt) + 300  # Increased for session section
        available = budget - reserved

        if available <= 0:
            # No room for memories at all
            return "\n\n".join(
                [
                    system_prompt,
                    "## CURRENT CONVERSATION\n",
                ]
            )

        # First, include all session messages (they're critical for context)
        session_lines = ["## SESSION HISTORY\n"]
        for role, content in session_messages:
            line = f"{role.capitalize()}: {content}"
            session_lines.append(line)

        session_section = "\n".join(session_lines)
        session_tokens = approximate_tokens(session_section)

        # Reserve space for session messages
        available_for_memories = available - session_tokens - 100  # Buffer

        if available_for_memories <= 0:
            # No room for memories, just return system + session
            return "\n\n".join(
                [
                    system_prompt,
                    session_section,
                    "## CURRENT CONVERSATION\n",
                ]
            )

        # Include memories until budget exhausted
        memory_lines = ["## RELEVANT MEMORIES\n"]
        current_tokens = approximate_tokens("\n".join(memory_lines))

        for memory in memories:
            prefix = "User" if memory.role == "user" else "Assistant"
            date = memory.timestamp.strftime("%Y-%m-%d")
            content = memory.content[:200]
            if len(memory.content) > 200:
                content += "..."
            sim = similarities.get(memory.entry_id or "", 0.0)
            sim_pct = int(sim * 100)
            scr = scores.get(memory.entry_id or "", 0.0)
            scr_pct = int(scr * 100)

            line = (
                f"- [{date}] {prefix}: {content} "
                f"(sim: {sim_pct}%, score: {scr_pct}%, id: {memory.entry_id})"
            )
            line_tokens = approximate_tokens(line)

            if current_tokens + line_tokens > available_for_memories:
                break

            memory_lines.append(line)
            current_tokens += line_tokens

        if len(memory_lines) == 1:
            memory_lines.append("_No memories fit in context window._")

        return "\n\n".join(
            [
                system_prompt,
                "\n".join(memory_lines),
                session_section,
                "## CURRENT CONVERSATION\n",
            ]
        )
