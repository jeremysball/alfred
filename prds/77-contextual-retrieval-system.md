# PRD: Contextual Retrieval System (Triple-Layer Memory)

**Issue**: #77
**Status**: Planning
**Priority**: Medium
**Created**: 2026-02-19
**Depends On**: #76 (Session Summarization with Cron)
**Related**: #53 (Session System), #55 (Advanced Session Features)

---

## Problem Statement

Current dual memory search finds relevant content but suffers from precision limits:

1. **Global message search** scans every message ever stored—high recall, low precision
2. **Session summaries** provide narrative context but miss specific details
3. **No contextual narrowing**—every query searches the entire corpus

When you ask "What was that bug with auth?", Alfred finds the message but loses the surrounding context. He cannot efficiently reconstruct: *"You were in the auth refactor session (context), working on JWT validation (theme), and hit a specific null pointer (detail)."

The missing layer: **in-session message embeddings** for contextual retrieval.

---

## Solution Overview

Implement a triple-layer memory architecture:

| Layer | What It Stores | Search Pattern | Precision |
|-------|----------------|----------------|-----------|
| **Global Memory** | Facts across all time | Semantic similarity | Low (everything) |
| **Session Summaries** | Narrative arcs of conversations | Semantic similarity | Medium (session-level) |
| **Session-Local Messages** | Individual messages WITHIN sessions | Session-scoped semantic | **High** (contextual) |

**The Hyperweb Retrieval Pattern:**

```
User Query: "What was that auth bug?"
    ↓
[1] Search session summaries → Find "Auth refactor session" (high relevance)
    ↓
[2] Search messages WITHIN that session only → Find "JWT null pointer" (precise)
    ↓
[3] Retrieve neighboring messages for context → "Testing edge cases..." 
    ↓
[4] Cross-link to related sessions (if needed) → "Session 52: Deployed auth fixes"
    ↓
Alfred: "In your auth refactor session last Tuesday, you hit a JWT null pointer 
         when testing edge cases. You deployed fixes the next day."
```

Instead of searching 10,000 messages globally, narrow to 2-3 relevant sessions, then find specifics with 10x higher precision.

---

## Technical Architecture

### Triple-Layer Storage

```
data/
├── memory/
│   └── memories.jsonl              # Layer 1: Curated facts Alfred remembers
│       └── embedding: [0.1, -0.2, ...]
│
└── sessions/
    └── sess_abc/                   # One folder per session
        ├── messages.jsonl          # Layer 3: Session messages with embeddings
        │   ├── idx: 0
        │   ├── content: "Starting auth refactor..."
        │   └── embedding: [0.2, -0.3, ...]
        │
        └── summary.json            # Layer 2: Session summary + embedding
            ├── session_id: "sess_abc"
            ├── summary_text: "Auth refactor discussion..."
            └── embedding: [0.3, -0.1, ...]
```

**Key insight**: Each session has its own folder containing messages and summary. Queries first find sessions via summaries, then drill down into messages.

### Contextual Retrieval Flow

```python
class ContextualRetrievalEngine:
    """Triple-layer memory retrieval with contextual narrowing."""
    
    async def retrieve(self, query: str, top_sessions: int = 3) -> RetrievalResult:
        """The hyperweb retrieval pattern."""
        
        # Layer 2: Find relevant sessions via summary similarity
        session_results = await self._search_session_summaries(
            query=query,
            top_k=top_sessions
        )
        
        # Layer 3: Search messages within each relevant session
        contextual_results = []
        for session in session_results:
            messages = await self._search_session_messages(
                session_id=session.session_id,
                query=query,
                top_k=5  # Per-session limit
            )
            contextual_results.append(SessionContext(
                session=session,
                messages=messages
            ))
        
        # Optional: Cross-link to related sessions
        cross_links = await self._find_related_sessions(
            session_ids=[c.session.session_id for c in contextual_results]
        )
        
        return RetrievalResult(
            contexts=contextual_results,
            cross_links=cross_links
        )
    
    async def _search_session_messages(
        self,
        session_id: str,
        query: str,
        top_k: int
    ) -> list[ScoredMessage]:
        """Search messages within a specific session only."""
        
        # Load session's message embeddings
        message_index = await self._load_session_index(session_id)
        
        # Embed query
        query_embedding = await self.embedder.create_embedding(query)
        
        # Search only this session's messages (O(session_size), not O(total))
        results = cosine_similarity_search(
            query=query_embedding,
            index=message_index,
            top_k=top_k
        )
        
        return results
```

