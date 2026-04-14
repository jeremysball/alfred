# Architecture Docs

Use `docs/architecture/` for first-class architecture documents.

`docs/ARCHITECTURE.md` is the top-level architecture overview and index.
This directory holds the boundary-specific and design-specific architecture docs that the overview points to.

## What belongs here

Architecture docs are the durable source of truth for:
- system shape
- boundaries between subsystems
- runtime contracts
- integration seams
- constraints and invariants
- tradeoffs and chosen designs
- migration and rollout shape for major refactors

Use an architecture doc when the main artifact is a design decision or system boundary, not a feature delivery plan.

## What does not belong here

Do not use architecture docs as a substitute for:
- PRDs
- execution plans
- task lists
- release notes

Those artifacts serve different purposes:
- **PRD** = product intent, user-visible behavior, scope, milestones, and success criteria
- **architecture doc** = system shape, boundaries, contracts, constraints, tradeoffs, and integration seams
- **execution plan** = implementation phases, validation workflow, and task sequencing for a PRD slice

## How to use this directory

- Prefer updating an existing architecture doc when it already owns the boundary or contract
- Create a new doc when the design deserves its own durable source of truth
- Keep the filename short and stable, based on the system boundary or design topic
- Link relevant architecture docs from PRDs that implement or depend on the design
- Keep architecture docs aligned with shipped behavior, linked PRDs, execution plans, and relevant user-facing docs

## Suggested filename pattern

Use:
- `docs/architecture/[slug].md`

Examples:
- `docs/architecture/support-runtime-adjudication.md`
- `docs/architecture/webui-bootstrap-boundary.md`
- `docs/architecture/support-learning-v2.md`

## Suggested document shape

A typical architecture doc should cover:
- problem
- goals and non-goals
- current constraints
- options considered
- chosen design
- ownership boundaries and contracts
- migration or rollout plan
- validation strategy
- risks and open questions

## Relationship to PRDs

If a change needs both system design and product planning:
1. create or update the architecture doc first
2. create or update the PRD against that design
3. link the PRD back to the architecture doc

This keeps architecture rationale out of parent PRDs and keeps PRDs focused on delivery.
