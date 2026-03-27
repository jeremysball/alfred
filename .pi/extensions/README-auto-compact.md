# Fixed Auto-Compact Extension

## The Problem

The original auto-compact extension caused pi to hang on the "Working..." throbber because:

1. **Blocking synchronous operations** in event handlers
2. **Missing error callbacks** causing silent failures
3. **Re-entrancy issues** - compaction triggering itself recursively
4. **Not yielding control** to let the TUI update

## The Fix

### 1. Non-blocking Event Handlers
```typescript
// BAD - blocks the TUI
pi.on("turn_end", async (event, ctx) => {
  await ctx.compact(); // Hangs here!
});

// GOOD - runs in background, doesn't block
pi.on("turn_end", async (event, ctx) => {
  maybeAutoCompact(ctx).catch(err => {
    console.error("Error:", err);
  });
});
```

### 2. Proper Callbacks
```typescript
// BAD - no callbacks, hangs if compaction fails
ctx.compact();

// GOOD - always provide callbacks
ctx.compact({
  onComplete: (result) => { /* ... */ },
  onError: (error) => { /* ... */ },
});
```

### 3. Re-entrancy Protection
```typescript
let isCompacting = false;

async function maybeAutoCompact(ctx) {
  if (isCompacting) return; // Prevent concurrent calls
  isCompacting = true;
  
  try {
    ctx.compact({
      onComplete: () => { isCompacting = false; },
      onError: () => { isCompacting = false; },
    });
  } catch (e) {
    isCompacting = false;
  }
}
```

### 4. Yield to TUI Thread
```typescript
// Allow throbber to animate before heavy work
await new Promise(resolve => setTimeout(resolve, 100));
```

## Installation

Copy `auto-compact-fixed.ts` to:
- Global: `~/.pi/agent/extensions/auto-compact.ts`
- Project-local: `.pi/extensions/auto-compact.ts`

## Usage

The extension auto-triggers when context exceeds 100k tokens. Manual commands:

```
/compact-auto    - Trigger compaction immediately
/compact-status  - Show current token count and cooldown
```

## Configuration

Edit the `CONFIG` object at the top of the file:

```typescript
const CONFIG = {
  TOKEN_THRESHOLD: 100_000,  // Tokens before auto-compact
  COOLDOWN_MS: 60_000,       // Min time between compactions
  NOTIFY_ON_COMPACT: true,   // Show notification when compacting
};
```
