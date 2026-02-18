# PRD: Skill System + Internal API

## Overview

**Issue**: #32
**Parent**: #10 (Alfred - The Rememberer)
**Status**: Planning
**Priority**: High
**Created**: 2026-02-17

Alfred implements Pi's philosophy: minimal core with four tools, everything else through skills. Skills access capabilities via an internal HTTP API.

---

## Problem Statement

Alfred needs a modular way for the LLM to trigger capabilities:
- Memory storage and retrieval
- Semantic search
- Context compaction
- Memory distillation
- Learning (updating agent files)

Hardcoding these as tool calls bloats the core. Pi solves this with skills—instructional markdown that tells the LLM *when* and *how* to accomplish tasks using only the four basic tools.

---

## Solution

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ALFRED (Python)                         │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │ Capabilities │◄───│  HTTP API   │◄───│  Four Tools         │  │
│  │ (built-in)   │    │  (FastAPI)  │    │  read, write,       │  │
│  │              │    │             │    │  edit, bash         │  │
│  │  - memory    │    │  /memories  │    │                     │  │
│  │  - search    │    │  /search    │    └──────────▲──────────┘  │
│  │  - distill   │    │  /distill   │               │           │
│  │  - compact   │    │  /compact   │               │           │
│  │  - learn     │    │  /learn     │               │           │
│  └─────────────┘    └─────────────┘               │           │
│                                                     │           │
└─────────────────────────────────────────────────────┼───────────┘
                                                      │
┌──────────────────────────────────────────────────────┼───────────┐
│                         SKILLS                       │           │
│                                                      │           │
│  ┌─────────────────┐                                │           │
│  │ remember/       │ ──► "POST /memories ..."       │           │
│  │   SKILL.md      │                                │           │
│  ├─────────────────┤                                │           │
│  │ search/         │ ──► "GET /search?q=..."        │           │
│  │   SKILL.md      │                                │           │
│  ├─────────────────┤                                │           │
│  │ distill/        │ ──► "POST /distill"            │           │
│  │   SKILL.md      │                                │           │
│  ├─────────────────┤                                │           │
│  │ learn/          │ ──► "POST /learn"              │           │
│  │   SKILL.md      │                                │           │
│  └─────────────────┘                                │           │
│                                                      │           │
│  Skills are markdown. They instruct the LLM          │           │
│  on WHEN and HOW to call the API.                   │           │
│                                                      │           │
│  LLM uses: bash + curl → API → capabilities         │           │
└──────────────────────────────────────────────────────────────────┘
```

### How It Works

1. **Skills load on startup** — Alfred scans skill directories, exposes skill descriptions to the LLM
2. **LLM recognizes need** — User request matches a skill's description
3. **LLM reads SKILL.md** — Uses `read` tool to load full instructions
4. **LLM executes via bash** — Follows skill's instructions to call API with curl
5. **API triggers capability** — In-process Python code performs the action
6. **Result returns to LLM** — API response informs next action

### Why This Approach

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Four tools only | Keep core minimal | Simplicity, consistency with Pi |
| Skills as markdown | Agent Skills standard | Interoperability, human-readable |
| HTTP API | In-process FastAPI | Skills trigger capabilities without Python code |
| curl via bash | LLM figures out syntax | No new tools needed, LLM is capable |

---

## The Four Tools

Alfred provides exactly four tools to the LLM:

### 1. `read` — Read file contents

```
parameters: { path: string, offset?: number, limit?: number }
```

Read any file: code, configs, skills, memories. Used to load SKILL.md files on demand.

### 2. `write` — Create or overwrite files

```
parameters: { path: string, content: string }
```

Create new files or completely replace existing ones.

### 3. `edit` — Make precise edits

```
parameters: { path: string, oldText: string, newText: string }
```

Find and replace exact text. For surgical modifications.

### 4. `bash` — Execute shell commands

```
parameters: { command: string, timeout?: number }
```

Run any shell command. Skills use this to call the API via curl.

---

## Skill System

### Agent Skills Standard

Alfred implements the [Agent Skills standard](https://agentskills.io/specification):

- **SKILL.md format** — YAML frontmatter + markdown instructions
- **Progressive disclosure** — Descriptions in system prompt, full content loaded on demand
- **Relative paths** — Skills reference assets relative to their directory

### Skill Locations

```
~/.alfred/skills/          # Global skills (user-installed)
/project/.alfred/skills/   # Project skills (team-shared)
alfred/skills/             # Bundled skills (shipped with Alfred)
```

Discovery rules:
- Direct `.md` files in skills directory root
- `SKILL.md` files in subdirectories

### Skill Structure

```
remember/
├── SKILL.md           # Required: frontmatter + instructions
├── references/        # Optional: detailed docs
│   └── api-details.md
└── examples/          # Optional: example usage
    └── curl-examples.txt
