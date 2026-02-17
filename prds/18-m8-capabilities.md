# PRD: M8 - Capabilities System

## Overview

**Issue**: #18  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #17 (M7: Personality)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Build automatic capabilities system. Alfred performs actions semantically without explicit commands.

---

## Problem Statement

Users should not run commands. "Remember when we talked about my Python project?" should trigger semantic search automatically. The model decides what to do.

---

## Solution

Create capabilities that:
1. Trigger automatically based on user intent
2. Use the LLM to decide when to activate
3. Execute without explicit commands
4. Feel like magic

---

## Acceptance Criteria

- [ ] `src/capabilities.py` - Capability registry
- [ ] `CAPABILITIES/` directory with implementations
- [ ] Automatic intent detection via LLM
- [ ] Search capability (automatic)
- [ ] Remember capability (automatic)
- [ ] No user commands required

---

## File Structure

```
src/
├── capabilities.py           # Registry and routing
└── capabilities/
    ├── __init__.py
    ├── base.py              # Base capability class
    ├── search.py            # Semantic search
    └── remember.py          # Store to memory
```

---

## Base Capability (src/capabilities/base.py)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class CapabilityResult:
    success: bool
    response: str
    data: Any | None = None


class Capability(ABC):
    """Base class for capabilities."""
    
    name: str
    description: str
    triggers: list[str]  # Description of when to use
    
    @abstractmethod
    async def can_handle(self, message: str, context: dict) -> float:
        """Return confidence 0-1 that this capability should handle the message."""
        pass
    
    @abstractmethod
    async def execute(self, message: str, context: dict) -> CapabilityResult:
        """Execute the capability."""
        pass
```

---

## Search Capability (src/capabilities/search.py)

```python
from src.capabilities.base import Capability, CapabilityResult
from src.search import MemorySearcher
from src.memory import MemoryStore


class SearchCapability(Capability):
    """Search memories based on semantic intent."""
    
    name = "search"
    description = "Search through past conversations for relevant information"
    triggers = [
        "User asks about something from the past",
        "User references previous conversations",
        "Questions starting with 'Remember when', 'Did we discuss', etc.",
        "User asks 'What did I say about...'",
    ]
    
    def __init__(self, searcher: MemorySearcher, memory: MemoryStore) -> None:
        self.searcher = searcher
        self.memory = memory
    
    async def can_handle(self, message: str, context: dict) -> float:
        """Check if this looks like a memory search."""
        search_phrases = [
            "remember when",
            "remember that",
            "did we talk about",
            "did we discuss",
            "what did i say",
            "what did we",
            "last time",
            "previously",
        ]
        
        message_lower = message.lower()
        for phrase in search_phrases:
            if phrase in message_lower:
                return 0.9
        
        # If no clear phrase, low confidence
        return 0.3
    
    async def execute(self, message: str, context: dict) -> CapabilityResult:
        """Search memories and return results."""
        all_memories = await self.memory.load_all_memories()
        results = await self.searcher.search(message, all_memories)
        
        if not results:
            return CapabilityResult(
                success=True,
                response="I don't recall us discussing that. Could you remind me?",
            )
        
        # Build response with found memories
        memory_texts = []
        for mem in results[:3]:
            date = mem.timestamp.strftime("%B %d")
            prefix = "You said" if mem.role == "user" else "I said"
            memory_texts.append(f"On {date}, {prefix}: \"{mem.content}\"")
        
        response = "I remember:\n\n" + "\n\n".join(memory_texts)
        
        return CapabilityResult(
            success=True,
            response=response,
            data={"memories": results},
        )
```

---

## Remember Capability (src/capabilities/remember.py)

```python
from src.capabilities.base import Capability, CapabilityResult
from src.memory import MemoryStore, ImportantMemory


