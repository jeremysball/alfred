# PRD: Observability and Logging System

## Overview

**Issue**: #25  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #12 (M2: Core Infrastructure), #16 (M6: Kimi Provider)  
**Status**: Planning  
**Priority**: Medium  
**Created**: 2026-02-17

Implement comprehensive observability with structured logging, metrics tracking, and health monitoring for Alfred.

---

## Problem Statement

Alfred currently operates in the dark:
- No visibility into LLM API calls, response times, or token usage
- Context loading failures are silent or logged to console only
- Memory operations (search, add, retrieve) have no metrics
- No way to detect performance degradation or errors in production
- Debugging issues requires adding print statements manually

---

## Solution

Build observability infrastructure:
1. Structured JSON logging for all operations
2. Metrics collection (timers, counters, gauges)
3. Health check endpoints for monitoring
4. Correlation IDs for request tracing
5. Configurable log levels and outputs

---

## Acceptance Criteria

- [ ] `src/logging_config.py` - Structured logging setup with JSON formatter
- [ ] `src/metrics.py` - Metrics collection (timers, counters, histograms)
- [ ] `src/health.py` - Health check endpoints and status reporting
- [ ] Correlation ID propagation through async context
- [ ] LLM API call logging (request/response, timing, token usage)
- [ ] Context loading metrics (cache hits/misses, load times)
- [ ] Memory operation metrics (search latency, storage operations)
- [ ] Configurable log levels via environment variables
- [ ] Log rotation and retention configuration

---

## File Structure

```
src/
├── logging_config.py   # Structured logging setup
├── metrics.py          # Metrics collection
├── health.py           # Health checks and status
└── middleware.py       # Correlation ID and request logging
```

---

## Logging Config (src/logging_config.py)

```python
"""Structured logging configuration for Alfred."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "token_usage"):
            log_data["token_usage"] = record.token_usage
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


def setup_logging(
    level: str = "INFO",
    json_output: bool = True,
    log_file: Path | None = None,
) -> None:
    """Configure structured logging for Alfred.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_output: Whether to use JSON formatting
        log_file: Optional file path for log output
    """
    handlers: list[logging.Handler] = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_output:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True,
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
```

---

## Metrics (src/metrics.py)

```python
"""Metrics collection for Alfred observability."""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Timer:
    """Context manager for timing operations."""
    name: str
    callback: Callable[[str, float], None]
    _start: float = field(default=0.0, init=False)
    
    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self
    
    def __exit__(self, *args: Any) -> None:
        duration = (time.perf_counter() - self._start) * 1000  # ms
        self.callback(self.name, duration)


class MetricsCollector:
    """Collect and report metrics for Alfred operations."""
    
    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._timers: dict[str, list[float]] = {}
        self._gauges: dict[str, float] = {}
    
    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        self._counters[name] = self._counters.get(name, 0) + value
    
    def record_timer(self, name: str, duration_ms: float) -> None:
        """Record a timer metric."""
        if name not in self._timers:
            self._timers[name] = []
        self._timers[name].append(duration_ms)
    
    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge metric."""
        self._gauges[name] = value
    
    @contextmanager
    def timer(self, name: str):
        """Context manager for timing operations."""
        with Timer(name, self.record_timer):
            yield
    
    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        summary = {
            "counters": self._counters.copy(),
            "gauges": self._gauges.copy(),
        }
        
        # Calculate timer statistics
        timer_stats = {}
        for name, values in self._timers.items():
            if values:
                timer_stats[name] = {
                    "count": len(values),
                    "avg_ms": sum(values) / len(values),
                    "min_ms": min(values),
                    "max_ms": max(values),
                }
        summary["timers"] = timer_stats
        
        return summary
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._timers.clear()
        self._gauges.clear()


# Global metrics instance
metrics = MetricsCollector()
```

---

## Health Checks (src/health.py)

```python
"""Health check endpoints and status reporting."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Awaitable

from src.config import Config


@dataclass
class HealthStatus:
    status: str  # "healthy", "degraded", "unhealthy"
    checks: dict[str, dict]
    timestamp: datetime


class HealthChecker:
    """Health check coordinator."""
    
    def __init__(self) -> None:
        self._checks: dict[str, Callable[[], Awaitable[dict]]] = {}
    
    def register(
        self, name: str, check: Callable[[], Awaitable[dict]]
    ) -> None:
        """Register a health check."""
        self._checks[name] = check
    
    async def check(self) -> HealthStatus:
        """Run all health checks."""
        results = {}
        overall_status = "healthy"
        
        for name, check in self._checks.items():
            try:
                result = await asyncio.wait_for(check(), timeout=5.0)
                results[name] = result
                if result.get("status") != "healthy":
                    overall_status = "degraded"
            except Exception as e:
                results[name] = {"status": "unhealthy", "error": str(e)}
                overall_status = "unhealthy"
        
        return HealthStatus(
            status=overall_status,
            checks=results,
            timestamp=datetime.utcnow(),
        )


# Built-in health checks
async def check_config(config: Config) -> dict:
    """Validate configuration is loaded."""
    return {
        "status": "healthy" if config.telegram_bot_token else "unhealthy",
        "checks": {
            "telegram_token": bool(config.telegram_bot_token),
            "kimi_key": bool(config.kimi_api_key),
            "openai_key": bool(config.openai_api_key),
        },
    }


async def check_context_files(config: Config) -> dict:
    """Check context files are accessible."""
    missing = []
    for name, path in config.context_files.items():
        if not path.exists():
            missing.append(name)
    
    return {
        "status": "unhealthy" if missing else "healthy",
        "missing_files": missing,
    }
```

