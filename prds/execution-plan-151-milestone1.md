# Execution Plan: PRD #151 - Milestone 1: Streaming Interaction Contract

## Overview
Define the message vocabulary, session mutation primitives, and composer-state contract that later milestones will use for streaming, cancel, and edit behavior. This phase locks down the names, payloads, and local UI state transitions for Enter, Shift+Enter, Esc, and edit mode. It stops before the later milestones that add runtime cancel/edit plumbing, mobile stop controls, and markdown layout fixes.

---

## Milestone 1: Streaming Interaction Contract

### Component: Protocol vocabulary and docs

- [x] **Test**: `test_chat_cancel_chat_edit_and_chat_cancelled_protocol_shapes()` - verify the new client/server message shapes validate round-trip in `tests/webui/test_protocol.py` and `tests/webui/test_validation.py`
- [x] **Implement**: add `chat.cancel`, `chat.edit`, and `chat.cancelled` models to `src/alfred/interfaces/webui/protocol.py` and `src/alfred/interfaces/webui/validation.py`, wire them into `validate_client_message()`, and document the contract in `docs/websocket-protocol.md`
- [x] **Run**: `uv run pytest tests/webui/test_protocol.py tests/webui/test_validation.py -v`

### Component: Session mutation primitives

- [x] **Test**: `test_session_manager_replaces_and_truncates_message_history_atomically()` - verify a session can update one message in place, truncate everything after it, and resave without stale embeddings or orphaned history rows
- [x] **Implement**: add narrow mutation helpers to `src/alfred/session.py`, replace stale message embeddings during `src/alfred/storage/sqlite.py::save_session()`, and keep the in-memory/session metadata in sync after a truncate or replacement
- [x] **Run**: `uv run pytest tests/test_session.py tests/storage/test_message_embeddings.py -v`

### Component: Web UI composer contract hooks

- [ ] **Test**: `test_chat_message_component_exposes_edit_state_and_websocket_client_helpers()` - verify `chat-message.js`, `websocket-client.js`, `main.js`, and `index.html` expose the new edit/cancel contract surface and versioned assets
- [ ] **Implement**: add the `editable` / composer-state hooks to `src/alfred/interfaces/webui/static/js/components/chat-message.js`, `src/alfred/interfaces/webui/static/js/websocket-client.js`, `src/alfred/interfaces/webui/static/js/main.js`, and bump the cache-buster references in `src/alfred/interfaces/webui/static/index.html`
- [ ] **Run**: `uv run pytest tests/webui/test_frontend.py tests/webui/test_input.py tests/webui/test_frontend_logging.py tests/webui/test_contrast_standardization.py -v`

### Component: Browser contract coverage

- [ ] **Test**: `test_streaming_composer_keyboard_contract()` - verify the browser-level contract for idle/streaming/editing state, Enter / Shift+Enter / Esc routing, and the pencil action on the last completed user message
- [ ] **Implement**: finish the minimal browser-state plumbing in `main.js` and `chat-message.js` so the Playwright test can drive the contract against the real DOM and WebSocket client stub
- [ ] **Run**: `uv run pytest tests/webui/test_streaming_composer.py -v`

---

## Files to Modify

1. `src/alfred/interfaces/webui/protocol.py` — new streaming-control message types
2. `src/alfred/interfaces/webui/validation.py` — Pydantic validation for the new messages
3. `src/alfred/interfaces/webui/static/js/components/chat-message.js` — edit action + editable state hooks
4. `src/alfred/interfaces/webui/static/js/main.js` — composer state and keyboard routing
5. `src/alfred/interfaces/webui/static/js/websocket-client.js` — client helpers for cancel/edit messages
6. `src/alfred/interfaces/webui/static/index.html` — cache-buster updates for changed client assets
7. `src/alfred/session.py` — message truncation and in-place update helpers
8. `src/alfred/storage/sqlite.py` — resave logic that removes stale embeddings
9. `docs/websocket-protocol.md` — document the new contract
10. `tests/webui/test_protocol.py` — protocol shape coverage
11. `tests/webui/test_validation.py` — validation coverage
12. `tests/webui/test_frontend.py` — static client contract assertions
13. `tests/webui/test_input.py` — input/composer contract assertions
14. `tests/webui/test_frontend_logging.py` — asset-order and version assertions
15. `tests/webui/test_contrast_standardization.py` — main.js version assertion
16. `tests/webui/test_streaming_composer.py` — browser contract coverage
17. `tests/test_session.py` — session mutation tests
18. `tests/storage/test_message_embeddings.py` — stale embedding cleanup tests

## Commit Strategy

- `test(webui): define streaming control protocol`
- `feat(session): add atomic history mutation helpers`
- `feat(webui): add composer contract hooks`
- `test(webui): cover streaming composer contract`

## Exit Criteria for Milestone 1

- The cancel/edit message vocabulary is documented and validated
- Session history mutations are atomic and do not leave stale embeddings behind
- The web UI exposes explicit idle/streaming/editing composer hooks
- Later milestones can wire in runtime cancel/edit behavior without changing the contract again
