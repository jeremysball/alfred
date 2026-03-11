# PRD: Fix Telegram Streaming

**Issue**: #58
**Status**: Planning
**Priority**: High
**Created**: 2026-02-18
**Parent PRD**: #48 (Alfred v1.0 Vision)

---

## Problem Statement

Streaming responses fail in the Telegram interface. The bot sends an initial "Thinking..." message but users report that streaming updates are not working. The exact symptom needs investigation — it could be:
- Message never updates from "Thinking..."
- Message only updates at the end (no true streaming)
- Updates are sporadic or delayed
- Errors are occurring silently

**Current State**: Code review shows the Telegram interface implements streaming logic, but the actual behavior in production is not working as expected.

---

## Investigation Plan

### M1: Reproduce and Diagnose

**Goal**: Determine the exact failure mode.

**Steps**:
1. Run Telegram bot locally with debug logging
2. Send a message that generates a multi-chunk response
3. Observe behavior:
   - Does the message update at all?
   - Are updates received in real-time or batched?
   - Are there exceptions in logs?
4. Add detailed logging to `message()` method:
   - Log each chunk received from `chat_stream`
   - Log each `edit_text` call and its result
   - Log timing between updates
   - Log any exceptions

**Deliverable**: Document the exact failure mode with logs.

### M2: Identify Root Cause

**Potential causes to investigate**:

| Hypothesis | Test | Evidence Needed |
|------------|------|-----------------|
| Rate limiting from Telegram API | Check for `RetryAfter` exceptions | Exception logs showing rate limit hits |
| Async generator not yielding | Add logging inside `chat_stream` loop | Chunks arriving but not being processed |
| `edit_text` failing silently | Wrap in try/except with logging | Exception on edit calls |
| Event loop blocking | Profile async execution | Delays between chunk reception and processing |
| Message object stale | Check `edit_text` return value | False return or exception on subsequent edits |
| Buffering in LLM client | Check OpenAI client streaming config | Chunks arriving in batches vs individually |

**Deliverable**: Confirmed root cause with evidence.

### M3: Implement Fix

Based on M2 findings, implement the appropriate fix:

- **If rate limiting**: Add cooldown between edits (1 second minimum)
- **If async issues**: Fix event loop handling
- **If edit failures**: Add proper error handling and retry
- **If buffering**: Adjust LLM client streaming parameters

### M4: Test Fix

- Unit tests for the specific fix
- Local integration test with Telegram bot
- Verify streaming works in production

### M5: Document

- Update any relevant documentation
- Add comments explaining the fix

---

## Current Implementation

```python
# src/interfaces/telegram.py

async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages with streaming."""
    if not update.message or not update.message.text:
        return

    response_message = await update.message.reply_text("Thinking...")

    full_response = ""
    last_update_len = 0
    update_threshold = 50  # Update every 50 chars

    try:
        async for chunk in self.alfred.chat_stream(update.message.text):
            full_response += chunk

            if len(full_response) - last_update_len >= update_threshold:
                display_text = full_response[:4000]
                if len(full_response) > 4000:
                    display_text += "\n[Response too long, truncated...]"

                await response_message.edit_text(display_text)
                last_update_len = len(full_response)

        # Final update
        display_text = full_response[:4000]
        if len(full_response) > 4000:
            display_text += "\n[Response too long, truncated...]"

        if display_text != "Thinking...":
            await response_message.edit_text(display_text)

    except Exception as e:
        logger.exception("Error handling message")
        await response_message.edit_text(f"Error: {e}")
```

---

## Success Criteria

- [ ] Root cause identified with evidence
- [ ] Fix implemented and tested locally
- [ ] Streaming updates appear in Telegram in real-time
- [ ] No exceptions in logs during normal operation
- [ ] All tests passing

---

## Open Questions

1. What is the exact symptom users observe? (no updates, delayed updates, etc.)
2. Are there any exceptions currently being logged?
3. Does this affect all responses or only certain types?
4. When did this issue start occurring?

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-18 | Investigation-first approach | Root cause unknown; avoid premature fixes |
