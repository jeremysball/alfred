# PRD: Support Memory Foundation

**GitHub Issue**: [#167](https://github.com/jeremysball/alfred/issues/167)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-03-30

---

## 1. Problem Statement

Alfred's current memory model is still organized around search and session recall rather than active support.

Three problems follow from that:

1. **Active work is not first-class memory**
   - Projects, tasks, and open loops are not the main runtime state.
   - Alfred often has to reconstruct active work from session history instead of reading a durable work model.

2. **Cross-session evidence is too narrative and too implicit**
   - Session summaries and raw search results are useful for recall, but they do not provide a small typed substrate for later support decisions.
   - Alfred can find prior conversations, but it cannot reliably answer: what is the active project, what is blocked, and what is the next step?

3. **Session search is carrying too much product weight**
   - Search is useful as provenance and evidence lookup.
   - It is not a strong primary abstraction for longitudinal support.
   - "Archive → search → hope for insight" is the wrong center of gravity.

The result is a system that can remember conversations, but not yet maintain an operational model of what the user is trying to do.

---

## 2. Goals

1. Make **projects, tasks, and open loops** first-class memory objects.
2. Add **structured session observations** as a typed bridge between raw sessions and durable support memory.
3. Keep the **raw session archive and search** as an internal provenance layer rather than the main product abstraction.
4. Improve Alfred's ability to resume active work without requiring the user to restate status.
5. Keep the design general-purpose rather than tied to a diagnosis-specific mode.
6. Create a foundation that later PRDs can use for support adaptation and reflection.
7. Treat **documentation and managed prompt/template updates** as part of the feature so Alfred's runtime instructions and user-facing explanations match the new memory model.

---

## 3. Non-Goals

- Implementing support-profile adaptation logic.
- Defining the intervention taxonomy or support-dimension update rules.
- Building weekly reflection or review UX.
- Replacing the archive or deleting session search.
- Building a full task manager with arbitrary project-management features.

---

## 4. Proposed Solution

### 4.1 Memory layers covered by this PRD

This PRD establishes the first three layers of the new memory model:

1. **Raw archive**
   - Full session history, tool outcomes, timestamps, and search index.
   - Retained for provenance, debugging, auditability, and evidence lookup.

2. **Session observations**
   - Compact structured extraction written per session.
   - Serves as typed evidence for downstream synthesis.

3. **Projects / tasks / open loops**
   - Durable operational memory for what the user is actively trying to do.
   - Becomes the primary runtime state for execution support.

Later PRDs will add the support profile and intervention learning on top of this foundation.

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
- open-loop management
- support-style decisions

### 4.3 Add structured session observations

Each session should produce a small typed observation record.

Minimum v1 fields:
- `session_id`
- `time_range`
- `primary_context` (for example: admin task, planning, review, scheduling)
- `intents`
- `projects_touched`
- `tasks_touched`
- `blockers_observed`
- `interventions_attempted`
- `outcome_signals`
- `evidence_refs`

Example:

```json
{
  "session_id": "sess_812",
  "primary_context": "admin_task",
  "intents": ["file taxes"],
  "projects_touched": ["taxes_2026"],
  "tasks_touched": ["download_w2"],
  "blockers_observed": ["task_initiation", "unclear_document_location"],
  "interventions_attempted": ["first_physical_step", "five_minute_timer"],
  "outcome_signals": ["task_started", "document_downloaded"],
  "evidence_refs": ["msg_441", "tool_88"]
}
```

The observation schema should be fixed and versioned.

### 4.4 Make projects, tasks, and open loops first-class memory

Alfred should maintain a durable work model with explicit objects for:
- **projects**: larger ongoing outcomes
- **tasks**: concrete actionable items
- **open loops**: unresolved commitments, waits, blockers, or pending follow-up states

Minimum v1 expectations:
- stable IDs
- status
- title
- relationship links
- next step
- blockers
- timestamps
- evidence refs back to sessions

Example task record:

```json
{
  "task_id": "download_w2",
  "project_id": "taxes_2026",
  "title": "Download W-2 from payroll portal",
  "status": "active",
  "next_step": "Open payroll portal and locate tax forms page",
  "blocked_by": ["unclear_document_location"],
  "source_refs": ["sess_812", "obs_812"]
}
```

### 4.5 Retrieval should prioritize operational state over archive recall

When Alfred is helping the user act, runtime retrieval should prefer:
1. relevant project/task/open-loop state
2. recent session observations tied to that work
3. archive/search hits only when evidence or history is needed

That makes the main memory question:
- not "what did we talk about?"
- but "what is active, what is blocked, and what is the next move?"

### 4.6 Keep work memory general-purpose

Projects and tasks should support all of Alfred's general capabilities, not just executive-function-heavy use cases.

Examples:
- coding work
- life admin
- research threads
- docs work
- follow-ups with other people
- decisions awaiting confirmation

The model should not require an explicit ADHD or coaching mode to use this structure.

### 4.7 Migration and coexistence

The current memory system should not be rewritten all at once.

Recommended rollout:
1. keep archive and search intact
2. add typed session observations
3. add first-class project/task/open-loop storage
4. update runtime retrieval to prefer the new operational layer
5. keep search as provenance and fallback

---

## 5. User Experience Requirements

Users should be able to experience Alfred as a system that:
- knows their active work without asking for a recap every time
- can tell the difference between a project, a task, and a blocked loop
- can resume where they left off
- can explain where a remembered work item came from

Examples of expected behavior:
- "What am I actively working on right now?"
- "What's blocked?"
- "What's the next step on taxes?"
- "What open loops do I still have from last week?"

---

## 6. Success Criteria

- [ ] Alfred stores projects, tasks, and open loops as first-class durable memory objects.
- [ ] Alfred can answer active-work questions without relying only on session search.
- [ ] Each session produces a structured observation record using a versioned schema.
- [ ] Operational retrieval prefers project/task/open-loop state over raw archive hits.
- [ ] Session search remains available for provenance and recall flows.
- [ ] The implementation keeps one clear source of truth for active work state.

---

## 7. Milestones

### Milestone 1: Define the support-memory foundation contract
Document the new layer responsibilities and demote session search to an internal archive/provenance primitive rather than the primary product abstraction.

Validation: architecture/docs and tests agree on the role of archive, observations, and operational work memory.

### Milestone 2: Add typed session observations
Implement a fixed observation schema and generate structured per-session records from recent session evidence.

Validation: targeted tests prove observation extraction creates stable, versioned records from session inputs.

### Milestone 3: Add first-class project, task, and open-loop models
Implement durable storage and relationships for projects, tasks, and open loops with evidence links.

Validation: targeted tests prove Alfred can create, update, and read operational work state independently of raw session search.

### Milestone 4: Switch runtime retrieval to operational-first memory
Update runtime context assembly and assistant flows to prefer operational work state and recent observations before falling back to archive recall.

Validation: targeted tests prove active-work questions are answered from the operational layer first, with archive used for provenance or fallback.

### Milestone 5: Regression coverage, documentation, and prompt/template updates
Add or update tests, docs, and managed prompt/template content for the support-memory foundation and its retrieval contract.

Validation: relevant Python validation passes, memory architecture docs reflect the new runtime model, and managed prompt/template content explains the new operational memory behavior consistently.

---

## 8. Likely File Changes

```text
src/alfred/memory/...                  # new or updated support-memory models and storage
src/alfred/context.py                  # retrieval priority updates
src/alfred/session.py                  # session observation integration
src/cli/main.py or related command UI  # if active-work inspection commands are added

docs/MEMORY.md
docs/ARCHITECTURE.md
templates/SYSTEM.md
templates/AGENTS.md
templates/prompts/agents/memory-system.md
prds/167-support-memory-foundation.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The work model turns into a full task-management product | Medium | keep v1 focused on projects, tasks, open loops, and next-step state |
| Duplicate truths emerge between archive, observations, and work objects | High | make projects/tasks/open loops the operational source of truth and keep evidence refs explicit |
| Session extraction becomes too freeform | Medium | use a fixed versioned observation schema |
| Runtime retrieval still overuses archive recall | Medium | encode and test operational-first retrieval order |

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
- memory architecture
- retrieval order
- role of session search after demotion
- how active projects/tasks/open loops are represented in Alfred's managed instructions and memory guidance

---

## 11. Related PRDs

- PRD #102: Unified Memory System
- PRD #117: Unified SQLite Storage System
- PRD #135: Persistent Memory Context
- PRD #167 depends on no new feature PRD, but establishes the substrate for #168 and #169

---

## 12. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Keep raw session archive and search | They remain valuable for provenance, recall, and evidence lookup |
| 2026-03-30 | Demote session search from product abstraction to internal primitive | Search alone is not a strong runtime model for active support |
| 2026-03-30 | Make projects, tasks, and open loops first-class memory | Alfred needs operational state, not just recall |
| 2026-03-30 | Add typed session observations | They create a small structured bridge from conversations to durable support memory |
