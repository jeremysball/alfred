/**
 * Keyboard Shortcuts Module
 *
 * Provides keyboard shortcut registration, help sheet, and message navigation.
 *
 * Usage:
 *   import { KeyboardManager, HelpSheet, MessageNavigator, ShortcutRegistry, KeymapManager } from './keyboard/index.js';
 *
 *   // Initialize keyboard manager with persisted keymap
 *   const keyboardManager = new KeyboardManager();
 *
 *   // Create help sheet (opens with F1)
 *   const helpSheet = new HelpSheet();
 *
 *   // Rebind a shortcut
 *   KeymapManager.setBinding('commandPalette.open', { key: 'P', ctrl: true, shift: true });
 */

// Re-export from help.js
import { HelpSheet } from "./help.js";
// Re-export from keyboard-manager.js
import { KeyboardManager } from "./keyboard-manager.js";
// Re-export from keymap.js
import {
  buildLeaderTree,
  DEFAULT_KEYMAP,
  exportKeymap,
  formatBinding,
  formatLeaderBreadcrumb,
  getBinding,
  getBindingsByCategory,
  getKeymap,
  getLeaderNodeForPath,
  importKeymap,
  loadKeymap,
  matchesBinding,
  resetAllBindings,
  resetBinding,
  saveKeymap,
  setBinding,
  subscribe,
} from "./keymap.js";
// Re-export from navigation.js
import { MessageNavigator } from "./navigation.js";
// Re-export from shortcuts.js
import {
  clear,
  formatShortcut,
  getAll,
  getAllFlat,
  getById,
  parseKeyCombo,
  register,
  unregister,
} from "./shortcuts.js";
// Re-export from which-key.js
import { WhichKey } from "./which-key.js";

// ShortcutRegistry convenience object
const ShortcutRegistry = {
  register,
  getAll,
  getAllFlat,
  getById,
  unregister,
  clear,
  formatShortcut,
  parseKeyCombo,
};

// KeymapManager convenience object
const KeymapManager = {
  DEFAULT_KEYMAP,
  loadKeymap,
  saveKeymap,
  getKeymap,
  getBinding,
  setBinding,
  resetBinding,
  resetAllBindings,
  getBindingsByCategory,
  buildLeaderTree,
  getLeaderNodeForPath,
  formatBinding,
  formatLeaderBreadcrumb,
  matchesBinding,
  subscribe,
  exportKeymap,
  importKeymap,
};

// Also expose registerShortcut as an alias for search module compatibility
const registerShortcut = register;

// Export for ES modules
export {
  buildLeaderTree,
  formatLeaderBreadcrumb,
  getLeaderNodeForPath,
  HelpSheet,
  KeyboardManager,
  KeymapManager,
  MessageNavigator,
  registerShortcut,
  ShortcutRegistry,
  WhichKey,
};

// Set up window globals for main.js
if (typeof window !== "undefined") {
  window.ShortcutRegistry = ShortcutRegistry;
  window.KeymapManager = KeymapManager;
  window.HelpSheet = HelpSheet;
  window.KeyboardManager = KeyboardManager;
  window.MessageNavigator = MessageNavigator;
  window.registerShortcut = registerShortcut;
  window.WhichKey = WhichKey;
}
