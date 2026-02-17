# PRD: Alfred - The Rememberer LLM Assistant

## Overview

**Issue**: #TBD  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Alfred is a persistent, memory-augmented LLM assistant that maintains context across infinite time horizons. Unlike typical assistants that start fresh with each conversation, Alfred captures daily interactions, curates long-term memories with embeddings, and evolves its personality and understanding of the user over time.

---

## Problem Statement

### Current State
- LLM assistants have no long-term memory
- Every conversation starts from scratch
- Context, relationships, and accumulated knowledge are lost
- No assistant truly "grows with you" over months and years
- Users must repeatedly explain context, preferences, and history

### User Pain Points
1. **Context Loss**: "I told it last week about my project, now it doesn't remember"
2. **Repetition**: Having to re-explain preferences, background, goals
3. **No Relationship Building**: Assistant doesn't learn user patterns or evolve understanding
4. **Shallow Interactions**: Surface-level conversations without deep continuity

### Desired State
An assistant that:
- Remembers everything from day one
- Learns and adapts to the user's evolving needs
- References past conversations naturally
- Develops a consistent personality
- Grows more helpful over time

---

## Solution Overview

### Core Concept
Alfred is a "friend" that lives in a Docker container, accessible via Telegram, and uses a file-based memory system with vector embeddings to maintain infinite context.

### Key Differentiators
1. **Infinite Memory**: JSON-based storage with OpenAI embeddings for semantic retrieval
2. **Daily Capture**: Automatic logging of all interactions to daily memory files
3. **Curated Long-term Memory**: IMPORTANT.md contains refined, persistent knowledge
4. **Contextual Loading**: Relevant memories automatically included in each prompt
5. **Modular Architecture**: Pluggable LLM providers (starts with Z.AI, Kimi)
6. **File-Based Configuration**: Human-readable, editable context files

---

## Technical Architecture

### Technology Stack
- **Runtime**: Python with `uv` package manager
- **Interface**: Telegram Bot API
- **Container**: Docker (user-provided Dockerfile)
- **Storage**: JSON files with OpenAI embeddings
- **Vector Search**: OpenAI embeddings with cosine similarity
- **Memory**: Daily JSON files + curated IMPORTANT.md

### File Structure
```
alfred/
├── AGENTS.md              # Behavior rules for ALL agents
├── SOUL.md               # Alfred's personality definition
├── USER.md               # User preferences and profile
├── TOOLS.md              # Local tool configurations
├── SKILLS/               # Available skill implementations
│   ├── skill_a.py
│   └── skill_b.py
├── memory/               # Daily memory captures
│   ├── 2026-02-16.json   # Each day's interactions
│   ├── 2026-02-17.json
│   └── ...
├── IMPORTANT.md          # Curated long-term memory
├── config.json           # Bot configuration
└── src/
    ├── __init__.py
    ├── bot.py            # Telegram bot handler
    ├── memory.py         # Memory management
    ├── embeddings.py     # OpenAI embedding operations
    ├── llm.py            # LLM provider abstraction
    ├── context.py        # Context file loader
    └── skills.py         # Skill registry
```

### Data Schema

#### Daily Memory Entry (memory/YYYY-MM-DD.json)
```json
{
  "date": "2026-02-16",
  "entries": [
    {
      "timestamp": "2026-02-16T14:32:00Z",
      "role": "user",
      "content": "I'm starting a new Python project",
      "embedding": [0.023, -0.045, ...],  // 1536-dim OpenAI embedding
      "importance": 0.8,
      "tags": ["coding", "python", "new-project"]
    },
    {
      "timestamp": "2026-02-16T14:32:15Z",
      "role": "assistant",
      "content": "That's exciting! What type of project are you building?",
      "embedding": [0.031, -0.022, ...],
      "importance": 0.5
    }
  ]
}
```

#### Long-term Memory (IMPORTANT.md entries embedded)
- Curated by user or auto-promoted from daily memories
- High-importance facts, preferences, relationships
- Embedded and searchable alongside daily memories

---

## Context System

