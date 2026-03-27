/**
 * Keyboard Shortcuts Module
 *
 * Provides keyboard shortcut registration, help modal, and message navigation.
 *
 * Usage:
 *   import { KeyboardManager, HelpModal, MessageNavigator, ShortcutRegistry } from './keyboard/index.js';
 *
 *   // Register shortcuts
 *   ShortcutRegistry.register({
 *     id: 'show-help',
 *     key: '?',
 *     description: 'Show keyboard shortcuts',
 *     category: 'Global',
 *     action: () => helpModal.show()
 *   });
 *
 *   // Initialize keyboard manager
 *   const keyboardManager = new KeyboardManager();
 *
 *   // Create help modal
 *   const helpModal = new HelpModal();
 */

// Import from window globals (loaded via script tags)
const {
  register,
  getAll,
  getAllFlat,
  getById,
  unregister,
  clear,
  formatShortcut,
  parseKeyCombo
} = window.ShortcutRegistry || {};

const HelpModal = window.HelpModal;
const KeyboardManager = window.KeyboardManager;
const MessageNavigator = window.MessageNavigator;

// ShortcutRegistry convenience object
const ShortcutRegistry = {
  register,
  getAll,
  getAllFlat,
  getById,
  unregister,
  clear,
  formatShortcut,
  parseKeyCombo
};

// Export for ES modules
export { ShortcutRegistry, HelpModal, KeyboardManager, MessageNavigator };