```

### SKILL.md Format

```markdown
---
name: remember
description: Store information to Alfred's long-term memory. Use when the user shares important preferences, facts about themselves, or anything worth remembering for future conversations.
---

# Remember Skill

Store information to memory so Alfred can recall it later.

## When to Use

- User shares a preference ("I prefer dark mode")
- User mentions important context ("My project uses Python 3.11")
- User wants something remembered ("Remember that my birthday is March 15")

## How to Use

Call the API to store a memory:

\`\`\`bash
curl -s -X POST http://localhost:${ALFRED_API_PORT}/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "The memory content to store",
    "importance": 0.8,
    "tags": ["preference", "coding"]
  }'
\`\`\`

### Parameters

- **content** (required): The memory text to store
- **importance** (optional): 0.0-1.0, higher = more likely to retrieve. Default: 0.5
- **tags** (optional): Array of strings for categorization

### Response

Returns JSON with the created memory ID and timestamp.

## Example

User: "Remember that I use Neovim for editing"

\`\`\`bash
curl -s -X POST http://localhost:8080/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "User uses Neovim for code editing", "importance": 0.6, "tags": ["preference", "editor"]}'
\`\`\`
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Lowercase a-z, 0-9, hyphens. Must match directory name. |
| `description` | Yes | When to use this skill (shown in system prompt) |
| `license` | No | License name |
| `compatibility` | No | Environment requirements |
| `metadata` | No | Arbitrary key-value data |

### Bundled Skills

Alfred ships with core skills:

| Skill | Description | API Endpoint |
|-------|-------------|--------------|
| `remember` | Store to long-term memory | `POST /memories` |
| `recall` | Search memories | `GET /search` |
| `distill` | Extract insights to MEMORY.md | `POST /distill` |
| `learn` | Update agent files (USER.md, SOUL.md) | `POST /learn` |
| `compact` | Summarize long context | `POST /compact` |

Additional skills can be installed to `~/.alfred/skills/` or bundled in projects.

---

## HTTP API

### Specification (API.md)

```markdown
# Alfred Internal API

Base URL: http://localhost:${ALFRED_API_PORT}
Default port: 8080

All endpoints return JSON.

## Error Handling

All errors follow this standard format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": {}  # Optional additional context
  }
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request (invalid parameters)
- `404` - Not Found
- `409` - Conflict (e.g., duplicate ID)
- `422` - Unprocessable Entity (validation failed)
- `500` - Internal Server Error

---

## Endpoints

### Health

#### Check Health

