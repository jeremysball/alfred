# PRD #123: TUI History and Keyboard Shortcuts

**Status**: Ready  
**Priority**: High  
**Created**: March 11, 2025  
**Author**: pi  
**Issue**: #123

---

## Problem Statement

The Alfred TUI lacks essential navigation and productivity features that users expect from modern terminal interfaces:

1. **No directory-scoped history** - Users cannot recall previous messages from the same working directory
2. **No keyboard shortcuts** - Common operations require manual typing (no Ctrl+C, Ctrl+L, etc.)
3. **No modifier key handling** - Ctrl, Alt, Shift combinations are ignored or handled inconsistently
4. **Poor discoverability** - Users don't know what shortcuts are available

This results in:
- Frustrating repetitive typing
- Slower workflows compared to standard terminal tools
- Inconsistent behavior between CLI and TUI modes
- Users abandoning TUI for simpler but less capable alternatives

---

## Goals

1. **Implement message history** - Persistent per-directory command/message recall with Up/Down arrows
2. **Add keyboard shortcuts** - Standard shortcuts (Ctrl+C, Ctrl+L, Ctrl+U, etc.) for common operations
3. **Support modifier keys** - Full Ctrl, Alt, Shift handling for custom shortcuts
4. **Visual feedback** - Show available shortcuts in status line or help overlay
5. **Zero regression** - All existing TUI functionality preserved

## Non-Goals

- Global history across all directories (out of scope - history is directory-scoped)
- Vim/Emacs keybinding modes (future PRD)
- Mouse support (future PRD)
- Customizable keybindings (future PRD)
- Breaking changes to existing TUI behavior

---

## Success Criteria

- [ ] Up/Down arrows cycle through message history (like bash)
- [ ] Ctrl+C copies selected text or cancels current operation
- [ ] Ctrl+L clears screen (preserving history)
- [ ] Ctrl+U clears current input line
- [ ] Ctrl+A/E move cursor to start/end of line
- [ ] Alt+Left/Right navigate by word
- [ ] Shift+Enter queues message (steering mode)
- [ ] All shortcuts shown in status line or help panel
- [ ] History persists across TUI restarts in same directory
- [ ] History cache stored in XDG-compliant location
- [ ] No existing TUI functionality broken
- [ ] All existing tests pass
- [ ] **All code passes mypy strict mode**: `mypy --strict src/alfred/interfaces/pypitui/`
- [ ] **100% type coverage**: No `Any` types, all functions annotated

---

## Dependencies

### Required
- [x] `pypitui` terminal framework with input handling
- [x] `prompt_toolkit` for key binding infrastructure
- [x] XDG cache directory access (`$XDG_CACHE_HOME/alfred/`)
- [x] Session storage for message persistence (already exists)

### External Dependencies
- None

### Related PRDs
| PRD | Relationship | Impact |
|-----|--------------|--------|
| #95 (PyPiTUI CLI) | Foundation - TUI architecture | Builds on existing TUI structure |
| #96 (Multiline Input) | Related - input handling | May share input widget code |
| #97 (Streaming Throbber) | Related - display components | Should work together |

---

## Integration Points

### What This PRD Touches
- `src/alfred/interfaces/pypitui/tui.py` - Main TUI class, key binding registration
- `src/alfred/interfaces/pypitui/wrapped_input.py` - Input widget modifications
- `src/alfred/interfaces/pypitui/status_line.py` - Shortcut display
- `src/alfred/interfaces/pypitui/history_cache.py` - NEW: Per-directory history cache
- `src/alfred/session.py` - Message history retrieval
- `src/alfred/interfaces/pypitui/message_panel.py` - Visual feedback for operations
- `$XDG_CACHE_HOME/alfred/history/` - Cache directory for history files

### What This PRD Does NOT Touch
| Component | Reason |
|-----------|--------|
| `alfred.py` core logic | TUI-only feature |
| `telegram.py` interface | Different input model |
| Tool implementations | No tool behavior changes |
| Session storage format | Uses existing message retrieval |

### Boundary Conditions
- History is **per-directory** - each working directory has its own history cache
- Cache location: `$XDG_CACHE_HOME/alfred/history.db` (SQLite database)
- Maximum history items: 100 per directory (configurable, prevents bloat)
- Cache format: SQLite table with deduplication (no consecutive duplicates)
- **No TTL** - history persists until manually cleared or evicted by capacity
- Modifier keys intercepted at TUI level before reaching tools
- Shortcuts should work during both idle and streaming states

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                         AlfredTUI                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 KeyboardHandler                       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │  │
│  │  │  KeyBinder   │  │HistoryManager│  │ShortcutHelp│ │  │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  WrappedInput                         │  │
│  │         (modified for history integration)            │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  MessagePanel                         │  │
│  │              (visual feedback)                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Type Safety Requirements

**All code must pass mypy strict mode**: `mypy --strict src/alfred/interfaces/pypitui/`

#### Type Annotation Rules
1. **All function parameters** must have explicit type annotations
2. **All return types** must be explicitly declared (use `-> None` for procedures)
3. **All class attributes** must be type-annotated
4. **No `Any` allowed** - use specific types or `typing.Protocol` for interfaces
5. **Generic types** must specify type parameters: `list[str]`, not `list`
6. **Optional types** must use `| None` syntax (Python 3.10+)
7. **Abstract methods** must use `@abstractmethod` with proper type signatures

#### Strict mypy Configuration
```ini
# pyproject.toml [tool.mypy] section
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
```

### Key Classes

