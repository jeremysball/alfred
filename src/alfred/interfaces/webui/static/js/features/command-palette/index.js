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

import { clear, getAll, getById, register, unregister } from "./commands.js";

import {
  benchmark,
  calculateScore,
  getHighlightIndices,
  isFuzzyMatch,
  search,
} from "./fuzzy-search.js";

import { CommandPalette } from "./palette.js";

// Command Registry API
const CommandRegistry = {
  register,
  getAll,
  getById,
  unregister,
  clear,
};

// Fuzzy Search API
const FuzzySearch = {
  search,
  benchmark,
  calculateScore,
  isFuzzyMatch,
  getHighlightIndices,
};

// Create library namespace on window
if (typeof window !== "undefined") {
  window.CommandPaletteLib = {
    CommandPalette,
    CommandRegistry,
    FuzzySearch,
  };
}

// Export for ES modules
export { CommandPalette, CommandRegistry, FuzzySearch };
