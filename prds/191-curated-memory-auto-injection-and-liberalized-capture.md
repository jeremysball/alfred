# PRD: Curated Memory Auto-Injection and Liberalized Capture

**GitHub Issue**: [#191](https://github.com/jeremysball/alfred/issues/191)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-04-07  
**Author**: Agent

---

## 1. Problem Statement

Alfred still underuses curated memory.

The current runtime already injects relevant curated memories automatically in context assembly. But the system contract around memory is still too ambiguous and too conservative.

Today, several things are true at once:
- `src/alfred/context.py` already searches and injects relevant memories into prompt context automatically
- the runtime still exposes `search_memories` as a tool
- prompt guidance still tells the model to search memories explicitly in many cases
- `remember` guidance emphasizes selectivity so strongly that Alfred under-captures durable reusable facts, preferences, decisions, and recurring constraints

That creates five problems:

1. **The recall contract is too tool-centric**
   - Alfred can already see relevant curated memories without calling a tool in many cases.
   - But the prompts and tool descriptions still make it sound as if explicit memory search is the normal path.

2. **The write policy is too conservative**
   - Alfred is currently biased toward remembering less.
   - That causes the system to miss facts and preferences that would clearly help later.

3. **Curated memory and support memory are not cleanly distinguished in practice**
   - Structured support memory should remain the main continuity layer for active work.
   - Curated memory should remain the reusable durable-fact layer.
   - The current guidance does not sharpen that distinction enough.

4. **`search_memories` has not settled into its best role**
   - It should be available for targeted lookup, inspection, or explicit recall.
   - It should not feel required for ordinary durable-memory access when relevant memories are already auto-injected.

5. **Docs and runtime guidance drift toward underuse**
   - Current wording such as “remember less” and strong emphasis on selectivity has likely pushed the model too far toward caution.

The result is a system that technically has curated memory, but does not use it as confidently or as often as it should.

---

## 2. Goals

1. Make auto-injected curated memory the default memory-recall path.
2. Keep `search_memories` as an optional targeted lookup and inspection tool.
3. Liberalize `remember` so Alfred stores more useful durable context.
4. Clarify the boundary between structured support memory, curated memory, always-loaded files, and session archive.
5. Align tool descriptions, prompts, docs, and tests with the true runtime contract.
6. Preserve signal quality so curated memory does not become noisy junk.

---

## 3. Non-Goals

- Removing the `search_memories` tool.
- Replacing structured support memory with curated memory.
- Turning every turn into an automatic memory write.
- Replacing the support-learning model from PRD #183.
- Replacing session archive search with curated memory.
- Building a full semantic memory-worthiness adjudicator in this PRD.

---

## 4. Proposed Solution

### 4.1 Make auto-injection the explicit contract

The runtime should treat curated memory retrieval as automatic by default.

Contract:
- relevant curated memories are assembled automatically into prompt context when available
- the model should not have to call `search_memories` just to access ordinary relevant durable memory
- docs and prompts should describe `search_memories` as an optional targeted lookup path, not the primary everyday recall path

### 4.2 Keep `search_memories` for targeted recall

`search_memories` still matters.

Its best-fit uses are:
- explicit memory lookup
- inspection of a specific recalled fact
- targeted recall when the current prompt context is not enough
- narrow retrieval requested by the user
- debugging or evidence-gathering behavior when the model wants a specific memory slice

Recommended rule:
- auto-injected memory first
- explicit `search_memories` only when Alfred wants additional targeted retrieval beyond the default context

### 4.3 Liberalize `remember`

The write policy should become more willing to store:
- stable user preferences likely to recur
- recurring user instructions and interaction preferences
- durable project decisions
- recurring constraints
- facts or context that are likely to matter again across future conversations

The policy should become less hesitant about writing memories that are clearly reusable later.

### 4.4 Keep the lane boundaries sharp

Clarify the memory split:
- **structured support memory** = active work, arcs, blockers, tasks, decisions, open loops, episodes, and runtime support state
- **curated memory** = reusable durable facts, preferences, recurring context, and durable decisions worth semantic retrieval later
- **always-loaded files** = explicit durable truths and operating rules
- **session archive** = transcript provenance and time-bounded recall

### 4.5 Add explicit boundary rules with support memory and learning

Curated memory should become more used, but it must not cheapen or override the support systems designed elsewhere.

Required ownership rules:
- `remember()` stores **explicit reusable context**, not adaptive runtime policy
- structured support memory owns **active work state** such as blockers, tasks, decisions, arcs, and open loops
- support learning owns **effective support and relational adaptation** such as values, patterns, observations, and cases
- curated memory may preserve explicit user-stated preferences or durable decisions that are relevant to those systems, but it does not replace them

Examples of what `remember()` should store:
- explicit user preferences likely to recur
- explicit recurring user instructions
- durable project decisions
- recurring constraints
- stable facts worth semantic retrieval later

Examples of what `remember()` should not become:
- the system of record for active blocker or task state
- the system of record for effective support values
- a dumping ground for inferred identity themes or candidate support patterns
- a substitute for support-learning observations, cases, or promotion logic

### 4.6 Define precedence and conflict rules

When multiple systems can speak to the same topic, the runtime should use this precedence:

For active-work, resume, orient, and blocked-work questions:
1. current conversation
2. structured support memory
3. fresh `ArcSituation` / `GlobalSituation` views
4. curated memory
5. session archive

For how Alfred should help or what interaction style works best:
1. explicit user correction or instruction in the current conversation
2. effective runtime support and relational values
3. explicit remembered preferences
4. session/archive evidence

For durable user truth:
1. explicit durable files such as `USER.md`
2. explicit remembered facts and preferences
3. learned support patterns only as evidence, not as silently promoted truth

Rule:
- curated memory supplements the other systems
- it does not outrank the systems built for active operational state or adaptive support behavior

### 4.7 Forbid silent cross-promotion between systems

These systems may reference one another, but they should not silently collapse into one another.

Prohibited by default:
- curated memories automatically becoming support-profile values
- support observations automatically becoming curated memories
- curated memories automatically becoming `USER.md`
- learned support patterns automatically rewriting explicit durable truth

Allowed by default:
- one system citing another as evidence
- user-visible or explicitly coded promotion flows with their own rules and review surfaces

### 4.8 Tighten wording across prompts and tools

Update wording so the runtime is steered toward the intended behavior.

Examples of needed shifts:
- from “remember less” toward “remember reusable durable facts and preferences more readily”
- from “search memories before asking the user to repeat” toward “relevant memories are already injected; use `search_memories` for targeted lookup when needed”
- from extreme selectivity toward bounded but more confident capture
- from blurry memory-language toward explicit ownership and precedence rules across curated memory, support memory, learned support values, and session archive

### 4.9 Keep quality safeguards

Liberalized memory capture should still avoid junk.

Required safeguards:
- prefer concise reusable memories over verbose transcripts
- avoid remembering obvious one-off noise
- avoid storing secrets unless the user asks or the system already treats them as appropriate durable context
- preserve permanent-vs-TTL behavior where relevant
- avoid storing inferred adaptive policy when the correct home is structured support learning

---

## 5. User Experience Requirements

Users should experience Alfred as:
- more likely to remember stable preferences and recurring facts
- less likely to ask for repetition of things that should already be known
- still capable of targeted explicit memory lookup when needed
- clearer about what kind of memory system is being used for which job

Representative experiences:
- “Remember that I do better with one next step.”
- “We’re using SQLite for this project.”
- “I hate being given five options at once.”
- “What have you remembered about how I like to work?”
- “Can you pull up what you remembered about the database choice?”

---

## 6. Success Criteria

- [ ] Prompt and tool guidance make auto-injected curated memory the default recall path.
- [ ] `search_memories` remains available, but is described as optional targeted lookup.
- [ ] `remember` guidance becomes materially more liberal about reusable durable facts, preferences, and decisions.
- [ ] Docs clearly distinguish curated memory from structured support memory, support learning, durable files, and session archive.
- [ ] The PRD defines explicit ownership, precedence, and no-silent-cross-promotion rules so curated memory does not clobber support runtime or learning.
- [ ] Tests and prompts align with the new memory contract.
- [ ] Alfred captures more useful curated memories without collapsing into noisy accumulation or flattening other memory systems.

---

## 7. Milestones

### Milestone 1: Define the curated-memory runtime contract
Clarify that relevant curated memories are auto-injected by default and that `search_memories` is supplemental.

Validation: docs and prompts describe the current and intended runtime truthfully.

### Milestone 2: Liberalize memory-write guidance
Update tool descriptions and prompt guidance so Alfred writes more useful curated memories.

Validation: the runtime guidance clearly favors capturing reusable facts, preferences, and decisions more often.

### Milestone 3: Define boundary and precedence rules
Update the PRD, prompts, and docs so curated memory has explicit ownership boundaries relative to support memory, support learning, durable files, and session archive.

Validation: curated memory is clearly supplemental and cannot silently override operational state or adaptive support policy.

### Milestone 4: Align retrieval and inspection guidance
Update the retrieval order and usage guidance across prompts, docs, and tool metadata.

Validation: `search_memories` is positioned as targeted lookup rather than a required default step, and the precedence rules stay clear.

### Milestone 5: Add targeted regression coverage
Update tests that reinforce tool ordering, tool descriptions, memory guidance, and the clarified contract boundaries.

Validation: tests reflect the new contract and prevent drift back toward underuse or boundary collapse.

---

## 8. Likely File Changes

```text
prds/191-curated-memory-auto-injection-and-liberalized-capture.md
docs/ROADMAP.md
docs/MEMORY.md
docs/how-alfred-helps.md
docs/relational-support-model.md
templates/SYSTEM.md
templates/prompts/agents/memory-system.md
src/alfred/tools/remember.py
src/alfred/tools/search_memories.py
tests/test_tool_metadata.py
tests/test_templates.py
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Curated memory becomes too noisy | High | keep the policy focused on reusable durable facts, preferences, decisions, and recurring constraints |
| Curated memory clobbers or cheapens support learning and operational memory | High | define ownership, precedence, and no-silent-cross-promotion rules explicitly |
| The distinction between curated memory and support memory blurs further | High | restate lane boundaries clearly in docs and prompts |
| `search_memories` becomes neglected even when targeted lookup would help | Medium | keep it available and describe its explicit best-fit uses |
| Docs drift from runtime reality again | Medium | treat prompt guidance, tool descriptions, and docs as part of the acceptance criteria |

---

## 10. Open Questions

1. Should auto-injected curated memory become more prominent in `/context` so users can see what was loaded?
2. Should the `remember` tool description explicitly name stable interaction preferences and recurring user instructions as primary examples?
3. Should later work add a separate semantic memory-worthiness adjudicator, or is prompt liberalization enough for now?