### Session-Local Embedding Index

Each session maintains its own vector index of messages in `data/sessions/{session_id}/messages.jsonl`:

```python
@dataclass
class SessionMessageIndex:
    """Embedded messages for a single session."""
    session_id: str
    messages: list[IndexedMessage]  # With embeddings
    
    def search(self, query_embedding: list[float], top_k: int) -> list[ScoredMessage]:
        """Local search within this session only."""
        scored = [
            (msg, cosine_similarity(query_embedding, msg.embedding))
            for msg in self.messages
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

@dataclass
class IndexedMessage:
    idx: int                    # Position in session
    content: str
    role: str                   # "user" | "assistant"
    timestamp: datetime
    embedding: list[float]
```

### Smart Context Assembly

The retrieval result assembles context hierarchically:

```python
@dataclass
class RetrievalResult:
    """Hierarchical retrieval output."""
    
    # Primary contexts: Session + relevant messages
    contexts: list[SessionContext]
    
    # Cross-links: Related sessions for expansion
    cross_links: list[SessionSummary]
    
    def to_prompt_context(self) -> str:
        """Format for LLM context injection."""
        parts = []
        
        for ctx in self.contexts:
            parts.append(f"## Session: {ctx.session.summary_text[:100]}...")
            parts.append("Relevant exchanges:")
            
            for msg in ctx.messages:
                neighbor_context = self._get_neighbors(ctx.session.session_id, msg.idx)
                parts.append(f"  [{msg.role}]: {msg.content}")
                if neighbor_context:
                    parts.append(f"    Context: {...}")
        
        if self.cross_links:
            parts.append("\n## Related sessions:")
            for link in self.cross_links:
                parts.append(f"- {link.summary_text[:80]}...")
        
        return "\n".join(parts)
```

---

## Integration with Existing Systems

### Relationship to PRD #76 (Session Summarization)

| Component | PRD #76 | This PRD |
|-----------|---------|----------|
| Session folders | ✅ Creates `data/sessions/{id}/` | Same structure |
| Session summaries | ✅ Auto-generated via cron to `summary.json` | Use for initial session retrieval |
| Message storage | ✅ In `messages.jsonl` with embeddings | Same, adds contextual search |
| Search pattern | Summary search only | Contextual narrowing (summary → messages) |

**Migration path**: PRD #76 creates session folders with summaries and messages. This PRD adds contextual search within sessions.

### Relationship to PRD #55 (Advanced Session Features)

PRD #55 provides on-demand substring search and LLM context control. This PRD adds:
- Semantic search within sessions (not just substring)
- Automatic contextual retrieval (not just LLM-requested)
- Cross-session linking

**Coexistence**: Substring search for exact text, contextual retrieval for semantic similarity.

---

## Usage Examples

### Precise Contextual Retrieval

```
User: What was that auth bug we fixed?

Alfred: [Layer 2: Search summaries]
        → Found: Session 47 "Auth refactor, JWT issues"
        
        [Layer 3: Search messages in Session 47]
        → Found: "exp field null causing validation failure"
        → Found: "Need to handle refresh token rotation"
        → Neighbors: Testing discussion, fix deployment
        
        [Cross-link]
        → Related: Session 52 "Deployed auth fixes"

Alfred: Last Tuesday in your auth refactor session, you hit a JWT 
         null pointer when the exp field was missing. You fixed it 
         by adding null checks and deployed the changes Wednesday.
```

### Pattern Spotting Across Sessions

