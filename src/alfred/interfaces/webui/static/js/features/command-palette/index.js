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

// Import dependencies
const { register, getAll, getById, unregister, clear } = require('./commands.js');
const { search, benchmark, calculateScore, isFuzzyMatch, getHighlightIndices } = require('./fuzzy-search.js');
const { CommandPalette } = require('./palette.js');

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

// Export everything
module.exports = {
  CommandPalette,
  CommandRegistry,
  FuzzySearch
};

// Also expose on window for browser usage
if (typeof window !== 'undefined') {
  window.CommandPaletteLib = {
    CommandPalette,
    CommandRegistry,
    FuzzySearch
  };
}
