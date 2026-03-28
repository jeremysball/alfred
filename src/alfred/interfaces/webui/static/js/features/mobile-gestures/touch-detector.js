/**
 * Touch Detector
 *
 * Detects touch capability and edge zones for gesture handling.
 * Used by mobile gesture features to determine device capabilities
 * and prevent conflicts with browser edge gestures.
 */

/**
 * Check if the current device supports touch input
 * @returns {boolean} True if touch is supported
 */
function isTouchDevice() {
  // Check for touch APIs
  const hasTouchAPI =
    typeof window !== "undefined" &&
    ("ontouchstart" in window ||
      (window.DocumentTouch && document instanceof window.DocumentTouch));

  // Check for touch points (modern browsers)
  const hasTouchPoints = typeof navigator !== "undefined" && navigator.maxTouchPoints > 0;

  // Check for coarse pointer (CSS media query via JS)
  const hasCoarsePointer =
    typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia("(pointer: coarse)").matches;

  return !!(hasTouchAPI || hasTouchPoints || hasCoarsePointer);
}

/**
 * Check if a touch position is in the edge zone (for browser gesture protection)
 * @param {number} touchX - The X coordinate of the touch
 * @param {number} screenWidth - The width of the screen/viewport
 * @param {number} edgeMargin - The margin size for edge zones (default: 40px)
 * @returns {boolean} True if touch is in edge zone
 */
function isInEdgeZone(touchX, screenWidth, edgeMargin = 40) {
  // Left edge zone: x < edgeMargin
  const isLeftEdge = touchX < edgeMargin;

  // Right edge zone: x > screenWidth - edgeMargin
  const isRightEdge = touchX > screenWidth - edgeMargin;

  return isLeftEdge || isRightEdge;
}

/**
 * Check if an element should handle touch events
 * Useful for disabling gestures on specific elements (inputs, scrollable areas)
 * @param {HTMLElement} element - The element to check
 * @param {string[]} excludedSelectors - CSS selectors to exclude
 * @returns {boolean} True if element should handle touches
 */
function shouldHandleTouch(
  element,
  excludedSelectors = ["input", "textarea", "select", "[contenteditable]"],
) {
  if (!element || !(element instanceof Element)) {
    return false;
  }

  // Check if element or any parent matches excluded selectors
  for (const selector of excludedSelectors) {
    if (element.matches(selector) || element.closest(selector)) {
      return false;
    }
  }

  return true;
}

// Export for ESM and browser usage
export { isInEdgeZone, isTouchDevice, shouldHandleTouch };

if (typeof window !== "undefined") {
  window.TouchDetector = {
    isTouchDevice,
    isInEdgeZone,
    shouldHandleTouch,
  };
}
