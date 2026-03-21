# Execution Plan Index: PRD #143 - Cosine Similarity Migration for Memory and Session Search

## Overview

PRD #143 has been broken into multiple execution plans, one per milestone, to keep the work test-first, atomic, and independently verifiable.

## Milestone Plans

1. `prds/execution-plan-143-milestone1.md` — lock the contract with failing tests
2. `prds/execution-plan-143-milestone2.md` — add vec schema metric awareness
3. `prds/execution-plan-143-milestone3.md` — migrate memory search to the new contract
4. `prds/execution-plan-143-milestone4.md` — migrate session search to the new contract
5. `prds/execution-plan-143-milestone5.md` — add safe rebuild and startup validation
6. `prds/execution-plan-143-milestone6.md` — add Web UI regression coverage and finalize verification

## Recommended Starting Point

Start with:
- `prds/execution-plan-143-milestone1.md`

That milestone locks the expected behavior in tests before any production changes are made.

## Exit Criteria

PRD #143 is ready for implementation when milestone 1 is accepted and the first red tests are in place.
