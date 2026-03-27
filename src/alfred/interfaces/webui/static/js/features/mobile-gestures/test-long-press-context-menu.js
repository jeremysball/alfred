/**
 * Tests for Long Press Context Menu
 *
 * Run with: node test-long-press-context-menu.js
 *
 * Phase 3: Touch Gesture Support - Long Press Context Menu Integration
 * - Attaches LongPressDetector to message elements
 * - Shows context menu on long press
 * - Integration with existing MessageContextMenu
 * - MutationObserver for dynamic messages
 */

// Setup DOM globals for Node.js testing
global.HTMLElement = class HTMLElement {
  constructor() {
    this.style = {};
    this._classes = new Set();
    this.classList = {
      add: (cls) => this._classes.add(cls),
      remove: (cls) => this._classes.delete(cls),
      contains: (cls) => this._classes.has(cls),
    };
    this.dataset = {};
    this.children = [];
    this._parent = null;
  }
  matches(selector) {
    // Simple mock matching
    if (selector === '.message') return this._classes.has('message');
    if (selector.includes('data-message-id')) return !!this.dataset.messageId;
    return true;
  }
  closest() { return null; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  getBoundingClientRect() {
    return { left: 100, top: 100, width: 200, height: 50 };
  }
  addEventListener() {}
  removeEventListener() {}
  appendChild(child) {
    child._parent = this;
    this.children.push(child);
  }
};

global.document = {
  createElement(tag) {
    return new global.HTMLElement();
  }
};

global.Node = { ELEMENT_NODE: 1 };

global.MutationObserver = class MutationObserver {
  constructor(callback) {
    this.callback = callback;
  }
  observe() {}
  disconnect() {}
};

global.navigator = {
  vibrate: () => {}
};

global.window = {
  innerWidth: 400,
  addEventListener: () => {},
  removeEventListener: () => {},
  MessageContextMenu: {
    showMessageMenu: () => {}
  }
};

const { LongPressContextMenu } = require('./long-press-context-menu.js');

let testsPassed = 0;
let testsFailed = 0;

function test(name, fn) {
  try {
    fn();
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

// Mock DOM elements for testing
function createMockMessageElement(id = 'msg-1') {
  const el = new HTMLElement();
  el.id = id;
  el.dataset = { messageId: id };
  el._classes.add('message');
  // Proper mock for matches - only matches specific selectors
  el.matches = function(selector) {
    if (selector === '.message') return this._classes.has('message');
    if (selector.includes('data-message-id')) return !!this.dataset.messageId;
    if (['button', 'a', 'input', 'textarea', 'select', '[contenteditable]'].includes(selector)) return false;
    return true;
  };
  el.closest = function() { return null; };
  return el;
}

function createMockContainer() {
  class MockContainer extends HTMLElement {
    querySelectorAll(selector) {
      if (selector === '.message, [data-message-id]') {
        return [
          createMockMessageElement('msg-1'),
          createMockMessageElement('msg-2'),
        ];
      }
      if (selector === '[data-message-id]') {
        return [
          createMockMessageElement('msg-1'),
          createMockMessageElement('msg-2'),
        ];
      }
      return [];
    }
  }
  return new MockContainer();
}

console.log('Running Long Press Context Menu Tests...\n');

// Test 1: Module exports correctly
test('long_press_context_menu_module_exports', () => {
  assert(typeof LongPressContextMenu === 'function', 'LongPressContextMenu should be a constructor function');
});

// Test 2: Initialize with default options
test('context_menu_initializes_with_defaults', () => {
  const menu = new LongPressContextMenu();
  assert(menu !== null, 'Should create instance');
  assert(menu.threshold === 500, 'Default threshold should be 500ms');
  assert(menu.movementTolerance === 10, 'Default movement tolerance should be 10px');
  assert(menu.enableHaptic === true, 'Haptic should be enabled by default');
  assert(menu.enableVisualFeedback === true, 'Visual feedback should be enabled by default');
  assert(Array.isArray(menu.excludeSelectors), 'Should have exclude selectors array');
});

// Test 3: Initialize with custom options
test('context_menu_accepts_custom_options', () => {
  const customHandler = () => {};
  const customExcludes = ['button', 'a'];
  
  const menu = new LongPressContextMenu({
    threshold: 800,
    movementTolerance: 15,
    showContextMenu: customHandler,
    enableHaptic: false,
    enableVisualFeedback: false,
    excludeSelectors: customExcludes,
  });
  
  assert(menu.threshold === 800, 'Custom threshold should be 800ms');
  assert(menu.movementTolerance === 15, 'Custom tolerance should be 15px');
  assert(menu.showContextMenu === customHandler, 'Custom handler should be set');
  assert(menu.enableHaptic === false, 'Haptic should be disabled');
  assert(menu.enableVisualFeedback === false, 'Visual feedback should be disabled');
  assert(menu.excludeSelectors === customExcludes, 'Custom excludes should be set');
});

// Test 4: Attach to element creates detector
test('attach_to_element_creates_detector', () => {
  const menu = new LongPressContextMenu();
  const element = createMockMessageElement('msg-123');
  
  const result = menu.attachToElement(element, 'msg-123');
  
  assert(result === true, 'Should return true on success');
  assert(menu._detectors.has('msg-123'), 'Should store detector by element ID');
  assert(menu.getAttachedCount() === 1, 'Attached count should be 1');
});

// Test 5: Attach returns false for invalid element
test('attach_returns_false_for_invalid_element', () => {
  const menu = new LongPressContextMenu();
  
  const result = menu.attachToElement(null, 'msg-123');
  assert(result === false, 'Should return false for null element');
  
  const result2 = menu.attachToElement('not-an-element', 'msg-123');
  assert(result2 === false, 'Should return false for non-element');
});

// Test 6: Detach removes detector
test('detach_removes_detector', () => {
  const menu = new LongPressContextMenu();
  const element = createMockMessageElement('msg-123');
  
  menu.attachToElement(element, 'msg-123');
  assert(menu._detectors.has('msg-123'), 'Should have detector before detach');
  
  menu.detachFromElement('msg-123');
  assert(!menu._detectors.has('msg-123'), 'Should remove detector after detach');
});

// Test 7: Attach all elements in container
test('attach_all_elements_in_container', () => {
  const menu = new LongPressContextMenu();
  const container = createMockContainer();
  
  const count = menu.attachToAllElements(container);
  
  assert(count === 2, 'Should attach to 2 elements');
  assert(menu._detectors.has('msg-1'), 'Should have detector for message 1');
  assert(menu._detectors.has('msg-2'), 'Should have detector for message 2');
});

// Test 8: Attach all messages convenience method
test('attach_all_messages_convenience', () => {
  const menu = new LongPressContextMenu();
  const container = createMockContainer();
  
  const count = menu.attachToAllMessages(container);
  
  assert(count === 2, 'Should attach to 2 messages');
});

// Test 9: Context menu callback invoked on long press
test('context_menu_callback_invoked', () => {
  let menuShown = false;
  let menuElement = null;
  let menuX = 0;
  let menuY = 0;
  
  const menu = new LongPressContextMenu({
    showContextMenu: (el, x, y) => {
      menuShown = true;
      menuElement = el;
      menuX = x;
      menuY = y;
    }
  });
  
  const element = createMockMessageElement('msg-456');
  menu.attachToElement(element, 'msg-456');
  
  // Simulate long press
  menu._handleLongPress(element, 'msg-456');
  
  assert(menuShown === true, 'showContextMenu should be called');
  assert(menuElement === element, 'Should pass element to callback');
  assert(menuX === 200, 'X should be center of element (100 + 200/2)');
  assert(menuY === 125, 'Y should be center of element (100 + 50/2)');
});

// Test 10: Exclude selectors prevent menu on excluded elements
test('exclude_selectors_prevent_menu', () => {
  let menuShown = false;
  
  const menu = new LongPressContextMenu({
    showContextMenu: () => { menuShown = true; },
    excludeSelectors: ['button']
  });
  
  const element = createMockMessageElement('msg-1');
  
  // Mock matches to simulate button element
  element.matches = (selector) => selector === 'button';
  
  menu._handleLongPress(element, 'msg-1');
  
  assert(menuShown === false, 'Menu should not show for excluded element');
});

// Test 11: Excluded element check with closest
test('exclude_selectors_with_closest', () => {
  let menuShown = false;
  
  const menu = new LongPressContextMenu({
    showContextMenu: () => { menuShown = true; }
  });
  
  const element = createMockMessageElement('msg-1');
  
  // Mock closest to find an anchor parent
  element.closest = (selector) => selector === 'a' ? { tagName: 'A' } : null;
  
  menu._handleLongPress(element, 'msg-1');
  
  assert(menuShown === false, 'Menu should not show when closest ancestor is excluded');
});

// Test 12: Press start/cancel tracking
test('press_start_and_cancel_tracking', () => {
  const menu = new LongPressContextMenu();
  const element = createMockMessageElement('msg-1');
  
  assert(menu.isPressing() === false, 'Should not be pressing initially');
  
  menu._handlePressStart(element);
  assert(menu.isPressing() === true, 'Should be pressing after start');
  assert(menu._activeElement === element, 'Should track active element');
  
  menu._handlePressCancel(element);
  assert(menu.isPressing() === false, 'Should not be pressing after cancel');
  assert(menu._activeElement === null, 'Should clear active element');
});

// Test 13: Re-attachment replaces existing detector
test('reattachment_replaces_detector', () => {
  const menu = new LongPressContextMenu();
  const element1 = createMockMessageElement('msg-1');
  const element2 = createMockMessageElement('msg-1'); // Same ID
  
  menu.attachToElement(element1, 'msg-1');
  const firstDetector = menu._detectors.get('msg-1').detector;
  
  menu.attachToElement(element2, 'msg-1');
  const secondDetector = menu._detectors.get('msg-1').detector;
  
  assert(firstDetector !== secondDetector, 'Should replace detector on re-attachment');
  assert(menu.getAttachedCount() === 1, 'Should still have only 1 detector');
});

// Test 14: Get attached count
test('get_attached_count', () => {
  const menu = new LongPressContextMenu();
  
  assert(menu.getAttachedCount() === 0, 'Count should be 0 initially');
  
  menu.attachToElement(createMockMessageElement('msg-1'), 'msg-1');
  menu.attachToElement(createMockMessageElement('msg-2'), 'msg-2');
  menu.attachToElement(createMockMessageElement('msg-3'), 'msg-3');
  
  assert(menu.getAttachedCount() === 3, 'Count should be 3 after attachments');
  
  menu.detachFromElement('msg-2');
  assert(menu.getAttachedCount() === 2, 'Count should be 2 after detach');
});

// Test 15: Destroy cleans up all detectors
test('destroy_cleans_up_all_detectors', () => {
  const menu = new LongPressContextMenu();
  
  menu.attachToElement(createMockMessageElement('msg-1'), 'msg-1');
  menu.attachToElement(createMockMessageElement('msg-2'), 'msg-2');
  menu.attachToElement(createMockMessageElement('msg-3'), 'msg-3');
  
  assert(menu.getAttachedCount() === 3, 'Should have 3 detectors');
  
  menu.destroy();
  
  assert(menu.getAttachedCount() === 0, 'Should have 0 detectors after destroy');
  assert(menu._mutationObserver === null, 'MutationObserver should be null');
});

// Test 16: Fallback to global MessageContextMenu
test('fallback_to_global_message_context_menu', () => {
  let globalMenuCalled = false;
  
  // Mock global MessageContextMenu
  const originalShowMessageMenu = window.MessageContextMenu.showMessageMenu;
  window.MessageContextMenu.showMessageMenu = () => { globalMenuCalled = true; };
  
  const menu = new LongPressContextMenu({
    showContextMenu: null // No custom handler
  });
  
  const element = createMockMessageElement('msg-1');
  menu.attachToElement(element, 'msg-1');
  
  // Simulate long press
  menu._handleLongPress(element, 'msg-1');
  
  assert(globalMenuCalled === true, 'Should fallback to global MessageContextMenu');
  
  // Restore
  window.MessageContextMenu.showMessageMenu = originalShowMessageMenu;
});

// Summary
console.log('\n-------------------');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('-------------------');

process.exit(testsFailed > 0 ? 1 : 0);
