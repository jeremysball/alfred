# PRD: M9 - Compaction System

## Overview

**Issue**: #19  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #18 (M8: Capabilities)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Implement `/compact` command that intelligently summarizes long-running conversations using model-driven decisions.

---

## Problem Statement

Long conversations grow unwieldy. Context windows overflow. Token costs rise. Alfred needs intelligent compaction: summarize old content, preserve recent context, truncate tool calls, maintain continuity.

---

## Solution

Create compaction system that:
1. Triggers manually via `/compact`
2. Uses the LLM to decide what matters
3. Summarizes intelligently, preserving key facts
4. Maintains conversation continuity
5. Model-driven, not rule-based

---

## Acceptance Criteria

- [ ] `src/compaction.py` - Compaction engine
- [ ] `/compact` command in Telegram bot
- [ ] Model-driven summarization
- [ ] Recent message preservation
- [ ] Tool call truncation
- [ ] Summary storage for reference

---

## File Structure

```
src/
└── compaction.py          # Compaction engine
```

---

## Compaction Engine (src/compaction.py)

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from src.types import MemoryEntry
from src.llm import LLMProvider, ChatMessage
from src.config import Config


@dataclass
class CompactionResult:
    summary: str
    preserved_count: int
    summarized_count: int
    token_savings: int


class CompactionEngine:
    """Intelligently compact conversation history."""
    
    def __init__(
        self,
        config: Config,
        llm: LLMProvider,
        preserve_recent: int = 10,
    ) -> None:
        self.config = config
        self.llm = llm
        self.preserve_recent = preserve_recent
    
    async def compact(
        self,
        memories: list[MemoryEntry],
        query_context: str = "",
    ) -> CompactionResult:
        """Compact memories using model-driven summarization."""
        if len(memories) <= self.preserve_recent * 2:
            return CompactionResult(
                summary="",
                preserved_count=len(memories),
                summarized_count=0,
                token_savings=0,
            )
        
        # Split: preserve recent, summarize older
        to_preserve = memories[-self.preserve_recent:]
        to_summarize = memories[:-self.preserve_recent]
        
        # Generate intelligent summary using LLM
        summary = await self._generate_summary(to_summarize, query_context)
        
        # Calculate savings (rough estimate)
        original_tokens = sum(len(m.content.split()) for m in to_summarize)
        summary_tokens = len(summary.split())
        
        return CompactionResult(
            summary=summary,
            preserved_count=len(to_preserve),
            summarized_count=len(to_summarize),
            token_savings=original_tokens - summary_tokens,
        )
    
    async def _generate_summary(
        self,
        memories: list[MemoryEntry],
        query_context: str,
    ) -> str:
        """Use LLM to generate intelligent summary."""
        # Build conversation transcript
        transcript = self._build_transcript(memories)
        
        # Prompt for summarization
        messages = [
            ChatMessage(
                role="system",
                content="""You are a memory compaction assistant. 

Your task: Summarize a conversation transcript while preserving:
1. Key facts and decisions
2. User preferences revealed
3. Important context for future conversations
4. Specific details that matter (names, dates, preferences)

Be concise but complete. Omit pleasantries and filler. Focus on substance.

Current context: """ + query_context,
            ),
            ChatMessage(
                role="user",
                content=f"Summarize this conversation:\n\n{transcript}",
            ),
        ]
        
        response = await self.llm.chat(messages)
        return response.content
    
    def _build_transcript(self, memories: list[MemoryEntry]) -> str:
        """Build readable transcript from memories."""
        lines = []
        for mem in memories:
            timestamp = mem.timestamp.strftime("%H:%M")
            role = "User" if mem.role == "user" else "Assistant"
            lines.append(f"[{timestamp}] {role}: {mem.content}")
        return "\n".join(lines)
    
    def compact_tool_calls(self, memories: list[MemoryEntry]) -> list[MemoryEntry]:
        """Truncate or remove tool call details."""
        compacted = []
        
        for mem in memories:
            content = mem.content
            
            # Truncate long tool outputs
            if "tool" in content.lower() or "function" in content.lower():
                if len(content) > 500:
                    content = content[:500] + "... [truncated]"
            
            # Create new entry with compacted content
            compacted.append(MemoryEntry(
                timestamp=mem.timestamp,
                role=mem.role,
                content=content,
                embedding=mem.embedding,
                importance=mem.importance,
                tags=mem.tags,
            ))
        
        return compacted
    
    async def compact_with_context(
        self,
        all_memories: list[MemoryEntry],
        current_query: str,
    ) -> tuple[str, list[MemoryEntry]]:
        """Compact and return context for current query."""
        # Compact older memories
        result = await self.compact(all_memories, current_query)
        
        # Build context: summary + recent memories
        context_parts = []
        
        if result.summary:
            context_parts.append(f"[Earlier conversation summary: {result.summary}]")
        
        # Add preserved recent memories
        recent = all_memories[-self.preserve_recent:]
        context_parts.extend([
            f"[{m.timestamp.strftime('%H:%M')}] {m.role}: {m.content}"
            for m in recent
        ])
        
        context = "\n\n".join(context_parts)
        
        return context, recent
