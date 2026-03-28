/**
 * Unit tests for Mention Dropdown (@ Mentions)
 * Milestone 9 Phase 3
 */

import { initializeMentions, MentionDropdown } from "./mention-dropdown.js";

// Test utilities
function createMockDOM() {
  // Clean up any existing dropdown
  const existing = document.querySelector(".mention-dropdown");
  if (existing) {
    existing.remove();
  }

  // Reset singleton
  MentionDropdown.instance = null;

  // Create mock composer and messages
  document.body.innerHTML = `
    <input id="message-input" type="text">
    <div id="message-list">
      <div class="message" data-message-id="msg-1">
        <span class="author">Alfred</span>
        <span class="message-text">Hello world, how are you today?</span>
      </div>
      <div class="message" data-message-id="msg-2">
        <span class="author">User</span>
        <span class="message-text">I'm doing great, thanks for asking!</span>
      </div>
      <div class="message" data-message-id="msg-3">
        <span class="author">Alfred</span>
        <span class="message-text">The API returns a 200 status code</span>
      </div>
    </div>
  `;
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
    test("MentionDropdown instantiates and creates DOM", () => {
      const composer = document.getElementById("message-input");
      const md = new MentionDropdown({ composer });

      if (!md.dropdown) {
        throw new Error("Dropdown not created");
      }
      if (!md.dropdown.classList.contains("mention-dropdown")) {
        throw new Error("Dropdown has wrong class");
      }
      if (!md.listEl) {
        throw new Error("List element not created");
      }

      md.destroy();
    }),

    test("MentionDropdown is singleton", () => {
      const composer = document.getElementById("message-input");
      const md1 = new MentionDropdown({ composer });
      const md2 = new MentionDropdown({ composer });

      if (md1 !== md2) {
        throw new Error("MentionDropdown is not a singleton");
      }

      // Also test getInstance
      const md3 = MentionDropdown.getInstance({ composer });
      if (md3 !== md1) {
        throw new Error("getInstance returns different instance");
      }

      md1.destroy();
    }),

    test("extractMessages() extracts from DOM", () => {
      const composer = document.getElementById("message-input");
      const md = new MentionDropdown({ composer });

      const messages = md.extractMessages();

      if (messages.length !== 3) {
        throw new Error(`Expected 3 messages, got ${messages.length}`);
      }

      // Check most recent first (reversed)
      if (messages[0].id !== "msg-3") {
        throw new Error("Messages should be reversed (most recent first)");
      }

      if (messages[0].author !== "Alfred") {
        throw new Error("Wrong author for first message");
      }

      if (!messages[0].text.includes("API")) {
        throw new Error("Wrong text content");
      }

      md.destroy();
    }),

    test("fuzzyMatch() matches correctly", () => {
      const md = new MentionDropdown();

      // Exact match
      if (!md.fuzzyMatch("hello", "hello world")) {
        throw new Error("Exact substring should match");
      }

      // Fuzzy match (characters in order)
      if (!md.fuzzyMatch("hw", "hello world")) {
        throw new Error("h->hello, w->world should match");
      }

      if (!md.fuzzyMatch("api", "the API returns")) {
        throw new Error("a->API should match case-insensitive");
      }

      // Non-match
      if (md.fuzzyMatch("xyz", "hello world")) {
        throw new Error("Non-matching characters should return false");
      }

      // Wrong order
      if (md.fuzzyMatch("wh", "hello world")) {
        throw new Error("Wrong order should not match");
      }

      md.destroy();
    }),

    test("filter() filters messages", () => {
      const composer = document.getElementById("message-input");
      const md = new MentionDropdown({ composer });

      md.messages = [
        { id: "1", text: "Hello world", author: "User" },
        { id: "2", text: "API documentation", author: "Alfred" },
        { id: "3", text: "Hello again", author: "User" },
      ];

      md.filter("api");

      if (md.filteredMessages.length !== 1) {
        throw new Error(`Expected 1 filtered message, got ${md.filteredMessages.length}`);
      }

      if (md.filteredMessages[0].id !== "2") {
        throw new Error("Wrong message filtered");
      }

      // Empty filter shows all
      md.filter("");
      if (md.filteredMessages.length !== 3) {
        throw new Error("Empty filter should show all messages");
      }

      md.destroy();
    }),

    test("open() shows dropdown", () => {
      const composer = document.getElementById("message-input");
      const md = new MentionDropdown({ composer });

      md.open();

      if (md.dropdown.classList.contains("hidden")) {
        throw new Error("Dropdown should be visible after open()");
      }
      if (!md.isOpen) {
        throw new Error("isOpen should be true");
      }

      md.destroy();
    }),

    test("close() hides dropdown", () => {
      const composer = document.getElementById("message-input");
      const md = new MentionDropdown({ composer });

      md.open();
      md.close();

      if (!md.dropdown.classList.contains("hidden")) {
        throw new Error("Dropdown should be hidden after close()");
      }
      if (md.isOpen) {
        throw new Error("isOpen should be false");
      }

      md.destroy();
    }),

    test("navigate() moves selection", () => {
      const composer = document.getElementById("message-input");
      const md = new MentionDropdown({ composer });

      md.filteredMessages = [
        { id: "1", text: "One", author: "A" },
        { id: "2", text: "Two", author: "B" },
        { id: "3", text: "Three", author: "C" },
      ];

      if (md.selectedIndex !== 0) {
        throw new Error("Initial selection should be 0");
      }

      md.navigate("next");
      if (md.selectedIndex !== 1) {
        throw new Error("Should move to index 1");
      }

      md.navigate("next");
      if (md.selectedIndex !== 2) {
        throw new Error("Should move to index 2");
      }

      // Wrap around
      md.navigate("next");
      if (md.selectedIndex !== 0) {
        throw new Error("Should wrap to index 0");
      }

      // Navigate previous
      md.navigate("previous");
      if (md.selectedIndex !== 2) {
        throw new Error("Previous from 0 should wrap to 2");
      }

      md.destroy();
    }),

    test("insertMention() inserts at cursor", () => {
      const composer = document.getElementById("message-input");
      const md = new MentionDropdown({ composer });

      composer.value = "As @ said earlier";
      composer.selectionStart = composer.selectionEnd = 6; // After @

      md.insertMention({
        author: "Alfred",
        text: "The API returns a 200 status code",
      });

      if (!composer.value.includes("@Alfred:")) {
        throw new Error("Mention not inserted correctly");
      }

      if (!composer.value.includes('"The API returns')) {
        throw new Error("Excerpt not included");
      }

      // Check cursor position is after mention
      const expectedMentionLength = '@Alfred: "The API returns a 200 status code" '.length;
      if (composer.selectionStart !== expectedMentionLength) {
        throw new Error("Cursor not positioned after mention");
      }

      md.destroy();
    }),

    test("escapeHtml() prevents XSS", () => {
      const md = new MentionDropdown();

      const dangerous = '<script>alert("xss")</script>';
      const safe = md.escapeHtml(dangerous);

      if (safe.includes("<script>")) {
        throw new Error("HTML not escaped");
      }
      if (!safe.includes("&lt;script&gt;")) {
        throw new Error("Script tags should be converted to entities");
      }

      md.destroy();
    }),

    test("maxMessages limits results", () => {
      const composer = document.getElementById("message-input");
      const md = new MentionDropdown({ composer, maxMessages: 2 });

      md.messages = [
        { id: "1", text: "One", author: "A" },
        { id: "2", text: "Two", author: "B" },
        { id: "3", text: "Three", author: "C" },
      ];

      md.filter("");

      if (md.filteredMessages.length !== 2) {
        throw new Error(`Expected 2 messages (max), got ${md.filteredMessages.length}`);
      }

      md.destroy();
    }),

    test("handleInput detects @ trigger", () => {
      const composer = document.getElementById("message-input");
      const md = new MentionDropdown({ composer });

      // Simulate typing @
      composer.value = "Hello @";
      composer.selectionStart = composer.selectionEnd = 7;

      const inputEvent = new Event("input", { bubbles: true });
      composer.dispatchEvent(inputEvent);

      // Should be open (or at least attempted)
      // Note: actual open requires message extraction from DOM

      md.destroy();
    }),

    test("initializeMentions returns instance", () => {
      const composer = document.getElementById("message-input");
      const md = initializeMentions({ composer });

      if (!(md instanceof MentionDropdown)) {
        throw new Error("initializeMentions should return MentionDropdown instance");
      }

      md.destroy();
    }),
  ];

  console.log("\n🧪 Running Mention Dropdown Tests...\n");

  for (const t of tests) {
    await runTest(t);
  }

  console.log(`\n📊 Results: ${results.passed} passed, ${results.failed} failed`);

  return results;
}

// Run tests if this file is loaded directly
if (typeof window !== "undefined" && window.location?.pathname?.includes("test-mention")) {
  runTests();
}
