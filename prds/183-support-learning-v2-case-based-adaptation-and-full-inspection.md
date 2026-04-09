# PRD: Support Learning V2 - Case-Based Adaptation and Full Inspection

**GitHub Issue**: [#183](https://github.com/jeremysball/alfred/issues/183)  
**Priority**: High  
**Status**: In Progress  
**Created**: 2026-04-07  
**Author**: Agent

---

## 1. Problem Statement

Alfred's current support-learning runtime is promising, but the live learning model is still too thin, too conservative, and too opaque.

Today, Alfred mostly learns from per-turn `LearningSituation` records. Those records are created too early, before the system has enough outcome evidence to know whether the move actually helped. The result is a learning layer that stores some useful state, but under-learns from the richer operational reality Alfred already tracks.

Seven problems matter now:

1. **The primary learning unit is too turn-centric**
   - A single turn is not the right unit for most support learning.
   - What matters is often not only what Alfred said, but what happened after: whether clarity increased, whether a blocker narrowed, whether a task started, whether a decision resolved, or whether an open loop reopened.

2. **Operational state is first-class in storage but second-class in learning**
   - Alfred already stores blockers, tasks, decisions, open loops, arcs, and related support context.
   - Those objects influence orientation and resume behavior, but they are not yet first-class promotion inputs for adaptive learning.

3. **Current learning records are too thin to drive promotion well**
   - Recent runtime `LearningSituation` rows often lack rich outcome fields such as user-response signals, outcome signals, and structured evidence refs.
   - That leaves the promotion engine with too little grounded evidence.

4. **The system is too conservative about what it learns and when it activates it**
   - Alfred should be allowed to learn broadly from support outcomes and work-state transitions.
   - The current runtime is too hesitant to promote or apply new learned values.

5. **Visibility is incomplete**
   - `/context` should show effective runtime values clearly.
   - `/support` should be able to show the full learned state, including active, inactive, candidate, shadow, confirmed, rejected, and retired values or patterns.
   - Today that inspection surface is incomplete and does not expose the full value ledger cleanly.

6. **Status semantics are too blurry**
   - The current system can blur the line between “observed” and “active.”
   - The user should be able to tell which values are merely proposed, which are active, which are confirmed, and why.

7. **The runtime contract around persistence needs to be stricter and clearer**
   - Support-learning persistence must use real session and message references.
   - Alfred should never fabricate placeholders such as `session_id="runtime"` to satisfy a write path.

The result is a system that can adapt a little, but not yet in the more ambitious, legible, user-correctable way Alfred needs.

---

## 2. Goals

1. Replace turn-centric learning with a cleaner **attempt → observation → case** model.
2. Make blockers, tasks, decisions, open loops, and arc transitions first-class learning evidence.
3. Let Alfred learn from a broader set of signals and with less conservative thresholds.
4. Allow both support values and relational values to auto-activate when evidence is strong enough.
5. Make aggressive learning safe through visibility, provenance, and correction rather than through excessive hesitation.
6. Make `/context` a truthful view of **effective runtime state**.
7. Make `/support` a truthful view of the **full learned ledger**, not only active state.
8. Preserve scope-aware learning across `arc`, `context`, and `global`, while allowing cross-arc generalization when evidence supports it.
9. Keep one clean runtime path rather than running v1 and v2 learning systems in parallel.
10. Treat docs, prompts, and inspection payloads as part of the feature contract.
11. Keep curated memory as a separate explicit memory lane rather than using support learning as a generic replacement for remembered facts, preferences, and durable decisions.

---

## 3. Non-Goals

- Preserving backward compatibility for v1 support-learning records when that conflicts with a cleaner v2 model.
- Building an unbounded introspection browser for every internal artifact Alfred ever emits.
- Turning Alfred into a freeform therapy or personality-engine product.
- Hiding aggressive learning behind silent, unverifiable automation.
- Keeping both `LearningSituation`-centric and case-centric learning pipelines alive long-term.
- Making manual confirmation mandatory for every learned value.
- Replacing curated memory with support learning or treating remembered facts as the same artifact type as support values, patterns, observations, or cases.

---

## 4. Proposed Solution

### 4.1 Replace `LearningSituation` as the primary learning unit

V2 should stop treating one turn as the core adaptive-learning unit.

Instead, Alfred should use three explicit stages:

1. **`SupportAttempt`**
   - what Alfred tried on a specific reply
   - created at reply time

2. **`OutcomeObservation`**
   - what happened after the reply
   - created whenever new conversational, operational, explicit-feedback, or timeout evidence appears

3. **`LearningCase`**
   - the completed learning unit
   - derived from one `SupportAttempt` plus its linked `OutcomeObservation` records and relevant operational transitions

The case, not the raw turn, becomes the unit used for:
- promotion
- demotion
- pattern generation
- evidence inspection
- runtime explanation

### 4.1A Boundary with curated memory

Support learning and curated memory may both preserve useful things, but they should remain different lanes.

Rule:
- curated memory stores explicit reusable facts, preferences, instructions, and durable decisions
- support learning stores adaptive support and relational evidence, values, patterns, observations, and cases

That means:
- remembered facts do not automatically become support-profile values
- support observations do not automatically become curated memories
- support learning may use remembered facts as supporting context, but it does not replace curated memory as the durable reusable-fact lane

Related sibling PRDs:
- **PRD #184** owns bounded semantic adjudication during runtime
- **PRD #191** owns curated-memory auto-injection, liberalized `remember` capture, and curated-memory boundary rules

### 4.2 Schema contract

V2 should introduce or rework the support-learning schema around the following primary entities.

#### A. `support_attempts`

Purpose:
- durable record of what Alfred actually tried on one reply

Required fields:
- `attempt_id`
- `session_id`
- `user_message_id`
- `assistant_message_id`
- `created_at`
- `need`
- `response_mode`
- `active_arc_id`
- `active_domain_ids`
- `subject_refs`
- `effective_support_values`
- `effective_relational_values`
- `intervention_family`
- `intervention_refs`
- `prompt_contract_summary`
- `operational_snapshot_ref`

Contract:
- must use a real persisted `session_id` when persistence is enabled
- should use real message ids when available
- if required references are unavailable, Alfred should skip or defer persistence rather than write fake placeholder ids

#### B. `support_outcome_observations`

Purpose:
- append-only event log of what happened after an attempt

Required fields:
- `observation_id`
- `attempt_id`
- `observed_at`
- `source_type`
  - `next_user_turn`
  - `work_state_transition`
  - `explicit_feedback`
  - `timeout`
  - `manual_review`
  - `system_inference`
- `signals`
- `signal_polarity`
- `signal_strength`
- `evidence_refs`
- `operational_delta_refs`
- `notes`

Example signals:
- `clarity`
- `confusion`
- `resonance`
- `resistance`
- `commitment`
- `next_step_chosen`
- `resume_ready`
- `comparison_started`
- `blocker_created`
- `blocker_reopened`
- `blocker_narrowed`
- `blocker_resolved`
- `task_started`
- `task_completed`
- `task_abandoned`
- `decision_narrowed`
- `decision_made`
- `decision_reopened`
- `open_loop_closed`
- `open_loop_reopened`
- `arc_resumed`
- `arc_stalled`
- `arc_completed`

#### C. `support_learning_cases`

Purpose:
- completed, inspectable, promotable unit of support learning

Required fields:
- `case_id`
- `attempt_id`
- `status`
  - `open`
  - `complete`
  - `insufficient_evidence`
  - `superseded`
- `scope_type`
- `scope_id`
- `created_at`
- `finalized_at`
- `aggregate_signals`
- `positive_evidence_count`
- `negative_evidence_count`
- `contradiction_count`
- `conversation_score`
- `operational_score`
- `overall_score`
- `promotion_eligibility`
- `evidence_refs`
- `summary`

Contract:
- only `complete` cases with sufficient evidence may drive promotion or demotion
- cases remain inspectable even when they do not qualify for promotion

#### D. `support_profile_values`

V2 should keep a durable value ledger, but make status semantics explicit.

Required statuses:
- `shadow` — learned but inactive
- `active_auto` — auto-activated by runtime policy
- `confirmed` — explicitly trusted or promoted into stable use
- `rejected`
- `retired`

Required fields:
- `value_id`
- `registry` (`support` or `relational`)
- `dimension`
- `scope_type`
- `scope_id`
- `value`
- `status`
- `source`
- `confidence`
- `evidence_count`
- `contradiction_count`
- `last_case_id`
- `created_at`
- `updated_at`
- `why`

Runtime contract:
- `/support values` must be able to show all statuses
- runtime resolution may load `active_auto` and `confirmed`
- runtime must not silently load `shadow`

#### E. `support_patterns`

Patterns should remain first-class, but with explicit status and provenance.

Required statuses:
- `candidate`
- `active_auto`
- `confirmed`
- `rejected`
- `retired`

Required fields:
- `pattern_id`
- `kind`
- `scope_type`
- `scope_id`
- `status`
- `claim`
- `evidence_count`
- `contradiction_count`
- `confidence`
- `source_case_ids`
- `created_at`
- `updated_at`
- `why`

Kinds should continue to include at least:
- `recurring_blocker`
- `support_preference`
- `identity_theme`
- `direction_theme`
- `calibration_gap`

V2 should allow some pattern kinds to become `active_auto` when the product rules allow it.

#### F. `support_profile_update_events`

Purpose:
- durable, user-inspectable log of why a value or pattern changed

Required fields:
- `event_id`
- `entity_type`
- `entity_id`
- `registry`
- `dimension_or_kind`
- `scope_type`
- `scope_id`
- `old_status`
- `new_status`
- `old_value`
- `new_value`
- `trigger_case_ids`
- `reason`
- `confidence`
- `created_at`

### 4.3 Runtime contract

V2 runtime should follow a strict staged contract.

#### A. Reply-time contract

Before Alfred sends a reply, runtime should:

1. resolve current need, response mode, subjects, arc, and domain context
2. load active values and active patterns from the new ledger
3. compile the effective support contract
4. create a `SupportAttempt`
5. generate the reply using the compiled contract

Required reply-time rule:
- attempt persistence must use the real resolved session id and real message refs when persistence is enabled

#### B. Observation-time contract

After the reply, runtime should append `OutcomeObservation` rows whenever evidence appears.

Evidence sources include:
- the next user turn
- explicit feedback
- blocker/task/decision/open-loop changes
- arc state changes
- timeout or no-progress windows
- manual support review actions

#### C. Case-finalization contract

Runtime should finalize a `LearningCase` when there is enough evidence to score whether the attempt helped.

Finalization rules should consider:
- at least one conversational or explicit-feedback observation
- and/or at least one operational transition
- evidence quality, not just count
- contradiction rate
- recency window

#### D. Promotion contract

Only finalized cases may drive adaptation.

Promotion and demotion should run through one bounded engine that:
- evaluates scoped evidence
- tracks contradictions
- updates value or pattern statuses
- writes `support_profile_update_events`
- makes those changes inspectable immediately

### 4.4 Learn from broader evidence and lower thresholds

V2 should be intentionally less conservative.

Alfred should learn from:
- conversational outcomes
- work-state transitions
- explicit user corrections
- repeated reopenings and stalls
- repeated successful progress patterns
- scoped recurrence across arcs, contexts, and the broader runtime

Default threshold direction:
- **arc-local values**: promote after roughly 2-3 sufficiently positive complete cases
- **cross-arc / context / global values**: promote after roughly 4-6 sufficiently positive complete cases
- negative evidence may demote or retire active values later

These thresholds should be configurable and easy to inspect, but the product default should tolerate some overzealousness because the user can interrogate and change the system.

### 4.5 Auto-activation policy

V2 should allow more aggressive auto-activation than v1.

#### Support values
Support values may auto-activate aggressively when the evidence threshold is met.

Representative dimensions:
- `planning_granularity`
- `option_bandwidth`
- `pacing`
- `proactivity_level`
- `accountability_style`
- `recovery_style`
- `recommendation_forcefulness`
- `reflection_depth`

#### Relational values
Relational values may also auto-activate when evidence is strong enough.

Boundary note:
- this PRD owns the shared ledger, status, promotion, activation, and inspection rules for relational values
- it does **not** own the product meaning of relational dimensions or how they compile into live stance behavior
- PRD #192 owns the relational runtime architecture, and PRD #193 owns the product semantics and compiler contract for dimensions such as `candor`, `challenge`, and `warmth`
- the list below is illustrative and should stay generic unless a child relational PRD explicitly owns the behavioral meaning

Representative dimensions:
- `candor`
- `challenge`
- `authority`
- `companionship`
- `warmth`
- `emotional_attunement`
- `analytical_depth`
- `momentum_pressure`

Because this is intentionally more aggressive, the safety boundary moves from “do not learn” to “learn visibly, explainably, and corrigibly.”

Required user-facing rule:
- any automatic activation, demotion, or retirement must be visible through `/context` and `/support`

### 4.6 Scope and cross-arc learning

V2 should preserve scope resolution order:
- `arc`
- `context`
- `global`

But it should allow cross-arc learning earlier than v1 when evidence is strong enough.

Rules:
- prefer the narrowest scope that explains the evidence well
- allow context- or global-scoped promotion when the same signal repeats across multiple arcs
- require a higher evidence threshold and contradiction check for broader scopes
- keep scope provenance explicit in inspection surfaces

### 4.7 Full inspection model

The user should be able to see both the active runtime state and the full learned ledger.

#### A. `/context`

`/context` should remain compact and answer:
- what is active right now?
- where did it come from?
- how confident is Alfred?

At minimum, it should show:
- active support values
- active relational values
- source
- scope
- confidence
- recent automatic changes
- active patterns

#### B. `/support values`

`/support values` should show the full value ledger.

It must be able to show:
- active values
- shadow values
- confirmed values
- rejected values
- retired values
- support and relational registries
- scope, source, confidence, evidence count, contradiction count, timestamps, and why

Representative filters:
- `/support values`
- `/support values active`
- `/support values all`
- `/support values support`
- `/support values relational`
- `/support values arc <arc_id>`

#### C. `/support cases`

`/support cases` should show completed learning cases and their inputs.

It should be able to show:
- attempt summary
- applied values
- linked observations
- linked blocker/task/decision/open-loop transitions
- aggregate signals
- scoring
- promotion impact

#### D. `/support patterns`

`/support patterns` should show candidate, active, confirmed, rejected, and retired patterns.

#### E. `/support trace <id>`

`/support trace` should show provenance for one attempt, case, value, or pattern.

It should answer:
- what was active?
- what did Alfred try?
- what happened after?
- why did the system promote, demote, activate, or reject something?

### 4.8 Correction and override model

Aggressive learning only works if the user can correct it easily.

V2 should preserve or extend support-correction flows so users can:
- confirm a value or pattern
- reject a value or pattern
- retire a value or pattern
- reset a scope
- inspect provenance before changing anything

Manual corrections should outrank auto-learned state at the same scope.

### 4.9 Migration and cutover

This PRD prefers clean replacement over compatibility glue.

Rules:
- do not keep parallel v1 and v2 learning runtimes alive after cutover
- do not backfill old `LearningSituation` rows into v2 cases by default
- preserve operational memory and normal session history
- treat current support-learning rows as disposable when they block a cleaner design
- delete dead v1 learning code after v2 is live

---

## 5. User Experience Requirements

### 5.1 Alfred should feel more adaptive, not more mysterious

When Alfred starts learning more aggressively, the user should be able to understand:
- what changed
- why it changed
- what evidence drove it
- how to change it back

### 5.2 `/context` should show active values clearly

A user inspecting `/context` should be able to see active values in a compact way.

Example shape:
- `option_bandwidth = single — source: active_auto, scope: arc:webui_cleanup, confidence: 0.82`
- `candor = high — source: active_auto, scope: context:execute, confidence: 0.76`

### 5.3 `/support` should expose the full ledger

A user should not have to guess whether Alfred has merely considered a value, actively uses it, rejected it, or retired it.

They should be able to inspect all of those states explicitly.

### 5.4 Learning should reflect real work movement

If Alfred's help contributed to:
- starting a task
- narrowing a blocker
- clarifying a decision
- closing an open loop
- resuming a stalled arc

that evidence should be visible in the case trace.

### 5.5 Automatic changes should be visible quickly

When a value or pattern auto-activates, demotes, or retires, the user should be able to notice that soon after the change without digging through opaque logs.

### 5.6 TUI and Web UI should agree

The same support-state story should appear across:
- TUI `/context`
- Web UI `/context`
- `/support` inspection commands
- WebSocket payloads and related docs

---

## 6. Technical Requirements

### 6.1 Persistence invariants

- Support-learning persistence must never fabricate fake session ids.
- Support-learning persistence must never rely on placeholder rows such as `session_id="runtime"`.
- When message or session references are required but missing, runtime should skip or defer the write cleanly.

### 6.2 One shared support inspection payload family

- TUI and Web UI should not assemble different support truths.
- Shared builders should produce the data that `/context` and `/support` render.
- WebSocket docs must reflect the real payload shape.

### 6.3 Learning engine inputs

The adaptation engine must accept evidence from:
- conversational signals
- explicit feedback
- operational transitions
- repeated reopenings or stalls
- manually confirmed or rejected corrections

### 6.4 Promotion and demotion engine

The engine must:
- score complete cases
- track contradictory evidence
- update statuses explicitly
- write update events
- keep scope provenance
- expose why a value or pattern changed

### 6.5 Runtime loading rules

Runtime should load:
- `active_auto`
- `confirmed`

Runtime should not load:
- `shadow`
- `rejected`
- `retired`

Equivalent rules should apply to patterns.

### 6.6 Value and pattern provenance

Each active value or pattern must be explainable through:
- source cases
- status
- scope
- confidence
- timestamps
- update events

### 6.7 Support commands

V2 should add or update commands so the runtime can inspect:
- active values
- all values
- cases
- patterns
- traces
- recent update events

### 6.8 Docs and prompt alignment

When runtime behavior changes, update:
- support-model docs
- `/context` docs
- relevant self-model or inspection docs
- managed prompts or templates if their claims about support learning change

---

## 7. Success Criteria

This PRD is successful when:

1. Alfred learns from completed cases, not only from thin turn snapshots.
2. Blockers, tasks, decisions, open loops, and arc transitions materially influence learning.
3. Support and relational values can auto-activate from evidence and become visible immediately.
4. The user can inspect all values, not only active ones.
5. The user can inspect why a value or pattern changed.
6. Runtime never writes fake session ids for support-learning persistence.
7. TUI and Web UI agree on the support state shown through `/context` and `/support`.
8. The codebase has one v2 learning path rather than parallel v1/v2 adaptation systems.

---

## 8. Milestones

- [ ] **Milestone 1: V2 learning schema and storage contract landed**  
      Add the new attempt, observation, case, value-status, pattern-status, and update-event structures with explicit persistence invariants.

- [x] **Milestone 2: Reply-time runtime writes `SupportAttempt` records with real refs**  
      Alfred persists what it tried using real session and message references and never falls back to fake runtime ids.

- [x] **Milestone 3: Outcome observation pipeline captures operational evidence**  
      Alfred records post-reply outcome observations from work-state transitions.

      Note: conversational / semantic observation extraction (explicit feedback, next-turn signals, etc.) is out-of-scope for PRD #183 and owned by **PRD #189**.

      Sub-milestones:
      - [x] **Milestone 3A:** Deterministic `work_state_transition` observations from public SQLite work-state seams, linked to the latest matching `SupportAttempt` by `active_arc_id`.

- [x] **Milestone 4: Case finalization and scoring replace turn-centric promotion logic**  
      Alfred promotes and demotes from completed `LearningCase` records instead of thin per-turn snapshots.

      Sub-milestones:
      - [x] **Milestone 4A:** Deterministic case finalization + scoring from stored `SupportAttempt` + `OutcomeObservation` bundles.
      - [x] **Milestone 4B:** Runtime cutover so promotion/adaptation reads finalized cases as the primary learning unit.
            Sub-milestones:
            - [x] **Milestone 4B.1:** Runtime value resolution prefers v2 value-ledger entries (`active_auto` / `confirmed`) over legacy v1 support-profile values.
            - [x] **Milestone 4B.2:** Remove or fully retire turn-centric bounded adaptation (`LearningSituation`) so case-derived learning is the primary driver.
            - [x] **Milestone 4B.3:** Apply v2 case-learning automatically from operational observations (work-state transitions).

- [ ] **Milestone 5: Less-conservative scoped adaptation ships for support and relational values**  
      Arc, context, and global learning work with lower thresholds, contradiction tracking, and explicit auto-activation rules.

      Sub-milestones:
      - [x] **Milestone 5A:** Case-based v2 value-ledger promotion (support + relational), exact-scope only (`arc` / `context`), persisting below-threshold evidence as `shadow` and promoting to `active_auto` when thresholds are met.
      - [ ] **Milestone 5B:** Broader scope generalization, demotion/retirement, and pattern-ledger inference (deferred).

- [ ] **Milestone 6: Full inspection surfaces ship across `/context` and `/support`**  
      Users can inspect active values, all values, patterns, cases, traces, and update events in both TUI and Web UI.

      Sub-milestones:
      - [x] **Milestone 6A.1 (Web UI-only foundation):** `/context` support inspection snapshot includes v2 `value_ledger_entries`, `value_ledger_summary`, and `recent_ledger_update_events`.
      - [x] **Milestone 6A.2 (Web UI):** Web UI renders the v2 value ledger inside `context-viewer` and the websocket protocol docs are updated.
            Sub-milestones:
            - [x] **Milestone 6A.2a (Python):** `/context` payload forwards `value_ledger_entries`, `value_ledger_summary`, and `recent_ledger_update_events` under `support_state.learned_state`.
            - [x] **Milestone 6A.2b (Docs):** websocket protocol docs describe the new v2 support learned-state fields.
            - [x] **Milestone 6A.2c (Web UI):** `context-viewer` renders the v2 value ledger and is covered by a Playwright browser test.
      - [ ] **Milestone 6B:** Full `/support` inspection surfaces + cross-surface (TUI/Web UI) parity for full-ledger inspection.

- [ ] **Milestone 7: V1 learning path is removed and docs are aligned**  
      Dead v1 learning code is deleted, and docs, tests, and payload contracts describe only the shipped v2 model.

---

## 9. Likely File Changes

### Python runtime and storage
- `src/alfred/support_policy.py`
- `src/alfred/alfred.py`
- `src/alfred/memory/support_learning.py`
- `src/alfred/memory/support_context.py`
- `src/alfred/support_reflection.py`
- `src/alfred/storage/sqlite.py`

### Inspection and interfaces
- `src/alfred/context_display.py`
- `src/alfred/interfaces/pypitui/commands/show_context.py`
- `src/alfred/interfaces/webui/server.py`
- `src/alfred/interfaces/webui/static/js/components/context-viewer.js`
- support inspection command handlers and shared payload builders

### Tests
- `tests/test_support_learning.py`
- `tests/test_support_policy.py`
- `tests/test_core_observability.py`
- `tests/test_context_display.py`
- `tests/test_context_command.py`
- `tests/webui/test_server_parity.py`
- `tests/webui/test_websocket.py`
- targeted new tests for support cases, traces, and value inspection

### Docs
- `docs/relational-support-model.md`
- `docs/self-model.md`
- `docs/websocket-protocol.md`
- `docs/how-alfred-helps.md`
- `docs/ROADMAP.md`

---

## 10. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| More aggressive learning causes bad or noisy auto-activations | High | Make every change visible, inspectable, and corrigible; track contradiction counts and allow fast demotion or retirement |
| Broader evidence inputs create messy scoring | High | Keep observation types explicit, score cases through one shared contract, and inspect full traces |
| Cross-arc learning overgeneralizes too quickly | High | Require higher thresholds and contradiction checks for broader scopes |
| Runtime complexity grows too much | Medium | Keep one shared case pipeline and delete the v1 path after cutover |
| Inspection surfaces become inconsistent across TUI and Web UI | Medium | Use shared builders and parity tests for `/context` and `/support` |
| Persistence bugs recur around session/message references | High | Require real refs, fail fast, and test public chat flows with storage enabled |

---

## 11. Validation Strategy

This PRD is architecture-first and documentation-first.

Validation for the planning pass should focus on:
- consistency with PRDs #167, #168, #169, and #179
- clear distinction between active runtime state and full learned ledger inspection
- explicit status semantics for values and patterns
- explicit persistence invariants that ban fake runtime session ids
- explicit support for broader, less-conservative learning

Implementation work from this PRD will likely touch both Python and JavaScript surfaces.

Required validation for implementation should therefore include the relevant workflows for touched files:

### Python workflow
```bash
uv run ruff check src/
uv run mypy --strict src/
uv run pytest <targeted tests for touched support-learning, storage, command, and interface surfaces>
```

### JavaScript workflow
```bash
npm run js:check
```

Additional required verification for this PRD:
- targeted persistence tests proving real session ids reach support-learning writes
- targeted tests for attempt, observation, case, and promotion behavior
- targeted `/context` and `/support` parity tests
- browser-level verification for Web UI inspection surfaces when the Web UI payload or rendering changes

---

## 12. Related PRDs

- PRD #167: Support Memory Foundation
- PRD #168: Adaptive Support Profile and Intervention Learning
- PRD #169: Reflection Reviews and Support Controls
- PRD #179: Relational Support Operating Model
- PRD #192: Relational Runtime Semantics and Stance Adjudication
- PRD #193: Product-Owned Relational Semantics and Compiler Contract
- PRD #165: Selective Tool Outcomes and Context Viewer Fixes

---

## 13. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-07 | Replace turn-centric support learning with `SupportAttempt` → `OutcomeObservation` → `LearningCase` | The current `LearningSituation` model is too early and too thin to capture real outcomes well |
| 2026-04-07 | Alfred should learn from blockers, tasks, decisions, open loops, and arc transitions directly | Operational state should be first-class learning evidence, not only background context |
| 2026-04-07 | Alfred should be less conservative about what it learns and when it activates it | The user prefers a more adaptive and somewhat overzealous system that can be inspected and corrected later |
| 2026-04-07 | Both support values and relational values may auto-activate when evidence is strong enough | The user explicitly prefers a less conservative adaptation model, including relational stance changes |
| 2026-04-09 | PRD #183 owns relational value ledger and activation semantics, not relational dimension meaning or live stance behavior | This keeps the shared learning architecture in #183 while deferring relational runtime semantics to PRDs #192 and #193 |
| 2026-04-09 | Work-state transition observations should trigger case finalization + v2 ledger updates in the same SQLite transaction | This makes the v2 learning pipeline run end-to-end deterministically from operational evidence without cross-connection visibility bugs |
| 2026-04-07 | Visibility and correction are the main safety boundary for aggressive learning | The user wants Alfred to learn more, provided the system can be interrogated and changed |
| 2026-04-07 | `/context` should show effective runtime state, while `/support` must be able to show all values and traces | Compact active-state inspection and full-ledger inspection serve different jobs |
| 2026-04-07 | Cross-arc learning is allowed, with higher thresholds than arc-local promotion | Generalization is desired, but should still be scope-aware |
| 2026-04-07 | Do not preserve backward compatibility for v1 learning data if it blocks a cleaner v2 runtime | The repo is in beta, and the current learning rows are too thin to justify migration-heavy preservation |
| 2026-04-07 | Support-learning persistence must use real session ids and should skip or defer writes rather than invent placeholders | The runtime contract must stay storage-safe and explainable |
| 2026-04-07 | Milestone 3 should start with deterministic `work_state_transition` observations before conversational or semantic extraction | This keeps the first observation lane inside PRD #183 and defers sibling semantic PRDs until later milestones |
| 2026-04-07 | Milestone 4 should start by finalizing deterministic cases from stored attempt-plus-observation bundles | This defines the case-scoring seam before replacing the older turn-centric adaptation path in runtime |
| 2026-04-07 | Milestone 5 should start with value-ledger promotion before pattern inference, and below-threshold evidence should persist as `shadow` rows | This keeps the first case-based promotion slice deterministic, inspectable, and narrow enough to ship before pattern heuristics |
| 2026-04-07 | Milestone 5A should stay exact-scope only, with arc-local promotion earlier than context promotion | This preserves the product preference for aggressive learning while keeping broader generalization and cross-arc rollout for later slices |
