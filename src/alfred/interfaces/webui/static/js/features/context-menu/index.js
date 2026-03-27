/**
 * Context Menu Module
 *
 * Provides right-click context menus for messages and code blocks.
 *
 * Usage:
 *   import { ContextMenu, MessageContextMenu, CodeContextMenu } from './context-menu/index.js';
 *
 *   // Show message menu
 *   MessageContextMenu.showMessageMenu(messageElement, x, y);
 *
 *   // Show code menu
 *   CodeContextMenu.showCodeMenu(codeBlock, x, y);
 *
 *   // Attach to all existing elements
 *   MessageContextMenu.attachToAllMessages();
 *   CodeContextMenu.attachToAllCodeBlocks();
 */

// Import modules (works with both CommonJS and browser globals)
const menu = typeof require !== 'undefined' ? require('./menu.js') : (window.ContextMenu ? { ContextMenu: window.ContextMenu } : {});
const messageMenu = typeof require !== 'undefined' ? require('./message-menu.js') : (window.MessageContextMenu || {});
const codeMenu = typeof require !== 'undefined' ? require('./code-menu.js') : (window.CodeContextMenu || {});

const { ContextMenu } = menu;

// Re-export everything
const ContextMenuModule = {
  ContextMenu,
  MessageContextMenu: messageMenu,
  CodeContextMenu: codeMenu
};

// Export for CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ContextMenuModule;
}

// Export for ES modules
export { ContextMenu };
export const MessageContextMenu = messageMenu;
export const CodeContextMenu = codeMenu;

// Also expose on window
if (typeof window !== 'undefined') {
  window.ContextMenuLib = ContextMenuModule;
}
