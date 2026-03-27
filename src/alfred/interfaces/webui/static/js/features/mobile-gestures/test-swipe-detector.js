/**
 * Tests for Swipe Detector
 *
 * Run with: node test-swipe-detector.js
 */

const { SwipeDetector } = require('./swipe-detector.js');

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

console.log('Running Swipe Detector Tests...\n');

// Test: SwipeDetector initializes
test('swipe detector initializes', () => {
  const detector = new SwipeDetector();
  assert(detector !== null, 'Detector should not be null');
  assert(detector.threshold === 100, 'Default threshold should be 100px');
});

// Test: Custom threshold
test('swipe detector accepts custom threshold', () => {
  const detector = new SwipeDetector({ threshold: 50 });
  assert(detector.threshold === 50, 'Threshold should be 50px');
});

// Test: Horizontal swipe detection (mock)
test('horizontal swipe detected with sufficient distance', () => {
  const detector = new SwipeDetector({ threshold: 100 });
  
  // Mock touch events
  const touchStart = { clientX: 100, clientY: 200 };
  const touchEnd = { clientX: 220, clientY: 205 }; // 120px right, 5px down
  
  detector._startX = touchStart.clientX;
  detector._startY = touchStart.clientY;
  
  const result = detector._calculateSwipe(touchEnd.clientX, touchEnd.clientY);
  
  assert(result.direction === 'right', `Expected direction 'right', got ${result.direction}`);
  assert(result.distance === 120, `Expected distance 120, got ${result.distance}`);
  assert(result.isValid === true, 'Should be valid swipe');
});

// Test: Vertical swipe ignored for horizontal detection
test('vertical swipe ignored for horizontal handler', () => {
  const detector = new SwipeDetector({ threshold: 100, direction: 'horizontal' });
  
  // Mock touch events - mostly vertical movement
  const touchStart = { clientX: 100, clientY: 200 };
  const touchEnd = { clientX: 105, clientY: 50 }; // 5px right, 150px up
  
  detector._startX = touchStart.clientX;
  detector._startY = touchStart.clientY;
  
  const result = detector._calculateSwipe(touchEnd.clientX, touchEnd.clientY);
  
  assert(result.direction === 'up', `Expected direction 'up', got ${result.direction}`);
  // Should still be detected, but caller can filter by direction
  assert(result.isVertical === true, 'Should be vertical swipe');
});

// Test: Under threshold
test('swipe under threshold is not valid', () => {
  const detector = new SwipeDetector({ threshold: 100 });
  
  const touchStart = { clientX: 100, clientY: 200 };
  const touchEnd = { clientX: 150, clientY: 200 }; // Only 50px right
  
  detector._startX = touchStart.clientX;
  detector._startY = touchStart.clientY;
  
  const result = detector._calculateSwipe(touchEnd.clientX, touchEnd.clientY);
  
  assert(result.isValid === false, 'Should not be valid (under threshold)');
  assert(result.distance === 50, `Expected distance 50, got ${result.distance}`);
});

// Test: Left swipe
test('left swipe detected', () => {
  const detector = new SwipeDetector({ threshold: 100 });
  
  const touchStart = { clientX: 300, clientY: 200 };
  const touchEnd = { clientX: 150, clientY: 200 }; // 150px left
  
  detector._startX = touchStart.clientX;
  detector._startY = touchStart.clientY;
  
  const result = detector._calculateSwipe(touchEnd.clientX, touchEnd.clientY);
  
  assert(result.direction === 'left', `Expected direction 'left', got ${result.direction}`);
  assert(result.isValid === true, 'Should be valid swipe');
});

// Test: Edge zone filtering
test('swipe in edge zone is ignored', () => {
  const detector = new SwipeDetector({ threshold: 100, edgeMargin: 40 });
  
  // Touch starts at x=30 (in left edge zone)
  const result = detector._shouldHandleTouch(30, 400);
  
  assert(result === false, 'Should ignore touch in edge zone');
});

// Test: Touch outside edge zone is handled
test('swipe outside edge zone is handled', () => {
  const detector = new SwipeDetector({ threshold: 100, edgeMargin: 40 });
  
  // Touch starts at x=100 (outside edge zone)
  const result = detector._shouldHandleTouch(100, 400);
  
  assert(result === true, 'Should handle touch outside edge zone');
});

// Summary
console.log('\n-------------------');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('-------------------');

process.exit(testsFailed > 0 ? 1 : 0);
