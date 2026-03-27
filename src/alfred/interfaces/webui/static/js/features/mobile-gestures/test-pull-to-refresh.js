/**
 * Tests for Pull to Refresh helpers and detector
 *
 * Run with: node test-pull-to-refresh.js
 */

// Minimal DOM-like globals for Node.js testing
class MockHTMLElement {
  constructor() {
    this.style = {
      _properties: {},
      setProperty(key, value) {
        this._properties[key] = value;
      },
      getPropertyValue(key) {
        return this._properties[key] || '';
      }
    };
    this.dataset = {};
    this.scrollTop = 0;
    this._classes = new Set();
    this._listeners = {};
    this.parentNode = null;
    this._attributes = {};
    this._className = '';
    const self = this;
    this.classList = {
      add: (...classes) => {
        classes.forEach(cls => self._classes.add(cls));
        self._syncClassName();
      },
      remove: (...classes) => {
        classes.forEach(cls => self._classes.delete(cls));
        self._syncClassName();
      },
      contains: (cls) => self._classes.has(cls),
    };
  }

  get className() {
    return this._className;
  }

  set className(value) {
    this._className = value;
    this._classes.clear();
    value.split(/\s+/).forEach(cls => {
      if (cls) this._classes.add(cls);
    });
  }

  _syncClassName() {
    this._className = Array.from(this._classes).join(' ');
  }

  setAttribute(key, value) {
    this._attributes[key] = String(value);
  }

  getAttribute(key) {
    return this._attributes[key] || null;
  }

  remove() {
    if (this.parentNode) {
      this.parentNode.removeChild(this);
    }
  }

  addEventListener(type, handler) {
    this._listeners[type] = handler;
  }

  removeEventListener(type, handler) {
    if (this._listeners[type] === handler) {
      delete this._listeners[type];
    }
  }

  appendChild(child) {
    if (child) {
      child.parentNode = this;
    }
    return child;
  }

  removeChild(child) {
    if (child) {
      child.parentNode = null;
    }
    return child;
  }

  matches() {
    return false;
  }

  closest() {
    return null;
  }

  querySelector(selector) {
    // Support .ptr-text selector for PullIndicator tests
    if (selector === '.ptr-text') {
      return new MockHTMLElement();
    }
    return null;
  }

  querySelectorAll() {
    return [];
  }
}

// Mock Element for document.createElement
class MockElement extends MockHTMLElement {
  constructor(tagName) {
    super();
    this.tagName = tagName;
    this.innerHTML = '';
  }
}

global.HTMLElement = MockHTMLElement;
global.document = {
  _elements: {},
  createElement(tagName) {
    const el = new MockElement(tagName);
    return el;
  },
  getElementById(id) {
    return this._elements[id] || null;
  },
  body: new MockHTMLElement(),
  appendChild(child) {
    if (child) {
      child.parentNode = this;
      // Store element by id for getElementById
      if (child.id) {
        this._elements[child.id] = child;
      }
    }
    return child;
  },
  removeChild(child) {
    if (child && child.id && this._elements[child.id]) {
      delete this._elements[child.id];
    }
    if (child) {
      child.parentNode = null;
    }
    return child;
  }
};
global.window = {
  innerWidth: 400,
  addEventListener() {},
  removeEventListener() {},
};
global.navigator = {
  vibrate() {}
};

const { isScrolledToTop, PullToRefreshDetector } = require('./pull-to-refresh.js');

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

function createMockElement() {
  return new MockHTMLElement();
}

function createTouchEvent(x, y, target = createMockElement()) {
  let prevented = false;
  return {
    touches: [{ clientX: x, clientY: y }],
    target,
    preventDefault() {
      prevented = true;
    },
    stopPropagation() {},
    get defaultPrevented() {
      return prevented;
    },
  };
}

console.log('Running Pull to Refresh Tests...\n');

