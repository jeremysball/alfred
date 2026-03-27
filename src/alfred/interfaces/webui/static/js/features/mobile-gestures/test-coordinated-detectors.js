/**
 * Tests for Coordinated Detector Wrappers
 *
 * Run with: node test-coordinated-detectors.js
 */

const { CoordinatedSwipeDetector, CoordinatedLongPressDetector } = require('./coordinated-detectors.js');
const { GestureCoordinator } = require('./gesture-coordinator.js');

// Minimal DOM-like globals for Node.js testing
class MockHTMLElement {
  constructor(tagName = 'div') {
    this.tagName = tagName;
    this._listeners = {};
    this._attributes = {};
    this.style = {};
  }

  addEventListener(type, handler, options) {
    if (!this._listeners[type]) {
      this._listeners[type] = [];
    }
    this._listeners[type].push({ handler, options });
  }

  removeEventListener(type, handler) {
    if (this._listeners[type]) {
      this._listeners[type] = this._listeners[type].filter(
        l => l.handler !== handler
      );
    }
  }

  // Helper to trigger all listeners for an event type
  triggerEvent(type, event) {
    if (this._listeners[type]) {
      this._listeners[type].forEach(l => l.handler(event));
    }
  }

  setAttribute(key, value) {
    this._attributes[key] = String(value);
  }

  getAttribute(key) {
    return this._attributes[key] || null;
  }
}

// Mock window object
global.window = {
  addEventListener: () => {},
  removeEventListener: () => {}
};

global.HTMLElement = MockHTMLElement;

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

console.log('\nRunning Coordinated Detector Tests...\n');

// Test 1: CoordinatedSwipeDetector creates wrapped detector
test('CoordinatedSwipeDetector creates wrapped detector', () => {
  const element = new MockHTMLElement();
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const detector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => {},
    threshold: 100
  });

  assert(detector.wrappedDetector !== null, 'Expected wrapped detector to be created');
  assert(detector.coordinator === coordinator, 'Expected coordinator to be GestureCoordinator instance');
});

// Test 2: CoordinatedSwipeDetector requests lock on touchstart
test('CoordinatedSwipeDetector requests lock on touchstart', () => {
  const element = new MockHTMLElement();
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  let swipeCalled = false;
  const detector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => { swipeCalled = true; },
    threshold: 100
  });

  detector.attach();

  // Simulate touchstart
  const touchStartEvent = {
    type: 'touchstart',
    touches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  };

  // Trigger the event on the element
  element.triggerEvent('touchstart', touchStartEvent);

  // Check that gesture was requested (coordinator should have active gesture)
  assert(coordinator.isGestureActive(), 'Expected gesture to be active after touchstart');
  assert(coordinator.isGestureActive('swipe'), 'Expected swipe gesture to be active');

  detector.destroy();
});

// Test 3: CoordinatedLongPressDetector uses priority 3
test('CoordinatedLongPressDetector uses priority 3', () => {
  const element = new MockHTMLElement();
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const detector = new CoordinatedLongPressDetector(element, {
    onLongPress: () => {},
    delay: 500
  });

  detector.attach();

  // Simulate touchstart
  const touchStartEvent = {
    type: 'touchstart',
    touches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  };

  // Trigger the event on the element
  element.triggerEvent('touchstart', touchStartEvent);

  // Check that longpress is active
  assert(coordinator.isGestureActive('longpress'), 'Expected longpress gesture to be active');

  // Verify priority by checking if it can preempt a lower priority gesture
  const activeGesture = coordinator.getActiveGesture();
  assert(activeGesture !== null, 'Expected active gesture info');
  assert(activeGesture.priority === 3, 'Expected priority 3 for longpress');

  detector.destroy();
});

// Summary
console.log('\n-------------------');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('-------------------');

process.exit(testsFailed > 0 ? 1 : 0);
