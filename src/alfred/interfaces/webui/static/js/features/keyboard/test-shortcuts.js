/**
 * Tests for Shortcut Registry
 *
 * Run with: node test-shortcuts.js
 */

const {
  register,
  getAll,
  getAllFlat,
  getById,
  unregister,
  clear,
  formatShortcut,
  parseKeyCombo,
} = require("./shortcuts.js");

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

// Setup
clear();

console.log("Running Shortcut Registry Tests...\n");

test("register adds shortcut to registry", () => {
  register({
    id: "test-help",
    key: "?",
    description: "Show help",
    action: () => {},
  });
  assert(getAllFlat().length === 1, "Should have 1 shortcut");
});

test("register requires id field", () => {
  clear();
  try {
    register({ key: "a", description: "Test", action: () => {} });
    assert(false, "Should have thrown");
  } catch (e) {
    assert(e.message.includes("id"), "Error should mention id");
  }
});

test("register requires key field", () => {
  clear();
  try {
    register({ id: "test", description: "Test", action: () => {} });
    assert(false, "Should have thrown");
  } catch (e) {
    assert(e.message.includes("key"), "Error should mention key");
  }
});

test("register requires action field", () => {
  clear();
  try {
    register({ id: "test", key: "a", description: "Test" });
    assert(false, "Should have thrown");
  } catch (e) {
    assert(e.message.includes("action"), "Error should mention action");
  }
});

test("register requires description field", () => {
  clear();
  try {
    register({ id: "test", key: "a", action: () => {} });
    assert(false, "Should have thrown");
  } catch (e) {
    assert(e.message.includes("description"), "Error should mention description");
  }
});

test("getAll groups shortcuts by category", () => {
  clear();
  register({ id: "cmd1", key: "a", description: "Action 1", category: "Global", action: () => {} });
  register({ id: "cmd2", key: "b", description: "Action 2", category: "Global", action: () => {} });
  register({
    id: "cmd3",
    key: "c",
    description: "Action 3",
    category: "Navigation",
    action: () => {},
  });

  const grouped = getAll();
  assert(Object.keys(grouped).length === 2, "Should have 2 categories");
  assert(grouped.Global.length === 2, "Global should have 2 shortcuts");
  assert(grouped.Navigation.length === 1, "Navigation should have 1 shortcut");
});

test("getAllFlat returns all shortcuts as array", () => {
  clear();
  register({ id: "a", key: "a", description: "A", action: () => {} });
  register({ id: "b", key: "b", description: "B", action: () => {} });

  const all = getAllFlat();
  assert(all.length === 2, "Should return 2 shortcuts");
});

test("getById returns correct shortcut", () => {
  clear();
  register({ id: "find-me", key: "x", description: "Find me", action: () => {} });
  const shortcut = getById("find-me");
  assert(shortcut !== undefined, "Should find shortcut");
  assert(shortcut.description === "Find me", "Should have correct description");
});

test("unregister removes shortcut", () => {
  clear();
  register({ id: "to-remove", key: "x", description: "Remove", action: () => {} });
  const removed = unregister("to-remove");
  assert(removed === true, "Should return true");
  assert(getById("to-remove") === undefined, "Should be removed");
});

test("parseKeyCombo parses simple key", () => {
  const parsed = parseKeyCombo("k");
  assert(parsed.key === "k", "Key should be k");
  assert(parsed.ctrl === false, "Ctrl should be false");
});

test("parseKeyCombo parses modifier combo", () => {
  const parsed = parseKeyCombo("Ctrl+K");
  assert(parsed.key === "K", "Key should be K");
  assert(parsed.ctrl === true, "Ctrl should be true");
});

test("parseKeyCombo parses multiple modifiers", () => {
  const parsed = parseKeyCombo("Ctrl+Shift+A");
  assert(parsed.key === "A", "Key should be A");
  assert(parsed.ctrl === true, "Ctrl should be true");
  assert(parsed.shift === true, "Shift should be true");
});

test("register stores modifiers correctly", () => {
  clear();
  register({ id: "ctrl-k", key: "Ctrl+K", description: "Ctrl K", action: () => {} });
  const shortcut = getById("ctrl-k");
  assert(shortcut.ctrl === true, "Ctrl should be true");
  assert(shortcut.key === "k", "Key should be lowercase k");
});

test("formatShortcut formats simple key", () => {
  const shortcut = { key: "k", ctrl: false, shift: false, alt: false, meta: false };
  assert(formatShortcut(shortcut) === "k", "Should be k");
});

test("formatShortcut formats with modifiers", () => {
  const shortcut = { key: "k", ctrl: true, shift: false, alt: false, meta: false };
  assert(formatShortcut(shortcut) === "Ctrl+k", "Should be Ctrl+k");
});

test("formatShortcut formats special keys", () => {
  assert(
    formatShortcut({ key: "arrowup", ctrl: false, shift: false, alt: false, meta: false }) === "↑",
  );
  assert(
    formatShortcut({ key: "escape", ctrl: false, shift: false, alt: false, meta: false }) === "Esc",
  );
  assert(
    formatShortcut({ key: "home", ctrl: false, shift: false, alt: false, meta: false }) === "Home",
  );
});

test("register throws on duplicate id", () => {
  clear();
  register({ id: "duplicate", key: "a", description: "First", action: () => {} });
  try {
    register({ id: "duplicate", key: "b", description: "Second", action: () => {} });
    assert(false, "Should have thrown");
  } catch (e) {
    assert(e.message.includes("already exists"), "Error should mention duplicate");
  }
});

test("clear removes all shortcuts", () => {
  register({ id: "a", key: "a", description: "A", action: () => {} });
  register({ id: "b", key: "b", description: "B", action: () => {} });
  clear();
  assert(getAllFlat().length === 0, "Should have no shortcuts");
});

test("shortcut stores context", () => {
  clear();
  register({
    id: "context-test",
    key: "ArrowUp",
    description: "Test context",
    context: "message-focused",
    action: () => {},
  });
  const shortcut = getById("context-test");
  assert(shortcut.context === "message-focused", "Context should be stored");
});

console.log(`\n${"=".repeat(40)}`);
console.log(`Results: ${testsPassed} passed, ${testsFailed} failed`);
console.log(`${"=".repeat(40)}`);

process.exit(testsFailed > 0 ? 1 : 0);