// Helper coverage
test('scroll at top is detected', () => {
  const result = isScrolledToTop({ scrollTop: 0 });
  assert(result === true, `Expected true for scrollTop=0, got ${result}`);
});

test('scroll position above top is not detected with strict threshold', () => {
  const result = isScrolledToTop({ scrollTop: 1 }, 0);
  assert(result === false, `Expected false for scrollTop=1 with threshold=0, got ${result}`);
});

test('small tolerance allows near-top scroll position', () => {
  const result = isScrolledToTop({ scrollTop: 8 }, 10);
  assert(result === true, `Expected true for scrollTop=8 with threshold=10, got ${result}`);
});

test('scroll position above tolerance is not detected', () => {
  const result = isScrolledToTop({ scrollTop: 11 }, 10);
  assert(result === false, `Expected false for scrollTop=11 with threshold=10, got ${result}`);
});

// Detector coverage
test('pull to refresh module exports detector', () => {
  assert(typeof PullToRefreshDetector === 'function', 'PullToRefreshDetector should be exported');
});

test('pull detector initializes with defaults', () => {
  const detector = new PullToRefreshDetector();

  assert(detector.threshold === 80, `Expected default threshold 80, got ${detector.threshold}`);
  assert(detector.topThreshold === 10, `Expected default top threshold 10, got ${detector.topThreshold}`);
  assert(detector.resistance > 0 && detector.resistance <= 1, 'Resistance should be normalized');
  assert(typeof detector.onRefresh === 'function', 'onRefresh should default to a function');
});

test('attach to element returns true and stores element', () => {
  const detector = new PullToRefreshDetector();
  const element = createMockElement();

  const result = detector.attachToElement(element);

  assert(result === true, 'Expected attachToElement to succeed');
  assert(detector._element === element, 'Expected element to be stored');
  assert(detector._scrollContainer === element, 'Expected scroll container to default to attached element');
});

test('pull is ignored when container is not at top', () => {
  const detector = new PullToRefreshDetector();
  const element = createMockElement();
  element.scrollTop = 25;
  detector.attachToElement(element);

  detector._handleTouchStart(createTouchEvent(100, 100, element));

  assert(detector._isTracking === false, 'Expected detector to ignore touches away from top');
});

test('pull starts when container is at top', () => {
  const detector = new PullToRefreshDetector();
  const element = createMockElement();
  element.scrollTop = 0;
  detector.attachToElement(element);

  detector._handleTouchStart(createTouchEvent(100, 100, element));

  assert(detector._isTracking === true, 'Expected detector to begin tracking at top');
  assert(detector._startX === 100, `Expected startX to be 100, got ${detector._startX}`);
  assert(detector._startY === 100, `Expected startY to be 100, got ${detector._startY}`);
});

test('pull callbacks report pull progress and state changes', () => {
  let startDetail = null;
  let moveDetail = null;
  let endDetail = null;

  const detector = new PullToRefreshDetector({
    onPullStart: (detail) => {
      startDetail = detail;
    },
    onPullMove: (detail) => {
      moveDetail = detail;
    },
    onPullEnd: (detail) => {
      endDetail = detail;
    }
  });

  const element = createMockElement();
  element.scrollTop = 0;
  detector.attachToElement(element);

  detector._handleTouchStart(createTouchEvent(100, 100, element));
  detector._handleTouchMove(createTouchEvent(100, 140, element));
  detector._handleTouchEnd({});

  assert(startDetail !== null, 'Expected onPullStart to receive detail');
  assert(startDetail.rawDistance === 0, `Expected start raw distance 0, got ${startDetail.rawDistance}`);
  assert(moveDetail !== null, 'Expected onPullMove to receive detail');
  assert(moveDetail.rawDistance === 40, `Expected move raw distance 40, got ${moveDetail.rawDistance}`);
  assert(moveDetail.progress > 0, 'Expected pull progress to be greater than 0');
  assert(endDetail !== null, 'Expected onPullEnd to receive detail');
  assert(endDetail.refreshed === false, 'Expected insufficient pull to report refreshed=false');
});

