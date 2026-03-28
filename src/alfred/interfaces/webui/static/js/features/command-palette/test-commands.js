/**
 * Tests for Command Registry
 *
 * Run with: node test-commands.js
 */

const { register, getAll, getById, unregister, clear } = require("./commands.js");

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

// Setup: clear registry before each test
clear();

console.log("Running Command Registry Tests...\n");

test("register adds command to registry", () => {
  register({
    id: "test-command",
    title: "Test Command",
    action: () => {},
  });
  assert(getAll().length === 1, "Should have 1 command");
});

test("getAll returns all registered commands", () => {
  clear();
  register({ id: "cmd1", title: "Command 1", action: () => {} });
  register({ id: "cmd2", title: "Command 2", action: () => {} });
  const all = getAll();
  assert(all.length === 2, "Should return 2 commands");
  assert(all[0].id === "cmd1", "First command should be cmd1");
  assert(all[1].id === "cmd2", "Second command should be cmd2");
});

test("getById returns correct command", () => {
  clear();
  register({ id: "find-me", title: "Find Me", action: () => {} });
  const cmd = getById("find-me");
  assert(cmd !== undefined, "Should find command");
  assert(cmd.title === "Find Me", "Should have correct title");
});

test("getById returns undefined for missing command", () => {
  const cmd = getById("non-existent");
  assert(cmd === undefined, "Should return undefined");
});

test("register requires id field", () => {
  clear();
  try {
    register({ title: "No ID", action: () => {} });
    assert(false, "Should have thrown");
  } catch (e) {
    assert(e.message.includes("id"), "Error should mention id");
  }
});

test("register requires title field", () => {
  clear();
  try {
    register({ id: "no-title", action: () => {} });
    assert(false, "Should have thrown");
  } catch (e) {
    assert(e.message.includes("title"), "Error should mention title");
  }
});

test("register requires action field", () => {
  clear();
  try {
    register({ id: "no-action", title: "No Action" });
    assert(false, "Should have thrown");
  } catch (e) {
    assert(e.message.includes("action"), "Error should mention action");
  }
});

test("register requires action to be a function", () => {
  clear();
  try {
    register({ id: "bad-action", title: "Bad Action", action: "not-a-function" });
    assert(false, "Should have thrown");
  } catch (e) {
    assert(e.message.includes("action"), "Error should mention action");
  }
});

test("register throws on duplicate id", () => {
  clear();
  register({ id: "duplicate", title: "First", action: () => {} });
  try {
    register({ id: "duplicate", title: "Second", action: () => {} });
    assert(false, "Should have thrown");
  } catch (e) {
    assert(e.message.includes("already exists"), "Error should mention duplicate");
  }
});

test("unregister removes command", () => {
  clear();
  register({ id: "to-remove", title: "To Remove", action: () => {} });
  const removed = unregister("to-remove");
  assert(removed === true, "Should return true");
  assert(getById("to-remove") === undefined, "Command should be removed");
});

test("unregister returns false for non-existent command", () => {
  clear();
  const removed = unregister("non-existent");
  assert(removed === false, "Should return false");
});

test("clear removes all commands", () => {
  register({ id: "cmd1", title: "CMD1", action: () => {} });
  register({ id: "cmd2", title: "CMD2", action: () => {} });
  clear();
  assert(getAll().length === 0, "Should have no commands");
});

test("registered command has all fields", () => {
  clear();
  register({
    id: "full-cmd",
    title: "Full Command",
    keywords: ["search", "term"],
    shortcut: "Ctrl+K",
    action: () => {},
  });
  const cmd = getById("full-cmd");
  assert(cmd.id === "full-cmd", "Has id");
  assert(cmd.title === "Full Command", "Has title");
  assert(cmd.keywords.length === 2, "Has keywords");
  assert(cmd.shortcut === "Ctrl+K", "Has shortcut");
  assert(typeof cmd.action === "function", "Has action");
});

test("keywords defaults to empty array", () => {
  clear();
  register({ id: "no-keywords", title: "No Keywords", action: () => {} });
  const cmd = getById("no-keywords");
  assert(Array.isArray(cmd.keywords), "Keywords should be array");
  assert(cmd.keywords.length === 0, "Keywords should be empty");
});

test("shortcut defaults to null", () => {
  clear();
  register({ id: "no-shortcut", title: "No Shortcut", action: () => {} });
  const cmd = getById("no-shortcut");
  assert(cmd.shortcut === null, "Shortcut should be null");
});

console.log(`\n${"=".repeat(40)}`);
console.log(`Results: ${testsPassed} passed, ${testsFailed} failed`);
console.log(`${"=".repeat(40)}`);

process.exit(testsFailed > 0 ? 1 : 0);
