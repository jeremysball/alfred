/**
 * Code Block Context Menu
 *
 * Context menu for code blocks with copy actions.
 */

import { ContextMenu } from './menu.js';

/**
 * Extract code from a code block element
 * @param {HTMLElement} codeBlock
 * @returns {string}
 */
function getCodeText(codeBlock) {
  // Try to find the code element
  const codeEl = codeBlock.querySelector('code, pre code');
  if (codeEl) {
    return codeEl.textContent;
  }

  // Fallback: the element itself
  return codeBlock.textContent;
}

/**
 * Get the language from a code block
 * @param {HTMLElement} codeBlock
 * @returns {string|null}
 */
function getCodeLanguage(codeBlock) {
  // Check data attribute
  if (codeBlock.dataset.language) {
    return codeBlock.dataset.language;
  }

  // Check class (e.g., "language-python")
  const match = codeBlock.className.match(/language-(\w+)/);
  if (match) {
    return match[1];
  }

  // Check parent pre element
  const parent = codeBlock.closest('pre');
  if (parent) {
    const parentMatch = parent.className.match(/language-(\w+)/);
    if (parentMatch) {
      return parentMatch[1];
    }
  }

  return null;
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
 * Show context menu for a code block
 * @param {HTMLElement} codeBlock
 * @param {number} x - Mouse X coordinate
 * @param {number} y - Mouse Y coordinate
 */
function showCodeMenu(codeBlock, x, y) {
  const menu = new ContextMenu();
  const codeText = getCodeText(codeBlock);
  const language = getCodeLanguage(codeBlock);

  const items = [
    {
      id: 'copy-code',
      label: 'Copy',
      icon: '📋',
      shortcut: 'Ctrl+C',
      action: async () => {
        const success = await copyToClipboard(codeText);
        if (success) {
          showToast('Code copied to clipboard');
        }
      }
    },
    {
      id: 'copy-as-markdown',
      label: 'Copy as Markdown',
      icon: '📝',
      action: async () => {
        const lang = language || '';
        const markdown = '```' + lang + '\n' + codeText + '\n```';
        const success = await copyToClipboard(markdown);
        if (success) {
          showToast('Markdown copied to clipboard');
        }
      }
    }
  ];

  // Add language-specific option if detected
  if (language) {
    items.push({ type: 'separator' });
    items.push({
      id: 'language-indicator',
      label: `Language: ${language}`,
      icon: '🔧',
      disabled: true
    });
  }

  menu.show({ x, y, items, triggerElement: codeBlock });
}

/**
 * Attach context menu to a code block element
 * @param {HTMLElement} codeBlock
 */
function attachCodeMenu(codeBlock) {
  // Right-click
  codeBlock.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    e.stopPropagation();
    showCodeMenu(codeBlock, e.clientX, e.clientY);
  });

  // Shift+F10 keyboard shortcut
  codeBlock.addEventListener('keydown', (e) => {
    if (e.shiftKey && e.key === 'F10') {
      e.preventDefault();
      const rect = codeBlock.getBoundingClientRect();
      showCodeMenu(codeBlock, rect.left, rect.top);
    }
  });

  // Make focusable
  if (!codeBlock.hasAttribute('tabindex')) {
    codeBlock.setAttribute('tabindex', '0');
  }
}

/**
 * Attach context menus to all code blocks
 */
function attachToAllCodeBlocks() {
  const codeBlocks = document.querySelectorAll('pre, code.hljs, code[class*="language-"], .code-block');
  codeBlocks.forEach(block => {
    if (!block.dataset.contextMenuAttached) {
      attachCodeMenu(block);
      block.dataset.contextMenuAttached = 'true';
    }
  });
}

// Export for ESM and browser
export {
  showCodeMenu,
  attachCodeMenu,
  attachToAllCodeBlocks,
  getCodeText,
  getCodeLanguage,
  copyToClipboard
};

if (typeof window !== 'undefined') {
  window.CodeContextMenu = {
    showCodeMenu,
    attachCodeMenu,
    attachToAllCodeBlocks,
    getCodeText,
    getCodeLanguage,
    copyToClipboard
  };
}
