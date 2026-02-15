"""Pi agent subprocess management - persistent processes per thread."""
import asyncio
import logging
import os
import time
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
        start_time = time.time()
        await self.start()
        
        async with self._lock:
            logger.info(f"[PI SEND] Thread {self.thread_id}: Starting send_message")
            logger.info(f"[PI SEND] Thread {self.thread_id}: Message length={len(message)}")
            logger.info(f"[PI SEND] Thread {self.thread_id}: Process alive={await self.is_alive()}, PID={self.process.pid if self.process else 'None'}")
            
            try:
                # Send message with delimiter
                msg = message.strip() + "\n\n__END__\n"
                msg_bytes = msg.encode()
                
                logger.info(f"[PI SEND] Thread {self.thread_id}: Writing {len(msg_bytes)} bytes to stdin...")
                self._stdin_writer.write(msg_bytes)
                await self._stdin_writer.drain()
                logger.info(f"[PI SEND] Thread {self.thread_id}: Write complete ({time.time() - start_time:.2f}s)")
                
                # Read response until delimiter
                response_lines = []
                line_count = 0
                last_log_time = time.time()
                
                logger.info(f"[PI RECV] Thread {self.thread_id}: Starting read loop (timeout={self.timeout}s)...")
                
                while True:
                    try:
                        line = await asyncio.wait_for(
                            self._stdout_reader.readline(),
                            timeout=5.0  # Shorter timeout for logging
                        )
                    except asyncio.TimeoutError:
                        # No data for 5 seconds, log progress
                        elapsed = time.time() - start_time
                        logger.info(f"[PI RECV] Thread {self.thread_id}: Still waiting... ({elapsed:.1f}s elapsed, {line_count} lines so far)")
                        
                        # Check if process is still alive
                        if not await self.is_alive():
                            logger.error(f"[PI RECV] Thread {self.thread_id}: Process died!")
                            # Read any remaining stderr
                            stderr_data = await self._read_stderr()
                            logger.error(f"[PI RECV] Thread {self.thread_id}: stderr: {stderr_data[:500]}")
                            raise RuntimeError("Pi process died while waiting for response")
                        continue
                    
                    if not line:
                        logger.warning(f"[PI RECV] Thread {self.thread_id}: EOF reached (empty line)")
                        break
                    
                    line_str = line.decode().rstrip()  # Keep trailing spaces, strip newline
                    line_count += 1
                    
                    if line_str == "__END__":
                        elapsed = time.time() - start_time
                        logger.info(f"[PI RECV] Thread {self.thread_id}: Found delimiter at line {line_count} ({elapsed:.2f}s)")
                        break
                    
                    response_lines.append(line_str)
                    
                    # Log first few lines for debugging
                    if line_count <= 3:
                        logger.info(f"[PI RECV] Thread {self.thread_id}: Line {line_count}: {line_str[:100]}...")
                
                response = "\n".join(response_lines).strip()
                total_time = time.time() - start_time
                
                logger.info(f"[PI RECV] Thread {self.thread_id}: Complete in {total_time:.2f}s")
                logger.info(f"[PI RECV] Thread {self.thread_id}: {len(response)} chars, {line_count} lines")
                
                if not response:
                    logger.warning(f"[PI RECV] Thread {self.thread_id}: Empty response!")
                    # Try to read stderr for debugging
                    stderr_data = await self._read_stderr()
                    if stderr_data:
                        logger.warning(f"[PI RECV] Thread {self.thread_id}: stderr: {stderr_data[:500]}")
                
                return response
                
            except asyncio.TimeoutError:
                total_time = time.time() - start_time
                logger.error(f"[PI TIMEOUT] Thread {self.thread_id}: Timeout after {total_time:.2f}s")
                # Try to get stderr before restart
                try:
                    stderr_data = await self._read_stderr()
                    logger.error(f"[PI TIMEOUT] Thread {self.thread_id}: stderr: {stderr_data[:1000]}")
                except Exception as e:
                    logger.error(f"[PI TIMEOUT] Thread {self.thread_id}: Could not read stderr: {e}")
                await self.restart()
                raise asyncio.TimeoutError(f"Pi timeout after {total_time:.1f}s")
                
            except Exception as e:
                total_time = time.time() - start_time
                logger.exception(f"[PI ERROR] Thread {self.thread_id}: {e} (after {total_time:.2f}s)")
                await self.restart()
                raise
    
    async def _read_stderr(self) -> str:
        """Read available data from stderr without blocking."""
        if not self.process or not self.process.stderr:
            return ""
        
        stderr_data = []
        try:
            # Try to read with short timeout
            while True:
                line = await asyncio.wait_for(self.process.stderr.readline(), timeout=0.5)
                if not line:
                    break
                stderr_data.append(line.decode())
        except asyncio.TimeoutError:
            pass  # No more data available
        except Exception as e:
            logger.debug(f"[PI STDERR] Thread {self.thread_id}: Error reading: {e}")
        
        return "".join(stderr_data)
    
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
