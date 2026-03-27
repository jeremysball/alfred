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

// Test 4: Axis locking - horizontal lock triggers at 15px X with minimal Y
test('axis locking - horizontal lock triggers at 15px X with minimal Y', () => {
  const element = new MockHTMLElement();
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const detector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => {},
    threshold: 100
  });

  detector.attach();

  // Simulate touchstart at (100, 200)
  element.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  });

  // Simulate touchmove with 20px X, 5px Y (should lock horizontal)
  element.triggerEvent('touchmove', {
    type: 'touchmove',
    touches: [{ clientX: 120, clientY: 205 }],
    preventDefault: () => {}
  });

  // Check that axis is locked to horizontal
  assert(detector.axisLock === 'horizontal', 'Expected axisLock to be horizontal');

  detector.destroy();
});

// Test 5: Axis locking - vertical lock triggers at 15px Y with minimal X
test('axis locking - vertical lock triggers at 15px Y with minimal X', () => {
  const element = new MockHTMLElement();
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const detector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => {},
    threshold: 100
  });

  detector.attach();

  // Simulate touchstart at (100, 200)
  element.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  });

  // Simulate touchmove with 5px X, 20px Y (should lock vertical)
  element.triggerEvent('touchmove', {
    type: 'touchmove',
    touches: [{ clientX: 105, clientY: 220 }],
    preventDefault: () => {}
  });

  // Check that axis is locked to vertical
  assert(detector.axisLock === 'vertical', 'Expected axisLock to be vertical');

  detector.destroy();
});

// Test 6: Axis locking - neutral state below 15px threshold
test('axis locking - neutral state below 15px threshold', () => {
  const element = new MockHTMLElement();
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const detector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => {},
    threshold: 100
  });

  detector.attach();

  // Simulate touchstart at (100, 200)
  element.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  });

  // Simulate touchmove with 10px X, 8px Y (below threshold, should stay neutral)
  element.triggerEvent('touchmove', {
    type: 'touchmove',
    touches: [{ clientX: 110, clientY: 208 }],
    preventDefault: () => {}
  });

  // Check that axis is still neutral
  assert(detector.axisLock === null, 'Expected axisLock to be null (neutral)');

  detector.destroy();
});

// Test 7: Axis locking - cannot switch axis after lock established
test('axis locking - cannot switch axis after lock established', () => {
  const element = new MockHTMLElement();
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const detector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => {},
    threshold: 100
  });

  detector.attach();

  // Simulate touchstart at (100, 200)
  element.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  });

  // First movement locks horizontal (20px X, 5px Y)
  element.triggerEvent('touchmove', {
    type: 'touchmove',
    touches: [{ clientX: 120, clientY: 205 }],
    preventDefault: () => {}
  });

  assert(detector.axisLock === 'horizontal', 'Expected initial lock to be horizontal');

  // Second movement tries to switch to vertical (5px more X, 30px Y)
  // This should NOT switch the lock
  element.triggerEvent('touchmove', {
    type: 'touchmove',
    touches: [{ clientX: 125, clientY: 235 }],
    preventDefault: () => {}
  });

  // Check that axis is still horizontal (lock persisted)
  assert(detector.axisLock === 'horizontal', 'Expected axisLock to remain horizontal after attempted switch');

  detector.destroy();
});

// Test 8: Edge zone handling - left edge touch does not request lock
test('edge zone handling - left edge touch does not request lock', () => {
  // Mock window.innerWidth for the test
  const originalInnerWidth = global.window.innerWidth;
  global.window.innerWidth = 400; // Simulate 400px wide viewport

  const element = new MockHTMLElement();
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const detector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => {},
    threshold: 100
  });

  detector.attach();

  // Simulate touchstart at x=20px (within 40px left edge zone)
  element.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 20, clientY: 200 }],
    preventDefault: () => {}
  });

  // Check that NO gesture lock was requested
  assert(!coordinator.isGestureActive(), 'Expected no gesture lock for left edge touch');

  detector.destroy();

  // Restore window.innerWidth
  global.window.innerWidth = originalInnerWidth;
});

// Test 9: Edge zone handling - right edge touch does not request lock
test('edge zone handling - right edge touch does not request lock', () => {
  // Mock window.innerWidth for the test
  const originalInnerWidth = global.window.innerWidth;
  global.window.innerWidth = 400; // Simulate 400px wide viewport

  const element = new MockHTMLElement();
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const detector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => {},
    threshold: 100
  });

  detector.attach();

  // Simulate touchstart at x=380px (within 40px of right edge: 400-380=20px)
  element.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 380, clientY: 200 }],
    preventDefault: () => {}
  });

  // Check that NO gesture lock was requested
  assert(!coordinator.isGestureActive(), 'Expected no gesture lock for right edge touch');

  detector.destroy();

  // Restore window.innerWidth
  global.window.innerWidth = originalInnerWidth;
});

// Test 10: Edge zone handling - safe zone touch requests lock normally
test('edge zone handling - safe zone touch requests lock normally', () => {
  // Mock window.innerWidth for the test
  const originalInnerWidth = global.window.innerWidth;
  global.window.innerWidth = 400; // Simulate 400px wide viewport

  const element = new MockHTMLElement();
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const detector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => {},
    threshold: 100
  });

  detector.attach();

  // Simulate touchstart at x=200px (middle of screen, safe zone)
  element.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 200, clientY: 200 }],
    preventDefault: () => {}
  });

  // Check that gesture lock WAS requested
  assert(coordinator.isGestureActive(), 'Expected gesture lock for safe zone touch');
  assert(coordinator.isGestureActive('swipe'), 'Expected swipe gesture to be active');

  detector.destroy();

  // Restore window.innerWidth
  global.window.innerWidth = originalInnerWidth;
});

// Summary
console.log('\n-------------------');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('-------------------');

process.exit(testsFailed > 0 ? 1 : 0);