GET /health

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-17T15:30:00Z"
}
```

---

### Memory Endpoints

#### Store Memory

POST /memories

Create a new memory.

Request:
```json
{
  "content": string,      # Required: Memory text to store
  "importance": number?,  # Optional: 0.0-1.0, default 0.5
  "tags": string[]?       # Optional: Array of tag strings
}
```

Response (201 Created):
```json
{
  "id": string,           # UUID for the memory
  "timestamp": string,    # ISO 8601 timestamp
  "content": string,      # Echo back the content
  "importance": number,
  "tags": string[]
}
```

Errors:
- `400` - Content is empty or invalid
- `422` - Importance out of range (must be 0.0-1.0)

---

#### Get Memory

GET /memories/{id}

Retrieve a specific memory by ID.

Path params:
- id: string  # Memory UUID

Response (200 OK):
```json
{
  "id": string,
  "content": string,
  "date": string,         # Date stored (YYYY-MM-DD)
  "timestamp": string,    # Full ISO timestamp
  "importance": number,
  "tags": string[],
  "source": string        # "daily" or "memory"
}
```

Errors:
- `404` - Memory not found

---

#### Update Memory

PUT /memories/{id}

Update an existing memory. Only provided fields are updated.

Path params:
- id: string  # Memory UUID

Request:
```json
{
  "content": string?,     # Optional: New content
  "importance": number?,  # Optional: New importance (0.0-1.0)
  "tags": string[]?       # Optional: Replace tags entirely
}
```

Response (200 OK):
```json
{
  "id": string,
  "timestamp": string,    # Original timestamp preserved
  "updated_at": string,   # When update occurred
  "content": string,
  "importance": number,
  "tags": string[]
}
```

Errors:
- `404` - Memory not found
- `422` - Importance out of range

---

#### Delete Memory

DELETE /memories/{id}

Delete a memory by ID.

Path params:
- id: string  # Memory UUID

Response (200 OK):
```json
{
  "id": string,
  "deleted": true,
  "timestamp": string  # When deletion occurred
}
```

Errors:
- `404` - Memory not found

---

#### Batch Delete Memories

DELETE /memories

Delete multiple memories by ID.

Request:
```json
{
  "ids": string[]  # Array of memory UUIDs to delete
}
```

Response (200 OK):
```json
{
  "deleted": number,      # Count successfully deleted
  "not_found": string[],  # IDs that didn't exist
  "timestamp": string
}
```

Errors:
- `400` - IDs array is empty or invalid

---

#### List Memories

GET /memories

List memories with pagination and filtering.

Query params:
- date: string?          # Filter by date (YYYY-MM-DD)
- tag: string?           # Filter by tag (exact match)
- source: string?        # Filter by source ("daily" | "memory")
- limit: number?         # Max results per page, default 20, max 100
- offset: number?        # Pagination offset, default 0
- sort_by: string?       # Sort field ("date" | "importance"), default "date"
- sort_order: string?    # "asc" | "desc", default "desc"

Response (200 OK):
```json
{
  "memories": [
    {
      "id": string,
      "content": string,
      "date": string,
      "timestamp": string,
      "importance": number,
      "tags": string[],
      "source": string
    }
  ],
  "pagination": {
    "total": number,      # Total matching memories
    "limit": number,      # Current page size
    "offset": number,     # Current offset
    "has_more": boolean   # Whether more results exist
  }
}
```

---

#### Batch Create Memories

POST /memories/batch

Create multiple memories in one request.

Request:
```json
{
  "memories": [
    {
      "content": string,
      "importance": number?,
      "tags": string[]?
    }
  ]
}
```

Response (201 Created):
```json
{
  "created": number,          # Count successfully created
  "memories": [
    {
      "id": string,
      "timestamp": string,
      "content": string,
      "importance": number,
      "tags": string[]
    }
  ],
  "errors": [                 # Any that failed validation
    {
      "index": number,        # Index in request array
      "error": string         # Error message
    }
  ]
}
```

---

#### Search Memories

GET /search

Semantic search across all memories.

Query params:
- q: string              # Required: Search query
- limit: number?         # Max results, default 10, max 50
- min_score: number?     # Minimum similarity (0.0-1.0), default 0.0
- source: string?        # Filter by source ("daily" | "memory")

Response (200 OK):
```json
{
  "results": [
    {
      "id": string,
      "content": string,
      "date": string,
      "timestamp": string,
      "importance": number,
      "tags": string[],
      "source": string,
      "score": number       # Similarity score 0.0-1.0
    }
  ],
  "query": string,
  "total": number,        # Total matches before limit
  "search_time_ms": number
}
```

Errors:
- `400` - Query is empty

---

### Capability Endpoints

#### Distill Insights

POST /distill

Triggers the distillation system to extract insights from recent conversations and write to MEMORY.md.

Request:
```json
{
  "scope": "recent" | "all",  # What to analyze
  "focus": string?,            # Optional: Topic to focus on
  "since": string?             # Optional: ISO timestamp, analyze from this time
}
```

Response (200 OK):
```json
{
  "status": "completed",
  "insights_added": number,
  "memory_file": string,
  "processed_memories": number,
  "duration_ms": number
}
```

Response (202 Accepted) - if processing is async:
```json
{
  "status": "processing",
  "job_id": string
}
```

---

#### Learn

POST /learn

Updates agent files (USER.md, SOUL.md) based on observed patterns.

Request:
```json
{
  "target": "user" | "soul",  # Which file to update
  "observation": string,       # What was learned
  "confidence": number?         # Optional: 0.0-1.0 confidence level
}
```

Response (200 OK):
```json
{
  "status": "updated",
  "file": string,
  "changes": string[],         # List of changes made
  "backup_created": string     # Path to backup file
}
```

Response (200 OK) - if no changes needed:
```json
{
  "status": "no_change",
  "file": string,
  "reason": string
}
```

Errors:
- `400` - Invalid target (must be "user" or "soul")
- `422` - Observation is empty

---

#### Compact Context

POST /compact

Triggers context compaction for the current session.

Request:
```json
{
  "instructions": string?,     # Optional: Custom instructions for summarization
  "preserve_recent": number?   # Optional: Number of recent messages to preserve
}
```

Response (200 OK):
```json
{
  "status": "completed",
  "tokens_before": number,
  "tokens_after": number,
  "tokens_saved": number,
  "summary": string,
  "messages_compacted": number
}
```

---

### System Endpoints

#### Get API Info

GET /

Returns API information and available endpoints.

Response (200 OK):
```json
{
  "name": "Alfred Internal API",
  "version": "1.0.0",
  "endpoints": [
    {
      "path": "/health",
      "methods": ["GET"],
      "description": "Health check"
    },
    {
      "path": "/memories",
      "methods": ["GET", "POST", "DELETE"],
      "description": "Memory management"
    },
    {
      "path": "/search",
      "methods": ["GET"],
      "description": "Semantic search"
    },
    {
      "path": "/distill",
      "methods": ["POST"],
      "description": "Extract insights to MEMORY.md"
    },
    {
      "path": "/learn",
      "methods": ["POST"],
      "description": "Update agent files"
    },
    {
      "path": "/compact",
      "methods": ["POST"],
      "description": "Summarize context"
    }
  ]
}
```
```