test('pull triggers refresh after threshold', () => {
  let refreshCalled = false;
  let receivedDetail = null;

  const detector = new PullToRefreshDetector({
    onRefresh: (detail) => {
      refreshCalled = true;
      receivedDetail = detail;
    }
  });

  const element = createMockElement();
  element.scrollTop = 0;
  detector.attachToElement(element);

  detector._handleTouchStart(createTouchEvent(100, 100, element));
  detector._handleTouchMove(createTouchEvent(100, 190, element));
  detector._handleTouchEnd({});

  assert(refreshCalled === true, 'Expected onRefresh to be called');
  assert(receivedDetail !== null, 'Expected refresh detail to be passed');
  assert(receivedDetail.rawDistance >= 80, `Expected raw distance >= 80, got ${receivedDetail.rawDistance}`);
  assert(receivedDetail.progress === 1, `Expected capped progress 1, got ${receivedDetail.progress}`);
});

test('pull does not trigger refresh below threshold', () => {
  let refreshCalled = false;
  let cancelCalled = false;

  const detector = new PullToRefreshDetector({
    onRefresh: () => {
      refreshCalled = true;
    },
    onPullCancel: () => {
      cancelCalled = true;
    }
  });

  const element = createMockElement();
  element.scrollTop = 0;
  detector.attachToElement(element);

  detector._handleTouchStart(createTouchEvent(100, 100, element));
  detector._handleTouchMove(createTouchEvent(100, 150, element));
  detector._handleTouchEnd({});

  assert(refreshCalled === false, 'Expected onRefresh not to fire below threshold');
  assert(cancelCalled === true, 'Expected onPullCancel to fire for insufficient pull');
  assert(element.style.transform === 'translateY(0)', 'Expected pull to snap back');
});

test('pull resistance dampens visual distance', () => {
  const detector = new PullToRefreshDetector({ resistance: 0.5 });

  const eighty = detector._calculateDisplayDistance(80);
  const oneSixty = detector._calculateDisplayDistance(160);

  assert(eighty > 0, 'Expected positive display distance');
  assert(eighty < 80, `Expected resistance to dampen 80px pull, got ${eighty}`);
  assert(oneSixty > eighty, 'Expected larger pulls to produce larger visual distances');
  assert(oneSixty < 160, `Expected resistance to dampen 160px pull, got ${oneSixty}`);
});

test('pull cancels if container leaves top during gesture', () => {
  let refreshCalled = false;
  let cancelCalled = false;

  const detector = new PullToRefreshDetector({
    onRefresh: () => {
      refreshCalled = true;
    },
    onPullCancel: () => {
      cancelCalled = true;
    }
  });

  const element = createMockElement();
  element.scrollTop = 0;
  detector.attachToElement(element);

  detector._handleTouchStart(createTouchEvent(100, 100, element));
  element.scrollTop = 20;
  detector._handleTouchMove(createTouchEvent(100, 170, element));
  detector._handleTouchEnd({});

  assert(refreshCalled === false, 'Expected refresh to be canceled after leaving top');
  assert(cancelCalled === true, 'Expected cancel callback when gesture becomes invalid');
  assert(detector._isTracking === false, 'Expected tracking to stop after cancel');
});

// PullIndicator Tests
const { PullIndicator, createPullIndicator } = require('./pull-indicator.js');

test('pull indicator creates DOM element on construction', () => {
  const indicator = new PullIndicator({ container: document });

  assert(indicator.element !== null, 'Expected element to be created');
  assert(indicator.element.id === 'pull-indicator', 'Expected default id');
  assert(indicator.element.classList.contains('ptr-indicator'), 'Expected ptr-indicator class');

  indicator.destroy();
});

