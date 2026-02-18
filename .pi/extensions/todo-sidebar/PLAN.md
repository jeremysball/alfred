# Todo-List Extension with Collapsible Sidebar - TDD Plan

## Requirements

1. **Collapsible Sidebar**: Display todo list in a sidebar that can be collapsed/expanded
2. **Todo Management**: Add, toggle, clear todos
3. **Persistent State**: Store todos in session (like existing todo example)
4. **UI Integration**: Use Pi's widget system for sidebar display

## Architecture

### Components

1. **TodoStore**: Manages todo state and session persistence
2. **SidebarWidget**: Renders the todo list in a collapsible sidebar
3. **TodoTool**: LLM-accessible tool for todo management
4. **Commands**:
   - `/todo`: Open todo sidebar
   - `/todo-toggle`: Collapse/expand sidebar
   - `/todo-add <text>`: Quick add todo
   - `/todo-clear`: Clear all todos

### State Management

- Todos stored in session via tool result details
- Sidebar collapsed/expanded state stored in extension (non-persisted)
- State reconstructed from session on load/switch/fork/tree events

### UI Design

```
┌─────────────────────────────────┬──────────────┐
│                                 │ ☐ Todo 1     │
│   Main Chat Area                │ ☐ Todo 2     │
│                                 │ ☑ Todo 3     │
│                                 │              │
│                                 │ [+ Add]      │
│                                 │              │
│                                 │ ▼ Collapse   │
└─────────────────────────────────┴──────────────┘
```

When collapsed:
```
┌─────────────────────────────────┬─────┐
│                                 │ ▶   │
│   Main Chat Area                │ 3   │
│                                 │     │
└─────────────────────────────────┴─────┘
```

## Test Plan

### Unit Tests

1. **TodoStore Tests**:
   - `add()` creates todo with auto-incrementing ID
   - `toggle()` marks todo as done/undone
   - `clear()` removes all todos
   - `getAll()` returns current todos
   - `getCompletedCount()` returns correct count
   - `getPendingCount()` returns correct count

2. **SidebarWidget Tests**:
   - Renders full list when expanded
   - Renders compact view when collapsed
   - Shows correct completion counts
   - Toggle button changes state

3. **Integration Tests**:
   - Tool execution updates state
   - State persists across session events
   - UI updates when state changes

### Acceptance Criteria

- [ ] Can add todo via LLM tool
- [ ] Can toggle todo via LLM tool
- [ ] Can clear todos via LLM tool
- [ ] Sidebar displays when `/todo` command used
- [ ] Sidebar can be collapsed/expanded
- [ ] Shows completion count in collapsed state
- [ ] Persists across session switches

## Implementation Steps

1. Create test file with failing tests
2. Implement TodoStore with state management
3. Implement SidebarWidget with render logic
4. Implement TodoTool for LLM integration
5. Implement Commands for user interaction
6. Run tests and fix any failures
7. Manual integration testing

## File Structure

```
.pie/extensions/
└── todo-sidebar/
    ├── PLAN.md
    ├── todo-sidebar.test.ts
    └── todo-sidebar.ts
```