#### 1. `HistoryManager`
```python
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, TypeAlias

# Type aliases for clarity
HistoryIndex: TypeAlias = int
CacheHash: TypeAlias = str
MessageText: TypeAlias = str


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """Immutable single history entry with timestamp.
    
    Attributes:
        message: The message text entered by user
        timestamp: UTC datetime when message was added
        working_dir: Absolute path of working directory for debugging
    """
    message: str
    timestamp: datetime
    working_dir: str
    
    def to_row(self) -> tuple[str, str, str]:
        """Serialize entry to SQLite row tuple."""
        return (
            self.message,
            self.timestamp.isoformat(),
            self.working_dir,
        )
    
    @classmethod
    def from_row(cls, row: tuple[str, str, str]) -> HistoryEntry:
        """Deserialize entry from SQLite row."""
        return cls(
            message=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            working_dir=row[2],
        )


class HistoryManager:
    """Manages per-directory message history with SQLite cache.
    
    Thread-safe: SQLite handles concurrent access.
    
    Attributes:
        _working_dir: The directory this history is scoped to
        _db_path: Path to the SQLite database file
        _max_history: Maximum entries before eviction
        _history: In-memory list of history entries
        _index: Current navigation position (0 = saved input)
        _saved_input: Input text saved when navigating up
    """
    
    _HASH_LENGTH: Final[int] = 16
    
    def __init__(
        self,
        working_dir: Path,
        cache_dir: Path,
        max_history: int = 100,
    ) -> None:
        self._working_dir: Path = working_dir.resolve()
        self._db_path: Path = cache_dir / "history.db"
        self._max_history: int = max_history
        
        self._history: list[HistoryEntry] = []
        self._index: HistoryIndex = 0
        self._saved_input: MessageText = ""
        
        # Initialize DB and load cache
        self._init_db()
        self._load_cache()
    
    def _dir_hash(self, path: Path) -> CacheHash:
        """Generate unique hash for directory path.
        
        Uses SHA256 truncated to _HASH_LENGTH characters.
        """
        full_hash: str = hashlib.sha256(
            str(path.resolve()).encode("utf-8")
        ).hexdigest()
        return full_hash[:self._HASH_LENGTH]
    
    def _init_db(self) -> None:
        """Initialize SQLite database with schema if not exists."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dir_hash TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    working_dir TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dir_hash 
                ON history(dir_hash)
            """)
            conn.commit()
    
    def _load_cache(self) -> None:
        """Load history from SQLite for this working directory."""
        dir_hash: str = self._dir_hash(self._working_dir)
        
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT message, timestamp, working_dir 
                    FROM history 
                    WHERE dir_hash = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (dir_hash, self._max_history)
                )
                rows = cursor.fetchall()
                # Reverse to get chronological order
                self._history = [
                    HistoryEntry.from_row(row) for row in reversed(rows)
                ]
        except sqlite3.Error:
            # Database error, start fresh
            self._history = []
    
    def _save_cache(self) -> None:
        """Save history to SQLite, replacing existing entries for this directory."""
        dir_hash: str = self._dir_hash(self._working_dir)
        
        try:
            with sqlite3.connect(self._db_path) as conn:
                # Delete existing entries for this directory
                conn.execute(
                    "DELETE FROM history WHERE dir_hash = ?",
                    (dir_hash,)
                )
                
                # Insert current history
                for entry in self._history:
                    conn.execute(
                        """
                        INSERT INTO history (dir_hash, message, timestamp, working_dir)
                        VALUES (?, ?, ?, ?)
                        """,
                        (dir_hash, *entry.to_row())
                    )
                
                conn.commit()
        except sqlite3.Error:
            # Silently fail if DB unavailable (graceful degradation)
            pass
    
    def add(self, message: MessageText) -> None:
        """Add message to history and persist to cache.
        
        Deduplicates consecutive identical messages.
        Evicts oldest if at capacity.
        """
        if not message or not message.strip():
            return
        
        stripped: str = message.strip()
        
        # Deduplicate consecutive entries
        if self._history and self._history[-1].message == stripped:
            return
        
        entry: HistoryEntry = HistoryEntry(
            message=stripped,
            timestamp=datetime.now(),
            working_dir=str(self._working_dir),
        )
        
        self._history.append(entry)
        
        # Evict oldest if over capacity
        if len(self._history) > self._max_history:
            self._history.pop(0)
        
        self._save_cache()
    
    def navigate_up(self, current_input: MessageText) -> MessageText:
        """Get previous history item.
        
        Saves current_input when moving from position 0.
        Returns current input if already at oldest history.
        """
        if not self._history:
            return current_input
        
        if self._index == 0:
            self._saved_input = current_input
        
        self._index = min(self._index + 1, len(self._history))
        return self._history[-self._index].message
    
    def navigate_down(self) -> MessageText:
        """Get next history item or return to saved input.
        
        Returns saved input when index reaches 0.
        """
        if self._index == 0:
            return self._saved_input
        
        self._index -= 1
        
        if self._index == 0:
            return self._saved_input
        
        return self._history[-self._index].message
    
    def clear(self) -> None:
        """Clear history and delete database entries for this directory."""
        self._history.clear()
        self._index = 0
        self._saved_input = ""
        
        dir_hash: str = self._dir_hash(self._working_dir)
        
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "DELETE FROM history WHERE dir_hash = ?",
                    (dir_hash,)
                )
                conn.commit()
        except sqlite3.Error:
            pass  # Ignore deletion errors
    
    @property
    def size(self) -> int:
        """Current number of history entries."""
        return len(self._history)
    
    @property
    def is_empty(self) -> bool:
        """True if no history entries."""
        return len(self._history) == 0
```

