# Development TODOs

- [ ] **Add Shift+Enter to queue message** - Allow queuing messages while LLM is running
- [ ] **Normal Enter is steering mode** - Interject with it instead of waiting for completion
- [ ] **Add background color to tool call output** - Better visual distinction for tool calls
- [ ] **Keybind to toggle tool call output** - Show/hide tool call sections

- investigate whether we should or should not include reasoning traces and if so how to do so. 
  - **Insight**: For a coding agent, the best middle ground is often to save the reasoning only for the immediate previous turn, but summarize or discard it for older turns.
- [ ] **Remove max iterations limit** - Agent should run until completion or user cancellation, not have an arbitrary iteration cap
- [ ] **Create PRD for ESC keybinding** - Add keyboard shortcut to cancel the current LLM call

## Edit Tool Safety

- [ ] **Ensure edit tool forces exact text matching**
  - Current issue: LLM sometimes guesses file state when it doesn't have the most up-to-date content
  - Solution: Add validation that `oldText` parameter matches current file content exactly before applying edit
  - Reject edit with clear error if mismatch detected

- [ ] **Add pre-edit validation to verify current file state**
  - Read file immediately before each edit operation
  - Compare against `oldText` parameter
  - Provide diff output when mismatch occurs
  - Require explicit confirmation for non-exact matches

## CLI Testing

- [ ] **Create CLI test harness for interactive testing**
  - Build a test harness that can actually interact with the CLI (not just unit tests)
  - Should support automated input sequences and output capture
  - Use for regression testing the threading/buffering fixes
  - Consider using `pexpect` or similar for pseudo-TTY interaction
  - Test scenarios: piped input, multiple inputs, streaming output, keyboard interrupts

- [ ] **Integrate prompt-toolkit library for proper async CLI**
  - Replace custom async_input() with prompt_toolkit's PromptSession
  - Native async support without run_in_executor() threading hacks
  - Eliminates need for os.write() workaround by avoiding threading entirely
  - Provides bonus features: history, keybindings, completion, multiline input
  - https://python-prompt-toolkit.readthedocs.io/

## Test Configuration

- [ ] **Skip integration and e2e tests during regular pytest runs**
  - Mark integration tests with `@pytest.mark.integration`
  - Mark e2e tests with `@pytest.mark.e2e`
  - Configure `pyproject.toml` to exclude these by default
  - Keep unit tests fast for development feedback

- [ ] **Configure CI to run integration and e2e tests**
  - Add separate CI job for integration tests
  - Add separate CI job for e2e tests
  - Run full suite on PRs and main branch
  - Allow unit tests to pass quickly for rapid iteration

## Code Quality

- [ ] **Fix pytest deprecation warnings**
  - `asyncio.iscoroutinefunction` deprecated in Python 3.16
    - Replace with `inspect.iscoroutinefunction()` in `src/cron/scheduler.py:289`
  - Pydantic class-based `config` deprecated in V2
    - Update `src/tools/base.py` to use `ConfigDict` instead
    - Update all tool parameter classes
  - Unknown pytest marks (`slow`)
    - Register custom marks in `pyproject.toml`

## Completed

- [x] ~~Implement M8 Resource Limits~~
- [x] ~~Implement M9 Natural Language Interface~~
- [x] ~~Implement M7 Approval Workflow~~
- [x] ~~Implement M11 Integration Testing~~
- [x] ~~Fix race condition in CronStore~~
- [x] ~~Add data/ to .gitignore~~
