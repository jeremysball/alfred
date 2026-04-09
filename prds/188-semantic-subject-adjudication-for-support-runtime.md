# PRD: Semantic Subject Adjudication for Support Runtime

**Parent PRD**: [#184 Semantic Adjudication Runtime for Support Routing and Learning](./184-semantic-adjudication-runtime-for-support-routing-and-learning.md)  
**GitHub Issue**: [#188](https://github.com/jeremysball/alfred/issues/188)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-04-07  
**Author**: Agent

---

## 1. Problem Statement

Alfred currently resolves support subjects through a mix of:
- embeddings against subject prototypes
- exact alias hits
- ordered alias hits
- token-overlap scoring
- abstract cue maps
- active-scope bonus scoring

That is a hard-to-maintain score stack for a semantic reference-resolution problem.

Five problems matter now:

1. **The current logic is brittle for deictic and implied references**
   - “this,” “that,” “the thing from last week,” and similar references are not well handled by alias and token-overlap rules.

2. **Abstract subject resolution is too cue-driven**
   - Identity, direction, global orientation, and current-turn focus are not best inferred from a handful of hardcoded phrases.

3. **Concrete candidate resolution should be candidate-bound**
   - Alfred already knows the current arcs and domains it could mean.
   - The job is to choose among them, not to rely on freeform lexical tricks.

4. **Embeddings help shortlist, but not final reference judgment**
   - Similarity is useful context.
   - It is not enough as the final authority for what the user is actually referring to right now.

5. **The current scoring blend is hard to reason about**
   - Semantic similarity, alias hits, overlap bands, and scope boosts all compete in one opaque total score.

This PRD replaces that score soup with bounded subject adjudication.

---

## 2. Goals

1. Replace heuristic subject scoring with LLM adjudication over explicit candidates.
2. Support both concrete subjects and abstract subject kinds.
3. Preserve stable ids and typed subject refs.
4. Keep candidate selection bounded and validated.
5. Allow embeddings to remain only as shortlist support when needed.

---

## 3. Non-Goals

- Redesigning the `SubjectKind` ontology.
- Letting the model invent new subjects or scopes.
- Removing active-scope information from the runtime.
- Replacing retrieval or search with subject adjudication.

---

## 4. Proposed Solution

### 4.1 Replace score-based subject selection with bounded adjudication

The subject adjudicator should select zero or more subject refs from a supplied candidate set.

Candidate categories:
- concrete arcs
- concrete domains
- abstract kinds:
  - `global`
  - `identity`
  - `direction`
  - `current_turn`

The output should be a bounded list of selected subject refs plus optional grounding quotes and confidence.

### 4.2 Forward structured candidate context

The prompt should receive:
- current user turn
- previous assistant reply when relevant
- currently active arc/domain ids
- candidate arcs with stable ids and compact summaries
- candidate domains with stable ids and compact summaries
- abstract candidate kinds
- any need classification already resolved upstream

This gives the model the symbolic state it needs to resolve references cleanly.

### 4.3 Keep selection bounded and validated

Required safeguards:
- selected subject refs must come from the provided candidate set
- subject count must respect a hard maximum
- quotes must be grounded if returned
- invalid output falls back to an empty subject list

### 4.4 Preserve embeddings only as optional shortlist support

If the candidate set becomes large, embeddings may still help shortlist concrete candidates before adjudication.

Required rule:
- embeddings may narrow the set
- the adjudicator makes the final bounded subject selection

---

## 5. User Experience Requirements

Users should be able to say things like:
- “Can we get back to that landlord thing?”
- “This is bigger than this one project.”
- “No, I mean the pattern in me, not the task list.”
- “I’m talking about the direction question, not the current thread.”

And Alfred should resolve the subject through the actual runtime candidate set rather than token-overlap hacks.

---

## 6. Success Criteria

- [ ] Subject resolution no longer depends on alias-hit and token-overlap scoring as the primary path.
- [ ] Concrete subjects are selected only from real supplied candidates.
- [ ] Abstract subject kinds remain bounded to the existing ontology.
- [ ] Deictic and implied references are handled through semantic adjudication.
- [ ] Invalid model output falls back safely.

---

## 7. Milestones

### Milestone 1: Define the subject-adjudication contract
Define candidate formats, output schema, and validation rules.

Validation: the contract supports bounded concrete and abstract subject selection.

### Milestone 2: Replace score-based subject selection
Use the adjudicator in the support-policy path that currently combines similarity, aliases, overlaps, and cue maps.

Validation: subject resolution flows through the adjudicated path.

### Milestone 3: Add targeted tests
Cover explicit references, deictic references, abstract redirection, over-selection, and invalid output.

Validation: tests prove candidate-bound selection and safe fallback behavior.

### Milestone 4: Align docs and observability
Document the new subject-resolution behavior and add traceable logs.

Validation: runtime and docs stay aligned.

---

## 8. Likely File Changes

```text
prds/188-semantic-subject-adjudication-for-support-runtime.md
src/alfred/support_policy.py
tests/test_support_policy.py
tests/test_core_observability.py
docs/relational-support-model.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The candidate set is too large for clean adjudication | Medium | shortlist concrete candidates before adjudication when necessary |
| The model over-selects multiple subjects | Medium | enforce hard max counts and validate the output |
| Abstract kinds become overused | Medium | keep the ontology closed and make empty selection acceptable |
| Old heuristic helpers remain as dead code | Medium | remove the score-soup path rather than keeping parallel primary logic |

---

## 10. Open Questions

1. What is the right maximum number of subjects per turn?
2. Should abstract subject selection always be available, or only when concrete candidates do not fit?
3. Which concrete candidate summaries are most helpful without bloating the prompt?
