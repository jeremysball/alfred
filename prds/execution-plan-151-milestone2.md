# Execution Plan: PRD #151 - Milestone 2: Markdown List Containment

## Overview
Make bulleted and numbered lists stay inside message bubbles on desktop and mobile. The fix should live in the shared base stylesheet so all themes inherit it, with a Playwright regression that renders real assistant markdown and checks for horizontal overflow at both viewport sizes.

---

## Phase 1: Global markdown list containment

### Component: Browser regression for bubble-contained lists

- [x] **Test**: `test_markdown_lists_stay_inside_message_bubbles_on_mobile_and_desktop()` - render assistant markdown containing unordered and ordered lists at desktop and mobile viewports, and assert the rendered list content does not overflow the bubble
- [x] **Implement**: add `tests/webui/test_markdown_lists.py` with a Playwright browser test that mounts a `chat-message`, renders markdown lists, and checks the bubble/content geometry at both viewport sizes
- [x] **Run**: `uv run pytest tests/webui/test_markdown_lists.py -v`

### Component: Shared list layout rules

- [x] **Test**: `test_base_css_contains_message_list_containment_rules()` - verify `base.css` defines global `ul`, `ol`, and `li` containment rules under `.message-content`
- [x] **Implement**: add shared list layout rules to `src/alfred/interfaces/webui/static/css/base.css` so list indentation and long list items stay within the bubble on all themes
- [x] **Run**: `uv run pytest tests/webui/test_contrast_standardization.py tests/webui/test_markdown_lists.py -v`

---

## Files to Modify

1. `src/alfred/interfaces/webui/static/css/base.css` — shared markdown list containment rules
2. `tests/webui/test_contrast_standardization.py` — static CSS contract assertion for list containment
3. `tests/webui/test_markdown_lists.py` — browser regression for mobile and desktop overflow

## Commit Strategy

Each checkbox should land as a small, atomic change:

- `test(webui): cover markdown list containment`
- `feat(webui): contain markdown lists inside message bubbles`

## Exit Criteria

- Ordered and unordered markdown lists stay inside the bubble on mobile and desktop
- The containment rules live in the shared base stylesheet rather than a theme override
- Browser regression coverage prevents the overflow regression from returning