```
User: I've been struggling with auth a lot, haven't I?

Alfred: [Search summaries for "auth"]
        → Found 5 sessions mentioning auth
        
        [Analyze pattern across sessions]
        → Session 12: "Initial auth setup"
        → Session 23: "Auth bug fixes"
        → Session 47: "Auth refactor"
        → Session 52: "Auth deployment issues"
        → Session 61: "Auth optimization"
        
Alfred: You've had 5 major auth sessions over the past month:
         setup, bug fixes, a refactor, deployment issues, and 
         finally optimization. Want me to summarize what you've 
         learned across all of them?
```

### Context Expansion

```
User: Tell me more about that JWT issue.

Alfred: [Already have Session 47 from previous query]
        [Expand context - retrieve more messages from same session]
        → Earlier: "Considering switching to refresh tokens"
        → Later: "Decided against it for now, too complex"
        → Even later: "Actually need it for mobile app"
        
Alfred: It was part of a larger debate. You initially considered 
         refresh tokens but decided against the complexity. Later 
         you realized you need them for the mobile app—that's when 
         you hit the JWT null pointer issue.
```

---

## Milestones

| # | Milestone | Description | Success Criteria |
|---|-----------|-------------|------------------|
| 1 | **Session Index Storage** | Per-session message storage already exists from PRD #76 | Each session folder has messages.jsonl |
| 2 | **Session-Local Search** | Search messages within single session only | O(session_size) search, not O(total_messages) |
| 3 | **Two-Stage Retrieval** | Session summary search → in-session message search | Retrieve relevant sessions then drill down |
| 4 | **Context Assembly** | Format retrieval results for LLM context | Hierarchical context with sessions and messages |
| 5 | **Cross-Session Linking** | Find related sessions via shared themes | Suggest related sessions automatically |
| 6 | **Integration** | Wire into existing search tools | `search_contextual` tool available |
| 7 | **Testing** | Full test coverage | >90% coverage, precision benchmarks |

---

## Performance Characteristics

### Search Complexity

| Approach | Time Complexity | Space Complexity |
|----------|-----------------|------------------|
| Global message search | O(n) where n = total messages | O(n) |
| Session summary search | O(s) where s = total sessions | O(s) |
| **Contextual retrieval** | **O(s + m)** where m = avg session size | **O(s × m)** |

**Typical scenario**: 200 sessions, 50 msgs/session
- Global summary search: 200 comparisons
- Contextual (3 sessions × 50 messages): 350 comparisons total
- Higher precision by narrowing to relevant sessions first

### Storage Overhead

- Per-session message embeddings: ~1.5KB per message (same as global)
- Organization overhead: Session files vs single file
- Tradeoff: Query speed vs storage complexity

---

## Success Criteria

- [ ] Retrieve relevant messages 5x faster than global search
- [ ] Higher precision: >80% top-3 results are relevant (vs 60% global)
- [ ] Natural context expansion: Can drill down within sessions
- [ ] Cross-session linking: Suggests related conversations
- [ ] Transparent to users: Just better answers, no new interface
- [ ] Backwards compatible: Existing search still works

---

## Dependencies

- ✅ PRD #76 (Session Summarization) — Session summaries for Layer 2
- ✅ PRD #53 (Session System) — Session tracking and storage
- Existing embedding client
- Existing message storage

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-19 | Triple-layer architecture | Contextual narrowing beats global search |
| 2026-02-19 | Per-session embedding indices | Enables scoped search without global scan |
| 2026-02-19 | Session-first retrieval | Summaries provide better initial filtering |
| 2026-02-19 | Cross-session linking | Pattern spotting requires session relationships |
| 2026-02-19 | Additive to existing PRDs | Doesn't replace #76 or #55, enhances them |

---

## Open Questions

1. **Index format**: Separate file per session, or partition single index?
2. **Memory pressure**: Load session indices on demand or keep hot sessions cached?
3. **Cross-linking strategy**: Embedding similarity, shared keywords, or explicit links?
4. **Fallback behavior**: When contextual retrieval finds nothing, fall back to global?

---

**The hyperweb: Not just finding memories, but navigating the context around them.**
