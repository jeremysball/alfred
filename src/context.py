"""Context file loading and assembly for Alfred."""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import BaseModel

from src.config import Config
from src.memory import MemoryEntry
from src.placeholders import resolve_all
from src.search import ContextBuilder, MemorySearcher
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
# Note: TOOLS.md is phased out (content moved to SYSTEM.md and USER.md per PRD #102)
CONTEXT_TO_TEMPLATE = {
    "system": "SYSTEM.md",
    "agents": "AGENTS.md",
    "soul": "SOUL.md",
    "user": "USER.md",
}


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


class ContextLoader:
    def __init__(
        self,
        config: Config,
        cache_ttl: int = 60,
        searcher: MemorySearcher | None = None,
    ) -> None:
        self.config = config
        self._cache = ContextCache(ttl_seconds=cache_ttl)
        self._template_manager = TemplateManager(config.workspace_dir)
        self._searcher = searcher
        self._context_builder: ContextBuilder | None = None
        if searcher:
            self._context_builder = ContextBuilder(
                searcher,
                memory_budget=config.memory_budget,
            )

    async def load_file(self, name: str, path: Path) -> ContextFile:
        """Load a context file, auto-creating from template if missing.

        Uses cache if available. Auto-creates missing files from templates
        for known context types (soul, user, tools).
        """
        # Check cache first
        cached = self._cache.get(name)
        if cached:
            return cached

        # Ensure prompts directory exists (for placeholders)
        self._template_manager.ensure_prompts_exist()

        # Auto-create from template if missing
        if not path.exists():
            template_name = CONTEXT_TO_TEMPLATE.get(name)
            if template_name and template_name in TemplateManager.AUTO_CREATE_TEMPLATES:
                logger.info(f"Auto-creating missing context file from template: {name}")
                self._template_manager.ensure_exists(template_name)

        if not path.exists():
            raise FileNotFoundError(f"Required context file missing: {path}")

        # Run file I/O in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, path.read_text, "utf-8")
        stat = await loop.run_in_executor(None, path.stat)

        # Resolve placeholders (file includes {{path}} and colors {color})
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
        tasks = [self.load_file(name, path) for name, path in self.config.context_files.items()]
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
        memories: list[MemoryEntry],
        session_messages: list[tuple[str, str]] | None = None,
        session_messages_with_tools: list | None = None,
    ) -> tuple[str, int]:
        """Assemble context with semantic memory search.

        Uses the MemorySearcher to find and rank relevant memories,
        then builds a complete prompt context with them injected.

        Args:
            query_embedding: Pre-computed embedding of the user's query
            memories: All available memories (caller loads these)
            session_messages: Optional list of (role, content) tuples from session history
            session_messages_with_tools: Optional list of Message objects with tool_calls

        Returns:
            Tuple of (context_string, memories_count) where:
            - context_string: Complete context ready for the LLM
            - memories_count: Number of memories included in context

        Raises:
            RuntimeError: If no MemorySearcher was provided to ContextLoader
        """
        if not self._context_builder:
            raise RuntimeError(
                "MemorySearcher required for assemble_with_search. "
                "Initialize ContextLoader with searcher parameter."
            )

        system_prompt = self._build_system_prompt_sync()
        return self._context_builder.build_context(
            query_embedding=query_embedding,
            memories=memories,
            system_prompt=system_prompt,
            session_messages=session_messages,
            session_messages_with_tools=session_messages_with_tools,
            tool_calls_enabled=getattr(self.config, 'tool_calls_enabled', True),
            tool_calls_max_calls=getattr(self.config, 'tool_calls_max_calls', 5),
            tool_calls_max_tokens=getattr(self.config, 'tool_calls_max_tokens', 2000),
            tool_calls_include_output=getattr(self.config, 'tool_calls_include_output', True),
            tool_calls_include_arguments=getattr(self.config, 'tool_calls_include_arguments', True),
        )

    def _build_system_prompt_sync(self) -> str:
        """Build system prompt from cached files (synchronous version).

        Uses cached files if available, otherwise returns minimal prompt.
        """
        # Try to use cached files
        files: dict[str, ContextFile] = {}
        for name, path in self.config.context_files.items():
            cached = self._cache.get(name)
            if cached:
                files[name] = cached
            elif path.exists():
                # Fallback: load synchronously
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

        if len(files) < 4:
            # Minimal fallback prompt (need system, agents, soul, user)
            return "You are Alfred, a helpful AI assistant."

        return self._build_system_prompt(files)

    def add_context_file(self, name: str, path: Path) -> None:
        """Dynamically add a custom context file."""
        self.config.context_files[name] = path
        self._cache.invalidate(name)

    def remove_context_file(self, name: str) -> None:
        """Remove a context file from loading."""
        self.config.context_files.pop(name, None)
        self._cache.invalidate(name)

    def _build_system_prompt(self, files: dict[str, ContextFile]) -> str:
        """Combine context files into system prompt."""
        # Note: TOOLS.md phased out per PRD #102 (content moved to SYSTEM.md and USER.md)
        parts = [
            "# SYSTEM\n\n" + files["system"].content,
            "# AGENTS\n\n" + files["agents"].content,
            "# SOUL\n\n" + files["soul"].content,
            "# USER\n\n" + files["user"].content,
        ]
        return "\n\n---\n\n".join(parts)