#### 2. `KeyBindingManager`
```python
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Final, Protocol

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys

if TYPE_CHECKING:
    from alfred.interfaces.pypitui.tui import AlfredTUI


# Protocol for TUI interface to avoid circular imports
class TUIProtocol(Protocol):
    """Protocol for TUI operations needed by key bindings."""
    
    @property
    def input_widget(self) -> object: ...
    
    @property
    def message_panel(self) -> object: ...
    
    @property
    def history_manager(self) -> HistoryManager | None: ...
    
    def clear_screen(self) -> None: ...
    
    def cancel_operation(self) -> None: ...
    
    def queue_message(self, text: str) -> None: ...


# Type alias for key binding handlers
KeyHandler: TypeAlias = Callable[[KeyPressEvent], None]


class KeyBindingManager:
    """Registers and handles all keyboard shortcuts.
    
    Uses prompt_toolkit's key binding system with type-safe handlers.
    All handlers receive KeyPressEvent and have void return.
    
    Attributes:
        bindings: KeyBindings instance from prompt_toolkit
        _tui: Reference to TUI for operations
    """
    
    # Shortcut definitions as class constants for introspection
    SHORTCUTS: Final[list[tuple[str, str]]] = [
        ("↑/↓", "History navigation"),
        ("Ctrl+C", "Copy / Cancel"),
        ("Ctrl+L", "Clear screen"),
        ("Ctrl+U", "Clear line"),
        ("Ctrl+A/E", "Start/End of line"),
        ("Alt+←/→", "Word navigation"),
        ("Shift+Enter", "Queue message"),
        ("?", "Toggle help"),
    ]
    
    def __init__(self, tui: TUIProtocol) -> None:
        self._tui: TUIProtocol = tui
        self.bindings: KeyBindings = KeyBindings()
        self._register_shortcuts()
    
    def _register_shortcuts(self) -> None:
        """Register all keyboard shortcuts with type-safe handlers."""
        # History navigation
        self.bindings.add(Keys.Up)(self._on_history_up)
        self.bindings.add(Keys.Down)(self._on_history_down)
        
        # Editing shortcuts
        self.bindings.add(Keys.ControlC)(self._on_copy_or_cancel)
        self.bindings.add(Keys.ControlL)(self._on_clear_screen)
        self.bindings.add(Keys.ControlU)(self._on_clear_line)
        self.bindings.add(Keys.ControlA)(self._on_start_of_line)
        self.bindings.add(Keys.ControlE)(self._on_end_of_line)
        
        # Word navigation (Alt+ arrows)
        self.bindings.add(Keys.Escape, Keys.Left)(self._on_word_left)
        self.bindings.add(Keys.Escape, Keys.Right)(self._on_word_right)
        
        # Steering mode
        self.bindings.add(Keys.ShiftEnter)(self._on_shift_enter)
        
        # Help
        self.bindings.add("?")(self._on_toggle_help)
    
    def get_bindings(self) -> KeyBindings:
        """Return bindings for prompt_toolkit integration."""
        return self.bindings
    
    def _on_history_up(self, event: KeyPressEvent) -> None:
        """Handle Up arrow - navigate to older history."""
        if self._tui.history_manager is None:
            return
        
        # Get current input text from buffer
        buffer = event.app.current_buffer
        current_text: str = buffer.text
        
        # Get previous history item
        new_text: str = self._tui.history_manager.navigate_up(current_text)
        buffer.text = new_text
        buffer.cursor_position = len(new_text)
    
    def _on_history_down(self, event: KeyPressEvent) -> None:
        """Handle Down arrow - navigate to newer history."""
        if self._tui.history_manager is None:
            return
        
        buffer = event.app.current_buffer
        new_text: str = self._tui.history_manager.navigate_down()
        buffer.text = new_text
        buffer.cursor_position = len(new_text)
    
    def _on_copy_or_cancel(self, event: KeyPressEvent) -> None:
        """Handle Ctrl+C - copy selection or cancel operation."""
        buffer = event.app.current_buffer
        
        if buffer.selection_state is not None:
            # Copy selected text to clipboard
            selected_text: str = buffer.copy_selection()
            event.app.clipboard.set_text(selected_text)
        else:
            # Cancel current operation
            self._tui.cancel_operation()
    
    def _on_clear_screen(self, event: KeyPressEvent) -> None:
        """Handle Ctrl+L - clear screen preserving history."""
        self._tui.clear_screen()
    
    def _on_clear_line(self, event: KeyPressEvent) -> None:
        """Handle Ctrl+U - clear from cursor to start of line."""
        buffer = event.app.current_buffer
        buffer.delete_before_cursor(buffer.cursor_position)
    
    def _on_start_of_line(self, event: KeyPressEvent) -> None:
        """Handle Ctrl+A - move cursor to start of line."""
        event.app.current_buffer.cursor_position = 0
    
    def _on_end_of_line(self, event: KeyPressEvent) -> None:
        """Handle Ctrl+E - move cursor to end of line."""
        buffer = event.app.current_buffer
        buffer.cursor_position = len(buffer.text)
    
    def _on_word_left(self, event: KeyPressEvent) -> None:
        """Handle Alt+Left - move cursor to previous word."""
        buffer = event.app.current_buffer
        pos: int = buffer.cursor_position
        text: str = buffer.text
        
        # Skip whitespace
        while pos > 0 and text[pos - 1].isspace():
            pos -= 1
        
        # Skip word characters
        while pos > 0 and not text[pos - 1].isspace():
            pos -= 1
        
        buffer.cursor_position = pos
    
    def _on_word_right(self, event: KeyPressEvent) -> None:
        """Handle Alt+Right - move cursor to next word."""
        buffer = event.app.current_buffer
        pos: int = buffer.cursor_position
        text: str = buffer.text
        
        # Skip current word
        while pos < len(text) and not text[pos].isspace():
            pos += 1
        
        # Skip whitespace
        while pos < len(text) and text[pos].isspace():
            pos += 1
        
        buffer.cursor_position = pos
    
    def _on_shift_enter(self, event: KeyPressEvent) -> None:
        """Handle Shift+Enter - queue message without sending."""
        buffer = event.app.current_buffer
        message: str = buffer.text.strip()
        
        if message:
            self._tui.queue_message(message)
            buffer.text = ""
    
    def _on_toggle_help(self, event: KeyPressEvent) -> None:
        """Handle ? - toggle shortcut help overlay."""
        # Implementation depends on TUI's help overlay
        pass
```

#### 3. `ShortcutHelpOverlay`
```python
from __future__ import annotations

from typing import Final


class ShortcutHelpOverlay:
    """Floating help panel showing available shortcuts.
    
    Attributes:
        _visible: Current visibility state
        SHORTCUTS: Class-level constant defining all shortcuts
    """
    
    SHORTCUTS: Final[list[tuple[str, str]]] = [
        ("↑/↓", "History navigation"),
        ("Ctrl+C", "Copy / Cancel"),
        ("Ctrl+L", "Clear screen"),
        ("Ctrl+U", "Clear line"),
        ("Ctrl+A/E", "Start/End of line"),
        ("Alt+←/→", "Word navigation"),
        ("Shift+Enter", "Queue message"),
        ("?", "Toggle this help"),
    ]
    
    def __init__(self) -> None:
        self._visible: bool = False
    
    def toggle(self) -> bool:
        """Show/hide help overlay.
        
        Returns:
            New visibility state (True = visible)
        """
        self._visible = not self._visible
        return self._visible
    
    @property
    def is_visible(self) -> bool:
        """Current visibility state."""
        return self._visible
    
    def hide(self) -> None:
        """Force hide the overlay."""
        self._visible = False
    
    def get_formatted_help(self) -> str:
        """Get formatted help text for display.
        
        Returns:
            Multi-line string with aligned shortcuts
        """
        lines: list[str] = ["Keyboard Shortcuts:", ""]
        
        # Calculate column width for alignment
        max_key_len: int = max(len(key) for key, _ in self.SHORTCUTS)
        
        for key, description in self.SHORTCUTS:
            lines.append(f"  {key:<{max_key_len}}  {description}")
        
        return "\n".join(lines)
```

