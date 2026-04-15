# PRD: Semantic Session-Start Routing for Resume and Orientation

**Architecture Doc**: [docs/architecture/semantic-runtime-engine.md](../docs/architecture/semantic-runtime-engine.md)
**Parent PRD**: [#184 Support Projection Work on the Semantic Runtime Engine](./184-semantic-adjudication-runtime-for-support-routing-and-learning.md)
**GitHub Issue**: [#186](https://github.com/jeremysball/alfred/issues/186)
**Priority**: High
**Status**: Draft
**Created**: 2026-04-07
**Author**: Agent

---

## 1. Problem Statement

Alfred currently routes fresh-session opening messages with deterministic lexical heuristics.

Today:
- `_find_strong_resume_arc_match(...)` looks for normalized arc-title substring matches
- `_is_broad_orientation_message(...)` looks for a short list of canned phrases

That creates four problems:

1. **Resume detection is too literal**
   - Users often refer to an arc indirectly, approximately, or with a nickname.
   - Arc-title substring matching misses those cases.

2. **Broad orientation detection is too phrase-bound**
   - Users can ask for re-orientation in many ways that do not match the current phrase list.

3. **Mixed or ambiguous openings are handled poorly**
   - A message can ask to resume one thread, ask what is active overall, or do neither.
   - Phrase checks do not make that pragmatic distinction well.

4. **Alfred already has better symbolic inputs than the current logic uses**
   - The runtime has resume arcs, arc snapshots, global situations, and ids.
   - The current logic does not let the model reason over those structured candidates.

This PRD applies the shared **candidate adjudication** primitive to fresh-session routing.

---

## 2. Goals

1. Replace phrase-list and substring routing with shared candidate adjudication over bounded candidates.
2. Distinguish among `resume_arc`, `broad_orientation`, and `none`.
3. Let the model choose a real candidate `arc_id` when resuming.
4. Preserve deterministic fallback and archive-search behavior.
5. Improve fresh-session routing without weakening safety.

---

## 3. Non-Goals

- Redesigning the arc model or orientation context model.
- Replacing archive search or session search.
- Letting the model invent new arc ids or create arcs during routing.
- Handling non-fresh-session support routing in this PRD.

---

## 4. Proposed Solution

### 4.1 Use the shared candidate-adjudication primitive for session start

Replace the current routing heuristics with one bounded candidate-adjudication request that returns exactly one of:
- `resume_arc`
- `broad_orientation`
- `none`

If the decision is `resume_arc`, the output may also include:
- `arc_id`
- grounded quote or excerpt
- confidence

### 4.2 Forward rich symbolic inputs

The routing prompt should receive structured inputs such as:
- opening message text
- fresh-session flag
- candidate arcs with:
  - `arc_id`
  - title
  - compact summary
  - active blocker / task hints when available
  - recent-activity hints when available
- global situation summary when relevant
- explicit candidate-set constraints

The model should reason over those candidates, not just the raw opening text.

### 4.3 Keep strict validation and fallback

Required safeguards:
- decision enum must be valid
- `arc_id` must come from the provided candidate list
- quote must be grounded if returned
- invalid output falls back to `none`
- archive search remains the fallback when structured routing returns `none`

### 4.4 Preserve current downstream behavior where appropriate

Once routed:
- `resume_arc` should still load arc resume context
- `broad_orientation` should still load orientation context
- `none` should still allow archive-search fallback behavior

This PRD changes the routing decision, not the shape of the loaded context.

---

## 5. User Experience Requirements

Users should be able to start a fresh session with messages like:
- “Can we pick back up the taxes thing?”
- “What do I actually have in flight right now?”
- “Where was I with the landlord email?”
- “I’m kind of lost. What’s active?”

And Alfred should route correctly without requiring exact canned wording.

---

## 6. Success Criteria

- [ ] Fresh-session routing no longer depends on phrase matching as the primary path.
- [ ] Alfred can distinguish resume versus broad orientation versus neither for paraphrased openings.
- [ ] When resuming, Alfred selects only real candidate arc ids.
- [ ] Invalid model output falls back safely.
- [ ] Archive search still runs when structured routing declines to resume or orient.

---

## 7. Milestones

### Milestone 1: Define the routing input and output contract
Define the bounded schema for opening-message routing.

Validation: the contract supports `resume_arc`, `broad_orientation`, and `none` plus validated `arc_id` selection.

### Milestone 2: Replace the lexical routing path
Use the adjudicator in `get_session_start_resume_context(...)` and `get_session_start_orientation_context(...)`.

Validation: the support-context entrypoint routes via the adjudicator instead of phrase heuristics.

### Milestone 3: Add targeted regression tests
Cover direct, indirect, ambiguous, and invalid-output cases.

Validation: tests prove safe fallbacks and correct candidate selection.

### Milestone 4: Align docs and observability
Document the new routing behavior and add traceable logs for accepted versus fallback outcomes.

Validation: docs and logs match runtime behavior.

---

## 8. Likely File Changes

```text
prds/186-semantic-session-start-routing-for-resume-and-orientation.md
src/alfred/memory/support_context.py
tests/test_support_policy.py
docs/relational-support-model.md
docs/how-alfred-helps.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The model over-resumes a wrong arc | High | restrict routing to explicit candidate arcs and allow `none` |
| Latency grows at session start | Medium | keep the schema narrow and candidate summaries compact |
| Archive fallback regresses | Medium | preserve the current archive-search fallback contract and test it explicitly |
| Routing becomes harder to inspect | Medium | add adjudication observability and deterministic validation logs |

---

## 10. Open Questions

1. How many candidate arcs should be shown before the prompt gets noisy?
2. Should global situation summaries always be present, or only when `broad_orientation` is plausible?
3. Should routing ever be allowed to choose more than one arc, or should that remain out of scope?
