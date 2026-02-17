"""Context file loading and assembly for Alfred."""

import asyncio
from pathlib import Path
from datetime import datetime, timedelta

from src.types import ContextFile, AssembledContext, MemoryEntry
from src.config import Config


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
    def __init__(self, config: Config, cache_ttl: int = 60) -> None:
        self.config = config
        self._cache = ContextCache(ttl_seconds=cache_ttl)
    
    async def load_file(self, name: str, path: Path) -> ContextFile:
        """Load a context file or fail if missing. Uses cache if available."""
        # Check cache first
        cached = self._cache.get(name)
        if cached:
            return cached
        
        if not path.exists():
            raise FileNotFoundError(f"Required context file missing: {path}")
        
        # Run file I/O in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, path.read_text, "utf-8")
        stat = await loop.run_in_executor(None, path.stat)
        
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
            for name, path in self.config.context_files.items()
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
            tools=files["tools"].content,
            memories=memories or [],
            system_prompt=self._build_system_prompt(files),
        )
    
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
        parts = [
            "# AGENTS\n\n" + files["agents"].content,
            "# SOUL\n\n" + files["soul"].content,
            "# USER\n\n" + files["user"].content,
            "# TOOLS\n\n" + files["tools"].content,
        ]
        return "\n\n---\n\n".join(parts)
