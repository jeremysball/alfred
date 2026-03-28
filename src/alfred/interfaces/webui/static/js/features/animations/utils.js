/**
 * Animation utilities
 */

/**
 * Check if user prefers reduced motion
 * @returns {boolean} True if reduced motion is preferred
 */
export function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Wait for a CSS transition to complete on an element
 * @param {HTMLElement} element - Element to watch
 * @param {string} property - CSS property name (optional)
 * @returns {Promise<void>}
 */
export function waitForTransition(element, property = null) {
  return new Promise((resolve) => {
    const handler = (event) => {
      if (!property || event.propertyName === property) {
        element.removeEventListener("transitionend", handler);
        resolve();
      }
    };
    element.addEventListener("transitionend", handler);
  });
}

/**
 * Wait for a CSS animation to complete
 * @param {HTMLElement} element - Element to watch
 * @returns {Promise<void>}
 */
export function waitForAnimation(element) {
  return new Promise((resolve) => {
    const handler = () => {
      element.removeEventListener("animationend", handler);
      resolve();
    };
    element.addEventListener("animationend", handler);
  });
}

/**
 * Apply will-change before animation, remove after
 * @param {HTMLElement} element - Element to optimize
 * @param {string} properties - CSS properties to optimize (e.g., 'transform, opacity')
 * @returns {Function} Call to remove will-change
 */
export function optimizeForAnimation(element, properties = "transform, opacity") {
  element.style.willChange = properties;

  return () => {
    element.style.willChange = "auto";
  };
}
