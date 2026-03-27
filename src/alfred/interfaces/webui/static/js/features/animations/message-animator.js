/**
 * Message entrance animations
 * Handles slide/fade animations for new messages
 */

import { prefersReducedMotion, waitForTransition, optimizeForAnimation } from './utils.js';

export class MessageAnimator {
  /**
   * Animate a message element entering the DOM
   * @param {HTMLElement} element - Message element to animate
   * @param {string} type - 'user' or 'assistant'
   * @returns {Promise<void>} Resolves when animation completes
   */
  static async animateEntrance(element, type = 'assistant') {
    // Skip animation if reduced motion is preferred
    if (prefersReducedMotion()) {
      element.classList.add('message-enter--visible');
      return;
    }

    // Add base animation class
    element.classList.add('message-enter');

    // Add type-specific variant
    if (type === 'user') {
      element.classList.add('message-enter--user');
    } else if (type === 'assistant') {
      element.classList.add('message-enter--assistant');
    }

    // Force reflow to ensure initial state is applied
    element.offsetHeight;

    // Apply will-change for performance
    const cleanup = optimizeForAnimation(element);

    // Trigger animation by adding visible class
    requestAnimationFrame(() => {
      element.classList.add('message-enter--visible');
    });

    // Wait for animation to complete
    await waitForTransition(element, 'transform');

    // Clean up will-change
    cleanup();

    // Return for chaining
    return;
  }

  /**
   * Quickly animate multiple messages in sequence
   * @param {Array<{element: HTMLElement, type: string}>} items - Messages to animate
   * @param {number} staggerDelay - Delay between each message (ms)
   */
  static async animateSequence(items, staggerDelay = 50) {
    for (let i = 0; i < items.length; i++) {
      const { element, type } = items[i];
      await this.animateEntrance(element, type);

      if (i < items.length - 1) {
        await new Promise(resolve => setTimeout(resolve, staggerDelay));
      }
    }
  }
}
