"""Token usage tracking from Pi session files."""
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token usage for a single request."""
    timestamp: str
    thread_id: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read: int
    cache_write: int
    total_tokens: int


class TokenTracker:
    """Tracks token usage by reading Pi session files."""
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.daily_log = log_dir / f"tokens_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    
    def parse_session_file(self, session_path: Path) -> list[TokenUsage]:
        """Parse a Pi session file and extract token usage."""
        usages = []
        
        if not session_path.exists():
            return usages
        
        try:
            with open(session_path, 'r') as f:
                thread_id = session_path.stem
                
                for line in f:
                    try:
                        entry = json.loads(line)
                        
                        # Look for assistant messages with usage data
                        if entry.get("type") == "message":
                            msg = entry.get("message", {})
                            if msg.get("role") == "assistant":
                                usage = msg.get("usage", {})
                                
                                if usage and "totalTokens" in usage:
                                    usages.append(TokenUsage(
                                        timestamp=entry.get("timestamp", datetime.now().isoformat()),
                                        thread_id=thread_id,
                                        provider=msg.get("provider", "unknown"),
                                        model=msg.get("model", "unknown"),
                                        input_tokens=usage.get("input", 0),
                                        output_tokens=usage.get("output", 0),
                                        cache_read=usage.get("cacheRead", 0),
                                        cache_write=usage.get("cacheWrite", 0),
                                        total_tokens=usage.get("totalTokens", 0)
                                    ))
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Error parsing session file {session_path}: {e}")
        
        return usages
    
    def log_usage(self, usage: TokenUsage) -> None:
        """Log token usage to daily log file."""
        with open(self.daily_log, 'a') as f:
            f.write(json.dumps({
                "timestamp": usage.timestamp,
                "thread_id": usage.thread_id,
                "provider": usage.provider,
                "model": usage.model,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read": usage.cache_read,
                "cache_write": usage.cache_write,
                "total_tokens": usage.total_tokens
            }) + '\n')
        
        logger.info(
            f"[TOKENS] {usage.thread_id}: {usage.total_tokens} tokens "
            f"({usage.input_tokens} in, {usage.output_tokens} out, "
            f"{usage.cache_read} cache) | {usage.provider}/{usage.model}"
        )
    
    def sync_from_session(self, session_path: Path) -> int:
        """Sync token usage from a session file."""
        usages = self.parse_session_file(session_path)
        
        for usage in usages:
            self.log_usage(usage)
        
        return len(usages)
    
    def get_daily_stats(self, date: Optional[datetime] = None) -> dict:
        """Get token statistics for a specific day."""
        date = date or datetime.now()
        log_file = self.log_dir / f"tokens_{date.strftime('%Y-%m-%d')}.jsonl"
        
        if not log_file.exists():
            return {
                "date": date.strftime('%Y-%m-%d'),
                "requests": 0,
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read": 0,
                "by_thread": {},
                "by_provider": {}
            }
        
        stats = {
            "date": date.strftime('%Y-%m-%d'),
            "requests": 0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read": 0,
            "by_thread": {},
            "by_provider": {}
        }
        
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    usage = json.loads(line)
                    stats["requests"] += 1
                    stats["total_tokens"] += usage["total_tokens"]
                    stats["input_tokens"] += usage["input_tokens"]
                    stats["output_tokens"] += usage["output_tokens"]
                    stats["cache_read"] += usage.get("cache_read", 0)
                    
                    # By thread
                    tid = usage["thread_id"]
                    if tid not in stats["by_thread"]:
                        stats["by_thread"][tid] = {"tokens": 0, "requests": 0}
                    stats["by_thread"][tid]["tokens"] += usage["total_tokens"]
                    stats["by_thread"][tid]["requests"] += 1
                    
                    # By provider
                    prov = usage["provider"]
                    if prov not in stats["by_provider"]:
                        stats["by_provider"][prov] = {"tokens": 0, "requests": 0}
                    stats["by_provider"][prov]["tokens"] += usage["total_tokens"]
                    stats["by_provider"][prov]["requests"] += 1
                    
                except json.JSONDecodeError:
                    continue
        
        return stats
    
    def get_logs_for_thread(self, thread_id: str, days: int = 7) -> list[TokenUsage]:
        """Get token logs for a specific thread."""
        usages = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            log_file = self.log_dir / f"tokens_{date.strftime('%Y-%m-%d')}.jsonl"
            
            if not log_file.exists():
                continue
            
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if data["thread_id"] == thread_id:
                            usages.append(TokenUsage(**data))
                    except (json.JSONDecodeError, TypeError):
                        continue
        
        return usages
