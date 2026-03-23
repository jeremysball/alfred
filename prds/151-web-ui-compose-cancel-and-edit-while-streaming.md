# PRD: Web UI Compose, Cancel, and Edit While Streaming

**GitHub Issue**: [#151](https://github.com/jeremysball/alfred/issues/151)  
**Status**: Draft  
**Priority**: High  
**Created**: 2026-03-23

---

## 1. Problem Statement

The Web UI chat flow still treats streaming as a blocking state.

Current problems:

- The composer is disabled while Alfred responds, so users cannot type a follow-up or correction while waiting.
- There is no explicit cancel action for the active response.
- Partial assistant output stays visible when a response needs to stop.
- The last user message cannot be edited in place, so users must retype or send a new correction.
- Markdown lists in assistant messages are not consistently contained inside the message bubble, especially on mobile.
- Mobile history controls do not provide a clear stop control while streaming.

The result is a chat experience that feels slower and more brittle than it needs to be.

---

## 2. Goals

1. Keep the message composer usable while Alfred is streaming.
2. Support two distinct composer actions during streaming:
   - **Shift+Enter** queues a follow-up for after the current turn completes.
   - **Enter** steers the conversation by canceling the active response and sending the new message as soon as the turn stops.
3. Add a clear cancel path for the current response.
4. Remove partial assistant output from the UI and session history when a response is canceled.
5. Add a pencil action to the last completed user message so it can be edited in place.
6. When a user edits the last user message, remove the trailing assistant response and continue the conversation from the edited text.
7. Fix markdown list containment globally so bulleted and numbered items stay inside message bubbles on mobile and desktop.
8. Provide a mobile stop button while streaming.

---

## 3. User Experience

### 3.1 Composer while streaming

The composer remains enabled while Alfred is responding.

- Users can keep typing while the assistant is streaming.
- **Shift+Enter** means “follow up later.” It queues the message and sends it after the current assistant turn ends normally.
- **Enter** means “steer now.” It stops the current assistant turn and sends the new message once the turn has been canceled.
- The send button follows the same behavior as Enter.

### 3.2 Cancel current response

- **Esc** cancels the active assistant response.
- On mobile, a square stop button appears while streaming.
- Canceling a response removes the partial assistant bubble from the conversation.
- Cancel does not send the current composer text unless the user chose steering with Enter.

### 3.3 Edit the last user message

- The last completed user message gets a pencil action.
- The pencil appears only after the assistant has finished responding.
- Clicking the pencil opens the main composer with that user message prefilled.
- Saving the edit removes the trailing assistant response, replaces the user message content, and continues the conversation from the edited text.
- Editing is limited to the last completed user turn.

### 3.4 Markdown lists inside bubbles

- Bulleted and numbered lists render with correct indentation inside the message bubble.
- This behavior is consistent across mobile and desktop widths.
- The fix applies globally, not just to a single theme.

---

## 4. Proposed Solution

### 4.1 Frontend state model

Add explicit composer states in the Web UI:

- `idle` — no active stream
- `streaming` — assistant response is active
- `editing` — the composer is prefilled with the last user message and will replace that message on submit

The composer should no longer be disabled just because the assistant is streaming.

### 4.2 WebSocket protocol additions

Add explicit client actions for streaming control:

- `chat.cancel` — cancel the active assistant response
- `chat.edit` — update the last user message and restart the conversation from that message

Add server acknowledgements where needed:

- `chat.cancelled` — confirm that the active response was canceled and cleaned up

The existing `chat.send` path remains the normal path for fresh turns.

### 4.3 Session mutation support

The session layer needs a clean way to mutate the conversation history:

- truncate messages after a given message ID
- update the content of a message in place
- persist the resulting session state atomically

This is required for both cancel and edit flows.

### 4.4 Partial assistant cleanup

When a response is canceled:

- the in-flight assistant message is removed from the DOM
- the partial assistant message is removed from the session store
- the next turn starts from the last completed user message

### 4.5 Edit flow

When the pencil action is used:

1. Prefill the main composer with the last user message.
2. Let the user revise the text.
3. On submit, update that stored message.
4. Remove the trailing assistant response.
5. Restart the assistant turn with the edited text.

### 4.6 Mobile stop control

While streaming on mobile:

- hide the history up/down buttons
- show a square stop button instead

When streaming ends, restore the history buttons.

### 4.7 Markdown list containment

Update message bubble and markdown styles so list markers and list item text stay within the bubble width on all screen sizes.

---

## 5. Technical Scope

### Likely files

- `src/alfred/interfaces/webui/static/css/base.css`
- `src/alfred/interfaces/webui/static/index.html`
- `src/alfred/interfaces/webui/static/js/main.js`
- `src/alfred/interfaces/webui/static/js/components/chat-message.js`
- `src/alfred/interfaces/webui/server.py`
- `src/alfred/interfaces/webui/validation.py`
- `src/alfred/session.py`
- `src/alfred/alfred.py`
- `docs/websocket-protocol.md`
- `docs/ROADMAP.md`
- `tests/webui/*`

### Functional changes

- Keep the composer enabled during streaming.
- Route Enter, Shift+Enter, and Esc to distinct behaviors.
- Add cancel and edit protocol support.
- Remove partial turns cleanly from UI and storage.
- Add a pencil action to the last user message.
- Fix markdown list layout globally.
- Add mobile stop controls during streaming.

---

## 6. Milestones

### Milestone 1: Define the streaming interaction contract
Lock down the behavior for Enter, Shift+Enter, Esc, and edit mode.

Validation:
- The interaction rules are documented.
- The protocol messages are named and scoped.
- The behavior is unambiguous for desktop and mobile.

### Milestone 2: Fix message bubble list layout globally
Make bulleted and numbered lists render inside bubbles on all themes and viewports.

Validation:
- Mobile and desktop screenshots show list items contained inside the bubble.
- The fix applies to both ordered and unordered lists.

### Milestone 3: Keep the composer active during streaming
Remove the input lockout and add the two streaming composer modes.

Validation:
- The composer accepts typing while Alfred is streaming.
- Shift+Enter queues a follow-up.
- Enter steers by canceling the active response and sending the new message.

### Milestone 4: Add cancel support and clean partial-turn removal
Cancel the active response from Esc and the mobile stop button, then remove the partial assistant message from both UI and session history.

Validation:
- Cancel leaves no partial assistant bubble visible.
- The session history no longer contains the canceled partial response.
- The next message starts from the last completed user turn.

### Milestone 5: Add last-user-message editing
Add the pencil action, prefill the composer, truncate the following assistant response, and continue from the edited text.

Validation:
- The pencil is visible only on the last completed user turn.
- Editing updates the stored user message.
- The following assistant message is removed.
- The new assistant response starts from the edited text.

### Milestone 6: Add mobile streaming controls
Swap mobile history arrows for a square stop button while streaming.

Validation:
- The stop button appears only during streaming.
- History buttons return when streaming ends.
- The control is usable on a small viewport.

### Milestone 7: Add browser and protocol regression coverage
Cover the new chat flow with tests that exercise the real browser and WebSocket behavior.

Validation:
- Desktop and mobile browser tests pass.
- WebSocket tests cover cancel and edit flows.
- Session truncation and message updates are verified.

### Milestone 8: Update docs and roadmap
Document the new behavior and keep the roadmap aligned with the PRD.

Validation:
- `docs/ROADMAP.md` includes this PRD in the short-term section.
- WebSocket protocol docs mention the new cancel/edit messages.

---

## 7. Risks and Mitigations

### Risk: Cancel and edit need session mutation support
Mitigation: add narrow session-manager methods for truncation and message replacement instead of ad hoc list surgery in the Web UI.

### Risk: Steering semantics could be ambiguous
Mitigation: keep the behavior explicit: Shift+Enter queues, Enter interrupts and sends, Esc cancels only.

### Risk: Partial assistant cleanup could drift between UI and storage
Mitigation: make the server own the cleanup and persist the session mutation before acknowledging cancel or edit completion.

### Risk: List indentation may vary across themes
Mitigation: define the bubble content rules in the base stylesheet and only let themes override color, not layout.

---

## 8. Validation Strategy

Primary verification should use the browser and the real WebSocket flow.

Recommended checks:

- Mobile screenshot of ordered and unordered lists inside bubbles.
- Typing in the composer while the assistant streams.
- Esc cancel on desktop.
- Stop button cancel on mobile.
- Enter steering path while streaming.
- Shift+Enter queue path while streaming.
- Pencil edit of the last user message after the assistant finishes.
- Session history after cancel/edit to confirm the partial assistant is removed.

---

## 9. Notes

This PRD subsumes the existing Web UI UX TODOs for:

- Shift+Enter queueing
- Enter steering mode
- ESC cancel behavior

It also adds the last-message edit flow and the markdown containment fix that were reported alongside them.
