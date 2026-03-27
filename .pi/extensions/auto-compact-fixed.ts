/**
 * Fixed Auto-Compact Extension for pi
 * 
 * This extension automatically compacts sessions when they exceed
token thresholds, without hanging on the "Working..." throbber.
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";

// Configuration
const CONFIG = {
  // Compact when context exceeds this many tokens
  TOKEN_THRESHOLD: 100_000,
  // Minimum time between auto-compactions (ms)
  COOLDOWN_MS: 60_000,
  // Show notification when auto-compacting
  NOTIFY_ON_COMPACT: true,
};

// Track last compaction time to prevent thrashing
let lastCompactionTime = 0;
let isCompacting = false;

export default function (pi: ExtensionAPI) {
  /**
   * Check if we should auto-compact based on context size
   */
  async function maybeAutoCompact(ctx: ExtensionContext): Promise<void> {
    // Prevent concurrent compactions
    if (isCompacting) {
      console.log("[auto-compact] Already compacting, skipping");
      return;
    }

    // Check cooldown
    const now = Date.now();
    if (now - lastCompactionTime < CONFIG.COOLDOWN_MS) {
      console.log("[auto-compact] In cooldown period, skipping");
      return;
    }

    // Get context usage
    const usage = ctx.getContextUsage();
    if (!usage || usage.tokens < CONFIG.TOKEN_THRESHOLD) {
      return; // Under threshold, no action needed
    }

    console.log(`[auto-compact] Context at ${usage.tokens} tokens, triggering compaction`);
    
    // Set flag to prevent re-entry
    isCompacting = true;

    try {
      if (CONFIG.NOTIFY_ON_COMPACT) {
        ctx.ui.notify(`Auto-compacting session (${usage.tokens.toLocaleString()} tokens)...`, "info");
      }

      // Use setTimeout to yield control and let the throbber animate
      await new Promise(resolve => setTimeout(resolve, 100));

      // Trigger compaction with proper callbacks
      ctx.compact({
        customInstructions: "Summarize the conversation, keeping recent context and any code changes.",
        onComplete: (result) => {
          isCompacting = false;
          lastCompactionTime = Date.now();
          
          const tokensSaved = result.tokensBefore - result.tokensAfter;
          ctx.ui.notify(
            `Compacted: ${tokensSaved.toLocaleString()} tokens saved`,
            "success"
          );
          
          console.log("[auto-compact] Compaction complete:", {
            tokensBefore: result.tokensBefore,
            tokensAfter: result.tokensAfter,
            tokensSaved,
          });
        },
        onError: (error) => {
          isCompacting = false;
          ctx.ui.notify(`Compaction failed: ${error.message}`, "error");
          console.error("[auto-compact] Compaction error:", error);
        },
      });
    } catch (error) {
      isCompacting = false;
      console.error("[auto-compact] Unexpected error:", error);
    }
  }

  /**
   * Check context size after each turn
   */
  pi.on("turn_end", async (_event, ctx) => {
    // Run in background - don't block the turn
    maybeAutoCompact(ctx).catch(err => {
      console.error("[auto-compact] Error in turn_end handler:", err);
    });
  });

  /**
   * Also check when agent becomes idle (after all tool calls complete)
   */
  pi.on("agent_end", async (_event, ctx) => {
    maybeAutoCompact(ctx).catch(err => {
      console.error("[auto-compact] Error in agent_end handler:", err);
    });
  });

  /**
   * Manual compact command with /compact-auto
   */
  pi.registerCommand("compact-auto", {
    description: "Trigger auto-compaction immediately",
    handler: async (_args, ctx) => {
      const usage = ctx.getContextUsage();
      if (!usage) {
        ctx.ui.notify("No context usage available", "error");
        return;
      }

      if (usage.tokens < CONFIG.TOKEN_THRESHOLD) {
        const ok = await ctx.ui.confirm(
          "Context below threshold",
          `Current: ${usage.tokens.toLocaleString()} tokens. Threshold: ${CONFIG.TOKEN_THRESHOLD.toLocaleString()}. Compact anyway?`
        );
        if (!ok) return;
      }

      await maybeAutoCompact(ctx);
    },
  });

  /**
   * Status command
   */
  pi.registerCommand("compact-status", {
    description: "Show auto-compact status",
    handler: async (_args, ctx) => {
      const usage = ctx.getContextUsage();
      const timeSinceLast = Date.now() - lastCompactionTime;
      const cooldownRemaining = Math.max(0, CONFIG.COOLDOWN_MS - timeSinceLast);
      
      ctx.ui.notify(
        `Tokens: ${usage?.tokens.toLocaleString() || "unknown"} / ${CONFIG.TOKEN_THRESHOLD.toLocaleString()} ` +
        `| Cooldown: ${Math.ceil(cooldownRemaining / 1000)}s`,
        "info"
      );
    },
  });

  // Log initialization
  console.log("[auto-compact] Extension loaded:", CONFIG);
}
