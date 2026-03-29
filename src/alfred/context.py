"""Context file loading and assembly for Alfred."""

import asyncio
import logging
import math
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from alfred.config import Config
from alfred.context_outcomes import collect_tool_outcome_lines
from alfred.embeddings import cosine_similarity
from alfred.memory import MemoryEntry
from alfred.placeholders import has_volatile_placeholder, resolve_all
from alfred.storage.sqlite import SQLiteStore
from alfred.templates import TemplateManager

if TYPE_CHECKING:
    from alfred.alfred import Alfred

# Runtime import for RuntimeSelfModel (needed for AssembledContext forward reference)
from alfred.self_model import RuntimeSelfModel

logger = logging.getLogger(__name__)


class ContextFileState(StrEnum):
    """State of a loaded context file."""

    ACTIVE = "active"
    BLOCKED = "blocked"


class ContextFile(BaseModel):
    """A loaded context file with metadata."""

    name: str
    path: str
    content: str
    last_modified: datetime
    state: ContextFileState = ContextFileState.ACTIVE
    blocked_reason: str | None = None
    refresh_on_load: bool = False

    def is_blocked(self) -> bool:
        """Return True when the file is blocked from context assembly."""
        return self.state is ContextFileState.BLOCKED


class AssembledContext(BaseModel):
    """Complete assembled context for LLM prompt."""

    agents: str
    tools: str = ""
    soul: str
    user: str
    memories: list[MemoryEntry]
    system_prompt: str  # Combined
    blocked_context_files: list[str] = Field(default_factory=list)
    self_model: "RuntimeSelfModel | None" = None  # Runtime self-awareness

    model_config = {"arbitrary_types_allowed": True}


# Stable order for the managed system prompt sections.
SYSTEM_PROMPT_SECTION_ORDER = ("system", "agents", "tools", "soul", "user")

# Map context file names to template filenames.
CONTEXT_TO_TEMPLATE = {
    "system": "SYSTEM.md",
    "agents": "AGENTS.md",
    "tools": "TOOLS.md",
    "soul": "SOUL.md",
    "user": "USER.md",
}

