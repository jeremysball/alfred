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

// Import from window globals set up by individual modules
const ContextMenu = window.ContextMenu || class {};
const MessageContextMenu = window.MessageContextMenu || {};
const CodeContextMenu = window.CodeContextMenu || {};

// Re-export everything
const ContextMenuLib = {
  ContextMenu,
  MessageContextMenu,
  CodeContextMenu,
};

// Export for ES modules
export { CodeContextMenu, ContextMenu, ContextMenuLib, MessageContextMenu };

// Also expose on window
if (typeof window !== "undefined") {
  window.ContextMenuLib = ContextMenuLib;
}
