"""Memory system for persistent agent context."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages daily memory files and long-term MEMORY.md."""

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.memory_dir = workspace_dir / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.notes_dir = workspace_dir / "notes"
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    def get_daily_memory_path(self, date: Optional[datetime] = None) -> Path:
        """Get path for daily memory file."""
        date = date or datetime.now()
        return self.memory_dir / f"{date.strftime('%Y-%m-%d')}.md"

    async def append_to_daily(
        self,
        content: str,
        section: str = "Notes",
        date: Optional[datetime] = None
    ) -> None:
        """Append note to daily memory file."""
        path = self.get_daily_memory_path(date)

        # Create file with header if doesn't exist
        if not path.exists():
            date_str = (date or datetime.now()).strftime('%Y-%m-%d')
            path.write_text(f"# {date_str}\n\n## {section}\n\n")

        # Append content
        with open(path, 'a') as f:
            f.write(f"- {content}\n")

        logger.info(f"[MEMORY] Appended to {path.name}: {content[:50]}...")

    def get_all_memories(self) -> list[Path]:
        """Get all daily memory files except today."""
        paths = []
        today = datetime.now().strftime('%Y-%m-%d')

        for path in sorted(self.memory_dir.glob("*.md")):
            if today not in path.name and path.name != "MEMORY.md":
                paths.append(path)

        return paths

    async def read_memory_md(self) -> Optional[str]:
        """Read long-term MEMORY.md if it exists."""
        path = self.workspace_dir / "MEMORY.md"
        if path.exists():
            return path.read_text()
        return None

    async def update_memory_md(self, content: str) -> None:
        """Update long-term MEMORY.md."""
        path = self.workspace_dir / "MEMORY.md"
        path.write_text(content)
        logger.info("[MEMORY] Updated MEMORY.md")


class MemoryCompactor:
    """Compacts daily memories into long-term MEMORY.md using LLM."""

    DEFAULT_PROMPT = """You are a memory compaction assistant. Review the daily memory files and create a concise summary for long-term storage.

Focus on:
- Key decisions made
- Important context about the user
- Action items or follow-ups
- Lessons learned

Format the output as markdown suitable for a MEMORY.md file.
Be concise but capture what's truly important."""

    def __init__(
        self,
        memory_manager: MemoryManager,
        llm_provider: str = "zai",
        llm_api_key: str = "",
        llm_model: str = ""
    ):
        self.memory_manager = memory_manager
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self._pending_memories: list[dict] = []

    async def append_pending(self, content: str, section: str = "Notes") -> None:
        """Queue a memory to be written before next compaction."""
        self._pending_memories.append({"content": content, "section": section})
        logger.info(f"[MEMORY] Queued pending memory: {content[:50]}...")

    async def _flush_pending(self) -> int:
        """Write all pending memories to disk."""
        count = 0
        for memory in self._pending_memories:
            await self.memory_manager.append_to_daily(
                memory["content"],
                section=memory["section"]
            )
            count += 1

        if count > 0:
            logger.info(f"[MEMORY] Flushed {count} pending memories to disk")

        self._pending_memories.clear()
        return count

    async def compact(self, custom_prompt: Optional[str] = None) -> dict:
        """Compact all daily memories into MEMORY.md using LLM.
        
        Args:
            custom_prompt: Optional custom prompt for the compaction LLM
        
        Returns:
            Dict with compaction results
        """
        # First, flush any pending memories to disk
        flushed = await self._flush_pending()

        # Get all memory files
        paths = self.memory_manager.get_all_memories()

        if not paths:
            return {"compacted": 0, "message": "No memories to compact", "flushed": flushed}

        # Read all daily memories
        combined_memories = []
        for path in paths:
            content = path.read_text()
            combined_memories.append(f"## {path.stem}\n\n{content}")

        all_memories = "\n\n---\n\n".join(combined_memories)

        # Call LLM to compact memories
        prompt = custom_prompt or self.DEFAULT_PROMPT
        compacted = await self._call_compaction_llm(all_memories, prompt)

        # Update MEMORY.md
        await self.memory_manager.update_memory_md(compacted)

        # Archive the daily files
        archived = await self._archive_files(paths)

        logger.info(f"[MEMORY] Compacted {len(paths)} memory files")

        return {
            "compacted": len(paths),
            "archived": archived,
            "flushed": flushed,
            "summary_length": len(compacted),
            "provider": self.llm_provider,
            "model": self.llm_model or "default"
        }

    async def _call_compaction_llm(self, memories: str, prompt: str) -> str:
        """Call LLM to compact memories."""
        if not self.llm_api_key:
            # Fallback: just concatenate with basic formatting
            return f"# MEMORY.md\n\n## Summary\n\n{memories[:2000]}...\n\n(Generated without LLM - no API key)"

        try:
            if self.llm_provider == "zai":
                return await self._call_zai(memories, prompt)
            elif self.llm_provider == "openai":
                return await self._call_openai(memories, prompt)
            else:
                logger.warning(f"Unknown provider {self.llm_provider}, using fallback")
                return f"# MEMORY.md\n\n## Raw Memories\n\n{memories[:3000]}"
        except Exception as e:
            logger.error(f"LLM compaction failed: {e}")
            return f"# MEMORY.md\n\n## Error\n\nCompaction failed: {e}\n\n## Raw Memories\n\n{memories[:2000]}"

    async def _call_zai(self, memories: str, prompt: str) -> str:
        """Call Z.AI API for compaction."""
        headers = {"Authorization": f"Bearer {self.llm_api_key}"}

        model = self.llm_model or "glm-4-flash"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.z.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"Please compact these daily memory files:\n\n{memories}"}
                    ],
                    "temperature": 0.3
                }
            ) as resp:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def _call_openai(self, memories: str, prompt: str) -> str:
        """Call OpenAI API for compaction."""
        headers = {"Authorization": f"Bearer {self.llm_api_key}"}

        model = self.llm_model or "gpt-4"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"Please compact these daily memory files:\n\n{memories}"}
                    ],
                    "temperature": 0.3
                }
            ) as resp:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def _archive_files(self, paths: list[Path]) -> int:
        """Move processed memory files to archive."""
        archive_dir = self.memory_manager.memory_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        count = 0
        for path in paths:
            dest = archive_dir / path.name
            path.rename(dest)
            count += 1

        return count
