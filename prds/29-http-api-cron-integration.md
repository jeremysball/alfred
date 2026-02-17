# PRD: HTTP API + Cron Integration

## Overview

**Issue**: #29
**Parent**: #10 (Alfred - The Rememberer)
**Status**: Planning
**Priority**: Medium
**Created**: 2026-02-17

Implement a local HTTP API that cron can call, with Alfred managing cron jobs through natural language.

---

## Problem Statement

Alfred currently operates reactively—all actions require user messages. Users want:
- Scheduled reminders ("Remind me to stand up every hour")
- Periodic tasks ("Summarize our conversations every 3 days")
- Time-based automation without external services

Running a full scheduler inside Alfred adds complexity. Since cron already exists and is reliable, we can leverage it with a simple HTTP API.

---

## Solution

1. **HTTP API** (FastAPI) listening on localhost
   - Single endpoint: `POST /message`
   - Two modes: notify (send to user) or inject (send as user)
   - Configurable port via config file

2. **Cron Management**
   - Alfred creates/edits crontab directly
   - Each job tagged with UUID comment for tracking
   - List and remove jobs via UUID

3. **Natural Language Interface**
   - LLM parses user requests directly
   - Converts "remind me every hour" → cron schedule + API call

---

## Acceptance Criteria

- [ ] FastAPI server with `POST /message` endpoint
- [ ] Request body: `{"mode": "notify" | "inject", "chat_id": int, "message": str}`
- [ ] Listen on localhost only, configurable port
- [ ] Return HTTP status codes only (200, 400, 500)
- [ ] Create cron jobs via `crontab -e` with UUID comments
- [ ] List Alfred-managed cron jobs (parse crontab)
- [ ] Remove cron jobs by UUID
- [ ] Natural language job creation via LLM
- [ ] Update Dockerfile to start crond

---

## File Structure

```
src/
├── api.py           # FastAPI server
└── cron.py          # Crontab management
```

---

## HTTP API (src/api.py)

```python
"""Local HTTP API for cron-triggered actions."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal

from src.config import Config

logger = logging.getLogger(__name__)


class MessageRequest(BaseModel):
    """Request body for /message endpoint."""
    mode: Literal["notify", "inject"]
    chat_id: int
    message: str


class APIServer:
    """FastAPI server for Alfred's HTTP API."""
    
    def __init__(self, config: Config, bot = None) -> None:
        self.config = config
        self.bot = bot
        self.app = self._create_app()
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Manage server lifecycle."""
        logger.info(f"Alfred API starting on port {self.config.api_port}")
        yield
        logger.info("Alfred API shutting down")
    
    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI app."""
        app = FastAPI(
            title="Alfred API",
            description="Local HTTP API for cron-triggered actions",
            version="1.0.0",
            lifespan=self.lifespan,
        )
        
        @app.post("/message")
        async def send_message(req: MessageRequest):
            """Send a message via Alfred.
            
            - **notify**: Alfred sends message TO the user
            - **inject**: Message is processed AS IF user sent it
            """
            if not self.bot:
                logger.error("Bot not initialized")
                raise HTTPException(status_code=500, detail="Bot not ready")
            
            if not req.message.strip():
                raise HTTPException(status_code=400, detail="Message cannot be empty")
            
            try:
                if req.mode == "notify":
                    await self._notify_user(req.chat_id, req.message)
                else:
                    await self._inject_message(req.chat_id, req.message)
                
                logger.info(f"Message sent: mode={req.mode}, chat_id={req.chat_id}")
                return {"status": "ok"}
                
            except Exception as e:
                logger.exception(f"Failed to send message: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy"}
        
        return app
    
    async def _notify_user(self, chat_id: int, message: str) -> None:
        """Send a notification TO the user."""
        # Bot sends message directly to the chat
        await self.bot.send_message(chat_id=chat_id, text=message)
    
    async def _inject_message(self, chat_id: int, message: str) -> None:
        """Inject a message AS the user for Alfred to process."""
        # Create a fake update and process it
        # This makes Alfred respond as if the user said it
        await self.bot.inject_user_message(chat_id=chat_id, text=message)
    
    def run(self) -> None:
        """Run the API server."""
        import uvicorn
        uvicorn.run(
            self.app,
            host="127.0.0.1",
            port=self.config.api_port,
            log_level="warning",
        )
```

---

## Cron Management (src/cron.py)