### API Server (src/api.py)

```python
"""Alfred Internal HTTP API."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from src.config import Config
from src.memory import MemoryManager
from src.search import SearchEngine
from src.distillation import Distiller
from src.learning import Learner
from src.compaction import Compactor

logger = logging.getLogger(__name__)


# Request/Response Models

# Error response model
class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


# Health
class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    timestamp: str


# Memory CRUD
class MemoryCreate(BaseModel):
    content: str
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class MemoryResponse(BaseModel):
    id: str
    timestamp: str
    content: str
    importance: float
    tags: list[str]


class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    importance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tags: Optional[list[str]] = None


class Memory(BaseModel):
    id: str
    content: str
    date: str
    timestamp: str
    importance: float
    tags: list[str]
    source: str


class PaginationInfo(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class MemoryList(BaseModel):
    memories: list[Memory]
    pagination: PaginationInfo


# Batch operations
class BatchMemoryCreate(BaseModel):
    memories: list[MemoryCreate]


class BatchMemoryCreateResult(BaseModel):
    index: int
    error: str


class BatchMemoryCreateResponse(BaseModel):
    created: int
    memories: list[MemoryResponse]
    errors: list[BatchMemoryCreateResult]


class BatchMemoryDelete(BaseModel):
    ids: list[str]


class BatchMemoryDeleteResponse(BaseModel):
    deleted: int
    not_found: list[str]
    timestamp: str


# Search
class SearchResult(BaseModel):
    id: str
    content: str
    date: str
    timestamp: str
    importance: float
    tags: list[str]
    source: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    total: int
    search_time_ms: int


# Capabilities
class DistillRequest(BaseModel):
    scope: str = "recent"
    focus: Optional[str] = None
    since: Optional[str] = None


class DistillResponse(BaseModel):
    status: str
    insights_added: int
    memory_file: str
    processed_memories: int
    duration_ms: int


class LearnRequest(BaseModel):
    target: str
    observation: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class LearnResponse(BaseModel):
    status: str
    file: str
    changes: list[str]
    backup_created: str


class CompactRequest(BaseModel):
    instructions: Optional[str] = None
    preserve_recent: Optional[int] = None


class CompactResponse(BaseModel):
    status: str
    tokens_before: int
    tokens_after: int
    tokens_saved: int
    summary: str
    messages_compacted: int


# API Info
class EndpointInfo(BaseModel):
    path: str
    methods: list[str]
    description: str


class APIInfoResponse(BaseModel):
    name: str
    version: str
    endpoints: list[EndpointInfo]


# API Server

class APIServer:
    """FastAPI server for Alfred's internal API."""

    def __init__(
        self,
        config: Config,
        memory: MemoryManager,
        search: SearchEngine,
        distiller: Distiller,
        learner: Learner,
        compactor: Compactor,
    ) -> None:
        self.config = config
        self.memory = memory
        self.search = search
        self.distiller = distiller
        self.learner = learner
        self.compactor = compactor
        self.app = self._create_app()

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        logger.info(f"Alfred API starting on port {self.config.api_port}")
        yield
        logger.info("Alfred API shutting down")

    def _create_app(self) -> FastAPI:
        app = FastAPI(
            title="Alfred API",
            description="Internal HTTP API for skill-triggered capabilities",
            version="1.0.0",
            lifespan=self.lifespan,
        )

        # API Info
        @app.get("/", response_model=APIInfoResponse)
        async def api_info():
            return APIInfoResponse(
                name="Alfred Internal API",
                version="1.0.0",
                endpoints=[
                    EndpointInfo(path="/health", methods=["GET"], description="Health check"),
                    EndpointInfo(path="/memories", methods=["GET", "POST", "DELETE"], description="Memory management"),
                    EndpointInfo(path="/search", methods=["GET"], description="Semantic search"),
                    EndpointInfo(path="/distill", methods=["POST"], description="Extract insights to MEMORY.md"),
                    EndpointInfo(path="/learn", methods=["POST"], description="Update agent files"),
                    EndpointInfo(path="/compact", methods=["POST"], description="Summarize context"),
                ]
            )

        # Health
        @app.get("/health", response_model=HealthResponse)
        async def health():
            from datetime import datetime, timezone
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        # Memory endpoints - CRUD
        @app.post("/memories", response_model=MemoryResponse, status_code=201)
        async def create_memory(req: MemoryCreate):
            if not req.content or not req.content.strip():
                raise HTTPException(400, detail={
                    "error": {"code": "INVALID_CONTENT", "message": "Content cannot be empty"}
                })
            result = self.memory.store(
                content=req.content,
                importance=req.importance,
                tags=req.tags,
            )
            return MemoryResponse(
                id=result.id,
                timestamp=result.timestamp,
                content=req.content,
                importance=req.importance,
                tags=req.tags,
            )

        @app.get("/memories/{memory_id}", response_model=Memory)
        async def get_memory(memory_id: str):
            memory = self.memory.get(memory_id)
            if not memory:
                raise HTTPException(404, detail={
                    "error": {"code": "NOT_FOUND", "message": f"Memory {memory_id} not found"}
                })
            return Memory(**memory)

        @app.put("/memories/{memory_id}", response_model=Memory)
        async def update_memory(memory_id: str, req: MemoryUpdate):
            memory = self.memory.get(memory_id)
            if not memory:
                raise HTTPException(404, detail={
                    "error": {"code": "NOT_FOUND", "message": f"Memory {memory_id} not found"}
                })
            updated = self.memory.update(
                memory_id,
                content=req.content,
                importance=req.importance,
                tags=req.tags,
            )
            return Memory(**updated)

        @app.delete("/memories/{memory_id}")
        async def delete_memory(memory_id: str):
            deleted = self.memory.delete(memory_id)
            if not deleted:
                raise HTTPException(404, detail={
                    "error": {"code": "NOT_FOUND", "message": f"Memory {memory_id} not found"}
                })
            from datetime import datetime, timezone
            return {
                "id": memory_id,
                "deleted": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        @app.delete("/memories")
        async def batch_delete_memories(req: BatchMemoryDelete):
            if not req.ids:
                raise HTTPException(400, detail={
                    "error": {"code": "INVALID_REQUEST", "message": "IDs array cannot be empty"}
                })
            result = self.memory.batch_delete(req.ids)
            from datetime import datetime, timezone
            return BatchMemoryDeleteResponse(
                deleted=result["deleted"],
                not_found=result["not_found"],
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        @app.get("/memories", response_model=MemoryList)
        async def list_memories(
            date: Optional[str] = Query(None),
            tag: Optional[str] = Query(None),
            source: Optional[str] = Query(None),
            limit: int = Query(20, ge=1, le=100),
            offset: int = Query(0, ge=0),
            sort_by: str = Query("date", regex="^(date|importance)$"),
            sort_order: str = Query("desc", regex="^(asc|desc)$"),
        ):
            memories, total = self.memory.list(
                date_filter=date,
                tag_filter=tag,
                source_filter=source,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            return MemoryList(
                memories=[Memory(**m) for m in memories],
                pagination=PaginationInfo(
                    total=total,
                    limit=limit,
                    offset=offset,
                    has_more=(offset + limit) < total
                )
            )

        @app.post("/memories/batch", response_model=BatchMemoryCreateResponse, status_code=201)
        async def batch_create_memories(req: BatchMemoryCreate):
            if not req.memories:
                raise HTTPException(400, detail={
                    "error": {"code": "INVALID_REQUEST", "message": "Memories array cannot be empty"}
                })
            
            created_memories = []
            errors = []
            
            for i, mem in enumerate(req.memories):
                try:
                    if not mem.content or not mem.content.strip():
                        errors.append(BatchMemoryCreateResult(
                            index=i,
                            error="Content cannot be empty"
                        ))
                        continue
                    
                    result = self.memory.store(
                        content=mem.content,
                        importance=mem.importance,
                        tags=mem.tags,
                    )
                    created_memories.append(MemoryResponse(
                        id=result.id,
                        timestamp=result.timestamp,
                        content=mem.content,
                        importance=mem.importance,
                        tags=mem.tags,
                    ))
                except Exception as e:
                    errors.append(BatchMemoryCreateResult(
                        index=i,
                        error=str(e)
                    ))
            
            return BatchMemoryCreateResponse(
                created=len(created_memories),
                memories=created_memories,
                errors=errors
            )

        @app.get("/search", response_model=SearchResponse)
        async def search_memories(
            q: str = Query(..., min_length=1),
            limit: int = Query(10, ge=1, le=50),
            min_score: float = Query(0.0, ge=0.0, le=1.0),
            source: Optional[str] = Query(None),
        ):
            import time
            start_time = time.time()
            
            results, total = self.search.search(
                query=q,
                limit=limit,
                min_score=min_score,
                source_filter=source,
            )
            
            search_time = int((time.time() - start_time) * 1000)
            
            return SearchResponse(
                results=[SearchResult(**r) for r in results],
                query=q,
                total=total,
                search_time_ms=search_time,
            )

        # Capability endpoints
        @app.post("/distill", response_model=DistillResponse)
        async def distill(req: DistillRequest):
            result = self.distiller.distill(
                scope=req.scope,
                focus=req.focus,
                since=req.since,
            )
            return DistillResponse(**result)

        @app.post("/learn", response_model=LearnResponse)
        async def learn(req: LearnRequest):
            if req.target not in ("user", "soul"):
                raise HTTPException(400, detail={
                    "error": {"code": "INVALID_TARGET", "message": "target must be 'user' or 'soul'"}
                })
            if not req.observation or not req.observation.strip():
                raise HTTPException(422, detail={
                    "error": {"code": "INVALID_OBSERVATION", "message": "Observation cannot be empty"}
                })
            result = self.learner.learn(
                target=req.target,
                observation=req.observation,
                confidence=req.confidence,
            )
            return LearnResponse(**result)

        @app.post("/compact", response_model=CompactResponse)
        async def compact(req: CompactRequest):
            result = self.compactor.compact(
                instructions=req.instructions,
                preserve_recent=req.preserve_recent,
            )
            return CompactResponse(**result)

        return app

    def run(self) -> None:
        import uvicorn
        uvicorn.run(
            self.app,
            host="127.0.0.1",
            port=self.config.api_port,
            log_level="warning",
        )
```

