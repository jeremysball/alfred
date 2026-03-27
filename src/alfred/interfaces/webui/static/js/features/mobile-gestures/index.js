/**
 * Mobile Gestures Module
 *
 * Touch-friendly interactions for mobile users.
 * Provides swipe-to-reply, long-press menus, and pull-to-refresh.
 *
 * @module mobile-gestures
 */

// Import detector utilities
const { isTouchDevice, isInEdgeZone, shouldHandleTouch } = require('./touch-detector.js');
const { SwipeDetector } = require('./swipe-detector.js');
const { LongPressDetector } = require('./long-press-detector.js');
const { LongPressContextMenu } = require('./long-press-context-menu.js');
const { SwipeToReply } = require('./swipe-to-reply.js');
const { PullToRefreshDetector } = require('./pull-to-refresh.js');
const { PullIndicator, createPullIndicator } = require('./pull-indicator.js');

/**
 * Gesture configuration constants
 */
const GESTURE_CONFIG = {
  SWIPE_THRESHOLD: 100,      // px to trigger swipe
  EDGE_MARGIN: 40,           // px to disable gestures (browser conflict protection)
  LONG_PRESS_DELAY: 500,     // ms
  PULL_THRESHOLD: 80,        // px to trigger refresh
};

/**
 * Initialize mobile gesture features
 * Called once on app startup
 */
function initializeGestures() {
  // Only initialize on touch devices
  if (!isTouchDevice()) {
    console.log('[Gestures] Touch device not detected, skipping gesture initialization');
    return;
  }

  console.log('[Gestures] Initializing mobile gestures...');

  // Initialize features will be added here as they are implemented:
  // - Swipe-to-reply on message elements
  // - Long-press context menus
  // - Pull-to-refresh on chat container

  console.log('[Gestures] Mobile gestures initialized');
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
 * Initialize pull-to-refresh with visual indicator
 *
 * @param {HTMLElement} element - Element to attach pull-to-refresh to
 * @param {Object} options - Configuration options
 * @param {Function} options.onRefresh - Callback when refresh is triggered
 * @param {HTMLElement} options.scrollContainer - Scroll container to check (default: element)
 * @param {Object} options.indicatorOptions - Options passed to PullIndicator
 * @returns {Object} Object containing detector and indicator instances
 */
function initializePullToRefresh(element, options = {}) {
  if (!element || !isTouchDevice()) {
    return null;
  }

  // Create detector
  const detector = new PullToRefreshDetector({
    threshold: options.threshold || GESTURE_CONFIG.PULL_THRESHOLD,
    onRefresh: options.onRefresh,
  });

  // Create and wire up visual indicator
  const indicator = createPullIndicator(detector, options.indicatorOptions);

  // Attach to element
  detector.attachToElement(element, options.scrollContainer);

  return { detector, indicator };
}

// Export public API
module.exports = {
  // Configuration
  GESTURE_CONFIG,

  // Device detection
  isTouchDevice,
  isInEdgeZone,
  shouldHandleTouch,
  shouldEnableGestures,

  // Gesture detectors
  SwipeDetector,
  LongPressDetector,

  // Feature implementations
  SwipeToReply,
  LongPressContextMenu,
  PullToRefreshDetector,
  PullIndicator,
  createPullIndicator,

  // Initialization
  initializeGestures,
  initializePullToRefresh,
};

// Also expose to window for browser usage
if (typeof window !== 'undefined') {
  window.MobileGestures = module.exports;
}