```python
"""Crontab management for Alfred-managed jobs."""

import subprocess
import uuid
import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

COMMENT_PREFIX = "# alfred-job:"


@dataclass
class CronJob:
    """Represents an Alfred-managed cron job."""
    id: str
    schedule: str
    command: str
    comment_line: str
    job_line: str


class CronManager:
    """Manage Alfred's cron jobs."""
    
    def __init__(self, api_port: int) -> None:
        self.api_port = api_port
        self.base_url = f"http://127.0.0.1:{api_port}/message"
    
    def list_jobs(self) -> list[CronJob]:
        """List all Alfred-managed cron jobs."""
        crontab = self._read_crontab()
        jobs = []
        
        lines = crontab.strip().split("\n") if crontab else []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for Alfred job comment
            if line.startswith(COMMENT_PREFIX):
                job_id = line.replace(COMMENT_PREFIX, "").strip()
                
                # Next line should be the cron entry
                if i + 1 < len(lines):
                    job_line = lines[i + 1].strip()
                    if job_line and not job_line.startswith("#"):
                        parts = self._parse_cron_line(job_line)
                        if parts:
                            jobs.append(CronJob(
                                id=job_id,
                                schedule=parts["schedule"],
                                command=parts["command"],
                                comment_line=line,
                                job_line=job_line,
                            ))
                i += 2
            else:
                i += 1
        
        return jobs
    
    def add_job(
        self,
        schedule: str,
        mode: str,
        chat_id: int,
        message: str,
        job_id: Optional[str] = None,
    ) -> str:
        """Add a new cron job. Returns the job ID."""
        job_id = job_id or str(uuid.uuid4())
        
        # Build the curl command
        command = self._build_curl_command(mode, chat_id, message)
        
        # Build the crontab entry
        entry = f"{COMMENT_PREFIX} {job_id}\n{schedule} {command}\n"
        
        # Append to crontab
        self._append_to_crontab(entry)
        
        logger.info(f"Added cron job {job_id}: {schedule} {mode}")
        return job_id
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a cron job by ID. Returns True if found and removed."""
        crontab = self._read_crontab()
        if not crontab:
            return False
        
        lines = crontab.strip().split("\n")
        new_lines = []
        skip_next = False
        found = False
        
        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue
            
            if line.strip().startswith(COMMENT_PREFIX) and job_id in line:
                # Skip this comment and the next line (the job)
                skip_next = True
                found = True
                continue
            
            new_lines.append(line)
        
        if found:
            self._write_crontab("\n".join(new_lines) + "\n")
            logger.info(f"Removed cron job {job_id}")
        
        return found
    
    def get_job(self, job_id: str) -> Optional[CronJob]:
        """Get a specific job by ID."""
        for job in self.list_jobs():
            if job.id == job_id:
                return job
        return None
    
    def _build_curl_command(self, mode: str, chat_id: int, message: str) -> str:
        """Build curl command for the API call."""
        # Escape message for shell
        escaped_message = message.replace('"', '\\"')
        
        return (
            f'curl -s -X POST {self.base_url} '
            f'-H "Content-Type: application/json" '
            f'-d \'{{"mode":"{mode}","chat_id":{chat_id},"message":"{escaped_message}"}}\''
        )
    
    def _parse_cron_line(self, line: str) -> Optional[dict]:
        """Parse a cron line into schedule and command."""
        # Cron format: minute hour day month weekday command
        parts = line.split(None, 5)
        if len(parts) < 6:
            return None
        
        return {
            "schedule": " ".join(parts[:5]),
            "command": parts[5],
        }
    
    def _read_crontab(self) -> str:
        """Read current crontab."""
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout
            # No crontab exists
            return ""
        except FileNotFoundError:
            logger.warning("crontab command not found")
            return ""
    
    def _write_crontab(self, content: str) -> None:
        """Write content to crontab."""
        process = subprocess.Popen(
            ["crontab", "-"],
            stdin=subprocess.PIPE,
            text=True,
        )
        process.communicate(input=content)
        
        if process.returncode != 0:
            raise RuntimeError(f"Failed to write crontab: exit code {process.returncode}")
    
    def _append_to_crontab(self, entry: str) -> None:
        """Append an entry to crontab."""
        current = self._read_crontab()
        
        # Ensure crontab ends with newline
        if current and not current.endswith("\n"):
            current += "\n"
        
        new_content = current + entry
        self._write_crontab(new_content)
```

---

## Configuration

Add to `config.json`:

```json
{
  "api_port": 8080,
  "api_enabled": true
}
```

Update `src/config.py`:

```python
class Config(BaseSettings):
    # ... existing fields ...
    
    # API settings
    api_port: int = 8080
    api_enabled: bool = True
```

---

## Natural Language Integration

The LLM handles parsing directly. When user says:

> "Remind me to stand up every hour"

The LLM:
1. Recognizes this as a reminder request
2. Parses "every hour" → `0 * * * *`
3. Extracts message: "Time to stand up!"
4. Determines mode: `notify`
5. Calls `cron_manager.add_job()`

When user says:

> "Summarize our conversations every 3 days"

The LLM:
1. Recognizes this as a periodic task
2. Parses "every 3 days" → `0 0 */3 * *`
3. Extracts message: "Summarize our conversations"
4. Determines mode: `inject`
5. Calls `cron_manager.add_job()`

The LLM also handles listing:

> "What reminders do you have set?"

LLM calls `cron_manager.list_jobs()` and formats the response.

And removal:

> "Remove the stand-up reminder"

LLM finds job by description/ID and calls `cron_manager.remove_job()`.

---

## Dockerfile Updates

