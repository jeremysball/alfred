/**
 * BUGGY Auto-Compact Extension - DO NOT USE
 * 
 * This shows the common mistakes that cause the "Working..." hang.
 * Compare with auto-compact-fixed.ts to see the fixes.
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  // BUG #1: Blocking handler - doesn't return immediately
  pi.on("turn_end", async (event, ctx) => {
    const usage = ctx.getContextUsage();
    if (usage && usage.tokens > 100000) {
      // This blocks the event loop - TUI can't update throbber
      await ctx.compact(); // <-- HANGS HERE
    }
  });

  // BUG #2: No error handling - if compact fails, promise never resolves
  pi.on("agent_end", async (event, ctx) => {
    ctx.compact(); // No await, no callbacks - silent failure
  });

  // BUG #3: No re-entrancy check - can trigger multiple concurrent compactions
  let shouldCompact = false;
  pi.on("context", async (event, ctx) => {
    if (shouldCompact) {
      // This can be called multiple times while first compaction is running
      ctx.compact(); // <-- Multiple concurrent compactions = chaos
    }
  });

  // BUG #4: Blocking in before_compact without returning
  pi.on("session_before_compact", async (event, ctx) => {
    // Doing heavy work here blocks the compaction
    const result = await heavyWork(); // <-- Blocks compaction
    // Should return immediately or use event data
  });
}

async function heavyWork() {
  // Simulates blocking work
  return new Promise(resolve => setTimeout(resolve, 5000));
}