### Data Flow

#### History Operations
```
TUI initializes
      ↓
HistoryManager loads from SQLite for current working_dir
      ↓
User sends message
      ↓
HistoryManager.add(message) → Update in-memory list
      ↓
Write to SQLite ($XDG_CACHE_HOME/alfred/history.db)
      ↓
User presses Up/Down
      ↓
Navigate in-memory history (fast, no disk I/O)
```

#### Keyboard Shortcuts
```
User presses key
      ↓
prompt_toolkit captures key
      ↓
KeyBindingManager.dispatch(event)
      ↓
  ├─→ History navigation? → HistoryManager → Update input widget
  ├─→ Editing shortcut?   → Modify input buffer
  ├─→ Steering mode?      → Queue message, don't send
  └─→ Help?               → Toggle overlay
      ↓
Return control to TUI
```

### System Invariants

Invariants are properties that must always hold true. Tests verify these across all operations.

#### History Invariants
```python
def invariant_history_size_bounded(history: HistoryManager):
    """History never exceeds max_history."""
    assert len(history._history) <= history._max_history

def invariant_no_consecutive_duplicates(history: HistoryManager):
    """No two consecutive entries are identical."""
    for i in range(len(history._history) - 1):
        assert history._history[i].message != history._history[i+1].message

def invariant_index_valid(history: HistoryManager):
    """Navigation index always in valid range."""
    assert 0 <= history._index <= len(history._history)

def invariant_cache_deterministic(history: HistoryManager):
    """Same directory always produces same cache file name."""
    hash1 = history._dir_hash(Path("/project"))
    hash2 = history._dir_hash(Path("/project"))
    assert hash1 == hash2
```

#### Key Binding Invariants
```python
def invariant_bindings_unique(bindings: KeyBindings):
    """No duplicate key bindings registered."""
    keys = [b.keys for b in bindings.bindings]
    assert len(keys) == len(set(keys))

def invariant_handlers_defined(bindings: KeyBindings):
    """All bindings have callable handlers."""
    for binding in bindings.bindings:
        assert callable(binding.handler)
```

#### State Invariants
```python
def invariant_saved_input_preserved(history: HistoryManager):
    """Saved input only modified when navigating up from position 0."""
    # Enforced by implementation
    pass

def invariant_cache_consistent_with_memory(history: HistoryManager):
    """After save, cache file matches in-memory history."""
    history._save_cache()
    # Load and verify
    loaded = HistoryManager(history._working_dir, history._cache_dir.parent)
    assert loaded._history == history._history
```

---

## Implementation Plan

### Phase 1: History Infrastructure
**Goal**: Implement per-directory history cache with SQLite persistence

1. Create `HistoryEntry` dataclass with timestamp and directory
2. Create `HistoryManager` class with in-memory storage
3. Implement directory hash generation for SQLite key
4. Initialize SQLite database with schema (dir_hash, message, timestamp, working_dir)
5. Implement cache loading from SQLite for specific directory
6. Implement cache saving (replace-on-write for simplicity)
7. Add deduplication (no consecutive duplicates)
8. Modify `WrappedInput` to accept history provider
9. Connect Up/Down arrow keys to history navigation
10. Hook into message submission to populate history and save to SQLite
11. Add history clear on `/new` command (deletes directory entries from DB)

**Commits**:
- `feat(tui): add HistoryEntry dataclass with SQLite row conversion`
- `feat(tui): add HistoryManager with SQLite schema initialization`
- `feat(tui): implement SQLite cache loading and saving`
- `feat(tui): integrate history into WrappedInput`
- `feat(tui): persist history to SQLite on message submit`

**Verification**:
```python
# Test cache persistence
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    cache_dir = Path(tmp) / "cache"
    work_dir = Path(tmp) / "project"
    work_dir.mkdir()
    
    # Create and populate history
    history = HistoryManager(work_dir, cache_dir)
    history.add("Hello")
    history.add("World")
    
    # Verify SQLite DB created
    assert (cache_dir / "history.db").exists()
    
    # Create new instance (simulates TUI restart)
    history2 = HistoryManager(work_dir, cache_dir)
    assert history2.navigate_up("") == "World"
    assert history2.navigate_up("") == "Hello"
```

### Phase 2: Basic Keyboard Shortcuts
**Goal**: Add standard editing shortcuts

1. Create `KeyBindingManager` with prompt_toolkit integration
2. Implement Ctrl+U (clear line)
3. Implement Ctrl+A/E (start/end of line)
4. Implement Ctrl+L (clear screen)
5. Implement Ctrl+C (copy if selection, else cancel)

**Commits**:
- `feat(tui): add KeyBindingManager infrastructure`
- `feat(tui): add Ctrl+U, Ctrl+A, Ctrl+E shortcuts`
- `feat(tui): add Ctrl+L clear screen shortcut`
- `feat(tui): add Ctrl+C copy/cancel shortcut`

**Verification**:
- [ ] Each shortcut works in TUI
- [ ] Ctrl+C copies selected text
- [ ] Ctrl+C cancels operation when no selection

### Phase 3: Advanced Navigation
**Goal**: Add word navigation and modifier key handling

1. Implement Alt+Left/Right (word navigation)
2. Implement Shift+Enter (steering mode)
3. Add support for Ctrl+W (delete word)
4. Add support for Ctrl+K (delete to end of line)
5. Test all modifier combinations

**Commits**:
- `feat(tui): add Alt+Left/Right word navigation`
- `feat(tui): add Shift+Enter steering mode`
- `feat(tui): add Ctrl+W and Ctrl+K shortcuts`

**Verification**:
- [ ] Alt+Left moves to previous word
- [ ] Alt+Right moves to next word
- [ ] Shift+Enter queues message without sending

### Phase 4: Visual Feedback
**Goal**: Show shortcuts in UI

1. Add shortcut hints to status line
2. Create `ShortcutHelpOverlay` component
3. Bind `?` key to toggle help
4. Update status line dynamically based on context
5. Add toast notification for shortcut usage

**Commits**:
- `feat(tui): add shortcut hints to status line`
- `feat(tui): add ShortcutHelpOverlay component`
- `feat(tui): bind ? key for help toggle`

**Verification**:
- [ ] Status line shows relevant shortcuts
- [ ] ? toggles help overlay
- [ ] Overlay lists all available shortcuts

### Phase 5: Testing and Polish
**Goal**: Ensure robustness with pre-condition/post-condition/invariant testing using shared fixtures