---

## Middleware (src/middleware.py)

```python
"""Request middleware for correlation IDs and logging."""

import contextvars
import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

# Context variable for correlation ID
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def get_correlation_id() -> str:
    """Get current correlation ID."""
    return correlation_id_var.get()


@asynccontextmanager
async def correlation_context() -> AsyncIterator[str]:
    """Create a correlation ID context."""
    cid = str(uuid.uuid4())[:8]
    token = correlation_id_var.set(cid)
    try:
        yield cid
    finally:
        correlation_id_var.reset(token)


def add_correlation_id(record: logging.LogRecord) -> None:
    """Add correlation ID to log record."""
    record.correlation_id = get_correlation_id()


class CorrelationIdFilter(logging.Filter):
    """Filter that adds correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True
```

---

## Integration with Existing Code

### Updated Context Loader with Metrics

```python
# In src/context.py

import logging
from src.metrics import metrics

logger = logging.getLogger(__name__)

class ContextLoader:
    async def load_file(self, name: str, path: Path) -> ContextFile:
        """Load a context file with logging and metrics."""
        logger.info("Loading context file", extra={
            "operation": "context_load",
            "file_name": name,
            "file_path": str(path),
        })
        
        with metrics.timer(f"context.load.{name}"):
            # Check cache first
            cached = self._cache.get(name)
            if cached:
                metrics.increment("context.cache.hit")
                logger.debug("Cache hit for context file", extra={
                    "file_name": name,
                })
                return cached
            
            metrics.increment("context.cache.miss")
            
            if not path.exists():
                logger.error("Context file missing", extra={
                    "file_name": name,
                    "file_path": str(path),
                })
                raise FileNotFoundError(f"Required context file missing: {path}")
            
            # ... rest of loading code
```

### Updated LLM Provider with Logging

```python
# In src/llm.py

import logging
from src.metrics import metrics

logger = logging.getLogger(__name__)

class KimiProvider:
    async def chat(self, messages: list[ChatMessage]) -> ChatResponse:
        """Send chat to Kimi with logging."""
        logger.info("LLM chat request", extra={
            "operation": "llm_chat",
            "model": self.model,
            "message_count": len(messages),
        })
        
        with metrics.timer("llm.chat"):
            response = await self.client.chat.completions.create(...)
        
        token_usage = {
            "prompt": response.usage.prompt_tokens if response.usage else 0,
            "completion": response.usage.completion_tokens if response.usage else 0,
        }
        
        logger.info("LLM chat response", extra={
            "operation": "llm_chat_complete",
            "model": response.model,
            "token_usage": token_usage,
            "response_length": len(response.choices[0].message.content or ""),
        })
        
        metrics.increment("llm.requests.total")
        metrics.increment("llm.tokens.prompt", token_usage["prompt"])
        metrics.increment("llm.tokens.completion", token_usage["completion"])
        
        return ChatResponse(...)
```

---

## Configuration

Add to `config.json`:

```json
{
  "logging": {
    "level": "INFO",
    "json": true,
    "file": "logs/alfred.log"
  },
  "metrics": {
    "enabled": true,
    "report_interval_seconds": 60
  },
  "health": {
    "enabled": true
  }
}
```

---

## Environment Variables

```bash
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # or "text"
LOG_FILE=logs/alfred.log

# Metrics
METRICS_ENABLED=true
METRICS_INTERVAL=60
```

---

## Tests

```python
# tests/test_logging.py
import json
import logging
from src.logging_config import JSONFormatter

def test_json_formatter():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "abc123"
    
    output = formatter.format(record)
    data = json.loads(output)
    
    assert data["message"] == "Test message"
    assert data["level"] == "INFO"
    assert data["correlation_id"] == "abc123"


# tests/test_metrics.py
import pytest
from src.metrics import metrics, MetricsCollector

@pytest.fixture(autouse=True)
def reset_metrics():
    metrics.reset()
    yield

def test_counter_increment():
    metrics.increment("test.counter")
    metrics.increment("test.counter", 5)
    
    summary = metrics.get_summary()
    assert summary["counters"]["test.counter"] == 6

@pytest.mark.asyncio
async def test_timer_context():
    with metrics.timer("test.operation"):
        pass  # Operation
    
    summary = metrics.get_summary()
    assert "test.operation" in summary["timers"]
    assert summary["timers"]["test.operation"]["count"] == 1
```

---

## Success Criteria

- [ ] Structured JSON logging for all major operations
- [ ] Metrics collection for LLM calls, context loading, memory operations
- [ ] Health check endpoint reporting system status
- [ ] Correlation ID propagation through request lifecycle
- [ ] Configurable log levels and outputs
- [ ] All existing code instrumented with logging/metrics
- [ ] Log rotation preventing disk exhaustion
- [ ] Type-safe throughout (mypy strict passes)
- [ ] Tests for logging, metrics, and health components

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | Use standard library logging | Avoid external dependencies, well-understood | Simpler setup, but less fancy features |
| 2026-02-17 | JSON structured logging | Machine-parseable, searchable in log aggregators | Better observability in production |
| 2026-02-17 | In-memory metrics collector | Simple, no external dependencies | Metrics reset on restart, but good for MVP |
| 2026-02-17 | Context variables for correlation IDs | Native Python async support | Works with any async framework |

---

## Open Questions

- [ ] Should we integrate with external APM (DataDog, New Relic)?
- [ ] Should metrics be persisted to disk or sent to external system?
- [ ] Should we add distributed tracing for multi-service scenarios?
