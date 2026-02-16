"""Pi agent subprocess management - one process per message."""
import asyncio
import logging
import os
import time
from collections.abc import AsyncGenerator
from pathlib import Path

from alfred.token_tracker import TokenTracker

logger = logging.getLogger(__name__)

DEFAULT_PI_PATH = Path("/usr/bin/pi")


class PiSubprocess:
    """Manages a Pi subprocess for a single message."""

    def __init__(
        self,
        thread_id: str,
        workspace: Path,
        timeout: int = 300,
        llm_provider: str = "zai",
        llm_api_key: str = "",
        llm_model: str = "",
        pi_path: Path | None = None,
        skills_dirs: list[Path] | None = None
    ):
        self.thread_id = thread_id
        self.workspace = workspace
        self.timeout = timeout
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.pi_path = pi_path or DEFAULT_PI_PATH
        self.skills_dirs = skills_dirs or []
        self.session_file = workspace / f"{thread_id}.json"

    async def is_alive(self) -> bool:
        """Always returns False for one-shot subprocess."""
        return False

    async def send_message(self, message: str, system_prompt: str | None = None) -> str:
        """Send message to Pi via subprocess."""
        start_time = time.time()

        # Prepend system prompt if provided
        if system_prompt:
            message = f"{system_prompt}\n\n---\n\nUser: {message}"

        cmd = [
            str(self.pi_path),
            "--print",
            "--provider", self.llm_provider,
            "--session", str(self.session_file),
        ]

        # Add skill directories
        for skills_dir in self.skills_dirs:
            if skills_dir.exists():
                cmd.extend(["--skill", str(skills_dir)])

        if self.llm_model:
            cmd.extend(["--model", self.llm_model])

        # Add message as argument
        cmd.append(message)

        logger.info(f"[PI] Thread {self.thread_id}: {' '.join(cmd[:8])}...")

        if not self.pi_path.exists():
            raise FileNotFoundError(f"Pi not found: {self.pi_path}")

        env = os.environ.copy()
        if self.llm_api_key:
            if self.llm_provider == "zai":
                env["ZAI_API_KEY"] = self.llm_api_key
            elif self.llm_provider == "moonshot":
                env["MOONSHOT_API_KEY"] = self.llm_api_key

        self.workspace.mkdir(parents=True, exist_ok=True)

        logger.info(f"[PI] Thread {self.thread_id}: Spawning process...")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            logger.info(f"[PI] Thread {self.thread_id}: PID {proc.pid}, waiting...")

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout
            )

            elapsed = time.time() - start_time
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            logger.info(f"[PI] Thread {self.thread_id}: Done in {elapsed:.2f}s, exit={proc.returncode}")
            logger.info(f"[PI] Thread {self.thread_id}: stdout={len(stdout_str)} chars, stderr={len(stderr_str)} chars")

            if stderr_str:
                logger.warning(f"[PI] Thread {self.thread_id}: stderr: {stderr_str[:500]}")

            if proc.returncode != 0:
                logger.error(f"[PI] Thread {self.thread_id}: Failed with code {proc.returncode}")
                raise RuntimeError(f"Pi failed: {stderr_str[:500]}")

            return stdout_str.strip()

        except asyncio.TimeoutError:
            logger.error(f"[PI] Thread {self.thread_id}: Timeout after {time.time() - start_time:.2f}s")
            raise
        except Exception as e:
            logger.exception(f"[PI] Thread {self.thread_id}: Error: {e}")
            raise

    async def send_message_stream(self, message: str, system_prompt: str | None = None) -> AsyncGenerator[str, None]:
        """Send message to Pi and stream response chunks."""
        start_time = time.time()

        # Prepend system prompt if provided
        if system_prompt:
            message = f"{system_prompt}\n\n---\n\nUser: {message}"

        cmd = [
            str(self.pi_path),
            "--print",
            "--stream",
            "--provider", self.llm_provider,
            "--session", str(self.session_file),
        ]

        # Add skill directories
        for skills_dir in self.skills_dirs:
            if skills_dir.exists():
                cmd.extend(["--skill", str(skills_dir)])

        if self.llm_model:
            cmd.extend(["--model", self.llm_model])

        # Add message as argument
        cmd.append(message)

        logger.info(f"[PI] Thread {self.thread_id}: Streaming {' '.join(cmd[:8])}...")

        if not self.pi_path.exists():
            raise FileNotFoundError(f"Pi not found: {self.pi_path}")

        env = os.environ.copy()
        if self.llm_api_key:
            if self.llm_provider == "zai":
                env["ZAI_API_KEY"] = self.llm_api_key
            elif self.llm_provider == "moonshot":
                env["MOONSHOT_API_KEY"] = self.llm_api_key

        self.workspace.mkdir(parents=True, exist_ok=True)

        logger.info(f"[PI] Thread {self.thread_id}: Spawning stream process...")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            logger.info(f"[PI] Thread {self.thread_id}: PID {proc.pid}, streaming...")

            buffer = ""
            chunk_count = 0

            # Stream stdout as it arrives
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        proc.stdout.read(1024),
                        timeout=self.timeout
                    )
                    if not chunk:
                        break

                    text = chunk.decode('utf-8', errors='replace')
                    buffer += text
                    chunk_count += 1

                    # Yield when we hit newlines or after accumulating enough
                    if '\n' in text or len(buffer) > 200:
                        yield buffer
                        buffer = ""

                except asyncio.TimeoutError:
                    logger.error(f"[PI] Thread {self.thread_id}: Stream timeout")
                    proc.kill()
                    raise

            # Wait for process to complete
            stdout, stderr = await proc.communicate()

            # Yield any remaining content
            if buffer:
                yield buffer

            elapsed = time.time() - start_time
            logger.info(f"[PI] Thread {self.thread_id}: Stream done in {elapsed:.2f}s, {chunk_count} chunks, exit={proc.returncode}")

            if stderr:
                stderr_str = stderr.decode('utf-8', errors='replace')
                if stderr_str:
                    logger.warning(f"[PI] Thread {self.thread_id}: stderr: {stderr_str[:500]}")

            if proc.returncode != 0:
                logger.error(f"[PI] Thread {self.thread_id}: Failed with code {proc.returncode}")

        except asyncio.TimeoutError:
            logger.error(f"[PI] Thread {self.thread_id}: Timeout after {time.time() - start_time:.2f}s")
            raise
        except Exception as e:
            logger.exception(f"[PI] Thread {self.thread_id}: Error: {e}")
            raise