1. **Design conftest.py fixture hierarchy**:
   - Base fixtures: `temp_cache_dir`, `temp_work_dir`, `default_config`
   - Component fixtures: `history_manager`, `populated_history`, `history_at_max_capacity`
   - Mock fixtures: `mock_tui`, `key_binding_manager`, `mock_key_event`
   - Specialized fixtures: `aged_cache_entry`, `corrupted_cache_file`, `preloaded_cache`
   - Invariant fixture: `assert_invariants` with verification methods

2. Write unit tests for `HistoryManager` using shared fixtures:
   - All tests use fixtures from conftest.py (zero inline setup)
   - `invariant_history_size_bounded`: len(history) ≤ max_history
   - `invariant_no_consecutive_duplicates`: No identical adjacent entries
   - `invariant_index_valid`: 0 ≤ index ≤ len(history)

3. Write cache persistence tests:
   - Use `preloaded_cache` fixture for realistic scenarios
   - Test SQLite error handling
   - Test permissions with `readonly_cache_dir`

4. Write unit tests for `KeyBindingManager`:
   - Use `mock_tui` fixture for isolation
   - `invariant_bindings_unique`: No duplicate key registrations
   - `invariant_handlers_defined`: All bindings have callable handlers

5. Write integration tests for realistic workflows:
   - Compose fixtures: `populated_history` + `key_binding_manager`
   - Test history + shortcuts working together

6. Test edge cases using specialized fixtures:
   - Empty history: fresh `history_manager`
   - Max capacity: `history_at_max_capacity`
   - Corrupted cache: `corrupted_cache_file`

7. Fix any modifier key issues on different terminals
8. Add documentation to USER.md

**Test Files Created**:
- `tests/pypitui/conftest.py` - **All shared fixtures (critical)**
- `tests/pypitui/test_history_manager.py` - Unit tests using fixtures
- `tests/pypitui/test_history_cache.py` - Persistence tests using fixtures
- `tests/pypitui/test_key_binding_manager.py` - Key binding tests using mock fixtures
- `tests/pypitui/test_keyboard_shortcuts.py` - Integration tests using composed fixtures
- `tests/pypitui/test_history_integration.py` - E2E tests using full fixture stack

**Commits**:
- `test(tui): add conftest.py with comprehensive shared fixture hierarchy`
- `test(tui): add HistoryManager unit tests using shared fixtures`
- `test(tui): add cache persistence tests using preloaded_cache fixture`
- `test(tui): add KeyBindingManager unit tests using mock_tui fixture`
- `test(tui): add keyboard shortcuts integration tests with composed fixtures`
- `test(tui): add history E2E tests using full fixture stack`
- `fix(tui): handle edge cases in history navigation`
- `docs(user): add keyboard shortcuts and history documentation`

**Verification**:
- [ ] All tests pass with `uv run pytest tests/pypitui/ -v`
- [ ] **mypy strict mode passes**: `uv run mypy --strict src/alfred/interfaces/pypitui/`
- [ ] **Zero inline setup in tests** - all use conftest.py fixtures
- [ ] Coverage meets targets (HistoryManager 95%, Cache 90%, KeyBindings 90%)
- [ ] All invariants pass (history bounded, no duplicates, valid indices)
- [ ] Fixture composition works correctly (populated_history builds on history_manager)
- [ ] Mock fixtures provide proper isolation for unit tests
- [ ] Cache persistence works across TUI restarts
- [ ] Deduplication prevents consecutive duplicates
- [ ] SQLite database handles concurrent access
- [ ] No regression in existing TUI tests
- [ ] Works on Linux, macOS terminal emulators

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Terminal compatibility issues | Medium | High | Test on multiple terminals (iTerm, Terminal.app, GNOME Terminal, etc.) |
| Conflicts with existing shortcuts | Low | Medium | Audit existing key bindings before implementation |
| SQLite database corruption | Low | High | SQLite is robust, graceful fallback to memory-only if DB locked |
| Database permissions | Low | Medium | Graceful fallback to memory-only if DB unavailable |
| History bloat across directories | Low | Medium | 100-item cap per directory, manual clear available |
| Modifier keys not detected | Medium | Medium | Use prompt_toolkit's cross-platform key handling |
| Breaking existing TUI behavior | Low | High | Comprehensive regression testing |

---

## Verification Checklist

After each commit:
- [ ] `uv run ruff check src/alfred/interfaces/pypitui/` passes
- [ ] `uv run mypy --strict src/alfred/interfaces/pypitui/` passes (zero errors)
- [ ] `uv run pytest tests/pypitui/ -x` passes
- [ ] TUI launches without errors: `uv run alfred`
- [ ] New shortcuts work as expected

After completion:
- [ ] All success criteria met
- [ ] **mypy strict mode passes with zero errors**
- [ ] **All public APIs have complete type annotations**
- [ ] **No use of `Any` type (except where truly necessary with `# type: ignore`)**
- [ ] Test coverage maintained or improved
- [ ] Documentation updated
- [ ] No regression in existing tests
- [ ] Manual testing on multiple terminals
- [ ] SQLite database verified in $XDG_CACHE_HOME/alfred/history.db

---

## Rollback Plan

1. Create backup branch: `git branch backup/pre-tui-history`
2. Each commit is atomic and reversible
3. If issues found: `git revert <commit>`
4. Full rollback: `git reset --hard backup/pre-tui-history`

---

## Test Suite Design

### Test Architecture

```
tests/pypitui/
├── test_history_manager.py          # Unit tests for HistoryManager
├── test_history_cache.py            # Cache persistence tests
├── test_key_binding_manager.py      # Unit tests for KeyBindingManager
├── test_keyboard_shortcuts.py       # Integration tests for shortcuts
├── test_history_integration.py      # End-to-end history tests
└── conftest.py                      # Shared fixtures and invariants
```

### Testing Methodology

All tests use **pre-conditions, post-conditions, and invariants**:

#### Pre-conditions
- Define the required state before test execution
- **Use shared fixtures from conftest.py** - never inline setup
- Establish baseline expectations

#### Operations
- Execute the action being tested
- Single logical operation per test
- Clear input/output boundaries

#### Post-conditions
- Verify expected state changes
- Assert on return values and side effects
- Validate cache/file system state

#### Invariants
- Assertions that must hold true across all states
- Boundaries (history size, index ranges)
- Data integrity (no duplicates, valid timestamps)
- System properties (deterministic hashing)

