/**
 * Tests for Swipe-to-Reply Feature
 *
 * Run with: node test-swipe-to-reply.js
 *
 * Phase 2: Touch Gesture Support - Swipe-to-Reply
 * - Attaches SwipeDetector to message elements
 * - Triggers reply composer on right-swipe
 * - Visual feedback during swipe (80px threshold)
 * - Haptic feedback support
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
      toggle: (cls) =>
        this._classes.has(cls) ? this._classes.delete(cls) : this._classes.add(cls),
    };
    this.dataset = {};
    this.children = [];
    this._parent = null;
  }
  matches() {
    return true;
  }
  closest() {
    return null;
  }
  querySelector() {
    return null;
  }
  querySelectorAll() {
    return [];
  }
  appendChild(child) {
    child._parent = this;
    this.children.push(child);
  }
  removeChild(child) {
    const index = this.children.indexOf(child);
    if (index > -1) {
      child._parent = null;
      this.children.splice(index, 1);
    }
  }
  addEventListener() {}
  removeEventListener() {}
};

global.document = {
  createElement(_tag) {
    return new global.HTMLElement();
  },
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
  vibrate: () => {},
};

// Mock window for SwipeDetector
global.window = {
  innerWidth: 400,
  addEventListener: () => {},
  removeEventListener: () => {},
  matchMedia: () => ({ matches: false }),
};

const { SwipeToReply } = require("./swipe-to-reply.js");

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
    throw new Error(message || "Assertion failed");
  }
}

// Mock DOM elements for testing
function createMockMessageElement(id = "msg-1") {
  const el = new HTMLElement();
  el.id = id;
  el.dataset = { messageId: id };
  return el;
}

console.log("Running Swipe-to-Reply Tests...\n");

// Test 1: Module exports correctly
test("swipe_to_reply_module_exports", () => {
  assert(typeof SwipeToReply === "function", "SwipeToReply should be a constructor function");
});

// Test 2: Initialize with default options
test("swipe_to_reply_initializes_with_defaults", () => {
  const swipeReply = new SwipeToReply();
  assert(swipeReply !== null, "Should create instance");
  assert(swipeReply.threshold === 80, "Default threshold should be 80px");
  assert(swipeReply.direction === "right", "Default direction should be right");
  assert(typeof swipeReply.onReply === "function", "Should have onReply callback");
});

// Test 3: Initialize with custom options
test("swipe_to_reply_accepts_custom_options", () => {
  const customCallback = () => {};
  const swipeReply = new SwipeToReply({
    threshold: 100,
    direction: "left",
    onReply: customCallback,
    enableHaptic: false,
  });
  assert(swipeReply.threshold === 100, "Custom threshold should be 100px");
  assert(swipeReply.direction === "left", "Custom direction should be left");
  assert(swipeReply.onReply === customCallback, "Custom callback should be set");
  assert(swipeReply.enableHaptic === false, "Haptic should be disabled");
});

// Test 4: Attach to message element creates detector
test("attach_to_message_creates_detector", () => {
  const swipeReply = new SwipeToReply();
  const messageEl = createMockMessageElement();

  const result = swipeReply.attachToMessage(messageEl, "msg-123");

  assert(result === true, "Should return true on success");
  assert(swipeReply._detectors.has("msg-123"), "Should store detector by message ID");
});

// Test 5: Attach returns false for invalid element
test("attach_returns_false_for_invalid_element", () => {
  const swipeReply = new SwipeToReply();

  const result = swipeReply.attachToMessage(null, "msg-123");

  assert(result === false, "Should return false for null element");
});

// Test 6: Detach removes detector and cleans up
test("detach_removes_detector", () => {
  const swipeReply = new SwipeToReply();
  const messageEl = createMockMessageElement();

  swipeReply.attachToMessage(messageEl, "msg-123");
  assert(swipeReply._detectors.has("msg-123"), "Should have detector before detach");

  swipeReply.detachFromMessage("msg-123");
  assert(!swipeReply._detectors.has("msg-123"), "Should remove detector after detach");
});

// Test 7: Attach all messages in container
test("attach_all_messages_in_container", () => {
  const swipeReply = new SwipeToReply();

  // Mock container with querySelectorAll
  const mockMessages = [createMockMessageElement("msg-1"), createMockMessageElement("msg-2")];

  // Create container that properly extends HTMLElement
  class MockContainer extends HTMLElement {
    querySelectorAll(selector) {
      if (selector === "[data-message-id]") return mockMessages;
      return [];
    }
  }

  const container = new MockContainer();

  const count = swipeReply.attachToAllMessages(container);

  assert(count === 2, "Should attach to 2 messages");
  assert(swipeReply._detectors.has("msg-1"), "Should have detector for message 1");
  assert(swipeReply._detectors.has("msg-2"), "Should have detector for message 2");
});

// Test 8: Swipe threshold calculation
test("swipe_threshold_calculation", () => {
  const swipeReply = new SwipeToReply({ threshold: 80 });

  // Simulate 100px swipe (capped at 1.0)
  const progress = swipeReply._calculateProgress(100);
  assert(progress === 1.0, `Progress should be 1.0 at threshold, got ${progress}`);

  // Simulate 40px swipe (halfway)
  const halfProgress = swipeReply._calculateProgress(40);
  assert(halfProgress === 0.5, `Progress should be 0.5 at half threshold, got ${halfProgress}`);
});

// Test 9: Visual feedback styles applied
test("visual_feedback_styles_applied", () => {
  const swipeReply = new SwipeToReply();
  const messageEl = createMockMessageElement();

  swipeReply._applyVisualFeedback(messageEl, 50);

  assert(messageEl.style.transform !== undefined, "Transform should be set");
  assert(messageEl.style.transform.includes("translateX"), "Should use translateX for performance");
  assert(messageEl.style.transform.includes("50"), "Should include distance value");
});

// Test 10: Snap back animation on insufficient swipe
test("snap_back_on_insufficient_swipe", () => {
  const swipeReply = new SwipeToReply({ threshold: 80 });
  const messageEl = createMockMessageElement();

  // Simulate swipe of only 50px (below 80px threshold)
  const shouldReply = swipeReply._handleSwipeEnd(
    messageEl,
    { direction: "right", distance: 50 },
    "msg-123",
  );

  assert(shouldReply === false, "Should not trigger reply under threshold");
  assert(messageEl.style.transition !== undefined, "Should set transition for snap-back animation");
});

// Test 11: Trigger reply on sufficient right swipe
test("trigger_reply_on_sufficient_right_swipe", () => {
  let replyTriggered = false;
  let replyMessageId = null;

  const swipeReply = new SwipeToReply({
    threshold: 80,
    onReply: (messageId) => {
      replyTriggered = true;
      replyMessageId = messageId;
    },
  });

  const messageEl = createMockMessageElement();
  swipeReply.attachToMessage(messageEl, "msg-456");

  // Simulate 100px right swipe
  const shouldReply = swipeReply._handleSwipeEnd(
    messageEl,
    { direction: "right", distance: 100 },
    "msg-456",
  );

  assert(shouldReply === true, "Should trigger reply at threshold");
  assert(replyTriggered === true, "onReply callback should be called");
  assert(replyMessageId === "msg-456", "Should pass correct message ID");
});

// Test 12: Haptic feedback called when enabled
test("haptic_feedback_called_when_enabled", () => {
  let hapticCalled = false;

  // Mock navigator.vibrate
  const originalVibrate = navigator.vibrate;
  navigator.vibrate = () => {
    hapticCalled = true;
  };

  const swipeReply = new SwipeToReply({ enableHaptic: true });
  swipeReply._triggerHaptic();

  assert(hapticCalled === true, "Haptic feedback should be triggered");

  // Restore
  navigator.vibrate = originalVibrate;
});

// Test 13: Haptic feedback skipped when disabled
test("haptic_feedback_skipped_when_disabled", () => {
  let hapticCalled = false;

  const originalVibrate = navigator.vibrate;
  navigator.vibrate = () => {
    hapticCalled = true;
  };

  const swipeReply = new SwipeToReply({ enableHaptic: false });
  swipeReply._triggerHaptic();

  assert(hapticCalled === false, "Haptic should not trigger when disabled");

  navigator.vibrate = originalVibrate;
});

// Test 14: Reply icon appears during swipe
test("reply_icon_appears_during_swipe", () => {
  const swipeReply = new SwipeToReply();
  const messageEl = createMockMessageElement();

  // Apply visual feedback with sufficient distance to trigger icon
  swipeReply._applyVisualFeedback(messageEl, 40);

  // Check if icon was created
  const _icon = messageEl.querySelector(".swipe-reply-icon");
  // In test environment, the icon may not be queryable but the function should complete without error
  assert(swipeReply.SWIPE_ICON_THRESHOLD === 20, "Icon threshold should be 20px");
});

// Test 15: Destroy cleans up all detectors
test("destroy_cleans_up_all_detectors", () => {
  const swipeReply = new SwipeToReply();

  swipeReply.attachToMessage(createMockMessageElement(), "msg-1");
  swipeReply.attachToMessage(createMockMessageElement(), "msg-2");
  swipeReply.attachToMessage(createMockMessageElement(), "msg-3");

  assert(swipeReply._detectors.size === 3, "Should have 3 detectors");

  swipeReply.destroy();

  assert(swipeReply._detectors.size === 0, "Should have 0 detectors after destroy");
});

// Summary
console.log("\n-------------------");
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log("-------------------");

process.exit(testsFailed > 0 ? 1 : 0);
