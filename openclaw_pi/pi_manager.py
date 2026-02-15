"""Pi agent subprocess management - persistent processes per thread."""
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default pi path - can be overridden via environment
DEFAULT_PI_PATH = Path(__file__).parent.parent / "node_modules" / ".bin" / "pi"


class PiSubprocess:
    """Manages a persistent Pi subprocess for a thread."""
    
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
        self._stdin_writer: Optional[asyncio.StreamWriter] = None
        self._stdout_reader: Optional[asyncio.StreamReader] = None
        self._lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Start persistent Pi subprocess in interactive mode."""
        if self.process and self.process.returncode is None:
            logger.debug(f"Pi already running for thread {self.thread_id}")
            return
        
        cmd = [
            str(self.pi_path),
            "--provider", self.llm_provider,
            "--session", str(self.session_file),
        ]
        
        if self.llm_model:
            cmd.extend(["--model", self.llm_model])
        
        logger.info(f"[PI START] Thread {self.thread_id}: {' '.join(cmd)}")
        
        if not self.pi_path.exists():
            raise FileNotFoundError(f"Pi not found: {self.pi_path}")
        
        env = os.environ.copy()
        if self.llm_api_key:
            if self.llm_provider == "zai":
                env["ZAI_API_KEY"] = self.llm_api_key
            elif self.llm_provider == "moonshot":
                env["MOONSHOT_API_KEY"] = self.llm_api_key
        
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            self._stdin_writer = self.process.stdin
            self._stdout_reader = self.process.stdout
            logger.info(f"[PI START] Thread {self.thread_id}: Started (PID {self.process.pid})")
        except Exception as e:
            logger.exception(f"[PI START] Failed to start: {e}")
            raise
    
    async def send_message(self, message: str) -> str:
        """Send message to Pi and get response."""
        await self.start()
        
        async with self._lock:
            try:
                # Send message with delimiter
                msg = message.strip() + "\n\n__END__\n"
                logger.debug(f"[PI SEND] Thread {self.thread_id}: {message[:100]}...")
                
                self._stdin_writer.write(msg.encode())
                await self._stdin_writer.drain()
                
                # Read response until delimiter
                response_lines = []
                while True:
                    line = await asyncio.wait_for(
                        self._stdout_reader.readline(),
                        timeout=self.timeout
                    )
                    if not line:
                        break
                    line_str = line.decode().strip()
                    if line_str == "__END__":
                        break
                    response_lines.append(line_str)
                
                response = "\n".join(response_lines).strip()
                logger.info(f"[PI RECV] Thread {self.thread_id}: {len(response)} chars")
                return response
                
            except asyncio.TimeoutError:
                logger.error(f"[PI TIMEOUT] Thread {self.thread_id}")
                await self.restart()
                raise asyncio.TimeoutError(f"Pi timeout after {self.timeout}s")
            except Exception as e:
                logger.exception(f"[PI ERROR] Thread {self.thread_id}: {e}")
                await self.restart()
                raise
    
    async def restart(self) -> None:
        """Restart the Pi process."""
        await self.kill()
        await self.start()
    
    async def kill(self) -> None:
        """Kill the subprocess."""
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            logger.info(f"[PI KILL] Thread {self.thread_id}")
    
    async def is_alive(self) -> bool:
        """Check if process is running."""
        if not self.process:
            return False
        return self.process.returncode is None


class PiManager:
    """Manages all Pi subprocesses - one per thread."""
    
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
        """Get or create a Pi subprocess for a thread."""
        if thread_id not in self._processes:
            logger.info(f"[PI MANAGER] Creating new Pi for thread {thread_id}")
            self._processes[thread_id] = PiSubprocess(
                thread_id,
                workspace,
                self.timeout,
                self.llm_provider,
                self.llm_api_key,
                self.llm_model,
                self.pi_path
            )
        
        pi = self._processes[thread_id]
        await pi.start()
        return pi
    
    async def kill_thread(self, thread_id: str) -> bool:
        """Kill a thread's Pi process."""
        if thread_id in self._processes:
            await self._processes[thread_id].kill()
            del self._processes[thread_id]
            logger.info(f"[PI MANAGER] Killed thread {thread_id}")
            return True
        return False
    
    async def cleanup(self) -> None:
        """Kill all processes."""
        for pi in list(self._processes.values()):
            await pi.kill()
        self._processes.clear()
        logger.info("[PI MANAGER] Cleanup complete")
    
    async def list_active(self) -> list[str]:
        """List active thread IDs."""
        active = []
        for thread_id, pi in list(self._processes.items()):
            if await pi.is_alive():
                active.append(thread_id)
        return active
