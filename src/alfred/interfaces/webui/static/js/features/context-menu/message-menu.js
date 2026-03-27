/**
 * Message Context Menu
 *
 * Context menu for chat messages with copy and quote actions.
 */

import { ContextMenu } from './menu.js';

/**
 * Extract text content from a message element
 * @param {HTMLElement} messageElement
 * @returns {string}
 */
function getMessageText(messageElement) {
  // Try to find the message content
  const contentEl = messageElement.querySelector('.message-content, .content, [data-message-content]');
  if (contentEl) {
    return contentEl.textContent.trim();
  }

  // Fallback: get all text except metadata
  const clone = messageElement.cloneNode(true);
  const metadata = clone.querySelector('.message-metadata, .timestamp, .author, .avatar');
  if (metadata) {
    metadata.remove();
  }
  return clone.textContent.trim();
}

/**
 * Copy text to clipboard
 * @param {string} text
 * @returns {Promise<boolean>}
 */
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    console.error('Failed to copy:', err);
    return false;
  }
}

/**
 * Show toast notification
 * @param {string} message
 */
function showToast(message) {
  if (window.addSystemMessage) {
    window.addSystemMessage(message);
  } else {
    console.log(message);
  }
}

/**
 * Quote a message in the input
 * @param {string} text
 * @param {string} [author]
 */
function quoteMessage(text, author) {
  const input = document.getElementById('message-input');
  if (!input) return;

  const quoteText = author
    ? `> ${author}: ${text.split('\n').join('\n> ')}\n\n`
    : `> ${text.split('\n').join('\n> ')}\n\n`;

  const currentValue = input.value;
  const cursorPos = input.selectionStart;

  const newValue = currentValue.slice(0, cursorPos) + quoteText + currentValue.slice(cursorPos);
  input.value = newValue;
  input.focus();
  input.selectionStart = input.selectionEnd = cursorPos + quoteText.length;
}

/**
 * Show context menu for a message
 * @param {HTMLElement} messageElement
 * @param {number} x - Mouse X coordinate
 * @param {number} y - Mouse Y coordinate
 */
function showMessageMenu(messageElement, x, y) {
  const menu = new ContextMenu();
  const messageText = getMessageText(messageElement);
  const authorEl = messageElement.querySelector('.message-author, .author, [data-author]');
  const author = authorEl ? authorEl.textContent.trim() : '';

  const items = [
    {
      id: 'copy-text',
      label: 'Copy Text',
      icon: '📋',
      shortcut: 'Ctrl+C',
      action: async () => {
        const success = await copyToClipboard(messageText);
        if (success) {
          showToast('Message copied to clipboard');
        }
      }
    },
    {
      id: 'quote-reply',
      label: 'Quote Reply',
      icon: '💬',
      action: () => {
        quoteMessage(messageText, author);
        showToast('Quote added to input');
      }
    },
    { type: 'separator' },
    {
      id: 'select-all',
      label: 'Select All',
      icon: '☐',
      shortcut: 'Ctrl+A',
      action: () => {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(messageElement);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    }
  ];

  menu.show({ x, y, items, triggerElement: messageElement });
}

/**
 * Attach context menu to a message element
 * @param {HTMLElement} messageElement
 */
function attachMessageMenu(messageElement) {
  // Right-click
  messageElement.addEventListener('contextmenu', (e) => {
    // Don't show if clicking on a link or button
    if (e.target.closest('a, button, input, textarea')) {
      return;
    }

    e.preventDefault();
    showMessageMenu(messageElement, e.clientX, e.clientY);
  });

  // Shift+F10 keyboard shortcut
  messageElement.addEventListener('keydown', (e) => {
    if (e.shiftKey && e.key === 'F10') {
      e.preventDefault();
      const rect = messageElement.getBoundingClientRect();
      showMessageMenu(messageElement, rect.left, rect.top);
    }
  });
}

/**
 * Attach context menus to all message elements
 */
function attachToAllMessages() {
  const messages = document.querySelectorAll('.message');
  messages.forEach(msg => {
    if (!msg.dataset.contextMenuAttached) {
      attachMessageMenu(msg);
      msg.dataset.contextMenuAttached = 'true';
    }
  });
}

// Export for ESM and browser
export {
  showMessageMenu,
  attachMessageMenu,
  attachToAllMessages,
  getMessageText,
  copyToClipboard,
  quoteMessage
};

if (typeof window !== 'undefined') {
  window.MessageContextMenu = {
    showMessageMenu,
    attachMessageMenu,
    attachToAllMessages,
    getMessageText,
    copyToClipboard,
    quoteMessage
  };
}
