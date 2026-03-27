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

// Re-export all modules
const shortcuts = typeof require !== 'undefined' ? require('./shortcuts.js') : (window.ShortcutRegistry || {});
const help = typeof require !== 'undefined' ? require('./help.js') : (window.HelpModal ? { HelpModal: window.HelpModal } : {});
const keyboardManager = typeof require !== 'undefined' ? require('./keyboard-manager.js') : (window.KeyboardManager ? { KeyboardManager: window.KeyboardManager } : {});
const navigation = typeof require !== 'undefined' ? require('./navigation.js') : (window.MessageNavigator ? { MessageNavigator: window.MessageNavigator } : {});

const { register, getAll, getAllFlat, getById, unregister, clear, formatShortcut, parseKeyCombo } = shortcuts;
const { HelpModal } = help;
const { KeyboardManager } = keyboardManager;
const { MessageNavigator } = navigation;

// ShortcutRegistry convenience object
const ShortcutRegistry = { register, getAll, getAllFlat, getById, unregister, clear, formatShortcut, parseKeyCombo };

// Export for CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    ShortcutRegistry,
    HelpModal,
    KeyboardManager,
    MessageNavigator
  };
}

// Export for ES modules
export { ShortcutRegistry, HelpModal, KeyboardManager, MessageNavigator };
