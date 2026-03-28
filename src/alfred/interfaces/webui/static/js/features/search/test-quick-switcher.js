/**
 * Unit tests for Quick Session Switcher
 * Milestone 9 Phase 2
 */

import { QuickSwitcher } from "./quick-switcher.js";

// Test utilities
function createMockDOM() {
  // Clean up any existing overlay
  const existing = document.getElementById("quick-switcher");
  if (existing) {
    existing.remove();
  }

  // Reset singleton
  QuickSwitcher.instance = null;
}

function _sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Test suite
export async function runTests() {
  const results = {
    passed: 0,
    failed: 0,
    tests: [],
  };

  function test(name, fn) {
    return { name, fn };
  }

  async function runTest(t) {
    try {
      createMockDOM();
      await t.fn();
      results.passed++;
      results.tests.push({ name: t.name, status: "PASS" });
      console.log(`✅ ${t.name}`);
    } catch (error) {
      results.failed++;
      results.tests.push({ name: t.name, status: "FAIL", error: error.message });
      console.error(`❌ ${t.name}: ${error.message}`);
    }
  }

  const tests = [
    test("QuickSwitcher instantiates and creates DOM", () => {
      const switcher = new QuickSwitcher();

      if (!switcher.overlay) {
        throw new Error("Overlay not created");
      }
      if (switcher.overlay.id !== "quick-switcher") {
        throw new Error("Overlay has wrong ID");
      }
      if (!switcher.searchInput) {
        throw new Error("Search input not created");
      }
      if (!switcher.resultsList) {
        throw new Error("Results list not created");
      }

      switcher.destroy();
    }),

    test("QuickSwitcher is singleton", () => {
      const switcher1 = new QuickSwitcher();
      const switcher2 = new QuickSwitcher();

      if (switcher1 !== switcher2) {
        throw new Error("QuickSwitcher is not a singleton");
      }

      // Also test getInstance
      const switcher3 = QuickSwitcher.getInstance();
      if (switcher3 !== switcher1) {
        throw new Error("getInstance returns different instance");
      }

      switcher1.destroy();
    }),

    test("open() shows overlay and focuses input", () => {
      const switcher = new QuickSwitcher();

      switcher.open();

      if (switcher.overlay.classList.contains("hidden")) {
        throw new Error("Overlay is hidden after open()");
      }
      if (!switcher.isOpen) {
        throw new Error("isOpen is false after open()");
      }
      if (document.activeElement !== switcher.searchInput) {
        throw new Error("Search input is not focused");
      }

      switcher.destroy();
    }),

    test("close() hides overlay", () => {
      const switcher = new QuickSwitcher();

      switcher.open();
      switcher.close();

      if (!switcher.overlay.classList.contains("hidden")) {
        throw new Error("Overlay is not hidden after close()");
      }
      if (switcher.isOpen) {
        throw new Error("isOpen is true after close()");
      }

      switcher.destroy();
    }),

    test("Escape key closes switcher", () => {
      const switcher = new QuickSwitcher();

      switcher.open();

      const escapeEvent = new KeyboardEvent("keydown", {
        key: "Escape",
        bubbles: true,
      });
      document.dispatchEvent(escapeEvent);

      if (switcher.isOpen) {
        throw new Error("Switcher is still open after Escape");
      }

      switcher.destroy();
    }),

    test("filter() filters sessions correctly", () => {
      const switcher = new QuickSwitcher();

      switcher.sessions = [
        { id: "1", name: "Project Planning", timestamp: Date.now() },
        { id: "2", name: "Code Review", timestamp: Date.now() },
        { id: "3", name: "Design Discussion", timestamp: Date.now() },
      ];

      switcher.filter("proj");

      if (switcher.filteredSessions.length !== 1) {
        throw new Error(`Expected 1 filtered session, got ${switcher.filteredSessions.length}`);
      }
      if (switcher.filteredSessions[0].id !== "1") {
        throw new Error("Wrong session filtered");
      }

      switcher.filter("");
      if (switcher.filteredSessions.length !== 3) {
        throw new Error("Empty filter should show all sessions");
      }

      switcher.destroy();
    }),

    test("fuzzyMatch() matches correctly", () => {
      const switcher = new QuickSwitcher();

      // Test basic matching
      if (!switcher.fuzzyMatch("abc", "abc")) {
        throw new Error("Exact match should work");
      }

      // Test fuzzy matching (characters in order)
      if (!switcher.fuzzyMatch("abc", "aabbcc")) {
        throw new Error("Fuzzy match should work");
      }

      // Test non-match
      if (switcher.fuzzyMatch("abc", "def")) {
        throw new Error("Non-matching should return false");
      }

      // Test partial match (not in order)
      if (switcher.fuzzyMatch("cba", "abc")) {
        throw new Error("Wrong order should not match");
      }

      switcher.destroy();
    }),

    test("navigate() moves selection", () => {
      const switcher = new QuickSwitcher();

      switcher.sessions = [
        { id: "1", name: "Session 1", timestamp: Date.now() },
        { id: "2", name: "Session 2", timestamp: Date.now() },
        { id: "3", name: "Session 3", timestamp: Date.now() },
      ];
      switcher.filter("");

      if (switcher.selectedIndex !== 0) {
        throw new Error("Initial selection should be 0");
      }

      switcher.navigate("next");
      if (switcher.selectedIndex !== 1) {
        throw new Error("Selection should move to 1");
      }

      switcher.navigate("next");
      if (switcher.selectedIndex !== 2) {
        throw new Error("Selection should move to 2");
      }

      // Wrap around
      switcher.navigate("next");
      if (switcher.selectedIndex !== 0) {
        throw new Error("Selection should wrap to 0");
      }

      // Navigate previous
      switcher.navigate("previous");
      if (switcher.selectedIndex !== 2) {
        throw new Error("Selection should wrap to 2");
      }

      switcher.destroy();
    }),

    test("select() calls onSelect callback", () => {
      let selectedId = null;
      const switcher = new QuickSwitcher({
        onSelect: (id) => {
          selectedId = id;
        },
      });

      switcher.sessions = [{ id: "test-id", name: "Test Session", timestamp: Date.now() }];
      switcher.filter("");
      switcher.select();

      if (selectedId !== "test-id") {
        throw new Error(`Expected 'test-id', got '${selectedId}'`);
      }

      switcher.destroy();
    }),

    test("trackSession() adds to recent", () => {
      const switcher = new QuickSwitcher();

      // Clear sessions
      switcher.sessions = [];

      switcher.trackSession("1", "First Session");
      if (switcher.sessions.length !== 1) {
        throw new Error("Session not added");
      }

      switcher.trackSession("2", "Second Session");
      if (switcher.sessions.length !== 2) {
        throw new Error("Second session not added");
      }

      // Re-add first session - should move to front
      switcher.trackSession("1", "First Session");
      if (switcher.sessions[0].id !== "1") {
        throw new Error("Session should move to front when re-added");
      }
      if (switcher.sessions.length !== 2) {
        throw new Error("Duplicate session should not increase count");
      }

      switcher.destroy();
    }),

    test("formatTimeAgo() formats correctly", () => {
      const switcher = new QuickSwitcher();
      const now = Date.now();

      // Just now
      const justNow = switcher.formatTimeAgo(now - 1000);
      if (justNow !== "just now") {
        throw new Error(`Expected 'just now', got '${justNow}'`);
      }

      // Minutes ago
      const minutesAgo = switcher.formatTimeAgo(now - 5 * 60 * 1000);
      if (minutesAgo !== "5m ago") {
        throw new Error(`Expected '5m ago', got '${minutesAgo}'`);
      }

      // Hours ago
      const hoursAgo = switcher.formatTimeAgo(now - 3 * 60 * 60 * 1000);
      if (hoursAgo !== "3h ago") {
        throw new Error(`Expected '3h ago', got '${hoursAgo}'`);
      }

      // Days ago
      const daysAgo = switcher.formatTimeAgo(now - 2 * 24 * 60 * 60 * 1000);
      if (daysAgo !== "2d ago") {
        throw new Error(`Expected '2d ago', got '${daysAgo}'`);
      }

      switcher.destroy();
    }),

    test("escapeHtml() prevents XSS", () => {
      const switcher = new QuickSwitcher();

      const dangerous = '<script>alert("xss")</script>';
      const safe = switcher.escapeHtml(dangerous);

      if (safe.includes("<script>")) {
        throw new Error("HTML not escaped properly");
      }
      if (!safe.includes("&lt;script&gt;")) {
        throw new Error("Script tags should be converted to entities");
      }

      switcher.destroy();
    }),

    test("Arrow keys navigate results", () => {
      const switcher = new QuickSwitcher();

      switcher.sessions = [
        { id: "1", name: "Session 1", timestamp: Date.now() },
        { id: "2", name: "Session 2", timestamp: Date.now() },
      ];
      switcher.open();

      // Arrow down
      const downEvent = new KeyboardEvent("keydown", {
        key: "ArrowDown",
        bubbles: true,
      });
      document.dispatchEvent(downEvent);

      if (switcher.selectedIndex !== 1) {
        throw new Error("ArrowDown should move to next item");
      }

      // Arrow up
      const upEvent = new KeyboardEvent("keydown", {
        key: "ArrowUp",
        bubbles: true,
      });
      document.dispatchEvent(upEvent);

      if (switcher.selectedIndex !== 0) {
        throw new Error("ArrowUp should move to previous item");
      }

      switcher.destroy();
    }),

    test("Enter key selects item", () => {
      let selectedId = null;
      const switcher = new QuickSwitcher({
        onSelect: (id) => {
          selectedId = id;
        },
      });

      switcher.sessions = [{ id: "enter-test", name: "Enter Test", timestamp: Date.now() }];
      switcher.open();

      const enterEvent = new KeyboardEvent("keydown", {
        key: "Enter",
        bubbles: true,
      });
      document.dispatchEvent(enterEvent);

      if (selectedId !== "enter-test") {
        throw new Error("Enter should select current item");
      }
      if (switcher.isOpen) {
        throw new Error("Switcher should close after selection");
      }

      switcher.destroy();
    }),

    test("maxSessions limits stored sessions", () => {
      const switcher = new QuickSwitcher({ maxSessions: 3 });

      switcher.trackSession("1", "Session 1");
      switcher.trackSession("2", "Session 2");
      switcher.trackSession("3", "Session 3");
      switcher.trackSession("4", "Session 4");

      if (switcher.sessions.length !== 3) {
        throw new Error(`Expected 3 sessions, got ${switcher.sessions.length}`);
      }
      if (switcher.sessions[0].id !== "4") {
        throw new Error("Most recent should be first");
      }

      switcher.destroy();
    }),
  ];

  console.log("\n🧪 Running Quick Switcher Tests...\n");

  for (const t of tests) {
    await runTest(t);
  }

  console.log(`\n📊 Results: ${results.passed} passed, ${results.failed} failed`);

  return results;
}

// Run tests if this file is loaded directly
if (typeof window !== "undefined" && window.location?.pathname?.includes("test-quick-switcher")) {
  runTests();
}
