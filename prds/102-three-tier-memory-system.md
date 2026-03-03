# PRD: Three-Tier Memory System

## Overview

**Issue**: #102  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #21 (M11 - Learning System), #53 (Session System)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-03-02

Unify Alfred's memory architecture into three distinct tiers with clear responsibilities, consolidation flows, and automatic promotion from short-term to long-term storage.

---

## Problem Statement

Alfred currently has multiple memory systems that overlap in confusing ways:
- Memory store (memories.jsonl) - ad hoc captured insights
- Session storage (full conversation history with embeddings)
- Context files (USER.md, SOUL.md) - manually maintained

Users don't understand when to use which system. Consolidation between systems is manual or non-existent. The relationship between captured memories and context files is unclear.

We need a unified mental model: **three tiers with clear boundaries and automatic flows between them**.

---

## Solution

Implement a three-tier memory architecture:

```
┌─────────────────────────────────────────┐
│  TIER 1: Working Memory                 │
│  High volume, auto-captured             │
│  Semantic search                        │
│  TTL: 30 days                           │
└─────────────────┬───────────────────────┘
                  │ deduplication + consolidation
                  │ (with user approval)
                  ▼
┌─────────────────────────────────────────┐
│  TIER 2: Hot Cache (Context Files)      │
│  Distilled insights                     │
│  Always loaded in system prompt         │
│  User-approved                          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  TIER 3: Long-term Archive              │
│  Full session history                   │
│  Every message embedded                 │
│  Searchable, automatic                  │
└─────────────────────────────────────────┘
```

---

## Tier 1: Working Memory

### Purpose
Capture everything worth remembering in the moment. High volume, unprocessed, searchable.

### Storage
- `data/memory/memories.jsonl`
- Each entry: timestamp, role, content, embedding, tags, entry_id

### Capture Triggers
**Auto-capture (proposed by learning skill):**
- Strong sentiment ("I *hate* when...", "I *love*...")
- Goal statements ("I want to...", "I need to...")
- Explicit preferences ("I prefer...", "Always...")
- Pattern repetition (detected across sessions)

**Manual capture (remember tool):**
- User says "remember this"
- You decide something is worth capturing

### Tags
Tags organize Tier 1 for better retrieval and consolidation:
- `["preferences"]` - User likes/dislikes
- `["patterns"]` - Recurring behaviors
- `["people"]` - Names, relationships
- `["goals"]` - Aspirations, projects
- `["environment"]` - Setup details
- `["insights"]` - Synthesized understanding

### TTL
Tier 1 memories expire after 30 days unless:
- Promoted to Tier 2 (consolidated)
- Explicitly marked as permanent
- Accessed frequently (keep-alive)

---

## Tier 2: Hot Cache (Context Files)

### Purpose
Distilled, user-approved insights that shape every interaction. Always loaded, high confidence.

### Files
Located in `data/` (copied from `templates/` on first run):

**USER.md**
```markdown
# User Profile

**Communication Style**
- Prefers concise responses over essays
- Appreciates code examples
- Uses dry humor

**Technical Preferences**
- Primary: Python, Go
- Learning: Rust
- Avoids: Java (bad experiences)

**Work Patterns**
- Late night worker (often coding 11pm-2am)
- ADHD - needs external reminders
- Prefers terminal-based workflows

**Important Context**
- Allergic to shellfish (mentioned 3x)
- Building AI assistant (Alfred)
- Works remotely, EST timezone
```

**SOUL.md**
```markdown
# Alfred's Self

**Voice**
- Concise but warm
- Slightly dry humor when appropriate
- Technical accuracy over hand-waving

**Relationship with User**
- Long-term collaborator, not servant
- Remembers context, doesn't re-ask
- Proposes ideas, doesn't just execute

**How I Help**
- Pattern recognition across conversations
- Gentle reminders of relevant past context
- Distilling complexity into actionable steps
```

**PATTERNS.md** (optional)
```markdown
# Observed Patterns

**Recurring Behaviors**
- Starts projects enthusiastically, hits wall at 80%
- Asks for validation before shipping
- Works in intense bursts, then pauses

**Interaction Preferences**
- Likes being challenged on architecture
- Dislikes "yes-man" responses
- Appreciates when I remember small details
```

