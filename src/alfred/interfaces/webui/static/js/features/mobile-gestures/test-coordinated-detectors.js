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

// Test 11: Multi-gesture - independent gestures on different elements work simultaneously
test('multi-gesture - independent gestures on different elements', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const elementA = new MockHTMLElement();
  const elementB = new MockHTMLElement();

  let swipeTriggered = false;
  let longPressTriggered = false;

  const swipeDetector = new CoordinatedSwipeDetector(elementA, {
    onSwipe: () => { swipeTriggered = true; },
    threshold: 100
  });

  const longPressDetector = new CoordinatedLongPressDetector(elementB, {
    onLongPress: () => { longPressTriggered = true; },
    delay: 500
  });

  swipeDetector.attach();
  longPressDetector.attach();

  // Start touch on element A (swipe)
  elementA.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  });

  // Verify swipe is active
  assert(coordinator.isGestureActive('swipe'), 'Expected swipe gesture to be active');

  // End swipe gesture
  elementA.triggerEvent('touchend', {
    type: 'touchend',
    changedTouches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  });

  // Reset for second gesture
  coordinator.releaseGesture();

  // Start touch on element B (long-press)
  elementB.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 300, clientY: 200 }],
    preventDefault: () => {}
  });

  // Verify long-press is active
  assert(coordinator.isGestureActive('longpress'), 'Expected longpress gesture to be active');

  swipeDetector.destroy();
  longPressDetector.destroy();
});

// Test 12: Multi-gesture - long-press priority 3 preempts swipe priority 1
test('multi-gesture - long-press priority 3 preempts swipe priority 1', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  // First verify coordinator-level priority behavior
  // Request low priority gesture first
  const granted1 = coordinator.requestGesture('swipe', 1, { element: 'test1' });
  assert(granted1 === true, 'Expected low priority request to be granted');
  assert(coordinator.getActiveGesture().priority === 1, 'Expected priority 1 active');

  // Higher priority should preempt
  const granted2 = coordinator.requestGesture('longpress', 3, { element: 'test2' });
  assert(granted2 === true, 'Expected high priority to preempt low priority');
  assert(coordinator.isGestureActive('longpress'), 'Expected longpress to be active');
  assert(coordinator.getActiveGesture().priority === 3, 'Expected priority 3 for longpress');

  coordinator.releaseGesture();

  // Now test with coordinated detectors on same element
  const element = new MockHTMLElement();

  const swipeDetector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => {},
    threshold: 100
  });

  const longPressDetector = new CoordinatedLongPressDetector(element, {
    onLongPress: () => {},
    delay: 500
  });

  swipeDetector.attach();
  longPressDetector.attach();

  // With both attached, long-press (priority 3) should preempt swipe (priority 1)
  element.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  });

  // Verify long-press won due to higher priority
  assert(coordinator.isGestureActive('longpress'), 'Expected longpress to take precedence');
  assert(coordinator.getActiveGesture().priority === 3, 'Expected priority 3 active');
  assert(longPressDetector.isActive === true, 'Expected long-press detector to be active');

  swipeDetector.destroy();
  longPressDetector.destroy();
});

// Test 13: Multi-gesture - active gesture owns touch until touchend
test('multi-gesture - active gesture owns touch until touchend', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const element = new MockHTMLElement();

  const swipeDetector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => {},
    threshold: 100
  });

  swipeDetector.attach();

  // Start first touch
  element.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  });

  // Verify gesture is active
  assert(coordinator.isGestureActive(), 'Expected gesture to be active');
  assert(swipeDetector.isActive === true, 'Expected detector to be active');

  // Try to start another gesture with same priority while first is active (should be denied)
  // Using same priority (1) to test exclusivity, not preemption
  const granted = coordinator.requestGesture('pull', 1, { element });
  assert(granted === false, 'Expected same priority gesture to be denied while first is active');

  // But higher priority should still be able to preempt
  const grantedHigh = coordinator.requestGesture('longpress', 3, { element });
  assert(grantedHigh === true, 'Expected higher priority gesture to preempt');

  // End the gesture
  element.triggerEvent('touchend', {
    type: 'touchend',
    changedTouches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  });

  // Verify gesture is released
  assert(!coordinator.isGestureActive(), 'Expected no gesture after touchend');
  assert(swipeDetector.isActive === false, 'Expected detector to be inactive');

  swipeDetector.destroy();
});

// Test 14: Multi-gesture - gesture priority respected in coordinator
test('multi-gesture - gesture priority respected in coordinator', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  // Request low priority gesture first (should succeed)
  const granted1 = coordinator.requestGesture('swipe', 1, { element: 'test1' });
  assert(granted1 === true, 'Expected low priority request to be granted');

  // Try to request same priority (should fail - already active)
  const granted2 = coordinator.requestGesture('pull', 1, { element: 'test2' });
  assert(granted2 === false, 'Expected same priority request to be denied');

  // Release and test higher priority
  coordinator.releaseGesture();

  // Request low priority again
  const granted3 = coordinator.requestGesture('swipe', 1, { element: 'test3' });
  assert(granted3 === true, 'Expected low priority to be granted after release');

  // Higher priority should preempt
  const granted4 = coordinator.requestGesture('longpress', 3, { element: 'test4' });
  assert(granted4 === true, 'Expected high priority to preempt low priority');

  const activeGesture = coordinator.getActiveGesture();
  assert(activeGesture.type === 'longpress', 'Expected longpress to be active');
  assert(activeGesture.priority === 3, 'Expected priority 3 to be active');

  coordinator.releaseGesture();
});

// Test 15: Multi-gesture - detector cleanup releases lock properly
test('multi-gesture - detector destroy releases gesture lock', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const element = new MockHTMLElement();

  const detector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => {},
    threshold: 100
  });

  detector.attach();

  // Start gesture
  element.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  });

  assert(coordinator.isGestureActive(), 'Expected gesture to be active');

  // Destroy detector (should release lock)
  detector.destroy();

  // Verify gesture lock was released
  assert(!coordinator.isGestureActive(), 'Expected gesture lock to be released after destroy');
});

// Test 16: Multi-gesture - touchcancel releases lock like touchend
test('multi-gesture - touchcancel releases gesture lock', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset

  const element = new MockHTMLElement();

  const detector = new CoordinatedSwipeDetector(element, {
    onSwipe: () => {},
    threshold: 100
  });

  detector.attach();

  // Start gesture
  element.triggerEvent('touchstart', {
    type: 'touchstart',
    touches: [{ clientX: 100, clientY: 200 }],
    preventDefault: () => {}
  });

  assert(coordinator.isGestureActive(), 'Expected gesture to be active');

  // Cancel gesture (should release lock)
  element.triggerEvent('touchcancel', {
    type: 'touchcancel',
    preventDefault: () => {}
  });

  // Verify gesture lock was released
  assert(!coordinator.isGestureActive(), 'Expected gesture lock to be released after touchcancel');
  assert(detector.isActive === false, 'Expected detector to be inactive');

  detector.destroy();
});

// Summary
console.log('\n-------------------');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('-------------------');

process.exit(testsFailed > 0 ? 1 : 0);