test('pull indicator show method removes hidden class', () => {
  const indicator = new PullIndicator({ container: document });

  indicator.show();

  assert(!indicator.element.classList.contains('ptr--hidden'), 'Expected hidden class removed');
  assert(indicator.element.classList.contains('ptr--pulling'), 'Expected pulling class added');
  assert(indicator.state === 'pulling', 'Expected state to be pulling');

  indicator.destroy();
});

test('pull indicator hide method adds hidden class', () => {
  const indicator = new PullIndicator({ container: document });

  indicator.show();
  indicator.hide();

  assert(indicator.element.classList.contains('ptr--hidden'), 'Expected hidden class added');
  assert(indicator.state === 'hidden', 'Expected state to be hidden');

  indicator.destroy();
});

test('pull indicator update sets CSS custom properties', () => {
  const indicator = new PullIndicator({ container: document });

  indicator.update(0.5, 40);

  assert(indicator.progress === 0.5, 'Expected progress to be 0.5');
  assert(indicator.element.style.getPropertyValue('--ptr-progress') === '0.5', 'Expected --ptr-progress set');
  assert(indicator.element.style.getPropertyValue('--ptr-distance') === '40px', 'Expected --ptr-distance set');

  indicator.destroy();
});

test('pull indicator update clamps progress to 0-1 range', () => {
  const indicator = new PullIndicator({ container: document });

  indicator.update(1.5, 120);

  assert(indicator.progress === 1, 'Expected progress clamped to 1');
  assert(indicator.state === 'ready', 'Expected state to be ready when progress >= 1');

  indicator.update(-0.5, -10);

  assert(indicator.progress === 0, 'Expected progress clamped to 0');

  indicator.destroy();
});

test('pull indicator setState applies correct CSS classes', () => {
  const indicator = new PullIndicator({ container: document });

  indicator.setState('ready');

  assert(indicator.state === 'ready', 'Expected state to be ready');
  assert(indicator.element.classList.contains('ptr--ready'), 'Expected ptr--ready class');

  indicator.setState('refreshing');

  assert(indicator.state === 'refreshing', 'Expected state to be refreshing');
  assert(indicator.element.classList.contains('ptr--refreshing'), 'Expected ptr--refreshing class');
  assert(!indicator.element.classList.contains('ptr--ready'), 'Expected ptr--ready class removed');

  indicator.destroy();
});

test('pull indicator isVisible returns correct state', () => {
  const indicator = new PullIndicator({ container: document });

  assert(!indicator.isVisible(), 'Expected not visible initially');

  indicator.show();

  assert(indicator.isVisible(), 'Expected visible after show');

  indicator.hide();

  assert(!indicator.isVisible(), 'Expected not visible after hide');

  indicator.destroy();
});

test('pull indicator destroy removes DOM element', () => {
  const indicator = new PullIndicator({ container: document });

  indicator.destroy();

  assert(indicator.element === null, 'Expected element to be null after destroy');
});

test('createPullIndicator wires callbacks to detector', () => {
  let refreshCalled = false;

  const detector = new PullToRefreshDetector({
    onRefresh: () => {
      refreshCalled = true;
    }
  });

  const indicator = createPullIndicator(detector, { container: document });

  // Simulate pull that triggers refresh
  const element = createMockElement();
  element.scrollTop = 0;
  detector.attachToElement(element);

  detector._handleTouchStart(createTouchEvent(100, 100, element));
  detector._handleTouchMove(createTouchEvent(100, 190, element));

  // Check indicator shows and updates
  assert(indicator.isVisible(), 'Expected indicator visible after pull start');
  assert(indicator.progress > 0, 'Expected progress updated');

  detector._handleTouchEnd({});

  // Check refresh was called
  assert(refreshCalled === true, 'Expected onRefresh to be called');
  assert(indicator.state === 'refreshing', 'Expected indicator in refreshing state');

  indicator.destroy();
  detector.detach();
});

// Summary
console.log('\n-------------------');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('-------------------');

process.exit(testsFailed > 0 ? 1 : 0);