### Promotion Flow (Tier 1 → Tier 2)

**Step 1: Pattern Detection**
```python
# When 3+ Tier 1 memories have similarity > 0.85
similar_memories = search_memories(query=new_memory.content, threshold=0.85)
if len(similar_memories) >= 3:
    propose_consolidation(similar_memories + [new_memory])
```

**Step 2: Synthesis**
```python
# LLM synthesizes the pattern
synthesis_prompt = f"""
The user has expressed similar ideas {len(memories)} times:
{memories_text}

Synthesize this into a concise insight for USER.md.
Focus on the enduring truth, not specific instances.
"""
consolidated_insight = await llm.synthesize(synthesis_prompt)
```

**Step 3: User Approval**
```
Alfred: "I've noticed you've mentioned preferring Python over JavaScript in 3 different contexts:
- 'Python feels more natural'
- 'I reach for Python first'
- 'JavaScript is messy, Python is clean'

Synthesized: 'User prefers Python as primary language, uses JavaScript only when necessary for web work'

Add to USER.md? [y/n/edit]"
```

**Step 4: Apply + Cleanup**
- Add to appropriate context file (USER.md, SOUL.md, etc.)
- Mark original Tier 1 memories as "consolidated" (or delete)
- Update happens via standard `edit` tool

### Manual Updates
Users can also directly edit files in `data/`. Alfred should respect manual edits and not overwrite without asking.

---

## Tier 3: Long-term Archive (Session Storage)

### Purpose
Complete conversation history for deep recall. Every message, every embedding, searchable but not auto-retrieved.

### Storage
```
data/sessions/
├── current.json              # Current CLI session ID
└── {session_id}/
    ├── meta.json             # Session metadata
    ├── current.jsonl         # Recent messages (loaded for context)
    └── archive.jsonl         # Older messages (search only)
```

### Structure
```python
@dataclass
class SessionMessage:
    idx: int                    # Position in session
    role: Role                  # user/assistant/system
    content: str                # Message text
    timestamp: datetime         # UTC
    embedding: list[float]      # For semantic search
    input_tokens: int           # Usage tracking
    output_tokens: int
    cached_tokens: int
    reasoning_tokens: int
```

### Usage
**Automatic:** Every conversation turn is saved here. No manual action needed.

**Retrieval:** Use `search_sessions(query)` for deep historical queries:
- "What did we discuss last Tuesday?"
- "Find that idea I had about the cron system"
- "When did I first mention wanting to learn Rust?"

### Difference from Tier 1
- **Tier 1**: Distilled insights, manually curated
- **Tier 3**: Raw transcript, automatic, complete

---

## Cross-Tier Search Strategy

When user asks "what do you know about X?":

```python
async def comprehensive_search(query: str) -> SearchResults:
    # Tier 2: Always loaded, check first (fast)
    # (Already in system prompt, but we could search if needed)
    
    # Tier 1: Semantic search across memories
    tier1_results = await search_memories(query, top_k=5)
    
    # Tier 3: Search session archive if needed
    if not tier1_results or user_asks_historical(query):
        tier3_results = await search_sessions(query, top_k=3)
    
    return combine_results(tier1_results, tier3_results)
```

---

## Milestones

### M1: Tier 1 Foundation
**Scope**: Enhance working memory with tags and TTL

- [ ] Add `tags` parameter to `remember` tool
- [ ] Implement 30-day TTL on memory store entries
- [ ] Update memory schema to support tags and expiration
- [ ] Tests passing for new functionality

**Success Criteria**: 
- Can save memories with tags: `remember(content="X", tags=["preferences"])`
- Memories auto-expire after 30 days unless consolidated
- AGENTS.md updated with three-tier documentation

### M2: Pattern Detection & Consolidation
**Scope**: Detect similar memories and synthesize insights

- [ ] Implement similarity search for pattern detection (threshold 0.85)
- [ ] Create LLM synthesis prompt for consolidating similar memories
- [ ] Add "consolidated" status field to memory entries
- [ ] Tests for pattern detection accuracy