### Test Design Principles

#### 1. Shared Fixtures Only
**Rule**: All test dependencies must come from `conftest.py` fixtures.

**Why**: 
- Consistent test setup across all test files
- Easy to modify behavior globally
- Reduces code duplication
- Makes tests readable and focused on behavior

**✅ Correct**:
```python
def test_add_increments_history_size(history_manager):
    # history_manager is a shared fixture
    assert len(history_manager._history) == 0
    history_manager.add("test")
    assert len(history_manager._history) == 1
```

**❌ Incorrect**:
```python
def test_add_increments_history_size():
    # Inline setup - never do this
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        work_dir = Path(tmp) / "work"
        history = HistoryManager(work_dir, cache_dir)  # Don't do this
        ...
```

#### 2. Fixture Composition Pattern
Build complex fixtures by composing simpler ones:

```python
# conftest.py
@pytest.fixture
def history_manager(temp_work_dir, temp_cache_dir):
    """Base history manager."""
    return HistoryManager(temp_work_dir, temp_cache_dir)

@pytest.fixture
def populated_history(history_manager):
    """History with 3 entries - composes history_manager."""
    history_manager.add("First")
    history_manager.add("Second")
    history_manager.add("Third")
    return history_manager

@pytest.fixture
def history_at_max_capacity(populated_history):
    """History at 100 items - composes populated_history."""
    for i in range(97):
        populated_history.add(f"Message {i}")
    return populated_history
```

#### 3. Fixture Scope Optimization
Use appropriate scopes to minimize setup overhead:

```python
@pytest.fixture(scope="session")  # Once per test run
def default_config():
    return {"max_history": 100, "ttl_days": 30}

@pytest.fixture(scope="module")  # Once per test file
def shared_cache_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)

@pytest.fixture(scope="function")  # Default: once per test
def history_manager(temp_work_dir, temp_cache_dir):
    return HistoryManager(temp_work_dir, temp_cache_dir)
```

#### 4. Parametrized Fixtures for Edge Cases
Use parametrization to test variations:

```python
@pytest.fixture(params=[0, 1, 50, 99, 100])
def history_size(request):
    """Various history sizes for boundary testing."""
    return request.param

@pytest.fixture
def history_with_size(history_manager, history_size):
    """History populated with specific size."""
    for i in range(history_size):
        history_manager.add(f"Message {i}")
    return history_manager
```

#### 5. Mock Fixtures for Isolation
Provide mocks via fixtures for unit testing:

```python
@pytest.fixture
def mock_tui():
    """Fully mocked TUI for isolated testing."""
    tui = MagicMock()
    tui.input_widget = MagicMock()
    tui.input_widget.text = ""
    tui.input_widget.cursor_position = 0
    tui.message_panel = MagicMock()
    tui.status_line = MagicMock()
    tui.history_manager = MagicMock()
    return tui

@pytest.fixture
def mock_cache_file():
    """Mock cache file with controlled content."""
    mock = MagicMock()
    mock.exists.return_value = True
    mock.read_text.return_value = ""
    return mock
```

### Example Test Structure

**Using Shared Fixtures with Type Annotations (Required Pattern)**:

```python
from pathlib import Path

# Type-only import to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from alfred.interfaces.pypitui.history_cache import HistoryManager
    from tests.pypitui.conftest import InvariantAssertions, MockTUI


def test_add_increments_history_size(
    history_manager: HistoryManager,
    assert_invariants: InvariantAssertions,
) -> None:
    """Test that add() increases history size by 1.
    
    Fixtures:
        history_manager: Fresh HistoryManager from conftest.py
        assert_invariants: Invariant assertion helpers
    """
    # Pre-condition
    assert len(history_manager._history) == 0
    
    # Operation
    history_manager.add("test message")
    
    # Post-condition
    assert len(history_manager._history) == 1
    assert history_manager._history[0].message == "test message"
    
    # Invariants
    assert_invariants.history_size_bounded(history_manager)
    assert_invariants.no_consecutive_duplicates(history_manager)


def test_navigate_up_returns_most_recent(
    populated_history: HistoryManager,
    assert_invariants: InvariantAssertions,
) -> None:
    """Test that navigate_up returns most recent entry first.
    
    Fixtures:
        populated_history: HistoryManager with 3 entries ["First", "Second", "Third"]
    """
    # Pre-condition
    assert len(populated_history._history) == 3
    
    # Operation
    result: str = populated_history.navigate_up("")
    
    # Post-condition
    assert result == "Third message"
    assert populated_history._index == 1
    
    # Invariants
    assert_invariants.index_valid(populated_history)


def test_cache_loads_on_initialization(
    preloaded_cache: Path,
    temp_work_dir: Path,
    temp_cache_dir: Path,
) -> None:
    """Test that history loads from existing SQLite database.
    
    Fixtures:
        preloaded_cache: Cache directory with 3 entries in SQLite
        temp_work_dir: Same directory used to create preloaded_cache
    """
    from alfred.interfaces.pypitui.history_cache import HistoryManager
    
    # Operation: Create new manager (simulates TUI restart)
    manager: HistoryManager = HistoryManager(temp_work_dir, temp_cache_dir)
    
    # Post-condition: All 3 entries loaded (no TTL, all persist)
    assert len(manager._history) == 3
    assert manager._history[0].message == "Recent"
    assert manager._history[1].message == "Old"
    assert manager._history[2].message == "Ancient"
```

**❌ Anti-Pattern (Never Do This)**:

```python
def test_add_increments_history_size():  # No fixture parameters! No return type!
    """Inline setup - violates shared fixtures AND type safety principles."""
    import tempfile
    from pathlib import Path
    from alfred.interfaces.pypitui.history_cache import HistoryManager
    
    # DON'T: Inline setup
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"  # Type inferred, not explicit
        work_dir = Path(tmp) / "work"
        cache_dir.mkdir()
        work_dir.mkdir()
        
        manager = HistoryManager(work_dir, cache_dir)  # Types unknown to mypy
        manager.add("test")
        
        assert len(manager._history) == 1  # No type checking on _history
```

**Why this is wrong:**
1. **No fixtures**: Cannot share setup, duplicates code across tests
2. **No type annotations**: mypy cannot verify correctness
3. **Inline imports**: Import placement inconsistent with project style
4. **No invariants**: Missing verification of system properties

### Coverage Targets

