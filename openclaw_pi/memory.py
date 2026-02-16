"""Memory system for persistent agent context."""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

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
    
    def get_recent_memories(self, days: int = 2) -> list[Path]:
        """Get paths to recent daily memory files."""
        paths = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            path = self.get_daily_memory_path(date)
            if path.exists():
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
        logger.info(f"[MEMORY] Updated MEMORY.md")


class MemoryCompactor:
    """Compacts daily memories into long-term MEMORY.md."""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
    
    async def compact(
        self,
        days: int = 7,
        strategy: str = "summarize"
    ) -> dict:
        """Compact recent daily memories into MEMORY.md.
        
        Args:
            days: Number of days to compact
            strategy: Compaction strategy - "summarize", "extract_key_decisions", or "archive"
        
        Returns:
            Dict with compaction results
        """
        paths = self.memory_manager.get_recent_memories(days)
        
        if not paths:
            return {"compacted": 0, "strategy": strategy, "message": "No memories to compact"}
        
        # Read all daily memories
        daily_contents = []
        for path in paths:
            daily_contents.append(path.read_text())
        
        combined = "\n\n".join(daily_contents)
        
        # Apply compaction strategy
        if strategy == "summarize":
            result = await self._summarize_strategy(combined, paths)
        elif strategy == "extract_key_decisions":
            result = await self._extract_decisions_strategy(combined, paths)
        elif strategy == "archive":
            result = await self._archive_strategy(paths)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        logger.info(f"[MEMORY] Compacted {len(paths)} days using {strategy} strategy")
        
        return {
            "compacted": len(paths),
            "strategy": strategy,
            "result": result
        }
    
    async def _summarize_strategy(self, content: str, paths: list[Path]) -> str:
        """Summarize daily memories into key points."""
        # For now, extract sections marked as "Key Decisions" or "Important"
        lines = content.split('\n')
        summary = ["## Recent Summary\n"]
        
        in_important_section = False
        for line in lines:
            if '##' in line and ('Key' in line or 'Important' in line or 'Decision' in line):
                in_important_section = True
                summary.append(line)
            elif line.startswith('## '):
                in_important_section = False
            elif in_important_section and line.strip().startswith('-'):
                summary.append(line)
        
        return '\n'.join(summary)
    
    async def _extract_decisions_strategy(self, content: str, paths: list[Path]) -> str:
        """Extract only key decisions and action items."""
        lines = content.split('\n')
        decisions = ["## Key Decisions\n"]
        actions = ["## Action Items\n"]
        
        for line in lines:
            line_lower = line.lower()
            if any(word in line_lower for word in ['decided', 'decision', 'chose', 'choice']):
                decisions.append(line)
            if line.strip().startswith('- [ ]'):
                actions.append(line)
        
        return '\n'.join(decisions + ['\n'] + actions)
    
    async def _archive_strategy(self, paths: list[Path]) -> str:
        """Move daily memories to archive folder."""
        archive_dir = self.memory_manager.memory_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        
        archived = []
        for path in paths:
            # Skip today
            if datetime.now().strftime('%Y-%m-%d') in path.name:
                continue
            
            dest = archive_dir / path.name
            path.rename(dest)
            archived.append(path.name)
        
        return f"Archived {len(archived)} files: {', '.join(archived)}"