---

## Integration

### Bot Startup (src/bot.py)

```python
from src.api import APIServer

class AlfredBot:
    def __init__(self, config: Config, ...) -> None:
        # ... existing init ...
        self.api = APIServer(
            config=config,
            memory=self.memory,
            search=self.search,
            distiller=self.distiller,
            learner=self.learner,
            compactor=self.compactor,
        )

    async def start(self) -> None:
        # Start API server in background
        if self.config.api_enabled:
            import asyncio
            asyncio.create_task(asyncio.to_thread(self.api.run))

        # Start Telegram bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
```

### Skill Loading (src/skills.py)

```python
"""Skill discovery and loading."""

import os
from pathlib import Path
from dataclasses import dataclass
import yaml

@dataclass
class Skill:
    name: str
    description: str
    path: Path


class SkillLoader:
    """Load and manage skills."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.skills: dict[str, Skill] = {}
        self._discover()

    def _discover(self) -> None:
        """Scan skill directories and load metadata."""
        search_paths = [
            Path.home() / ".alfred" / "skills",      # Global
            Path.cwd() / ".alfred" / "skills",       # Project
            Path(__file__).parent / "skills",        # Bundled
        ]

        for base_path in search_paths:
            if not base_path.exists():
                continue

            # Direct .md files
            for md_file in base_path.glob("*.md"):
                self._load_skill(md_file)

            # SKILL.md in subdirectories
            for skill_file in base_path.glob("*/SKILL.md"):
                self._load_skill(skill_file)

    def _load_skill(self, path: Path) -> None:
        """Load skill metadata from SKILL.md."""
        try:
            content = path.read_text()
            frontmatter, _ = self._parse_frontmatter(content)

            if not frontmatter:
                return

            name = frontmatter.get("name", "")
            description = frontmatter.get("description", "")

            if name and description:
                self.skills[name] = Skill(
                    name=name,
                    description=description,
                    path=path,
                )
        except Exception as e:
            logger.warning(f"Failed to load skill {path}: {e}")

    def _parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from markdown."""
        if not content.startswith("---"):
            return {}, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        try:
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return frontmatter or {}, body
        except yaml.YAMLError:
            return {}, content

    def get_skill_descriptions(self) -> list[str]:
        """Get skill descriptions for system prompt."""
        return [
            f"- **{skill.name}**: {skill.description}"
            for skill in self.skills.values()
        ]

    def get_skill_path(self, name: str) -> Path | None:
        """Get path to a skill's SKILL.md."""
        skill = self.skills.get(name)
        return skill.path if skill else None
```

