# PRD: M10 - Distillation System

## Overview

**Issue**: #20  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #53 (Session System), #19 (M9: Compaction)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

> **Note**: Updated to use tool-based architecture. Removed importance scoring (feature removed in #57).

Build distillation system that extracts insights from conversations and writes to memory files using model-driven decisions.

---

## Problem Statement

Daily memory files accumulate endlessly. Not everything deserves long-term storage. Alfred needs intelligent distillation: extract key insights and write to MEMORY.md automatically. The model decides what matters.

---

## Solution

Create distillation that:
1. Monitors conversations continuously
2. Uses LLM to extract key insights
3. Decides what deserves permanent storage
4. Writes to MEMORY.md automatically
5. Model-driven, not rule-based

---

## Acceptance Criteria

- [ ] `src/distillation.py` - Distillation engine
- [ ] Continuous conversation monitoring
- [ ] Key insight extraction via LLM
- [ ] Automatic MEMORY.md updates
- [ ] Duplicate detection

---

## File Structure

```
src/
└── distillation.py        # Distillation engine
```

---

## Distillation Engine (src/distillation.py)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from src.types import MemoryEntry
from src.llm import LLMProvider, ChatMessage
from src.memory import ImportantMemory
from src.config import Config


@dataclass
class DistillationResult:
    insights: list[str]
    added_to_important: list[str]
    duplicates_skipped: int


class DistillationEngine:
    """Extract and store key insights from conversations."""
    
    def __init__(
        self,
        config: Config,
        llm: LLMProvider,
        memory_store: MemoryStore,
    ) -> None:
        self.config = config
        self.llm = llm
        self.memory_store = memory_store
    
    async def distill(
        self,
        recent_memories: list[MemoryEntry],
        force: bool = False,
    ) -> DistillationResult:
        """Distill recent conversation for insights."""
        if len(recent_memories) < 3 and not force:
            return DistillationResult(
                insights=[],
                added_to_important=[],
                duplicates_skipped=0,
            )
        
        # Build conversation context
        conversation = self._format_conversation(recent_memories)
        
        # Extract insights using LLM
        insights = await self._extract_insights(conversation)
        
        # Filter and store
        added = []
        duplicates = 0
        
        for insight in insights:
            # Check for duplicates
            if await self._is_duplicate(insight):
                duplicates += 1
                continue
            
            await self._store_insight(insight)
            added.append(insight)
        
        return DistillationResult(
            insights=[i.text for i in insights],
            added_to_important=added,
            duplicates_skipped=duplicates,
        )
    
    def _format_conversation(self, memories: list[MemoryEntry]) -> str:
        """Format memories for LLM consumption."""
        lines = []
        for mem in memories:
            role = "User" if mem.role == "user" else "Assistant"
            lines.append(f"{role}: {mem.content}")
        return "\n".join(lines)
    
    async def _extract_insights(self, conversation: str) -> list["Insight"]:
        """Use LLM to extract key insights."""
        messages = [
            ChatMessage(
                role="system",
                content="""Extract key insights from this conversation. 

For each insight, provide:
- Content: The specific fact, preference, or decision
- Category: user_preference, user_fact, decision, goal, context

Only extract substantive insights. Skip trivialities.

Format as JSON array:
[
  {"content": "...", "category": "user_preference"}
]""",
            ),
            ChatMessage(
                role="user",
                content=conversation,
            ),
        ]
        
        response = await self.llm.chat(messages)
        
        # Parse JSON response
        try:
            import json
            data = json.loads(response.content)
            return [Insight(**item) for item in data]
        except Exception:
            # Fallback: treat whole response as single insight
            return [Insight(content=response.content, category="context")]
    
    async def _is_duplicate(self, insight: "Insight") -> bool:
        """Check if similar insight already exists."""
        existing = await self.important.get_entries()
        
        # Simple text similarity
        for entry in existing:
            similarity = self._text_similarity(insight.content, entry.content)
            if similarity > 0.85:
                return True
        
        return False
    
    def _text_similarity(self, a: str, b: str) -> float:
        """Calculate simple text similarity."""
        # Use embedding similarity if available, else simple overlap
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        
        if not a_words or not b_words:
            return 0.0
        
        intersection = a_words & b_words
        union = a_words | b_words
        
        return len(intersection) / len(union)

    async def _store_insight(self, insight: "Insight") -> None:
        """Store insight to MEMORY.md."""
        formatted = f"[{insight.category.upper()}] {insight.content}"
        await self.curated.append(formatted)
    
    async def periodic_distill(self) -> DistillationResult:
        """Run distillation on recent unprocessed memories."""
        # TODO: Track which memories have been processed
        # For now, process last N messages
        from src.memory import MemoryStore
        from src.embeddings import EmbeddingClient
        
        embedder = EmbeddingClient(self.config)
        memory = MemoryStore(self.config, embedder)
        
        all_memories = await memory.load_all_memories()
        recent = all_memories[-50:]  # Last 50 messages
        
        return await self.distill(recent)


@dataclass
class Insight:
    content: str
    category: str
