# PRD #130: Context Sidebar Panel for Alfred TUI

**Status**: Draft  
**Priority**: Medium  
**Created**: 2026-03-13  
**Related**: #123 (TUI History and Keyboard Shortcuts)

---

## Problem Statement

Users have no visibility into:
1. How much of their context budget is being used
2. What memories are currently loaded
3. How tokens are distributed across system prompt, memories, session history, and tools
4. Which memories could be removed to free up space

Users must currently type `/context` to see a text dump, which:
- Interrupts conversation flow
- Provides no visual hierarchy
- Shows no usage percentages
- Requires leaving chat view

---

## Solution Overview

Add a collapsible **Context Sidebar Panel** to the Alfred TUI that displays:
- Real-time context budget usage (progress bar)
- Breakdown by category (System, Memories, Session, Tools)
- Expandable/collapsible sections
- Quick actions (search, manage, clear)

The sidebar sits alongside the conversation panel in a horizontal split layout.

---

## User Stories

1. **As a power user**, I want to see context usage at a glance so I know when I'm approaching limits.

2. **As a memory-heavy user**, I want to see which memories are loaded so I can manage them without leaving chat.

3. **As a debugging user**, I want to see token breakdown by category so I can understand what's consuming context.

4. **As a screen-limited user**, I want to collapse the sidebar so I have more space for conversation.

---

## Technical Constraints

**Critical**: PyPiTUI only supports **vertical stacking** of components. There is no built-in horizontal layout, flexbox, or grid system.

Components available:
- `Container` - stacks children vertically
- `Box` / `BorderedBox` - single bordered content area
- `Text` / `Markdown` / `RichText` - text rendering
- `Input` - text input with focus
- `TUI` - root container

**Implication**: To achieve horizontal layout (sidebar + main content), we must either:
1. Create a custom `HSplit` component that renders two children side-by-side
2. Use a fixed-width overlay that floats over the conversation
3. Use a "pane switch" pattern (toggle between chat and context views)

---

## Design Options

### Option A: Custom HSplit Component (Recommended)

Create a new `HSplit` layout component that:
- Takes sidebar + main content as children
- Renders them side-by-side in `render()` method
- Handles width calculations
- Passes input to focused panel

```
┌──────────────┬─────────────────────────────────────┐
│ Context      │                                     │
│ [████░░] 67% │  Conversation                       │
│ ▼ SYSTEM     │  goes here...                       │
│   2.4k       │                                     │
│ ▶ MEMORIES   │                                     │
│ ▶ SESSION    │                                     │
└──────────────┴─────────────────────────────────────┘
     ↑30 cols              ↑remaining width
```

**Pros**:
- True side-by-side layout
- Both panels visible simultaneously
- Familiar IDE/editor pattern

**Cons**:
- Requires custom component (new code to maintain)
- Need to handle focus management between panels
- Sidebar reduces conversation width

---

### Option B: Overlay Panel (Modal)

Sidebar slides in as overlay on top of conversation:

```
┌─────────────────────────────────────────────────────┐
│ Conversation                     ┌─ Context ─┐      │
│                                  │ [████░░]  │      │
│ Some text that is partially      │ ▼ SYSTEM  │      │
│ obscured by the overlay panel    │ ▶ MEMORIES│      │
│                                  └───────────┘      │
└─────────────────────────────────────────────────────┘
```

**Pros**:
- Uses existing overlay system
- Conversation still visible underneath
- No layout changes needed

**Cons**:
- Obscures conversation text
- Still reduces visible content
- Overlay focus management complexity

---

### Option C: Pane Switching (Toggle View)

Press key to toggle between Chat view and Context view:

```
Chat View:                    Context View:
┌─────────────────────┐      ┌─────────────────────┐
│ Hello Alfred        │      │ Context Breakdown   │
│                     │  →   │ [████████░░] 80%    │
│ How are you?        │ Tab  │                     │
│                     │      │ Memories: 12        │
│ I'm doing well!     │      │ System: 2.4k        │
└─────────────────────┘      └─────────────────────┘
```

**Pros**:
- Simple implementation (just switch Container children)
- Full width for both views
- No custom layout component needed

**Cons**:
- Can't see context and chat simultaneously
- Requires context switching

---

## Decision

