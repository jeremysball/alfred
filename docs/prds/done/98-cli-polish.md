# PRD: CLI Polish - Status Line Enhancements

**Status**: Proposed
**Priority**: Low
**Created**: 2026-02-26
**Depends on**: 95-pypitui-cli, 97-streaming-throbber

---

## Problem Statement

The status line is functional but could be more informative and visually appealing. This PRD collects polish items that enhance the user experience without adding major features.

---

## Enhancement Categories

### 1. Visual Indicators

#### 1.1 Streaming Animation
See PRD #97 (Streaming Throbber)

#### 1.2 Context Health Bar

Visual context window usage indicator.

```
[████████░░] 80%
```

- Gradient from green (low) → yellow (medium) → red (high)
- Show only when > 50% used
- Click or hover for exact numbers

**Implementation:**
- Calculate percentage: `ctx_tokens / max_context`
- Map to bar segments (10 segments = 10% each)
- Color based on threshold

#### 1.3 Model Provider Icon

Tiny icon before model name indicating provider.

| Provider | Icon | Unicode |
|----------|------|---------|
| OpenAI | ◯ | U+25EF |
| Anthropic | △ | U+25B3 |
| Google | ◇ | U+25C7 |
| Local | ◆ | U+25C6 |
| Unknown | □ | U+25A1 |

**Implementation:**
- Detect provider from model name prefix
- Fall back to unknown icon

#### 1.4 Connection Status

Network health indicator.

| State | Icon | Color |
|-------|------|-------|
| Connected | ◉ | Green |
| Disconnected | ○ | Red |
| Reconnecting | ◔ | Yellow blink |

**Implementation:**
- Track last successful API call
- Show disconnected if > 30s without response
- Requires error state tracking

---

### 2. Token Display

#### 2.1 Token Cost Estimation

Show approximate dollar cost for session.

```
kimi/kimi-k2-5 | ↓1.2K ↑150 | ≈$0.02
```

- Dim color (subtle)
- Requires model pricing configuration
- Formula: `(input_tokens * input_price + output_tokens * output_price) / 1M`

**Implementation:**
- Add pricing config per model
- Calculate running total
- Format with appropriate precision

#### 2.2 Token Rate

Show tokens per second during streaming.

```
↓1.2K ↑150 | 125 t/s
```

- Only show during active streaming
- Update every frame
- Hide when not streaming

**Implementation:**
- Track tokens received and time elapsed
- Calculate rate: `tokens / seconds`
- Reset on each message

#### 2.3 Cache Hit Indicator

Show cache effectiveness.

```
⚡85%
```

- Only show when cache ratio > 0
- Lightning bolt suggests speed
- Encourages context reuse

**Implementation:**
- Calculate: `cached_tokens / total_input_tokens`
- Show as percentage

---

### 3. Session Info

#### 3.1 Session Duration

How long this session has been active.

```
23m
```

- Update every minute
- Format: `5m`, `1h 23m`, `2d 5h`

**Implementation:**
- Track session start time
- Calculate elapsed on each render
- Format human-readable

#### 3.2 Message Count

Total messages in conversation.

```
💬42
```

- Or just `#42` for simpler look
- Useful for long sessions

**Implementation:**
- Count messages in conversation container
- Or track in AlfredTUI state

#### 3.3 Memory Count

Stored memories in system.

```
📚128
```

- Shows value of the session
- Click to search (future)

**Implementation:**
- Query memory count from Alfred
- Cache to avoid repeated queries

---

### 4. Interactive Elements (Advanced)

#### 4.1 Clickable Model Name

Switch model on click.

- Shows dropdown/fuzzy finder
- Requires overlay support
- Future enhancement

#### 4.2 Progress Bar for Tools

Tool execution progress indicator.

```
[░░░░░░░░░░] running bash...
```

- Show while tool is executing
- Animate with moving indicator

#### 4.3 Error Indicator

Flash on errors, show count.

```
⚠ 2 errors
```

- Click to see error log
- Reset on new session

---

### 5. Layout Variations

#### 5.1 Right-Aligned Info

Some info on right side of status.

```
kimi/kimi-k2-5 | ↓1.2K ↑150        23m 💬5
```

- Left: model, tokens, streaming
- Right: session info

#### 5.2 Multi-Line Status

Two rows when terminal wide enough (>120 cols).

```
Row 1: kimi/kimi-k2-5 | ↓1.2K ↑150 | ⠋
Row 2: 23m | 💬5 | 📚128 | ≈$0.02
```

---

## Priority Ranking

| Item | Priority | Effort | Impact |
|------|----------|--------|--------|
| Streaming throbber | High | Low | High |
| Context health bar | Medium | Medium | Medium |
| Token cost | Medium | Low | Medium |
| Session duration | Low | Low | Low |
| Message count | Low | Low | Low |
| Cache indicator | Low | Low | Low |
| Provider icon | Low | Low | Low |
| Token rate | Low | Low | Medium |
| Connection status | Low | Medium | Low |
| Interactive elements | Low | High | Medium |
| Multi-line status | Low | Medium | Low |

---

## Implementation Order

1. **Streaming throbber** (PRD #97) — Biggest visual impact
2. **Context health bar** — Useful feedback
3. **Token cost** — Cost awareness
4. **Session duration** — Simple, nice to have
5. **Cache indicator** — Encourages good patterns
6. **Token rate** — During streaming only

---

## Testing Strategy

Each enhancement should have:
- Unit test for calculation/formatting
- Visual test in tmux
- Width responsiveness test

---

## Out of Scope

- Real-time collaboration indicators
- Usage quotas/billing integration
- A/B testing of layouts
