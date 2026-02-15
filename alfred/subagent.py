"""Sub-agent support for isolated task execution."""
import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

from alfred.pi_manager import PiSubprocess

logger = logging.getLogger(__name__)


class SubAgent:
    """A sub-agent with isolated context for specific tasks."""

    def __init__(
        self,
        subagent_id: str,
        parent_thread_id: str,
        task: str,
        workspace_dir: Path,
        llm_provider: str = "zai",
        llm_api_key: str = "",
        llm_model: str = "",
        timeout: int = 300
    ):
        self.subagent_id = subagent_id
        self.parent_thread_id = parent_thread_id
        self.task = task
        self.workspace_dir = workspace_dir
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.timeout = timeout
        self.temp_dir: Path | None = None
        self.pi: PiSubprocess | None = None

    async def setup(self) -> None:
        """Create isolated workspace for subagent."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"subagent_{self.subagent_id}_"))

        # Copy workspace files
        if self.workspace_dir.exists():
            for item in self.workspace_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, self.temp_dir / item.name)
                elif item.is_dir() and item.name not in [".pi", "__pycache__", ".venv"]:
                    shutil.copytree(item, self.temp_dir / item.name, dirs_exist_ok=True)

        logger.info(f"Sub-agent {self.subagent_id} workspace: {self.temp_dir}")

    async def run(self) -> str:
        """Run the sub-agent task."""
        if not self.temp_dir:
            await self.setup()

        self.pi = PiSubprocess(
            self.subagent_id,
            self.temp_dir,
            self.timeout,
            self.llm_provider,
            self.llm_api_key,
            self.llm_model
        )

        try:
            await self.pi.start()
            result = await self.pi.send_message(self.task)
            logger.info(f"Sub-agent {self.subagent_id} completed")
            return result
        except asyncio.TimeoutError:
            logger.error(f"Sub-agent {self.subagent_id} timed out")
            return f"⏱️ Sub-agent {self.subagent_id} timed out"
        finally:
            await self.cleanup()

    async def cleanup(self) -> None:
        """Clean up subagent resources."""
        if self.pi:
            await self.pi.kill()

        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up sub-agent {self.subagent_id}")