| Component | Target Coverage |
|-----------|----------------|
| HistoryManager | 95% |
| HistoryEntry | 100% |
| KeyBindingManager | 90% |
| Cache I/O | 90% |
| Integration flows | 80% |

### Shared Fixtures (conftest.py)

**Location**: `tests/pypitui/conftest.py`

**Principle**: All test dependencies come from fixtures. Zero inline setup.
**Type Safety**: All fixtures have explicit return type annotations.

#### Type Imports

```python
from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, TypeAlias
from unittest.mock import MagicMock

import pytest
import tempfile

# Type aliases for fixture return types
ConfigDict: TypeAlias = dict[str, int | str]
CacheEntryFactory: TypeAlias = Callable[[str, int], "HistoryEntry"]
```

#### Base Fixtures (Foundation Layer)

```python
@pytest.fixture(scope="session")
def default_config() -> ConfigDict:
    """Default configuration for all history tests.
    
    Session-scoped: Same config for entire test run.
    
    Returns:
        Dictionary with max_history and cache_dir_name
    """
    return {
        "max_history": 100,
        "cache_dir_name": "history",
    }


@pytest.fixture
def temp_cache_dir() -> Iterator[Path]:
    """Temporary cache directory for isolated tests.
    
    Function-scoped: Fresh cache for each test.
    Yields Path to ensure cleanup even on test failure.
    
    Yields:
        Path to temporary cache directory
    """
    with tempfile.TemporaryDirectory() as tmp:
        cache_path: Path = Path(tmp) / "cache"
        cache_path.mkdir(parents=True, exist_ok=True)
        yield cache_path


@pytest.fixture
def temp_work_dir() -> Iterator[Path]:
    """Temporary working directory simulating project directory.
    
    Function-scoped: Fresh directory for each test.
    
    Yields:
        Path to temporary working directory
    """
    with tempfile.TemporaryDirectory() as tmp:
        work_path: Path = Path(tmp) / "project"
        work_path.mkdir(parents=True, exist_ok=True)
        yield work_path
```

#### Component Fixtures (Middle Layer)

```python
@pytest.fixture
def history_manager(
    temp_work_dir: Path,
    temp_cache_dir: Path,
    default_config: ConfigDict,
) -> "HistoryManager":
    """HistoryManager with default configuration.
    
    Depends on: temp_work_dir, temp_cache_dir, default_config
    
    Returns:
        Configured HistoryManager instance
    """
    from alfred.interfaces.pypitui.history_cache import HistoryManager
    return HistoryManager(
        working_dir=temp_work_dir,
        cache_dir=temp_cache_dir,
        max_history=int(default_config["max_history"]),
    )


@pytest.fixture
def populated_history(history_manager: "HistoryManager") -> "HistoryManager":
    """HistoryManager with 3 entries for navigation testing.
    
    Depends on: history_manager
    
    Returns:
        HistoryManager with 3 added entries
    """
    history_manager.add("First message")
    history_manager.add("Second message")
    history_manager.add("Third message")
    return history_manager


@pytest.fixture
def history_at_max_capacity(
    history_manager: "HistoryManager",
    default_config: ConfigDict,
) -> "HistoryManager":
    """HistoryManager at max_history limit.
    
    Depends on: history_manager, default_config
    Used for: Testing eviction, boundary conditions
    
    Returns:
        HistoryManager filled to capacity
    """
    max_history: int = int(default_config["max_history"])
    for i in range(max_history):
        history_manager.add(f"Message {i}")
    return history_manager


@pytest.fixture
def history_with_duplicates(history_manager: "HistoryManager") -> "HistoryManager":
    """HistoryManager with consecutive duplicates.
    
    Used for: Testing deduplication logic
    
    Returns:
        HistoryManager with duplicate entries
    """
    history_manager.add("Duplicate")
    history_manager.add("Duplicate")  # Should be deduplicated
    history_manager.add("Unique")
    history_manager.add("Duplicate")  # Not consecutive, should remain
    return history_manager
```

#### Mock Fixtures (Isolation Layer)

```python
class MockTUI(Protocol):
    """Protocol for mocked TUI to satisfy type checking."""
    input_widget: MagicMock
    message_panel: MagicMock
    status_line: MagicMock
    history_manager: MagicMock
    
    def clear_screen(self) -> None: ...
    def cancel_operation(self) -> None: ...
    def queue_message(self, text: str) -> None: ...


@pytest.fixture
def mock_tui() -> MockTUI:
    """Fully mocked TUI for isolated unit testing.
    
    Provides: input_widget, message_panel, status_line, history_manager
    
    Returns:
        MagicMock configured as TUI
    """
    tui: MockTUI = MagicMock()
    
    # Input widget mock
    tui.input_widget = MagicMock()
    tui.input_widget.text = ""
    tui.input_widget.cursor_position = 0
    tui.input_widget.buffer = MagicMock()
    tui.input_widget.buffer.text = ""
    tui.input_widget.buffer.cursor_position = 0
    
    # Other components
    tui.message_panel = MagicMock()
    tui.status_line = MagicMock()
    tui.history_manager = MagicMock()
    
    return tui


@pytest.fixture
def key_binding_manager(mock_tui: MockTUI) -> "KeyBindingManager":
    """KeyBindingManager with mocked TUI.
    
    Depends on: mock_tui
    
    Returns:
        KeyBindingManager configured with mock TUI
    """
    from alfred.interfaces.pypitui.key_bindings import KeyBindingManager
    return KeyBindingManager(mock_tui)


@pytest.fixture
def mock_key_event() -> Callable[[str], MagicMock]:
    """Factory for mock key press events.
    
    Usage: mock_key_event("up"), mock_key_event("ctrl-c")
    
    Returns:
        Factory function that creates mock KeyPressEvent
    """
    def _create(key_name: str) -> MagicMock:
        event: MagicMock = MagicMock()
        event.key_sequence = [MagicMock()]
        event.key_sequence[0].key = key_name
        return event
    return _create
```

#### Specialized Fixtures (Application Layer)

