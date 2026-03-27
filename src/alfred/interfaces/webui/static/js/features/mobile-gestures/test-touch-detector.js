/**
 * Tests for Touch Detector
 *
 * Run with: node test-touch-detector.js
 */

const { isTouchDevice, isInEdgeZone } = require('./touch-detector.js');

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

console.log('Running Touch Detector Tests...\n');

// Test: detects touch device
test('detects touch device', () => {
  // Mock window.ontouchstart to simulate touch device
  global.window = { ontouchstart: null };
  global.navigator = { maxTouchPoints: 5 };

  const result = isTouchDevice();
  assert(result === true, `Expected true for touch device, got ${result}`);

  delete global.window;
  delete global.navigator;
});

// Test: detects mouse-only device
test('detects mouse device', () => {
  // Mock environment without touch support
  global.window = {};
  global.navigator = { maxTouchPoints: 0 };

  const result = isTouchDevice();
  assert(result === false, `Expected false for mouse device, got ${result}`);

  delete global.window;
  delete global.navigator;
});

// Test: edge zone detection - left edge
test('edge zone 40px left', () => {
  const result = isInEdgeZone(39, 400, 40);
  assert(result === true, `Expected true for x=39px, got ${result}`);
});

// Test: edge zone detection - right edge
test('edge zone 40px right', () => {
  const result = isInEdgeZone(361, 400, 40); // 400 - 39 = 361
  assert(result === true, `Expected true for x=361px on 400px screen, got ${result}`);
});

// Test: not in edge zone
test('not edge zone at 50px', () => {
  const result = isInEdgeZone(50, 400, 40);
  assert(result === false, `Expected false for x=50px, got ${result}`);
});

// Test: exactly at edge boundary (not in zone)
test('not edge zone at exactly 40px', () => {
  const result = isInEdgeZone(40, 400, 40);
  assert(result === false, `Expected false for x=40px (boundary), got ${result}`);
});

// Test: edge zone with custom margin
test('edge zone with custom 20px margin', () => {
  const result = isInEdgeZone(19, 400, 20);
  assert(result === true, `Expected true for x=19px with 20px margin, got ${result}`);
});

// Summary
console.log('\n-------------------');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('-------------------');

process.exit(testsFailed > 0 ? 1 : 0);