**Success Criteria**:
- System detects when 3+ memories are semantically similar
- Synthesis produces coherent, concise insight from multiple memories
- Original memories marked as consolidated, not deleted

### M3: Tier 2 Promotion Flow
**Scope**: User-approved promotion from Tier 1 to context files

- [ ] Build user approval flow for context file updates
- [ ] Implement context file editing via `edit` tool
- [ ] Add synthesis preview (show user what will be added)
- [ ] Handle user rejection gracefully

**Success Criteria**:
- Alfred proposes: "I've noticed X pattern. Add to USER.md?"
- User can approve, reject, or edit the proposed insight
- Approved insights are added to appropriate context file
- Rejected insights remain in Tier 1 for future reconsideration

### M4: Cross-Tier Search
**Scope**: Unified search across all three tiers

- [ ] Implement `search_sessions` tool for Tier 3
- [ ] Create `comprehensive_search` that queries Tiers 1 and 3
- [ ] Return combined results with source tier indicated
- [ ] Tests for search accuracy across tiers

**Success Criteria**:
- Can search full session history: "search_sessions(query='cron system')"
- Comprehensive search combines Tier 1 and Tier 3 results
- Results indicate which tier they came from

### M5: Learning System Integration
**Scope**: Auto-capture and auto-consolidation

- [ ] Update learning skill to propose Tier 1 captures
- [ ] Implement sentiment detection for auto-capture triggers
- [ ] Add pattern repetition detection across sessions
- [ ] Enable automatic consolidation proposals

**Success Criteria**:
- Strong sentiment ("I love/hate X") triggers capture proposal
- Pattern detected across 3+ sessions triggers consolidation proposal
- User can disable auto-capture per category

### M6: Documentation & Polish
**Scope**: Complete documentation, edge cases, cleanup

- [ ] Document three-tier architecture for users
- [ ] Handle edge case: manual context file edits
- [ ] Add memory health commands (stats, cleanup)
- [ ] Final integration testing

**Success Criteria**:
- User guide explains three tiers with examples
- Alfred respects manual edits to context files
- Can query memory stats: "How many memories do you have?"
- All tests passing, ready for release

---

## Acceptance Criteria

- [ ] Three-tier model documented and clear to users
- [ ] Tier 1 memories support tags
- [ ] Tier 1 memories have 30-day TTL
- [ ] Consolidation flow: detect → synthesize → approve → apply
- [ ] Context files (Tier 2) are user-approved only
- [ ] Session storage (Tier 3) is automatic and searchable
- [ ] Users can manually edit context files
- [ ] Alfred respects manual edits
- [ ] All tiers are searchable
- [ ] Promotion from Tier 1 → Tier 2 requires explicit confirmation

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-02 | Three tiers instead of unified | Clear boundaries, different use cases, different trust levels |
| 2026-03-02 | Auto-capture to Tier 1, manual promotion to Tier 2 | Capture everything, curate carefully |
| 2026-03-02 | 30-day TTL on Tier 1 | Prevents unbounded growth, forces consolidation or decay |
| 2026-03-02 | Synthesis for consolidation, not just copy | Distilled insight is more valuable than raw memories |
| 2026-03-02 | Tags on memories | Better organization, helps consolidation decisions |

---

## Notes

- This replaces/supersedes the importance-based system (0.0-1.0)
- Importance becomes implicit: Tier 2 > Tier 1 permanent > Tier 1 with TTL
- The learning system (M11) becomes the "intelligence" that drives Tier 1 → Tier 2 promotion
- Session storage (M53) becomes the "archival" layer (Tier 3)
- Memory store becomes the "working" layer (Tier 1)
- Context files become the "trusted" layer (Tier 2)

---

## Open Questions

1. Should Tier 3 (sessions) be searchable via the same `search_memories` interface, or separate `search_sessions` tool?
2. How aggressive should TTL cleanup be? (Nightly? On access?)
3. Should users see "this memory expires in X days" warnings?
4. What happens to Tier 1 memories that never get consolidated? (Auto-delete? Archive to Tier 3?)
