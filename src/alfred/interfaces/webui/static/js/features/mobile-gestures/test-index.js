/**
 * Tests for Mobile Gestures Index Module
 *
 * Run with: node test-index.js
 */

const MobileGestures = require('./index.js');

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

console.log('Running Mobile Gestures Index Tests...\n');

// Test: Module exports exist
test('exports GESTURE_CONFIG', () => {
  assert(MobileGestures.GESTURE_CONFIG !== undefined, 'GESTURE_CONFIG should be exported');
  assert(MobileGestures.GESTURE_CONFIG.SWIPE_THRESHOLD === 100, 'SWIPE_THRESHOLD should be 100');
  assert(MobileGestures.GESTURE_CONFIG.EDGE_MARGIN === 40, 'EDGE_MARGIN should be 40');
});

// Test: Device detection functions exported
test('exports isTouchDevice', () => {
  assert(typeof MobileGestures.isTouchDevice === 'function', 'isTouchDevice should be a function');
});

test('exports isInEdgeZone', () => {
  assert(typeof MobileGestures.isInEdgeZone === 'function', 'isInEdgeZone should be a function');
});

test('exports shouldHandleTouch', () => {
  assert(typeof MobileGestures.shouldHandleTouch === 'function', 'shouldHandleTouch should be a function');
});

test('exports shouldEnableGestures', () => {
  assert(typeof MobileGestures.shouldEnableGestures === 'function', 'shouldEnableGestures should be a function');
});

// Test: SwipeDetector exported
test('exports SwipeDetector', () => {
  assert(typeof MobileGestures.SwipeDetector === 'function', 'SwipeDetector should be a class/function');
});

// Test: Initialization function exported
test('exports initializeGestures', () => {
  assert(typeof MobileGestures.initializeGestures === 'function', 'initializeGestures should be a function');
});

// Test: shouldEnableGestures returns false for non-touch device
test('shouldEnableGestures returns false on non-touch device', () => {
  // Mock non-touch environment
  global.window = {};
  global.navigator = { maxTouchPoints: 0 };

  const result = MobileGestures.shouldEnableGestures(null, 100);
  assert(result === false, 'Should return false for non-touch device');

  delete global.window;
  delete global.navigator;
});

// Test: shouldEnableGestures returns false in edge zone
test('shouldEnableGestures returns false in edge zone', () => {
  // Mock touch environment
  global.window = { innerWidth: 400 };
  global.navigator = { maxTouchPoints: 5 };

  // Touch at x=30 (in left edge zone)
  const mockElement = { matches: () => false, closest: () => null };
  const result = MobileGestures.shouldEnableGestures(mockElement, 30);
  assert(result === false, 'Should return false for touch in edge zone');

  delete global.window;
  delete global.navigator;
});

// Test: shouldEnableGestures returns true for valid touch
test('shouldEnableGestures returns true for valid touch', () => {
  // Mock touch environment
  global.window = { innerWidth: 400 };
  global.navigator = { maxTouchPoints: 5 };
  global.Element = function() {};

  // Touch at x=100 (outside edge zone)
  const mockElement = { matches: () => false, closest: () => null };
  Object.setPrototypeOf(mockElement, global.Element.prototype);

  const result = MobileGestures.shouldEnableGestures(mockElement, 100);
  assert(result === true, 'Should return true for valid touch outside edge zone');

  delete global.window;
  delete global.navigator;
  delete global.Element;
});

// Summary
console.log('\n-------------------');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('-------------------');

process.exit(testsFailed > 0 ? 1 : 0);
