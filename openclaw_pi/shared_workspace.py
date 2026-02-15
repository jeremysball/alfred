"""Shared workspace for cross-thread collaboration."""
import logging
from pathlib import Path
from typing import Optional
import aiofiles

logger = logging.getLogger(__name__)


class SharedWorkspace:
    """Shared workspace accessible by all threads."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir / "shared"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.notes_dir = self.base_dir / "notes"
        self.notes_dir.mkdir(exist_ok=True)
        
        self.files_dir = self.base_dir / "files"
        self.files_dir.mkdir(exist_ok=True)
        
        self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
    
    async def write_note(self, filename: str, content: str, author: str) -> Path:
        """Write a note to the shared workspace."""
        path = self.notes_dir / f"{filename}.md"
        
        header = f"# {filename}\n\n**Author:** {author}\n\n"
        full_content = header + content
        
        async with aiofiles.open(path, 'w') as f:
            await f.write(full_content)
        
        logger.info(f"[SHARED] Note created: {filename} by {author}")
        return path
    
    async def read_note(self, filename: str) -> Optional[str]:
        """Read a note from the shared workspace."""
        path = self.notes_dir / f"{filename}.md"
        
        if not path.exists():
            return None
        
        async with aiofiles.open(path, 'r') as f:
            return await f.read()
    
    async def list_notes(self) -> list[dict]:
        """List all notes in the shared workspace."""
        notes = []
        
        for path in self.notes_dir.glob("*.md"):
            stat = path.stat()
            notes.append({
                "name": path.stem,
                "path": str(path),
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
        
        return sorted(notes, key=lambda x: x["modified"], reverse=True)
    
    async def append_to_note(self, filename: str, content: str) -> bool:
        """Append content to an existing note."""
        path = self.notes_dir / f"{filename}.md"
        
        if not path.exists():
            return False
        
        async with aiofiles.open(path, 'a') as f:
            await f.write(f"\n\n{content}")
        
        logger.info(f"[SHARED] Note appended: {filename}")
        return True
    
    async def delete_note(self, filename: str) -> bool:
        """Delete a note from the shared workspace."""
        path = self.notes_dir / f"{filename}.md"
        
        if path.exists():
            path.unlink()
            logger.info(f"[SHARED] Note deleted: {filename}")
            return True
        return False
    
    def get_data_path(self, filename: str) -> Path:
        """Get path for a data file (creates if needed)."""
        return self.data_dir / filename
    
    async def write_data(self, filename: str, content: str | bytes) -> Path:
        """Write data to the shared workspace."""
        path = self.data_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        
        mode = 'wb' if isinstance(content, bytes) else 'w'
        async with aiofiles.open(path, mode) as f:
            await f.write(content)
        
        logger.info(f"[SHARED] Data written: {filename}")
        return path
    
    async def read_data(self, filename: str) -> Optional[str | bytes]:
        """Read data from the shared workspace."""
        path = self.data_dir / filename
        
        if not path.exists():
            return None
        
        # Try text first, fallback to binary
        try:
            async with aiofiles.open(path, 'r') as f:
                return await f.read()
        except UnicodeDecodeError:
            async with aiofiles.open(path, 'rb') as f:
                return await f.read()
    
    async def list_data_files(self) -> list[dict]:
        """List all data files in the shared workspace."""
        files = []
        
        for path in self.data_dir.rglob("*"):
            if path.is_file():
                stat = path.stat()
                files.append({
                    "name": path.name,
                    "path": str(path.relative_to(self.data_dir)),
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })
        
        return sorted(files, key=lambda x: x["modified"], reverse=True)
    
    def get_structure(self) -> dict:
        """Get the structure of the shared workspace."""
        return {
            "base_dir": str(self.base_dir),
            "notes": len(list(self.notes_dir.glob("*.md"))),
            "data_files": len(list(self.data_dir.rglob("*")) if self.data_dir.exists() else []),
            "files": len(list(self.files_dir.rglob("*")) if self.files_dir.exists() else [])
        }
