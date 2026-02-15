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
        self.session_file = workspace / f"{thread_id}.json"
    
    async def start(self) -> None:
        """Start is a no-op - pi runs per-message in --print mode."""
        pass
    
    async def send_message(self, message: str) -> str:
        """Send message to pi via subprocess invocation in --print mode."""
        # Build pi command
        cmd = [
            str(self.pi_path),
            "--print",  # Non-interactive mode
            "--provider", self.llm_provider,
            "--session", str(self.session_file),
        ]
        
        if self.llm_model:
            cmd.extend(["--model", self.llm_model])
        
        # Add the message
        cmd.append(message)
        
        logger.info(f"Running pi for thread {self.thread_id}: {' '.join(cmd[:6])}...")
        
        # Set up environment with API key
        env = os.environ.copy()
        if self.llm_api_key:
            if self.llm_provider == "zai":
                env["ZAI_API_KEY"] = self.llm_api_key
            elif self.llm_provider == "moonshot":
                env["MOONSHOT_API_KEY"] = self.llm_api_key
        
        # Ensure workspace exists
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Run pi subprocess
        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await asyncio.wait_for(
                self.process.communicate(),
                timeout=self.timeout
            )
            
            if self.process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace') if stderr else "Unknown error"
                stdout_preview = stdout.decode('utf-8', errors='replace')[:200] if stdout else ""
                logger.error(f"pi stderr: {error_msg}")
                logger.error(f"pi stdout: {stdout_preview}")
                raise RuntimeError(f"pi failed with code {self.process.returncode}: {error_msg}")
            
            response = stdout.decode('utf-8', errors='replace').strip()
            logger.info(f"pi completed for thread {self.thread_id}")
            return response
            
        except asyncio.TimeoutError:
            if self.process and self.process.returncode is None:
                self.process.kill()
                await self.process.wait()
            raise asyncio.TimeoutError(f"pi timed out after {self.timeout}s")
    
    async def kill(self) -> None:
        """Kill the subprocess if running."""
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
        """Get or create a pi subprocess for a thread."""
        if thread_id not in self._processes:
            self._processes[thread_id] = PiSubprocess(
                thread_id,
                workspace,
                self.timeout,
                self.llm_provider,
                self.llm_api_key,
                self.llm_model,
                self.pi_path
            )
        return self._processes[thread_id]
    
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
        # Filter to only processes that are actually running
        active = []
        for thread_id, pi in list(self._processes.items()):
            if await pi.is_alive():
                active.append(thread_id)
        return active
