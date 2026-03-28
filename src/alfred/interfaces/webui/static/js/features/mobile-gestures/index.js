/**
 * Mobile Gestures Module
 *
 * Touch-friendly interactions for mobile users.
 * Provides swipe-to-reply, long-press menus, and pull-to-refresh.
 *
 * @module mobile-gestures
 */

import { CoordinatedLongPressDetector, CoordinatedSwipeDetector } from "./coordinated-detectors.js";
import { createFullscreenCompose, FullscreenComposeModal } from "./fullscreen-compose.js";
import { GestureCoordinator } from "./gesture-coordinator.js";
import { LongPressContextMenu } from "./long-press-context-menu.js";
import { LongPressDetector } from "./long-press-detector.js";
import { createPullIndicator, PullIndicator } from "./pull-indicator.js";
import { PullToRefreshDetector } from "./pull-to-refresh.js";
import { SwipeDetector } from "./swipe-detector.js";
import { SwipeToReply } from "./swipe-to-reply.js";
// Import detector utilities
import { isInEdgeZone, isTouchDevice, shouldHandleTouch } from "./touch-detector.js";

/**
 * Gesture configuration constants
 */
const GESTURE_CONFIG = {
  SWIPE_THRESHOLD: 100, // px to trigger swipe
  EDGE_MARGIN: 40, // px to disable gestures (browser conflict protection)
  LONG_PRESS_DELAY: 500, // ms
  PULL_THRESHOLD: 80, // px to trigger refresh
};

/**
 * Initialize mobile gesture features
 * Called once on app startup
 */
function initializeGestures() {
  // Only initialize on touch devices
  if (!isTouchDevice()) {
    console.log("[Gestures] Touch device not detected, skipping gesture initialization");
    return;
  }

  console.log("[Gestures] Initializing mobile gestures...");

  // Initialize features will be added here as they are implemented:
  // - Swipe-to-reply on message elements
  // - Long-press context menus
  // - Pull-to-refresh on chat container

  console.log("[Gestures] Mobile gestures initialized");
}

/**
 * Check if gestures should be enabled for an element
 * @param {HTMLElement} element - Element to check
 * @param {number} touchX - Touch X coordinate
 * @returns {boolean}
 */
function shouldEnableGestures(element, touchX) {
  // Check if touch device
  if (!isTouchDevice()) {
    return false;
  }

  // Check edge zone
  if (isInEdgeZone(touchX, window.innerWidth, GESTURE_CONFIG.EDGE_MARGIN)) {
    return false;
  }

  // Check if element should handle touches
  if (!shouldHandleTouch(element)) {
    return false;
  }

  return true;
}

/**
 * Initialize pull-to-refresh with visual indicator and optional ConnectionMonitor integration
 *
 * @param {HTMLElement} element - Element to attach pull-to-refresh to
 * @param {Object} options - Configuration options
 * @param {Function} options.onRefresh - Callback when refresh is triggered (optional)
 * @param {Object} options.connectionMonitor - ConnectionMonitor instance with reconnect() method (optional)
 * @param {HTMLElement} options.scrollContainer - Scroll container to check (default: element)
 * @param {Object} options.indicatorOptions - Options passed to PullIndicator
 * @param {number} options.debounceMs - Debounce time between pulls in ms (default: 2000)
 * @returns {Object} Object containing detector, indicator, and cleanup function
 */
function initializePullToRefresh(element, options = {}) {
  if (!element || !isTouchDevice()) {
    return null;
  }

  const connectionMonitor = options.connectionMonitor;
  const debounceMs = options.debounceMs ?? 2000;
  let isRefreshing = false;
  let lastRefreshTime = 0;

  // Create detector with integrated callback
  const detector = new PullToRefreshDetector({
    threshold: options.threshold || GESTURE_CONFIG.PULL_THRESHOLD,
    onRefresh: async (detail) => {
      // Debounce check
      const now = Date.now();
      if (isRefreshing || now - lastRefreshTime < debounceMs) {
        console.log("[PullToRefresh] Debounced - ignoring pull");
        return;
      }

      // Check if ConnectionMonitor is available
      if (!connectionMonitor) {
        console.warn("[PullToRefresh] No ConnectionMonitor provided");
        // Still call user callback if provided
        if (typeof options.onRefresh === "function") {
          await options.onRefresh(detail);
        }
        return;
      }

      isRefreshing = true;

      try {
        // Attempt to reconnect
        await connectionMonitor.reconnect();

        // Success - indicator will show success via createPullIndicator wiring
        lastRefreshTime = Date.now();
      } catch (error) {
        // Failure - indicator will show error via createPullIndicator wiring
        console.error("[PullToRefresh] Reconnect failed:", error);
        throw error; // Re-throw so indicator shows error state
      } finally {
        isRefreshing = false;
      }
    },
  });

  // Create and wire up visual indicator
  const indicator = createPullIndicator(detector, options.indicatorOptions);

  // Attach to element
  detector.attachToElement(element, options.scrollContainer);

  // Return cleanup function
  const cleanup = () => {
    detector.destroy();
    indicator.destroy();
  };

  return { detector, indicator, cleanup };
}

/**
 * Initialize fullscreen compose on a textarea element
 *
 * @param {HTMLTextAreaElement} compactInput - The compact composer textarea
 * @param {Object} options - Configuration options
 * @param {Function} options.onSubmit - Callback when message is submitted
 * @param {Function} options.onOpen - Callback when modal opens
 * @param {Function} options.onClose - Callback when modal closes
 * @param {string} options.placeholder - Placeholder text
 * @returns {Object} Object containing modal and cleanup function
 */
function initializeFullscreenCompose(compactInput, options = {}) {
  if (!compactInput || !isTouchDevice()) {
    console.log(
      "[Gestures] Touch device not detected or no input provided, skipping fullscreen compose",
    );
    return null;
  }

  console.log("[Gestures] Initializing fullscreen compose...");

  const result = createFullscreenCompose(compactInput, options);

  if (result) {
    console.log("[Gestures] Fullscreen compose initialized");
  }

  return result;
}

// Export public API
export {
  CoordinatedLongPressDetector,
  CoordinatedSwipeDetector,
  createFullscreenCompose,
  createPullIndicator,
  FullscreenComposeModal,
  // Configuration
  GESTURE_CONFIG,
  // Gesture coordination
  GestureCoordinator,
  initializeFullscreenCompose,
  // Initialization
  initializeGestures,
  initializePullToRefresh,
  isInEdgeZone,
  // Device detection
  isTouchDevice,
  LongPressContextMenu,
  LongPressDetector,
  PullIndicator,
  PullToRefreshDetector,
  // Gesture detectors
  SwipeDetector,
  // Feature implementations
  SwipeToReply,
  shouldEnableGestures,
  shouldHandleTouch,
};

// Also expose to window for browser usage
if (typeof window !== "undefined") {
  window.MobileGestures = {
    GESTURE_CONFIG,
    isTouchDevice,
    isInEdgeZone,
    shouldHandleTouch,
    shouldEnableGestures,
    SwipeDetector,
    LongPressDetector,
    SwipeToReply,
    LongPressContextMenu,
    PullToRefreshDetector,
    PullIndicator,
    createPullIndicator,
    FullscreenComposeModal,
    createFullscreenCompose,
    GestureCoordinator,
    CoordinatedSwipeDetector,
    CoordinatedLongPressDetector,
    initializeGestures,
    initializePullToRefresh,
    initializeFullscreenCompose,
  };
}
