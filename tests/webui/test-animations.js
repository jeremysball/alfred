/**
 * Test: Message Entrance Animations
 * Verifies that animation classes are applied to new messages
 */

import { MessageAnimator } from '../../src/alfred/interfaces/webui/static/js/features/animations/message-animator.js';

describe('MessageAnimator', () => {
  let container;

  beforeEach(() => {
    container = document.createElement('div');
    container.id = 'message-list';
    document.body.appendChild(container);
  });

  afterEach(() => {
    container.remove();
  });

  describe('animateEntrance', () => {
    it('should add message-enter class to element', async () => {
      const messageEl = document.createElement('chat-message');
      messageEl.setAttribute('role', 'user');
      container.appendChild(messageEl);

      // Mock reduced motion to false for test
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: jest.fn().mockImplementation(query => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        })),
      });

      await MessageAnimator.animateEntrance(messageEl, 'user');

      expect(messageEl.classList.contains('message-enter')).toBe(true);
      expect(messageEl.classList.contains('message-enter--visible')).toBe(true);
    });

    it('should add user-specific animation class for user messages', async () => {
      const messageEl = document.createElement('chat-message');
      messageEl.setAttribute('role', 'user');
      container.appendChild(messageEl);

      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: jest.fn().mockImplementation(query => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        })),
      });

      await MessageAnimator.animateEntrance(messageEl, 'user');

      expect(messageEl.classList.contains('message-enter--user')).toBe(true);
    });

    it('should add assistant-specific animation class for assistant messages', async () => {
      const messageEl = document.createElement('chat-message');
      messageEl.setAttribute('role', 'assistant');
      container.appendChild(messageEl);

      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: jest.fn().mockImplementation(query => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        })),
      });

      await MessageAnimator.animateEntrance(messageEl, 'assistant');

      expect(messageEl.classList.contains('message-enter--assistant')).toBe(true);
    });

    it('should skip animation when reduced motion is preferred', async () => {
      const messageEl = document.createElement('chat-message');
      messageEl.setAttribute('role', 'user');
      container.appendChild(messageEl);

      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: jest.fn().mockImplementation(query => ({
          matches: query === '(prefers-reduced-motion: reduce)',
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        })),
      });

      await MessageAnimator.animateEntrance(messageEl, 'user');

      expect(messageEl.classList.contains('message-enter--visible')).toBe(true);
      expect(messageEl.classList.contains('message-enter')).toBe(false);
    });
  });

  describe('animateSequence', () => {
    it('should animate multiple messages in sequence', async () => {
      const items = [
        { element: document.createElement('chat-message'), type: 'user' },
        { element: document.createElement('chat-message'), type: 'assistant' },
        { element: document.createElement('chat-message'), type: 'user' },
      ];

      items.forEach(item => container.appendChild(item.element));

      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: jest.fn().mockImplementation(query => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        })),
      });

      await MessageAnimator.animateSequence(items, 0);

      items.forEach(item => {
        expect(item.element.classList.contains('message-enter--visible')).toBe(true);
      });
    });
  });
});