SYSTEM_PROMPT_SECTION_LABELS = {
    section_name: CONTEXT_TO_TEMPLATE[section_name]
    for section_name in SYSTEM_PROMPT_SECTION_ORDER
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
        workspace_dir: Path | None = None,
    ) -> None:
        self.store = store
        self.memory_budget = memory_budget
        self.min_similarity = min_similarity
        self.recency_half_life = recency_half_life
        self.workspace_dir = workspace_dir or Path.cwd()

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

        # Build similarity lookup from Alfred-facing search results
        similarities_by_id = {r["entry_id"]: r.get("similarity", 0.0) for r in results}

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
            # Get normalized similarity from the search results lookup
            similarity = similarities_by_id.get(memory.entry_id, 0.0)
            # min_similarity compares normalized similarity, not raw backend distance.
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
        """Combine normalized similarity and recency into a single score."""
        now = datetime.now(memory.timestamp.tzinfo) if memory.timestamp.tzinfo else datetime.now()
        age_days = (now - memory.timestamp).days
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

    async def build_context(
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
        started_at = perf_counter()
        session_message_count = len(session_messages or [])
        tool_message_count = len(session_messages_with_tools or [])
        logger.debug(
            "core.context.start available_memories=%s session_messages=%s tool_messages=%s memory_budget=%s",
            len(memories),
            session_message_count,
            tool_message_count,
            self.memory_budget,
        )

        # Search and deduplicate
        relevant, similarities, scores = await self.search_memories(query_embedding, top_k=10)

        # Build memory section
        memory_section = self._format_memories(relevant, similarities, scores)

        # Build session history section, folding derived tool outcomes into the recent context.
        session_section = self._format_session_messages(
            session_messages or [],
            session_messages_with_tools if tool_calls_enabled else [],
            tool_calls_max_calls=tool_calls_max_calls,
            tool_calls_max_tokens=tool_calls_max_tokens,
        )

        # Combine parts
        parts = [system_prompt, memory_section, session_section, "## CURRENT CONVERSATION\n"]

        context = "\n\n".join(parts)

        # Verify token budget
        token_count = approximate_tokens(context)
        if token_count > self.memory_budget:
            truncated, truncated_count = self._truncate_to_budget(
                system_prompt,
                relevant,
                session_messages or [],
                self.memory_budget,
                similarities,
                scores,
                session_messages_with_tools=session_messages_with_tools if tool_calls_enabled else [],
                tool_calls_max_calls=tool_calls_max_calls,
            )
            logger.warning(
                "core.context.truncated memory_budget=%s token_count=%s "
                "truncated_count=%s available_memories=%s session_messages=%s "
                "duration_ms=%.2f",
                self.memory_budget,
                token_count,
                truncated_count,
                len(memories),
                session_message_count,
                (perf_counter() - started_at) * 1000,
            )
            return truncated, truncated_count

        logger.debug(
            "core.context.completed selected_memories=%s session_messages=%s token_count=%s context_chars=%s duration_ms=%.2f",
            len(relevant),
            session_message_count,
            token_count,
            len(context),
            (perf_counter() - started_at) * 1000,
        )
        return context, len(relevant)

    def _format_session_messages(
        self,
        messages: list[tuple[str, str]],
        messages_with_tools: list[Any] | None = None,
        *,
        tool_calls_max_calls: int = 5,
        tool_calls_max_tokens: int = 2000,
        include_empty_placeholder: bool = True,
    ) -> str:
        """Format session messages for context."""
        if not messages and not messages_with_tools:
            if include_empty_placeholder:
                return "## SESSION HISTORY\n\n_No previous messages in this session._"
            return ""

        lines = ["## SESSION HISTORY\n"]
        for role, content in messages:
            lines.append(f"{role.capitalize()}: {content}")

        max_output_chars = min(120, max(16, tool_calls_max_tokens * 4))
        tool_outcomes = collect_tool_outcome_lines(
            messages_with_tools,
            max_calls=tool_calls_max_calls,
            workspace_dir=self.workspace_dir,
            max_output_chars=max_output_chars,
        )
        if tool_outcomes:
            lines.append("")
            lines.append("Tool outcomes:")
            for outcome in tool_outcomes:
                lines.append(f"- {outcome}")

        return "\n".join(lines)

    def _select_session_messages_for_budget(
        self,
        messages: list[tuple[str, str]],
        messages_with_tools: list[Any] | None,
        budget: int,
        *,
        tool_calls_max_calls: int = 5,
        tool_calls_max_tokens: int = 2000,
    ) -> str:
        """Return the newest session message suffix that fits within budget."""
        if budget <= 0:
            return ""

        tool_messages = list(messages_with_tools or [])
        selected_count = len(messages) if messages else len(tool_messages)
        if selected_count == 0:
            return ""

        while selected_count > 0:
            candidate_messages = messages[-selected_count:] if messages else []
            candidate_tools = tool_messages[-selected_count:] if tool_messages else []
            candidate_section = self._format_session_messages(
                candidate_messages,
                candidate_tools,
                tool_calls_max_calls=tool_calls_max_calls,
                tool_calls_max_tokens=tool_calls_max_tokens,
                include_empty_placeholder=False,
            )
            if approximate_tokens(candidate_section) <= budget:
                return candidate_section
            selected_count -= 1

        return ""

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
            entry_id = memory.entry_id
            line = f"- [{date}] {prefix}: {content} (sim: {sim_pct}%, score: {scr_pct}%, id: {entry_id})"
            lines.append(line)

        return "\n".join(lines)

    def _truncate_to_budget(
        self,
        system_prompt: str,
        memories: list[MemoryEntry],
        session_messages: list[tuple[str, str]],
        budget: int,
        similarities: dict[str, float] | None = None,
        scores: dict[str, float] | None = None,
        session_messages_with_tools: list[Any] | None = None,
        tool_calls_max_calls: int = 5,
        tool_calls_max_tokens: int = 2000,
    ) -> tuple[str, int]:
        """Truncate memories and session messages to fit within token budget."""
        similarities = similarities or {}
        scores = scores or {}
        footer = "## CURRENT CONVERSATION\n"

        if approximate_tokens(system_prompt) + approximate_tokens(footer) >= budget:
            return "\n\n".join([system_prompt, footer]), 0

        selected_memories: list[MemoryEntry] = []
        memory_section = ""
        for memory in memories:
            candidate_memories = selected_memories + [memory]
            candidate_memory_section = self._format_memories(candidate_memories, similarities, scores)
            candidate_parts = [system_prompt, candidate_memory_section, footer]
            candidate_context = "\n\n".join(part for part in candidate_parts if part)
            if approximate_tokens(candidate_context) <= budget:
                selected_memories = candidate_memories
                memory_section = candidate_memory_section
            else:
                break

        base_parts = [system_prompt]
        if memory_section:
            base_parts.append(memory_section)
        base_parts.append(footer)
        remaining_budget = budget - approximate_tokens("\n\n".join(base_parts))
        session_section = self._select_session_messages_for_budget(
            session_messages,
            session_messages_with_tools if session_messages_with_tools is not None else [],
            remaining_budget,
            tool_calls_max_calls=tool_calls_max_calls,
            tool_calls_max_tokens=tool_calls_max_tokens,
        )

        parts = [system_prompt]
        if memory_section:
            parts.append(memory_section)
        if session_section:
            parts.append(session_section)
        parts.append(footer)

        return "\n\n".join(parts), len(selected_memories)


class ContextLoader:
    def __init__(
        self,
        config: Config,
        cache_ttl: int = 60,
        cache_dir: Path | None = None,
        store: SQLiteStore | None = None,
    ) -> None:
        self.config = config
        self._cache = ContextCache(ttl_seconds=cache_ttl)
        self._template_manager = TemplateManager(config.workspace_dir, cache_dir=cache_dir)
        self._store = store
        self._context_builder: ContextBuilder | None = None
        self._blocked_context_files: set[str] = set()
        self._disabled_sections: set[str] = set()  # Track disabled context sections
        if store:
            self._context_builder = ContextBuilder(
                store,
                memory_budget=config.memory_budget,
                workspace_dir=config.workspace_dir,
            )

    def toggle_section(self, name: str, enabled: bool) -> bool:
        """Enable or disable a context section.

        Args:
            name: The context section name (e.g., 'AGENTS', 'SOUL', 'TOOLS')
            enabled: Whether the section should be enabled

        Returns:
            True if the section state was changed, False otherwise
        """
        upper_name = name.upper()
        if enabled:
            if upper_name in self._disabled_sections:
                self._disabled_sections.discard(upper_name)
                logger.info(f"Context section '{upper_name}' enabled")
                return True
        else:
            if upper_name not in self._disabled_sections:
                self._disabled_sections.add(upper_name)
                logger.info(f"Context section '{upper_name}' disabled")
                return True
        return False

    def get_disabled_sections(self) -> list[str]:
        """Return list of disabled context sections."""
        return sorted(self._disabled_sections)

    def is_section_enabled(self, name: str) -> bool:
        """Check if a context section is enabled."""
        return name.upper() not in self._disabled_sections

    def get_blocked_context_files(self) -> list[str]:
        """Return blocked managed context files in stable order."""
        return sorted(self._blocked_context_files)

    def _record_blocked_context_file(self, name: str) -> None:
        """Remember that a managed context file is blocked."""
        self._blocked_context_files.add(name)

    def _clear_blocked_context_file(self, name: str) -> None:
        """Forget a blocked context file once it becomes usable again."""
        self._blocked_context_files.discard(name)

    def _make_blocked_context_file(
        self,
        name: str,
        path: Path,
        reason: str,
        last_modified: datetime | None = None,
    ) -> ContextFile:
        """Build a blocked context file placeholder."""
        return ContextFile(
            name=name,
            path=str(path),
            content="",
            last_modified=last_modified or datetime.now(),
            state=ContextFileState.BLOCKED,
            blocked_reason=reason,
        )

    def _refresh_context_file(self, file: ContextFile) -> ContextFile:
        """Render volatile placeholders for a cached context file."""
        if not file.refresh_on_load:
            return file

        content = resolve_all(file.content, self.config.workspace_dir)
        return file.model_copy(update={"content": content})

    def _reconcile_template(self, name: str) -> None:
        """Reconcile a context file with its managed template if supported."""
        template_name = CONTEXT_TO_TEMPLATE.get(name)
        if template_name is None or template_name not in TemplateManager.AUTO_CREATE_TEMPLATES:
            return

        try:
            # Preserve user-customized files to avoid overwriting their changes
            self._template_manager.reconcile_template(template_name, preserve={"USER.md", "SOUL.md", "CUSTOM.md"})
        except Exception as exc:
            logger.warning(f"Failed to reconcile template {template_name}: {exc}")

    async def load_file(self, name: str, path: Path) -> ContextFile:
        """Load a context file, auto-creating from template if missing."""
        template_name = CONTEXT_TO_TEMPLATE.get(name)
        is_managed_template = template_name in TemplateManager.AUTO_CREATE_TEMPLATES if template_name else False
        sync_record = self._template_manager.get_sync_record(template_name) if is_managed_template and template_name is not None else None

        if sync_record is not None and sync_record.is_conflicted() and not path.exists():
            blocked = self._make_blocked_context_file(
                name=name,
                path=path,
                reason=f"Conflicted managed template {template_name} is blocked",
                last_modified=sync_record.updated_at,
            )
            self._record_blocked_context_file(name)
            return blocked

        cached = self._cache.get(name)
        if cached is not None and (not is_managed_template or sync_record is None or not sync_record.is_conflicted()):
            return self._refresh_context_file(cached)

        self._template_manager.ensure_prompts_exist()
        self._reconcile_template(name)

        if is_managed_template and template_name is not None:
            sync_record = self._template_manager.get_sync_record(template_name)
            if sync_record is not None and sync_record.is_conflicted():
                last_modified = sync_record.updated_at
                if path.exists():
                    loop = asyncio.get_running_loop()
                    try:
                        stat = await loop.run_in_executor(None, path.stat)
                        last_modified = datetime.fromtimestamp(stat.st_mtime)
                    except Exception:
                        pass
                blocked = self._make_blocked_context_file(
                    name=name,
                    path=path,
                    reason=f"Conflicted managed template {template_name} is blocked",
                    last_modified=last_modified,
                )
                self._record_blocked_context_file(name)
                return blocked

        if not path.exists() and is_managed_template and template_name:
            logger.info(f"Auto-creating missing context file from template: {name}")
            self._template_manager.ensure_exists(template_name)

        if not path.exists():
            raise FileNotFoundError(f"Required context file missing: {path}")

        loop = asyncio.get_running_loop()
        raw_content = await loop.run_in_executor(None, path.read_text, "utf-8")
        stat = await loop.run_in_executor(None, path.stat)
        static_content = resolve_all(raw_content, self.config.workspace_dir, resolve_volatile=False)
        refresh_on_load = has_volatile_placeholder(static_content)

        cached_file = ContextFile(
            name=name,
            path=str(path),
            content=static_content,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            state=ContextFileState.ACTIVE,
            refresh_on_load=refresh_on_load,
        )

        self._clear_blocked_context_file(name)
        self._cache.set(name, cached_file)
        return self._refresh_context_file(cached_file)

    async def load_all(self) -> dict[str, ContextFile]:
        """Load all required context files concurrently.

        Filters out disabled sections.
        """
        files = self.config.context_files or {}
        # Filter out disabled sections
        enabled_files = {name: path for name, path in files.items() if name.upper() not in self._disabled_sections}
        tasks = [self.load_file(name, path) for name, path in enabled_files.items()]
        files_list = await asyncio.gather(*tasks)
        return {f.name: f for f in files_list}

    def _blocked_context_files_for(self, files: dict[str, ContextFile]) -> list[str]:
        """Return blocked context file names from a loaded file set."""
        return sorted(name for name, file in files.items() if file.is_blocked())

    def _context_file_content(self, files: dict[str, ContextFile], name: str) -> str:
        """Return active content for a loaded context file or an empty string."""
        file = files.get(name)
        if file is None or file.is_blocked():
            return ""
        return file.content

    async def assemble(self, memories: list[MemoryEntry] | None = None) -> AssembledContext:
        """Assemble complete context for LLM prompt."""
        files = await self.load_all()
        blocked_context_files = self._blocked_context_files_for(files)

        return AssembledContext(
            agents=self._context_file_content(files, "agents"),
            tools=self._context_file_content(files, "tools"),
            soul=self._context_file_content(files, "soul"),
            user=self._context_file_content(files, "user"),
            memories=memories or [],
            system_prompt=self._build_system_prompt(files),
            blocked_context_files=blocked_context_files,
        )

    async def assemble_with_self_model(
        self,
        alfred: "Alfred",
        memories: list[MemoryEntry] | None = None,
    ) -> AssembledContext:
        """Assemble context with runtime self-model included.

        Builds a fresh self-model snapshot from Alfred's current state
        and includes it in the assembled context.

        Args:
            alfred: The Alfred instance to build self-model from
            memories: Optional pre-loaded memories to include

        Returns:
            AssembledContext with self_model populated
        """
        from alfred.self_model import build_runtime_self_model

        logger.debug("assemble_with_self_model: starting context assembly with self-model")

        files = await self.load_all()
        blocked_context_files = self._blocked_context_files_for(files)

        # Build self-model from current Alfred state
        logger.debug("assemble_with_self_model: building self-model from Alfred state")
        self_model = build_runtime_self_model(alfred)
        logger.debug(
            "assemble_with_self_model: self-model built - interface=%s, tools=%d, memories=%d",
            self_model.runtime.interface.value if self_model.runtime.interface else None,
            len(self_model.capabilities.tools_available),
            self_model.context_pressure.memory_count,
        )

        # Build system prompt with self-model appended
        base_prompt = self._build_system_prompt(files)
        self_model_section = self_model.to_prompt_section()
        system_prompt = f"{base_prompt}\n\n---\n\n{self_model_section}"
        logger.debug(
            "assemble_with_self_model: system prompt assembled, length=%d chars, self_model_section_length=%d chars",
            len(system_prompt),
            len(self_model_section),
        )

        return AssembledContext(
            agents=self._context_file_content(files, "agents"),
            tools=self._context_file_content(files, "tools"),
            soul=self._context_file_content(files, "soul"),
            user=self._context_file_content(files, "user"),
            memories=memories or [],
            system_prompt=system_prompt,
            blocked_context_files=blocked_context_files,
            self_model=self_model,
        )

    async def assemble_with_search(
        self,
        query_embedding: list[float],
        memories: list[Any],
        session_messages: list[tuple[str, str]] | None = None,
        session_messages_with_tools: list[Any] | None = None,
        alfred: "Alfred | None" = None,
    ) -> tuple[str, int]:
        """Assemble context with semantic memory search.

        Args:
            query_embedding: Embedding vector for semantic search
            memories: Available memories to include
            session_messages: Current session message history
            session_messages_with_tools: Session messages with tool calls
            alfred: Optional Alfred instance to include self-model

        Returns:
            Tuple of (system_prompt, memories_count)
        """
        if not self._context_builder:
            raise RuntimeError("SQLiteStore required for assemble_with_search. Initialize ContextLoader with store parameter.")

        files = await self.load_all()
        system_prompt = self._build_system_prompt(files)
        logger.debug("assemble_with_search: base system prompt built, length=%d chars", len(system_prompt))

        # Include self-model if Alfred instance provided
        if alfred is not None:
            from alfred.self_model import build_runtime_self_model

            logger.debug("assemble_with_search: building self-model for search context")
            self_model = build_runtime_self_model(alfred)
            self_model_section = self_model.to_prompt_section()
            system_prompt = f"{system_prompt}\n\n---\n\n{self_model_section}"
            logger.debug(
                "assemble_with_search: self-model appended - interface=%s, tools=%d, prompt_length=%d chars",
                self_model.runtime.interface.value if self_model.runtime.interface else None,
                len(self_model.capabilities.tools_available),
                len(system_prompt),
            )
        else:
            logger.debug("assemble_with_search: no Alfred instance provided, self-model skipped")

        return await self._context_builder.build_context(
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
        """Combine active context files into system prompt."""
        parts = []
        for name in SYSTEM_PROMPT_SECTION_ORDER:
            file = files.get(name)
            if file is None or file.is_blocked():
                continue
            parts.append(f"# {name.upper()}\n\n{file.content}")
        return "\n\n---\n\n".join(parts) if parts else ""


# Rebuild AssembledContext to resolve forward references
AssembledContext.model_rebuild()