### Context Assembly (src/context.py)

```python
def build_system_prompt(skills: SkillLoader, ...) -> str:
    """Build system prompt with skill descriptions."""
    parts = [
        "# Alfred - Your AI Assistant",
        "",
        "## Available Skills",
        "",
        *skills.get_skill_descriptions(),
        "",
        "To use a skill, read its SKILL.md file with the read tool.",
        "",
        "## Available Tools",
        "",
        "- read: Read file contents",
        "- write: Create or overwrite files",
        "- edit: Make precise edits to files",
        "- bash: Execute shell commands",
        "",
        "## API Access",
        "",
        f"The internal API is at http://localhost:{config.api_port}",
        "Use curl via bash to call API endpoints.",
        "",
        # ... rest of system prompt ...
    ]
    return "\n".join(parts)
```

---

## File Structure

```
alfred/
├── src/
│   ├── api.py              # FastAPI server (this PRD)
│   ├── skills.py           # Skill loading (this PRD)
│   ├── bot.py              # Updated to start API
│   ├── context.py          # Updated to include skills
│   ├── memory.py           # M3 (existing)
│   ├── search.py           # M4 (existing)
│   ├── distillation.py     # M10 (existing)
│   ├── learning.py         # M11 (existing)
│   └── compaction.py       # M9 (existing)
├── skills/                 # Bundled skills (this PRD)
│   ├── remember/
│   │   └── SKILL.md
│   ├── recall/
│   │   └── SKILL.md
│   ├── distill/
│   │   └── SKILL.md
│   ├── learn/
│   │   └── SKILL.md
│   └── compact/
│       └── SKILL.md
└── API.md                  # API specification (this PRD)
```