class RememberCapability(Capability):
    """Store information to long-term memory."""
    
    name = "remember"
    description = "Store important information to permanent memory"
    triggers = [
        "User says 'Remember that I...' or 'Make sure to remember...'",
        "User shares important facts about themselves",
        "User states preferences or goals",
        "Information that should persist long-term",
    ]
    
    def __init__(self, memory: MemoryStore, important: ImportantMemory) -> None:
        self.memory = memory
        self.important = important
    
    async def can_handle(self, message: str, context: dict) -> float:
        """Check if user wants to store something."""
        remember_phrases = [
            "remember that i",
            "remember i",
            "make sure to remember",
            "don't forget that",
            "important: ",
        ]
        
        message_lower = message.lower()
        for phrase in remember_phrases:
            if phrase in message_lower:
                return 0.9
        
        # Check for important facts (model could decide)
        return 0.2
    
    async def execute(self, message: str, context: dict) -> CapabilityResult:
        """Store to IMPORTANT.md."""
        # Extract what to remember (in real impl, use LLM to extract)
        # For now, store the whole message
        await self.important.append(f"- {message}")
        
        return CapabilityResult(
            success=True,
            response="Got it. I've added that to my permanent memory.",
        )
```

---

## Capability Registry (src/capabilities.py)

```python
from typing import list
from src.capabilities.base import Capability, CapabilityResult


class CapabilityRegistry:
    """Registry and router for capabilities."""
    
    def __init__(self) -> None:
        self.capabilities: list[Capability] = []
    
    def register(self, capability: Capability) -> None:
        """Register a capability."""
        self.capabilities.append(capability)
    
    async def route(
        self, message: str, context: dict
    ) -> tuple[Capability | None, float]:
        """Find best capability for message."""
        best_capability = None
        best_confidence = 0.0
        
        for capability in self.capabilities:
            confidence = await capability.can_handle(message, context)
            if confidence > best_confidence:
                best_confidence = confidence
                best_capability = capability
        
        return best_capability, best_confidence
    
    async def handle(
        self, message: str, context: dict, min_confidence: float = 0.7
    ) -> CapabilityResult | None:
        """Route and execute if confidence high enough."""
        capability, confidence = await self.route(message, context)
        
        if capability and confidence >= min_confidence:
            return await capability.execute(message, context)
        
        return None


# Factory function
def create_registry(config, memory, searcher) -> CapabilityRegistry:
    """Create registry with all capabilities."""
    from src.capabilities.search import SearchCapability
    from src.capabilities.remember import RememberCapability
    from src.memory import ImportantMemory
    from src.embeddings import EmbeddingClient
    
    registry = CapabilityRegistry()
    embedder = EmbeddingClient(config)
    important = ImportantMemory(config, embedder)
    
    registry.register(SearchCapability(searcher, memory))
    registry.register(RememberCapability(memory, important))
    
    return registry
```

---

## Integration with Bot

```python
# Update src/bot.py

class AlfredBot:
    def __init__(
        self,
        config: Config,
        context_loader: ContextLoader,
        memory_store: MemoryStore,
        llm: LLMProvider,
        capabilities: CapabilityRegistry,
    ) -> None:
        self.config = config
        self.context_loader = context_loader
        self.memory = memory_store
        self.llm = llm
        self.capabilities = capabilities
        self.application: Application | None = None
    
    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages with capabilities."""
        if not update.message or not update.message.text:
            return
        
        user_message = update.message.text
        
        try:
            # Try capabilities first
            ctx = {"user_id": update.effective_user.id if update.effective_user else 0}
            capability_result = await self.capabilities.handle(user_message, ctx)
            
            if capability_result:
                await update.message.reply_text(capability_result.response)
                return
            
            # Fall back to normal LLM flow
            # ... rest of normal flow ...
            
        except Exception as e:
            logger.exception("Error handling message")
            await update.message.reply_text(f"Error: {e}")
            raise
```

---

## Tests

```python
# tests/test_capabilities.py
import pytest
from src.capabilities.search import SearchCapability
from src.capabilities.remember import RememberCapability


@pytest.mark.asyncio
async def test_search_capability_triggers_on_remember_when():
    capability = SearchCapability(MockSearcher(), MockMemory())
    
    confidence = await capability.can_handle(
        "Remember when we talked about Python?",
        {}
    )
    
    assert confidence > 0.8


@pytest.mark.asyncio
async def test_remember_capability_triggers_on_remember_that():
    capability = RememberCapability(MockMemory(), MockImportant())
    
    confidence = await capability.can_handle(
        "Remember that I'm allergic to peanuts",
        {}
    )
    
    assert confidence > 0.8
```

---

## Success Criteria

- [ ] Capabilities register and route correctly
- [ ] Search triggers on memory questions
- [ ] Remember triggers on explicit storage requests
- [ ] No commands needed
- [ ] Confidence scoring works
- [ ] All tests pass
