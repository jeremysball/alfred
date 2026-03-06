"""Context file loading and assembly for Alfred."""

import asyncio
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.config import Config
from src.embeddings import cosine_similarity
from src.memory import MemoryEntry
from src.placeholders import resolve_all
from src.storage.sqlite import SQLiteStore
from src.templates import TemplateManager

logger = logging.getLogger(__name__)


class ContextFile(BaseModel):
    """A loaded context file with metadata."""

    name: str
    path: str
    content: str
    last_modified: datetime


class AssembledContext(BaseModel):
    """Complete assembled context for LLM prompt."""

    agents: str
    soul: str
    user: str
    memories: list[MemoryEntry]
    system_prompt: str  # Combined

    model_config = {"arbitrary_types_allowed": True}


# Map context file names to template filenames
CONTEXT_TO_TEMPLATE = {
    "system": "SYSTEM.md",
    "agents": "AGENTS.md",
    "soul": "SOUL.md",
    "user": "USER.md",
}


def approximate_tokens(text: str) -> int:
    """Approximate token count (4 chars ≈ 1 token)."""
    return len(text) // 4


class ContextCache:
    """Simple TTL cache for context files."""

    def __init__(self, ttl_seconds: int = 60) -> None:
        self._cache: dict[str, ContextFile] = {}
        self._timestamps: dict[str, datetime] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> ContextFile | None:
        """Get cached file if not expired."""
        if key not in self._cache:
            return None
        if datetime.now() - self._timestamps[key] > self._ttl:
            del self._cache[key]
            del self._timestamps[key]
            return None
        return self._cache[key]

    def set(self, key: str, value: ContextFile) -> None:
        """Cache a file with timestamp."""
        self._cache[key] = value
        self._timestamps[key] = datetime.now()

    def invalidate(self, key: str) -> None:
        """Remove a file from cache."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

    def clear(self) -> None:
        """Clear all cached files."""
        self._cache.clear()
        self._timestamps.clear()


class ContextBuilder:
    """Build prompt context with relevant memories injected.
    
    Consolidated from src/search.py - now uses SQLiteStore directly.
    """

    def __init__(
        self,
        store: SQLiteStore,
        memory_budget: int = 32000,
        min_similarity: float = 0.7,
        recency_half_life: int = 30,
    ) -> None:
        self.store = store
        self.memory_budget = memory_budget
        self.min_similarity = min_similarity
        self.recency_half_life = recency_half_life

    async def search_memories(
        self,
        query_embedding: list[float],
        top_k: int = 10,
    ) -> tuple[list[MemoryEntry], dict[str, float], dict[str, float]]:
        """Search memories using SQLiteStore with hybrid scoring."""
        results = await self.store.search_memories(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # Get extra for deduplication
        )
        
        # Convert to MemoryEntry objects
        memories = []
        for r in results:
            try:
                entry = MemoryEntry(
                    entry_id=r["entry_id"],
                    content=r["content"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    role=r.get("role", "assistant"),
                    tags=r.get("tags", []),
                    permanent=r.get("permanent", False),
                )
                memories.append(entry)
            except Exception as e:
                logger.warning(f"Failed to parse memory entry: {e}")
                continue
        
        # Apply hybrid scoring
        scored = []
        for memory in memories:
            # Get similarity from search result or compute it
            similarity = r.get("similarity", 0.0)
            if similarity < self.min_similarity:
                continue
            
            score = self._hybrid_score(memory, similarity)
            scored.append((score, memory, similarity))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Deduplicate
        unique = self._deduplicate([m for _, m, _ in scored])
        
        # Build result dicts
        similarities = {m.entry_id: sim for _, m, sim in scored if m in unique}
        scores = {m.entry_id: scr for scr, m, _ in scored if m in unique}
        
        return unique, similarities, scores

    def _hybrid_score(self, memory: MemoryEntry, similarity: float) -> float:
        """Combine similarity and recency into a single score."""
        age_days = (datetime.now() - memory.timestamp).days
        recency = math.exp(-age_days / self.recency_half_life)
        return similarity * 0.6 + recency * 0.4

    def _deduplicate(
        self,
        memories: list[MemoryEntry],
        threshold: float = 0.95,
    ) -> list[MemoryEntry]:
        """Remove near-duplicate memories by embedding similarity."""
        if not memories:
            return []

        unique: list[MemoryEntry] = []
        for memory in memories:
            if not memory.embedding:
                unique.append(memory)
                continue

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

        return unique

    def build_context(
        self,
        query_embedding: list[float],
        memories: list[MemoryEntry],
        system_prompt: str,
        session_messages: list[tuple[str, str]] | None = None,
        session_messages_with_tools: list[Any] | None = None,
        tool_calls_enabled: bool = True,
        tool_calls_max_calls: int = 5,
        tool_calls_max_tokens: int = 2000,
        tool_calls_include_output: bool = True,
        tool_calls_include_arguments: bool = True,
    ) -> tuple[str, int]:
        """Build full context with relevant memories and session history injected."""
        logger.debug(f"Building context with {len(memories)} memories available")

        # Search and deduplicate (async, but called from sync context)
        try:
            loop = asyncio.get_event_loop()
            relevant, similarities, scores = loop.run_until_complete(
                self.search_memories(query_embedding, top_k=10)
            )
        except RuntimeError:
            # No event loop
            relevant, similarities, scores = [], {}, {}

        # Build memory section
        memory_section = self._format_memories(relevant, similarities, scores)

        # Build session history section
        session_section = self._format_session_messages(session_messages or [])

        # Build tool calls section
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
        parts = [system_prompt, memory_section]
        if tool_calls_section:
            parts.append(tool_calls_section)
        parts.extend([session_section, "## CURRENT CONVERSATION\n"])

        context = "\n\n".join(parts)

        # Verify token budget
        token_count = approximate_tokens(context)
        if token_count > self.memory_budget:
            logger.warning(f"Context exceeds budget: {token_count} > {self.memory_budget}")
            truncated, truncated_count = self._truncate_to_budget(
                system_prompt, relevant, session_messages or [], self.memory_budget,
                similarities, scores,
            )
            return truncated, truncated_count

        return context, len(relevant)

    def _format_session_messages(self, messages: list[tuple[str, str]]) -> str:
        """Format session messages for context."""
        if not messages:
            return "## SESSION HISTORY\n\n_No previous messages in this session._"

        lines = ["## SESSION HISTORY\n"]
        for role, content in messages:
            lines.append(f"{role.capitalize()}: {content}")
        return "\n".join(lines)

    def _format_tool_calls(
        self,
        messages: list[Any],
        max_calls: int = 5,
        max_tokens: int = 2000,
        include_output: bool = True,
        include_arguments: bool = True,
    ) -> str:
        """Format tool calls section for context."""
        all_tool_calls = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                all_tool_calls.extend(msg.tool_calls)

        if not all_tool_calls:
            return ""

        tool_calls = all_tool_calls[-max_calls:] if len(all_tool_calls) > max_calls else all_tool_calls

        lines = ["## RECENT TOOL CALLS\n"]
        for i, tc in enumerate(tool_calls, 1):
            status_indicator = "✓" if tc.status == "success" else "✗"
            if include_arguments and tc.arguments:
                args_str = ", ".join(f"{k}={v}" for k, v in tc.arguments.items())
                args_str = args_str[:100]
                tool_line = f"{i}. {status_indicator} {tc.tool_name}: {args_str}"
            else:
                tool_line = f"{i}. {status_indicator} {tc.tool_name}"
            lines.append(tool_line)

            if include_output and tc.output:
                output = tc.output.strip()
                if len(output) > 200:
                    output = output[:200] + "..."
                for output_line in output.split("\n")[:5]:
                    lines.append(f"   {output_line}")

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
            content = memory.content[:200]
            if len(memory.content) > 200:
                content += "..."
            sim = similarities.get(memory.entry_id, 0.0)
            sim_pct = int(sim * 100)
            scr = scores.get(memory.entry_id, 0.0)
            scr_pct = int(scr * 100)
            lines.append(
                f"- [{date}] {prefix}: {content} (sim: {sim_pct}%, score: {scr_pct}%, id: {memory.entry_id})"
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
        reserved = approximate_tokens(system_prompt) + 300
        available = budget - reserved

        if available <= 0:
            return "\n\n".join([system_prompt, "## CURRENT CONVERSATION\n"]), 0

        # Include all session messages
        session_lines = ["## SESSION HISTORY\n"]
        for role, content in session_messages:
            session_lines.append(f"{role.capitalize()}: {content}")
        session_section = "\n".join(session_lines)
        session_tokens = approximate_tokens(session_section)
        available_for_memories = available - session_tokens - 100

        if available_for_memories <= 0:
            return "\n\n".join([system_prompt, session_section, "## CURRENT CONVERSATION\n"]), 0

        # Include memories until budget exhausted
        memory_lines = ["## RELEVANT MEMORIES\n"]
        current_tokens = approximate_tokens("\n".join(memory_lines))

        for memory in memories:
            prefix = "User" if memory.role == "user" else "Assistant"
            date = memory.timestamp.strftime("%Y-%m-%d")
            content = memory.content[:200]
            if len(memory.content) > 200:
                content += "..."
            sim = similarities.get(memory.entry_id, 0.0)
            sim_pct = int(sim * 100)
            scr = scores.get(memory.entry_id, 0.0)
            scr_pct = int(scr * 100)
            line = f"- [{date}] {prefix}: {content} (sim: {sim_pct}%, score: {scr_pct}%, id: {memory.entry_id})"
            line_tokens = approximate_tokens(line)

            if current_tokens + line_tokens > available_for_memories:
                break

            memory_lines.append(line)
            current_tokens += line_tokens

        if len(memory_lines) == 1:
            memory_lines.append("_No memories fit in context window._")

        included_count = len(memory_lines) - 1
        return "\n\n".join([system_prompt, "\n".join(memory_lines), session_section, "## CURRENT CONVERSATION\n"]), included_count


class ContextLoader:
    def __init__(
        self,
        config: Config,
        cache_ttl: int = 60,
        store: SQLiteStore | None = None,
    ) -> None:
        self.config = config
        self._cache = ContextCache(ttl_seconds=cache_ttl)
        self._template_manager = TemplateManager(config.workspace_dir)
        self._store = store
        self._context_builder: ContextBuilder | None = None
        if store:
            self._context_builder = ContextBuilder(
                store,
                memory_budget=config.memory_budget,
            )

    async def load_file(self, name: str, path: Path) -> ContextFile:
        """Load a context file, auto-creating from template if missing."""
        cached = self._cache.get(name)
        if cached:
            return cached

        self._template_manager.ensure_prompts_exist()

        if not path.exists():
            template_name = CONTEXT_TO_TEMPLATE.get(name)
            if template_name and template_name in TemplateManager.AUTO_CREATE_TEMPLATES:
                logger.info(f"Auto-creating missing context file from template: {name}")
                self._template_manager.ensure_exists(template_name)

        if not path.exists():
            raise FileNotFoundError(f"Required context file missing: {path}")

        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, path.read_text, "utf-8")
        stat = await loop.run_in_executor(None, path.stat)
        content = resolve_all(content, self.config.workspace_dir)

        file = ContextFile(
            name=name,
            path=str(path),
            content=content,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
        )

        self._cache.set(name, file)
        return file

    async def load_all(self) -> dict[str, ContextFile]:
        """Load all required context files concurrently."""
        tasks = [
            self.load_file(name, path)
            for name, path in (self.config.context_files or {}).items()
        ]
        files_list = await asyncio.gather(*tasks)
        return {f.name: f for f in files_list}

    async def assemble(self, memories: list[MemoryEntry] | None = None) -> AssembledContext:
        """Assemble complete context for LLM prompt."""
        files = await self.load_all()

        return AssembledContext(
            agents=files["agents"].content,
            soul=files["soul"].content,
            user=files["user"].content,
            memories=memories or [],
            system_prompt=self._build_system_prompt(files),
        )

    def assemble_with_search(
        self,
        query_embedding: list[float],
        memories: list[Any],
        session_messages: list[tuple[str, str]] | None = None,
        session_messages_with_tools: list[Any] | None = None,
    ) -> tuple[str, int]:
        """Assemble context with semantic memory search."""
        if not self._context_builder:
            raise RuntimeError(
                "SQLiteStore required for assemble_with_search. "
                "Initialize ContextLoader with store parameter."
            )

        system_prompt = self._build_system_prompt_sync()
        return self._context_builder.build_context(
            query_embedding=query_embedding,
            memories=memories,
            system_prompt=system_prompt,
            session_messages=session_messages,
            session_messages_with_tools=session_messages_with_tools,
            tool_calls_enabled=getattr(self.config, "tool_calls_enabled", True),
            tool_calls_max_calls=getattr(self.config, "tool_calls_max_calls", 5),
            tool_calls_max_tokens=getattr(self.config, "tool_calls_max_tokens", 2000),
            tool_calls_include_output=getattr(self.config, "tool_calls_include_output", True),
            tool_calls_include_arguments=getattr(self.config, "tool_calls_include_arguments", True),
        )

    def _build_system_prompt_sync(self) -> str:
        """Build system prompt from cached files (synchronous version)."""
        files: dict[str, ContextFile] = {}
        for name, path in (self.config.context_files or {}).items():
            cached = self._cache.get(name)
            if cached:
                files[name] = cached
            elif path.exists():
                try:
                    content = path.read_text("utf-8")
                    stat = path.stat()
                    files[name] = ContextFile(
                        name=name,
                        path=str(path),
                        content=content,
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                    )
                except Exception as e:
                    logger.warning(f"Failed to load context file {name}: {e}")

        return self._build_system_prompt(files)

    def add_context_file(self, name: str, path: Path) -> None:
        """Dynamically add a custom context file."""
        if self.config.context_files is None:
            self.config.context_files = {}
        self.config.context_files[name] = path
        self._cache.invalidate(name)

    def remove_context_file(self, name: str) -> None:
        """Remove a context file from loading."""
        if self.config.context_files is not None:
            self.config.context_files.pop(name, None)
        self._cache.invalidate(name)

    def _build_system_prompt(self, files: dict[str, ContextFile]) -> str:
        """Combine context files into system prompt."""
        parts = []
        for name in ["system", "agents", "soul", "user"]:
            if name in files:
                parts.append(f"# {name.upper()}\n\n{files[name].content}")
        return "\n\n---\n\n".join(parts) if parts else ""
