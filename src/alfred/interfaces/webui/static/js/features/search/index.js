/**
 * Search Feature Module
 * Milestone 9 Phase 1: In-Conversation Search (Ctrl+F)
 * Milestone 9 Phase 2: Quick Session Switcher (Ctrl+Tab)
 * Milestone 9 Phase 3: @ Mentions
 *
 * Exports: SearchOverlay, QuickSwitcher, MentionDropdown components and initialization functions
 */

import { SearchOverlay } from './search-overlay.js';
import { QuickSwitcher, initializeQuickSwitcher } from './quick-switcher.js';
import { MentionDropdown, initializeMentions } from './mention-dropdown.js';

/**
 * Initialize search feature
 * Registers Ctrl+F keyboard shortcut
 */
function initializeSearch() {
  // Import keyboard shortcuts module
  import('../keyboard/index.js').then(({ registerShortcut }) => {
    registerShortcut({
      id: 'search-in-conversation',
      key: 'f',
      ctrl: true,
      description: 'Search in current conversation',
      action: () => {
        const overlay = SearchOverlay.getInstance();
        overlay.open();
      },
      preventDefault: true // Override browser's native find
    });
  }).catch(error => {
    console.error('[Search] Failed to register keyboard shortcut:', error);
  });
}

/**
 * Check if search is supported in current environment
 * @returns {boolean}
 */
function isSearchSupported() {
  return typeof window !== 'undefined' && typeof window.find === 'function';
}

// Export public API
export {
  SearchOverlay,
  QuickSwitcher,
  MentionDropdown,
  initializeSearch,
  initializeQuickSwitcher,
  initializeMentions,
  isSearchSupported
};

// Default exports for convenience
export default SearchOverlay;
