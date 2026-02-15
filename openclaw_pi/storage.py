"""Thread persistence using JSON files."""
import aiofiles
import logging
from pathlib import Path
from openclaw_pi.models import Thread

logger = logging.getLogger(__name__)


class ThreadStorage:
    """Manages thread persistence to JSON files."""
    
    def __init__(self, threads_dir: Path):
        self.threads_dir = threads_dir
        self.threads_dir.mkdir(parents=True, exist_ok=True)
    
    def _thread_path(self, thread_id: str) -> Path:
        """Get the file path for a thread."""
        return self.threads_dir / f"{thread_id}.json"
    
    async def save(self, thread: Thread) -> None:
        """Save a thread to disk."""
        path = self._thread_path(thread.thread_id)
        async with aiofiles.open(path, "w") as f:
            await f.write(thread.model_dump_json(indent=2))
        logger.debug(f"Saved thread {thread.thread_id}")
    
    async def load(self, thread_id: str) -> Thread | None:
        """Load a thread from disk."""
        path = self._thread_path(thread_id)
        if not path.exists():
            return None
        async with aiofiles.open(path, "r") as f:
            content = await f.read()
            return Thread.model_validate_json(content)
    
    async def list_threads(self) -> list[str]:
        """List all thread IDs."""
        threads = []
        for path in self.threads_dir.glob("*.json"):
            threads.append(path.stem)
        return threads
    
    async def delete(self, thread_id: str) -> bool:
        """Delete a thread from disk."""
        path = self._thread_path(thread_id)
        if path.exists():
            path.unlink()
            logger.debug(f"Deleted thread {thread_id}")
            return True
        return False
