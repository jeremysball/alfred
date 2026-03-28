/**
 * Animations Feature Module
 * GPU-accelerated animations for native app feel
 */

import { MessageAnimator } from "./message-animator.js";
import { Skeleton } from "./skeleton.js";
import { ToolCallProgress } from "./tool-call-progress.js";
import { TypingIndicator } from "./typing-indicator.js";
import { prefersReducedMotion } from "./utils.js";

/**
 * Initialize all animation features
 */
export function initAnimations() {
  // Check for reduced motion preference
  if (prefersReducedMotion()) {
    console.log("[Animations] Reduced motion preference detected, animations disabled");
    return;
  }

  // Add animation styles if not already present
  if (!document.getElementById("animations-styles")) {
    const link = document.createElement("link");
    link.id = "animations-styles";
    link.rel = "stylesheet";
    link.href = "/static/js/features/animations/styles.css";
    document.head.appendChild(link);
  }

  console.log("[Animations] Initialized");
}

export { MessageAnimator, prefersReducedMotion, Skeleton, ToolCallProgress, TypingIndicator };