### Loaded on Every Message
1. **AGENTS.md** - Universal behavior rules (e.g., "Always ask permission before editing files")
2. **SOUL.md** - Alfred's personality traits, speaking style, values
3. **USER.md** - User's background, preferences, goals, communication style
4. **TOOLS.md** - Available local tools and their configurations
5. **SKILLS/*** - Loaded skill definitions
6. **Retrieved Memories** - Top-k relevant memories from daily + long-term storage

### Memory Retrieval Flow
```
User Message → Generate Embedding → Search All Memories (cosine similarity) 
→ Rank by relevance + recency + importance → Top 10-20 memories 
→ Inject into context → Send to LLM
```

---

## Key Features

### 1. Memory Capture
- Every interaction stored to daily JSON file
- Automatic embedding generation via OpenAI API
- Importance scoring (user-defined or auto-detected)
- Tag extraction for categorical search

### 2. Memory Retrieval
- Semantic search using embeddings
- Hybrid scoring: similarity + recency + importance
- Configurable context window size
- Deduplication of similar memories

### 3. Long-term Curation
- IMPORTANT.md for persistent knowledge
- Auto-promotion of high-importance memories
- User can manually add/edit IMPORTANT.md
- Periodic consolidation of daily memories

### 4. Multi-Agent Support
- Modular LLM provider architecture
- Initial: Z.AI Coding, Kimi Coding Plan
- Pluggable: OpenAI, Anthropic, local models
- Per-agent configuration in SKILLS/

### 5. Telegram Interface
- Simple, conversational UI
- Support for text, images, documents
- Inline commands for memory management
- Notification capabilities

---

## User Experience

### Onboarding Flow
1. User starts Telegram chat with Alfred
2. Alfred introduces itself, asks about user's goals
3. Initial USER.md created from conversation
4. SOUL.md initialized with default personality
5. First daily memory file created

### Daily Interaction
1. User sends message
2. Alfred loads context (files + relevant memories)
3. Alfred responds with context-aware message
4. Interaction logged to daily memory with embedding
5. User can rate importance or add to IMPORTANT.md

### Memory Management
- User: "Remember that I'm allergic to peanuts"
- Alfred: Stores in IMPORTANT.md, responds: "Got it, I've added that to my permanent memory"
- Later: "What foods should I avoid?" → Alfred recalls peanut allergy

### Learning Examples
- User prefers concise answers → Alfred adapts style
- User works late nights → Alfred stops saying "good morning" at 2am
- User's project evolves → Alfred tracks progress in IMPORTANT.md

---

## Milestones

### Milestone 1: Core Infrastructure
- [ ] Project structure with `uv` and Python setup
- [ ] Docker container working with user-provided Dockerfile
- [ ] Configuration system (config.json, environment variables)
- [ ] File-based context loader (AGENTS.md, SOUL.md, USER.md, TOOLS.md)
- [ ] Basic logging and error handling

**Success Criteria**: Container builds, config loads, context files readable

### Milestone 2: Memory System Foundation
- [ ] JSON daily memory storage implementation
- [ ] OpenAI embedding integration
- [ ] Memory write path (every interaction stored)
- [ ] Memory read path (retrieve by date range)
- [ ] IMPORTANT.md support (curated memory)

**Success Criteria**: Conversations persist to JSON, embeddings generated

### Milestone 3: Vector Search & Context Injection
- [ ] Cosine similarity search implementation
- [ ] Hybrid scoring (relevance + recency + importance)
- [ ] Context builder (inject memories into prompts)
- [ ] Token budget management for context window
- [ ] Memory deduplication

**Success Criteria**: Relevant memories retrieved and injected automatically

### Milestone 4: Telegram Bot Integration
- [ ] Telegram Bot API integration
- [ ] Message handler (text, basic commands)
- [ ] Conversation state management
- [ ] Error handling and retry logic
- [ ] Webhook or polling mode support

**Success Criteria**: Can chat with Alfred via Telegram

### Milestone 5: LLM Provider Abstraction
- [ ] Modular provider interface
- [ ] Z.AI Coding implementation
- [ ] Kimi Coding Plan implementation
- [ ] Provider switching logic
- [ ] Streaming response support (if supported by provider)

**Success Criteria**: Can use Z.AI or Kimi interchangeably

### Milestone 6: Personality & Learning
- [ ] SOUL.md parsing and injection
- [ ] Personality consistency enforcement
- [ ] Basic preference learning (from USER.md updates)
- [ ] Importance scoring for memories
- [ ] Auto-promotion to IMPORTANT.md

**Success Criteria**: Alfred has consistent personality, remembers preferences

### Milestone 7: Skills System
- [ ] Skill registry and loader
- [ ] SKILLS/ directory support
- [ ] Skill discovery and registration
- [ ] Basic built-in skills (memory search, user profile update)
- [ ] Skill execution context

**Success Criteria**: Skills load and execute correctly

### Milestone 8: Memory Management Commands
- [ ] `/remember` - Add to IMPORTANT.md
- [ ] `/forget` - Remove from memory
- [ ] `/search` - Search memories
- [ ] `/summary` - Daily/weekly summary
- [ ] `/status` - Memory stats

**Success Criteria**: User can manage memories via commands

### Milestone 9: Testing & Quality
- [ ] Unit tests for core modules
- [ ] Integration tests for memory system
- [ ] Telegram bot tests (mocked)
- [ ] Embedding quality evaluation
- [ ] Context retrieval accuracy metrics

**Success Criteria**: Test suite passes, memory retrieval >80% relevant

### Milestone 10: Documentation & Deployment
- [ ] README with setup instructions
- [ ] Configuration guide
- [ ] Docker deployment guide
- [ ] Telegram bot setup tutorial
- [ ] API keys and environment setup

**Success Criteria**: New user can set up Alfred in <30 minutes

---

## Technical Specifications

### Dependencies
```toml
[project]
name = "alfred"
version = "0.1.0"
dependencies = [
    "python-telegram-bot>=20.0",
    "openai>=1.0",
    "numpy>=1.24",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "aiofiles>=23.0",
    "tiktoken>=0.5",
]
```

### Environment Variables
```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key

# LLM Providers (at least one required)
ZAI_API_KEY=your_zai_key
ZAI_BASE_URL=https://api.z.ai/v1
KIMI_API_KEY=your_kimi_key
KIMI_BASE_URL=https://api.moonshot.cn/v1

# Optional
DEFAULT_LLM_PROVIDER=zai
MEMORY_CONTEXT_LIMIT=20
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4o-mini
```

### Configuration (config.json)
```json
{
  "bot": {
    "name": "Alfred",
    "polling_interval": 1.0,
    "timeout": 30
  },
  "memory": {
    "daily_retention_days": 365,
    "context_window_size": 20,
    "min_similarity_threshold": 0.7,
    "auto_embed": true
  },
  "llm": {
    "default_provider": "zai",
    "max_tokens": 2000,
    "temperature": 0.7
  },
  "context_files": {
    "agents": "AGENTS.md",
    "soul": "SOUL.md",
    "user": "USER.md",
    "tools": "TOOLS.md"
  }
}
```

---

## AGENTS.md Template

```markdown
# Agent Behavior Rules

## Core Principles
1. **Permission First**: Always ask for explicit permission before:
   - Editing any files
   - Deleting data
   - Making external API calls
   - Running commands

2. **Transparency**: Explain what you're doing and why

3. **User Control**: User has final say on all decisions

4. **Privacy**: Never share user data without consent

## Communication Style
- Be concise unless asked for detail
- Confirm understanding of ambiguous requests
- Admit uncertainty rather than hallucinate
```

---

## Success Criteria

### Functional
- [ ] Alfred remembers conversations from weeks/months ago
- [ ] Context automatically includes relevant past interactions
- [ ] Personality remains consistent across sessions
- [ ] User preferences learned and applied
- [ ] Memory retrieval is fast (<2s for search)

### Quality
- [ ] Retrieved memories are >80% relevant to query
- [ ] Response latency <5s for typical queries
- [ ] No data loss across container restarts
- [ ] Graceful handling of API failures

### User Experience
- [ ] Setup time <30 minutes for technical users
- [ ] Intuitive Telegram interface
- [ ] Clear feedback on memory operations
- [ ] Personality feels natural and friendly

---

## Future Enhancements (Post-MVP)

### Phase 2
- [ ] Web dashboard for memory visualization
- [ ] Voice message support
- [ ] Image understanding and memory
- [ ] Multi-user support (with separate memory spaces)
- [ ] Automatic memory consolidation (summarize old memories)

### Phase 3
- [ ] Local LLM support (llama.cpp, ollama)
- [ ] Multi-modal memory (images, documents)
- [ ] Integration with external services (calendar, notes)
- [ ] Proactive notifications (reminders, follow-ups)
- [ ] Memory import/export

---

## Open Questions

1. **Memory pruning**: Should old daily memories be archived/summarized after N days?
2. **Conflict resolution**: How to handle contradictory information in memories?
3. **Privacy**: Should there be a "forget permanently" option?
4. **Multi-device**: Should Alfred work across multiple Telegram clients?
5. **Backup**: Automated backup strategy for memory files?

---

## References

- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Python Telegram Bot](https://docs.python-telegram-bot.org/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Cosine Similarity](https://en.wikipedia.org/wiki/Cosine_similarity)
