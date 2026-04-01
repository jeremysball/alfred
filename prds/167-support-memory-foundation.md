# PRD: Support Memory Foundation

**GitHub Issue**: [#167](https://github.com/jeremysball/alfred/issues/167)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-03-30

---

## 1. Problem Statement

Alfred's current memory model is still organized primarily around recall rather than active support.

Three problems follow from that:

1. **Active work is not first-class memory**
   - Projects, tasks, and open loops are not yet the main runtime state.
   - Alfred often has to reconstruct what matters from session history instead of reading a durable operational model.

2. **Evidence for later learning is too coarse and too narrative**
   - Raw sessions and summary search are useful for recall.
   - They are too blunt to support reliable intervention learning, relational learning, or reflective synthesis.
   - One blob per session is not enough for a system that moves between planning, execution, decision support, and reflection within a single conversation.

3. **Session search is carrying too much product weight**
   - Search should remain valuable for provenance and recall.
   - It should not remain the primary abstraction for active support, next-step selection, or structured learning.

The result is a system that can remember conversations, but does not yet maintain a compact operational model of what the user is doing or a typed evidence layer for later support learning.

---

## 2. Goals

1. Make **projects, tasks, and open loops** first-class durable memory objects.
2. Add **typed interaction episodes** as the core evidence unit between raw archive and later support learning.
3. Add **session-level syntheses** derived from episode evidence when useful, without treating the session blob as the main learning unit.
4. Keep the **raw session archive and search** as provenance and recall infrastructure rather than the main runtime abstraction.
5. Improve Alfred's ability to resume active work, blocked work, pending decisions, and unresolved loops without requiring a recap.
6. Keep the memory substrate general-purpose across action support, decision support, review, identity reflection, and direction reflection.
7. Establish the foundation that PRDs #168 and #169 will use for support learning and reflection.
8. Treat documentation and managed prompt/template updates as part of the feature so the memory model is explained consistently.

---

## 3. Non-Goals

- Implementing support-profile adaptation rules.
- Defining the full relational/support-dimension registries.
- Building review card UX or weekly reflection flows.
- Replacing the archive or deleting session search.
- Building a full task-management product with arbitrary PM features.
- Letting reflective themes silently become durable identity truth.

---

## 4. Proposed Solution

### 4.1 Memory layers covered by this PRD

This PRD should establish the operational and evidentiary foundation for the relational support system.

It covers four layers:

1. **Raw archive**
   - Full session history, tool outcomes, timestamps, and search index.
   - Retained for provenance, evidence lookup, debugging, recall, and auditability.

2. **Interaction episodes**
   - Typed slices of a session with one dominant context and explicit evidence refs.
   - Becomes the primary unit for downstream learning.

3. **Session syntheses**
   - Compact rollups of a session derived from its episodes.
   - Useful for search, review, and summarization, but not the only structured memory surface.

4. **Projects / tasks / open loops**
   - Durable operational memory for what the user is actively trying to do, decide, revisit, or resolve.
   - Becomes the primary runtime state for support.

Later PRDs add support profiles, intervention learning, pattern generation, review cards, and correction controls on top of this foundation.

### 4.2 Demote session search to an internal primitive

Session search should remain available, but its role changes.

It should be used for:
- provenance
- evidence lookup
- user recall requests
- debugging and explanation
- backfilling structured observations when needed

It should not be the main runtime abstraction for:
- active work tracking
- next-step selection
- blocked-loop management
- support-style decisions
- reflective pattern generation

### 4.3 Add typed interaction episodes

A session should be able to contain multiple typed episodes.

Each episode should represent a locally coherent support exchange with one dominant context.

Minimum v1 fields:
- `episode_id`
- `session_id`
- `time_range`
- `dominant_context`
- `subject_refs`
- `projects_touched`
- `tasks_touched`
- `open_loops_touched`
- `blockers_observed`
- `interventions_attempted`
- `response_signals`
- `outcome_signals`
- `evidence_refs`

Example:

```json
{
  "episode_id": "ep_204",
  "session_id": "sess_812",
  "dominant_context": "decide",
  "subject_refs": ["startup_future", "prestige_vs_aliveness"],
  "projects_touched": ["studio_strategy_2026"],
  "tasks_touched": [],
  "open_loops_touched": ["commit_to_direction_q2"],
  "blockers_observed": ["value_misalignment", "fear_of_visibility"],
  "interventions_attempted": ["tradeoff_frame", "name_values_mismatch"],
  "response_signals": ["resonance", "deepening"],
  "outcome_signals": ["decision_clarified"],
  "evidence_refs": ["msg_441", "msg_446"]
}
```

The episode schema should be fixed and versioned.

### 4.4 Add session-level syntheses derived from episodes

Session-level summaries are still useful.

However, they should be treated as derived rollups built from the episode layer rather than the sole structured substrate.

Session syntheses can support:
- search and recall
- higher-level weekly review input
- human-readable summaries of what changed

But operational retrieval and later support learning should rely on episodes plus durable support memory, not summaries alone.

### 4.5 Make projects, tasks, and open loops first-class memory

Alfred should maintain a durable operational model with explicit objects for:
- **projects** — larger ongoing outcomes or threads
- **tasks** — concrete actionable items
- **open loops** — unresolved commitments, waits, blockers, pending decisions, or reflective threads requiring return

Minimum v1 expectations:
- stable IDs
- status
- title
- relationship links
- next step or current unresolved state
- blockers
- timestamps
- evidence refs back to sessions or episodes

Example task record:

```json
{
  "task_id": "download_w2",
  "project_id": "taxes_2026",
  "title": "Download W-2 from payroll portal",
  "status": "active",
  "next_step": "Open payroll portal and locate tax forms page",
  "blocked_by": ["unclear_document_location"],
  "source_refs": ["sess_812", "ep_204"]
}
```

Example open-loop record:

```json
{
  "open_loop_id": "commit_to_direction_q2",
  "title": "Choose whether to keep pursuing the startup path",
  "status": "pending_review",
  "kind": "decision_thread",
  "current_tension": "Prestige and aliveness keep pulling in different directions",
  "source_refs": ["sess_812", "ep_204"]
}
```

### 4.6 Retrieval should prioritize operational state over archive recall

When Alfred is helping the user act, decide, review, or resume, runtime retrieval should prefer:
1. relevant project/task/open-loop state
2. recent episodes tied to that state
3. session syntheses tied to those episodes
4. archive/search hits only when evidence or history is needed

That changes the main question from:
- "what did we talk about?"

to:
- "what is active, what is unresolved, what is blocked, and what is the next move?"

### 4.7 Keep the operational substrate general-purpose

Projects, tasks, and open loops should support all of Alfred's general support contexts, not just execution-heavy use cases.

Examples:
- coding work
- life admin
- research threads
- collaboration follow-ups
- pending decisions
- reflective threads worth returning to

The substrate should not require a diagnosis-specific mode to be useful.

### 4.8 Migration and coexistence

The current memory system should not be rewritten all at once.

Recommended rollout:
1. keep archive and search intact
2. add typed episodes
3. add session syntheses derived from episodes where useful
4. add durable project/task/open-loop storage
5. update runtime retrieval to prefer the operational layer
6. keep archive search as provenance and fallback

---

## 5. User Experience Requirements

Users should experience Alfred as a system that:
- knows their active work and open loops without asking for a recap every time
- can distinguish between a project, a task, a blocked loop, and a pending decision
- can resume where they left off even when the prior conversation mixed multiple support contexts
- can explain where a remembered work item or unresolved loop came from

Examples of expected behavior:
- "What am I actively working on right now?"
- "What's blocked?"
- "What decisions are still open?"
- "What's the next step on taxes?"
- "What threads from last week still need attention?"

---

## 6. Success Criteria

- [ ] Alfred stores projects, tasks, and open loops as first-class durable memory objects.
- [ ] Alfred stores typed interaction episodes as a versioned evidence layer.
- [ ] Operational retrieval prefers project/task/open-loop state and relevant episodes over raw archive hits.
- [ ] Session search remains available for provenance and recall flows.
- [ ] Alfred can answer active-work and unresolved-loop questions without relying only on session search.
- [ ] The implementation keeps one clear source of truth for operational support state.

---

## 7. Milestones

### Milestone 1: Define the support-memory foundation contract
Document the layer responsibilities for archive, episodes, session syntheses, and operational support memory.

Validation: architecture/docs and tests agree on the role of each layer.

### Milestone 2: Add typed interaction episodes
Implement a fixed episode schema and generate stable episode records from session evidence.

Validation: targeted tests prove episode extraction creates stable, versioned records from mixed-context session inputs.

### Milestone 3: Add first-class project, task, and open-loop models
Implement durable storage and relationships for operational support state with evidence links.

Validation: targeted tests prove Alfred can create, update, and read operational work state independently of raw session search.

### Milestone 4: Switch runtime retrieval to operational-first memory
Update runtime context assembly and assistant flows to prefer operational state and relevant episode evidence before falling back to archive recall.

Validation: targeted tests prove active-work questions are answered from the operational layer first, with archive used for provenance or fallback.

### Milestone 5: Regression coverage, documentation, and prompt/template updates
Add or update tests, docs, and managed prompt/template content for the support-memory foundation and its retrieval contract.

Validation: relevant Python validation passes, memory architecture docs reflect the new runtime model, and managed prompt/template content explains operational-first retrieval consistently.

---

## 8. Likely File Changes

```text
src/alfred/memory/...                  # support-memory models and storage
src/alfred/context.py                  # retrieval priority updates
src/alfred/session.py                  # episode extraction and synthesis integration
src/cli/main.py or related command UI  # if active-work inspection commands are added

docs/MEMORY.md
docs/ARCHITECTURE.md
docs/relational-support-model.md
templates/SYSTEM.md
templates/AGENTS.md
prds/167-support-memory-foundation.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The work model turns into a full task manager | Medium | keep v1 focused on projects, tasks, open loops, and next-step state |
| Duplicate truths emerge between archive, episodes, and operational objects | High | make projects/tasks/open loops the operational source of truth and keep evidence refs explicit |
| Episode extraction becomes too freeform | Medium | use a fixed, versioned episode schema |
| Runtime retrieval still overuses archive recall | Medium | encode and test operational-first retrieval order |
| Reflective threads have nowhere to live in the operational model | Medium | allow open loops to represent pending decisions and reflective return threads |

---

## 10. Validation Strategy

This is a Python-led change.

Required validation:

```bash
uv run ruff check src/
uv run mypy --strict src/
uv run pytest <targeted tests for touched memory and context surfaces>
```

Docs and prompt/template updates should cover:
- operational memory architecture
- episode and synthesis roles
- retrieval order
- role of session search after demotion
- how projects/tasks/open loops are represented in Alfred's managed instructions and memory guidance

---

## 11. Related PRDs

- PRD #147: Alfred Self-Model and Personality
- PRD #168: Adaptive Support Profile and Intervention Learning
- PRD #169: Reflection Reviews and Support Controls
- PRD #179: Relational Support Operating Model

---

## 12. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Keep raw session archive and search | They remain valuable for provenance, recall, and evidence lookup |
| 2026-03-30 | Use typed interaction episodes as the main evidence unit | Support learning needs finer structure than one session blob |
| 2026-03-30 | Make projects, tasks, and open loops first-class memory | Alfred needs operational state, not just recall |
| 2026-03-30 | Demote session search from product abstraction to internal primitive | Search alone is not a strong runtime model for active support |
| 2026-03-30 | Allow open loops to cover pending decisions and reflective return threads | Operational support must cover more than task execution |
