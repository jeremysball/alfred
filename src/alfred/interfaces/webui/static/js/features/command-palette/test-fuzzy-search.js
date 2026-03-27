/**
 * Tests for Fuzzy Search Engine
 *
 * Run with: node test-fuzzy-search.js
 */

const { search, calculateScore, isFuzzyMatch, getHighlightIndices } = require('./fuzzy-search.js');

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

console.log('Running Fuzzy Search Tests...\n');

// Test data
const testCommands = [
  { id: 'clear', title: 'Clear Chat', keywords: ['reset', 'clean'], action: () => {} },
  { id: 'theme', title: 'Toggle Theme', keywords: ['dark', 'light', 'mode'], action: () => {} },
  { id: 'sessions', title: 'View Sessions', keywords: ['history', 'list'], action: () => {} },
  { id: 'export', title: 'Export Conversation', keywords: ['save', 'download'], action: () => {} },
  { id: 'new', title: 'New Session', keywords: ['create', 'start'], action: () => {} }
];

test('search returns all commands when query is empty', () => {
  const results = search('', testCommands);
  assert(results.length === 5, `Expected 5, got ${results.length}`);
});

test('search filters by title match', () => {
  const results = search('clear', testCommands);
  assert(results.length === 1, `Expected 1, got ${results.length}`);
  assert(results[0].command.id === 'clear', 'Should match Clear Chat');
});

test('search matches with fuzzy logic (clr -> clear)', () => {
  const results = search('clr', testCommands);
  assert(results.length >= 1, 'Should find at least one match');
  assert(results.some(r => r.command.id === 'clear'), 'Should match "clear"');
});

test('search matches with fuzzy logic (thm -> theme)', () => {
  const results = search('thm', testCommands);
  assert(results.length >= 1, 'Should find at least one match');
  assert(results.some(r => r.command.id === 'theme'), 'Should match "theme"');
});

test('search matches keywords', () => {
  const results = search('dark', testCommands);
  assert(results.some(r => r.command.id === 'theme'), 'Should match "theme" via keyword');
});

test('search ranks exact matches highest', () => {
  // "Clear Chat" starts with "Clear" which matches "clear" case-insensitively
  // This is a prefix match, not exact, so score should be 50 (prefix)
  const results = search('clear', testCommands);
  assert(results[0].command.id === 'clear', 'Clear Chat should be first match');
  assert(results[0].score >= 50, `Prefix match should have good score, got ${results[0].score}`);
});

test('search ranks prefix matches higher than fuzzy', () => {
  const commands = [
    { id: 'chat', title: 'Chat Options', keywords: [], action: () => {} },
    { id: 'clear', title: 'Clear Chat', keywords: [], action: () => {} }
  ];
  const results = search('chat', commands);
  // "Chat Options" has "chat" as prefix of "Chat", should score higher
  // than fuzzy match in "Clear Chat"
  const chatOptionsScore = results.find(r => r.command.id === 'chat')?.score || 0;
  const clearChatScore = results.find(r => r.command.id === 'clear')?.score || 0;
  assert(chatOptionsScore >= clearChatScore, 'Prefix match should score >= fuzzy match');
});

test('search limits results', () => {
  const commands = Array.from({ length: 20 }, (_, i) => ({
    id: `cmd-${i}`,
    title: `Command ${i}`,
    keywords: [],
    action: () => {}
  }));
  const results = search('cmd', commands, { limit: 5 });
  assert(results.length === 5, `Expected 5, got ${results.length}`);
});

test('calculateScore returns 0 for no match', () => {
  const score = calculateScore('xyz', 'clear chat');
  assert(score === 0, 'Should be 0 for no match');
});

test('calculateScore returns high score for exact match', () => {
  const score = calculateScore('clear', 'clear');
  assert(score === 100, `Expected 100, got ${score}`);
});

test('calculateScore returns medium score for prefix match', () => {
  const score = calculateScore('cle', 'clear chat');
  assert(score === 50, `Expected 50, got ${score}`);
});

test('calculateScore returns lower score for fuzzy match', () => {
  const score = calculateScore('clr', 'clear chat');
  assert(score === 25, `Expected 25, got ${score}`);
});

test('isFuzzyMatch returns true for matching characters in order', () => {
  assert(isFuzzyMatch('clr', 'clear'), 'clr should match clear');
  assert(isFuzzyMatch('thm', 'theme'), 'thm should match theme');
  assert(isFuzzyMatch('vw', 'view'), 'vw should match view');
});

test('isFuzzyMatch returns false when characters not in order', () => {
  assert(!isFuzzyMatch('xyz', 'clear'), 'xyz should not match clear');
  assert(!isFuzzyMatch('rlc', 'clear'), 'rlc should not match clear (wrong order)');
});

test('isFuzzyMatch is case insensitive', () => {
  assert(isFuzzyMatch('CLR', 'clear'), 'CLR should match clear');
  assert(isFuzzyMatch('clr', 'CLEAR'), 'clr should match CLEAR');
});

test('getHighlightIndices returns correct character positions', () => {
  const indices = getHighlightIndices('clr', 'Clear Chat');
  assert(indices.length === 3, `Expected 3 indices, got ${indices.length}`);
  // "Clear Chat" = C(0) l(1) e(2) a(3) r(4) " "(5) C(6) h(7) a(8) t(9)
  assert(indices[0] === 0, 'First index should be 0 (C)');
  assert(indices[1] === 1, 'Second index should be 1 (l)');
  assert(indices[2] === 4, 'Third index should be 4 (r)');
});

test('getHighlightIndices handles case insensitive matching', () => {
  const indices = getHighlightIndices('CLR', 'Clear Chat');
  assert(indices.length === 3, 'Should find matches regardless of case');
});

test('search returns highlight indices for matched commands', () => {
  const results = search('clr', testCommands);
  const clearResult = results.find(r => r.command.id === 'clear');
  assert(clearResult, 'Should find clear command');
  assert(clearResult.highlightIndices.length > 0, 'Should have highlight indices');
});

test('search returns matched fields info', () => {
  const results = search('dark', testCommands);
  const themeResult = results.find(r => r.command.id === 'theme');
  assert(themeResult, 'Should find theme command');
  assert(themeResult.matchedFields.includes('keywords'), 'Should indicate keyword match');
});

test('search handles empty command list', () => {
  const results = search('test', []);
  assert(results.length === 0, 'Should return empty array');
});

test('search handles whitespace-only query', () => {
  const results = search('   ', testCommands);
  assert(results.length === 5, 'Should return all commands for whitespace');
});

console.log(`\n${'='.repeat(40)}`);
console.log(`Results: ${testsPassed} passed, ${testsFailed} failed`);
console.log(`${'='.repeat(40)}`);

process.exit(testsFailed > 0 ? 1 : 0);
