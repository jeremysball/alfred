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
        
        # Log full command for debugging
        logger.info(f"[LLM CALL] Thread {self.thread_id}: Starting pi subprocess")
        logger.info(f"[LLM CALL] Command: {' '.join(cmd)}")
        logger.info(f"[LLM CALL] Workspace: {self.workspace}")
        logger.info(f"[LLM CALL] Session file: {self.session_file}")
        logger.info(f"[LLM CALL] Provider: {self.llm_provider}, Model: {self.llm_model or 'default'}")
        
        # Check if pi executable exists
        if not self.pi_path.exists():
            logger.error(f"[LLM CALL] Pi executable not found at: {self.pi_path}")
            raise FileNotFoundError(f"Pi executable not found: {self.pi_path}")
        
        # Set up environment with API key
        env = os.environ.copy()
        if self.llm_api_key:
            if self.llm_provider == "zai":
                env["ZAI_API_KEY"] = self.llm_api_key
                logger.info(f"[LLM CALL] Set ZAI_API_KEY environment variable")
            elif self.llm_provider == "moonshot":
                env["MOONSHOT_API_KEY"] = self.llm_api_key
                logger.info(f"[LLM CALL] Set MOONSHOT_API_KEY environment variable")
        else:
            logger.warning(f"[LLM CALL] No API key provided for provider: {self.llm_provider}")
        
        # Ensure workspace exists
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Run pi subprocess
        try:
            logger.info(f"[LLM CALL] Spawning subprocess...")
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            logger.info(f"[LLM CALL] Subprocess started (PID: {self.process.pid}), waiting for response...")
            
            stdout, stderr = await asyncio.wait_for(
                self.process.communicate(),
                timeout=self.timeout
            )
            
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            
            logger.info(f"[LLM CALL] Subprocess completed (return code: {self.process.returncode})")
            logger.debug(f"[LLM CALL] stdout length: {len(stdout_str)} chars")
            logger.debug(f"[LLM CALL] stderr length: {len(stderr_str)} chars")
            
            if stderr_str:
                logger.warning(f"[LLM CALL] stderr: {stderr_str[:500]}")
            
            if self.process.returncode != 0:
                logger.error(f"[LLM CALL] pi failed with code {self.process.returncode}")
                logger.error(f"[LLM CALL] stderr: {stderr_str}")
                logger.error(f"[LLM CALL] stdout preview: {stdout_str[:500]}")
                raise RuntimeError(f"pi failed with code {self.process.returncode}: {stderr_str}")
            
            response = stdout_str.strip()
            logger.info(f"[LLM CALL] Response received for thread {self.thread_id} ({len(response)} chars)")
            
            if not response:
                logger.warning(f"[LLM CALL] Empty response from pi for thread {self.thread_id}")
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"[LLM CALL] Timeout after {self.timeout}s for thread {self.thread_id}")
            if self.process and self.process.returncode is None:
                self.process.kill()
                await self.process.wait()
                logger.info(f"[LLM CALL] Killed timed-out process")
            raise asyncio.TimeoutError(f"pi timed out after {self.timeout}s")
        except Exception as e:
            logger.exception(f"[LLM CALL] Exception in pi subprocess for thread {self.thread_id}: {e}")
            raise
    
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
