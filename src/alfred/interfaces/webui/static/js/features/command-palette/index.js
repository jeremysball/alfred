/**
 * Command Palette - Universal search and action launcher
 *
 * Exports:
 * - CommandRegistry: Register and manage commands
 * - FuzzySearch: Search and score commands
 * - CommandPalette: UI component (modal + keyboard handling)
 *
 * Usage:
 *   import { CommandPalette, CommandRegistry } from './command-palette/index.js';
 *
 *   // Register commands
 *   CommandRegistry.register({
 *     id: 'clear-chat',
 *     title: 'Clear Chat',
 *     keywords: ['reset', 'clean'],
 *     shortcut: 'Ctrl+Shift+C',
 *     action: () => window.dispatchEvent(new CustomEvent('chat:clear'))
 *   });
 *
 *   // Create and use palette
 *   const palette = new CommandPalette();
 *   // Press Ctrl+K to open
 */

// Import dependencies (works with both CommonJS and ES modules)
let register, getAll, getById, unregister, clear;
let search, benchmark, calculateScore, isFuzzyMatch, getHighlightIndices;
let CommandPalette;

if (typeof require !== 'undefined') {
  // CommonJS (Node.js/testing)
  const commands = require('./commands.js');
  register = commands.register;
  getAll = commands.getAll;
  getById = commands.getById;
  unregister = commands.unregister;
  clear = commands.clear;

  const fuzzy = require('./fuzzy-search.js');
  search = fuzzy.search;
  benchmark = fuzzy.benchmark;
  calculateScore = fuzzy.calculateScore;
  isFuzzyMatch = fuzzy.isFuzzyMatch;
  getHighlightIndices = fuzzy.getHighlightIndices;

  const palette = require('./palette.js');
  CommandPalette = palette.CommandPalette;
} else {
  // ES modules or browser globals
  // Will be set below from window exports
}

// For browser: load from window exports
if (typeof window !== 'undefined') {
  const waitForDeps = () => {
    if (window.CommandRegistry && window.FuzzySearch && window.CommandPalette) {
      register = window.CommandRegistry.register;
      getAll = window.CommandRegistry.getAll;
      getById = window.CommandRegistry.getById;
      unregister = window.CommandRegistry.unregister;
      clear = window.CommandRegistry.clear;

      search = window.FuzzySearch.search;
      benchmark = window.FuzzySearch.benchmark;
      calculateScore = window.FuzzySearch.calculateScore;
      isFuzzyMatch = window.FuzzySearch.isFuzzyMatch;
      getHighlightIndices = window.FuzzySearch.getHighlightIndices;

      CommandPalette = window.CommandPalette;

      // Create library namespace
      window.CommandPaletteLib = {
        CommandPalette,
        CommandRegistry: { register, getAll, getById, unregister, clear },
        FuzzySearch: { search, benchmark, calculateScore, isFuzzyMatch, getHighlightIndices }
      };
    } else {
      setTimeout(waitForDeps, 10);
    }
  };
  waitForDeps();
}

// Command Registry API
const CommandRegistry = {
  register,
  getAll,
  getById,
  unregister,
  clear
};

// Fuzzy Search API
const FuzzySearch = {
  search,
  benchmark,
  calculateScore,
  isFuzzyMatch,
  getHighlightIndices
};

// Export for CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    CommandPalette,
    CommandRegistry,
    FuzzySearch
  };
}

// Export for ES modules
export { CommandPalette, CommandRegistry, FuzzySearch };
