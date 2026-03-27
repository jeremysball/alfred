/**
 * Fuzzy Search Engine for Command Palette
 *
 * Uses native Intl.Collator for fast, locale-aware string matching.
 * Falls back to character-by-character fuzzy matching if needed.
 */

/**
 * @typedef {Object} SearchResult
 * @property {Command} command - The matched command
 * @property {number} score - Match score (higher = better)
 * @property {string[]} matchedFields - Which fields matched ('title', 'keywords')
 * @property {number[]} highlightIndices - Character indices to highlight in title
 */

// Scoring constants
const SCORE_EXACT = 100;
const SCORE_PREFIX = 50;
const SCORE_FUZZY = 25;
const SCORE_KEYWORD_MATCH = 10;

// Create collator for case-insensitive, punctuation-agnostic comparison
const collator = new Intl.Collator('en', {
  sensitivity: 'base',
  ignorePunctuation: true
});

/**
 * Calculate fuzzy match score for query against text
 * @param {string} query - The search query
 * @param {string} text - The text to search in
 * @returns {number} Score (0 = no match, higher = better)
 */
function calculateScore(query, text) {
  if (!query || !text) return 0;

  const queryLower = query.toLowerCase();
  const textLower = text.toLowerCase();

  // Exact match
  if (textLower === queryLower) {
    return SCORE_EXACT;
  }

  // Prefix match (starts with query)
  if (textLower.startsWith(queryLower)) {
    return SCORE_PREFIX;
  }

  // Word boundary match (e.g., "Clear chat" matches "chat" at word boundary)
  const wordBoundaryRegex = new RegExp(`\\b${escapeRegex(queryLower)}`, 'i');
  if (wordBoundaryRegex.test(textLower)) {
    return SCORE_PREFIX - 5; // Slightly less than prefix
  }

  // Fuzzy match: all characters in query appear in order in text
  if (isFuzzyMatch(queryLower, textLower)) {
    return SCORE_FUZZY;
  }

  return 0;
}

/**
 * Check if query is a fuzzy match against text
 * (all characters in query appear in order in text)
 * @param {string} query
 * @param {string} text
 * @returns {boolean}
 */
function isFuzzyMatch(query, text) {
  if (!query) return true;
  if (!text) return false;

  let queryIndex = 0;
  let textIndex = 0;

  while (queryIndex < query.length && textIndex < text.length) {
    // Use collator for case-insensitive comparison
    if (collator.compare(query[queryIndex], text[textIndex]) === 0) {
      queryIndex++;
    }
    textIndex++;
  }

  return queryIndex === query.length;
}

/**
 * Escape special regex characters
 * @param {string} str
 * @returns {string}
 */
function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Get indices of matched characters for highlighting
 * @param {string} query
 * @param {string} text
 * @returns {number[]}
 */
function getHighlightIndices(query, text) {
  if (!query || !text) return [];

  const indices = [];
  const queryLower = query.toLowerCase();
  const textLower = text.toLowerCase();

  let queryIndex = 0;

  for (let i = 0; i < text.length && queryIndex < queryLower.length; i++) {
    if (collator.compare(queryLower[queryIndex], textLower[i]) === 0) {
      indices.push(i);
      queryIndex++;
    }
  }

  return indices;
}

/**
 * Search commands with fuzzy matching
 * @param {string} query - The search query
 * @param {Command[]} commands - Array of commands to search
 * @param {Object} [options] - Search options
 * @param {number} [options.limit=10] - Maximum results to return
 * @returns {SearchResult[]} Sorted results (best matches first)
 */
function search(query, commands, options = {}) {
  const { limit = 10 } = options;

  if (!query || !query.trim()) {
    // Return all commands with no score when query is empty
    return commands.map(cmd => ({
      command: cmd,
      score: 0,
      matchedFields: [],
      highlightIndices: []
    })).slice(0, limit);
  }

  const queryStr = query.trim();
  const results = [];

  for (const cmd of commands) {
    let score = 0;
    const matchedFields = [];

    // Check title match
    const titleScore = calculateScore(queryStr, cmd.title);
    if (titleScore > 0) {
      score += titleScore;
      matchedFields.push('title');
    }

    // Check keyword matches (additive scoring)
    if (cmd.keywords && cmd.keywords.length > 0) {
      for (const keyword of cmd.keywords) {
        const keywordScore = calculateScore(queryStr, keyword);
        if (keywordScore > 0) {
          score += keywordScore * 0.5; // Keywords worth less than title
          if (!matchedFields.includes('keywords')) {
            matchedFields.push('keywords');
          }
        }
      }
    }

    // Only include commands that match
    if (score > 0) {
      results.push({
        command: cmd,
        score,
        matchedFields,
        highlightIndices: getHighlightIndices(queryStr, cmd.title)
      });
    }
  }

  // Sort by score descending
  results.sort((a, b) => b.score - a.score);

  return results.slice(0, limit);
}

/**
 * Benchmark search performance
 * @param {string} query
 * @param {Command[]} commands
 * @param {number} iterations - Number of iterations
 * @returns {number} Average time in milliseconds
 */
function benchmark(query, commands, iterations = 100) {
  const start = performance.now();

  for (let i = 0; i < iterations; i++) {
    search(query, commands);
  }

  const total = performance.now() - start;
  return total / iterations;
}

// Export for both CommonJS and ES modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { search, benchmark, calculateScore, isFuzzyMatch, getHighlightIndices };
}

if (typeof window !== 'undefined') {
  window.FuzzySearch = { search, benchmark, calculateScore, isFuzzyMatch, getHighlightIndices };
}
