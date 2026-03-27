/**
 * Tests for Long Press Detector
 *
 * Run with: node test-long-press-detector.js
 *
 * Phase 3: Touch Gesture Support - Long Press Context Menu
 * - Detects long press gestures (>500ms)
 * - Distinguishes from swipe (movement tolerance)
 * - Visual feedback during press (scale/opacity)
 * - Haptic feedback support
 * - Touch gesture conflict resolution with SwipeDetector
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
    this._parent = null;
  }
  matches() { return true; }
  closest() { return null; }
  querySelector() { return null; }
  addEventListener() {}
  removeEventListener() {}
};

global.document = {
  createElement(tag) {
    return new global.HTMLElement();
  }
};

global.window = {
  innerWidth: 400,
  addEventListener: () => {},
  removeEventListener: () => {},
};

global.navigator = {
  vibrate: () => {}
};

global.setTimeout = setTimeout;
global.clearTimeout = clearTimeout;
global.Date = Date;

const { LongPressDetector } = require('./long-press-detector.js');

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
function createMockElement(id = 'el-1') {
  const el = new HTMLElement();
  el.id = id;
  return el;
}

// Mock TouchEvent
createMockTouchEvent = (x, y) => ({
  touches: [{ clientX: x, clientY: y }],
  target: createMockElement(),
  preventDefault: () => {},
  stopPropagation: () => {},
});

console.log('Running Long Press Detector Tests...\n');

// Test 1: Module exports correctly
test('long_press_module_exports', () => {
  assert(typeof LongPressDetector === 'function', 'LongPressDetector should be a constructor function');
});

// Test 2: Initialize with default options
test('long_press_initializes_with_defaults', () => {
  const detector = new LongPressDetector();
  assert(detector !== null, 'Should create instance');
  assert(detector.threshold === 500, 'Default threshold should be 500ms');
  assert(detector.movementTolerance === 10, 'Default movement tolerance should be 10px');
  assert(typeof detector.onLongPress === 'function', 'Should have onLongPress callback');
  assert(typeof detector.onPressStart === 'function', 'Should have onPressStart callback');
  assert(typeof detector.onPressCancel === 'function', 'Should have onPressCancel callback');
  assert(detector.enableHaptic === true, 'Haptic should be enabled by default');
  assert(detector.enableVisualFeedback === true, 'Visual feedback should be enabled by default');
});

// Test 3: Initialize with custom options
test('long_press_accepts_custom_options', () => {
  const customLongPress = () => {};
  const customStart = () => {};
  const customCancel = () => {};
  
  const detector = new LongPressDetector({
    threshold: 800,
    movementTolerance: 15,
    onLongPress: customLongPress,
    onPressStart: customStart,
    onPressCancel: customCancel,
    enableHaptic: false,
    enableVisualFeedback: false,
  });
  
  assert(detector.threshold === 800, 'Custom threshold should be 800ms');
  assert(detector.movementTolerance === 15, 'Custom tolerance should be 15px');
  assert(detector.onLongPress === customLongPress, 'Custom onLongPress should be set');
  assert(detector.onPressStart === customStart, 'Custom onPressStart should be set');
  assert(detector.onPressCancel === customCancel, 'Custom onPressCancel should be set');
  assert(detector.enableHaptic === false, 'Haptic should be disabled');
  assert(detector.enableVisualFeedback === false, 'Visual feedback should be disabled');
});

// Test 4: Attach to element
test('attach_to_element', () => {
  const detector = new LongPressDetector();
  const element = createMockElement();
  
  const result = detector.attachToElement(element);
  
  assert(result === true, 'Should return true on success');
  assert(detector._element === element, 'Should store element reference');
});

// Test 5: Attach returns false for invalid element
test('attach_returns_false_for_invalid_element', () => {
  const detector = new LongPressDetector();
  
  const result = detector.attachToElement(null);
  
  assert(result === false, 'Should return false for null element');
  
  const result2 = detector.attachToElement('not-an-element');
  assert(result2 === false, 'Should return false for non-element');
});

// Test 6: Press start state tracking
test('press_start_tracks_state', () => {
  const detector = new LongPressDetector();
  const element = createMockElement();
  detector.attachToElement(element);
  
  const event = createMockTouchEvent(100, 100);
  detector._handleTouchStart(event);
  
  assert(detector._isPressing === true, 'Should set pressing flag');
  assert(detector._startX === 100, 'Should store start X');
  assert(detector._startY === 100, 'Should store start Y');
  assert(detector._startTime > 0, 'Should store start time');
});

// Test 7: Movement calculation
test('movement_calculation', () => {
  const detector = new LongPressDetector();
  const element = createMockElement();
  detector.attachToElement(element);
  
  // Start at (100, 100)
  detector._startX = 100;
  detector._startY = 100;
  
  // Move to (105, 110)
  const distance = detector._calculateMovement(105, 110);
  
  assert(Math.abs(distance - 11.18) < 0.1, 'Should calculate Euclidean distance correctly');
});

// Test 8: Press cancels if movement exceeds tolerance
test('press_cancels_on_excessive_movement', () => {
  let cancelCalled = false;
  
  const detector = new LongPressDetector({
    movementTolerance: 10,
    onPressCancel: () => { cancelCalled = true; }
  });
  
  const element = createMockElement();
  detector.attachToElement(element);
  
  // Start press
  const startEvent = createMockTouchEvent(100, 100);
  detector._handleTouchStart(startEvent);
  
  // Move beyond tolerance (15px away)
  const moveEvent = createMockTouchEvent(115, 100);
  detector._handleTouchMove(moveEvent);
  
  assert(detector._isPressing === false, 'Should cancel press on excessive movement');
  assert(cancelCalled === true, 'Should call onPressCancel callback');
});

// Test 9: Press continues if movement within tolerance
test('press_continues_within_tolerance', () => {
  let cancelCalled = false;
  
  const detector = new LongPressDetector({
    movementTolerance: 10,
    onPressCancel: () => { cancelCalled = true; }
  });
  
  const element = createMockElement();
  detector.attachToElement(element);
  
  // Start press
  const startEvent = createMockTouchEvent(100, 100);
  detector._handleTouchStart(startEvent);
  
  // Move within tolerance (5px away)
  const moveEvent = createMockTouchEvent(105, 100);
  detector._handleTouchMove(moveEvent);
  
  assert(detector._isPressing === true, 'Should continue press within tolerance');
  assert(cancelCalled === false, 'Should not call onPressCancel');
});

// Test 10: Visual feedback applied during press
test('visual_feedback_applied_during_press', () => {
  const detector = new LongPressDetector({ enableVisualFeedback: true });
  const element = createMockElement();
  detector.attachToElement(element);
  
  // Start press
  const startEvent = createMockTouchEvent(100, 100);
  detector._handleTouchStart(startEvent);
  
  // Simulate visual feedback (typically called at 200ms via setTimeout)
  detector._applyVisualFeedback(element);
  
  assert(element.style.transform !== undefined, 'Transform should be set');
  assert(element.style.transition !== undefined, 'Transition should be set');
});

// Test 11: Haptic feedback triggered at visual feedback point
test('haptic_triggered_at_feedback_point', () => {
  let hapticCalled = false;
  
  const originalVibrate = navigator.vibrate;
  navigator.vibrate = () => { hapticCalled = true; };
  
  const detector = new LongPressDetector({ enableHaptic: true });
  const element = createMockElement();
  detector.attachToElement(element);
  
  // Trigger haptic manually (normally called via setTimeout at 200ms)
  detector._triggerHaptic();
  
  assert(hapticCalled === true, 'Haptic feedback should be triggered');
  
  navigator.vibrate = originalVibrate;
});

// Test 12: Long press triggers after threshold
test('long_press_triggers_after_threshold', () => {
  let longPressCalled = false;
  let longPressElement = null;
  
  const detector = new LongPressDetector({
    threshold: 500,
    onLongPress: (el) => {
      longPressCalled = true;
      longPressElement = el;
    }
  });
  
  const element = createMockElement();
  detector.attachToElement(element);
  
  // Start press 600ms ago
  detector._isPressing = true;
  detector._startX = 100;
  detector._startY = 100;
  detector._startTime = Date.now() - 600;
  detector._element = element;
  
  // End press
  const endEvent = createMockTouchEvent(100, 100);
  detector._handleTouchEnd(endEvent);
  
  assert(longPressCalled === true, 'onLongPress should be called');
  assert(longPressElement === element, 'Should pass element to callback');
});

// Test 13: Short press does not trigger long press
test('short_press_does_not_trigger_long_press', () => {
  let longPressCalled = false;
  
  const detector = new LongPressDetector({
    threshold: 500,
    onLongPress: () => { longPressCalled = true; }
  });
  
  const element = createMockElement();
  detector.attachToElement(element);
  
  // Start press 300ms ago (below threshold)
  detector._isPressing = true;
  detector._startX = 100;
  detector._startY = 100;
  detector._startTime = Date.now() - 300;
  detector._element = element;
  
  // End press
  const endEvent = createMockTouchEvent(100, 100);
  detector._handleTouchEnd(endEvent);
  
  assert(longPressCalled === false, 'onLongPress should not be called for short press');
});

// Test 14: Visual state resets on cancel
test('visual_state_resets_on_cancel', () => {
  const detector = new LongPressDetector();
  const element = createMockElement();
  detector.attachToElement(element);
  
  // Apply some visual state
  element.style.transform = 'scale(0.98)';
  element.style.opacity = '0.9';
  
  detector._resetVisualState(element);
  
  assert(element.style.transform === '', 'Transform should be reset');
  assert(element.style.opacity === '', 'Opacity should be reset');
});

// Test 15: Destroy cleans up state and timers
test('destroy_cleans_up_state', () => {
  const detector = new LongPressDetector();
  const element = createMockElement();
  detector.attachToElement(element);
  
  // Simulate active press
  detector._isPressing = true;
  detector._visualFeedbackTimer = setTimeout(() => {}, 1000);
  detector._longPressTimer = setTimeout(() => {}, 1000);
  
  detector.destroy();
  
  assert(detector._element === null, 'Element should be null');
  assert(detector._isPressing === false, 'Pressing flag should be false');
  assert(detector._visualFeedbackTimer === null, 'Visual feedback timer should be cleared');
  assert(detector._longPressTimer === null, 'Long press timer should be cleared');
});

// Test 16: Multiple elements can have separate detectors
test('multiple_detectors_independent', () => {
  const detector1 = new LongPressDetector();
  const detector2 = new LongPressDetector();
  
  const element1 = createMockElement('el-1');
  const element2 = createMockElement('el-2');
  
  detector1.attachToElement(element1);
  detector2.attachToElement(element2);
  
  // Start press on element 1
  detector1._handleTouchStart(createMockTouchEvent(100, 100));
  
  assert(detector1._isPressing === true, 'Detector 1 should be pressing');
  assert(detector2._isPressing === false, 'Detector 2 should not be pressing');
});

// Summary
console.log('\n-------------------');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('-------------------');

process.exit(testsFailed > 0 ? 1 : 0);