```dockerfile
# Add to existing Dockerfile

# Ensure cron service directory exists
RUN mkdir -p /var/spool/cron

# Update entrypoint to start crond
ENTRYPOINT ["/tini", "-s", "--", "bash", "-c", "crond && source /app/.venv/bin/activate && alfred"]
```

---

## Bot Integration

```python
# src/bot.py additions

from src.api import APIServer
from src.cron import CronManager


class AlfredBot:
    def __init__(self, config: Config, ...) -> None:
        # ... existing init ...
        self.api = APIServer(config, bot=self)
        self.cron = CronManager(config.api_port)
    
    async def send_message(self, chat_id: int, text: str) -> None:
        """Send a message to a chat (for API use)."""
        await self.application.bot.send_message(chat_id=chat_id, text=text)
    
    async def inject_user_message(self, chat_id: int, text: str) -> None:
        """Process a message as if the user sent it."""
        # Create minimal update structure for processing
        # Implementation depends on bot architecture
        pass
    
    async def start(self) -> None:
        """Start bot and API server."""
        # Start API in background task if enabled
        if self.config.api_enabled:
            asyncio.create_task(asyncio.to_thread(self.api.run()))
        
        # Start Telegram bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
```

---

## Tests

```python
# tests/test_cron.py

import pytest
from src.cron import CronManager, COMMENT_PREFIX


@pytest.fixture
def cron_manager():
    return CronManager(api_port=8080)


def test_build_curl_command(cron_manager):
    cmd = cron_manager._build_curl_command("notify", 123, "Hello world")
    
    assert "curl" in cmd
    assert "8080/message" in cmd
    assert '"mode":"notify"' in cmd
    assert '"chat_id":123' in cmd
    assert '"message":"Hello world"' in cmd


def test_build_curl_command_escapes_quotes(cron_manager):
    cmd = cron_manager._build_curl_command("notify", 123, 'Say "hi"')
    
    assert '\\"hi\\"' in cmd


def test_parse_cron_line(cron_manager):
    result = cron_manager._parse_cron_line("0 * * * * echo hello")
    
    assert result["schedule"] == "0 * * * *"
    assert result["command"] == "echo hello"


def test_parse_cron_line_invalid(cron_manager):
    result = cron_manager._parse_cron_line("not a cron line")
    
    assert result is None


# Integration tests would mock crontab commands
```

```python
# tests/test_api.py

import pytest
from fastapi.testclient import TestClient
from src.api import APIServer


@pytest.fixture
def api_server():
    from src.config import Config
    config = Config(
        telegram_bot_token="test",
        openai_api_key="test",
        kimi_api_key="test",
        api_port=8080,
    )
    return APIServer(config, bot=None)


@pytest.fixture
def client(api_server):
    return TestClient(api_server.app)


def test_health_endpoint(client):
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_message_requires_fields(client):
    response = client.post("/message", json={})
    
    assert response.status_code == 422  # Validation error


def test_message_empty_rejected(client):
    response = client.post("/message", json={
        "mode": "notify",
        "chat_id": 123,
        "message": "   ",
    })
    
    assert response.status_code == 400


def test_message_mode_must_be_valid(client):
    response = client.post("/message", json={
        "mode": "invalid",
        "chat_id": 123,
        "message": "hello",
    })
    
    assert response.status_code == 422
```

---

## Milestones

- [ ] **M1: HTTP API implementation** - FastAPI server with `/message` and `/health` endpoints
- [ ] **M2: Cron management** - `CronManager` class with add/list/remove operations
- [ ] **M3: Bot integration** - Wire API and cron into AlfredBot, implement `send_message` and `inject_user_message`
- [ ] **M4: Natural language interface** - LLM can create/list/remove cron jobs via conversation
- [ ] **M5: Dockerfile update** - Start crond in container entrypoint
- [ ] **M6: Tests and documentation** - Unit tests, README update

---

## Success Criteria

- [ ] `POST /message` accepts valid requests, returns 200
- [ ] `notify` mode sends message to user via Telegram
- [ ] `inject` mode processes message as if user sent it
- [ ] Cron jobs created with UUID comments
- [ ] Cron jobs listable by Alfred
- [ ] Cron jobs removable by UUID
- [ ] LLM can create jobs from natural language
- [ ] LLM can list and remove jobs conversationally
- [ ] crond starts automatically in Docker
- [ ] API port configurable via config file
- [ ] All tests pass

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | Use cron (not internal scheduler) | Simpler, leverages proven tool | Less code to maintain |
| 2026-02-17 | FastAPI for HTTP | Async, fits existing architecture | Consistent with bot |
| 2026-02-17 | Localhost only, no auth | Security via network isolation | Simpler implementation |
| 2026-02-17 | JSON request body | Extensible, standard | Easy to add fields later |
| 2026-02-17 | UUID for job tracking | Unique, no collisions | Simple job identification |
| 2026-02-17 | `crontab -e` for management | Standard, works in Docker | No special permissions |

---

## Open Questions

- [ ] Should we support timezone-aware schedules?
- [ ] Should we log cron job execution results somewhere Alfred can see?
- [ ] Should `inject` mode include any metadata (e.g., "This is a scheduled message")?