---

## Milestones

| # | Milestone | Description |
|---|-----------|-------------|
| **1** | API Foundation | FastAPI server with `/health`, startup integration |
| **2** | Memory Endpoints | `/memories` CRUD, `/search` semantic retrieval |
| **3** | Capability Endpoints | `/distill`, `/learn`, `/compact` |
| **4** | Skill Loader | SKILL.md discovery, frontmatter parsing, descriptions |
| **5** | Bundled Skills | Create 5 core skills (remember, recall, distill, learn, compact) |
| **6** | Integration | Wire into bot startup, context assembly, test end-to-end |

---

## Acceptance Criteria

- [ ] FastAPI server runs on configurable port (default 8080)
- [ ] `/health` endpoint returns `{"status": "healthy"}`
- [ ] `/memories` endpoint stores and retrieves memories
- [ ] `/search` endpoint returns semantic search results
- [ ] `/distill` endpoint triggers distillation
- [ ] `/learn` endpoint updates agent files
- [ ] `/compact` endpoint triggers context compaction
- [ ] Skills load from `~/.alfred/skills/`, `.alfred/skills/`, and bundled
- [ ] Skill descriptions appear in system prompt
- [ ] LLM can load SKILL.md via `read` tool
- [ ] LLM can call API via `bash` + `curl`
- [ ] API server starts automatically with bot
- [ ] All endpoints return proper error responses

