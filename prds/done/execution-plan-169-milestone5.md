# Execution Plan: PRD #169 - Milestone 5 Review Generation

## Overview
Generate bounded weekly and on-demand reviews from durable patterns plus recent broad support/relational changes.

## Current Repo Constraints
- Review cards are derived from durable patterns, not a second truth layer.
- Reviews must stay bounded to 1-3 cards and should surface broader changes without turning into essays.
- The existing Web UI command channel can deliver review output without introducing a new transport shape.

## Success Signal
- Alfred can generate on-demand and weekly reviews with 1-3 typed cards, evidence-backed next actions, and recent broad changes.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/alfred/support_reflection.py src/alfred/alfred.py src/alfred/interfaces/webui/server.py src/alfred/interfaces/webui/contracts.py tests/test_support_reflection.py tests/webui/test_reflection_commands.py tests/webui/fakes.py`
- **Typing:** `uv run mypy --strict src/alfred/support_reflection.py src/alfred/alfred.py src/alfred/interfaces/webui/server.py src/alfred/interfaces/webui/contracts.py`
- **Targeted tests:** `uv run pytest --no-cov -p no:cacheprovider tests/test_support_reflection.py tests/webui/test_reflection_commands.py -q`

---

## Phase 1: Review builder

- [x] Test: `test_support_reflection_runtime_builds_bounded_on_demand_and_weekly_reviews()` - verify the runtime builds bounded typed reviews and includes recent broad changes.
- [x] Implement: add the bounded review report builder and text renderer in `src/alfred/support_reflection.py`.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_support_reflection_runtime_builds_bounded_on_demand_and_weekly_reviews -v`

## Phase 2: User-facing command

- [x] Test: `test_review_week_command_renders_weekly_review_output()` - verify `/review week` exposes the weekly review surface through the assistant-message websocket flow.
- [x] Implement: add the `/review` Web UI command handler plus Alfred wrapper method.
- [x] Run: `uv run pytest tests/webui/test_reflection_commands.py::test_review_week_command_renders_weekly_review_output -v`
