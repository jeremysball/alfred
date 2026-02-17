# PRD: M10 - Distillation System

## Overview

**Issue**: #20  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #19 (M9: Compaction)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Build distillation system that extracts insights from conversations and writes to memory files using model-driven decisions.

---

## Problem Statement

Daily memory files accumulate endlessly. Not everything deserves long-term storage. Alfred needs intelligent distillation: extract key insights and write to IMPORTANT.md automatically. The model decides what matters.

---

## Solution

Create distillation that:
1. Monitors conversations continuously
2. Uses LLM to extract key insights
3. Decides what deserves permanent storage
4. Writes to IMPORTANT.md automatically
5. Model-driven, not rule-based

---

## Acceptance Criteria

- [ ] `src/distillation.py` - Distillation engine
- [ ] Continuous conversation monitoring
- [ ] Key insight extraction via LLM
- [ ] Automatic IMPORTANT.md updates
- [ ] Importance scoring
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
        important: ImportantMemory,
        min_importance: float = 0.7,
    ) -> None:
        self.config = config
        self.llm = llm
        self.important = important
        self.min_importance = min_importance
    
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
            
            # Score importance
            importance = await self._score_importance(insight)
            
            if importance >= self.min_importance:
                await self._store_insight(insight, importance)
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
- Importance (0-1): How valuable is this for future conversations?
- Category: user_preference, user_fact, decision, goal, context

Only extract substantive insights. Skip trivialities.

Format as JSON array:
[
  {"content": "...", "importance": 0.9, "category": "user_preference"}
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
            return [Insight(content=response.content, importance=0.8, category="context")]
    
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
    
    async def _score_importance(self, insight: "Insight") -> float:
        """Score importance using LLM."""
        messages = [
            ChatMessage(
                role="system",
                content="""Rate the importance of this insight for long-term memory (0-1).

High importance (0.8-1.0):
- Core user preferences
- Important life facts
- Project goals and decisions
- Relationship information

Medium importance (0.5-0.7):
- Temporary preferences
- Minor context
- Routine information

Low importance (0.0-0.4):
- Trivial details
- One-time mentions
- Obvious information

Respond with only a number between 0 and 1.""",
            ),
            ChatMessage(
                role="user",
                content=f"Insight: {insight.content}\nCategory: {insight.category}",
            ),
        ]
        
        response = await self.llm.chat(messages)
        
        try:
            return float(response.content.strip())
        except ValueError:
            return insight.importance  # Fallback to original
    
    async def _store_insight(self, insight: "Insight", importance: float) -> None:
        """Store insight to IMPORTANT.md."""
        formatted = f"[{insight.category.upper()}] {insight.content}"
        await self.important.append(formatted)
    
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
    importance: float
    category: str
