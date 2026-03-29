## Testing Guidance

For code changes, prefer test-first work when practical:

1. Add or update a test that describes the intended behavior
2. Observe the failure when useful
3. Implement the smallest change that passes
4. Re-run the relevant checks

When the bug is about lifecycle, integration, CLI, TUI, or other user-visible behavior, verify through the real interface rather than only internal state.

Ad-hoc shell checks are useful for exploration, but they do not replace repeatable verification.