```

---

## Bot Integration

```python
# Update src/bot.py

from src.compaction import CompactionEngine

class AlfredBot:
    def __init__(
        self,
        config: Config,
        context_loader: ContextLoader,
        memory_store: MemoryStore,
        llm: LLMProvider,
        capabilities: CapabilityRegistry,
        compaction: CompactionEngine,
    ) -> None:
        # ... existing init ...
        self.compaction = compaction
    
    async def compact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /compact command."""
        if not update.message:
            return
        
        await update.message.reply_text("Compacting memories...")
        
        try:
            all_memories = await self.memory.load_all_memories()
            
            result = await self.compaction.compact(all_memories)
            
            if result.summarized_count == 0:
                await update.message.reply_text(
                    "No compaction needed. Conversation is still short."
                )
                return
            
            # Store summary to memory
            await self.memory.add_entry(
                role="system",
                content=f"[Summary of {result.summarized_count} messages]: {result.summary}",
                importance=1.0,
                tags=["compaction", "summary"],
            )
            
            await update.message.reply_text(
                f"Compacted {result.summarized_count} messages into summary. "
                f"Preserved {result.preserved_count} recent messages. "
                f"Saved ~{result.token_savings} tokens."
            )
            
        except Exception as e:
            logger.exception("Compaction failed")
            await update.message.reply_text(f"Compaction failed: {e}")
            raise
```

---

## Tests

```python
# tests/test_compaction.py
import pytest
from datetime import datetime
from src.compaction import CompactionEngine
from src.types import MemoryEntry


@pytest.fixture
def mock_llm():
    class MockLLM:
        async def chat(self, messages):
            from src.llm import ChatResponse
            return ChatResponse(
                content="User likes Python and wants to build an AI project.",
                model="test",
            )
    return MockLLM()


@pytest.mark.asyncio
async def test_compact_short_conversation_skips(mock_llm, mock_config):
    engine = CompactionEngine(mock_config, mock_llm, preserve_recent=5)
    
    memories = [
        MemoryEntry(timestamp=datetime.now(), role="user", content=f"msg {i}")
        for i in range(8)
    ]
    
    result = await engine.compact(memories)
    
    assert result.summarized_count == 0
    assert result.preserved_count == 8


@pytest.mark.asyncio
async def test_compact_long_conversation_summarizes(mock_llm, mock_config):
    engine = CompactionEngine(mock_config, mock_llm, preserve_recent=5)
    
    memories = [
        MemoryEntry(timestamp=datetime.now(), role="user", content=f"message content {i}")
        for i in range(20)
    ]
    
    result = await engine.compact(memories)
    
    assert result.summarized_count == 15  # 20 - 5 preserved
    assert result.preserved_count == 5
    assert result.summary != ""
    assert result.token_savings > 0
```

---

## Success Criteria

- [ ] `/compact` command works
- [ ] Short conversations skip compaction
- [ ] Long conversations summarize correctly
- [ ] Model-driven summaries capture key facts
- [ ] Recent messages preserved
- [ ] Summary stored to memory
- [ ] Token savings calculated
- [ ] All tests pass
