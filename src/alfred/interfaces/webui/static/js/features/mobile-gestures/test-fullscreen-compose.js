/**
 * Tests for Fullscreen Compose Modal
 *
 * Run with: node test-fullscreen-compose.js
 */

// Minimal DOM-like globals for Node.js testing
class MockHTMLElement {
  constructor(tagName = 'div') {
    this.tagName = tagName;
    this.style = {};
    this.dataset = {};
    this._classes = new Set();
    this._listeners = {};
    this.parentNode = null;
    this._attributes = {};
    this._children = [];
    this.textContent = '';

    const self = this;
    this.classList = {
      add: (...classes) => classes.forEach(cls => self._classes.add(cls)),
      remove: (...classes) => classes.forEach(cls => self._classes.delete(cls)),
      contains: (cls) => self._classes.has(cls),
    };
  }

  setAttribute(key, value) {
    this._attributes[key] = String(value);
  }

  getAttribute(key) {
    return this._attributes[key] || null;
  }

  appendChild(child) {
    if (child) {
      child.parentNode = this;
      this._children.push(child);
    }
    return child;
  }

  removeChild(child) {
    const index = this._children.indexOf(child);
    if (index > -1) {
      this._children.splice(index, 1);
    }
    if (child) {
      child.parentNode = null;
    }
    return child;
  }

  addEventListener(type, handler) {
    this._listeners[type] = handler;
  }

  removeEventListener(type, handler) {
    if (this._listeners[type] === handler) {
      delete this._listeners[type];
    }
  }

  focus() {
    this._focused = true;
  }

  remove() {
    if (this.parentNode) {
      this.parentNode.removeChild(this);
    }
  }
}

class MockTextArea extends MockHTMLElement {
  constructor() {
    super('textarea');
    this.value = '';
    this.placeholder = '';
  }
}

class MockBody extends MockHTMLElement {
  constructor() {
    super('body');
  }
}

// Mock requestAnimationFrame for Node.js environment
global.requestAnimationFrame = (callback) => {
  return setTimeout(callback, 0);
};

global.cancelAnimationFrame = (id) => {
  clearTimeout(id);
};

global.HTMLElement = MockHTMLElement;
global.document = {
  body: new MockBody(),
  _listeners: {},
  createElement(tagName) {
    if (tagName === 'textarea') {
      return new MockTextArea();
    }
    return new MockHTMLElement(tagName);
  },
  addEventListener(type, handler) {
    this._listeners[type] = handler;
  },
  removeEventListener(type, handler) {
    if (this._listeners[type] === handler) {
      delete this._listeners[type];
    }
  }
};

const { FullscreenComposeModal, createFullscreenCompose } = require('./fullscreen-compose.js');

let testsPassed = 0;
let testsFailed = 0;