```python
@pytest.fixture
def aged_cache_entry() -> CacheEntryFactory:
    """Factory for creating cache entries with specific age.
    
    Usage: aged_cache_entry("message", days_ago=45)
    
    Returns:
        Factory function: (message: str, days_ago: int) -> HistoryEntry
    """
    def _create(message: str, days_ago: int) -> "HistoryEntry":
        from alfred.interfaces.pypitui.history_cache import HistoryEntry
        return HistoryEntry(
            message=message,
            timestamp=datetime.now() - timedelta(days=days_ago),
            working_dir="/test"
        )
    return _create


@pytest.fixture
def corrupted_cache_file(temp_cache_dir: Path) -> Path:
    """Cache file with invalid JSON content.
    
    Used for: Testing graceful error handling
    
    Returns:
        Path to corrupted cache file
    """
    cache_file: Path = temp_cache_dir / "corrupted.jsonl"
    cache_file.write_text("invalid json {\nnot valid}")
    return cache_file


@pytest.fixture
def readonly_cache_dir(temp_cache_dir: Path) -> Iterator[Path]:
    """Cache directory without write permissions.
    
    Used for: Testing permission error handling.
    Restores permissions after test for cleanup.
    
    Yields:
        Path to read-only cache directory
    """
    temp_cache_dir.chmod(0o555)  # Read-only
    yield temp_cache_dir
    temp_cache_dir.chmod(0o755)  # Restore for cleanup


@pytest.fixture
def preloaded_cache(
    temp_cache_dir: Path,
    temp_work_dir: Path,
    aged_cache_entry: CacheEntryFactory,
) -> Path:
    """Cache directory with existing history entries.
    
    Creates realistic cache state for loading tests.
    
    Returns:
        Path to cache directory with 3 entries (no TTL, all persist)
    """
    from alfred.interfaces.pypitui.history_cache import HistoryManager
    
    # Create manager to use its save logic
    manager: HistoryManager = HistoryManager(temp_work_dir, temp_cache_dir)
    
    # Add entries with various ages (no TTL, all persist)
    manager._history = [
        aged_cache_entry("Recent", days_ago=1),
        aged_cache_entry("Old", days_ago=20),
        aged_cache_entry("Ancient", days_ago=365),  # No TTL, persists
    ]
    manager._save_cache()
    
    return temp_cache_dir
```

#### Invariant Verification Fixtures

```python
class InvariantAssertions:
    """Collection of invariant assertion methods."""
    
    @staticmethod
    def history_size_bounded(
        history: "HistoryManager",
        max_size: int | None = None,
    ) -> None:
        """Assert history never exceeds max_history."""
        max_size = max_size or history._max_history
        assert len(history._history) <= max_size, \
            f"History size {len(history._history)} exceeds max {max_size}"
    
    @staticmethod
    def no_consecutive_duplicates(history: "HistoryManager") -> None:
        """Assert no two consecutive entries are identical."""
        for i in range(len(history._history) - 1):
            assert history._history[i].message != history._history[i+1].message, \
                f"Duplicate at positions {i} and {i+1}"
    
    @staticmethod
    def index_valid(history: "HistoryManager") -> None:
        """Assert navigation index always in valid range."""
        assert 0 <= history._index <= len(history._history), \
            f"Index {history._index} out of range [0, {len(history._history)}]"
    
    @staticmethod
    def cache_deterministic(
        history: "HistoryManager",
        path: Path,
        expected_hash: str,
    ) -> None:
        """Assert same directory produces same cache file name."""
        actual_hash: str = history._dir_hash(path)
        assert actual_hash == expected_hash, \
            f"Hash mismatch: {actual_hash} != {expected_hash}"


@pytest.fixture
def assert_invariants() -> InvariantAssertions:
    """Provide invariant assertion functions to all tests.
    
    Usage in test:
        def test_something(history_manager: HistoryManager, assert_invariants: InvariantAssertions):
            history_manager.add("test")
            assert_invariants.history_size_bounded(history_manager)
    
    Returns:
        InvariantAssertions instance with static assertion methods
    """
    return InvariantAssertions()
```

#### Fixture Dependency Graph

```
conftest.py Fixture Hierarchy:

Session Scope:
└── default_config

Function Scope - Base:
├── temp_cache_dir
└── temp_work_dir

Function Scope - Component:
├── history_manager (depends: temp_work_dir, temp_cache_dir, default_config)
├── populated_history (depends: history_manager)
├── history_at_max_capacity (depends: history_manager, default_config)
└── history_with_duplicates (depends: history_manager)

Function Scope - Mocks:
├── mock_tui
├── key_binding_manager (depends: mock_tui)
└── mock_key_event

Function Scope - Specialized:
├── aged_cache_entry (factory)
├── corrupted_cache_file (depends: temp_cache_dir)
├── readonly_cache_dir (depends: temp_cache_dir)
├── preloaded_cache (depends: temp_cache_dir, temp_work_dir, aged_cache_entry)
└── assert_invariants (utility)
```

### Key Test Categories

1. **Unit Tests**: Isolated component testing with mocks
2. **Cache Tests**: SQLite persistence, error handling
3. **Integration Tests**: Component interactions, end-to-end flows
4. **Invariant Tests**: Property-based testing for boundaries

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2025-03-11 | Per-directory history cache | User requested directory-scoped history for project context | Cache file per working directory, hash-based naming |
| 2025-03-11 | Pre/post/invariant test methodology | Formal verification approach ensures robustness | All tests follow structured format, invariants prevent regressions |
| 2025-03-11 | 100-item cap per directory | Prevents cache bloat, matches common shell history limits | Memory bounded, predictable performance |
| 2025-03-11 | SQLite for history storage | ACID compliance, concurrent access, single file | Reliable persistence, no manual file management |
| 2025-03-11 | SHA256 hash for directory key | Deterministic, collision-resistant, efficient lookup | Same directory always maps to same key |
| 2025-03-11 | Replace-on-write strategy | Simpler than incremental updates, prevents corruption | SQLite transaction ensures consistency |
| 2025-03-11 | **No TTL** | User wants full history preservation | History persists until manually cleared or evicted |
| 2025-03-11 | Consecutive deduplication only | Preserves intentional repeated commands later | Natural shell-like behavior |
| 2025-03-11 | All tests use shared fixtures from conftest.py | Eliminates code duplication, ensures consistency | Zero inline setup in tests, fixture composition pattern |
| 2025-03-11 | Strict mypy enforcement (`--strict` mode) | Prevents type errors, improves IDE support | All functions fully annotated, no `Any` types |

---

## References

- prompt_toolkit key binding docs: https://python-prompt-toolkit.readthedocs.io/en/master/pages/advanced_topics/key_bindings.html
- Existing TUI: `src/alfred/interfaces/pypitui/tui.py`
- Input widget: `src/alfred/interfaces/pypitui/wrapped_input.py`
- Related PRDs: #95 (PyPiTUI CLI), #96 (Multiline Input)
