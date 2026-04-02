# PRD: Support Memory Foundation

**GitHub Issue**: [#167](https://github.com/jeremysball/alfred/issues/167)  
**Priority**: High  
**Status**: In Progress
**Created**: 2026-03-30

---

## 1. Problem Statement

Alfred's current memory model is still organized primarily around recall rather than active support.

Four problems follow from that:

1. **Active continuity is not first-class memory**
   - Projects, tasks, open loops, and decisions are not yet the main runtime state.
   - Alfred often has to reconstruct what matters from session history instead of reading a durable operational model.

2. **The session is carrying too much semantic weight**
   - In traditional chat apps, one session acts as chat container, context boundary, meaning unit, and memory boundary.
   - That is too blunt for Alfred.
   - A single session can include multiple support episodes and multiple targets, while a meaningful work thread can continue across many sessions.

3. **Evidence for later learning is too coarse and too narrative**
   - Raw sessions and summary search are useful for recall.
   - They are too blunt to support reliable intervention learning, relational learning, or reflective synthesis.
   - One blob per session is not enough for a system that moves between planning, execution, decision support, and reflection within a single conversation.

4. **Session search is carrying too much product weight**
   - Search should remain valuable for provenance and recall.
   - It should not remain the primary abstraction for active support, next-step selection, or structured learning.

The result is a system that can remember conversations, but does not yet maintain a compact operational model of what the user is doing, what broad life area it belongs to, or what typed evidence should feed later learning.

---

## 2. Goals

1. Make **life domains** and **operational arcs** first-class durable memory objects.
2. Keep **projects, tasks, blockers, decisions, and open loops** first-class by representing them inside or alongside operational arcs.
3. Add **typed interaction episodes** as the core evidence unit between raw archive and later support learning.
4. Add **explicit evidence refs** so later pattern claims and calibration claims can point back to the record.
5. Add **GlobalSituation** and **ArcSituation** as derived, refreshable situation snapshots.
6. Keep the **raw session archive and search** as provenance and recall infrastructure rather than the main runtime abstraction.
7. Improve Alfred's ability to resume active work, blocked work, pending decisions, and unresolved loops without requiring a recap.
8. Keep the memory substrate general-purpose across project support, executive-function support, decision support, review, identity reflection, and direction reflection.
9. Establish the foundation that PRDs #168 and #169 will use for behavior compilation, support learning, and reflection.
10. Treat documentation and managed prompt/template updates as part of the feature so the memory model is explained consistently.

---

## 3. Non-Goals

- Implementing the full support-profile adaptation rules.
- Defining the full relational/support-dimension registries.
- Building review-card UX or weekly reflection flows.
- Replacing the archive or deleting session search.
- Building a full task-management product with arbitrary PM features.
- Letting reflective themes silently become durable identity truth.
- Treating a chat session as the main semantic truth of what support happened.

---

## 4. Proposed Solution

### 4.1 Memory layers covered by this PRD

This PRD should establish the continuity and evidence foundation for the relational support system.

It covers six layers:

1. **Transcript sessions**
   - raw user-visible conversations, tool outcomes, timestamps, titles, and transcript refs
   - retained for provenance, replay, debugging, and search

2. **Episode evidence**
   - typed slices of support activity with one dominant need and one dominant context
   - becomes the primary unit for downstream learning

3. **Evidence refs**
   - explicit pointers from episodes, arcs, and patterns back to the underlying record

4. **Life domains**
   - durable broad areas like work, health, relationships, and direction
   - provide a stable lens that outlives any single project or session

5. **Operational arcs**
   - resumable continuity threads such as projects, decision threads, admin pushes, recovery pushes, research threads, and recurring work streams
   - become the main operational continuity object Alfred resumes across sessions

6. **Derived situation objects**
   - `GlobalSituation` and `ArcSituation`
   - compact runtime snapshots built from operational state and recent evidence

Later PRDs add support profiles, behavior compilation, pattern generation, review cards, and correction controls on top of this foundation.

### 4.2 Demote the session to transcript/provenance status

A `TranscriptSession` should remain useful, but its role changes.

It should own:
- transcript refs
- title
- timestamps
- UI grouping
- provenance metadata
- optional linked arc IDs for browsing convenience

It should **not** be the main runtime abstraction for:
- continuity
- learning
- pattern generation
- next-step selection
- support-style decisions

Important rules:
- a session may link to zero, one, or many operational arcs
- a session may contain many episodes
- a fresh session resets transcript clutter and local assumptions, not continuity
- a thread may continue across sessions

### 4.3 Add life domains and operational arcs

The operational substrate should distinguish between broad life area and resumable thread.

#### Life domains
Recommended v1 domains:
- `work`
- `health`
- `relationships`
- `direction`

Each domain should support at minimum:
- stable ID
- name
- status
- salience
- linked pattern IDs
- timestamps
- derived linked arc IDs via operational arcs that point to the domain

#### Operational arcs
An `OperationalArc` should represent a resumable support target.

Recommended v1 arc kinds:
- `project`
- `decision_thread`
- `admin_thread`
- `research_thread`
- `recovery_push`
- `recurring_stream`

Each arc should support at minimum:
- stable ID
- title
- kind
- primary domain
- status (`tentative`, `active`, `dormant`, `archived`)
- salience
- links to task/open-loop/blocker/decision state
- recent activity timestamps
- evidence refs

Projects remain first-class here by being a primary arc kind, not by being flattened into generic themes.

### 4.4 Keep projects, tasks, blockers, decisions, and open loops first-class

Alfred should maintain a durable operational model with explicit objects for:
- **projects** — represented as `OperationalArc(kind=project)`
- **tasks** — concrete actionable items attached to an arc
- **blockers** — things currently impeding progress or clarity
- **open loops** — unresolved commitments, waits, or return threads
- **decisions** — unresolved or active choice points attached to an arc or domain

Minimum v1 expectations:
- stable IDs
- relationship links
- status
- next step or unresolved state
- timestamps
- evidence refs back to sessions or episodes

Example composed arc view (assembled from the persisted arc plus linked work-state records):

```json
{
  "arc_id": "webui_cleanup",
  "title": "Web UI cleanup",
  "kind": "project",
  "primary_domain_id": "work",
  "status": "active",
  "salience": 0.94,
  "blockers": ["app_structure_ambiguity"],
  "open_loops": ["pick_bootstrap_boundary"],
  "tasks": ["split_bootstrap_flow"],
  "decisions": ["where_runtime_should_boot"],
  "evidence_ref_ids": ["ev_441", "ev_442"]
}
```

Example open-loop record:

```json
{
  "open_loop_id": "commit_to_direction_q2",
  "arc_id": "startup_direction",
  "title": "Choose whether to keep pursuing the startup path",
  "status": "pending_review",
  "kind": "decision_thread",
  "current_tension": "Prestige and aliveness keep pulling in different directions",
  "evidence_ref_ids": ["ev_441", "ev_442"]
}
```

### 4.5 Add typed interaction episodes

A session should be able to contain multiple typed episodes.

Each episode should represent a locally coherent support exchange with one dominant need and one dominant context.

Minimum v1 fields:
- `episode_id`
- `session_id`
- `time_range`
- `dominant_need`
- `dominant_context`
- `dominant_arc_id`
- `domain_ids`
- `subject_refs`
- `friction_signals`
- `interventions_attempted`
- `response_signals`
- `outcome_signals`
- `evidence_refs`

Example:

```json
{
  "episode_id": "ep_204",
  "session_id": "sess_812",
  "dominant_need": "activate",
  "dominant_context": "execute",
  "dominant_arc_id": "webui_cleanup",
  "domain_ids": ["work"],
  "subject_refs": ["bootstrap_entrypoint", "app_structure"],
  "friction_signals": ["ambiguity", "initiation_friction"],
  "interventions_attempted": ["narrow_next_step", "state_recap"],
  "response_signals": ["resonance", "commitment"],
  "outcome_signals": ["next_step_chosen"],
  "evidence_refs": [
    {
      "evidence_id": "ev_441",
      "episode_id": "ep_204",
      "session_id": "sess_812",
      "message_start_idx": 441,
      "message_end_idx": 446,
      "timestamp": "2026-03-30T10:14:00+00:00",
      "domain_ids": ["work"],
      "arc_ids": ["webui_cleanup"],
      "claim_type": "stated_goal",
      "confidence": 0.86
    },
    {
      "evidence_id": "ev_442",
      "episode_id": "ep_204",
      "session_id": "sess_812",
      "message_start_idx": 447,
      "message_end_idx": 447,
      "timestamp": "2026-03-30T10:16:00+00:00",
      "domain_ids": ["work"],
      "arc_ids": ["webui_cleanup"],
      "claim_type": "stated_decision",
      "confidence": 0.91
    }
  ]
}
```

The episode schema should be fixed and versioned.

### 4.6 Add explicit evidence refs

An `EvidenceRef` should be the bridge between structured support memory and the underlying record.

Minimum v1 fields:
- `evidence_id`
- `episode_id`
- `session_id`
- `message_start_idx`
- `message_end_idx` when the evidence spans multiple messages
- `excerpt` when a short quote is useful
- `timestamp`
- `domain_ids`
- `arc_ids`
- `claim_type`
- `confidence`

`excerpt` may duplicate transcript text as a snapshot convenience field for inspection and audit. Transcript sessions remain authoritative for raw message content and order.

Recommended v1 `claim_type` values:
- `stated_priority`
- `stated_goal`
- `stated_decision`
- `predicted_outcome`
- `actual_outcome`
- `blocker`
- `value_signal`
- `contradiction`
- `support_preference_signal`

This makes later reflection and calibration inspectable instead of purely narrative.

### 4.7 Add derived situation objects

The runtime should not recompute all continuity from scratch on every turn.

It should maintain derived situation objects.

#### GlobalSituation
Broad answer to:
- what is active overall?
- what is blocked?
- what is unresolved?
- what is drifting?

Recommended fields:
- active domains
- top arcs
- unresolved decisions
- top blockers
- drift risks
- current tensions
- computed_at
- confidence
- staleness
- refresh_reason

#### ArcSituation
Scoped answer to:
- what is true about this arc right now?
- what changed recently?
- what is blocked?
- what is the likely next move?

Recommended fields:
- arc_id
- current_state
- recent_progress
- blockers
- next_moves
- linked_pattern_ids
- computed_at
- confidence
- staleness
- refresh_reason

These objects are derived and refreshable, not the deepest source of truth.

### 4.8 Retrieval should prioritize operational state over archive recall

When Alfred is helping the user act, decide, review, or resume, runtime retrieval should prefer:
1. relevant life-domain and operational-arc state
2. current `ArcSituation` or `GlobalSituation` when fresh enough
3. recent episodes tied to that state
4. archive/search hits only when evidence or history is needed

That changes the main question from:
- "what did we talk about?"

to:
- "what is active, what is unresolved, what is blocked, and what is the next move?"

### 4.9 Session-start and resume contract

The memory foundation should support this session-start behavior:

1. create a new `TranscriptSession`
2. infer whether the opening message strongly matches an existing `OperationalArc`
3. if yes, load the arc and refresh `ArcSituation` when stale
4. if not, optionally refresh `GlobalSituation` when broad orientation is likely useful
5. if the topic is clearly new, create a tentative `OperationalArc` silently
6. if Alfred resumes an existing arc across sessions, he should be able to say so explicitly

That means the memory layer must support fresh sessions without forcing Alfred to lose continuity.

### 4.10 Keep the substrate general-purpose

The memory substrate should support all of Alfred's general support contexts, not just execution-heavy use cases.

Examples:
- coding work
- life admin
- research threads
- collaboration follow-ups
- pending decisions
- identity and direction discussions that need evidence and return points
- executive-function recovery after drift or interruption

The substrate should not require a diagnosis-specific mode to be useful.

### 4.11 Migration and coexistence

The current memory system should not be rewritten all at once.

Recommended rollout:
1. keep archive and search intact
2. add typed episodes and evidence refs
3. add life domains and operational arcs
4. add derived `GlobalSituation` and `ArcSituation`
5. update runtime retrieval to prefer operational continuity over raw archive recall
6. keep archive search as provenance and fallback

---

## 5. User Experience Requirements

Users should experience Alfred as a system that:
- knows their active work and open loops without asking for a recap every time
- can distinguish between a project, a task, a blocked loop, and a pending decision
- can resume where they left off even when the prior conversation mixed multiple support contexts
- can keep continuity across fresh sessions without dragging all transcript clutter forward
- can explain where a remembered work item or unresolved loop came from
- can orient broadly across domains when the user feels lost

Examples of expected behavior:
- "What am I actively working on right now?"
- "What's blocked?"
- "What decisions are still open?"
- "What's the next step on taxes?"
- "What threads from last week still need attention?"
- "I'm resuming the Web UI cleanup thread. Last known state: bootstrap cleanup is active and the main open question is app structure."

---

## 6. Success Criteria

- [ ] Alfred stores transcript sessions as provenance objects without relying on them as the sole continuity abstraction.
- [x] Alfred stores life domains and operational arcs as first-class durable memory objects.
- [x] Alfred stores projects, tasks, blockers, decisions, and open loops as first-class operational state.
- [x] Alfred stores typed interaction episodes as a versioned evidence layer.
- [x] Alfred stores explicit evidence refs that connect structured state back to the record.
- [ ] Alfred can maintain and refresh `GlobalSituation` and `ArcSituation` snapshots.
- [ ] Operational retrieval prefers domain/arc state and relevant episodes over raw archive hits.
- [ ] Session search remains available for provenance and recall flows.
- [ ] Alfred can answer active-work and unresolved-loop questions without relying only on session search.
- [ ] The implementation keeps one clear source of truth for operational support state.

---

## 7. Milestones

### Milestone 1: Define the support-memory foundation contract
Document the layer responsibilities for transcript sessions, episodes, evidence refs, life domains, operational arcs, and derived situations.

Validation: architecture/docs and tests agree on the role of each layer.

### Milestone 2: Add typed interaction episodes and evidence refs
Implement fixed schemas and generate stable episode/evidence records from session evidence.

Validation: targeted tests prove mixed-context session inputs can yield stable, versioned episode and evidence records.

### Milestone 3: Add life domains and operational arcs
Implement durable storage and relationships for broad domains plus resumable operational continuity.

Validation: targeted tests prove Alfred can create, update, and read domain/arc state independently of raw session search.

### Milestone 4: Add project/task/open-loop operational state
Implement durable project, task, blocker, decision, and open-loop storage linked to arcs and evidence.

Validation: targeted tests prove Alfred can create, update, and read operational work state independently of raw session search.

### Milestone 5: Add derived situation objects and session-start retrieval
Implement `GlobalSituation`, `ArcSituation`, freshness metadata, and retrieval behavior that supports resume/orient flows.

Validation: targeted tests prove Alfred can build fresh-session resume and orientation context from structured state first.

### Milestone 6: Regression coverage, documentation, and prompt/template updates
Add or update tests, docs, and managed prompt/template content for the support-memory foundation and its retrieval contract.

Validation: relevant Python validation passes, memory architecture docs reflect the new runtime model, and managed prompt/template content explains operational-first retrieval consistently.

---

## 8. Likely File Changes

```text
src/alfred/memory/...                  # domain, arc, task, episode, and evidence storage
src/alfred/context.py                  # retrieval priority updates
src/alfred/session.py                  # episode extraction and synthesis integration
src/alfred/orchestration/...           # situation refresh / session-start loading if introduced
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
| The work model turns into a full task manager | Medium | keep v1 focused on domains, operational arcs, tasks, open loops, and next-step state |
| Session semantics remain overloaded in implementation even if docs improve | High | encode and test the separation between transcript sessions, episodes, and arcs |
| Duplicate truths emerge between archive, episodes, situations, and operational objects | High | make domains/arcs/tasks the operational source of truth and keep evidence refs explicit |
| Episode extraction becomes too freeform | Medium | use a fixed, versioned episode schema |
| Runtime retrieval still overuses archive recall | Medium | encode and test operational-first retrieval order |
| Derived situations become stale and misleading | Medium | add freshness metadata plus targeted refresh rules |
| Reflective threads have nowhere to live in the operational model | Medium | allow decisions and open loops to represent reflective return threads without collapsing themes into arcs |

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
- transcript sessions versus episodes versus arcs
- life-domain and operational-arc roles
- operational memory architecture
- evidence-ref and situation-object roles
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
| 2026-03-30 | Keep raw transcript sessions and search | They remain valuable for provenance, recall, and evidence lookup |
| 2026-03-30 | Demote the session from main semantic primitive to transcript/provenance primitive | Fresh chats should be allowed without losing continuity |
| 2026-03-30 | Use typed interaction episodes as the main evidence unit | Support learning needs finer structure than one session blob |
| 2026-03-30 | Add life domains and operational arcs as first-class memory objects | Alfred needs broad context plus resumable continuity, not just recall |
| 2026-03-30 | Keep projects, tasks, and open loops first-class inside the operational model | Alfred needs operational state, not just recall |
| 2026-03-30 | Add explicit evidence refs | Reflection and calibration need inspectable grounding |
| 2026-03-30 | Treat `EvidenceRef.excerpt` as a snapshot convenience field, not the transcript source of truth | Keeps transcript sessions authoritative for raw message content and order while preserving inspectable promoted evidence |
| 2026-03-30 | Derive domain-to-arc linkage from operational arcs instead of storing duplicate linked arc IDs on domains | Keeps one authority for arc membership and reduces drift between related records |
| 2026-03-30 | Maintain derived `GlobalSituation` and `ArcSituation` objects with freshness metadata | Runtime needs compact, refreshable situation views rather than constant full recomputation |
| 2026-03-30 | Demote session search from product abstraction to internal primitive | Search alone is not a strong runtime model for active support |
