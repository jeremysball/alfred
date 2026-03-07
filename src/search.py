"""Vector search and context building for semantic memory retrieval."""

import logging
import math
from datetime import datetime

from src.embeddings import cosine_similarity
from src.memory import MemoryEntry
from src.session_storage import SessionStorage

logger = logging.getLogger(__name__)


def approximate_tokens(text: str) -> int:
    """Approximate token count (4 chars ≈ 1 token)."""
    return len(text) // 4


class MemorySearcher:
    """Search and rank memories by semantic similarity with hybrid scoring."""

    def __init__(
        self,
        min_similarity: float = 0.7,
        recency_half_life: int = 30,  # days
    ) -> None:
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

        results = [memory for _, memory, _ in scored]
        similarities = {memory.entry_id or "": sim for _, memory, sim in scored}
        scores = {memory.entry_id or "": scr for scr, memory, _ in scored}
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
        memory_budget: int = 32000,
    ) -> None:
        self.searcher = searcher
        self.memory_budget = memory_budget

    def build_context(
        self,
        query_embedding: list[float],
        memories: list[MemoryEntry],
        system_prompt: str,
        session_messages: list[tuple[str, str]] | None = None,
        session_messages_with_tools: list | None = None,
        tool_calls_enabled: bool = True,
        tool_calls_max_calls: int = 5,
        tool_calls_max_tokens: int = 2000,
        tool_calls_include_output: bool = True,
        tool_calls_include_arguments: bool = True,
    ) -> tuple[str, int]:
        """Build full context with relevant memories and session history injected.

        Args:
            query_embedding: Pre-computed query embedding
            memories: All available memories (caller loads these)
            system_prompt: Base system prompt from context files
            session_messages: Optional list of (role, content) tuples from current session
            session_messages_with_tools: Optional list of Message objects with tool_calls
            tool_calls_enabled: Whether to include tool calls in context
            tool_calls_max_calls: Maximum number of tool calls to include
            tool_calls_max_tokens: Maximum tokens for tool calls section
            tool_calls_include_output: Whether to include tool output
            tool_calls_include_arguments: Whether to include tool arguments

        Returns:
            Tuple of (context_string, memories_count) where:
            - context_string: Combined context ready for LLM
            - memories_count: Number of memories included in context
        """
        logger.debug(f"Building context with {len(memories)} memories available")

        # Search and deduplicate
        relevant, similarities, scores = self.searcher.search(query_embedding, memories)
        relevant = self.searcher.deduplicate(relevant)

        # Build memory section with similarities and scores
        memory_section = self._format_memories(relevant, similarities, scores)

        # Build session history section
        session_section = self._format_session_messages(session_messages or [])

        # Build tool calls section (if enabled and messages provided)
        tool_calls_section = ""
        if tool_calls_enabled and session_messages_with_tools:
            tool_calls_section = self._format_tool_calls(
                session_messages_with_tools,
                max_calls=tool_calls_max_calls,
                max_tokens=tool_calls_max_tokens,
                include_output=tool_calls_include_output,
                include_arguments=tool_calls_include_arguments,
            )

        # Combine parts
        parts = [
            system_prompt,
            memory_section,
        ]

        # Add tool calls section if present
        if tool_calls_section:
            parts.append(tool_calls_section)

        parts.extend(
            [
                session_section,
                "## CURRENT CONVERSATION\n",
            ]
        )

        context = "\n\n".join(parts)

        # Verify token budget (log warning if exceeded)
        token_count = approximate_tokens(context)
        mem_count = len(relevant)
        sess_count = len(session_messages or [])
        tool_calls_count = len(
            [
                m
                for m in (session_messages_with_tools or [])
                if hasattr(m, "tool_calls") and m.tool_calls
            ]
        )
        logger.info(
            f"Context: {token_count} tokens ({mem_count} memories, {sess_count} "
            f"session msg, {tool_calls_count} with tool calls)"
        )

        if token_count > self.memory_budget:
            logger.warning(
                f"Context exceeds budget: {token_count} > {self.memory_budget} tokens, truncating"
            )
            # Simple truncation: limit memories included
            # More sophisticated: could trim oldest or least relevant
            truncated, truncated_count = self._truncate_to_budget(
                system_prompt,
                relevant,
                session_messages or [],
                self.memory_budget,
                similarities,
                scores,
            )
            return truncated, truncated_count

        return context, mem_count

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

    def _format_tool_calls(
        self,
        messages: list,
        max_calls: int = 5,
        max_tokens: int = 2000,
        include_output: bool = True,
        include_arguments: bool = True,
    ) -> str:
        """Format tool calls section for context.

        Args:
            messages: List of Message objects (may have tool_calls attribute)
            max_calls: Maximum number of tool calls to include
            max_tokens: Maximum tokens for tool calls section
            include_output: Whether to include tool output
            include_arguments: Whether to include tool arguments

        Returns:
            Formatted tool calls section, or empty string if no tool calls
        """
        # Collect all tool calls from messages
        all_tool_calls = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    all_tool_calls.append(tc)

        if not all_tool_calls:
            return ""

        # Limit to max_calls (take most recent = last ones)
        if len(all_tool_calls) > max_calls:
            tool_calls = all_tool_calls[-max_calls:]
        else:
            tool_calls = all_tool_calls

        lines = ["## RECENT TOOL CALLS\n"]

        for i, tc in enumerate(tool_calls, 1):
            # Format tool call info
            status_indicator = "✓" if tc.status == "success" else "✗"

            # Format arguments
            if include_arguments and tc.arguments:
                # Format as key=value pairs for readability
                args_str = ", ".join(f"{k}={v}" for k, v in tc.arguments.items())
                args_str = args_str[:100]  # Limit arg length
                tool_line = f"{i}. {status_indicator} {tc.tool_name}: {args_str}"
            else:
                tool_line = f"{i}. {status_indicator} {tc.tool_name}"

            lines.append(tool_line)

            # Include output if enabled
            if include_output and tc.output:
                output = tc.output.strip()
                # Truncate long output
                if len(output) > 200:
                    output = output[:200] + "..."
                # Indent output
                for output_line in output.split("\n")[:5]:  # Limit to 5 lines
                    lines.append(f"   {output_line}")

        result = "\n".join(lines)

        # Check token budget and truncate if needed
        if approximate_tokens(result) > max_tokens:
            # Simple truncation: keep header and as many calls as fit
            header = "## RECENT TOOL CALLS\n"
            header_tokens = approximate_tokens(header)
            available_tokens = max_tokens - header_tokens

            truncated_lines = [header]
            current_tokens = 0

            for line in lines[1:]:  # Skip header, already added
                line_tokens = approximate_tokens(line)
                if current_tokens + line_tokens > available_tokens:
                    truncated_lines.append("   ... (truncated)")
                    break
                truncated_lines.append(line)
                current_tokens += line_tokens

            result = "\n".join(truncated_lines)

        return result

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

            content = memory.content[:200]
            if len(memory.content) > 200:
                content += "..."

            sim = similarities.get(memory.entry_id or "", 0.0)
            sim_pct = int(sim * 100)
            # Get hybrid score and format as percentage
            scr = scores.get(memory.entry_id or "", 0.0)
            scr_pct = int(scr * 100)
            mid = memory.entry_id
            lines.append(
                f"- [{date}] {prefix}: {content} (sim: {sim_pct}%, score: {scr_pct}%, id: {mid})"
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
    ) -> tuple[str, int]:
        """Truncate memories and session messages to fit within token budget."""
        similarities = similarities or {}
        scores = scores or {}
        # Reserve tokens for system prompt, headers, and conversation
        reserved = approximate_tokens(system_prompt) + 300  # Increased for session section
        available = budget - reserved

        if available <= 0:
            # No room for memories at all
            return (
                "\n\n".join(
                    [
                        system_prompt,
                        "## CURRENT CONVERSATION\n",
                    ]
                ),
                0,
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
            return (
                "\n\n".join(
                    [
                        system_prompt,
                        session_section,
                        "## CURRENT CONVERSATION\n",
                    ]
                ),
                0,
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

        # Count actual memories included (excluding header line)
        included_count = len(memory_lines) - 1

        return (
            "\n\n".join(
                [
                    system_prompt,
                    "\n".join(memory_lines),
                    session_section,
                    "## CURRENT CONVERSATION\n",
                ]
            ),
            included_count,
        )


async def search_session_summaries(
    query_embedding: list[float],
    storage: SessionStorage,
    top_k: int = 5,
    min_similarity: float = 0.3,
) -> list[dict]:
    """Search session summaries by embedding similarity.

    Args:
        query_embedding: Pre-computed embedding for the query
        storage: SessionStorage instance for accessing summaries
        top_k: Maximum number of results to return
        min_similarity: Minimum similarity threshold (0-1)

    Returns:
        List of dicts with keys:
        - session_id: str
        - summary: SessionSummary
        - similarity: float
        Sorted by similarity descending.
    """
    logger.debug(
        "Searching session summaries with top_k=%s, min_similarity=%s",
        top_k,
        min_similarity,
    )

    session_ids = storage.list_sessions()
    logger.debug("Found %d sessions to search", len(session_ids))

    scored: list[tuple[float, str, object]] = []  # (similarity, session_id, summary)

    for session_id in session_ids:
        try:
            summary = await storage.get_summary(session_id)
            if summary is None:
                logger.debug("Session %s has no summary, skipping", session_id)
                continue

            if not summary.embedding:
                logger.debug("Session %s summary has no embedding, skipping", session_id)
                continue

            similarity = cosine_similarity(query_embedding, summary.embedding)
            if similarity < min_similarity:
                logger.debug(
                    "Session %s similarity %.3f below threshold %.3f, skipping",
                    session_id,
                    similarity,
                    min_similarity,
                )
                continue

            scored.append((similarity, session_id, summary))

        except Exception as e:
            logger.warning("Error loading summary for session %s: %s", session_id, e)
            continue

    # Sort by similarity descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top_k
    top_results = scored[:top_k]

    results = [
        {
            "session_id": session_id,
            "summary": summary,
            "similarity": similarity,
        }
        for similarity, session_id, summary in top_results
    ]

    logger.info(
        "Session summary search: %d total sessions, %d matched, %d returned",
        len(session_ids),
        len(scored),
        len(results),
    )
    return results
