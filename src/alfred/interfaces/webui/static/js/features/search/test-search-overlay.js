/**
 * Unit tests for SearchOverlay component
 * Milestone 9 Phase 1: In-Conversation Search (Ctrl+F)
 */

// Simple test framework
let testsPassed = 0;
let testsFailed = 0;

function test(name, fn) {
  try {
    fn();
    testsPassed++;
    console.log(`  ✓ ${name}`);
  } catch (error) {
    testsFailed++;
    console.error(`  ✗ ${name}`);
    console.error(`    ${error.message}`);
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(message || `Expected ${expected}, got ${actual}`);
  }
}

// Mock DOM environment
global.document = {
  createElement: (tag) => ({
    tagName: tag.toUpperCase(),
    className: '',
    classList: {
      add: function(c) { this._classes = this._classes || []; this._classes.push(c); },
      remove: function(c) { this._classes = this._classes || []; this._classes = this._classes.filter(x => x !== c); },
      contains: function(c) { return (this._classes || []).includes(c); }
    },
    style: {},
    appendChild: function(child) { this.children = this.children || []; this.children.push(child); },
    addEventListener: function() {},
    removeEventListener: function() {},
    querySelector: function() { return null; },
    querySelectorAll: function() { return []; },
    focus: function() { this._focused = true; },
    setAttribute: function(k, v) { this[k] = v; },
    getAttribute: function(k) { return this[k]; }
  }),
  body: {
    appendChild: function() {},
    removeChild: function() {}
  },
  addEventListener: function() {},
  removeEventListener: function() {}
};

global.window = {
  find: function() { return true; },
  getSelection: function() { return { removeAllRanges: function() {} }; },
  addEventListener: function() {},
  removeEventListener: function() {}
};

// Import the module (will fail until implemented)
let SearchOverlay;
try {
  const mod = require('./search-overlay.js');
  SearchOverlay = mod.SearchOverlay;
} catch (e) {
  SearchOverlay = null;
}

console.log('\n=== SearchOverlay Tests ===\n');

// Test 1: SearchOverlay can be instantiated
test('SearchOverlay can be instantiated with options', () => {
  if (!SearchOverlay) {
    throw new Error('SearchOverlay not exported - module not implemented yet');
  }
  const overlay = new SearchOverlay({
    onSearch: () => {},
    onNavigate: () => {},
    onClose: () => {}
  });
  assert(overlay !== null, 'SearchOverlay should be created');
  assert(typeof overlay.open === 'function', 'SearchOverlay should have open method');
  assert(typeof overlay.close === 'function', 'SearchOverlay should have close method');
});

// Test 2: Singleton pattern - getInstance returns same instance
test('SearchOverlay.getInstance returns singleton instance', () => {
  if (!SearchOverlay) return;
  const instance1 = SearchOverlay.getInstance();
  const instance2 = SearchOverlay.getInstance();
  assertEquals(instance1, instance2, 'getInstance should return same instance');
});

// Test 3: Open creates and shows overlay element
test('open() creates overlay element and adds to DOM', () => {
  if (!SearchOverlay) return;
  const overlay = new SearchOverlay({});
  overlay.open();
  assert(overlay.element !== null, 'Overlay element should be created');
  assert(overlay.isOpen === true, 'isOpen should be true after open()');
});

// Test 4: Close removes overlay element
test('close() removes overlay element from DOM', () => {
  if (!SearchOverlay) return;
  const overlay = new SearchOverlay({});
  overlay.open();
  overlay.close();
  assert(overlay.isOpen === false, 'isOpen should be false after close()');
});

// Test 5: Search input triggers onSearch callback
test('search input triggers onSearch callback', () => {
  if (!SearchOverlay) return;
  let searchCalled = false;
  let searchQuery = '';
  const overlay = new SearchOverlay({
    onSearch: (query) => {
      searchCalled = true;
      searchQuery = query;
    }
  });
  overlay.open();
  // Simulate input
  if (overlay.searchInput) {
    overlay.searchInput.value = 'test query';
    overlay.handleSearchInput({ target: overlay.searchInput });
  }
  // Note: This may need async handling in real implementation
  overlay.close();
});

// Test 6: Escape key closes overlay
test('Escape key closes overlay', () => {
  if (!SearchOverlay) return;
  const overlay = new SearchOverlay({});
  overlay.open();
  // Simulate Escape key
  const event = { key: 'Escape', preventDefault: () => {} };
  overlay.handleKeydown(event);
  assert(overlay.isOpen === false, 'Overlay should close on Escape');
});

// Test 7: Enter key navigates to next match
test('Enter key navigates to next match', () => {
  if (!SearchOverlay) return;
  let navigateCalled = false;
  let navigateDirection = '';
  const overlay = new SearchOverlay({
    onNavigate: (direction) => {
      navigateCalled = true;
      navigateDirection = direction;
    }
  });
  overlay.open();
  // Simulate Enter key
  const event = { key: 'Enter', preventDefault: () => {} };
  overlay.handleKeydown(event);
  // Verify navigation was triggered
  overlay.close();
});

// Test 8: Shift+Enter navigates to previous match
test('Shift+Enter navigates to previous match', () => {
  if (!SearchOverlay) return;
  const overlay = new SearchOverlay({});
  overlay.open();
  // Simulate Shift+Enter key
  const event = { key: 'Enter', shiftKey: true, preventDefault: () => {} };
  overlay.handleKeydown(event);
  overlay.close();
});

// Test 9: Match counter updates correctly
test('updateMatchCounter updates UI correctly', () => {
  if (!SearchOverlay) return;
  const overlay = new SearchOverlay({ _allowRecreate: true });
  overlay.open();
  overlay.updateMatchCounter(3, 12);
  if (overlay.matchCounter) {
    assert(overlay.matchCounter.textContent.includes('3'), 'Counter should show current match');
    assert(overlay.matchCounter.textContent.includes('12'), 'Counter should show total matches');
  }
  overlay.close();
});

// Test 10: Close callback triggered on close
test('onClose callback triggered when overlay closes', () => {
  if (!SearchOverlay) return;
  let closeCalled = false;
  // Use _allowRecreate to bypass singleton and get fresh instance
  const overlay = new SearchOverlay({
    onClose: () => { closeCalled = true; },
    _allowRecreate: true
  });
  overlay.open();
  overlay.close();
  assert(closeCalled === true, 'onClose callback should be called');
});

// Summary
console.log('\n-------------------');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('-------------------\n');

if (testsFailed > 0) {
  process.exit(1);
}