---

## Tests

```python
# tests/test_api.py

import pytest
from fastapi.testclient import TestClient
from src.api import APIServer


@pytest.fixture
def client():
    # Create mock dependencies
    config = Config(api_port=8080, ...)
    memory = MockMemoryManager()
    search = MockSearchEngine()
    distiller = MockDistiller()
    learner = MockLearner()
    compactor = MockCompactor()

    server = APIServer(config, memory, search, distiller, learner, compactor)
    return TestClient(server.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_memory(client):
    response = client.post("/memories", json={
        "content": "Test memory",
        "importance": 0.8,
        "tags": ["test"],
    })
    assert response.status_code == 200
    assert "id" in response.json()


def test_search_memories(client):
    response = client.get("/search", params={"q": "test query"})
    assert response.status_code == 200
    assert "results" in response.json()


def test_distill(client):
    response = client.post("/distill", json={"scope": "recent"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
```

```python
# tests/test_skills.py

from src.skills import SkillLoader


def test_load_bundled_skills():
    loader = SkillLoader(config)
    assert "remember" in loader.skills
    assert "recall" in loader.skills


def test_skill_has_description():
    loader = SkillLoader(config)
    skill = loader.skills["remember"]
    assert skill.description
    assert len(skill.description) < 1024  # Agent Skills spec


def test_get_skill_descriptions():
    loader = SkillLoader(config)
    descriptions = loader.get_skill_descriptions()
    assert any("remember" in d for d in descriptions)
```

---

## Success Criteria

- [ ] LLM uses skills to accomplish tasks without hardcoded tools
- [ ] Skills are human-readable markdown files
- [ ] Adding a new skill requires only creating a directory
- [ ] API responds in under 100ms for all endpoints
- [ ] No API authentication needed (localhost only)
- [ ] Skills work identically whether bundled or user-installed

---

## Dependencies

- **FastAPI** — API framework
- **Uvicorn** — ASGI server
- **PyYAML** — Frontmatter parsing
- **Existing capabilities** — Memory, search, distillation, learning, compaction

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | Four tools only | Pi philosophy, minimal core | LLM uses bash + curl |
| 2026-02-17 | Skills as markdown | Agent Skills standard | Interoperable, human-readable |
| 2026-02-17 | HTTP API for capabilities | Skills trigger actions without Python | In-process, no external deps |
| 2026-02-17 | No API tool | LLM can figure out curl | Simpler, fewer tools |
| 2026-02-17 | Localhost only | Security via network isolation | No auth needed |

---

## Notes

- This PRD defines the skill system and API, not the capabilities themselves
- Capabilities (memory, search, etc.) remain defined in milestones #11-21
- Skills are the *interface* to capabilities, not the implementation
- Third-party skills can be installed to `~/.alfred/skills/`
