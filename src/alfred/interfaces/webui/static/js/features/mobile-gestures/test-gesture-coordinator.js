/**
 * Tests for GestureCoordinator
 *
 * Run with: node test-gesture-coordinator.js
 */

const { GestureCoordinator } = require('./gesture-coordinator.js');

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

console.log('\nRunning GestureCoordinator Tests...\n');

// Test 1: Singleton pattern
test('coordinator singleton pattern', () => {
  const coord1 = GestureCoordinator.getInstance();
  const coord2 = GestureCoordinator.getInstance();
  
  assert(coord1 === coord2, 'Expected same instance for singleton');
  assert(coord1 instanceof GestureCoordinator, 'Expected GestureCoordinator instance');
});

// Test 2: Request gesture grants lock when available
test('requestGesture grants lock when available', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset state
  
  const granted = coordinator.requestGesture('swipe', 1);
  
  assert(granted === true, 'Expected gesture lock to be granted');
  assert(coordinator.isGestureActive('swipe'), 'Expected swipe to be active');
  assert(coordinator.getActiveGesture().type === 'swipe', 'Expected active gesture type to be swipe');
  
  coordinator.releaseGesture(); // Cleanup
});

// Test 3: Request gesture denies when busy (same or lower priority)
test('requestGesture denies when another gesture is active', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset state
  
  // First gesture gets lock
  const firstGranted = coordinator.requestGesture('swipe', 2);
  assert(firstGranted === true, 'Expected first gesture to be granted');
  
  // Second gesture with same priority should be denied
  const secondGranted = coordinator.requestGesture('longpress', 2);
  assert(secondGranted === false, 'Expected second gesture with same priority to be denied when busy');
  
  // First gesture should still be active
  assert(coordinator.isGestureActive('swipe'), 'Expected swipe to still be active');
  assert(!coordinator.isGestureActive('longpress'), 'Expected longpress to not be active');
  
  coordinator.releaseGesture(); // Cleanup
});

// Test 4: Release gesture clears lock
test('releaseGesture clears active lock', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset state
  
  coordinator.requestGesture('swipe', 1);
  assert(coordinator.isGestureActive('swipe'), 'Expected gesture to be active before release');
  
  coordinator.releaseGesture();
  
  assert(!coordinator.isGestureActive('swipe'), 'Expected gesture to be inactive after release');
  assert(coordinator.getActiveGesture() === null, 'Expected no active gesture after release');
});

// Test 5: Higher priority can preempt lower priority
test('higher priority gesture can preempt lower priority', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset state
  
  // Low priority gesture gets lock
  const lowPriorityGranted = coordinator.requestGesture('pull', 1);
  assert(lowPriorityGranted === true, 'Expected low priority gesture to be granted');
  
  // High priority gesture should preempt
  const highPriorityGranted = coordinator.requestGesture('longpress', 3);
  assert(highPriorityGranted === true, 'Expected high priority to preempt low priority');
  
  // Longpress should now be active, pull should not
  assert(coordinator.isGestureActive('longpress'), 'Expected longpress to be active after preempt');
  assert(!coordinator.isGestureActive('pull'), 'Expected pull to be inactive after preempt');
  
  coordinator.releaseGesture(); // Cleanup
});

// Test 6: Equal priority cannot preempt
test('equal priority gesture cannot preempt', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset state
  
  // First gesture gets lock
  const firstGranted = coordinator.requestGesture('swipe', 2);
  assert(firstGranted === true, 'Expected first gesture to be granted');
  
  // Equal priority gesture should be denied
  const secondGranted = coordinator.requestGesture('pull', 2);
  assert(secondGranted === false, 'Expected equal priority gesture to be denied');
  
  // First gesture should still be active
  assert(coordinator.isGestureActive('swipe'), 'Expected swipe to still be active');
  
  coordinator.releaseGesture(); // Cleanup
});

// Test 7: getActiveGesture returns full gesture info
test('getActiveGesture returns complete gesture information', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset state
  
  const mockElement = { id: 'test-element' };
  coordinator.requestGesture('swipe', 2, { element: mockElement });
  
  const active = coordinator.getActiveGesture();
  
  assert(active !== null, 'Expected active gesture to not be null');
  assert(active.type === 'swipe', 'Expected type to be swipe');
  assert(active.priority === 2, 'Expected priority to be 2');
  assert(active.element === mockElement, 'Expected element to match');
  assert(typeof active.startTime === 'number', 'Expected startTime to be a number');
  assert(active.startTime > 0, 'Expected startTime to be positive');
  
  coordinator.releaseGesture(); // Cleanup
});

// Test 8: isGestureActive with no argument checks any gesture
test('isGestureActive checks any active gesture when no type specified', () => {
  const coordinator = GestureCoordinator.getInstance();
  coordinator.releaseGesture(); // Reset state
  
  assert(coordinator.isGestureActive() === false, 'Expected false when no gesture active');
  
  coordinator.requestGesture('swipe', 1);
  assert(coordinator.isGestureActive() === true, 'Expected true when any gesture active');
  
  coordinator.releaseGesture();
  assert(coordinator.isGestureActive() === false, 'Expected false after release');
});

// Summary
console.log('\n-------------------');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('-------------------');

process.exit(testsFailed > 0 ? 1 : 0);
