"""Pi agent subprocess management."""
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default pi path - can be overridden via environment
DEFAULT_PI_PATH = Path(__file__).parent.parent / "node_modules" / ".bin" / "pi"


class PiSubprocess:
    """Manages a single pi subprocess for a thread."""
    
    def __init__(
        self,
        thread_id: str,
        workspace: Path,
        timeout: int = 300,
        llm_provider: str = "zai",
        llm_api_key: str = "",
        llm_model: str = "",
        pi_path: Path | None = None
    ):
        self.thread_id = thread_id
        self.workspace = workspace
        self.timeout = timeout
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.pi_path = pi_path or DEFAULT_PI_PATH
        self.process: Optional[asyncio.subprocess.Process] = None
    
    async def start(self) -> None:
        """Start the pi subprocess with LLM config."""
        env = os.environ.copy()
        
        # Set LLM provider config for pi
        if self.llm_provider == "zai":
            env["ZAI_API_KEY"] = self.llm_api_key
            if self.llm_model:
                env["ZAI_MODEL"] = self.llm_model
        elif self.llm_provider == "moonshot":
            env["MOONSHOT_API_KEY"] = self.llm_api_key
            if self.llm_model:
                env["MOONSHOT_MODEL"] = self.llm_model
        
        self.process = await asyncio.create_subprocess_exec(
            str(self.pi_path),
            "--workspace", str(self.workspace),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        logger.info(f"Started pi for thread {self.thread_id} (PID: {self.process.pid})")
    
    async def send_message(self, message: str) -> str:
        """Send message to pi, get response with timeout."""
        if not self.process or self.process.returncode is not None:
            raise RuntimeError("Pi process not running")
        
        # Send message + newline
        self.process.stdin.write(f"{message}\n".encode())
        await self.process.stdin.drain()
        
        # Read response with timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                self.process.communicate(),
                timeout=self.timeout
            )
            
            if stderr:
                logger.warning(f"Pi stderr: {stderr.decode()}")
            
            return stdout.decode()
        except asyncio.TimeoutError:
            logger.error(f"Pi timeout for thread {self.thread_id}")
            self.process.kill()
            raise
    
    async def kill(self) -> None:
        """Kill the subprocess."""
        if self.process and self.process.returncode is None:
            self.process.kill()
            await self.process.wait()
            logger.info(f"Killed pi for thread {self.thread_id}")
    
    async def is_alive(self) -> bool:
        """Check if process is still running."""
        if not self.process:
            return False
        return self.process.returncode is None


class PiManager:
    """Manages all pi subprocesses."""
    
    def __init__(
        self,
        timeout: int = 300,
        llm_provider: str = "zai",
        llm_api_key: str = "",
        llm_model: str = "",
        pi_path: Path | None = None
    ):
        self.timeout = timeout
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.pi_path = pi_path or DEFAULT_PI_PATH
        self._processes: dict[str, PiSubprocess] = {}
    
    async def get_or_create(self, thread_id: str, workspace: Path) -> PiSubprocess:
        """Get existing or create new pi subprocess."""
        if thread_id in self._processes:
            pi = self._processes[thread_id]
            if await pi.is_alive():
                return pi
            # Dead process, clean up
            del self._processes[thread_id]
        
        # Create new
        pi = PiSubprocess(
            thread_id,
            workspace,
            self.timeout,
            self.llm_provider,
            self.llm_api_key,
            self.llm_model,
            self.pi_path
        )
        await pi.start()
        self._processes[thread_id] = pi
        return pi
    
    async def kill_thread(self, thread_id: str) -> bool:
        """Kill a specific thread's pi process."""
        if thread_id in self._processes:
            await self._processes[thread_id].kill()
            del self._processes[thread_id]
            return True
        return False
    
    async def cleanup(self) -> None:
        """Kill all processes."""
        for pi in list(self._processes.values()):
            await pi.kill()
        self._processes.clear()
        logger.info("Cleaned up all pi processes")
    
    async def list_active(self) -> list[str]:
        """List active thread IDs."""
        return list(self._processes.keys())