class PiManager:
    """Manages Pi subprocesses - one per message."""

    def __init__(
        self,
        timeout: int = 300,
        llm_provider: str = "zai",
        llm_api_key: str = "",
        llm_model: str = "",
        pi_path: Path | None = None,
        token_tracker: TokenTracker | None = None,
        skills_dirs: list[Path] | None = None,
        streaming_enabled: bool = False
    ):
        self.timeout = timeout
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.pi_path = pi_path or DEFAULT_PI_PATH
        self._active_threads: set[str] = set()
        self.token_tracker = token_tracker
        self.skills_dirs = skills_dirs or []
        self.streaming_enabled = streaming_enabled

    async def send_message(self, thread_id: str, workspace: Path, message: str, system_prompt: str | None = None) -> str:
        """Send message to Pi for a thread."""
        self._active_threads.add(thread_id)

        try:
            pi = PiSubprocess(
                thread_id,
                workspace,
                self.timeout,
                self.llm_provider,
                self.llm_api_key,
                self.llm_model,
                self.pi_path,
                self.skills_dirs
            )
            response = await pi.send_message(message, system_prompt)

            # Sync token usage from session file
            if self.token_tracker:
                count = self.token_tracker.sync_from_session(pi.session_file)
                if count > 0:
                    logger.info(f"[TOKENS] Synced {count} token usage entries from {thread_id}")

            return response
        finally:
            self._active_threads.discard(thread_id)

    async def send_message_stream(
        self, thread_id: str, workspace: Path, message: str, system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Send message to Pi and stream response chunks."""
        self._active_threads.add(thread_id)

        try:
            pi = PiSubprocess(
                thread_id,
                workspace,
                self.timeout,
                self.llm_provider,
                self.llm_api_key,
                self.llm_model,
                self.pi_path,
                self.skills_dirs
            )

            async for chunk in pi.send_message_stream(message, system_prompt):
                yield chunk

            # Sync token usage after streaming
            if self.token_tracker:
                count = self.token_tracker.sync_from_session(pi.session_file)
                if count > 0:
                    logger.info(f"[TOKENS] Synced {count} token usage entries from {thread_id}")

        finally:
            self._active_threads.discard(thread_id)

    async def kill_thread(self, thread_id: str) -> bool:
        """Kill a thread (no-op for one-shot mode, just remove from active)."""
        if thread_id in self._active_threads:
            self._active_threads.discard(thread_id)
            return True
        return False

    async def cleanup(self) -> None:
        """Clear active threads."""
        self._active_threads.clear()
        logger.info("[PI MANAGER] Cleanup")

    async def list_active(self) -> list[str]:
        """List active thread IDs."""
        return list(self._active_threads)
