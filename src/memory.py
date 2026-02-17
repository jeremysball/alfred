"""Memory storage system for daily logs and curated memories."""

import re
from datetime import datetime
from pathlib import Path

import aiofiles

from src.config import Config
from src.embeddings import EmbeddingClient
from src.types import MemoryEntry


class MemoryStore:
    """Store and retrieve memories from daily logs and MEMORY.md.

    Daily logs are Markdown files created by the distillation process.
    They contain summarized insights from conversations, not raw chat.

    MEMORY.md holds durable, important memories curated by the model or user.
    """

    def __init__(self, config: Config, embedder: EmbeddingClient) -> None:
        self.config = config
        self.embedder = embedder
        self.memory_dir = config.memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.curated_path = Path("MEMORY.md")

    def _daily_path(self, date: str | None = None) -> Path:
        """Get path for daily memory file (YYYY-MM-DD.md)."""
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        return self.memory_dir / f"{date_str}.md"

    async def write_daily_log(
        self,
        date: str,
        entries: list[MemoryEntry],
    ) -> Path:
        """Write distilled entries to a daily log file.

        Called by the distillation process after summarizing conversations.
        Overwrites existing file for that date.
        """
        path = self._daily_path(date)
        lines = [f"# {date}\n"]

        for entry in entries:
            timestamp = entry.timestamp.strftime("%H:%M")
            lines.append(f"\n## {timestamp} - {entry.role.title()}\n")
            lines.append(entry.content)
            if entry.importance != 0.5 or entry.tags:
                metadata = {"importance": entry.importance}
                if entry.tags:
                    metadata["tags"] = entry.tags
                lines.append(f"\n<!-- metadata: {metadata} -->")

        async with aiofiles.open(path, "w") as f:
            await f.write("\n".join(lines))

        return path

    async def read_daily_log(self, date: str | None = None) -> str:
        """Read a daily log file as raw Markdown."""
        path = self._daily_path(date)
        if not path.exists():
            return ""
        async with aiofiles.open(path, "r") as f:
            return await f.read()

    async def read_all_daily_logs(self) -> list[tuple[str, str]]:
        """Read all daily logs, returning list of (date, content) tuples."""
        results = []
        for path in sorted(self.memory_dir.glob("*.md")):
            date = path.stem
            async with aiofiles.open(path, "r") as f:
                content = await f.read()
                if content.strip():
                    results.append((date, content))
        return results

    async def parse_daily_log(self, date: str | None = None) -> list[MemoryEntry]:
        """Parse a daily log into MemoryEntry objects with embeddings."""
        content = await self.read_daily_log(date)
        if not content:
            return []

        entries = []
        # Split on ## headers (each entry)
        sections = re.split(r"\n## ", content)[1:]  # Skip title

        for section in sections:
            lines = section.strip().split("\n")
            header = lines[0]  # "HH:MM - Role"
            body = "\n".join(lines[1:]).strip()

            # Parse header
            match = re.match(r"(\d{2}:\d{2}) - (\w+)", header)
            if not match:
                continue

            time_str, role = match.groups()
            role = role.lower()
            if role not in ("user", "assistant", "system"):
                role = "system"

            # Parse metadata from HTML comment
            importance = 0.5
            tags: list[str] = []
            metadata_match = re.search(r"<!-- metadata: ({.*?}) -->", body)
            if metadata_match:
                try:
                    import ast

                    metadata = ast.literal_eval(metadata_match.group(1))
                    importance = metadata.get("importance", 0.5)
                    tags = metadata.get("tags", [])
                    body = body[: metadata_match.start()].strip()
                except (ValueError, SyntaxError):
                    pass

            # Generate embedding for the content
            embedding = await self.embedder.embed(body)

            # Construct timestamp
            date_str = date or datetime.now().strftime("%Y-%m-%d")
            timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

            entries.append(
                MemoryEntry(
                    timestamp=timestamp,
                    role=role,  # type: ignore
                    content=body,
                    embedding=embedding,
                    importance=importance,
                    tags=tags,
                )
            )

        return entries

    async def read_curated_memory(self) -> str:
        """Read MEMORY.md content."""
        if not self.curated_path.exists():
            return ""
        async with aiofiles.open(self.curated_path, "r") as f:
            return await f.read()

    async def write_curated_memory(self, content: str) -> None:
        """Write to MEMORY.md (overwrites existing content).

        Use this for durable, important memories that should persist
        across sessions and be loaded into every context.
        """
        async with aiofiles.open(self.curated_path, "w") as f:
            await f.write(content)

    async def append_curated_memory(self, content: str) -> None:
        """Append to MEMORY.md."""
        async with aiofiles.open(self.curated_path, "a") as f:
            await f.write(f"\n\n{content}\n")

    async def parse_curated_memory(self) -> list[MemoryEntry]:
        """Parse MEMORY.md into MemoryEntry objects with embeddings.

        Each section (separated by blank lines or headers) becomes an entry.
        """
        content = await self.read_curated_memory()
        if not content:
            return []

        # Split by headers or double newlines
        sections = re.split(r"\n#{1,2} |\n\n", content)
        sections = [s.strip() for s in sections if s.strip()]

        entries = []
        for section in sections:
            embedding = await self.embedder.embed(section)
            entries.append(
                MemoryEntry(
                    timestamp=datetime.now(),
                    role="system",
                    content=section,
                    embedding=embedding,
                    importance=1.0,  # Curated memories are high importance
                    tags=["curated"],
                )
            )

        return entries

    async def search_memories(
        self,
        query: str,
        top_k: int = 10,
        include_curated: bool = True,
    ) -> list[MemoryEntry]:
        """Search all memories by semantic similarity to query.

        Returns top-k most relevant entries from daily logs and MEMORY.md.
        """
        from src.embeddings import cosine_similarity

        query_embedding = await self.embedder.embed(query)

        # Collect all entries
        all_entries: list[MemoryEntry] = []

        # Parse all daily logs
        for date, _ in await self.read_all_daily_logs():
            entries = await self.parse_daily_log(date)
            all_entries.extend(entries)

        # Add curated memories
        if include_curated:
            all_entries.extend(await self.parse_curated_memory())

        # Score and rank
        scored = []
        for entry in all_entries:
            if entry.embedding:
                score = cosine_similarity(query_embedding, entry.embedding)
                # Boost by importance
                score *= 0.7 + (entry.importance * 0.3)
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]