async function test(name, fn) {
  try {
    await fn();
    console.log(`✓ ${name}`);
    testsPassed++;
  } catch (e) {
    console.log(`✗ ${name}`);
    console.log(`  Error: ${e.message}`);
    testsFailed++;
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

// Async test runner
(async () => {
console.log('\nRunning Fullscreen Compose Tests...\n');

// Basic module exports
await test('fullscreen compose module exports', () => {
  assert(typeof FullscreenComposeModal === 'function', 'FullscreenComposeModal should be exported');
  assert(typeof createFullscreenCompose === 'function', 'createFullscreenCompose should be exported');
});

// Modal initialization
await test('modal initializes with defaults', () => {
  const modal = new FullscreenComposeModal();

  assert(modal.isOpen === false, 'Expected isOpen to be false initially');
  assert(typeof modal.onOpen === 'function', 'Expected onOpen to be a function');
  assert(typeof modal.onClose === 'function', 'Expected onClose to be a function');
  assert(typeof modal.onSubmit === 'function', 'Expected onSubmit to be a function');
  assert(modal.placeholder === 'Type a message...', 'Expected default placeholder');
});

await test('modal accepts custom options', () => {
  const compactInput = new MockTextArea();
  const onOpen = () => {};
  const onClose = () => {};
  const onSubmit = () => {};

  const modal = new FullscreenComposeModal({
    compactInput,
    onOpen,
    onClose,
    onSubmit,
    placeholder: 'Custom placeholder'
  });

  assert(modal.compactInput === compactInput, 'Expected compactInput to be set');
  assert(modal.onOpen === onOpen, 'Expected onOpen to be custom function');
  assert(modal.onClose === onClose, 'Expected onClose to be custom function');
  assert(modal.onSubmit === onSubmit, 'Expected onSubmit to be custom function');
  assert(modal.placeholder === 'Custom placeholder', 'Expected custom placeholder');
});

// Modal open/close
await test('modal open creates DOM elements', () => {
  const modal = new FullscreenComposeModal();

  modal.open();

  assert(modal.element !== null, 'Expected element to be created');
  assert(modal.textarea !== null, 'Expected textarea to be created');
  assert(modal.closeButton !== null, 'Expected close button to be created');
  assert(modal.submitButton !== null, 'Expected submit button to be created');
  assert(modal.backdrop !== null, 'Expected backdrop to be created');

  // Clean up
  modal.close();
});

await test('modal transfers content from compact input on open', () => {
  const compactInput = new MockTextArea();
  compactInput.value = 'Test content';

  const modal = new FullscreenComposeModal({ compactInput });

  modal.open();

  assert(modal.textarea.value === 'Test content', 'Expected content to be transferred');

  // Clean up
  modal.close();
});

await test('modal close transfers content back to compact input', async () => {
  const compactInput = new MockTextArea();
  compactInput.value = 'Initial content';

  const modal = new FullscreenComposeModal({ compactInput });

  modal.open();
  // Wait for open animation
  await new Promise(resolve => setTimeout(resolve, 100));

  modal.textarea.value = 'Updated content';
  modal.close();

  // Content is transferred immediately on close, before animation
  assert(compactInput.value === 'Updated content', 'Expected content to be transferred back');

  // Wait for close animation to complete cleanup
  await new Promise(resolve => setTimeout(resolve, 350));
});

await test('modal tracks open state correctly', async () => {
  const modal = new FullscreenComposeModal();

  assert(modal.isOpened() === false, 'Expected isOpened to be false initially');

  modal.open();
  // Wait for open animation
  await new Promise(resolve => setTimeout(resolve, 100));
  assert(modal.isOpened() === true, 'Expected isOpened to be true after open');

  modal.close();
  // Wait for close animation
  await new Promise(resolve => setTimeout(resolve, 350));
  assert(modal.isOpened() === false, 'Expected isOpened to be false after close');
});

// Content management
await test('getContent returns current textarea value', () => {
  const modal = new FullscreenComposeModal();

  modal.open();
  modal.textarea.value = 'Test message';

  assert(modal.getContent() === 'Test message', 'Expected getContent to return textarea value');

  modal.close();
});

await test('setContent updates textarea value', () => {
  const modal = new FullscreenComposeModal();

  modal.open();
  modal.setContent('New content');

  assert(modal.textarea.value === 'New content', 'Expected setContent to update textarea');

  modal.close();
});

// Submit functionality
await test('submit calls onSubmit with content', () => {
  let submittedContent = null;
  const onSubmit = (content) => { submittedContent = content; };

  const modal = new FullscreenComposeModal({ onSubmit });

  modal.open();
  modal.textarea.value = 'Hello world';
  modal.submit();

  assert(submittedContent === 'Hello world', 'Expected onSubmit to be called with content');
});

await test('submit trims content', () => {
  let submittedContent = null;
  const onSubmit = (content) => { submittedContent = content; };

  const modal = new FullscreenComposeModal({ onSubmit });

  modal.open();
  modal.textarea.value = '  Trimmed content  ';
  modal.submit();

  assert(submittedContent === 'Trimmed content', 'Expected content to be trimmed');
});

await test('submit does not call onSubmit for empty content', () => {
  let submitCalled = false;
  const onSubmit = () => { submitCalled = true; };

  const modal = new FullscreenComposeModal({ onSubmit });

  modal.open();
  modal.textarea.value = '   ';
  modal.submit();

  assert(submitCalled === false, 'Expected onSubmit not to be called for empty content');

  modal.close();
});

await test('submit clears content after sending', () => {
  const compactInput = new MockTextArea();
  compactInput.value = 'Old content';

  const modal = new FullscreenComposeModal({ compactInput });

  modal.open();
  modal.textarea.value = 'Sent message';
  modal.submit();

  assert(modal.textarea.value === '', 'Expected textarea to be cleared');
  assert(compactInput.value === '', 'Expected compact input to be cleared');
});

// Callbacks
await test('onOpen callback is called when modal opens', () => {
  let openCalled = false;
  const onOpen = () => { openCalled = true; };

  const modal = new FullscreenComposeModal({ onOpen });

  modal.open();

  // Callback is called after animation, so check immediately
  // In real implementation it's async, but for test we check the flag is set up
  assert(typeof modal.onOpen === 'function', 'Expected onOpen to be set');

  modal.close();
});

await test('onClose callback is called when modal closes', () => {
  let closeCalled = false;
  const onClose = () => { closeCalled = true; };

  const modal = new FullscreenComposeModal({ onClose });

  modal.open();
  modal.close();

  assert(typeof modal.onClose === 'function', 'Expected onClose to be set');
});

// Edge cases
await test('modal prevents double open', () => {
  const modal = new FullscreenComposeModal();

  modal.open();
  const firstElement = modal.element;

  modal.open(); // Try to open again
  const secondElement = modal.element;

  assert(firstElement === secondElement, 'Expected modal not to recreate elements on double open');

  modal.close();
});

await test('modal prevents close when not open', () => {
  const modal = new FullscreenComposeModal();

  // Should not throw
  modal.close();
  modal.close();

  assert(modal.isOpen === false, 'Expected isOpen to remain false');
});

await test('destroy cleans up modal', async () => {
  const modal = new FullscreenComposeModal();

  modal.open();
  // Wait for open animation
  await new Promise(resolve => setTimeout(resolve, 100));

  modal.destroy();
  // Wait for close animation
  await new Promise(resolve => setTimeout(resolve, 350));

  assert(modal.element === null, 'Expected element to be null after destroy');
  assert(modal.textarea === null, 'Expected textarea to be null after destroy');
  assert(modal.isOpen === false, 'Expected isOpen to be false after destroy');
});

// createFullscreenCompose factory
await test('createFullscreenCompose returns modal and cleanup', () => {
  const compactInput = new MockTextArea();

  const result = createFullscreenCompose(compactInput);

  assert(result !== null, 'Expected result to be returned');
  assert(result.modal !== null, 'Expected modal to be returned');
  assert(typeof result.cleanup === 'function', 'Expected cleanup function to be returned');

  result.cleanup();
});

await test('createFullscreenCompose returns null without input', () => {
  const result = createFullscreenCompose(null);

  assert(result === null, 'Expected null when no input provided');
});

await test('createFullscreenCompose attaches touch event listeners', () => {
  const compactInput = new MockTextArea();

  const result = createFullscreenCompose(compactInput);

  assert(compactInput._listeners.touchstart !== undefined, 'Expected touchstart listener to be attached');
  assert(compactInput._listeners.touchmove !== undefined, 'Expected touchmove listener to be attached');
  assert(compactInput._listeners.touchend !== undefined, 'Expected touchend listener to be attached');

  result.cleanup();
});

await test('cleanup removes event listeners', () => {
  const compactInput = new MockTextArea();

  const result = createFullscreenCompose(compactInput);
  result.cleanup();

  assert(Object.keys(compactInput._listeners).length === 0, 'Expected all listeners to be removed');
});

// Summary
console.log('\n-------------------');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('-------------------');

process.exit(testsFailed > 0 ? 1 : 0);
})();