**Option B (Overlay Panel)** selected based on user requirements:

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Layout** | Overlay panel | Floats over conversation, doesn't affect layout |
| **Default state** | Collapsed (hidden) | Clean chat view by default |
| **Persistence** | None | Fresh state each session |
| **Width** | Configurable, resizable | User controls panel size |
| **Narrow terminals** | Auto-hide | Hide if terminal < 80 cols |
| **Sections** | Full expand/collapse | All four sections (System, Memories, Session, Tools) |

### Overlay Behavior

```
Collapsed (default):
┌─────────────────────────────────────────────────────┐
│                                                     │
│  Conversation flows full width...                   │
│                                                     │
│  [Press Ctrl+B to show context panel]              │
│                                                     │
└─────────────────────────────────────────────────────┘

Expanded (overlay on right):
┌──────────────────────────────────────────┬──────────┐
│                                          │ Context  │
│  Conversation visible but               │ [████░░] │
│  partially obscured by overlay          │ ▼ SYSTEM │
│                                          │   2.4k   │
│  [Ctrl+B] toggles, [+/-] resizes        │ ▶ MEM... │
│                                          │          │
└──────────────────────────────────────────┴──────────┘
                                    ↑ adjustable width

Narrow terminal (<80 cols):
┌─────────────────────────────────────────────────────┐
│                                                     │
│  Sidebar auto-hidden - terminal too narrow         │
│                                                     │
│  (Would require <70 cols for conversation)         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Resizing

- `Ctrl++` / `Ctrl+-` to increase/decrease width
- Width range: 20-50 columns
- Default when opened: 30 columns
- Visual indicator during resize

---

## Detailed Design

### Layout Structure

```
AlfredTUI (TUI root)
├── MainContainer (existing)
│   ├── Conversation (scrollable messages)
│   ├── StatusLine
│   └── InputField
└── ContextSidebarOverlay (overlay, conditionally rendered)
    └── ContextPanel (actual content)
        ├── BudgetBar
        ├── Section: System
        ├── Section: Memories
        ├── Section: Session
        ├── Section: Tools
        └── QuickActions
```

**Note**: Overlay uses PyPiTUI's built-in overlay system. When visible, it renders on top of the main content without affecting layout.

### Context Sidebar Content

```
┌─ Context Budget ─────────┐
│ [████████████░░░░] 67%   │  ← Progress bar, color-coded
│ 21.4k / 32k tokens used  │  ← Exact numbers
├──────────────────────────┤
│ ▼ SYSTEM       2.4k      │  ← Always expanded
│   Behavior rules...      │  ← Truncated content preview
├──────────────────────────┤
│ ▶ MEMORIES (12)  8.1k    │  ← Collapsed by default
├──────────────────────────┤
│ ▶ SESSION       10.5k    │  ← Shows message count
│   (45 messages)          │
├──────────────────────────┤
│ ▶ TOOLS          0.3k    │  ← Rarely expanded
├──────────────────────────┤
│ [S]earch  [M]anage [C]lr │  ← Quick actions
└──────────────────────────┘
```

### Color Coding

| Usage | Color | Threshold |
|-------|-------|-----------|
| Healthy | Green | < 50% |
| Warning | Yellow | 50-80% |
| Critical | Red | > 80% |

---

## Interactions

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+B` | Toggle sidebar overlay visibility |
| `Ctrl++` | Increase sidebar width |
| `Ctrl+-` | Decrease sidebar width |
| `Ctrl+1/2/3/4` | Toggle System/Memories/Session/Tools sections |
| `Ctrl+F` | Focus search in memories (when open) |
| `↑/↓` | Navigate sections (when sidebar focused) |
| `Enter` | Expand/collapse section |
| `Esc` | Close sidebar |

### Behavior Rules

1. **Sidebar closed**: All input goes to chat input field
2. **Sidebar open**: Sidebar receives input, chat is visible but inactive
3. **Narrow terminal**: Sidebar refuses to open, shows warning toast
4. **Resize**: Visual indicator shows new width temporarily

### Mouse Support (Future)

- Click section headers to expand/collapse
- Click memories to view details
- Drag sidebar edge to resize

---

## API Requirements

### Context Data Source

The sidebar needs access to:

```python
class ContextInfo:
    budget: int          # Total context budget (e.g., 32000)
    used: int            # Currently used tokens
    
    # Breakdown by section
    system_tokens: int
    memory_tokens: int
    memory_count: int
    session_tokens: int
    session_messages: int
    tool_tokens: int
    
    # Memory details (when expanded)
    memories: list[MemoryPreview]

class MemoryPreview:
    entry_id: str
    content_preview: str  # First 50 chars
    token_count: int
    similarity_score: float  # Why it was included
```

### Integration Points

1. **Alfred.get_context_info()** - Returns current context breakdown
2. **SessionManager.get_message_count()** - For session section
3. **MemoryStore.get_loaded_memories()** - For memories section
4. **ContextAssembler.get_budget_usage()** - For budget bar

---

## Implementation Plan

### Phase 1: Foundation
Create `ContextSidebarOverlay` component using PyPiTUI's overlay system.

**Tasks:**
1. Create `ContextSidebarOverlay` class (extends `Component`)
2. Add toggle keybinding `Ctrl+B` to AlfredTUI
3. Wire overlay into TUI's overlay system
4. Basic show/hide functionality

**Success Criteria**: Press `Ctrl+B` to show/hide overlay panel

### Phase 2: Content & Sections
Build the sidebar content with sections.

**Tasks:**
1. Create `ContextPanel` component (actual content)
2. Design section layout (System, Memories, Session, Tools)
3. Implement expand/collapse for each section
4. Progress bar component for budget
5. Static/mock data for testing

**Success Criteria**: All sections render with expand/collapse working

### Phase 3: Data Integration
Connect to Alfred's context system.

**Tasks:**
1. Create `ContextInfo` dataclass
2. Add `get_context_info()` method to Alfred
3. Real-time updates when context changes
4. Color-coded budget bar (green/yellow/red)

**Success Criteria**: Sidebar shows live context data

### Phase 4: Resizing & Polish
Add width controls and edge cases.

**Tasks:**
1. Width state management (default 30, range 20-50)
2. Keybindings: `Ctrl++` / `Ctrl+-` to resize
3. Auto-hide on narrow terminals (<80 cols)
4. Visual resize indicator
5. Keyboard navigation within panel

**Success Criteria**: Fully functional, polished overlay panel

### Phase 5: Quick Actions
Add action buttons.

**Tasks:**
1. `[S]earch` button → triggers memory search
2. `[M]anage` button → opens memory manager
3. `[C]lear` button → clears session context
4. Button keybindings work

**Success Criteria**: All quick actions functional

---

## Open Questions

1. **Width**: Fixed 30 cols? Configurable? Resizable?
2. **Persistence**: Remember sidebar state across sessions?
3. **Mobile**: How does this work on narrow terminals (< 80 cols)?
4. **Memory Previews**: Show full content on expand, or just metadata?

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Toggle | `Ctrl+B` shows/hides panel in < 100ms |
| Resize | Width adjustable 20-50 cols |
| Narrow handling | Auto-hide when terminal < 80 cols |
| Sections | All 4 sections with expand/collapse |
| Data | Live context budget updates |
| Keyboard | All functions work without mouse |

---

## Out of Scope

- Side-by-side layout (using overlay instead)
- State persistence across sessions
- Memory editing inline (opens editor)
- Context visualization graphs
- Historical context usage charts
- Multiple sidebar panels
- Smooth animations (not supported by PyPiTUI)

---

## Dependencies

- PyPiTUI (already integrated)
- ContextAssembler (existing)
- MemoryStore (existing)
- SessionManager (existing)

---

## Related Files

- `src/alfred/interfaces/pypitui/tui.py` - Main TUI class
- `src/alfred/context.py` - Context assembly
- `src/alfred/context_display.py` - Context formatting (may be replaced)

---

## Notes

The overlay panel uses PyPiTUI's existing overlay system. Key implementation details:

1. **Overlay Registration**: Use `TUI.show_overlay()` to display panel
2. **Input Handling**: Panel receives all input when visible
3. **Positioning**: Fixed position on right side of screen
4. **Z-Index**: Overlays render above main content automatically
5. **Focus**: Panel must call `tui.close_overlay()` to return to chat

**Component Pattern**:
- `ContextSidebarOverlay` - Container, handles visibility and positioning
- `ContextPanel` - Actual content, implements `render(width)`
- Sections are simple data structures, not separate components
